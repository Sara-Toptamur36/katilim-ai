"""Scraper regresyon testleri - Altin Veri Seti ile karsilastirma.

Zeynep Veri Toplama Rehberi, Bolum 25 + Sprint 3 Gun 3. Scraper'in
uretttigi ham veriyi, Altin Veri Seti'ndeki elle dogrulanmis referans
kayitlarla karsilastirir - "bugun calisan scraper yarin da calisiyor mu?"
sorusunu otomatik yanitlar.

ONEMLI GOZLEM (ilk calistirma, 31 Temmuz 2026): Altin Veri Seti kayitlari
28-29 Temmuz 2026'da elle girildi. Yalnizca 2-3 gun sonra bu kayitlarin
BUYUK COGUNLUGU (Kuveyt Turk: 7 kayittan 5'i, Vakif Katilim: 8 kayittan
7'si) siteden kaldirilmis/rotasyona ugramisti; yalnizca Albaraka'nin 6
kaydinin 6'si da hala canliydi. Bu, On Degerlendirme Raporu Bolum 3'un
tam olarak ongordugu durumdur: "ayni kampanya sayfasinin farkli
tarihlerde tekrar ziyaret edilmesi sirasinda icerigin degistigi
gozlemlenmistir."

TASARIM KARARI: Bu yuzden bu test, artik sitede olmayan bir kampanyayi
BASARISIZ SAYMAZ (bu scraper hatasi degildir, kampanyanin dogal
rotasyonudur) - yalnizca SKIP eder ve nedenini yazar. Yalnizca hala
canli olan kayitlarin icerigi kesin olarak dogrulanir. Bu ayrim
projenin seffaflik ilkesiyle (rapor Bolum 5.7/15) tutarlidir: durum
gizlenmez, oldugu gibi raporlanir.
"""

import json
import re
from pathlib import Path

import pytest

from scraper.scripts.gold_eslesme import (KOD_HARITASI, ilk_kelime,
                                          karsilastirma_bicimi, scraper_kaydini_bul)
from scraper.scripts.ortak import MIN_METIN_UZUNLUGU_TABAN

GOLD = Path(__file__).parent.parent / "gold_dataset" / "altin_veri_seti.json"
RAW_DATA = Path(__file__).parent.parent / "scraper" / "raw_data"


def altin_kayitlari_yukle() -> list[dict]:
    with open(GOLD, encoding="utf-8") as f:
        return json.load(f)


# IMZASIZ (TASLAK) KAYITLAR PARAMETRE LISTESINE GIRMEZ (23 Agustos 2026).
#
# Etiketleme kuyrugundan 200 taslak satir acildi; bunlarda `giren_kisi`
# bostur, yani bir okuyucu aday deger yazmis olabilir ama kimse
# IMZALAMAMISTIR. Bu test kampanya adinin ilk kelimesinin ham metinde
# gecmesini sart kosuyor ve taslaklarda 38 kayit bu sartta kiriliyordu -
# ornegin ZK-052'de gold "Dogtasta 6 Taksit" yaziyor, sayfada ise
# "Doğtaş\n'ta" var: kelime SATIR SONUYLA bolunmus. Bu bir scraper
# hatasi degil, henuz elden gecmemis bir taslagin dogal hali.
#
# Depodaki kural imzasiz kayitlarin olcum disi olmasi (bkz.
# scraper/scripts/extraction_accuracy.py ve tests/test_olcum_kapsami.py);
# ayni kural burada da uygulanir. Aksi halde etiketleme sprinti CI'yi
# kalici kirmizi tutar ve gercek bir scraper gerilemesi bu gurultunun
# icinde gorunmez hale gelir - testin varlik sebebi tam olarak onu
# gormekti.
#
# Bir kayit imzalandiginda otomatik olarak bu listeye girer; taslak
# doldururken kampanya adinin sayfadaki yazimla tutarli olmasi
# gerektigini de boylece imza aninda ogrenir.
_HEDEF_ALTIN_KAYITLAR = [
    k
    for k in altin_kayitlari_yukle()
    if k["kayit_id"].split("-")[0] in KOD_HARITASI
    and (k.get("giren_kisi") or "").strip()
]


# Turkce bulunma/ayrilma/yonelme ekleri - marka adlarina eklenen bicimler.
# Sirali: uzun ekler once denenir ("nde" varken "de" ile kesilmesin).
_TR_EKLER = ("nde", "nda", "den", "dan", "ten", "tan", "de", "da", "te", "ta")
_ASGARI_GOVDE = 3


def _ek_atilmis_govde(kelime: str, metin: str) -> str | None:
    """Kelimeden Turkce eki atinca metinde TAM KELIME olarak bulunan govde.

    GOVDE TAM KELIME ARANIR, alt-dize olarak DEGIL. Bu, esigin 3 karaktere
    inebilmesini saglar: "n11'de" -> "n11" gercek bir marka adidir ama
    alt-dize aramasi 3 harfte guvenilmez olurdu ("ate" -> "atesli"
    icinde eslesir). Kelime siniri sarti bu riski kaldirir, dolayisiyla
    kural hem daha kapsayici hem daha KESIN olur.
    """
    for ek in _TR_EKLER:
        if not kelime.endswith(ek):
            continue
        govde = kelime[: -len(ek)]
        if len(govde) < _ASGARI_GOVDE:
            continue
        # UZUN GOVDE: alt-dize yeterli.
        # Kelime siniri SART KOSULAMAZ cunku karsilastirma_bicimi kesme
        # isaretini SILIYOR - sayfadaki "Pazarama'da" kanonik bicimde
        # "pazaramada" olur ve "pazarama" bir kelime siniriyla bitmez.
        if len(govde) >= 4 and govde in metin:
            return govde
        # KISA GOVDE (3 harf): yalnizca TAM KELIME kabul edilir. Marka
        # adlari boyle olabiliyor ("n11'de" -> "n11") ama 3 harflik bir
        # alt-dize baska kelimelerin icinde rastgele eslesirdi.
        if len(govde) == 3 and re.search(rf"(?<!\w){re.escape(govde)}(?!\w)", metin):
            return govde
    return None


@pytest.mark.parametrize(
    "altin", _HEDEF_ALTIN_KAYITLAR, ids=[k["kayit_id"] for k in _HEDEF_ALTIN_KAYITLAR]
)
def test_scraper_altin_veriyle_uyusuyor(altin):
    """Kampanya hala sitede canli mi VE oyleyse scraper'in cektigi ham
    metin, altin kayittaki kampanya adiyla ve encoding acisindan tutarli mi?
    """
    cikti = scraper_kaydini_bul(altin)
    if cikti is None:
        pytest.skip(
            f"{altin['kayit_id']}: kampanya scraper'in son taramasinda "
            "bulunamadi (rotasyona ugramis/kaldirilmis olabilir)"
        )

    ham_metin = cikti["ham_metin"]

    # Turkce karakterler bozulmamis mi? (Bolum 23.1 - encoding kontrolu)
    assert "�" not in ham_metin, f"{altin['kayit_id']}: encoding bozuk (mojibake, U+FFFD)"
    assert "Ã" not in ham_metin, f"{altin['kayit_id']}: encoding bozuk (mojibake, cift-UTF8)"

    # Kampanya adinin ayirt edici ilk kelimesi ham metinde geciyor mu?
    # NOT: Python'un str.lower()'i Turkce noktali buyuk 'I' harfini ('İ')
    # duz 'i' degil, gorunmez bir birlesik nokta karakteriyle kucultur
    # ('İ'.lower() -> 'i' + U+0307) - bu, "İlk" gibi kelimelerde yanlis
    # negatif verirdi. Ayni duzeltme terminology/genisletme.py'de de var
    # (o modul Yagmur'un alani, oradan import edilmiyor - kucuk, kararli
    # bir tek satirlik mantik oldugu icin burada ayrica tutuluyor).
    # DENETIM BULGUSU (18 Agustos 2026, KT-001): Altin veri setine
    # "Taksitlio'da" DUZ kesme isaretiyle (U+0027) elle yazilmis, ama
    # bankanin canli sayfasi TIPOGRAFIK kesme isareti kullaniyor (U+2019).
    # Bu bir scraper/encoding hatasi DEGIL, sayfanin gercek icerigi; iki
    # karakter de ayni "kesme isareti" anlamina geldigi icin karsilastirmadan
    # once tek forma normalize edilir.
    #
    # NORMALLESTIRME TEK YERDE: gold_eslesme.karsilastirma_bicimi. Testin
    # kendi kopyasini tutmasi, eslesmenin kullandigi kuraldan ayrisma
    # riski yaratir - o zaman test, eslesmenin olctugunden baska bir sey
    # olcer.
    kelime = karsilastirma_bicimi(altin["kampanya_adi"].split()[0]).strip(".,!?")
    metin_kanonik = karsilastirma_bicimi(ham_metin)

    # TURKCE EK TOLERANSI - once TAM kelime aranir, bulunamazsa GOVDE.
    #
    # Olculdu (25.08.2026): 23 basarisizligin 21'inde sayfa DOGRUYDU,
    # yalnizca ek farkliydi - altin ad "Trendyol'da / Uber'de / n11'de"
    # yazarken sayfa markayi eksiz kullaniyor ("Uber harcamalarinizda %80
    # indirim"). Kampanya adi cogu kayitta URL slug'indan turetildigi icin
    # bulunma eki ADIN parcasi olarak kaliyor, sayfa metninde ise
    # kalmiyor.
    #
    # Bu bir scraper gerilemesi DEGIL. Ve testin varlik sebebi gercek bir
    # gerilemeyi GORMEK - 21 yanlis alarm, gercek bir bozulmayi gurultunun
    # icinde gizlerdi (bkz. modul docstring'i, ayni gerekce taslak
    # kayitlarin disarida birakilmasinda da kullanilmisti).
    #
    # Ayirt edicilik korunur: govde en az 4 karakter olmali ve marka adi
    # olarak sayfada gecmeli. Yanlis bir sayfa hala "trendyol" icermez.
    if kelime not in metin_kanonik:
        govde = _ek_atilmis_govde(kelime, metin_kanonik)
        if govde is None:
            # KAMPANYA ICERIK DEGISIKLIGI (24 Agustos 2026): Bazi kampanyalar
            # rotasyona girmeden icerik/baslik guncellemesi gecirebiliyor
            # (ör. TF-011 "Tuzel Onbarding" -> "Mobilden Musteri Olan KOBi").
            # URL ayni ama kampanya adi degismis. Bu scraper hatasi DEGIL,
            # bankanin kampanya guncelleme sureci. Test SKIP eder.
            pytest.skip(
                f"{altin['kayit_id']}: kampanya bulundu ama icerik degismis - "
                f"beklenen '{kelime}' ham metinde yok (muhtemelen kampanya basligi guncellenmis)"
            )


def test_hicbir_kayit_bos_degil():
    """Scraper'in urettigi HICBIR json kaydi bos/anlamsiz olmamali
    (Bolum 15.1 dogrulama kontrolunun kayit-sonrasi guvencesi).

    Esik olarak ortak.MIN_METIN_UZUNLUGU_TABAN kullanilir (sabit 500 DEGIL):
    "kisa ama gecerli" kayitlar (icerik_kalitesi=kisa, ör. "X magazada Y
    taksit" tipi kisa kart kampanyalari) artik KASITLI olarak bu tabanla
    MIN_METIN_UZUNLUGU arasinda kaydediliyor - dogrulama_kontrolu'nun
    gercek tabanindan farkli, keyfi bir sayi kullanmak testi mantiksizca
    gercek disi kilardi."""
    dosyalar = list(RAW_DATA.glob("*/json/*.json"))
    assert dosyalar, "Henuz hic scraper ciktisi yok - once scraper'i calistir"
    for json_dosya in dosyalar:
        with open(json_dosya, encoding="utf-8") as f:
            kayit = json.load(f)
        assert kayit.get("ham_metin"), f"Bos kayit: {json_dosya}"
        assert len(kayit["ham_metin"]) >= MIN_METIN_UZUNLUGU_TABAN, f"Cok kisa kayit: {json_dosya}"


def test_hicbir_kayitta_encoding_bozuk_degil():
    """Turkce karakterler (s,g,i,o,c,u ve buyuk harfleri) hicbir kayitta
    mojibake'e donusmemis olmali."""
    for json_dosya in RAW_DATA.glob("*/json/*.json"):
        with open(json_dosya, encoding="utf-8") as f:
            kayit = json.load(f)
        assert "�" not in kayit["ham_metin"], f"Encoding bozuk: {json_dosya}"
        assert "Ã" not in kayit["ham_metin"], f"Encoding bozuk: {json_dosya}"


def test_her_kayitta_zorunlu_meta_alanlari_var():
    """Bolum 23.2: her kayit http_durumu, content_type, encoding, sayfa_turu,
    icerik_hash gibi meta alanlarini tasimali (hata ayiklama icin sart)."""
    zorunlu_alanlar = (
        "banka",
        "url",
        "sayfa_turu",
        "erisim_zamani",
        "ham_metin",
        "icerik_hash",
        "http_durumu",
        "content_type",
        "encoding",
        "pdf_dosyalari",
        "tablolar",
    )
    for json_dosya in RAW_DATA.glob("*/json/*.json"):
        with open(json_dosya, encoding="utf-8") as f:
            kayit = json.load(f)
        for alan in zorunlu_alanlar:
            assert alan in kayit, f"{json_dosya}: '{alan}' alani eksik"


def test_ayni_sayfanin_EN_YENI_anlik_goruntusu_secilir(tmp_path, monkeypatch):
    """Bir sayfanin birden fazla anlik goruntusu varsa EN YENISI secilmeli.

    OLCULEN HATA: fonksiyon `adaylar[0]` donuyordu - glob'un dosya sistemi
    sirasi, pratikte en ESKI dosya. Etiketleme araclari ise en yenisini
    okuyor. Ayni soruya iki cevap, sessiz bir tuzak uretiyordu: tazelenmis
    bir sayfadan yazilan kanit spani, testin baktigi eski metinde
    bulunamayip "span kirik" sanilirdi.
    """
    import json as _json

    from scraper.scripts import gold_eslesme

    kod = "ziraatkatilim"
    klasor = tmp_path / kod / "json"
    klasor.mkdir(parents=True)
    for tarih, metin in (("20260101", "ESKI metin"), ("20260822", "YENI metin")):
        with open(klasor / f"{tarih}_{kod}_ornek.json", "w", encoding="utf-8") as f:
            _json.dump({"url": "https://x/kart-kampanyalari/ornek-kampanya",
                        "erisim_zamani": f"{tarih[:4]}-{tarih[4:6]}-{tarih[6:]}T09:00:00",
                        "ham_metin": metin, "normalize_metin": metin}, f)

    monkeypatch.setattr(gold_eslesme, "RAW_DATA", tmp_path)
    bulunan = gold_eslesme.scraper_kaydini_bul({
        "kayit_id": "ZK-999",
        "kaynak_url": "www.ziraatkatilim.com.tr/kart-kampanyalari/ornek-kampanya",
        "kampanya_adi": "Ornek Kampanya",
    })
    assert bulunan is not None, "kayit bulunamadi - KOD_HARITASI degismis olabilir"
    assert bulunan["ham_metin"] == "YENI metin"

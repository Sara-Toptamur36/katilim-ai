"""Altin Veri Seti kayitlarini scraper ciktisiyla eslestiren ortak mantik.

`tests/test_scraper_regresyon.py` ve `extraction_accuracy.py` (Sprint 3
Gun 4) tarafindan paylasilir - eslestirme kurallari TEK yerde tutulur.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

RAW_DATA = Path(__file__).resolve().parent.parent / "raw_data"

# kayit_id onekinden scraper klasor koduna (rehber Bolum 13.3/Tablo 6)
#
# TOM birden fazla klasore denk gelir: "tombank" T.O.M. Katilim'in kendi
# sitesi, "tombankhadi" ise ayni bankanin Hadi mikrositesi
# (hadiyanindakibanka.com, 22 Agustos 2026'da bankalar.json'a eklendi).
# Ikisi de kayit_id'de "TOM-" onekini paylasir (banka-duzeyi ayni "ad"
# altinda toplanmak icin bilerek boyle kuruldu) - bu yuzden TEK klasore
# bakmak, Hadi kaynakli TOM- kayitlarini sessizce "kaynaksiz" gosterirdi.
KOD_HARITASI = {
    "KT": "kuveytturk",
    "AL": "albaraka",
    "VK": "vakifkatilim",
    "ZK": "ziraatkatilim",
    "TF": "turkiyefinans",
    "TEK": "emlakkatilim",
    "DK": "dunyakatilim",
    "HF": "hayatfinans",
    "TOM": ("tombank", "tombankhadi"),
}

# T.O.M. gibi "tek sayfada coklu kampanya" bankalarinda (Bolum 13.3) her
# kampanyanin sentetik URL'si AYNI liste sayfasini paylasir - slug'a gore
# tek bir aday bulunamaz, hepsi eslesir. Bu kodlar icin kampanya_adi'nin
# ayirt edici kelimesiyle disambiguate edilir.
TEK_SAYFALI_KODLAR = {"tombank"}


def karsilastirma_bicimi(metin: str) -> str:
    """Kampanya kimligi karsilastirmalari icin ortak bicim.

    KESME ISARETI IKI TARAFTA DA AYNI OLMALI. Olculdu: altin kayitta
    "BAUHAUS'ta" (duz kesme) yaziyor, banka sayfasinda
    "BAUHAUS'ta" (kivrik kesme, U+2019) geciyor. Eski surum
    kesmeyi yalnizca kelimenin UCLARINDAN temizliyordu; Turkcede ek
    kesmeyle baglandigi icin isaret kelimenin ORTASINDA kaliyor ve
    karsilastirma sessizce basarisiz oluyordu - kampanya sayfada
    dururken "sayfa degismis" hatasi veriliyordu.

    Buyuk I notu: Python'un str.lower()'i Turkce noktali
    buyuk I harfini duz i degil, gorunmez birlesik nokta karakteriyle
    kucultur (İ.lower() -> i + U+0307 combining dot). NFD normalizasyonu
    ile combining karakterleri ayrilir ve temizlenir.
    
    DENETIM BULGUSU (24 Agustos 2026): Gold dataset'te "Istikbalde"
    (Latin I), ham metinde "İstikbal" (Turkce İ). Lower sonrasi "i" vs
    "i̇" uyusmazligi NFD + combining char filtresiyle cozulur.
    """
    # NFD normalizasyonu: combining karakterleri ayir
    metin = unicodedata.normalize("NFD", metin)
    # Combining karakterleri (Mn category) kaldir
    metin = "".join(c for c in metin if unicodedata.category(c) != "Mn")
    
    return (metin.replace("’", "'")
            .replace("‘", "'")
            .replace(".", "")  # Kisaltmalardaki noktalar (E.C.A. -> eca)
            .replace("İ", "i").lower())


def ilk_kelime(metin: str) -> str:
    """Karsilastirma icin normallestirilmis ilk kelime.

    NOT: Python'un str.lower()'i Turkce noktali buyuk 'I' harfini ('İ')
    duz 'i' degil, gorunmez bir birlesik nokta karakteriyle kucultur
    ('İ'.lower() -> 'i' + U+0307) - bu yuzden once manuel degistirilir.
    Ayni duzeltme terminology/genisletme.py'de de var (o modul Yagmur'un
    alani, oradan import edilmiyor)."""
    return karsilastirma_bicimi(metin.split()[0]).strip(".,!?")


def _en_yeni(kayitlar: list[dict]) -> dict:
    """Ayni sayfanin birden fazla anlik goruntusunden en gunceli."""
    return max(kayitlar, key=lambda a: a.get("erisim_zamani") or "")


def scraper_kaydini_bul(altin_kayit: dict) -> dict | None:
    """Altin kayittaki kaynak_url'nin son slug parcasina gore, scraper'in
    urettigi json kaydini bulur. Bulamazsa None doner (kampanya artik
    sitede olmayabilir - dogal rotasyon, bkz. tests/test_scraper_regresyon.py
    docstring'i).

    TEK_SAYFALI_KODLAR icin: slug TUM kayitlarda ayni oldugundan, adaylar
    arasindan kampanya_adi'nin ayirt edici ilk kelimesiyle secim yapilir.
    """
    kod = KOD_HARITASI.get(altin_kayit["kayit_id"].split("-")[0])
    if kod is None:
        return None
    kodlar = (kod,) if isinstance(kod, str) else kod

    slug = altin_kayit["kaynak_url"].rstrip("/").split("/")[-1]
    if not slug:
        return None

    adaylar = []
    for tek_kod in kodlar:
        json_klasor = RAW_DATA / tek_kod / "json"
        if not json_klasor.exists():
            continue
        for dosya in json_klasor.glob("*.json"):
            with open(dosya, encoding="utf-8") as f:
                aday = json.load(f)
            if slug in aday.get("url", ""):
                adaylar.append(aday)

    if not adaylar:
        return None

    # EN YENI ANLIK GORUNTU. Eskiden `adaylar[0]` donuyordu - yani glob'un
    # dosya sistemi sirasi, pratikte EN ESKI dosya. Bu, kod tabaninda ayni
    # soruya iki farkli cevap birakiyordu: etiketleme araclari
    # (gold_dataset/sprint_is_listesi._ham_kampanyalar) EN YENI anlik
    # goruntuyu okur, dogrulama testi ise EN ESKISINI.
    #
    # Sonuc sessiz ve tehlikeliydi: tazelenmis bir sayfadan yazilan kanit
    # spani, testin baktigi ESKI metinde bulunamayip "span kirik" hatasi
    # verirdi - oysa span dogruydu, test yanlis metne bakiyordu.
    #
    # Bir sayfanin anlik goruntusu sorusunun TEK cevabi olmali: en yenisi.
    # Eski dosyalar diskte kalir (kampanya_tarihcesi.py onlara dayanir).
    #
    # `kodlar` tuple olabilir (TOM gibi birden fazla klasore denk gelen
    # kodlar icin) - TEK_SAYFALI_KODLAR kontrolu bu yuzden `kod` yerine
    # kume kesisimiyle yapilir.
    if not (set(kodlar) & TEK_SAYFALI_KODLAR) or len(adaylar) == 1:
        return _en_yeni(adaylar)

    # DENETIM BULGUSU (9 Agustos 2026): Eskiden hedef kelime adayin TUM
    # govde metninde araniyordu - bu, "ozel" gibi yaygin bir kelimenin
    # BASKA bir kampanyanin govdesinde TESADUFEN gecmesi durumunda yanlis
    # eslesme uretiyordu. Somut ornek: TOM-002'nin ("Ozel Okul Odemelerinde
    # 10 Taksit") hedef kelimesi "ozel"; Restoran kampanyasinin govdesinde
    # "Hadi Ozel Bankaciligi" ifadesi gectigi icin (ilgisiz bir segment
    # adi), eslestirme YANLISLIKLA Restoran kaydini donduruyordu - dogru
    # aday ("Ozel Okul Odemelerinde...") diskte mevcut olmasina ragmen.
    # Duzeltme: hedef kelime, adayin TUM govdesinde degil yalnizca kendi
    # BASLIGININ (ilk satirinin) ilk kelimesiyle karsilastirilir - ayni
    # `ilk_kelime()` fonksiyonu simetrik olarak iki tarafa da uygulanir.
    hedef_kelime = ilk_kelime(altin_kayit["kampanya_adi"])
    eslesenler = [
        aday for aday in adaylar
        if ilk_kelime(aday["ham_metin"].split("\n", 1)[0]) == hedef_kelime
    ]
    # Basligi tutan adaylar arasindan yine EN YENISI secilir.
    return _en_yeni(eslesenler) if eslesenler else None

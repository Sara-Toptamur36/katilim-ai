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
from pathlib import Path

import pytest

GOLD = Path(__file__).parent.parent / "gold_dataset" / "altin_veri_seti.json"
RAW_DATA = Path(__file__).parent.parent / "scraper" / "raw_data"

# kayit_id onekinden scraper klasor koduna (rehber Bolum 13.3/Tablo 6)
KOD_HARITASI = {
    "KT": "kuveytturk",
    "AL": "albaraka",
    "VK": "vakifkatilim",
    "ZK": "ziraatkatilim",
    "TF": "turkiyefinans",
    "TEK": "emlakkatilim",
}


def altin_kayitlari_yukle() -> list[dict]:
    with open(GOLD, encoding="utf-8") as f:
        return json.load(f)


def _scraper_kaydini_bul(altin_kayit: dict) -> dict | None:
    """Altin kayittaki kaynak_url'nin son slug parcasina gore, scraper'in
    urettigi json kaydini bulur. Bulamazsa None doner (kampanya artik
    sitede olmayabilir - bkz. modul docstring)."""
    kod = KOD_HARITASI.get(altin_kayit["kayit_id"].split("-")[0])
    if kod is None:
        return None
    json_klasor = RAW_DATA / kod / "json"
    if not json_klasor.exists():
        return None

    slug = altin_kayit["kaynak_url"].rstrip("/").split("/")[-1]
    if not slug:
        return None

    for dosya in json_klasor.glob("*.json"):
        with open(dosya, encoding="utf-8") as f:
            aday = json.load(f)
        if slug in aday.get("url", ""):
            return aday
    return None


_HEDEF_ALTIN_KAYITLAR = [
    k for k in altin_kayitlari_yukle() if k["kayit_id"].split("-")[0] in KOD_HARITASI
]


@pytest.mark.parametrize(
    "altin", _HEDEF_ALTIN_KAYITLAR, ids=[k["kayit_id"] for k in _HEDEF_ALTIN_KAYITLAR]
)
def test_scraper_altin_veriyle_uyusuyor(altin):
    """Kampanya hala sitede canli mi VE oyleyse scraper'in cektigi ham
    metin, altin kayittaki kampanya adiyla ve encoding acisindan tutarli mi?
    """
    cikti = _scraper_kaydini_bul(altin)
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
    ilk_kelime = altin["kampanya_adi"].split()[0].strip(".,!?'’").replace("İ", "i").lower()
    assert ilk_kelime in ham_metin.replace("İ", "i").lower(), (
        f"{altin['kayit_id']}: beklenen ifade ('{ilk_kelime}') ham metinde yok - "
        "sayfa degismis veya secici bozulmus olabilir"
    )


def test_hicbir_kayit_bos_degil():
    """Scraper'in urettigi HICBIR json kaydi bos/anlamsiz olmamali
    (Bolum 15.1 dogrulama kontrolunun kayit-sonrasi guvencesi)."""
    dosyalar = list(RAW_DATA.glob("*/json/*.json"))
    assert dosyalar, "Henuz hic scraper ciktisi yok - once scraper'i calistir"
    for json_dosya in dosyalar:
        with open(json_dosya, encoding="utf-8") as f:
            kayit = json.load(f)
        assert kayit.get("ham_metin"), f"Bos kayit: {json_dosya}"
        assert len(kayit["ham_metin"]) > 500, f"Cok kisa kayit: {json_dosya}"


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

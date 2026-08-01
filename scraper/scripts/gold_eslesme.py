"""Altin Veri Seti kayitlarini scraper ciktisiyla eslestiren ortak mantik.

`tests/test_scraper_regresyon.py` ve `extraction_accuracy.py` (Sprint 3
Gun 4) tarafindan paylasilir - eslestirme kurallari TEK yerde tutulur.
"""

from __future__ import annotations

import json
from pathlib import Path

RAW_DATA = Path(__file__).resolve().parent.parent / "raw_data"

# kayit_id onekinden scraper klasor koduna (rehber Bolum 13.3/Tablo 6)
KOD_HARITASI = {
    "KT": "kuveytturk",
    "AL": "albaraka",
    "VK": "vakifkatilim",
    "ZK": "ziraatkatilim",
    "TF": "turkiyefinans",
    "TEK": "emlakkatilim",
    "DK": "dunyakatilim",
    "HF": "hayatfinans",
    "TOM": "tombank",
}

# T.O.M. gibi "tek sayfada coklu kampanya" bankalarinda (Bolum 13.3) her
# kampanyanin sentetik URL'si AYNI liste sayfasini paylasir - slug'a gore
# tek bir aday bulunamaz, hepsi eslesir. Bu kodlar icin kampanya_adi'nin
# ayirt edici kelimesiyle disambiguate edilir.
TEK_SAYFALI_KODLAR = {"tombank"}


def ilk_kelime(metin: str) -> str:
    """Karsilastirma icin normallestirilmis ilk kelime.

    NOT: Python'un str.lower()'i Turkce noktali buyuk 'I' harfini ('İ')
    duz 'i' degil, gorunmez bir birlesik nokta karakteriyle kucultur
    ('İ'.lower() -> 'i' + U+0307) - bu yuzden once manuel degistirilir.
    Ayni duzeltme terminology/genisletme.py'de de var (o modul Yagmur'un
    alani, oradan import edilmiyor)."""
    return metin.split()[0].strip(".,!?'’").replace("İ", "i").lower()


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
    json_klasor = RAW_DATA / kod / "json"
    if not json_klasor.exists():
        return None

    slug = altin_kayit["kaynak_url"].rstrip("/").split("/")[-1]
    if not slug:
        return None

    adaylar = []
    for dosya in json_klasor.glob("*.json"):
        with open(dosya, encoding="utf-8") as f:
            aday = json.load(f)
        if slug in aday.get("url", ""):
            adaylar.append(aday)

    if not adaylar:
        return None
    if kod not in TEK_SAYFALI_KODLAR or len(adaylar) == 1:
        return adaylar[0]

    hedef_kelime = ilk_kelime(altin_kayit["kampanya_adi"])
    for aday in adaylar:
        if hedef_kelime in aday["ham_metin"].replace("İ", "i").lower():
            return aday
    return None

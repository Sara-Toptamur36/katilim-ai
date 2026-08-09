"""Kampanyalar tablosundaki bos finansal alanlari regex motoruyla doldurur.

scraper/scripts/postgrese_yukle.py'nin ikinci adimi: o script yalnizca
kaynak/izlenebilirlik alanlarini yazip finansal alanlari NULL birakiyordu
(bkz. o dosyanin HENUZ_CIKARILMAMIS_ALANLAR listesi). Bu script, ayni
scraper/raw_data/*/json/*.json ham metinlerini extraction/regex_extractor.py
ile isleyip SADECE HALA NULL olan alanlari doldurur.

IDEMPOTENT VE GUVENLI GUNCELLEME: Bir alan zaten dolu ise (manuel duzeltme,
NER/LLM katmani veya onceki bir regex calistirmasi ile) UZERINE YAZILMAZ -
her alan tek tek kontrol edilir. Boylece Yagmur'un ileride ekleyecegi
NER/LLM katmani veya elle yapilan duzeltmeler bu script tekrar
calistirildiginda SILINMEZ.

Kullanim:
    python -m extraction.regex_ile_zenginlestir
"""

import json
from pathlib import Path

from api.db import OturumYerel
from api.models import Kampanya
from extraction.regex_extractor import genel_guven_hesapla, kaydi_cikar

RAW_DATA_KOK = Path(__file__).resolve().parent.parent / "scraper" / "raw_data"

# CampaignRecord alan adi -> Kampanya ORM kolon adi ayni, dogrudan setattr edilir.
CIKARILABILEN_ALANLAR = [
    "kar_payi_orani_percent",
    "kar_payi_orani_decimal",
    "vade_ay",
    "taksit_sayisi",
    "erteleme_suresi_ay",
    "finansman_tutari",
    "odul_miktari",
    "odul_birimi",
    "masraf_durumu",
    "tahsis_ucreti",
    "kampanya_avantaji",
    "kampanya_baslangic",
    "kampanya_bitis",
    "kampanya_turu",
    "hedef_kitle",
]


def _ham_metinleri_url_ile_esle() -> dict[str, str]:
    """kaynak_url -> ham_metin sozlugu. postgrese_yukle.py'deki
    _json_kayitlarini_bul ile ayni tarama mantigi."""
    esleme = {}
    for dosya in RAW_DATA_KOK.glob("*/json/*.json"):
        try:
            with open(dosya, encoding="utf-8") as f:
                kayit = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        url = kayit.get("url")
        metin = kayit.get("ham_metin") or kayit.get("normalize_metin")
        if url and metin:
            esleme[url] = metin
    return esleme


def zenginlestir() -> dict:
    """Donen ozet: {"guncellendi": N, "atlandi": M, "ham_metin_yok": K}."""
    ozet = {"guncellendi": 0, "atlandi": 0, "ham_metin_yok": 0}
    url_metin = _ham_metinleri_url_ile_esle()
    oturum = OturumYerel()

    try:
        satirlar = oturum.query(Kampanya).all()
        for satir in satirlar:
            ham_metin = url_metin.get(satir.kaynak_url)
            if not ham_metin:
                ozet["ham_metin_yok"] += 1
                continue

            cikan = kaydi_cikar(ham_metin)
            izler = cikan.pop("_izler")

            alan_belirtilmemis = dict(satir.alan_belirtilmemis or {})
            degisti = False

            for alan in CIKARILABILEN_ALANLAR:
                mevcut_deger = getattr(satir, alan, None)
                yeni_deger = cikan.get(alan)
                if mevcut_deger is None and yeni_deger is not None:
                    setattr(satir, alan, yeni_deger)
                    alan_belirtilmemis[alan] = False
                    degisti = True

            if degisti:
                satir.alan_belirtilmemis = alan_belirtilmemis
                satir.confidence = genel_guven_hesapla(izler)
                satir.cikarim_yontemi = "regex"
                ozet["guncellendi"] += 1
            else:
                ozet["atlandi"] += 1

        oturum.commit()
    finally:
        oturum.close()

    return ozet


if __name__ == "__main__":
    sonuc = zenginlestir()
    print(
        f"Zenginlestirildi: {sonuc['guncellendi']} guncellendi, "
        f"{sonuc['atlandi']} zaten doluydu/degismedi, "
        f"{sonuc['ham_metin_yok']} icin ham metin bulunamadi"
    )

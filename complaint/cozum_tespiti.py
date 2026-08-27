"""Sikayetin COZUM DURUMU tespiti - api/models.py::Sikayet.cozum_durumu
kolonunu dolduran kural tabanli katman.

NEDEN SIMDIYE KADAR HICBIR SEY DOLDURMUYORDU: api/models.py'deki kolon
yorumu "cozum sureci gercek destek/CRM akisina baglanana kadar (Faz 2)
DAIMA None'dir" diyordu - CRM entegrasyonu (bilet acildi mi, kapandi mi)
gercekten yok ve olmayacak (Faz 1). AMA sikayetin KENDI METNI cogu zaman
cozum durumunu ZATEN SOYLUYOR: "hala cozulmedi", "sonunda iade edildi"
gibi ifadeler CRM'e degil, musterinin kendi cumlesine aittir. Bu modul
CRM entegrasyonu DEGIL, metnin kendi kendini raporlamasidir - iki farkli
bilgi kaynagi.

--------------------------------------------------------------------------
DORT DEGER, VARSAYILAN "COZULMEDI" DEGIL
--------------------------------------------------------------------------
    cozuldu     - musteri cozumu ACIKCA bildiriyor
    kismen      - kismi cozum ACIKCA bildiriliyor
    cozulmedi   - musteri cozulmedigini/yanit alamadigini ACIKCA bildiriyor
    bilinmiyor  - VARSAYILAN. Cogu sikayet metni yalnizca SORUNU anlatir,
                  cozum surecinin nerede oldugunu SOYLEMEZ - bu durumda
                  "cozulmedi" DEMEK bir iddia UYDURMAK olurdu (sikayetin
                  yazildigi an itibariyle surec hala isliyor olabilir).

Kirmizi cizgi tema_siniflandirici.py ve kampanya_eslestirme.py ile AYNI:
kanit yoksa en olumsuz degil, "bilinmiyor" uretilir.
"""

from __future__ import annotations

from extraction.normalizer import turkce_ascii_kucult

COZULDU = "cozuldu"
KISMEN = "kismen"
COZULMEDI = "cozulmedi"
BILINMIYOR = "bilinmiyor"

# Sira ONEMLI: "kismen cozuldu" gibi ifadeler hem KISMEN hem COZULDU
# desenine uyabilir - KISMEN once kontrol edilir, daha spesifik olan
# kazanir (regex_extractor.py'deki "baglam eslesmeli desen once" ilkesiyle
# ayni sira mantigi).
_KISMEN_IFADELERI = ["kismen cozuldu", "bir kismi odendi", "yarisi odendi", "kismi iade"]
_COZULDU_IFADELERI = [
    "sonunda cozuldu", "cozume kavustu", "iade edildi", "geri odendi",
    "sorun giderildi", "duzeltildi ve",
]
_COZULMEDI_IFADELERI = [
    "hala cozulmedi", "cozulmedi", "hicbir cevap alamadim",
    "yanit veren olmadi", "hala yanit yok", "cozum saglanamadi",
]


def cozum_durumu_belirle(temiz_metin: str) -> dict:
    """Metnin kendi ifadesinden cozum durumunu tespit eder.

    Donen sozluk: {"cozum_durumu": str, "gerekce": dict}.
    """
    katlanmis = turkce_ascii_kucult(temiz_metin or "")

    for ifade in _KISMEN_IFADELERI:
        if ifade in katlanmis:
            return {"cozum_durumu": KISMEN, "gerekce": {"eslesen_ifade": ifade}}

    for ifade in _COZULDU_IFADELERI:
        if ifade in katlanmis:
            return {"cozum_durumu": COZULDU, "gerekce": {"eslesen_ifade": ifade}}

    for ifade in _COZULMEDI_IFADELERI:
        if ifade in katlanmis:
            return {"cozum_durumu": COZULMEDI, "gerekce": {"eslesen_ifade": ifade}}

    return {
        "cozum_durumu": BILINMIYOR,
        "gerekce": {"sebep": "metin_cozum_surecini_belirtmiyor"},
    }

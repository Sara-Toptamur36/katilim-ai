"""Turkce metin normalizasyonu.

Zeynep Veri Toplama Rehberi, Sprint 1 Gun 5. Scraper'in cektigi ham metni,
Yagmur'un cikarim katmanina vermeden once temel bir temizlikten gecirir.

KRITIK SINIR: Bu fonksiyon yalnizca bosluk/gorunmez karakter temizligi yapar.
Sayilari, yuzdeleri ve tarihleri DEGISTIRMEZ - "%1,89" -> "%1.89" gibi bir
donusum burada YAPILMAZ; bu, Yagmur'un cikarim katmaninin isidir (orada
percent/decimal olarak ikili saklanir, bkz. api/schemas.py CampaignRecord).
"""

import re
import unicodedata


def metni_normalize_et(metin: str) -> str:
    """Ham sayfa metnini, cikarim icin temizler.

    - NFKC normalizasyonu: gorunmez/kirik unicode karakterleri (ornegin
      birlesik aksan karakterleri) standart bilesik forma cevirir.
    - Coklu bosluk/sekme -> tek bosluk.
    - Ucten fazla ust uste bos satir -> iki bos satir.
    - Bas/son bosluklari kirpar.

    DIKKAT: Sayilari ve oranlari BOZMAZ - yalnizca bosluk/gorunmez
    karakter temizligi yapar.
    """
    metin = unicodedata.normalize("NFKC", metin)
    metin = re.sub(r"[ \t]+", " ", metin)
    metin = re.sub(r"\n{3,}", "\n\n", metin)
    return metin.strip()

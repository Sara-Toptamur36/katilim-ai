"""Sayisal/tarih normalizasyonu - yalnizca cikarim katmani icin.

preprocessing/normalizer.py (Zeynep) yalnizca bosluk/gorunmez karakter
temizligi yapar ve KASITLI OLARAK sayilari degistirmez (kendi dosyasindaki
uyariya bakin). Sayi/yuzde/tarih donusumu BURADA, cikarim asamasinda
yapilir - boylece "%1,89" -> 0.0189 gibi donusumler yalnizca gercekten
bir kar payi oranini temsil ettigi DOGRULANDIKTAN sonra gerceklesir.
"""

import re


def turkce_kucult(metin: str) -> str:
    """Python'un standart str.lower()'i Turkce noktali buyuk 'İ' harfini
    duz 'i' degil, gorunmez bir birlesik nokta karakteriyle kucultur
    (ornek: 'İ'.lower() -> 'i' + U+0307) - bu da "İndirim" gibi kelimelerin
    "indirim" ile essiz sekilde eslesmesini sessizce bozar. Ayni duzeltme
    terminology/genisletme.py'de de var (bagimsiz olarak, iki ekip
    tarafindan bulundu - bu, hatanin gercekten yaygin oldugunu dogrular).

    Duz ASCII 'I' harfine bilerek dokunulmuyor - o hem 'I' hem 'ı'
    anlamina gelebilir (belirsiz), yanlis donusum yeni uyusmazlik yaratir.
    """
    return metin.replace("İ", "i").lower()


def yuzdeye_cevir(ham: str) -> float | None:
    """'%2,05' / '% 2.05' / '2.05 %' -> 0.0205 (ondalik oran).

    Turkce ondalik ayiraci (virgul) desteklenir; yuzde isareti metnin
    herhangi bir tarafinda olabilir.
    """
    m = re.search(r"%?\s*([\d]{1,3}(?:[.,]\d+)?)\s*%?", ham)
    if not m:
        return None
    sayi = m.group(1).replace(",", ".")
    try:
        return round(float(sayi) / 100.0, 6)
    except ValueError:
        return None


def tutara_cevir(ham: str) -> float | None:
    """'500 TL' / '500₺' / '50.000 TL' -> 500.0 / 50000.0.

    Turkce binlik ayiraci (nokta) ve ondalik ayiraci (virgul) dikkate alinir.
    """
    m = re.search(r"([\d]{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?)", ham)
    if not m:
        return None
    sayi = m.group(1)
    if "," in sayi:
        sayi = sayi.replace(".", "").replace(",", ".")
    else:
        sayi = sayi.replace(".", "")
    try:
        return float(sayi)
    except ValueError:
        return None


_TR_AYLAR = {
    "ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "mayis": 5,
    "haziran": 6, "temmuz": 7, "ağustos": 8, "agustos": 8, "eylül": 9, "eylul": 9,
    "ekim": 10, "kasım": 11, "kasim": 11, "aralık": 12, "aralik": 12,
}


def tarihe_cevir(ham: str) -> str | None:
    """'31.12.2026' / '31/12/2026' / '31 Aralık 2026' -> '2026-12-31' (ISO8601)."""
    ham = ham.strip().lower()

    m = re.match(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", ham)
    if m:
        g, a, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{y:04d}-{a:02d}-{g:02d}"

    m = re.match(r"(\d{1,2})\s+([a-zçğıöşü]+)\s+(\d{4})", ham)
    if m:
        g, ay_adi, y = int(m.group(1)), m.group(2), int(m.group(3))
        ay = _TR_AYLAR.get(ay_adi)
        if ay:
            return f"{y:04d}-{ay:02d}-{g:02d}"

    return None


def aya_cevir(ham: str) -> int | None:
    """'120 ay' / '120 aya kadar' / '10 yıl' -> 120 (ay cinsinden int)."""
    ham = ham.lower()
    m = re.search(r"(\d+)\s*ay", ham)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*y[ıi]l", ham)
    if m:
        return int(m.group(1)) * 12
    return None

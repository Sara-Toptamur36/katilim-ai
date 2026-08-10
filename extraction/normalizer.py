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


# Kelime bazli buyukluk ekleri. GERCEK VERI: T.O.M. Katilim sayfalarinda
# tutarlar binlik ayirac yerine kelimeyle yaziliyor - "250 Bin TL ye kadar"
# ("250.000 TL" DEGIL). Bu bicim taninmadigi surece tutar hic bulunamiyordu
# (olculdu: TOM-002'de finansman_tutari None donuyordu).
# validation/verifier.py ayni bulguyu TERS yonde kullanir: bildigi sayinin
# "250 bin" varyantini uretip metinde arar.
_BUYUKLUK_EKLERI = {"bin": 1_000, "milyon": 1_000_000, "milyar": 1_000_000_000}

_TUTAR_DESENI = re.compile(
    r"([\d]{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?)\s*(bin|milyon|milyar)?",
    re.IGNORECASE,
)


def tutara_cevir(ham: str) -> float | None:
    """'500 TL' / '500₺' / '50.000 TL' / '250 Bin TL' -> 500.0 / 50000.0 / 250000.0.

    Turkce binlik ayiraci (nokta) ve ondalik ayiraci (virgul) dikkate alinir;
    kelime bazli buyukluk eki (bin/milyon/milyar) varsa carpan uygulanir.
    """
    m = _TUTAR_DESENI.search(ham)
    if not m:
        return None
    sayi = m.group(1)
    if "," in sayi:
        sayi = sayi.replace(".", "").replace(",", ".")
    else:
        sayi = sayi.replace(".", "")
    try:
        deger = float(sayi)
    except ValueError:
        return None

    ek = (m.group(2) or "").lower()
    return deger * _BUYUKLUK_EKLERI.get(ek, 1)


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

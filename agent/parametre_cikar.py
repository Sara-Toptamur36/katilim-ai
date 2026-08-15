"""Kullanici sorusundan Hesap Makinesi / Karsilastirma araclari icin
parametre cikarimi.

ONEMLI SINIR: Bu modul, KISA ve YAPILANDIRILMIŞ kullanici sorularindan
(ornek: "500.000 TL, %1,99 oranla 24 ay vadeyle taksitim ne kadar olur?")
sayisal parametre cikarir. Bu, Yagmur'un UZUN banka kampanya sayfalarindan
finansal alan cikaran extraction katmanindan (extraction/) FARKLI bir
sorumluluktur - burasi Ajan Orkestratorun kendi arac-cagirma (tool-calling)
katmanidir, kampanya metni islemez.
"""

import re


def _tutari_sayiya_cevir(ham: str) -> float | None:
    """'500.000' / '500000' / '1.500.000,50' -> float.

    TUTAR yaziminda Turkce kural gecerlidir: nokta BINLIK ayiraç, virgul
    ONDALIK ayiraç. (Oran icin bu kural GECERSIZDIR - bkz.
    _orani_sayiya_cevir.)
    """
    ham = ham.strip()
    if "," in ham:
        ham = ham.replace(".", "").replace(",", ".")
    else:
        ham = ham.replace(".", "")
    try:
        return float(ham)
    except ValueError:
        return None


def _orani_sayiya_cevir(ham: str) -> float | None:
    """'1,99' / '1.99' / '2' -> float.

    ORANDA BINLIK AYIRAC OLMAZ - hem virgul hem nokta ONDALIK ayiracidir.
    Bu ayrim bir hatadan dogdu: oran da tutarla ayni cevirimden geciyordu
    ve '%2.79' ifadesindeki nokta binlik ayiraci sanilip siliniyordu ->
    279.0. Hesaplanan taksit yuz kat siserken sistem yine 'basarili'
    diyordu (sessiz yanlis cevap).
    """
    try:
        return float(ham.strip().replace(",", "."))
    except ValueError:
        return None


# Iki alternatif BILEREK ayri: once binlik-ayiracli tam yazim ('1.250.000'),
# sonra ayiracsiz duz sayi ('500000').
#
# Cevreleyen (?<![\d.,]) ve (?!\d) sinir kontrolleri hatanin can alici
# noktasiydi: eski desen anchorsuz oldugu ve '(?:\.\d{3})*' sifir tekrara
# izin verdigi icin '1234 TL' metninde 1. indeksten baslayip '234'u
# yakaliyordu. Sonuc 1234 degil 234 olarak hesaplaniyor, arac yine
# basarili donuyordu. Sinir kontrolleri, sayinin ORTASINDAN eslesme
# baslamasini imkansiz kilar.
_TUTAR_DESENI = re.compile(
    r"(?<![\d.,])"
    r"(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)"
    r"(?!\d)"
    r"\s*(?:TL|₺|Türk Lirası)",
    re.IGNORECASE,
)

# "%1,99" kadar "yuzde 2,79" da kabul edilir - kullanicilar yuzde isaretini
# her zaman yazmaz (gercek /chat denemesinde bulundu).
_ORAN_DESENI = re.compile(r"(?:%|y[üu]zde\b)\s*(\d{1,2}(?:[.,]\d+)?)", re.IGNORECASE)

_VADE_AY_DESENI = re.compile(r"(\d{1,3})\s*ay\b", re.IGNORECASE)
_VADE_YIL_DESENI = re.compile(r"(\d{1,2})\s*y[ıi]l\b", re.IGNORECASE)


def hesaplama_parametrelerini_cikar(soru: str) -> dict:
    """Soru metninden anapara/aylik_oran_percent/vade_ay cikarmaya calisir.

    Herhangi bir alan bulunamazsa None kalir - uydurma deger URETILMEZ
    (rapor Bolum 5.7/15 ile ayni seffaflik ilkesi). Cagiran taraf (Tool
    Router), eksik alan varsa kullanicidan ek bilgi istemelidir.
    """
    anapara = None
    m = _TUTAR_DESENI.search(soru)
    if m:
        anapara = _tutari_sayiya_cevir(m.group(1))

    aylik_oran_percent = None
    m = _ORAN_DESENI.search(soru)
    if m:
        aylik_oran_percent = _orani_sayiya_cevir(m.group(1))

    vade_ay = None
    m = _VADE_AY_DESENI.search(soru)
    if m:
        vade_ay = int(m.group(1))
    else:
        m = _VADE_YIL_DESENI.search(soru)
        if m:
            vade_ay = int(m.group(1)) * 12

    return {
        "anapara": anapara,
        "aylik_oran_percent": aylik_oran_percent,
        "vade_ay": vade_ay,
    }


def eksik_parametreler(parametreler: dict) -> list[str]:
    """Hesaplama icin zorunlu olup bulunamayan alanlarin listesini doner."""
    return [alan for alan in ("anapara", "aylik_oran_percent", "vade_ay") if parametreler.get(alan) is None]

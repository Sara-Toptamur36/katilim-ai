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


def _sayiya_cevir(ham: str) -> float | None:
    """'500.000' / '500000' / '1,99' -> float.

    Turkce format: nokta binlik ayiraç, virgul ondalik ayiraç.
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


_TUTAR_DESENI = re.compile(
    r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*(?:TL|₺|Türk Lirası)", re.IGNORECASE
)
_ORAN_DESENI = re.compile(r"%\s*(\d{1,2}(?:[.,]\d+)?)")
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
        anapara = _sayiya_cevir(m.group(1))

    aylik_oran_percent = None
    m = _ORAN_DESENI.search(soru)
    if m:
        aylik_oran_percent = _sayiya_cevir(m.group(1))

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

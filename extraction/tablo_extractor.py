"""HTML tablolarindan (scraper/scripts/tablo_isle.py) kâr payi orani
disclosure tablolarini secer - Rehber Bolum 18.

NEDEN TEK SAYIYA INDIRGENMEZ (bilerek): bankalar bu tabloyu VADE ve/veya
FINANSMAN TUTARI dilimine gore degisen birden fazla oranla yayinliyor
(gercek veride dogrulandi - bkz. docs/extraction_accuracy_raporu.md
"Guncelleme - 20 Agustos 2026"). Ayni sayfada BIRDEN FAZLA tablo da
olabiliyor (ör. Turkiye Finans'ta "sigortali" ve "sigortasiz" icin ayri
iki tablo, farkli oranlarla). Hangi satirin/tablonun "asil" kampanya
orani oldugunu otomatik secmek UYDURMA deger uretmek olurdu (rapor
Bolum 5.7/15 ilkesi) - bu yuzden bu modul TEK bir kar_payi_orani sayisi
URETMEZ, yalnizca oran tablosu GORUNEN tablolari oldugu gibi (satir/sutun
yapisi korunarak) secip dondurur. Kararı insana (dashboard/Juri Audit
Paneli) birakir.
"""

from __future__ import annotations

from extraction.normalizer import turkce_ascii_kucult

_GORUNMEZ_KARAKTERLER = str.maketrans("", "", "​﻿")


def _baslik_normalize_et(baslik: str) -> str:
    """Sutun basligini karsilastirma icin sadelestirir - bankalarin bazi
    sayfalarinda sutun adlari zero-width space (\\u200b) ile bolunmus
    geliyor (ör. '​Va​de'), bu da düz 'vade in' testini
    sessizce bozar."""
    temiz = baslik.translate(_GORUNMEZ_KARAKTERLER).replace("\xa0", " ")
    return turkce_ascii_kucult(temiz).strip()


def _oran_tablosu_mu(sutunlar: list[str]) -> bool:
    normlar = [_baslik_normalize_et(s) for s in sutunlar]
    vade_var = any("vade" in n for n in normlar)
    oran_var = any("kar" in n and "oran" in n for n in normlar)
    return vade_var and oran_var


def _basligi_temizle(baslik: str) -> str:
    """Gorunmez karakterleri temizler ama METNI DEGISTIRMEZ (dashboard'da
    okunabilir gorunmesi icin - degerler asla degistirilmez)."""
    return baslik.translate(_GORUNMEZ_KARAKTERLER).replace("\xa0", " ").strip()


def oran_tablolarini_sec(tablolar: list[dict] | None) -> list[dict] | None:
    """`tablolar` (tablo_isle.tablolari_json_yap ciktisi) icinden VADE ve
    KAR PAYI ORANI sutunu barindiran tablolari secer, digerlerini
    (ödül/referans/liste tablolari vb.) eler.

    Secilen tablolarin sutun basliklari gorunmez karakterlerden temizlenir,
    SATIR DEGERLERI OLDUGU GIBI KORUNUR. Hicbir tablo eslesmezse None doner
    (ne "bulunamadi" hatasi, ne uydurma deger - basitce yok)."""
    if not tablolar:
        return None

    secilenler = []
    for tablo in tablolar:
        sutunlar = tablo.get("sutunlar") or []
        if not _oran_tablosu_mu(sutunlar):
            continue
        secilenler.append(
            {
                "tablo_index": tablo.get("tablo_index"),
                "sutunlar": [_basligi_temizle(s) for s in sutunlar],
                "satirlar": [
                    {_basligi_temizle(k): v for k, v in satir.items()}
                    for satir in tablo.get("satirlar", [])
                ],
            }
        )

    return secilenler or None

"""Bir kampanyanin zaman icindeki degisim tarihcesini cikarir.

NEDEN MUMKUN: scraper delta kontrolu (ortak.py::icerik_degisti_mi)
yalnizca icerik GERCEKTEN degistiginde yeni bir dosya yazar - ayni URL
icin birden fazla tarihli JSON dosyasi varsa, bu, sitenin o kampanyayi
o tarihler arasinda GERCEKTEN guncelledigi anlamina gelir (rastgele bir
yeniden-tarama artefakti degil). Bu modul o dosyalari gruplayip zaman
sirali bir "tarihce" cikarir - EK VERI TOPLAMA GEREKTIRMEZ, yalnizca
zaten scraper/raw_data'da duran dosyalari okur.

OLCUM (11 Agustos 2026): 230 benzersiz URL'den 33'unde icerik gercekten
degismis (birden fazla farkli icerik_hash). Ornek: Dunya Katilim'in
'avantajli-kurlar' kampanyasinin bitis tarihi 2026-07-30'dan 2026-08-06'ya
degismis - kampanya suresi uzatilmis.

NEDEN HIBRIT DEGIL REGEX KULLANILIYOR: Tarihce cok sayida gecmis
kayit uzerinde calisir; hibrit cikarim (NER+LLM) kayit basina saniyeler
surebilir (bkz. extraction/llm_extractor.py). Regex deterministik ve
hizlidir (<10ms/kayit) - trend icin "yaklasik dogru ama hizli" yeterlidir,
regex_ile_zenginlestir.py zaten veritabanindaki NIHAI degerler icin
hibrit kullaniyor.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from extraction.regex_extractor import kaydi_cikar

RAW_DATA_KOK = Path(__file__).resolve().parent.parent / "raw_data"

# Tarihce acisindan anlamli sayilan alanlar - kaydi_cikar()'in tum
# ciktisi degil, yalnizca kullanicinin "degisti mi" diye merak edecegi
# finansal/yasam dongusu alanlari (ör. "_izler" gibi ic alanlar haric).
_TAKIP_EDILEN_ALANLAR = [
    "kar_payi_orani_percent",
    "vade_ay",
    "finansman_tutari",
    "taksit_sayisi",
    "erteleme_suresi_ay",
    "odul_miktari",
    "odul_birimi",
    "kampanya_baslangic",
    "kampanya_bitis",
]


def _tum_kayitlari_url_ile_grupla() -> dict[str, list[dict]]:
    """scraper/raw_data altindaki TUM json kayitlarini kaynak URL'ye
    gore gruplar. Ayni URL'nin birden fazla tarihli kaydi varsa, bu
    kampanyanin zaman icinde degistigi anlamina gelir."""
    gruplar: dict[str, list[dict]] = defaultdict(list)
    for dosya in RAW_DATA_KOK.glob("*/json/*.json"):
        try:
            with open(dosya, encoding="utf-8") as f:
                kayit = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        url = kayit.get("url")
        if url:
            gruplar[url].append(kayit)
    return gruplar


def tarihce_getir(url: str) -> list[dict]:
    """Bir kampanya URL'sinin TUM tarihli kayitlarindaki takip edilen
    alan degerlerini, en eskiden en yeniye siralanmis olarak dondurur.

    Donen liste bos ise, bu URL icin hic kayit yok. Tek elemanli liste,
    kampanyanin (henuz) hic degismedigi anlamina gelir - bu bir hata
    degildir, coklu-tarihli olmasi zaten istisnadir (bkz. modul
    docstring'i: 230 URL'den yalnizca 33'u degisti)."""
    gruplar = _tum_kayitlari_url_ile_grupla()
    kayitlar = gruplar.get(url, [])

    tarihce = []
    for kayit in sorted(kayitlar, key=lambda k: k.get("erisim_zamani", "")):
        cikan = kaydi_cikar(kayit.get("ham_metin", ""))
        tarihce.append(
            {
                "tarih": (kayit.get("erisim_zamani") or "")[:10],
                "icerik_hash": kayit.get("icerik_hash"),
                "alanlar": {alan: cikan.get(alan) for alan in _TAKIP_EDILEN_ALANLAR},
            }
        )
    return tarihce


def degisen_alanlari_bul(tarihce: list[dict]) -> dict[str, dict]:
    """Tarihcenin ILK ve SON kaydi arasinda GERCEKTEN degeri degisen
    alanlari doner: {"kampanya_bitis": {"eski": "2026-07-30", "yeni":
    "2026-08-06"}}. Degismeyen alanlar (ör. sadece kozmetik bir metin
    duzeltmesi yuzunden hash degismis ama sayisal alanlar ayniysa)
    listelenmez - kullaniciya yalniz GERCEK degisiklikler gosterilir."""
    if len(tarihce) < 2:
        return {}

    ilk, son = tarihce[0]["alanlar"], tarihce[-1]["alanlar"]
    degisenler = {}
    for alan in _TAKIP_EDILEN_ALANLAR:
        eski, yeni = ilk.get(alan), son.get(alan)
        if eski != yeni:
            degisenler[alan] = {"eski": eski, "yeni": yeni}
    return degisenler

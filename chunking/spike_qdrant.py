"""Qdrant + embedding uctan uca dogrulama (spike).

AMAC (PeacewAI Ilerleme Plani, Sprint 2): "en az 1 bankanin metniyle ilk
vektor kaydi denenir, donanim/RAM sorunlari Sprint 3'u beklemeden erken
yakalanir". Bu bir RISK AZALTMA adimidir - RAG'in kendisi degildir.

BU SCRIPT NE YAPAR:
  gercek banka metni -> kaba parcalama -> embedding -> Qdrant'a yazma
  -> gercek Turkce sorguyla arama -> her adimin suresini raporlama

BU SCRIPT NE YAPMAZ:
  Semantik chunking (DOM basligi/tablo satiri farkindaligi), metadata
  semasi, reranking, retrieval kalite metrikleri. Buradaki parcalama
  BILEREK en kaba haliyle (paragraf) birakildi - gercek chunking
  stratejisi NLP tarafinin (Yagmur) tasarim karari, bu spike onun yerine
  karar vermez.

Kullanim:
    docker compose up -d qdrant
    python -m chunking.spike_qdrant
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from chunking.embedding import (
    VEKTOR_BOYUTU,
    belgeleri_vektore_cevir,
    sorguyu_vektore_cevir,
)
from chunking.qdrant_baglanti import (
    QDRANT_URL,
    ara,
    koleksiyon_hazirla,
    koleksiyon_sayisi,
    parcalari_ekle,
    qdrant_hazir_mi,
)

RAW_DATA = Path(__file__).resolve().parent.parent / "scraper" / "raw_data"
SPIKE_KOLEKSIYONU = "spike_kampanya_parcalari"

MIN_PARCA_UZUNLUGU = 80  # cok kisa satirlar (menu/baglanti) indekslenmesin


def kaba_parcala(metin: str) -> list[str]:
    """Metni satir/paragraf bazinda kabaca boler.

    KASITLI OLARAK BASIT: bu bir spike'tir (bkz. modul docstring'i).
    Gercek semantik chunking ayri bir tasarim isidir.
    """
    parcalar = [p.strip() for p in metin.split("\n")]
    return [p for p in parcalar if len(p) >= MIN_PARCA_UZUNLUGU]


def ornek_kayitlari_yukle(azami_kayit: int = 8) -> list[dict]:
    """Farkli bankalardan gercek kampanya kaydi okur.

    ONEMLI - ORNEKLEM SECIMI: Ilk yazimda her banka klasorunden ALFABETIK
    ILK dosya aliniyordu; bu, ornekleme tamamen kart/duyuru sayfalarini
    doldurdu ve iceride "kar payi" hic gecmedi - sonuc olarak finansman
    sorusu ANLAMSIZ bir teste donustu. Simdi finansman/kar payi iceren
    kayitlara oncelik verilir, boylece arama gercekten olculebilir olur.
    """
    ilgili_anahtar_kelimeler = ("kâr pay", "kar pay", "finansman", "vade")

    ilgili: list[dict] = []
    diger: list[dict] = []
    for dosya in sorted(RAW_DATA.glob("*/json/*.json")):
        with open(dosya, encoding="utf-8") as f:
            kayit = json.load(f)
        metin = (kayit.get("ham_metin") or "").strip()
        if not metin:
            continue
        metin_kucuk = metin.lower()
        hedef = ilgili if any(k in metin_kucuk for k in ilgili_anahtar_kelimeler) else diger
        hedef.append(kayit)

    # Once ilgili kayitlar, yetmezse digerleriyle tamamla
    return (ilgili + diger)[:azami_kayit]


def calistir() -> dict:
    """Spike'i calistirir, olcum ozetini doner."""
    if not qdrant_hazir_mi():
        raise RuntimeError(
            f"Qdrant'a erisilemiyor ({QDRANT_URL}). "
            "Once calistirin: docker compose up -d qdrant"
        )

    kayitlar = ornek_kayitlari_yukle()
    if not kayitlar:
        raise RuntimeError("scraper/raw_data altinda islenecek kayit bulunamadi")

    # --- 1) Parcalama ---
    t0 = time.monotonic()
    parcalar: list[str] = []
    ustveriler: list[dict] = []
    for kayit in kayitlar:
        for parca in kaba_parcala(kayit["ham_metin"]):
            parcalar.append(parca)
            # Provenance (rapor Bolum 9): parca hangi belgeden geldi?
            ustveriler.append(
                {
                    "banka": kayit.get("banka"),
                    "kaynak_url": kayit.get("url"),
                    "erisim_zamani": kayit.get("erisim_zamani"),
                    "metin": parca,
                }
            )
    parcalama_sn = time.monotonic() - t0

    # --- 2) Embedding ---
    t1 = time.monotonic()
    vektorler = belgeleri_vektore_cevir(parcalar)
    embedding_sn = time.monotonic() - t1

    # --- 3) Qdrant'a yazma ---
    t2 = time.monotonic()
    koleksiyon_hazirla(SPIKE_KOLEKSIYONU, vektor_boyutu=VEKTOR_BOYUTU, sifirla=True)
    yazilan = parcalari_ekle(vektorler, ustveriler, koleksiyon=SPIKE_KOLEKSIYONU)
    yazma_sn = time.monotonic() - t2

    # --- 4) Iki farkli sorgu tipiyle arama ---
    # ALAKALI sorgu: cevabi indekslenen veride VAR.
    # ALAKASIZ sorgu: cevabi kesinlikle YOK - skorlarin bu durumda ne kadar
    # dustugunu olcmek icin. Iki sorgunun skorlari birbirine yakin cikarsa,
    # ham benzerlik skoruna bakip "kaynak buldum" demek YANLIS POZITIF
    # uretir; RAG'e mutlaka bir esik/abstention kurali gerekir (rapor
    # Bolum 5.7/15 - bilmedigini bilmek).
    sorgular = {
        "alakali": "Kâr payı oranı ve vade seçenekleri nedir?",
        "alakasiz": "Uzay istasyonunda yerçekimi nasıl ölçülür?",
    }

    t3 = time.monotonic()
    arama_sonuclari = {
        etiket: ara(sorguyu_vektore_cevir(s), limit=3, koleksiyon=SPIKE_KOLEKSIYONU)
        for etiket, s in sorgular.items()
    }
    arama_sn = time.monotonic() - t3

    en_iyi_alakali = arama_sonuclari["alakali"][0]["skor"] if arama_sonuclari["alakali"] else 0.0
    en_iyi_alakasiz = arama_sonuclari["alakasiz"][0]["skor"] if arama_sonuclari["alakasiz"] else 0.0

    return {
        "kayit_sayisi": len(kayitlar),
        "parca_sayisi": len(parcalar),
        "yazilan": yazilan,
        "koleksiyondaki_kayit": koleksiyon_sayisi(SPIKE_KOLEKSIYONU),
        "sorgular": sorgular,
        "arama_sonuclari": arama_sonuclari,
        "skor_farki": round(en_iyi_alakali - en_iyi_alakasiz, 4),
        "sureler_sn": {
            "parcalama": round(parcalama_sn, 2),
            "embedding": round(embedding_sn, 2),
            "qdrant_yazma": round(yazma_sn, 2),
            "arama": round(arama_sn, 3),
        },
    }


if __name__ == "__main__":
    sonuc = calistir()

    print("=== Qdrant + embedding spike ===")
    print(f"Islenen kayit   : {sonuc['kayit_sayisi']} (farkli bankalardan)")
    print(f"Uretilen parca  : {sonuc['parca_sayisi']}")
    print(f"Qdrant'a yazilan: {sonuc['yazilan']} (koleksiyonda: {sonuc['koleksiyondaki_kayit']})")
    print()
    print("Sureler (saniye):")
    for adim, sure in sonuc["sureler_sn"].items():
        print(f"  {adim:<14}: {sure}")
    for etiket, sorgu in sonuc["sorgular"].items():
        print()
        print(f"--- {etiket.upper()} sorgu: {sorgu}")
        for i, s in enumerate(sonuc["arama_sonuclari"][etiket], 1):
            u = s["ustveri"]
            print(f"  {i}. skor={s['skor']:.4f} | {u.get('banka')}")
            print(f"     {(u.get('metin') or '')[:120]}...")

    print()
    print(f"Alakali/alakasiz en iyi skor farki: {sonuc['skor_farki']}")
    if sonuc["skor_farki"] < 0.05:
        print(
            "  UYARI: Fark cok kucuk. Ham benzerlik skoruna bakarak 'kaynak\n"
            "  buldum' demek YANLIS POZITIF uretir - RAG'e esik/abstention\n"
            "  kurali ve/veya reranker gerekir."
        )

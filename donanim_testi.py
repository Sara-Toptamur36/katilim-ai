"""Donanim tanilama ve hiz testi - baska bir makinede calistirilip paylasilir.

AMAC: Ayni depo farkli makinelerde COK farkli hizlarda calisiyor (olculdu:
LLM cikarimi CPU-agirlikli bir makinede tek cagri ~355 sn). Hangi makinenin
neyi ne kadar surede yaptigini bilmeden dogru ayar secilemez ve juri demosu
icin hangi makinenin kullanilacagina saglikli karar verilemez.

Bu script:
  1. Donanimi ve secilen profili yazar
  2. Servislerin (Qdrant / Ollama / PostgreSQL) durumunu kontrol eder
  3. Embedding ve LLM hizini GERCEK veriyle olcer
  4. Ciktisi oldugu gibi paylasilabilir

Kullanim:
    python donanim_testi.py              # tam test
    python donanim_testi.py --hizli      # LLM testini atla (uzun surer)
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

RAW_DATA = Path(__file__).resolve().parent / "scraper" / "raw_data"


def _baslik(metin: str) -> None:
    print(f"\n{'=' * 62}\n{metin}\n{'=' * 62}")


def _ornek_metin() -> str:
    """Gercek bir banka kampanya metni (ortalama uzunlukta)."""
    for dosya in sorted(RAW_DATA.glob("*/json/*.json")):
        with open(dosya, encoding="utf-8") as f:
            kayit = json.load(f)
        metin = (kayit.get("ham_metin") or "").strip()
        if 800 < len(metin) < 3000:
            return metin
    return (
        "Yeni musterilerimize ozel yuzde 1,89 kar payi orani ile 100.000 TL'ye "
        "kadar 120 aya varan konut finansmani firsati! Kampanya 31 Aralik 2026 "
        "tarihine kadar gecerlidir."
    )


def servisleri_kontrol_et() -> None:
    _baslik("2) SERVISLER")

    try:
        from chunking.qdrant_baglanti import (
            VARSAYILAN_KOLEKSIYON,
            koleksiyon_sayisi,
            qdrant_hazir_mi,
        )

        if qdrant_hazir_mi():
            try:
                sayi = koleksiyon_sayisi(VARSAYILAN_KOLEKSIYON)
            except Exception:
                sayi = None
            print(f"  Qdrant      : CALISIYOR (indekste {sayi if sayi is not None else 0} parca)")
        else:
            print("  Qdrant      : KAPALI  -> docker compose up -d qdrant")
    except Exception as e:  # noqa: BLE001
        print(f"  Qdrant      : kontrol edilemedi ({type(e).__name__})")

    try:
        from extraction.llm_extractor import _ollama_hazir_mi

        print(f"  Ollama      : {'CALISIYOR' if _ollama_hazir_mi() else 'KAPALI  -> ollama serve'}")
    except Exception as e:  # noqa: BLE001
        print(f"  Ollama      : kontrol edilemedi ({type(e).__name__})")

    try:
        from api.db import engine

        with engine.connect():
            print("  PostgreSQL  : CALISIYOR")
    except Exception:
        print("  PostgreSQL  : KAPALI  -> docker compose up -d postgres")


def embedding_hizi_olc() -> None:
    _baslik("3) EMBEDDING HIZI")
    try:
        from chunking.embedding import belgeleri_vektore_cevir
    except Exception as e:  # noqa: BLE001
        print(f"  atlandi: {type(e).__name__}: {e}")
        return

    metin = _ornek_metin()

    t0 = time.monotonic()
    belgeleri_vektore_cevir([metin[:500]])
    ilk = time.monotonic() - t0
    print(f"  ilk cagri (model yuklemesi dahil) : {ilk:6.1f} sn")

    yigin = [metin[i * 100 : i * 100 + 500] for i in range(20)]
    t1 = time.monotonic()
    belgeleri_vektore_cevir(yigin)
    toplu = time.monotonic() - t1
    print(f"  20 metin (toplu)                  : {toplu:6.1f} sn")
    print(f"  parca basina                      : {toplu / 20:6.2f} sn")

    # Tam indeksleme tahmini (mevcut veri ~734 parca)
    print(f"  ~734 parcalik tam indeksleme tahmini: {toplu / 20 * 734 / 60:.0f} dakika")


def llm_hizi_olc() -> None:
    _baslik("4) LLM HIZI (Ollama)")
    try:
        from extraction.llm_extractor import (
            _BAGLAM_PENCERESI,
            _MAKS_GIRDI_TOKEN,
            _ollama_hazir_mi,
            llm_ile_cikar,
            token_say,
        )
    except Exception as e:  # noqa: BLE001
        print(f"  atlandi: {type(e).__name__}: {e}")
        return

    if not _ollama_hazir_mi():
        print("  Ollama kapali - atlandi.")
        return

    metin = _ornek_metin()
    print(f"  test metni: {token_say(metin)} token "
          f"(baglam={_BAGLAM_PENCERESI}, girdi siniri={_MAKS_GIRDI_TOKEN})")
    print("  cagri yapiliyor... (bu makinede dakikalar surebilir)")

    t0 = time.monotonic()
    sonuc = llm_ile_cikar(
        metin,
        sadece_bu_alanlar={"kar_payi_orani_percent", "vade_ay", "finansman_tutari"},
    )
    sure = time.monotonic() - t0

    bulunan = {k: v for k, v in sonuc.items() if not k.startswith("_") and v is not None}
    print(f"  sure                              : {sure:6.1f} sn")
    print(f"  cikarilan alanlar                 : {bulunan or 'HICBIRI'}")
    if not bulunan:
        print("  UYARI: hicbir alan cikarilamadi - zaman asimi ya da baglam sorunu olabilir")


def profil_onerisi() -> None:
    _baslik("5) DEGERLENDIRME")
    from donanim import GUCLU_GPU_ASGARI_VRAM_MB, ayarlar, gpu_bilgisi

    gpu = gpu_bilgisi()
    a = ayarlar()

    if gpu and gpu[1] >= GUCLU_GPU_ASGARI_VRAM_MB:
        print(f"  Bu makine GUCLU profilde ({gpu[0]}, {gpu[1]} MB VRAM).")
        print("  Juri demosu icin uygun; tum belgeler kirpilmadan islenir.")
    elif gpu:
        print(f"  GPU var ({gpu[0]}) ama VRAM yetersiz: {gpu[1]} MB "
              f"< {GUCLU_GPU_ASGARI_VRAM_MB} MB")
        print("  7B model VRAM'e sigmadigi icin Ollama modeli agirlikli olarak")
        print("  CPU'da calistirir - LLM cikarimi dakikalar surer.")
        print("  Demo icin daha guclu bir makine onerilir.")
    else:
        print("  GPU bulunamadi - LLM cikarimi CPU'da calisir ve yavastir.")
        print("  Demo icin GPU'lu bir makine onerilir.")

    print(f"\n  Secilen profil: {a.ad}")
    print("  Profili elle zorlamak icin: KATILIMAI_PROFIL=gpu (veya cpu)")


def main() -> None:
    ayristirici = argparse.ArgumentParser(description="Donanim tanilama ve hiz testi")
    ayristirici.add_argument(
        "--hizli", action="store_true", help="LLM hiz testini atla (uzun surer)"
    )
    argumanlar = ayristirici.parse_args()

    from donanim import ozet

    _baslik("1) DONANIM")
    print(f"  Isletim sistemi : {platform.system()} {platform.release()}")
    print(f"  Python          : {sys.version.split()[0]}")
    print()
    print(ozet())

    servisleri_kontrol_et()
    embedding_hizi_olc()
    if argumanlar.hizli:
        _baslik("4) LLM HIZI (Ollama)")
        print("  --hizli verildi, atlandi.")
    else:
        llm_hizi_olc()
    profil_onerisi()

    print("\n" + "=" * 62)
    print("Bu ciktinin tamamini paylasabilirsiniz.")
    print("=" * 62)


if __name__ == "__main__":
    main()

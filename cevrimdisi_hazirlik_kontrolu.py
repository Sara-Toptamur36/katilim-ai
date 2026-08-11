"""Juri demosu icin cevrimdisi hazirlik kontrolu (E1).

AMAC: Sartname Md. 5.9 (on-premise) ve degerlendirme kriterlerindeki
"On-Prem Uygulanabilirlik" (%20) kalemi, sistemin internetsiz calisabilmesini
gerektirir. Ancak sistemin bazi parcalari ILK CALISMADA internetten indirilir
(Ollama modeli, HuggingFace embedding modeli, Docker imajlari) - bu indirme
BIR KERE yapilip yerel onbellege alindiktan sonra internet gerekmez, ama
kontrol edilmezse jüri ortaminda internet yoksa demo ilk adimda calisir
gibi gorunup ortasinda takilabilir.

Bu script MODEL/IMAJ INDIRMEZ - yalnizca "onceden indirilmis mi" diye
KONTROL EDER. Amac, demo gununden ONCE (internet varken) bir kez calistirip
hepsi YESIL cikana kadar eksikleri tamamlamak, sonra internet olmadan da
guvenle demo yapabilmek.

Kullanim:
    python cevrimdisi_hazirlik_kontrolu.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import requests

_GEREKLI_DOCKER_IMAJLARI = ("postgres:16", "qdrant/qdrant:v1.18.1", "ollama/ollama:0.32.5")
_GEREKLI_OLLAMA_MODELI = "qwen2.5:7b-instruct-q4_K_M"
_OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"


def _baslik(metin: str) -> None:
    print(f"\n{'=' * 62}\n{metin}\n{'=' * 62}")


def _sonuc(basarili: bool, etiket: str, detay: str = "") -> bool:
    isaret = "[OK]" if basarili else "[EKSIK]"
    print(f"  {isaret:8} {etiket}" + (f" - {detay}" if detay else ""))
    return basarili


def docker_imajlari_kontrol_et() -> bool:
    _baslik("1) DOCKER IMAJLARI (docker compose up -d icin gerekli)")

    if shutil.which("docker") is None:
        print("  [EKSIK]  docker komutu bulunamadi - Docker Desktop kurulu mu?")
        return False

    try:
        cikti = subprocess.run(
            ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
            capture_output=True, text=True, timeout=15, check=True,
        ).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
        print(f"  [EKSIK]  'docker images' calistirilamadi ({type(e).__name__}) - Docker Desktop acik mi?")
        return False

    yerel_imajlar = set(cikti.split())
    hepsi_tamam = True
    for imaj in _GEREKLI_DOCKER_IMAJLARI:
        varmi = imaj in yerel_imajlar
        hepsi_tamam &= _sonuc(varmi, imaj, "" if varmi else f"docker pull {imaj}")
    return hepsi_tamam


def ollama_modeli_kontrol_et() -> bool:
    _baslik("2) OLLAMA MODELI (hibrit cikarimin LLM katmani)")

    try:
        yanit = requests.get(_OLLAMA_TAGS_URL, timeout=3)
        yanit.raise_for_status()
        modeller = {m["name"] for m in yanit.json().get("models", [])}
    except requests.RequestException:
        print("  [EKSIK]  Ollama servisine ulasilamadi - 'docker compose up -d' calisiyor mu?")
        return False

    varmi = _GEREKLI_OLLAMA_MODELI in modeller
    return _sonuc(
        varmi, _GEREKLI_OLLAMA_MODELI,
        "" if varmi else f"ollama pull {_GEREKLI_OLLAMA_MODELI}",
    )


def embedding_modeli_onbellek_kontrol_et() -> bool:
    _baslik("3) EMBEDDING MODELI (RAG icin, HuggingFace onbellegi)")

    try:
        from chunking.embedding import MODEL_ADI
    except Exception as e:  # noqa: BLE001
        print(f"  [EKSIK]  chunking.embedding import edilemedi ({type(e).__name__})")
        return False

    onbellek_adi = "models--" + MODEL_ADI.replace("/", "--")
    onbellek_yolu = Path.home() / ".cache" / "huggingface" / "hub" / onbellek_adi
    varmi = onbellek_yolu.exists() and any(onbellek_yolu.rglob("*.safetensors"))
    return _sonuc(
        varmi, MODEL_ADI,
        "" if varmi else "internet acikken bir kez 'python -m chunking.indeksleyici' calistirin",
    )


def postgres_semasi_kontrol_et() -> bool:
    _baslik("4) POSTGRESQL SEMASI (alembic migration)")

    try:
        from sqlalchemy import text

        from api.db import engine

        with engine.connect() as baglanti:
            surum = baglanti.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception as e:  # noqa: BLE001
        print(f"  [EKSIK]  PostgreSQL'e baglanilamadi veya sema yok ({type(e).__name__})")
        print("           -> docker compose up -d postgres && alembic upgrade head")
        return False

    return _sonuc(surum is not None, f"alembic_version = {surum}")


def main() -> None:
    sonuclar = [
        docker_imajlari_kontrol_et(),
        ollama_modeli_kontrol_et(),
        embedding_modeli_onbellek_kontrol_et(),
        postgres_semasi_kontrol_et(),
    ]

    _baslik("SONUC")
    if all(sonuclar):
        print("  Tum bagimliliklar yerel onbellekte - internet KAPALIYKEN de demo calisir.")
    else:
        print("  Eksik kalemler var - yukaridaki komutlari INTERNET ACIKKEN calistirip")
        print("  bu script'i tekrar calistirin. Hepsi [OK] olana kadar demo gunu")
        print("  internetsiz ortamda calisacagi GARANTI DEGILDIR.")


if __name__ == "__main__":
    main()

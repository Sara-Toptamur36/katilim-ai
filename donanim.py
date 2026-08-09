"""Donanim profili: ayni depo, hem zayif hem guclu makinede en iyi ayarla calissin.

NEDEN GEREKLI: LLM cikarim suresi donanima gore 10 kattan fazla degisiyor
(olculdu: bu depoda CPU-agirlikli bir makinede tek cagri ~355 sn). Tek bir
sabit ayar iki makineye birden uymuyor:
  - Zayif makinede genis baglam penceresi -> zaman asimi, sessiz None
  - Guclu makinede dar baglam penceresi   -> bosuna kirpilan belgeler

Bu modul donanimi tespit edip uygun profili secer. Her deger ortam
degiskeniyle EZILEBILIR - otomatik tespit yalnizca makul bir varsayilan
saglar, son sozu kullanici soyler.

PROFIL SECIMI VRAM'E BAKAR, "GPU VAR MI"YA DEGIL:
Gercek bir ornek (bu depoda olculdu): makinede GeForce MX230 var ama
yalnizca 2 GB VRAM - 7B model (~5 GB) sigmiyor ve Ollama modeli %84
oraninda CPU'da calistiriyor. "GPU var" demek hizli demek degildir;
belirleyici olan modelin VRAM'e sigip sigmadigidir.

Kullanim:
    from donanim import ayarlar
    ayarlar().llm_baglam_penceresi

Tanilama:
    python -m donanim
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache

# 7B'lik bir modelin (q4 kuantize, ~5 GB) rahatca sigmasi icin gereken
# asgari VRAM. Altinda kalan GPU'lar modeli tam yukleyemez ve Ollama
# katmanlarin bir kismini CPU'ya tasir - bu durumda "gpu" profili
# yaniltici olur.
GUCLU_GPU_ASGARI_VRAM_MB = 8000


@dataclass(frozen=True)
class Profil:
    """Donanima gore secilen ayar kumesi."""

    ad: str
    # LLM (Ollama): Ollama, num_ctx verilmezse modeli 4096 ile servis eder
    # ve uzun promptu SESSIZCE kirpar - bu yuzden hep acikca gonderilir.
    llm_baglam_penceresi: int
    llm_zaman_asimi_sn: int
    # Embedding: toplu isleme, tek tek islemeye gore belirgin hizli
    embedding_yigin_boyutu: int
    aciklama: str


CPU_PROFILI = Profil(
    ad="cpu",
    llm_baglam_penceresi=4096,
    llm_zaman_asimi_sn=900,
    embedding_yigin_boyutu=32,
    aciklama=(
        "GPU yok ya da VRAM 7B modele yetmiyor. Baglam penceresi dar "
        "tutulur (genisletmek cikarimi zaman asimina sokuyor - olculdu), "
        "zaman asimi comert birakilir."
    ),
)

GPU_PROFILI = Profil(
    ad="gpu",
    llm_baglam_penceresi=16384,
    llm_zaman_asimi_sn=300,
    embedding_yigin_boyutu=128,
    aciklama=(
        "Model VRAM'e sigiyor. Genis baglam penceresi kullanilir - hicbir "
        "belge kirpilmaz; cikarim hizli oldugu icin zaman asimi kisaltilir."
    ),
)


@lru_cache(maxsize=1)
def gpu_bilgisi() -> tuple[str, int] | None:
    """(GPU adi, VRAM MB) doner; GPU yoksa None.

    `nvidia-smi` kullanilir - torch import etmek ~50 sn suruyor ve bu
    modul her ayar okumasinda cagrilabiliyor. nvidia-smi ~50 ms.
    """
    if not shutil.which("nvidia-smi"):
        return None
    try:
        cikti = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None

    if not cikti:
        return None
    ilk = cikti.splitlines()[0]
    try:
        ad, vram = ilk.rsplit(",", 1)
        return ad.strip(), int(vram.strip())
    except ValueError:
        return None


@lru_cache(maxsize=1)
def ayarlar() -> Profil:
    """Bu makine icin gecerli ayarlari doner (ortam degiskenleri uygulanmis)."""
    zorlanan = (os.environ.get("KATILIMAI_PROFIL") or "").strip().lower()
    if zorlanan == "gpu":
        secilen = GPU_PROFILI
    elif zorlanan == "cpu":
        secilen = CPU_PROFILI
    else:
        gpu = gpu_bilgisi()
        secilen = (
            GPU_PROFILI
            if gpu and gpu[1] >= GUCLU_GPU_ASGARI_VRAM_MB
            else CPU_PROFILI
        )

    # Tek tek ayarlar da ezilebilir (profilden bagimsiz)
    return Profil(
        ad=secilen.ad,
        llm_baglam_penceresi=int(
            os.environ.get("LLM_BAGLAM_PENCERESI", secilen.llm_baglam_penceresi)
        ),
        llm_zaman_asimi_sn=int(
            os.environ.get("LLM_ZAMAN_ASIMI", secilen.llm_zaman_asimi_sn)
        ),
        embedding_yigin_boyutu=int(
            os.environ.get("EMBEDDING_YIGIN_BOYUTU", secilen.embedding_yigin_boyutu)
        ),
        aciklama=secilen.aciklama,
    )


def ozet() -> str:
    """Tanilama ciktisi - baska bir makinede calistirilip paylasilabilir."""
    gpu = gpu_bilgisi()
    a = ayarlar()
    satirlar = [
        "=== KatilimAI donanim profili ===",
        f"GPU                  : {gpu[0]} ({gpu[1]} MB VRAM)" if gpu else "GPU                  : yok",
        f"CPU cekirdek         : {os.cpu_count()}",
        f"Secilen profil       : {a.ad}",
        f"  gerekce            : {a.aciklama}",
        "",
        f"LLM baglam penceresi : {a.llm_baglam_penceresi}",
        f"LLM zaman asimi      : {a.llm_zaman_asimi_sn} sn",
        f"Embedding yigin      : {a.embedding_yigin_boyutu}",
    ]
    if os.environ.get("KATILIMAI_PROFIL"):
        satirlar.append(f"\n(profil ortam degiskeniyle zorlandi: {os.environ['KATILIMAI_PROFIL']})")
    return "\n".join(satirlar)


if __name__ == "__main__":
    print(ozet())

"""Metinleri vektore ceviren embedding katmani (RAG icin ilk adim).

MODEL SECIMI - intfloat/multilingual-e5-base:
  - Cok dilli, Turkce destegi guclu; 768 boyutlu vektor uretir.
  - ~1.1 GB - bge-m3'e (~2.3 GB) gore juri demo makinesinde cok daha hafif.
  - Model adi ORTAM DEGISKENIYLE degistirilebilir (EMBEDDING_MODELI), boylece
    NLP tarafi (Yagmur) baska bir modele gecmek isterse kod degismez;
    yalnizca VEKTOR_BOYUTU'nun yeni modelle uyusmasi gerekir.

E5 MODELLERININ ONEK KURALI (kritik):
  e5 ailesi, egitim sirasinda her metnin basina bir gorev oneki almistir:
  aranan metin "query: ", indekslenen belge "passage: " ile baslar. Bu onek
  ATLANIRSA model calismaya devam eder ama benzerlik skorlari belirgin
  sekilde bozulur - sessiz bir kalite kaybidir. Bu yuzden onek burada
  ZORUNLU tutuldu: `belgeleri_vektore_cevir` ve `sorguyu_vektore_cevir`
  ayri fonksiyonlardir, cagiran tarafin oneki hatirlamasi gerekmez.

PERFORMANS (bu depoda olculdu, GPU'suz makine):
  ilk model yuklemesi ~12 sn (tek seferlik), 20 metnin toplu encode'u
  ~0.9 sn. Yani embedding, LLM cikarimindan (bkz. extraction/llm_extractor.py
  zaman asimi notu: 150-300+ sn) COK daha ucuzdur ve RAG icin darbogaz
  degildir.
"""

from __future__ import annotations

import os
from typing import Optional

MODEL_ADI = os.environ.get("EMBEDDING_MODELI", "intfloat/multilingual-e5-base")
VEKTOR_BOYUTU = int(os.environ.get("EMBEDDING_BOYUTU", "768"))

_model = None


def modeli_yukle():
    """Modeli ILK cagrida yukler (tembel yukleme).

    ner_extractor.py ile ayni gerekce: modul import edildigi anda ~1 GB'lik
    bir model yuklemek, embedding'e hic dokunmayan testleri/servisleri de
    yavaslatirdi.
    """
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_ADI)
    return _model


def _vektore_cevir(metinler: list[str], onek: str) -> list[list[float]]:
    model = modeli_yukle()
    onekli = [f"{onek}{m}" for m in metinler]
    vektorler = model.encode(onekli, normalize_embeddings=True)
    return [v.tolist() for v in vektorler]


def belgeleri_vektore_cevir(metinler: list[str]) -> list[list[float]]:
    """Indekslenecek belge parcalari icin ('passage: ' oneki)."""
    return _vektore_cevir(metinler, "passage: ")


def sorguyu_vektore_cevir(sorgu: str) -> list[float]:
    """Kullanici sorusu icin ('query: ' oneki)."""
    return _vektore_cevir([sorgu], "query: ")[0]


def model_hazir_mi() -> Optional[str]:
    """Model yuklenebiliyor mu? Yuklenebiliyorsa None, aksi halde hata
    metni doner (test/spike'larin anlamli sekilde atlanabilmesi icin -
    ornegin model hic indirilmemisse ve internet yoksa)."""
    try:
        modeli_yukle()
        return None
    except Exception as e:  # noqa: BLE001 - hata TURU degil, mesaji onemli
        return f"{type(e).__name__}: {e}"

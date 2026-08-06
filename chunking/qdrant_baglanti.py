"""Qdrant vektor veritabani erisim katmani.

api/db.py'nin (PostgreSQL) Qdrant karsiligi: baglanti kurulumu ve temel
islemler burada toplanir, cagiran taraf qdrant_client API'sini dogrudan
bilmek zorunda kalmaz.

KAPSAM NOTU: Bu dosya RAG'in TAMAMI DEGILDIR - yalnizca altyapi katmanidir
(baglan, koleksiyon ac, vektor yaz, ara). Semantik chunking stratejisi,
metadata semasi ve retrieval kalitesi NLP tarafinin (Yagmur) alanidir;
bu katman ona hazir bir zemin birakir, kararlarini onceden vermez.

ERISILEBILIRLIK: Qdrant kapaliyken cagrilar hata FIRLATMAK yerine
`qdrant_hazir_mi()` ile onceden kontrol edilebilir - extraction/
llm_extractor.py'deki Ollama kontrolüyle ayni desen (30 sn onbellekli),
cunku kapali bir servise baglanma denemesi Windows'ta anlik degil
saniyeler suruyor ve cok kayitli akislarda bu bedel katlanarak artiyor.
"""

from __future__ import annotations

import os
import time
from typing import Any, Optional

import requests

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
VARSAYILAN_KOLEKSIYON = os.environ.get("QDRANT_KOLEKSIYON", "kampanya_parcalari")

_istemci = None
_DURUM_CACHE: dict[str, Any] = {}
_DURUM_CACHE_SURESI_SN = 30.0


def qdrant_hazir_mi() -> bool:
    """Qdrant servisi ayakta mi? Sonuc 30 saniye onbellege alinir.

    Onbellek gerekcesi extraction/llm_extractor.py::_ollama_hazir_mi ile
    ayni: servis kapaliyken her cagrida ayri ayri baglanti-reddi beklemesi
    odenmesin.
    """
    simdi = time.monotonic()
    son = _DURUM_CACHE.get("zaman")
    if son is not None and (simdi - son) < _DURUM_CACHE_SURESI_SN:
        return bool(_DURUM_CACHE["hazir"])
    try:
        yanit = requests.get(f"{QDRANT_URL}/", timeout=2)
        hazir = yanit.status_code == 200
    except requests.RequestException:
        hazir = False
    _DURUM_CACHE["hazir"] = hazir
    _DURUM_CACHE["zaman"] = simdi
    return hazir


def istemci_al():
    """QdrantClient ornegini (tembel) olusturur."""
    global _istemci
    if _istemci is None:
        from qdrant_client import QdrantClient

        _istemci = QdrantClient(url=QDRANT_URL)
    return _istemci


def koleksiyon_hazirla(
    koleksiyon: str = VARSAYILAN_KOLEKSIYON,
    vektor_boyutu: int = 768,
    sifirla: bool = False,
) -> None:
    """Koleksiyonu olusturur (yoksa).

    `sifirla=True` verilirse ONCE SILER - yalnizca spike/test icin;
    gercek indeksleme akisinda veri kaybina yol acar, bu yuzden
    varsayilani False.
    """
    from qdrant_client.models import Distance, VectorParams

    istemci = istemci_al()
    if sifirla and istemci.collection_exists(koleksiyon):
        istemci.delete_collection(koleksiyon)

    if not istemci.collection_exists(koleksiyon):
        istemci.create_collection(
            collection_name=koleksiyon,
            # COSINE: embedding.py vektorleri normalize edilmis donduruyor
            # (normalize_embeddings=True), normalize vektorlerde kosinus
            # benzerligi dogru olcudur.
            vectors_config=VectorParams(size=vektor_boyutu, distance=Distance.COSINE),
        )


def parcalari_ekle(
    vektorler: list[list[float]],
    ustveriler: list[dict],
    koleksiyon: str = VARSAYILAN_KOLEKSIYON,
    baslangic_id: int = 0,
) -> int:
    """Vektorleri ustverileriyle birlikte yazar, yazilan kayit sayisini doner.

    `ustveriler` her parca icin kaynak bilgisini tasimali (banka, kaynak_url,
    metin vb.) - rapor Bolum 9 (provenance): bir cevabin hangi belgeden
    geldigi gosterilemiyorsa RAG'in degeri yoktur.
    """
    from qdrant_client.models import PointStruct

    if len(vektorler) != len(ustveriler):
        raise ValueError(
            f"vektor sayisi ({len(vektorler)}) ile ustveri sayisi "
            f"({len(ustveriler)}) eslesmiyor"
        )

    noktalar = [
        PointStruct(id=baslangic_id + i, vector=v, payload=u)
        for i, (v, u) in enumerate(zip(vektorler, ustveriler))
    ]
    istemci_al().upsert(collection_name=koleksiyon, points=noktalar)
    return len(noktalar)


def ara(
    sorgu_vektoru: list[float],
    limit: int = 5,
    koleksiyon: str = VARSAYILAN_KOLEKSIYON,
) -> list[dict]:
    """En benzer parcalari doner: [{"skor": float, "ustveri": {...}}, ...]"""
    sonuclar = istemci_al().query_points(
        collection_name=koleksiyon, query=sorgu_vektoru, limit=limit
    ).points
    return [{"skor": s.score, "ustveri": s.payload} for s in sonuclar]


def koleksiyon_sayisi(koleksiyon: str = VARSAYILAN_KOLEKSIYON) -> Optional[int]:
    """Koleksiyondaki kayit sayisi; koleksiyon yoksa None."""
    istemci = istemci_al()
    if not istemci.collection_exists(koleksiyon):
        return None
    return istemci.count(collection_name=koleksiyon).count

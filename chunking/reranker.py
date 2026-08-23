"""Reranker: Qdrant'tan donen genis aday listesini Cross-Encoder ile yeniden siralar.

Qdrant (veya genel vektor aramasi) Recall (getirilen adaylar arasinda dogru 
cevabin bulunma ihtimali) acisindan basarili olsa da, siralamada (Precision@1) 
bazen zayif kalabilir. Cross-Encoder modeli soruyu ve parcayi *birlikte* okuyup
skorlayarak siralamayi iyilestirir.
"""

from __future__ import annotations

import os
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

# Kucuk ve hizli bir reranker modeli (Turkce destegi de kismen iyi calisir)
RERANKER_MODEL = os.environ.get("KATILIMAI_RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")


@lru_cache(maxsize=1)
def _reranker_yukle():
    """Reranker modelini tembel (lazy) olarak yukler ve onbellege alir."""
    try:
        from sentence_transformers import CrossEncoder
        logger.info(f"Reranker modeli yukleniyor: {RERANKER_MODEL}")
        return CrossEncoder(RERANKER_MODEL, max_length=512)
    except ImportError:
        logger.warning("sentence_transformers paketi bulunamadi. Reranker calismayacak.")
        return None
    except Exception as e:
        logger.error(f"Reranker yuklenirken hata olustu: {e}")
        return None


def rerank(sorgu: str, parcalar: list[dict], top_k: int = 5) -> list[dict]:
    """Qdrant'tan donen parcalari Cross-Encoder ile yeniden siralar.
    
    Args:
        sorgu: Kullanicinin sordugu orijinal soru.
        parcalar: Qdrant'tan donen parcalar listesi (icinde 'ustveri' -> 'metin' olmali).
        top_k: En yuksek skorlu kac parcanin dondurulecegi.
        
    Returns:
        Yeniden siralanmis ve top_k ile sinirlandirilmis parca listesi.
        Eger model yuklenemezse orijinal parcalarin top_k'si doner.
    """
    if not parcalar:
        return []

    model = _reranker_yukle()
    if model is None:
        return parcalar[:top_k]

    girdiler = []
    for p in parcalar:
        metin = (p.get("ustveri") or {}).get("metin", "")
        girdiler.append((sorgu, metin))

    try:
        skorlar = model.predict(girdiler)
        
        # Orijinal parcalara rerank_score ekle
        for parca, skor in zip(parcalar, skorlar):
            parca["rerank_score"] = float(skor)
            
        # Skorlara gore buyukten kucuge sirala
        siralanmis = sorted(parcalar, key=lambda x: x.get("rerank_score", -999.0), reverse=True)
        return siralanmis[:top_k]
    except Exception as e:
        logger.error(f"Rerank islemi basarisiz oldu: {e}")
        return parcalar[:top_k]

"""Ajan Orkestratoru - tek giris noktasi.

Mimari (rapor Bolum 8): Intent Detection -> Tool Router -> (SQL/Calculator/
Dictionary/RAG/Fallback) -> Response Generator -> Terminology Check ->
Verifier -> Provenance.

SPRINT 3 KAPSAMI (bu dosya): Intent Detection + Tool Router + ilk uc arac
(Hesaplama, Sozluk, Karsilastirma). RAG (embedding/Qdrant) ve LLM tabanli
serbest metin uretimi Sprint 4'te eklenecek - o zamana kadar "bilgi" turu
serbest sorular FALLBACK'e duser, bu ACIKCA sebep alaninda belirtilir.

api/main.py, GERCEK_VERI_AKTIF bayragina gore uygun `kayit_getirici`
fonksiyonunu bu module verir - boylece bu dosya mock/DB ayrimindan
tamamen habersiz kalir (Sara'nin Sprint 2'de kurdugu ayrimla tutarli).
"""

import time
from typing import Callable

from agent.intent import Niyet, niyet_tespit_et
from agent.router import (
    hesaplama_aracini_cagir,
    karsilastirma_aracini_cagir,
    sozluk_aracini_cagir,
)

KayitGetirici = Callable[[str], list]


def soru_isle(soru: str, kayit_getirici: KayitGetirici) -> dict:
    """Bir kullanici sorusunu isler, cevap + Juri Audit Paneli icin
    gereken tum izlenebilirlik alanlarini doner (rapor Bolum 10.2).

    Donen sozluk: cevap, kaynaklar, confidence, fallback, audit_ekstra
    (intent, intent_confidence, cagrilan_arac, sebep, latency_ms).
    """
    baslangic = time.time()
    niyet, guven = niyet_tespit_et(soru)

    if niyet == Niyet.HESAPLAMA:
        sonuc = hesaplama_aracini_cagir(soru)
        arac = "calculator"
    elif niyet == Niyet.SOZLUK:
        sonuc = sozluk_aracini_cagir(soru)
        arac = "dictionary"
    elif niyet == Niyet.KARSILASTIRMA:
        sonuc = karsilastirma_aracini_cagir(soru, kayit_getirici)
        arac = "sql"
    else:
        sonuc = {
            "basarili": False,
            "cevap": (
                "Bu soruyu su an hangi araca yonlendirecegimi tespit edemedim. "
                "Hesaplama, sozluk veya banka karsilastirmasi ile ilgili "
                "bir soru sorabilir misiniz?"
            ),
            "sebep": "Niyet tespit edilemedi (anahtar kelime eslesmesi yok)",
        }
        arac = "fallback"

    latency_ms = int((time.time() - baslangic) * 1000)

    return {
        "cevap": sonuc["cevap"],
        "kaynaklar": [],  # RAG baglanmadan provenance uretilemez (Sprint 4)
        "confidence": 1.0 if sonuc.get("basarili") else 0.0,
        "fallback": not sonuc.get("basarili", False),
        "audit_ekstra": {
            "intent": niyet.value,
            "intent_confidence": guven,
            "cagrilan_arac": arac,
            "latency_ms": latency_ms,
            "sebep": sonuc.get("sebep"),
        },
    }

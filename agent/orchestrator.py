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
    rag_aracini_cagir,
    sozluk_aracini_cagir,
)

KayitGetirici = Callable[[str], list]


def soru_isle(soru: str, kayit_getirici: KayitGetirici, rag_araci=None) -> dict:
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
        # Belirli bir arac eslesmedi -> serbest bilgi sorusu olabilir:
        # kaynaklarda ara (RAG). Kaynak bulunamazsa rag_aracini_cagir
        # zaten basarili=False ve gerekce doner - cevap UYDURULMAZ.
        #
        # `rag_araci` enjekte edilebilir (kayit_getirici ile ayni desen):
        # yonlendirme mantigini test eden birim testleri, gercek embedding
        # modelini yuklemek zorunda kalmasin diye - olculdu: gercek RAG
        # ile bu testler 2 sn yerine 121 sn suruyordu.
        sonuc = (rag_araci or rag_aracini_cagir)(soru)
        niyet = Niyet.BILGI
        arac = "rag" if sonuc.get("basarili") else "fallback"

    latency_ms = int((time.time() - baslangic) * 1000)
    veri = sonuc.get("veri", {})

    # Kaynaklar YALNIZCA RAG'den gelir - hesaplama/sozluk/karsilastirma
    # araclari belge degil yapilandirilmis veri kullanir.
    kaynaklar = sonuc.get("kaynaklar", [])

    return {
        "cevap": sonuc["cevap"],
        "kaynaklar": kaynaklar,
        "confidence": 1.0 if sonuc.get("basarili") else 0.0,
        "fallback": not sonuc.get("basarili", False),
        "audit_ekstra": {
            "intent": niyet.value,
            "intent_confidence": guven,
            "cagrilan_arac": arac,
            "latency_ms": latency_ms,
            "sebep": sonuc.get("sebep"),
            # Yalnizca karsilastirma araci (gercek kampanya kayitlari
            # kullanir) doldurur; hesaplama/sozluk icin None kalir - bu
            # alanlarin o araclarda anlami yoktur (rapor Bolum 5.7/15).
            "extraction_confidence": veri.get("extraction_confidence"),
            "regex_basari_orani": veri.get("regex_basari_orani"),
            # Juri Audit Paneli'nin retriever bolumu (rapor Bolum 10.2):
            # hangi parcalar, hangi skorla getirildi?
            "retriever_sonuclari": [
                {
                    "chunk_id": k.get("kaynak_url") or "",
                    "similarity_score": k.get("similarity_score"),
                    "metin_ozeti": (k.get("metin") or "")[:200],
                }
                for k in kaynaklar
            ],
        },
    }

"""KatilimAI API - FastAPI uygulamasi.

SPRINT 1 DURUMU: Uc uc nokta mock veriyle calisir. Mock JWT dogrulamasi
ILK GUNDEN aktiftir; /chat yaniti audit blogunu ILK GUNDEN icerir (ici bos
olsa da), boylece Havin arayuzunu bekletmeden kurabilir.

Calistirma:
    uvicorn api.main:app --reload
Swagger:
    http://localhost:8000/docs
"""

import time

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api.auth import token_dogrula
from api.logging_config import log
from api.mock_data import id_ile_getir, kampanyalari_getir
from api.schemas import (
    AuditBilgisi,
    CampaignRecord,
    ChatIstek,
    ChatYanit,
    KarsilastirIstek,
    KarsilastirYanit,
)

app = FastAPI(
    title="KatilimAI API",
    description=(
        "Katilim bankaciligi kampanya metinlerinden bilgi cikarimi, "
        "karsilastirma ve kaynakli dogal dil yanitlari. "
        "TEKNOFEST 2026 Yapay Zeka Dil Ajanlari Yarismasi - PeacewAI"
    ),
    version="0.1.0",
)

# Havin'in React gelistirme sunucusu (Vite varsayilani 5173)
IZINLI_KAYNAKLAR = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=IZINLI_KAYNAKLAR,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_ADI = "qwen2.5:7b-instruct-q4_K_M"  # rapor Bolum 5.3
TEMPERATURE = 0.0  # rapor Bolum 8: tutarli/tekrarlanabilir cikti


def _bos_audit(**kwargs) -> AuditBilgisi:
    """Sprint 1'de tum audit alanlari bos doner ama YAPI hazirdir."""
    varsayilan = {
        "model": MODEL_ADI,
        "temperature": TEMPERATURE,
        "cache_hit": False,
    }
    varsayilan.update(kwargs)
    return AuditBilgisi(**varsayilan)


@app.get("/", tags=["Sistem"])
def kok():
    """Servis ayakta mi kontrolu (kimlik dogrulama gerektirmez)."""
    return {
        "servis": "KatilimAI API",
        "surum": app.version,
        "durum": "calisiyor",
        "sprint": 1,
        "not": "Uc uc nokta su an MOCK veri dondurmektedir.",
    }


@app.get("/saglik", tags=["Sistem"])
def saglik():
    """Health check - CI ve docker-compose icin."""
    return {"durum": "saglikli"}


@app.get("/kampanyalar", response_model=list[CampaignRecord], tags=["Kampanyalar"])
def kampanyalar(
    banka: str | None = Query(None, description="Banka adina gore filtrele"),
    kampanya_turu: str | None = Query(None, description="Kampanya turune gore filtrele"),
    kullanici: dict = Depends(token_dogrula),
):
    """Kampanya listesi (Sprint 1: mock veri).

    ONEMLI: Eksik alanlar GIZLENMEZ. None donen alanlar, `alan_belirtilmemis`
    sozlugunde True olarak isaretlenir (rapor Bolum 5.7/15 - seffaflik ilkesi).
    """
    log.info(
        "kampanyalar sorgusu | kullanici=%s | banka=%s | tur=%s",
        kullanici.get("kullanici"),
        banka,
        kampanya_turu,
    )
    return kampanyalari_getir(banka=banka, kampanya_turu=kampanya_turu)


@app.get("/kampanyalar/{kampanya_id}", response_model=CampaignRecord, tags=["Kampanyalar"])
def kampanya_detay(kampanya_id: int, kullanici: dict = Depends(token_dogrula)):
    kayit = id_ile_getir(kampanya_id)
    if kayit is None:
        raise HTTPException(status_code=404, detail="Kampanya bulunamadi")
    return kayit


@app.post("/karsilastir", response_model=KarsilastirYanit, tags=["Karsilastirma"])
def karsilastir(istek: KarsilastirIstek, kullanici: dict = Depends(token_dogrula)):
    """Kampanya karsilastirmasi (Sprint 1: mock).

    Sprint 2'de comparison/compare_engine.py devreye girecek:
      - Sabit, guvenli SQL sablonlari (serbest metinden SQL URETILMEZ)
      - NULLS LAST: eksik veri en sona gider, filtrelenip gizlenmez
    """
    baslangic = time.time()
    log.info(
        "karsilastir sorgusu | kullanici=%s | ids=%s | kriter=%s",
        kullanici.get("kullanici"),
        istek.ids,
        istek.kriter,
    )

    secilenler = [k for k in (id_ile_getir(i) for i in istek.ids) if k is not None]
    if len(secilenler) < 2:
        raise HTTPException(
            status_code=404, detail="Karsilastirma icin en az 2 gecerli kampanya gerekli"
        )

    # Sprint 1 mock siralamasi: None degerler EN SONA (NULLS LAST mantigi)
    def sirala_anahtari(k: CampaignRecord):
        deger = k.kar_payi_orani_percent
        return (deger is None, deger if deger is not None else 0)

    sirali = sorted(secilenler, key=sirala_anahtari)
    latency = int((time.time() - baslangic) * 1000)

    return KarsilastirYanit(
        kriter=istek.kriter,
        sonuclar=[k.model_dump(mode="json") for k in sirali],
        calistirilan_sql=None,  # Sprint 2'de gercek SQL buraya gelecek
        audit=_bos_audit(cagrilan_arac="mock_sql", latency_ms=latency),
    )


@app.post("/chat", response_model=ChatYanit, tags=["Chatbot"])
def chat(istek: ChatIstek, kullanici: dict = Depends(token_dogrula)):
    """Dogal dilde soru-cevap (Sprint 1: mock).

    Sprint 3'te agent/orchestrator.py devreye girecek:
      Intent Detection -> Tool Router -> (SQL|Calculator|Dictionary|RAG|Fallback)
      -> Response Generator -> Terminology Check -> Verifier -> Provenance

    NOT: audit blogu ILK GUNDEN doludur (degerler bos olsa da). Havin'in
    Juri Audit Paneli bu alan adlarina gore kurulur; sonradan isim
    degistirmek onun kodunu bozar.
    """
    baslangic = time.time()
    log.info("chat sorgusu | kullanici=%s", kullanici.get("kullanici"))

    latency = int((time.time() - baslangic) * 1000)

    return ChatYanit(
        cevap=(
            "Bu bir MOCK yanittir. Ajan orkestratoru Sprint 3'te devreye girecek. "
            "Su an yalnizca API sozlesmesi ve arayuz entegrasyonu test edilmektedir."
        ),
        kaynaklar=[],
        confidence=0.0,
        fallback=False,
        audit=_bos_audit(
            intent="mock",
            intent_confidence=0.0,
            cagrilan_arac="mock",
            extraction_confidence=0.0,
            response_confidence=0.0,
            latency_ms=latency,
            sebep="Sprint 1 - ajan orkestratoru henuz baglanmadi",
        ),
    )

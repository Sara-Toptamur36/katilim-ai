"""KatilimAI API - FastAPI uygulamasi.

SPRINT 1 DURUMU: Uc uc nokta mock veriyle calisir. Mock JWT dogrulamasi
ILK GUNDEN aktiftir; /chat yaniti audit blogunu ILK GUNDEN icerir (ici bos
olsa da), boylece Havin arayuzunu bekletmeden kurabilir.

GERCEK VERI GECISI: /kampanyalar ve /karsilastir, GERCEK_VERI_AKTIF ortam
degiskeni "true" oldugunda mock_data.py yerine PostgreSQL'i (api/db.py,
api/kampanya_repository.py) kullanir. Varsayilan DEGERI FALSE'tur - boylece
Havin'in sozlesme testleri (tests/test_api_sozlesme.py, sabit A/B/C/D Bankasi
degerlerine dayanir) ve mevcut gelistirme akisi bozulmaz. Zeynep'in
scraper/scripts/postgrese_yukle.py ile PostgreSQL'e veri yukledigi ve ekip
gercek veriyle calismaya hazir oldugunda bu bayrak "true" yapilir.

Calistirma:
    uvicorn api.main:app --reload
Swagger:
    http://localhost:8000/docs
"""

import os
import time

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api.auth import token_dogrula
from api.db import oturum_al
from api.kampanya_repository import id_ile_getir_db, kampanyalari_getir_db
from api.logging_config import log
from api.mock_data import id_ile_getir, kampanyalari_getir
from api.schemas import (
    AuditBilgisi,
    CampaignRecord,
    ChatIstek,
    ChatYanit,
    HesapIstek,
    HesapYanit,
    KarsilastirIstek,
    KarsilastirYanit,
    OdemeSatiriYanit,
)
from calculator.calculator import (
    HesapGirdiHatasi,
    aylik_taksit_hesapla,
    odeme_plani_uret,
)
from comparison.compare_engine import (
    BilinmeyenKriter,
    aciklama_uret,
    karsilastir_bellekte,
    karsilastir_sorgusu,
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

# Sprint 2'de "true" yapilacak (bkz. dosya basi aciklamasi).
GERCEK_VERI_AKTIF = os.environ.get("GERCEK_VERI_AKTIF", "false").lower() == "true"


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
    """Kampanya listesi (GERCEK_VERI_AKTIF=false iken mock, true iken PostgreSQL).

    ONEMLI: Eksik alanlar GIZLENMEZ. None donen alanlar, `alan_belirtilmemis`
    sozlugunde True olarak isaretlenir (rapor Bolum 5.7/15 - seffaflik ilkesi).
    """
    log.info(
        "kampanyalar sorgusu | kullanici=%s | banka=%s | tur=%s | kaynak=%s",
        kullanici.get("kullanici"),
        banka,
        kampanya_turu,
        "db" if GERCEK_VERI_AKTIF else "mock",
    )
    if GERCEK_VERI_AKTIF:
        oturum = next(oturum_al())
        try:
            return kampanyalari_getir_db(oturum, banka=banka, kampanya_turu=kampanya_turu)
        finally:
            oturum.close()
    return kampanyalari_getir(banka=banka, kampanya_turu=kampanya_turu)


@app.get("/kampanyalar/{kampanya_id}", response_model=CampaignRecord, tags=["Kampanyalar"])
def kampanya_detay(kampanya_id: int, kullanici: dict = Depends(token_dogrula)):
    if GERCEK_VERI_AKTIF:
        oturum = next(oturum_al())
        try:
            kayit = id_ile_getir_db(oturum, kampanya_id)
        finally:
            oturum.close()
    else:
        kayit = id_ile_getir(kampanya_id)
    if kayit is None:
        raise HTTPException(status_code=404, detail="Kampanya bulunamadi")
    return kayit


@app.post("/karsilastir", response_model=KarsilastirYanit, tags=["Karsilastirma"])
def karsilastir(istek: KarsilastirIstek, kullanici: dict = Depends(token_dogrula)):
    """Kampanya karsilastirmasi - comparison/compare_engine.py ile.

    - Kriter SABIT bir sozlukten secilir; serbest metinden SQL URETILMEZ
    - Eksik veri gizlenmez: NULLS LAST + eksik_alanlar isareti
    - Uretilen SQL, Juri Audit Paneli icin yanitla birlikte doner

    Sprint 1'de siralama bellekte yapilir; uretilen SQL sablonu, Sprint 2'de
    PostgreSQL'e gecildiginde AYNEN kullanilacaktir (cikti sekli degismez).
    """
    baslangic = time.time()
    log.info(
        "karsilastir sorgusu | kullanici=%s | ids=%s | kriter=%s",
        kullanici.get("kullanici"),
        istek.ids,
        istek.kriter,
    )

    if GERCEK_VERI_AKTIF:
        oturum = next(oturum_al())
        try:
            secilenler = [
                k for k in (id_ile_getir_db(oturum, i) for i in istek.ids) if k is not None
            ]
        finally:
            oturum.close()
    else:
        secilenler = [k for k in (id_ile_getir(i) for i in istek.ids) if k is not None]
    if len(secilenler) < 2:
        raise HTTPException(
            status_code=404, detail="Karsilastirma icin en az 2 gecerli kampanya gerekli"
        )

    try:
        sonuc = karsilastir_bellekte(secilenler, kriter=istek.kriter)
        # Sprint 2'de bu sorgu gercekten calistirilacak; simdiden uretip
        # audit panelinde gosteriyoruz (seffaflik)
        sql, _ = karsilastir_sorgusu(istek.kriter)
    except BilinmeyenKriter as e:
        log.warning("Gecersiz kriter istendi: %s", istek.kriter)
        raise HTTPException(status_code=422, detail=str(e))

    latency = int((time.time() - baslangic) * 1000)

    return KarsilastirYanit(
        kriter=istek.kriter,
        sonuclar=sonuc["sonuclar"],
        calistirilan_sql=sql,
        audit=_bos_audit(
            cagrilan_arac="sql",
            latency_ms=latency,
            sql_sorgusu=sql,
            sebep=aciklama_uret(sonuc),
        ),
    )


@app.post("/hesapla", response_model=HesapYanit, tags=["Hesaplama"])
def hesapla(istek: HesapIstek, kullanici: dict = Depends(token_dogrula)):
    """Taksit/kar payi hesabi - Calculator Tool.

    TASARIM ILKESI (rapor Bolum 8): Hesap LLM'e BIRAKILMAZ. Bu uc nokta
    saf Python fonksiyonlarini cagirir; LLM yalnizca sonucu cumleye doker.

    Sprint 3'te Ajan Orkestratoru, "hesaplama" niyeti tespit ettiginde
    dogrudan bu mantigi cagiracak.
    """
    baslangic = time.time()
    log.info(
        "hesap sorgusu | kullanici=%s | anapara=%s | oran=%s | vade=%s",
        kullanici.get("kullanici"),
        istek.anapara,
        istek.aylik_oran_percent,
        istek.vade_ay,
    )

    # Yuzde -> ondalik (1.89 -> 0.0189)
    aylik_oran = istek.aylik_oran_percent / 100

    try:
        sonuc = aylik_taksit_hesapla(istek.anapara, aylik_oran, istek.vade_ay)
    except HesapGirdiHatasi as e:
        log.warning("Gecersiz hesap girdisi: %s", e)
        raise HTTPException(status_code=422, detail=str(e))

    plan: list[OdemeSatiriYanit] = []
    if istek.odeme_plani_istiyor:
        plan = [
            OdemeSatiriYanit(
                ay=s.ay,
                taksit=s.taksit,
                kar_payi_kismi=s.kar_payi_kismi,
                anapara_kismi=s.anapara_kismi,
                kalan_bakiye=s.kalan_bakiye,
            )
            for s in odeme_plani_uret(istek.anapara, aylik_oran, istek.vade_ay)
        ]

    latency = int((time.time() - baslangic) * 1000)

    return HesapYanit(
        anapara=sonuc.anapara,
        aylik_oran_percent=istek.aylik_oran_percent,
        vade_ay=sonuc.vade_ay,
        aylik_taksit=sonuc.aylik_taksit,
        toplam_odeme=sonuc.toplam_odeme,
        toplam_kar_payi=sonuc.toplam_kar_payi,
        ozet=sonuc.ozet_metni(),
        odeme_plani=plan,
        audit=_bos_audit(
            cagrilan_arac="calculator",
            latency_ms=latency,
            response_confidence=1.0,  # deterministik hesap - belirsizlik yok
            sebep="Saf Python hesabi, LLM kullanilmadi",
        ),
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

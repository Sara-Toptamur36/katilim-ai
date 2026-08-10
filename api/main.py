"""KatilimAI API - FastAPI uygulamasi.

DURUM: Yedi uc nokta da gercek verilerle calisir. /chat, Ajan
Orkestratoru uzerinden Intent Detection -> Tool Router -> (SQL /
Calculator / Sozluk / RAG / Fallback) zincirini calistirir ve her
yanitla birlikte Juri Audit Paneli'nin (rapor Bolum 10.2) ihtiyac
duydugu izlenebilirlik blogunu doner.

VERI KAYNAGI: /kampanyalar ve /karsilastir, GERCEK_VERI_AKTIF ortam
degiskeni "true" oldugunda mock_data.py yerine PostgreSQL'i (api/db.py,
api/kampanya_repository.py) kullanir. Varsayilan FALSE'tur; mock veri
sartnamenin Senaryo-1 ornegini (A/B/C/D Bankasi) birebir tasir ve
sozlesme testleri (tests/test_api_sozlesme.py) bu sabit degerlere
dayanir - bu yuzden varsayilan bilerek degistirilmemistir.

KIMLIK DOGRULAMA: Authorization basligi her zaman zorunludur; JWT_AKTIF
"true" oldugunda token gercekten dogrulanir. Baslik formati iki modda da
ayni oldugu icin arayuz kodu geciste degismez (bkz. api/auth.py).

Calistirma:
    uvicorn api.main:app --reload
Swagger:
    http://localhost:8000/docs
"""

import os
import time

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from agent.orchestrator import soru_isle
from api.auth import GERCEK_JWT_AKTIF, token_dogrula, token_uret
from api.db import oturum_al
from api.kampanya_repository import id_ile_getir_db, kampanyalari_getir_db
from api.kullanici_repository import kullanici_dogrula
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
    TokenYanit,
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

# Varsayilan "false" (bkz. dosya basi aciklamasi, VERI KAYNAGI).
GERCEK_VERI_AKTIF = os.environ.get("GERCEK_VERI_AKTIF", "false").lower() == "true"


def _bos_audit(**kwargs) -> AuditBilgisi:
    """Audit blogunu her uc nokta icin ortak varsayilanlarla (model,
    temperature, cache_hit) kurar; cagiran uc nokta kendi alanlarini
    ustune yazar. Bir alanin o uc noktada anlami yoksa None kalir -
    uydurulmaz (rapor Bolum 5.7/15)."""
    varsayilan = {
        "model": MODEL_ADI,
        "temperature": TEMPERATURE,
        "cache_hit": False,
    }
    varsayilan.update(kwargs)
    return AuditBilgisi(**varsayilan)


@app.get("/", tags=["Sistem"])
def kok():
    """Servis ayakta mi kontrolu (kimlik dogrulama gerektirmez).

    Aktif yapilandirmayi da doner - juri/gelistirici, API'nin gercek
    veriyle mi mock veriyle mi calistigini ve JWT'nin acik olup
    olmadigini sormadan gorebilsin (seffaflik ilkesi, rapor Bolum 5.7/15).
    """
    return {
        "servis": "KatilimAI API",
        "surum": app.version,
        "durum": "calisiyor",
        "veri_kaynagi": "postgresql" if GERCEK_VERI_AKTIF else "mock",
        "jwt_dogrulama": "gercek" if GERCEK_JWT_AKTIF else "mock",
        "dokumantasyon": "/docs",
    }


@app.get("/saglik", tags=["Sistem"])
def saglik():
    """Health check - CI ve docker-compose icin."""
    return {"durum": "saglikli"}


@app.post("/token", response_model=TokenYanit, tags=["Kimlik Dogrulama"])
def token_al(form: OAuth2PasswordRequestForm = Depends()):
    """Kullanici adi/parolayla JWT alir (yalnizca JWT_AKTIF=true iken).

    Mock modda (varsayilan) bu uc nokta kullanilmaz - herhangi bir
    'Bearer <token>' zaten kabul edilir (bkz. api/auth.py).
    """
    if not GERCEK_JWT_AKTIF:
        raise HTTPException(
            status_code=400,
            detail=(
                "Gercek JWT modu aktif degil (JWT_AKTIF=true degil). "
                "Mock modda herhangi bir 'Bearer <token>' kabul edilir, "
                "/token gerekmez."
            ),
        )
    oturum = next(oturum_al())
    try:
        kullanici = kullanici_dogrula(oturum, form.username, form.password)
    finally:
        oturum.close()
    if kullanici is None:
        log.warning("Basarisiz giris denemesi | kullanici_adi=%s", form.username)
        raise HTTPException(status_code=401, detail="Kullanici adi veya parola hatali")
    return TokenYanit(access_token=token_uret(kullanici.kullanici_adi, kullanici.rol))


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

    SIRALAMA BELLEKTE YAPILIR (bilincli): kayitlar PostgreSQL'den
    cekilir, ama siralama/eksik-alan isaretleme comparison/
    compare_engine.py'nin bellek modunda yurur. Boylece mock ve gercek
    veri AYNI kod yolundan gecer ve iki mod arasindaki fark yalnizca
    kayitlarin nereden geldigidir. `calistirilan_sql`, ayni kriterin
    SQL karsiligidir ve seffaflik icin audit panelinde gosterilir -
    su an calistirilmaz, uretilir.
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
    saf Python fonksiyonlarini cagirir; ozet cumle de dogrudan
    sayilardan uretilir, LLM kullanilmaz.

    Ajan Orkestratoru "hesaplama" niyeti tespit ettiginde ayni
    calculator/ mantigini cagirir (bkz. agent/router.py) - iki yol da
    tek bir hesap kaynagini kullanir.
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


def _banka_kayitlarini_getir(banka: str) -> list:
    """agent/router.py'nin karsilastirma araci icin kayit kaynagi.

    GERCEK_VERI_AKTIF bayragina gore mock/DB ayrimini burada yapariz -
    agent/ paketi hangi kaynaktan geldigini hic bilmez (Sprint 2'de
    kurulan ayni ayrimla tutarli, bkz. dosya basi aciklamasi).
    """
    if GERCEK_VERI_AKTIF:
        oturum = next(oturum_al())
        try:
            return kampanyalari_getir_db(oturum, banka=banka)
        finally:
            oturum.close()
    return kampanyalari_getir(banka=banka)


@app.post("/chat", response_model=ChatYanit, tags=["Chatbot"])
def chat(istek: ChatIstek, kullanici: dict = Depends(token_dogrula)):
    """Dogal dilde soru-cevap - Ajan Orkestratoru (agent/orchestrator.py).

    AKIS: Intent Detection -> Tool Router -> SQL / Calculator / Sozluk /
    RAG / Fallback. Belirli bir araca uymayan serbest bilgi sorulari
    RAG ile KAYNAK GOSTEREREK yanitlanir; secilen arac yetersiz kalirsa
    soru yine RAG'e sorulur (kademeli geri cekilme). Hicbir yolda
    kaynaksiz cevap uretilmez - kaynak bulunamazsa sistem acikca
    cekimser kalir (rapor Bolum 5.7/15).

    NOT: audit blogu her yanitta bulunur; o an anlamsiz olan alanlar
    None doner. Havin'in Juri Audit Paneli bu alan adlarina gore
    kurulur; sonradan isim degistirmek onun kodunu bozar.
    """
    log.info("chat sorgusu | kullanici=%s | soru=%s", kullanici.get("kullanici"), istek.soru)

    sonuc = soru_isle(istek.soru, _banka_kayitlarini_getir)
    ekstra = sonuc["audit_ekstra"]

    return ChatYanit(
        cevap=sonuc["cevap"],
        kaynaklar=sonuc["kaynaklar"],
        confidence=sonuc["confidence"],
        fallback=sonuc["fallback"],
        audit=_bos_audit(
            intent=ekstra["intent"],
            intent_confidence=ekstra["intent_confidence"],
            cagrilan_arac=ekstra["cagrilan_arac"],
            extraction_confidence=ekstra["extraction_confidence"],
            regex_basari_orani=ekstra["regex_basari_orani"],
            retriever_sonuclari=ekstra["retriever_sonuclari"],
            response_confidence=sonuc["confidence"],
            latency_ms=ekstra["latency_ms"],
            sebep=ekstra["sebep"],
            terminoloji_tutarli=ekstra["terminoloji_tutarli"],
            terminoloji_sorunlari=ekstra["terminoloji_sorunlari"],
        ),
    )

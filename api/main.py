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

import ortam_yukle  # noqa: F401 - side effect: .env process ortamina yuklenir, HER SEYDEN ONCE

import asyncio
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm

from agent.orchestrator import soru_isle
from api.auth import GERCEK_JWT_AKTIF, rol_gerekli, token_dogrula, token_uret
from complaint.izin_kapisi import herhangi_bir_izin_var_mi
from complaint.tema_siniflandirici import tema_siniflandir
from complaint.toplama import (
    COZUM_ORANI_ASGARI_ORNEKLEM,
    hazirla,
    musteri_sesi_istatistiklerini_hesapla,
    yogunluk_ozeti,
)
from api.db import oturum_al
from api.kampanya_repository import id_ile_getir_db, kampanyalari_getir_db
from api.kullanici_repository import (
    kullanici_dogrula,
    kullanici_getir,
    kullanici_olustur,
    sifre_degistir as sifre_degistir_db,
)
from api.logging_config import log
from api.mock_data import id_ile_getir, kampanyalari_getir
from api.models import AuditKayit, Sikayet
from api.schemas import (
    AuditBilgisi,
    CampaignRecord,
    ChatIstek,
    ChatYanit,
    HesapIstek,
    HesapYanit,
    Kaynak,
    KarsilastirIstek,
    KarsilastirYanit,
    KayitIstek,
    KayitYanit,
    SifreDegistirIstek,
    SifreDegistirYanit,
    MusteriSesiIstek,
    MusteriSesiOrnek,
    MusteriSesiOrnekYanit,
    MusteriSesiYogunlukYanit,
    MusteriSesiYanit,
    SikayetDetayYanit,
    KampanyaMusteriSesiOrnegi,
    KampanyaMusteriSesiOzeti,
    MusteriSesiIstatistikler,
    CikarimAdayi,
    CikarimIstek,
    CikarimIzi,
    CikarimYanit,
    EtkiSkoruYanit,
    OdemeSatiriYanit,
    RakipAnaliziYanit,
    TarihceYanit,
    TazelikYanit,
    TerimKarti,
    TokenYanit,
)
from chunking.indeks_durumu import indeks_durumu_oku
from scraper.scripts.kampanya_tarihcesi import degisen_alanlari_bul, tarihce_getir
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
    rakip_matrisi,
)
from comparison.etki_skoru import etki_skoru
from extraction.hybrid_pipeline import kaydi_hibrit_cikar
from extraction.regex_extractor import genel_guven_hesapla
from validation.verifier import kaydi_dogrula
from terminology.sozluk import sozluk_yukle
from terminology.tutarlilik_kontrolu import terminoloji_tutarliligini_kontrol_et

# Gomme modeli normalde ILK /chat sorusunda yuklenir (chunking/embedding.py,
# tembel yukleme). Olculdu (17 Agu): sicak sorgu ~5-9 sn, ilk sorgu 54,9 sn -
# bellek sikisikken cok daha uzun. Yani DEMODA ILK SORUYU SORAN JURI UYESI
# en kotu deneyimi yasar; sonraki herkes hizli cevap alir.
#
# ISITMA bu maliyeti sunucu acilisina tasir: uygulama hazir dedigi anda model
# de hazirdir. VARSAYILAN KAPALI, cunku testler ve CI api.main'i sik sik
# import eder ve orada 1 GB'lik modeli yuklemek olcumsuz bir yavaslama olur.
# Demo/sunum oncesi acilir:  KATILIMAI_MODEL_ISIT=true uvicorn api.main:app
MODEL_ISITMA_AKTIF = os.environ.get("KATILIMAI_MODEL_ISIT", "false").lower() == "true"


@asynccontextmanager
async def yasam_dongusu(_app: FastAPI):
    if MODEL_ISITMA_AKTIF:
        from chunking.embedding import model_hazir_mi

        baslangic = time.time()
        hata = model_hazir_mi()
        sure = round(time.time() - baslangic, 1)
        if hata:
            # Isitma basarisiz olsa bile API AYAGA KALKAR: embedding'e
            # dokunmayan uc noktalar (/kampanyalar, /hesapla, /karsilastir)
            # calismaya devam etmeli. Sessizce yutulmaz, log'a yazilir.
            log.warning("model isitma basarisiz | sure=%ss | hata=%s", sure, hata)
        else:
            log.info("gomme modeli isitildi | sure=%ss", sure)
    else:
        log.info("model isitma kapali - ilk /chat sorusu yavas olacak")
    yield


app = FastAPI(
    lifespan=yasam_dongusu,
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
    "http://localhost:5174",  # 5173 kullanımdaysa Vite 5174'e geçer
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
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

# Faz 1 T8 - sentetik musteri sesi demo verisi (urun verisi DEGIL, bkz.
# complaint/tema_siniflandirici.py modul basligi).
SENTETIK_MUSTERI_SESI_YOLU = (
    Path(__file__).resolve().parent.parent
    / "tests" / "veri" / "kapsam_disi" / "sentetik_musteri_sesi.json"
)

# Varsayilan "false" (bkz. dosya basi aciklamasi, VERI KAYNAGI).
GERCEK_VERI_AKTIF = os.environ.get("GERCEK_VERI_AKTIF", "false").lower() == "true"

# DEMO_MODE: Frontend demo banner + demo_snapshot flag'i icin.
# GERCEK_VERI_AKTIF=false iken otomatik True sayilir (mock veri = demo).
# Gercek veri akilken de DEMO_MODE=true cevrimicdisi senaryo icin set edilebilir.
DEMO_MODE = not GERCEK_VERI_AKTIF or os.environ.get("DEMO_MODE", "false").lower() == "true"


def _bos_audit(**kwargs) -> AuditBilgisi:
    """Audit blogunu her uc nokta icin ortak varsayilanlarla (model,
    temperature, cache_hit, trace_id, demo_snapshot) kurar; cagiran
    uc nokta kendi alanlarini ustune yazar. Bir alanin o uc noktada
    anlami yoksa None kalir - uydurulmaz (rapor Bolum 5.7/15).

    trace_id: Her istege ait UUID - Decision Trace modali + log arama.
    demo_snapshot: GERCEK_VERI_AKTIF=false iken otomatik True - frontend
      DEMO SNAPSHOT rozeti gosterir.
    """
    varsayilan = {
        "model": MODEL_ADI,
        "temperature": TEMPERATURE,
        "cache_hit": False,
        "trace_id": str(uuid.uuid4()),
        "demo_snapshot": DEMO_MODE,
    }
    varsayilan.update(kwargs)
    return AuditBilgisi(**varsayilan)


def _audit_kaydet(
    kullanici: dict,
    uc_nokta: str,
    latency_ms: int,
    soru: str | None = None,
    intent: str | None = None,
    intent_confidence: float | None = None,
    cagrilan_arac: str | None = None,
    sql_sorgusu: str | None = None,
    cache_hit: bool = False,
) -> None:
    """Md. 11 izlenebilirlik: her istegi audit_kayitlari tablosuna yazar.

    DENETIM BULGUSU (mentor denetimi): AuditKayit tablosu tanimli ve
    migrate edilmisti ama hicbir yer ona satir yazmiyordu.

    YALNIZCA GERCEK_VERI_AKTIF modunda calisir - mock mod BILEREK
    Docker/Postgres gerektirmez (bkz. dosya basi aciklamasi, VERI
    KAYNAGI); audit yazimi bu garantiyi bozarsa mock moddaki her /chat,
    /karsilastir, /hesapla cagrisi (ve onlara dayanan sozlesme testleri)
    Postgres calismadan hata verirdi.

    Yazim basarisiz olursa kullanicinin ASIL istegi ETKILENMEZ (loglanir,
    hata firlatilmaz) - audit ikincil bir kayittir, ana islevi engellemez.
    """
    if not GERCEK_VERI_AKTIF:
        return
    try:
        oturum = next(oturum_al())
        try:
            oturum.add(
                AuditKayit(
                    kullanici=kullanici.get("kullanici"),
                    rol=kullanici.get("rol"),
                    uc_nokta=uc_nokta,
                    soru=soru,
                    intent=intent,
                    intent_confidence=intent_confidence,
                    cagrilan_arac=cagrilan_arac,
                    sql_sorgusu=sql_sorgusu,
                    latency_ms=latency_ms,
                    cache_hit=cache_hit,
                )
            )
            oturum.commit()
        finally:
            oturum.close()
    except Exception:
        log.warning("Audit kaydi yazilamadi (uc_nokta=%s)", uc_nokta, exc_info=True)


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


def _ham_veri_tazeligi() -> tuple[str | None, int, int]:
    """(en yeni erisim_zamani, tekil kampanya sayisi, anlik goruntu sayisi).

    Ham veri toplam ~1,4 MB oldugu icin tamamini okumak ucuz; dosya
    adindaki tarihe guvenmek yerine kaydin KENDI erisim zamani kullanilir.
    """
    kok = Path(__file__).resolve().parent.parent / "scraper" / "raw_data"
    en_yeni: str | None = None
    urller: set[str] = set()
    anlik = 0
    for dosya in kok.glob("*/json/*.json"):
        try:
            with open(dosya, encoding="utf-8") as f:
                kayit = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        anlik += 1
        if kayit.get("url"):
            urller.add(kayit["url"])
        zaman = kayit.get("erisim_zamani")
        if zaman and (en_yeni is None or zaman > en_yeni):
            en_yeni = zaman
    return en_yeni, len(urller), anlik


_SOZLUK_YOLU = Path(__file__).resolve().parent.parent / "terminology" / "sozluk.json"


def _kural_versiyonu() -> str | None:
    """RULE_VERSION tanimli degilse terminology/sozluk.json'un icerik
    hash'inden turetilir - api/schemas.py'deki TazelikYanit.rule_version
    aciklamasi ("RULE_VERSION ortam degiskeninden ya da sozluk git
    hash'inden") bunu vaat ediyordu ama bu fallback hic yazilmamisti,
    alan hep bos donuyordu (denetim bulgusu, 25.08.2026).

    Git commit hash'i yerine DOSYA ICERIGI hash'i kullanilir: dagitilan
    ortamda git gecmisi bulunmayabilir (ornegin Docker imaji), ama sozluk
    dosyasi her zaman oradadir. Ayrica bu, "kural gercekten degisti mi"
    sorusuna git hash'inden daha dogru cevap verir - sozlugun disindaki
    bir commit git hash'ini degistirir ama kural versiyonunu degistirmez.
    """
    ortam_degeri = os.environ.get("RULE_VERSION")
    if ortam_degeri:
        return ortam_degeri
    try:
        icerik = _SOZLUK_YOLU.read_bytes()
    except OSError:
        return None
    import hashlib

    return "sozluk-" + hashlib.sha256(icerik).hexdigest()[:12]


_ALTIN_VERI_SETI_YOLU = (
    Path(__file__).resolve().parent.parent / "gold_dataset" / "altin_veri_seti.json"
)


def _veri_seti_versiyonu() -> str | None:
    """DATASET_VERSION tanimli degilse Altin Veri Seti'nin kendisinden
    turetilir (imzali kayit sayisi + en son giris tarihi) - env
    degiskeni elle guncellenmeyi unutulup bayatlayabilir, bu deger dosya
    her degistiginde kendiliginden dogru kalir (denetim bulgusu,
    25.08.2026 - ayni sinif hata: dashboard'daki SISTEM_DURUMU.sonTarama
    sabitiyle celisen canli tarih).
    """
    ortam_degeri = os.environ.get("DATASET_VERSION")
    if ortam_degeri:
        return ortam_degeri
    try:
        with open(_ALTIN_VERI_SETI_YOLU, encoding="utf-8") as f:
            kayitlar = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    imzali = [
        k for k in kayitlar
        if k.get("giren_kisi") and k["giren_kisi"] != "ORNEK"
    ]
    if not imzali:
        return None
    en_son_giris = max((k.get("giris_tarihi") or "" for k in imzali), default="")
    return f"{len(imzali)}imzali-{en_son_giris}" if en_son_giris else f"{len(imzali)}imzali"


def _rag_indeks_versiyonu(durum: dict) -> str | None:
    """RAG_INDEX_VERSION tanimli degilse indeks_durumu.json'daki parca
    sayisi + kurulma tarihinden turetilir - ayni gerekce (yukaridaki
    _veri_seti_versiyonu docstring'i)."""
    ortam_degeri = os.environ.get("RAG_INDEX_VERSION")
    if ortam_degeri:
        return ortam_degeri
    parca = durum.get("parca_sayisi")
    kuruldu = durum.get("kuruldu")
    if parca is None or not kuruldu:
        return None
    return f"{parca}parca-{kuruldu[:10]}"


def _gun_farki(zaman_metni: str | None) -> int | None:
    if not zaman_metni:
        return None
    try:
        an = datetime.fromisoformat(zaman_metni)
    except ValueError:
        return None
    if an.tzinfo is None:
        an = an.replace(tzinfo=timezone.utc)
    return max(0, (datetime.now(timezone.utc) - an).days)


@app.get("/sistem/tazelik", response_model=TazelikYanit, tags=["Sistem"])
def tazelik(kullanici: dict = Depends(token_dogrula)):
    """Veri ve RAG indeksi ne kadar guncel? (Mentor raporu II, P0 #1)

    Dashboard bunu ust seritte gosterir. Bilinmeyen deger TAHMIN EDILMEZ:
    indeks durum dosyasi yoksa alanlar None doner ve arayuz "bilinmiyor"
    yazar - "indeks eski" ile "indeks durumu bilinmiyor" farkli seylerdir.
    """
    son_tarama, tekil, anlik = _ham_veri_tazeligi()
    durum = indeks_durumu_oku() or {}
    kuruldu = durum.get("kuruldu")

    # Indeks kurulduktan SONRA yeni veri toplandiysa RAG bayat demektir.
    # Iki taraf da bilinmiyorsa karar da bilinmiyordur (None) - False
    # dondurmek "guncel" gibi okunurdu.
    eski_mi = None
    if kuruldu and son_tarama:
        eski_mi = son_tarama > kuruldu

    return TazelikYanit(
        son_tarama=son_tarama,
        tarama_gun_once=_gun_farki(son_tarama),
        rag_indeks_kuruldu=kuruldu,
        rag_indeks_gun_once=_gun_farki(kuruldu),
        rag_parca_sayisi=durum.get("parca_sayisi"),
        rag_belge_sayisi=durum.get("belge_sayisi"),
        indeks_ham_veriden_eski_mi=eski_mi,
        tekil_kampanya=tekil,
        anlik_goruntu=anlik,
        # System Health / Versiyon alanlari.
        # Oncelik sirasi: indeks_durumu dosyasi > ortam degiskeni >
        # dosyadan turetilen deger > None. Hicbir kaynak yoksa None doner -
        # tahmin edilmez (bkz. _veri_seti_versiyonu / _rag_indeks_versiyonu
        # docstring'leri, denetim bulgusu 25.08.2026).
        dataset_version=durum.get("dataset_version") or _veri_seti_versiyonu(),
        rag_index_version=durum.get("rag_index_version") or _rag_indeks_versiyonu(durum),
        model_version=MODEL_ADI,
        rule_version=_kural_versiyonu(),
        demo_mode=DEMO_MODE,
        git_commit=os.environ.get("GIT_COMMIT"),
        last_ci=os.environ.get("LAST_CI"),
    )


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
    return TokenYanit(
        access_token=token_uret(kullanici.kullanici_adi, kullanici.rol),
        rol=kullanici.rol,
    )


@app.post("/kayit", response_model=KayitYanit, tags=["Kimlik Dogrulama"])
def kayit_ol(istek: KayitIstek):
    """Kendi kendine kayit - yalnizca 'musteri' rolu icin.

    TEKNOFEST teknik toplantisinda netlesen kapsam: "sıradan müşteriler
    de kullanıcı sayılabilir" - bu yuzden banka_calisani/denetleyici/
    yonetici rolleri (halihazirda api/scripts/kullanici_ekle.py ile elle
    acilan hesaplardir, bilerek serbest kayit disinda tutuldu) disinda
    dorduncu, kisitli bir rol acildi.

    ROL ISTEMCIDEN ASLA KABUL EDILMEZ (bkz. KayitIstek): sunucu HER ZAMAN
    'musteri' atar - aksi halde herhangi bir ziyaretci kendini yonetici
    yapabilirdi. Bu uc nokta JWT_AKTIF durumundan BAGIMSIZ calisir (mock
    modda bile kayit DB'ye yazilir, boylece kayit ekrani JWT kapaliyken
    de gelistirilip test edilebilir - gercek yetkilendirme yalnizca
    JWT_AKTIF=true oldugunda devreye girer).
    """
    oturum = next(oturum_al())
    try:
        if kullanici_getir(oturum, istek.kullanici_adi) is not None:
            raise HTTPException(status_code=409, detail="Bu kullanici adi zaten kayitli")
        yeni = kullanici_olustur(oturum, istek.kullanici_adi, istek.sifre, rol="musteri")
        log.info("yeni musteri kaydi | kullanici_adi=%s", yeni.kullanici_adi)
        return KayitYanit(kullanici_adi=yeni.kullanici_adi, rol=yeni.rol)
    finally:
        oturum.close()


@app.post(
    "/kullanici/sifre-degistir",
    response_model=SifreDegistirYanit,
    tags=["Kimlik Dogrulama"],
)
def sifre_degistir_uc(istek: SifreDegistirIstek):
    """Mevcut sifreyi dogrulayip yenisiyle degistirir.

    /kayit ile AYNI gerekce: JWT_AKTIF durumundan BAGIMSIZ calisir. Mock
    modda kullanici kimligi token'dan degil, istek govdesindeki
    kullanici_adi'ndan gelir (bu modda zaten hicbir Bearer token
    dogrulanmiyor - bkz. api/auth.py::token_dogrula).
    """
    oturum = next(oturum_al())
    try:
        kullanici = kullanici_dogrula(oturum, istek.kullanici_adi, istek.mevcut_sifre)
        if kullanici is None:
            log.warning(
                "basarisiz sifre degistirme denemesi | kullanici_adi=%s",
                istek.kullanici_adi,
            )
            raise HTTPException(status_code=401, detail="Mevcut sifre hatali")
        sifre_degistir_db(oturum, istek.kullanici_adi, istek.yeni_sifre)
        log.info("sifre degistirildi | kullanici_adi=%s", istek.kullanici_adi)
        return SifreDegistirYanit(basarili=True)
    finally:
        oturum.close()


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


@app.get("/terminoloji", response_model=list[TerimKarti], tags=["Terminoloji"])
def terminoloji(kullanici: dict = Depends(token_dogrula)):
    """Katilim bankaciligi terminoloji sozlugu (Sartname Md. 5.5).

    Kaynak terminology/sozluk.json'dir - arayuz artik kendi kopyasini
    tutmaz. DENETIM BULGUSU: dashboard/src/api/terminolojiMock.js, bu uc
    nokta olmadigi icin sozlugun AYRI bir kopyasini tasiyordu ve zamanla
    surukleniyordu (gercek sozlukte 31 kavram varken mock'ta 8 kalmisti,
    ustelik mock'ta olan `aciklama` alani gercek sozlukte yoktu). Tek
    kaynak burasidir; mock kaldirildi.

    Kimlik dogrulama, diger okuma uc noktalariyla (bkz. /kampanyalar)
    tutarli olsun diye istenir - sozluk gizli veri degildir.
    """
    sozluk = sozluk_yukle()
    return [
        TerimKarti(
            anahtar=anahtar,
            standart_terim=veri["standart_terim"],
            gelenek_karsilik=veri["gelenek_karsilik"],
            aciklama=veri["aciklama"],
            kaynak=veri["kaynak"],
            sema_alani=veri.get("sema_alani", []),
            ornek_kaynak=veri.get("ornek_kaynak"),
        )
        for anahtar, veri in sozluk.items()
    ]


# Bu alanlar metinden SPAN olarak cikarilmaz, anahtar kelimeyle
# SINIFLANDIRILIR; izlerindeki "kaynak_span" bir etikettir, metinde aynen
# gecmez (bkz. extraction/hybrid_pipeline.py "KAPSAM DISI ALANLAR").
#
# "hedef_kitle" DE BURAYA AIT (17 Agustos'ta eklendi): o da kampanya_turu
# ile BIREBIR ayni sekilde, anahtar kelime listesiyle bir ETIKETE
# ("Yeni müşteri" / "Mevcut müşteri" / "Maaş müşterisi") siniflandirilir -
# izindeki deger metinden kesilmis bir alinti degil, o etiketin kendisidir.
# Eksikligi simdiye kadar GORUNMUYORDU: regex_extractor diyakritiksiz
# yazilmis metinde hedef_kitle'yi hic bulamadigi icin (bkz. ayni tarihli
# katlama duzeltmesi) test metninde alan bos donuyor, dolayisiyla iz de
# uretilmiyordu. Katlama duzeltilince alan doldu ve "Yeni müşteri" etiketi
# span diye isaretlenip metinde ARANMAYA calisildi.
_SINIFLANDIRMA_ALANLARI = {"kampanya_turu", "hedef_kitle"}


@app.post("/cikar", response_model=CikarimYanit, tags=["Cikarim"])
def cikar(
    istek: CikarimIstek,
    kullanici: dict = Depends(rol_gerekli(["banka_calisani", "denetleyici", "yonetici"])),
):
    """Serbest kampanya metninden yapilandirilmis alanlari cikarir.

    ROL KISITI: yalnizca banka calisani/denetleyici/yonetici - "musteri"
    rolu icin DEGIL (bkz. api/schemas.py::KayitIstek). Bu, cikarim
    motorunun ic/analiz araci (MetinAnalizi ekrani) olmasindan gelir, son
    kullaniciya sunulan bir kampanya karsilastirma ozelligi degildir.
    MOCK modda (varsayilan, GERCEK_JWT_AKTIF=false) bu kisit hicbir etki
    yapmaz - rol_gerekli() sadece JWT_AKTIF=true oldugunda uygulanir
    (bkz. api/auth.py). DENETIM BULGUSU: rol_gerekli() yazilmisti ama
    hicbir endpoint'e baglanmamisti - "rol var ama hicbir yerde
    kullanilmiyor" durumu artik somut bir orneğe sahip.

    NEDEN VAR (Sartname Md. 6): demo videosunda "metin girdisi verilmesi,
    modelin urettigi yapilandirilmis cikti" gosterilmesi ZORUNLU. Cikarim
    motoru bugune kadar yalnizca toplu zenginlestirme script'inden
    (extraction/regex_ile_zenginlestir.py) erisilebiliyordu; bu uc nokta
    ayni motoru tek bir metin icin acar.

    SONUC TEK BASINA DONMEZ: her alanin yaninda hangi katmanin doldurdugu,
    metindeki kaniti (kaynak_span), guveni, Verifier'in dogrulayip
    dogrulamadigi ve varsa diger katmanlarin adaylari gider. Bulunamayan
    alanlar `bos_alanlar` icinde ADIYLA listelenir - sifir yazilmaz,
    "kaynakta belirtilmemis" demektir.

    HIBRIT VARSAYILAN OLARAK KAPALI: `hibrit=true` NER+LLM katmanlarini da
    acar ama LLM GPU'suz makinede kayit basina 150-300 sn surer. Canli
    demoda kullanilmamalidir.
    """
    baslangic = time.time()

    cikan = kaydi_hibrit_cikar(
        istek.metin, ner_kullan=istek.hibrit, llm_kullan=istek.hibrit
    )
    izler_ham = cikan.pop("_izler")
    kaynaklar = cikan.pop("_kaynaklar")
    adaylar = cikan.pop("_adaylar", {})
    catismalar = cikan.pop("_catismalar", [])

    # Verifier: yazilan sayisal degerler kaynak metinde (deger + baglam)
    # gercekten geciyor mu? Sonuc GORUNURLUK icindir, deger BUDANMAZ -
    # extraction/regex_ile_zenginlestir.py'deki ayni ilke.
    dogrulama = kaydi_dogrula(
        {alan: cikan.get(alan) for alan in izler_ham}, istek.metin
    )

    izler = [
        CikarimIzi(
            alan=alan,
            kaynak_span=span,
            # kampanya_turu anahtar kelimeyle SINIFLANDIRILIR, span
            # cikarilmaz - "kanit" olarak gosterilirse kullanici metinde
            # o ifadeyi arar ve bulamaz.
            kanit_turu="siniflandirma" if alan in _SINIFLANDIRMA_ALANLARI else "span",
            guven=guven,
            katman=kaynaklar.get(alan, "regex"),
            dogrulandi=(
                dogrulama[alan].dogrulandi if alan in dogrulama else None
            ),
            adaylar=[CikarimAdayi(**a) for a in adaylar.get(alan, [])],
        )
        for alan, (span, guven) in izler_ham.items()
    ]

    bos_alanlar = sorted(a for a, d in cikan.items() if d is None)
    # Degeri var ama izi yok => metinden cikarilmadi, TURETILDI (ör.
    # kampanya_avantaji ozeti, kar_payi_orani_decimal). Sabit liste yerine
    # izlerin yoklugundan hesaplaniyor - yeni turetilmis alan eklenirse
    # burasi kendiliginden dogru kalir.
    turetilmis_alanlar = sorted(
        a for a, d in cikan.items() if d is not None and a not in izler_ham
    )

    # Ollama kapaliyken hibrit istenirse sessizce regex sonucu donerdi -
    # kullanici "hibrit calisti" saniyordu. Durumu acikca bildiriyoruz.
    not_metni = None
    if istek.hibrit and not any(k in ("ner", "llm") for k in kaynaklar.values()):
        not_metni = (
            "Hibrit istendi ancak NER/LLM katmanlarindan hicbir alan gelmedi. "
            "Ollama kapali olabilir ya da regex tum alanlari zaten doldurmus "
            "olabilir; sonuc deterministik katmanindir."
        )

    sure_ms = int((time.time() - baslangic) * 1000)
    _audit_kaydet(kullanici, "cikar", sure_ms, cagrilan_arac="extraction")

    return CikarimYanit(
        alanlar=cikan,
        izler=izler,
        catismalar=catismalar,
        bos_alanlar=bos_alanlar,
        turetilmis_alanlar=turetilmis_alanlar,
        genel_guven=genel_guven_hesapla(izler_ham),
        hibrit_kullanildi=istek.hibrit,
        sure_ms=sure_ms,
        # Cikarim, denetim kaydina (yukaridaki _audit_kaydet) zaten
        # yaziliyordu ama YANITA konmadigi icin Juri Audit Paneli'ne hic
        # dusmuyordu - /hesapla ve /karsilastir'da olan blok burada eksikti
        # (Havin'in 24.08.2026 raporu, Md. 6).
        audit=_bos_audit(
            cagrilan_arac="extraction",
            latency_ms=sure_ms,
            response_confidence=genel_guven_hesapla(izler_ham),
            sebep=(
                "Hibrit cikarim (regex -> NER -> LLM)"
                if istek.hibrit
                else "Yalnizca deterministik regex katmani"
            ),
        ),
        **{"not": not_metni},
    )


@app.post(
    "/musteri-sesi/siniflandir",
    response_model=MusteriSesiYanit,
    tags=["Musteri Sesi"],
)
def musteri_sesi_siniflandir(
    istek: MusteriSesiIstek, kullanici: dict = Depends(token_dogrula)
):
    """Serbest metni Complaint Insight taksonomisine (mentor 3.3, 10 tema)
    gore kural tabanli siniflandirir.

    HICBIR SEY SAKLAMAZ: bu uc nokta bir sikayet veritabani DEGILDIR,
    gonderilen metni islenmez, kaydetmez - yalnizca siniflandirip doner.
    Gercek musteri verisi henuz yok (bkz. MusteriSesiOrnekYanit docstring'i
    - kurumsal/hukuki izin sureci Faz 2). KURAL TABANLI (duygu modeli
    degil) - hizli, aciklanabilir, "neden bu temaya girdi?" sorusuna hangi
    ifadenin eslestigini gostererek cevap verir. Hicbir tema eslesmezse
    None doner - uydurulmaz (rapor Bolum 5.7/15 ile ayni ilke).
    """
    sonuc = tema_siniflandir(istek.metin)
    return MusteriSesiYanit(**sonuc)


@app.get(
    "/musteri-sesi/ornekler",
    response_model=MusteriSesiOrnekYanit,
    tags=["Musteri Sesi"],
)
def musteri_sesi_ornekler(kullanici: dict = Depends(token_dogrula)):
    """Sentetik musteri sesi demo seti - Faz 1 T8.

    DURUSTLUK: donen 'ornekler' GERCEK sikayet DEGILDIR, elle yazilmis
    sentetik veridir (bkz. MusteriSesiOrnekYanit.aciklama alani, her
    yanitta tekrar edilir - dashboard bunu gizlemeden gostermeli).

    27 Agustos 2026'dan itibaren `complaint/toplama.py::hazirla` HATTININ
    TAMAMINDAN gecirilir (yalnizca tema_siniflandir DEGIL) - boylece
    dashboard PII maskeleme, onem derecesi, cozum durumu ve dusuk-bilgi
    isaretini de gorebilir. VERITABANINA YAZILMAZ: `hazirla()` cagrilir,
    `kaydet()` cagrilmaz - bu ornekler HALA `sikayetler` tablosuna
    girmez (bkz. docs/kapsam_ve_veri_ayrimi.md §6).
    """
    with open(SENTETIK_MUSTERI_SESI_YOLU, encoding="utf-8") as f:
        veri = json.load(f)

    bilinen_hashler: list[str] = []
    ornekler = []
    for o in veri["ornekler"]:
        hazir = hazirla(
            o["metin"], kaynak="sentetik_musteri_sesi", izin_zorunlu=False,
            bilinen_icerik_hashleri=bilinen_hashler,
        )
        bilinen_hashler.append(hazir.icerik_hash)
        ornekler.append(MusteriSesiOrnek(
            id=o["id"],
            metin=hazir.temiz_metin,
            tema=hazir.tema,
            guven=tema_siniflandir(o["metin"])["guven"],
            eslesen_ifadeler=tema_siniflandir(o["metin"])["eslesen_ifadeler"],
            tema_surumu=hazir.tema_surumu,
            onem_derecesi=hazir.onem_derecesi,
            cozum_durumu=hazir.cozum_durumu,
            dusuk_bilgi_supheli=hazir.dusuk_bilgi_supheli,
            yineleme_supheli=hazir.yineleme_supheli,
        ))
    return MusteriSesiOrnekYanit(temalar=veri["temalar"], ornekler=ornekler)


@app.get(
    "/musteri-sesi/yogunluk-ozeti",
    response_model=MusteriSesiYogunlukYanit,
    tags=["Musteri Sesi"],
)
def musteri_sesi_yogunluk_ozeti(kullanici: dict = Depends(token_dogrula)):
    """Gercek `sikayetler` tablosundan tema bazli gozlenen yogunluk.

    Faz 2 Hafta 1 - `campaign_experience_metrics` kapsaminda planlanan
    ozet gorunumu (bkz. docs/adr/0001-sikayet-veri-modeli.md). Izin kapisi
    (complaint/izin_kapisi.py) kapali oldugu surece tablo BOStur - bu
    durumda `toplam_sikayet: 0` doner, hata FIRLATILMAZ: bos veri gecerli
    ve dogru bir durumdur, "henuz veri yok" demek "sistem bozuk" demek
    degildir.

    `kapsam_durumu`: bos donusun IKI FARKLI sebebi olabilir - hicbir
    kaynak icin izin yoksa ("izin_yok") veya izin var ama henuz sikayet
    islenmemisse ("izin_var_veri_yok"). Bu ayrim, izin dosyasina
    kaynaktan bagimsiz bakan `herhangi_bir_izin_var_mi()` ile kurulur.
    """
    izin_var = herhangi_bir_izin_var_mi()
    oturum = next(oturum_al())
    try:
        sikayetler = oturum.query(Sikayet).all()
    finally:
        oturum.close()
    return MusteriSesiYogunlukYanit(**yogunluk_ozeti(sikayetler, izin_var=izin_var))


# "Cozum orani" icin ASGARI ornek sayisi - complaint/toplama.py::
# COZUM_ORANI_ASGARI_ORNEKLEM ile AYNI degerdir (tek tanim orada, DENETIM
# BULGUSU 27/28 Agustos 2026: asagidaki uc nokta payda>0 ise dogrudan oran
# uretiyordu - payda 1/2 iken "%0"/"%100" gibi kesin gorunen ama
# ISTATISTIKSEL OLARAK ANLAMSIZ bir sayi ureterek complaint/toplama.py::
# yogunluk_ozeti'nin kendi kirmizi cizgisini ihlal ediyordu).


@app.get(
    "/kampanyalar/{kampanya_id}/musteri-sesi-ozeti",
    response_model=KampanyaMusteriSesiOzeti,
    tags=["Musteri Sesi"],
)
def kampanya_musteri_sesi_ozeti(
    kampanya_id: int, kullanici: dict = Depends(token_dogrula)
):
    """Bir kampanyaya bağlı şikayetlerin özet metrikleri.

    Dashboard'da kampanya detay kartında "Müşteri Geri Bildirimi" bölümünde
    veya Etki Skoru kartında müşteri bileşeninde görünür. Ham şikâyet metinleri
    değil, anonimleştirilmiş içgörüler döner (rapor Bölüm 4).

    KAMPANYA EŞLEŞME KRİTERİ: `eslesen_kampanya_id == kampanya_id` VE
    `eslesme_guveni >= 0.50` (ASGARI_GUVEN). Daha düşük güvenli eşleşmeler
    "orta güven kuyruğu"na düşer, bu uç noktada sayılmaz.

    BOŞLUK GEÇERLİDİR: Hiç şikayet yoksa `toplam_sikayet: 0`, temalar/önem/
    çözüm boş dict döner - bu bir hata değil, "bu kampanyaya hiç şikayet
    bağlanmadı" durumudur (izin var ama o kampanya için veri yok).
    """
    oturum = next(oturum_al())
    try:
        from sqlalchemy import func
        from datetime import datetime, timezone

        # Kampanyaya eşleşen şikayetler (güven >= 0.50, None değil)
        sikayetler = (
            oturum.query(Sikayet)
            .filter(
                Sikayet.eslesen_kampanya_id == kampanya_id,
                Sikayet.eslesme_guveni >= 0.50,
            )
            .all()
        )

        if not sikayetler:
            return KampanyaMusteriSesiOzeti(
                kampanya_id=kampanya_id,
                toplam_sikayet=0,
                temalar={},
                onem_dagilimi={},
                cozum_dagilimi={},
                cozum_orani=None,
                ornek_metinler=[],
                veri_var=False,
            )

        # Tema dağılımı
        temalar: dict[str, int] = {}
        for s in sikayetler:
            tema_anahtar = s.tema or "SINIFLANDIRILAMADI"
            temalar[tema_anahtar] = temalar.get(tema_anahtar, 0) + 1

        # Önem dağılımı
        onem: dict[str, int] = {}
        for s in sikayetler:
            onem_anahtar = s.onem_derecesi or "ORTA"
            onem[onem_anahtar] = onem.get(onem_anahtar, 0) + 1

        # Çözüm dağılımı
        cozum: dict[str, int] = {}
        for s in sikayetler:
            cozum_anahtar = s.cozum_durumu or "bilinmiyor"
            cozum[cozum_anahtar] = cozum.get(cozum_anahtar, 0) + 1

        # Çözüm oranı: (çözüldü + kısmen) / (toplam - bilinmiyor). ASGARI
        # ornek sarti: bkz. yukaridaki COZUM_ORANI_ASGARI_ORNEKLEM notu.
        cozuldu = cozum.get("cozuldu", 0) + cozum.get("kismen", 0)
        payda = len(sikayetler) - cozum.get("bilinmiyor", 0)
        cozum_orani = (
            round(cozuldu / payda, 4)
            if payda >= COZUM_ORANI_ASGARI_ORNEKLEM
            else None
        )

        # Son 5 şikayet (özet)
        bugun = datetime.now(timezone.utc).date()
        son_sikayetler = sorted(sikayetler, key=lambda s: s.kayit_zamani, reverse=True)[:5]
        ornekler = []
        for s in son_sikayetler:
            gun_once = None
            if s.sikayet_tarihi:
                gun_once = (bugun - s.sikayet_tarihi).days
            ornekler.append(
                KampanyaMusteriSesiOrnegi(
                    id=s.id,
                    metin_ozet=s.temiz_metin[:150] + ("..." if len(s.temiz_metin) > 150 else ""),
                    tema=s.tema,
                    onem_derecesi=s.onem_derecesi or "ORTA",
                    cozum_durumu=s.cozum_durumu or "bilinmiyor",
                    sikayet_tarihi=s.sikayet_tarihi,
                    gun_once=gun_once,
                )
            )

        return KampanyaMusteriSesiOzeti(
            kampanya_id=kampanya_id,
            toplam_sikayet=len(sikayetler),
            temalar=temalar,
            onem_dagilimi=onem,
            cozum_dagilimi=cozum,
            cozum_orani=cozum_orani,
            ornek_metinler=ornekler,
            veri_var=True,
        )
    finally:
        oturum.close()


@app.get(
    "/musteri-sesi/istatistikler",
    response_model=MusteriSesiIstatistikler,
    tags=["Musteri Sesi"],
)
def musteri_sesi_istatistikler(kullanici: dict = Depends(token_dogrula)):
    """Dashboard ana sayfası Müşteri Sesi widget'i için özet metrikler.

    Tüm zamanın toplam istatistikleri (son 30 gün filtresi yok, çünkü
    henüz gerçek veri akışı başlamadı - tüm veriler sentetik ve az sayıda).
    Gerçek veri geldiğinde tarih filtresi parametre olarak eklenebilir.

    Hesaplama complaint/toplama.py::musteri_sesi_istatistiklerini_hesapla'da
    - agent/router.py::musteri_sesi_aracini_cagir de AYNI fonksiyonu
    dogrudan cagirir (28 Agustos 2026 duzeltmesi: eskiden bu uc noktaya
    kendi kendine HTTP istegi atardi, bkz. o fonksiyonun docstring'i).
    """
    izin_var = herhangi_bir_izin_var_mi()
    oturum = next(oturum_al())
    try:
        sikayetler = oturum.query(Sikayet).all()
    finally:
        oturum.close()
    return MusteriSesiIstatistikler(
        **musteri_sesi_istatistiklerini_hesapla(sikayetler, izin_var=izin_var)
    )


@app.get(
    "/musteri-sesi/sikayetler/{sikayet_id}",
    response_model=SikayetDetayYanit,
    tags=["Musteri Sesi"],
)
def sikayet_detay(sikayet_id: int, kullanici: dict = Depends(token_dogrula)):
    """Tek bir şikayetin detaylı bilgilerini döndürür.

    DENETIM BULGUSU (28 Agustos 2026): bu uc nokta MusteriSesiOrnek semasi
    kullanarak var OLMAYAN Sikayet alanlarina (onem_gerekcesi, cozum_gerekcesi,
    esleme_guveni - dogrusu eslesme_guveni) erisiyordu, ilk cagrida
    AttributeError ile 500 donuyordu. SikayetDetayYanit ile duzeltildi -
    bkz. o semanin docstring'i.
    """
    oturum = next(oturum_al())
    try:
        sikayet = oturum.query(Sikayet).filter(Sikayet.id == sikayet_id).first()

        if not sikayet:
            raise HTTPException(status_code=404, detail="Şikayet bulunamadı")

        return SikayetDetayYanit(
            id=sikayet.id,
            metin=sikayet.temiz_metin,
            tema=sikayet.tema,
            tema_surumu=sikayet.tema_surumu,
            onem_derecesi=sikayet.onem_derecesi,
            cozum_durumu=sikayet.cozum_durumu,
            dusuk_bilgi_supheli=sikayet.dusuk_bilgi_supheli or False,
            yineleme_supheli=sikayet.yineleme_supheli or False,
            insan_kontrolu_gerekir=sikayet.insan_kontrolu_gerekir or False,
            eslesen_kampanya_id=sikayet.eslesen_kampanya_id,
            eslesme_guveni=sikayet.eslesme_guveni,
        )
    finally:
        oturum.close()


@app.get(
    "/kampanyalar/{kampanya_id}/etki",
    response_model=EtkiSkoruYanit,
    tags=["Karsilastirma"],
)
def kampanya_etki_skoru(kampanya_id: int, kullanici: dict = Depends(token_dogrula)):
    """Kampanyanin etki skoru: piyasaya gore nerede duruyor?

    /karsilastir "hangisi daha ucuz?" sorusunu cevaplar; bu uc nokta
    "bu kampanya IYI bir kampanya mi?" sorusunu cevaplar - ayni turdeki
    aktif kampanyalar arasinda eksen eksen yuzdelik sira.

    Agirlikli formul KULLANILMAZ, kume kucukse skor URETILMEZ; gerekceler
    comparison/etki_skoru.py modul basliginda.
    """
    baslangic = time.time()

    if GERCEK_VERI_AKTIF:
        oturum = next(oturum_al())
        try:
            kayit = id_ile_getir_db(oturum, kampanya_id)
            tum_kayitlar = kampanyalari_getir_db(oturum) if kayit else []
        finally:
            oturum.close()
    else:
        kayit = id_ile_getir(kampanya_id)
        tum_kayitlar = kampanyalari_getir() if kayit else []

    if kayit is None:
        raise HTTPException(status_code=404, detail="Kampanya bulunamadi")

    sonuc = etki_skoru(kayit, tum_kayitlar)
    latency = int((time.time() - baslangic) * 1000)
    _audit_kaydet(kullanici, "etki-skoru", latency, cagrilan_arac="sql")

    # aciklama tamamen sabit Turkce sablonlardan uretilir (bkz.
    # comparison/etki_skoru.py) - /karsilastir ve /hesapla ile ayni
    # gerekceyle terminoloji kontrolu burada da uygulanir.
    aciklama = sonuc.get("aciklama")
    terminoloji_sonucu = (
        terminoloji_tutarliligini_kontrol_et(aciklama) if aciklama else None
    )

    return EtkiSkoruYanit(
        **sonuc,
        audit=_bos_audit(
            cagrilan_arac="sql",
            latency_ms=latency,
            sebep=aciklama,
            terminoloji_tutarli=(
                terminoloji_sonucu["tutarli"] if terminoloji_sonucu else None
            ),
            terminoloji_sorunlari=(
                terminoloji_sonucu["bulunan_sorunlar"] if terminoloji_sonucu else []
            ),
        ),
    )


@app.get(
    "/kampanyalar/{kampanya_id}/tarihce",
    response_model=TarihceYanit,
    tags=["Kampanyalar"],
)
def kampanya_tarihce(kampanya_id: int, kullanici: dict = Depends(token_dogrula)):
    """Kampanyanin zaman icindeki degisim tarihcesi (Sprint 5).

    DENETIM BULGUSU: scraper/scripts/kampanya_tarihcesi.py yazilip test
    edilmisti (README'de "Dunya Katilim'in bitis tarihi degisti" gibi
    somut bir ornekle anlatiliyor) ama hicbir uc noktaya baglanmamisti -
    chatbot/dashboard uzerinden bir kampanyanin gecmisini sormanin yolu
    yoktu. Ek veri toplamaz; scraper/raw_data'da zaten duran coklu-tarihli
    dosyalari okur (bkz. o modulun docstring'i).

    EK VERI TOPLAMAZ - regex tabanli (hizli, deterministik) oldugu icin
    hibrit cikarimla (Yagmur'un DB'ye yazdigi NIHAI degerler) birebir
    ayni sayilari VERMEYEBILIR; trend/degisim icin yaklasik dogru yeterli
    (bkz. kampanya_tarihcesi.py "NEDEN HIBRIT DEGIL REGEX").
    """
    baslangic = time.time()

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

    tarihce = tarihce_getir(kayit.kaynak_url)
    degisenler = degisen_alanlari_bul(tarihce)

    latency = int((time.time() - baslangic) * 1000)
    _audit_kaydet(kullanici, "tarihce", latency, cagrilan_arac="sql")

    return TarihceYanit(
        kampanya_id=kampanya_id,
        banka=kayit.banka,
        kampanya_adi=kayit.kampanya_adi,
        kaynak_url=kayit.kaynak_url,
        tarihce=tarihce,
        degisen_alanlar=degisenler,
        audit=_bos_audit(cagrilan_arac="sql", latency_ms=latency),
    )


@app.get("/rakip-analizi", response_model=RakipAnaliziYanit, tags=["Karsilastirma"])
def rakip_analizi(
    kampanya_turu: str | None = Query(
        None, description="Kampanya turune gore suz (bos birakilirsa tum turler)"
    ),
    yalnizca_aktif: bool = Query(True, description="Yalnizca ACTIVE kampanyalar"),
    kullanici: dict = Depends(token_dogrula),
):
    """Bir kampanya turundeki tum kampanyalari eksen eksen yan yana koyar.

    /karsilastir TEK bir kritere gore siralar ve secilmis id'ler ister;
    bu uc nokta TUM kriterleri tek tabloda, tum kampanyalar icin gosterir
    (Sartname Md. 5.7 - "farkli katilim bankalarina ait urunlerin
    karsilastirilabilir hale getirilmesi").

    Kampanyalar tek satira SIKISTIRILMAZ: bir bankanin ayni turde iki
    kampanyasi varsa iki satir doner. Gerekcesi
    comparison/compare_engine.py::rakip_matrisi docstring'inde.
    """
    baslangic = time.time()

    if GERCEK_VERI_AKTIF:
        oturum = next(oturum_al())
        try:
            kayitlar = kampanyalari_getir_db(oturum, kampanya_turu=kampanya_turu)
        finally:
            oturum.close()
    else:
        kayitlar = kampanyalari_getir(kampanya_turu=kampanya_turu)

    sonuc = rakip_matrisi(
        kayitlar, kampanya_turu=kampanya_turu, yalnizca_aktif=yalnizca_aktif
    )

    latency = int((time.time() - baslangic) * 1000)
    _audit_kaydet(kullanici, "rakip-analizi", latency, cagrilan_arac="sql")
    return RakipAnaliziYanit(
        **sonuc,
        audit=_bos_audit(cagrilan_arac="sql", latency_ms=latency),
    )


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
    _audit_kaydet(
        kullanici, "karsilastir", latency, cagrilan_arac="sql", sql_sorgusu=sql
    )

    # Md. 5.5 - Karsilastirma ciktisi tamamen sabit Turkce sablonlardan
    # uretilir (LLM/kazinmis metin karismaz), ama denetim yine de burada
    # yapilir: AuditBilgisi'nin kendi tasarim ilkesiyle ayni ("Hesaplama/
    # Karsilastirma'da gercek True/False", bkz. api/schemas.py) - yalnizca
    # /chat'in orkestrator yoluna degil, dashboard'un dogrudan cagirdigi
    # bu uc noktaya da uygulanir.
    aciklama = aciklama_uret(sonuc)
    terminoloji_sonucu = terminoloji_tutarliligini_kontrol_et(aciklama)

    return KarsilastirYanit(
        kriter=istek.kriter,
        sonuclar=sonuc["sonuclar"],
        calistirilan_sql=sql,
        audit=_bos_audit(
            cagrilan_arac="sql",
            latency_ms=latency,
            sql_sorgusu=sql,
            sebep=aciklama,
            terminoloji_tutarli=terminoloji_sonucu["tutarli"],
            terminoloji_sorunlari=terminoloji_sonucu["bulunan_sorunlar"],
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
    _audit_kaydet(kullanici, "hesapla", latency, cagrilan_arac="calculator")

    ozet = sonuc.ozet_metni()
    terminoloji_sonucu = terminoloji_tutarliligini_kontrol_et(ozet)

    return HesapYanit(
        anapara=sonuc.anapara,
        aylik_oran_percent=istek.aylik_oran_percent,
        vade_ay=sonuc.vade_ay,
        aylik_taksit=sonuc.aylik_taksit,
        toplam_odeme=sonuc.toplam_odeme,
        toplam_kar_payi=sonuc.toplam_kar_payi,
        ozet=ozet,
        odeme_plani=plan,
        audit=_bos_audit(
            cagrilan_arac="calculator",
            latency_ms=latency,
            response_confidence=1.0,  # deterministik hesap - belirsizlik yok
            sebep="Saf Python hesabi, LLM kullanilmadi",
            terminoloji_tutarli=terminoloji_sonucu["tutarli"],
            terminoloji_sorunlari=terminoloji_sonucu["bulunan_sorunlar"],
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
    _audit_kaydet(
        kullanici,
        "chat",
        ekstra["latency_ms"],
        soru=istek.soru,
        intent=ekstra["intent"],
        intent_confidence=ekstra["intent_confidence"],
        cagrilan_arac=ekstra["cagrilan_arac"],
        sql_sorgusu=ekstra["sql_sorgusu"],
    )

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
            dogrulama=ekstra["dogrulama"],
            sql_sorgusu=ekstra["sql_sorgusu"],
            terim_agirliklari=ekstra["terim_agirliklari"] or [],
        ),
    )


@app.post("/chat/stream", tags=["Chatbot"])
async def chat_stream(istek: ChatIstek, kullanici: dict = Depends(token_dogrula)):
    """SSE ile token token streaming yanit - demo canli his icin.

    TASARIM NOTU (demo gercekligi): agent/orchestrator.py::soru_isle
    sync bir fonksiyon oldugundan gercek LLM token streaming'i burada
    mumkun degil (orchestrator async generator'a donusturulmeli - P1).

    DEMO ICIN - Sahte streaming (Secenek B):
      Sync cevap alindiktan sonra kelime kelime SSE ile gonderilir.
      Juri gozunden: cevap ekranda canli yaziliyor gibi gorukur.
      Teknik gozunden: LLM cevabi hala tek seferde hesaplaniyor.

    SSE formati:
      data: {"token": "kelime "}   - her kelime icin
      data: {"done": true, "audit": {...}, "kaynaklar": [...], "fallback": bool}

    Frontend EventSource veya fetch + ReadableStream ile baglanir.
    """
    log.info(
        "chat/stream sorgusu | kullanici=%s | soru=%s",
        kullanici.get("kullanici"), istek.soru,
    )

    # Orchestrator cevabi hesapla (sync)
    sonuc = soru_isle(istek.soru, _banka_kayitlarini_getir)
    ekstra = sonuc["audit_ekstra"]

    # DB audit yaz (sync cagri ile ayni)
    _audit_kaydet(
        kullanici,
        "chat_stream",
        ekstra["latency_ms"],
        soru=istek.soru,
        intent=ekstra["intent"],
        intent_confidence=ekstra["intent_confidence"],
        cagrilan_arac=ekstra["cagrilan_arac"],
        sql_sorgusu=ekstra["sql_sorgusu"],
    )

    audit = _bos_audit(
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
        dogrulama=ekstra["dogrulama"],
        sql_sorgusu=ekstra["sql_sorgusu"],
        terim_agirliklari=ekstra["terim_agirliklari"] or [],
    )

    cevap = sonuc["cevap"]

    # KAYNAKLAR AKIS BASLAMADAN ONCE HAZIRLANIR.
    #
    # Hata 1 (olculdu): `sonuc["kaynaklar"]` bir Kaynak listesi DEGIL, duz
    # dict listesidir - /chat onlari ChatYanit'a verip Pydantic'e dogrulatir.
    # Burada dogrudan `k.model_dump()` cagriliyordu ve akis her istekte
    # AttributeError ile patliyordu. Uc nokta vardi ama calismiyordu.
    #
    # Hata 2 (ayni satirin ikinci tuzagi): bu is jenerator'un ICINDE
    # yapilirsa hata akis basladiktan SONRA olusur - HTTP durum kodu coktan
    # 200 gonderilmistir, istemci hatayi goremez, yalnizca yarim kalmis bir
    # akis gorur. Bu yuzden dogrulama BURADA, yanit donmeden yapilir:
    # bozuk veri duzgun bir 500 uretir.
    #
    # Dogrulamadan gecirmek (ham dict'i oldugu gibi yollamak yerine) iki
    # ucun AYNI semayi uygulamasini garanti eder; aksi halde /chat ile
    # /chat/stream'in kaynak nesneleri sessizce birbirinden ayrilirdi.
    kaynaklar_json = [Kaynak.model_validate(k).model_dump() for k in sonuc["kaynaklar"]]
    audit_json = audit.model_dump()

    async def jenerator():
        # Kelime kelime gonder - canli yazma hissi
        kelimeler = cevap.split(" ")
        for i, kelime in enumerate(kelimeler):
            parca = kelime + (" " if i < len(kelimeler) - 1 else "")
            yield f"data: {json.dumps({'token': parca}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.03)  # ~30ms - gercekci his, demo'da yeterli

        # Tamamlandi: audit + kaynaklar + fallback
        tamamlandi = {
            "done": True,
            "audit": audit_json,
            "kaynaklar": kaynaklar_json,
            "fallback": sonuc["fallback"],
        }
        yield f"data: {json.dumps(tamamlandi, ensure_ascii=False, default=str)}\n\n"

    return StreamingResponse(
        jenerator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.get(
    "/audit/extraction/{kampanya_id}",
    tags=["Denetim"],
)
def extraction_audit(
    kampanya_id: int,
    kullanici: dict = Depends(
        rol_gerekli(["banka_calisani", "denetleyici", "yonetici"])
    ),
):
    """Bir kampanya icin cikarim katman izlerini gosterir.

    ExtractionAudit sayfasi (Juri Audit - "hangi katman ne deger verdi?")
    icin tasarlanmistir. CampaignRecord'daki mevcut degerleri
    CikarimIzi formatinda dondurur.

    NOT: Bu uc nokta ham kaynak metni yeniden taramaz - DB'deki mevcut
    cikarim sonuclari kullanilir (cikarim_yontemi + confidence alanlari).
    Ham metin tarama gerektiren tam iz: POST /cikar (hibrit=false).

    ROL KISITI: yalnizca banka_calisani/denetleyici/yonetici -
    musteri rolu icin cikarim motoru ic/analiz araci.
    """
    baslangic = time.time()

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

    # CampaignRecord'daki sayisal alanlar + cikarim bilgileri
    IZLENECEK_ALANLAR = [
        ("kar_payi_orani_percent", "Kar Payi Orani (%)", "aylik yuzde"),
        ("vade_ay", "Vade (Ay)", "ay"),
        ("finansman_tutari", "Finansman Tutari (TL)", "TL"),
        ("taksit_sayisi", "Taksit Sayisi", "adet"),
        ("erteleme_suresi_ay", "Erteleme Suresi (Ay)", "ay"),
        ("tahsis_ucreti", "Tahsis Ucreti (TL)", "TL"),
        ("odul_miktari", "Odul Miktari", None),
    ]

    cikarim_yontemi = (
        kayit.cikarim_yontemi.value if kayit.cikarim_yontemi else "regex"
    )
    genel_guven = kayit.confidence

    alanlar = []
    for alan_adi, alan_label, birim in IZLENECEK_ALANLAR:
        deger = getattr(kayit, alan_adi, None)
        belirtilmemis = kayit.alan_belirtilmemis.get(alan_adi, False)
        dogrulandi = kayit.dogrulanan_alanlar.get(alan_adi)

        alanlar.append({
            "alan": alan_adi,
            "label": alan_label,
            "birim": birim,
            "mevcut_deger": deger,
            "belirtilmemis": belirtilmemis,
            "katmanlar": [
                {
                    "katman": cikarim_yontemi,
                    "deger": str(deger) if deger is not None else None,
                    "confidence": genel_guven if deger is not None else None,
                    "evidence": None,  # ham metin bu uc noktada mevcut degil
                }
            ] if deger is not None else [],
            "resolver": {
                "secilen": cikarim_yontemi,
                "sebep": "tek_katman",
                "deger": str(deger) if deger is not None else None,
            },
            # gold_dataset klasoru icin: gold_dataset/gold_records.json
            "gold_reference": _gold_referans_bul(kampanya_id, alan_adi),
            "dogrulandi": dogrulandi,
        })

    latency = int((time.time() - baslangic) * 1000)
    _audit_kaydet(
        kullanici, "extraction-audit", latency, cagrilan_arac="extraction"
    )

    return {
        "kampanya_id": kampanya_id,
        "banka": kayit.banka,
        "kampanya_adi": kayit.kampanya_adi,
        "kaynak_url": kayit.kaynak_url,
        "cikarim_yontemi": cikarim_yontemi,
        "genel_guven": genel_guven,
        "alanlar": alanlar,
        "audit": _bos_audit(
            cagrilan_arac="extraction", latency_ms=latency
        ).model_dump(),
    }


def _gold_referans_bul(kampanya_id: int, alan_adi: str) -> dict | None:
    """gold_dataset/gold_records.json'dan kampanya + alan icin referans deger arar.

    Dosya yoksa ya da kayit bulunamazsa None doner - uydurulmaz.
    Gold kayit yapisi: [{"kampanya_id": 1, "alan": "kar_payi_orani_percent",
                         "deger": "1.89", "dogrulandi": true}, ...]
    """
    gold_dosya = Path(__file__).resolve().parent.parent / "gold_dataset" / "gold_records.json"
    if not gold_dosya.exists():
        return None
    try:
        with open(gold_dosya, encoding="utf-8") as f:
            kayitlar = json.load(f)
        for kayit in kayitlar:
            if kayit.get("kampanya_id") == kampanya_id and kayit.get("alan") == alan_adi:
                return {
                    "deger": kayit.get("deger"),
                    "dogrulandi": kayit.get("dogrulandi", False),
                }
    except (OSError, json.JSONDecodeError, KeyError):
        log.warning(
            "Gold referans okunamadi | kampanya_id=%s | alan=%s",
            kampanya_id, alan_adi, exc_info=True,
        )
    return None

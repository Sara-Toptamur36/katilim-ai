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

import json
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from agent.orchestrator import soru_isle
from api.auth import GERCEK_JWT_AKTIF, rol_gerekli, token_dogrula, token_uret
from complaint.tema_siniflandirici import tema_siniflandir
from api.db import oturum_al
from api.kampanya_repository import id_ile_getir_db, kampanyalari_getir_db
from api.kullanici_repository import kullanici_dogrula, kullanici_getir, kullanici_olustur
from api.logging_config import log
from api.mock_data import id_ile_getir, kampanyalari_getir
from api.models import AuditKayit
from api.schemas import (
    AuditBilgisi,
    CampaignRecord,
    ChatIstek,
    ChatYanit,
    HesapIstek,
    HesapYanit,
    KarsilastirIstek,
    KarsilastirYanit,
    KayitIstek,
    KayitYanit,
    MusteriSesiIstek,
    MusteriSesiOrnek,
    MusteriSesiOrnekYanit,
    MusteriSesiYanit,
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

# Faz 1 T8 - sentetik musteri sesi demo verisi (urun verisi DEGIL, bkz.
# complaint/tema_siniflandirici.py modul basligi).
SENTETIK_MUSTERI_SESI_YOLU = (
    Path(__file__).resolve().parent.parent
    / "tests" / "veri" / "kapsam_disi" / "sentetik_musteri_sesi.json"
)

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
    """
    with open(SENTETIK_MUSTERI_SESI_YOLU, encoding="utf-8") as f:
        veri = json.load(f)

    ornekler = [
        MusteriSesiOrnek(id=o["id"], metin=o["metin"], **tema_siniflandir(o["metin"]))
        for o in veri["ornekler"]
    ]
    return MusteriSesiOrnekYanit(temalar=veri["temalar"], ornekler=ornekler)


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
        ),
    )

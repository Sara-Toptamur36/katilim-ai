"""SQLAlchemy veritabani modelleri (Alembic migration'lari bunlari izler).

NEDEN ORM + MIGRATION: Sprint 2'de semaya yeni bir sutun eklemek gerektiginde,
tabloyu elle silip yeniden kurmak Zeynep'in topladigi TUM gercek veriyi yok
eder. Alembic, degisikligi veriyi koruyarak uygular ve surumler.

Sema degistiren kisi migration dosyasini da commit'ler; digerleri `git pull`
sonrasi `alembic upgrade head` calistirir.
"""

from sqlalchemy import Boolean, Column, Date, DateTime, Float, Integer, JSON, String, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Kampanya(Base):
    """CampaignRecord'un veritabani karsiligi (bkz. api/schemas.py)."""

    __tablename__ = "kampanyalar"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Kimlik
    banka = Column(String(100), nullable=False, index=True)
    kampanya_adi = Column(String(300), nullable=False)
    kampanya_turu = Column(String(100), index=True)

    # Finansal (yuzde IKILI saklanir - rapor Bolum 5.1)
    kar_payi_orani_percent = Column(Float, nullable=True)
    kar_payi_orani_decimal = Column(Float, nullable=True)
    vade_ay = Column(Integer, nullable=True)
    finansman_tutari = Column(Float, nullable=True)

    # Vade/taksit/erteleme UC AYRI kavramdir - gercek banka verisiyle
    # dogrulandi (ornek: "2 ay ertelemeli ... 12 aya varan taksit" hicbir
    # yerde klasik "vade" ifadesi gecmez). Bunlari vade_ay'a sikistirmak
    # yanlis veri uretir (Yagmur, extraction/regex_extractor.py).
    taksit_sayisi = Column(Integer, nullable=True)
    erteleme_suresi_ay = Column(Integer, nullable=True)

    # Odul / avantaj
    odul_miktari = Column(Float, nullable=True)
    odul_birimi = Column(String(50), nullable=True)
    kampanya_avantaji = Column(String(1000), nullable=True)
    masraf_durumu = Column(String(300), nullable=True)
    tahsis_ucreti = Column(Float, nullable=True)

    # Yasam dongusu
    kampanya_baslangic = Column(Date, nullable=True)
    kampanya_bitis = Column(Date, nullable=True)
    durum = Column(String(20), default="BILINMIYOR", index=True)

    # Hedef kitle
    hedef_kitle = Column(String(300), nullable=True)

    # Izlenebilirlik (rapor Bolum 9)
    kaynak_url = Column(String(700), nullable=False)
    belge_tarihi = Column(Date, nullable=True)
    confidence = Column(Float, default=0.0)
    cikarim_yontemi = Column(String(20), nullable=True)

    # Seffaflik bayragi: {"odul_miktari": true} gibi
    alan_belirtilmemis = Column(JSON, default=dict)

    # Verifier sonucu (validation/verifier.py): {"kar_payi_orani_percent": true}
    # gibi - o alanin kaynak metinde (deger + baglam) dogrulanip dogrulanmadigi.
    # ONCEDEN yalnizca log dosyasina yaziliyordu (goruntulenemez, sorgulanamaz);
    # artik kalici - dashboard/API bir alanin "kaynakta dogrulandi mi" bilgisini
    # gosterebilsin diye (bkz. extraction/regex_ile_zenginlestir.py).
    dogrulanan_alanlar = Column(JSON, default=dict)

    # Kaynak sayfada Rehber Bolum 18 tarzi bir "Kâr Payı Oranları" tablosu
    # varsa OLDUGU GIBI (vade/tutar kirilimi korunarak) burada saklanir -
    # extraction/tablo_extractor.py TEK bir sayiya indirgemez (bkz. o
    # modulun docstring'i), bu yuzden kar_payi_orani_percent'ten AYRI bir
    # alan. None = sayfada boyle bir tablo yok (extraction/
    # regex_ile_zenginlestir.py).
    kar_payi_tablosu = Column(JSON, nullable=True)

    # Kayit izleri
    olusturulma = Column(DateTime(timezone=True), server_default=func.now())
    guncellenme = Column(DateTime(timezone=True), onupdate=func.now())


class Kullanici(Base):
    """Gercek JWT girisi icin kullanici kaydi (rapor Bolum 11 - RBAC).

    GUVENLIK: Duz metin parola HICBIR ZAMAN saklanmaz - yalnizca bcrypt
    hash'i (bkz. api/auth.py sifre_hashle/sifre_dogrula).
    """

    __tablename__ = "kullanicilar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kullanici_adi = Column(String(100), nullable=False, unique=True, index=True)
    sifre_hash = Column(String(100), nullable=False)
    rol = Column(String(50), nullable=False, default="banka_calisani")
    aktif = Column(Boolean, default=True)
    olusturulma = Column(DateTime(timezone=True), server_default=func.now())


class AuditKayit(Base):
    """Audit log (rapor Bolum 11): kim, ne zaman, hangi sorguyu calistirdi.

    Juri Audit Paneli ile ortak altyapiyi kullanir.
    GUVENLIK: Bu tabloya token/parola YAZILMAZ.
    """

    __tablename__ = "audit_kayitlari"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kullanici = Column(String(100), index=True)
    rol = Column(String(50), nullable=True)
    uc_nokta = Column(String(100))
    soru = Column(String(1000), nullable=True)
    intent = Column(String(50), nullable=True)
    intent_confidence = Column(Float, nullable=True)
    cagrilan_arac = Column(String(50), nullable=True)
    sql_sorgusu = Column(String(2000), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    cache_hit = Column(Boolean, default=False)
    zaman = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class Sikayet(Base):
    """Musteri sikayeti (Complaint Insight).

    KIRMIZI CIZGI (Rehber_Zeynep_Veri.md): "Sikayet verisi kampanya
    tablosuna ve RAG indeksine KARISMAZ. Ayri tablo, ayri indeks, ayri
    etiket." Bu yuzden `kampanyalar` tablosuna bir FOREIGN KEY BILEREK
    KONULMADI - eslesme, silinebilir/duzeltilebilir bir HIPOTEZDIR
    (bkz. complaint/kampanya_eslestirme.py), veritabani seviyesinde
    dayatilan bir gercek degil. FK koymak, dusuk guvenli bir tahmini
    semanin garantisi gibi gosterirdi.

    HAM METIN YOKTUR: yalnizca `temiz_metin` saklanir. PII temizligi
    KAYITTAN ONCE yapilir (complaint/pii_temizleme.py); ham metin hicbir
    asamada diske yazilmaz.
    """

    __tablename__ = "sikayetler"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # --- Icerik (yalnizca temizlenmis) ---
    temiz_metin = Column(String(4000), nullable=False)
    pii_bulundu = Column(Boolean, default=False)
    insan_kontrolu_gerekir = Column(Boolean, default=False, index=True)

    # --- Siniflandirma (complaint/tema_siniflandirici.py) ---
    tema = Column(String(50), nullable=True, index=True)
    tema_kaniti = Column(String(200), nullable=True)

    # --- Kaynak ve izin izi ---
    # Hangi izin kaydiyla toplandigi saklanir: denetimde "bu satir hangi
    # onaya dayaniyor?" sorusunun cevabi kaydin kendisinde olmali.
    kaynak = Column(String(100), nullable=False, index=True)
    izin_onaylayan = Column(String(100), nullable=True)
    izin_onay_tarihi = Column(Date, nullable=True)

    # --- Kampanya eslesmesi (HIPOTEZ - bkz. sinif docstring'i) ---
    eslesen_kampanya_id = Column(Integer, nullable=True, index=True)
    eslesme_guveni = Column(Float, nullable=True)
    eslesme_gerekcesi = Column(JSON, nullable=True)

    sikayet_tarihi = Column(Date, nullable=True, index=True)
    kayit_zamani = Column(DateTime(timezone=True), server_default=func.now())

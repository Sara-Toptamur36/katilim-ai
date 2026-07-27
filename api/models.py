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

    # Kayit izleri
    olusturulma = Column(DateTime(timezone=True), server_default=func.now())
    guncellenme = Column(DateTime(timezone=True), onupdate=func.now())


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

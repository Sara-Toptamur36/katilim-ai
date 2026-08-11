"""API sozlesmesi: istek/yanit semalari.

Bu dosya ekibin ORTAK SOZLESMESIDIR:
  - Yagmur cikarim motorunu bu semaya gore doldurur
  - Sara karsilastirma/ajan mantigini bu sema uzerinde calistirir
  - Havin arayuzu bu alan adlarina gore kurar

Alan adlari degistirilecekse ONCE ekiple konusulur (Havin'in kodu bozulur).

Kaynak: On Degerlendirme Raporu Bolum 15 (CampaignRecord) + sartname Md. 5.3
"""

from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class KampanyaTuru(str, Enum):
    """Sartname Md. 5.4'teki ornek kampanya turleri."""

    KONUT = "Konut Finansmani Kampanyasi"
    IHTIYAC = "Ihtiyac Finansmani Kampanyasi"
    TASIT = "Tasit Finansmani Kampanyasi"
    FINANSMAN = "Finansman Kampanyasi"
    KART = "Kart Kampanyasi"
    ALISVERIS_PUANI = "Alisveris Puani Kampanyasi"
    YENI_MUSTERI = "Yeni Musteri Kampanyasi"
    YATIRIM = "Yatirim Urunu Kampanyasi"
    BELIRSIZ = "Belirlenemedi"


class YasamDongusu(str, Enum):
    """Kampanyanin guncellik durumu (rapor Bolum 15)."""

    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    BILINMIYOR = "BILINMIYOR"


class CikarimYontemi(str, Enum):
    """Bir alanin hangi yontemle cikarildigi (rapor Bolum 9 - izlenebilirlik)."""

    REGEX = "regex"
    NER = "ner"
    LLM = "llm"
    TABLO = "tablo"
    MANUEL = "manuel"


class CampaignRecord(BaseModel):
    """Tek bir kampanyanin yapilandirilmis kaydi.

    TASARIM ILKESI (rapor Bolum 5.7 / 15): Eksik veri GIZLENMEZ, isaretlenir.
    Bir alan bulunamadiysa None birakilir ve `alan_belirtilmemis` icinde
    True olarak bayraklanir. Karsilastirmada NULLS LAST ile en sona gider.
    """

    id: int | None = None

    # --- Kimlik ---
    banka: str = Field(..., description="Banka adi (BDDK SEED listesinden)")
    kampanya_adi: str = Field(..., description="Kampanya/urun basligi")
    kampanya_turu: KampanyaTuru = KampanyaTuru.BELIRSIZ

    # --- Finansal bilgiler ---
    # Yuzde alani IKILI saklanir (rapor Bolum 5.1 notu): formul karisikligini onler
    kar_payi_orani_percent: float | None = Field(
        None, description="Ornek: 1.89  (yani %1,89)"
    )
    kar_payi_orani_decimal: float | None = Field(
        None, description="Ornek: 0.0189 (hesaplamalarda kullanilir)"
    )
    vade_ay: int | None = Field(None, description="Standart ay cinsinden vade")
    finansman_tutari: float | None = Field(None, description="TL cinsinden")

    # Vade/taksit/erteleme UC AYRI kavramdir (regex_extractor gercek veriyle
    # dogruladi: "12 aya varan taksit" vade degildir; "2 ay ertelemeli"
    # de ayrica farkli bir kavramdir - bkz. extraction/regex_extractor.py)
    taksit_sayisi: int | None = Field(None, description="Ornek: 12 (vade DEGIL, taksit adedi)")
    erteleme_suresi_ay: int | None = Field(None, description="Odemesiz donem, ornek: 2 ay ertelemeli")

    # --- Odul / avantaj ---
    odul_miktari: float | None = None
    odul_birimi: str | None = Field(
        None, description="Mil / Gram / Puan / TL gibi farkli birimler"
    )
    kampanya_avantaji: str | None = Field(
        None, description="Sartname Md. 5.3 - serbest metin avantaj aciklamasi"
    )
    masraf_durumu: str | None = Field(
        None, description="Ornek: 'Dosya masrafi yok' / 'Belirtilmemis'"
    )
    tahsis_ucreti: float | None = None

    # --- Yasam dongusu ---
    kampanya_baslangic: date | None = None
    kampanya_bitis: date | None = None
    durum: YasamDongusu = YasamDongusu.BILINMIYOR

    # --- Hedef kitle ---
    hedef_kitle: str | None = Field(None, description="Yeni musteri, maas musterisi vb.")

    # --- Izlenebilirlik (rapor Bolum 9) ---
    kaynak_url: str = Field(..., description="Provenance: bilginin geldigi sayfa")
    belge_tarihi: date | None = Field(None, description="Sayfanin son tarandigi tarih")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Extraction Confidence")
    cikarim_yontemi: CikarimYontemi | None = None

    # --- Seffaflik bayragi (rapor Bolum 15) ---
    alan_belirtilmemis: dict[str, bool] = Field(
        default_factory=dict,
        description="Ornek: {'odul_miktari': True} - eksik veri gizlenmez, isaretlenir",
    )


# ---------------------------------------------------------------------------
# Istek semalari
# ---------------------------------------------------------------------------


class KarsilastirIstek(BaseModel):
    ids: list[int] = Field(..., min_length=2, description="En az 2 kampanya secilmeli")
    kriter: str = Field(
        "en_dusuk_kar_payi",
        description=(
            "en_dusuk_kar_payi | en_yuksek_odul | en_uzun_vade | en_dusuk_masraf | "
            "en_avantajli (Sartname Md. 5.7 kompozit kriteri) | en_yuksek_tutar (bonus)"
        ),
    )


class TokenYanit(BaseModel):
    """POST /token yaniti - GERCEK_JWT_AKTIF modunda kullanilir."""

    access_token: str
    token_type: str = "bearer"


class ChatIstek(BaseModel):
    soru: str = Field(..., min_length=1, max_length=500)


class HesapIstek(BaseModel):
    """Taksit hesabi istegi.

    ORAN BIRIMI: aylik_oran_percent AYLIK orandir (ornek: 1.89 = ayda %1,89).
    CampaignRecord'daki kar_payi_orani_percent alani ile ayni birimdedir.
    """

    anapara: float = Field(..., gt=0, le=100_000_000, description="TL cinsinden")
    aylik_oran_percent: float = Field(
        ..., ge=0, le=20, description="Aylik kar payi orani, ornek: 1.89"
    )
    vade_ay: int = Field(..., gt=0, le=480)
    odeme_plani_istiyor: bool = Field(
        False, description="True ise ay ay odeme plani da doner"
    )


class OdemeSatiriYanit(BaseModel):
    ay: int
    taksit: float
    kar_payi_kismi: float
    anapara_kismi: float
    kalan_bakiye: float


class HesapYanit(BaseModel):
    anapara: float
    aylik_oran_percent: float
    vade_ay: int
    aylik_taksit: float
    toplam_odeme: float
    toplam_kar_payi: float
    ozet: str
    yontem: str = Field(
        "deterministik_python",
        description="Hesap LLM'e birakilmaz - saf Python fonksiyonu",
    )
    odeme_plani: list[OdemeSatiriYanit] = Field(default_factory=list)
    audit: "AuditBilgisi | None" = None


# ---------------------------------------------------------------------------
# Yanit semalari
# ---------------------------------------------------------------------------


class Kaynak(BaseModel):
    """Bir cevabin dayandigi kaynak (rapor Bolum 9 - Provenance).

    `metin`, RAG'in bulup BIREBIR dondurdugu kaynak parcasidir. Alan
    eksikti: agent/router.py bu degeri zaten uretiyordu ama semada
    karsiligi olmadigi icin Pydantic tarafindan SESSIZCE dusuruluyordu -
    yani "her cumle bir kaynak belgeden gelir" iddiasinin kaniti
    arayuze hic ulasmiyordu.
    """

    banka: str | None = None
    kampanya_adi: str | None = None
    kaynak_url: str | None = None
    belge_tarihi: date | None = None
    chunk_id: str | None = None
    similarity_score: float | None = None
    metin: str | None = Field(
        None, description="Kaynak parcanin birebir metni (RAG yanitlarinda dolu)"
    )


class RetrieverSonuc(BaseModel):
    chunk_id: str
    similarity_score: float | None = None
    rerank_score: float | None = None
    metin_ozeti: str | None = None


class TerminolojiSorunu(BaseModel):
    """agent/orchestrator.py::terminoloji_tutarliligini_kontrol_et'in
    bulunan_sorunlar cikti sekliyle AYNI (Md. 5.5)."""

    gelenek_terim: str
    onerilen: str


class AuditBilgisi(BaseModel):
    """Juri Audit Paneli'nin (rapor Bolum 10.2) ihtiyac duydugu TUM alanlar.

    ONEMLI: Bu blok ilk gunden /chat yanitinda bulunur - alanlar bos olsa bile.
    Havin arayuzu bu alan adlarina gore kurar; sonradan isim degistirmek
    onun kodunu bozar.
    """

    intent: str | None = None
    intent_confidence: float | None = None
    cagrilan_arac: str | None = None
    sql_sorgusu: str | None = None
    retriever_sonuclari: list[RetrieverSonuc] = Field(default_factory=list)
    extraction_confidence: float | None = None
    response_confidence: float | None = None
    regex_basari_orani: float | None = None
    latency_ms: int | None = None
    cache_hit: bool = False
    model: str | None = None
    temperature: float | None = None
    sebep: str | None = Field(None, description="Fallback'e dusuldiyse nedeni")
    # Md. 5.5 - agent/orchestrator.py::_TERMINOLOJI_BILGI_NOTU_ARACLARI ile
    # AYNI kural: RAG/Sozluk'te "uygulanamaz" (None, gelenek terim mesru
    # olabilir - kaynak alintisi/gelenek karsiligi ogretimi), Hesaplama/
    # Karsilastirma'da gercek True/False.
    terminoloji_tutarli: bool | None = None
    terminoloji_sorunlari: list[TerminolojiSorunu] = Field(default_factory=list)


class ChatYanit(BaseModel):
    cevap: str
    kaynaklar: list[Kaynak] = Field(default_factory=list)
    confidence: float = 0.0
    fallback: bool = False
    audit: AuditBilgisi


class KarsilastirYanit(BaseModel):
    kriter: str
    sonuclar: list[dict[str, Any]] = Field(default_factory=list)
    calistirilan_sql: str | None = None
    audit: AuditBilgisi | None = None

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
    # Birden fazla katmanin (regex + NER/LLM) katkisiyla doldurulmus kayit.
    # extraction/regex_ile_zenginlestir.py bu degeri BILEREK yaziyordu ama
    # enum'da karsiligi yoktu: GERCEK_VERI_AKTIF=true iken /kampanyalar,
    # boyle 16 kaydin bulundugu veritabaninda ValidationError ile
    # patliyordu. Yazan taraf dogruydu - eksik olan buydu.
    HIBRIT = "hibrit"


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
    kar_payi_tablosu: list[dict] | None = Field(
        None,
        description=(
            "Kaynak sayfada Rehber Bolum 18 tarzi bir vade/tutar kirilimli "
            "'Kâr Payı Oranları' tablosu varsa OLDUGU GIBI (satir/sutun "
            "yapisi korunarak) burada tasinir - kar_payi_orani_percent TEK "
            "bir sayidir ve boyle bir tablo genellikle TEK sayiya "
            "indirgenemeyecek kadar cok degiskenlidir (bkz. extraction/"
            "tablo_extractor.py docstring'i), bu yuzden ayri alan. "
            "None = kaynakta boyle bir tablo bulunamadi."
        ),
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

    # --- Verifier sonucu (validation/verifier.py) ---
    dogrulanan_alanlar: dict[str, bool] = Field(
        default_factory=dict,
        description=(
            "Ornek: {'kar_payi_orani_percent': True} - o alanin kaynak metinde "
            "(deger + baglam) Verifier tarafindan dogrulanip dogrulanmadigi. "
            "Alan burada YOKSA o alan icin Verifier hic calistirilmamis demektir "
            "(ör. deger zaten onceden doluydu, uzerine yazilmadi) - False ile "
            "karistirilmamalidir."
        ),
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
    rol: str = Field(
        ..., description="Arayuzun menuyu role gore cizebilmesi icin (ör. musteri 3 ekran gorur)"
    )


class KayitIstek(BaseModel):
    """POST /kayit istegi. BILEREK rol alani YOK - rol istemciden asla
    kabul edilmez, sunucu her zaman 'musteri' atar (aksi halde herhangi
    bir kullanici kendini yonetici/denetleyici yapabilirdi)."""

    kullanici_adi: str = Field(..., min_length=1, max_length=100)
    sifre: str = Field(..., min_length=8)


class KayitYanit(BaseModel):
    kullanici_adi: str
    rol: str


class MusteriSesiIstek(BaseModel):
    """POST /musteri-sesi/siniflandir istegi - serbest metin.

    ONEMLI: Bu uc nokta bir SIKAYET VERI TABANI DEGILDIR, hicbir seyi
    saklamaz - yalnizca gonderilen metni kural tabanli 10 temali
    taksonomiye (complaint/tema_siniflandirici.py) gore siniflandirip
    doner. Gercek musteri verisi henuz ingest edilmiyor (bkz.
    MusteriSesiOrnekYanit aciklamasi)."""

    metin: str = Field(..., min_length=1, max_length=2000)


class MusteriSesiYanit(BaseModel):
    tema: str | None = Field(
        None, description="Eslesen tema kodu (ör. REWARD_NOT_CREDITED) - hicbiri eslesmezse None"
    )
    guven: float = Field(0.0, ge=0.0, le=1.0)
    eslesen_ifadeler: list[str] = Field(default_factory=list)


class MusteriSesiOrnek(BaseModel):
    id: str
    metin: str
    tema: str | None
    guven: float
    eslesen_ifadeler: list[str]


class MusteriSesiOrnekYanit(BaseModel):
    """GET /musteri-sesi/ornekler yaniti.

    DURUSTLUK NOTU: buradaki 'ornekler' GERCEK musteri sikayeti DEGILDIR -
    elle yazilmis, hicbir gercek bankaya atfedilmeyen SENTETIK veridir
    (bkz. tests/veri/kapsam_disi/sentetik_musteri_sesi.json _uretim_yontemi
    alani). Gercek Sikayetvar/musteri platformu verisi ancak kurumsal/
    hukuki (KVKK) izin surecinden sonra ingest edilecek - Faz 2. Bu uc
    nokta o zamana kadar YALNIZCA "sistem boyle bir siniflandirmayi
    yapabilir mi?" sorusunun demosudur.
    """

    sentetik: bool = True
    aciklama: str = (
        "Bu ornekler gercek musteri sikayeti degildir - elle yazilmis, "
        "hicbir bankaya atfedilmeyen sentetik veridir (Faz 1 demo verisi)."
    )
    temalar: list[dict]
    ornekler: list[MusteriSesiOrnek]


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
    kampanya_id: int | None = Field(
        None,
        description=(
            "Kampanya tablosundaki id - dashboard'un isme gore kirilgan "
            "eslestirme yapmasi yerine dogrudan kullanabilmesi icin. "
            "HENUZ agent/router.py::rag_aracini_cagir tarafindan "
            "doldurulmuyor (vektor indeksindeki parca metadata'sinda id "
            "tutulmuyor) - bu alan simdilik None doner, doldurma ayri bir "
            "is (kayit_getirici enjeksiyonunun rag katmanina da "
            "tasinmasini gerektirir)."
        ),
    )
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


class TazelikYanit(BaseModel):
    """Dashboard'un "bu veri ne kadar guncel?" sorusunun cevabi.

    Mentor raporu II, P0 #1: "freshness metrigini dashboard'da gorunur yapin."
    Bilinmeyen degerler TAHMIN EDILMEZ, None doner - "eski indeks" ile
    "indeks durumu bilinmiyor" ayri seylerdir (bkz. README ilke 1).
    """

    son_tarama: str | None = Field(None, description="En yeni ham kaydin erisim zamani")
    tarama_gun_once: int | None = None
    rag_indeks_kuruldu: str | None = Field(
        None, description="None = indeks durumu bilinmiyor (henuz hic kurulmamis olabilir)"
    )
    rag_indeks_gun_once: int | None = None
    rag_parca_sayisi: int | None = None
    rag_belge_sayisi: int | None = None
    indeks_ham_veriden_eski_mi: bool | None = Field(
        None,
        description=(
            "True ise indeks kurulduktan SONRA yeni veri toplanmis demektir - "
            "RAG cevaplari en guncel kampanyalari icermeyebilir."
        ),
    )
    tekil_kampanya: int | None = None
    anlik_goruntu: int | None = None


class TarihceSatiri(BaseModel):
    """Bir kampanyanin TEK bir tarihli taramasindaki takip edilen alanlar
    (bkz. scraper/scripts/kampanya_tarihcesi.py::tarihce_getir)."""

    tarih: str
    icerik_hash: str | None = None
    alanlar: dict[str, Any]


class TarihceYanit(BaseModel):
    """Bir kampanyanin zaman icindeki degisim tarihcesi (Sprint 5).

    DENETIM BULGUSU: scraper/scripts/kampanya_tarihcesi.py yazilip test
    edilmisti (README'de somut ornekle anlatiliyor) ama hicbir API uc
    noktasina baglanmamisti - chatbot/dashboard uzerinden erisilemiyordu.
    """

    kampanya_id: int
    banka: str
    kampanya_adi: str
    kaynak_url: str
    tarihce: list[TarihceSatiri]
    degisen_alanlar: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Ilk ve son tarama arasinda GERCEKTEN degisen alanlar: {'alan': {'eski':..., 'yeni':...}}",
    )
    audit: "AuditBilgisi | None" = None


class CikarimIstek(BaseModel):
    """Serbest kampanya metninden yapilandirilmis alan cikarimi istegi
    (Sartname Md. 6 - demo videosunda "metin girdisi verilmesi, modelin
    urettigi yapilandirilmis cikti" gosterilmesi zorunlu)."""

    metin: str = Field(..., min_length=20, max_length=20000)
    hibrit: bool = Field(
        False,
        description=(
            "True ise NER+LLM katmanlari da calisir. VARSAYILAN FALSE: LLM "
            "GPU'suz makinede kayit basina 150-300 sn suruyor, canli demo "
            "bunu bekleyemez (bkz. extraction/llm_extractor.py)."
        ),
    )


class CikarimAdayi(BaseModel):
    """Bir alan icin BIR katmanin onerdigi deger. Ayni alanda birden fazla
    aday olabilir - hangisinin neden secildigi `catismalar`da yazar."""

    katman: str
    deger: Any = None
    guven: float | None = None


class CikarimIzi(BaseModel):
    """Alanin metindeki KANITI: hangi parcadan, hangi guvenle cikarildi."""

    alan: str
    kaynak_span: str | None = None
    kanit_turu: str = Field(
        "span",
        description=(
            "span            = kaynak_span metinden BIREBIR alintidir\n"
            "siniflandirma   = kaynak_span bir ETIKETTIR, metinde aynen gecmez "
            "(ör. kampanya_turu anahtar kelimeyle siniflandirilir, span "
            "cikarilmaz). Arayuz bunu 'metindeki kanit' gibi gostermemelidir."
        ),
    )
    guven: float | None = None
    katman: str
    dogrulandi: bool | None = Field(
        None,
        description=(
            "Verifier sonucu: deger kaynak metinde (deger + baglam) "
            "gercekten geciyor mu? None = bu alan icin dogrulama yapilmadi "
            "(sayisal olmayan alanlar)."
        ),
    )
    adaylar: list[CikarimAdayi] = Field(default_factory=list)


class CikarimYanit(BaseModel):
    """Cikarim sonucu + TAM denetim izi.

    `alanlar` tek basina dondurulmez: her alanin yaninda hangi katmanin
    doldurdugu, metindeki kaniti ve dogrulanip dogrulanmadigi gider -
    "eksik veri gizlenmez" ilkesinin cikarim tarafindaki karsiligi.
    """

    alanlar: dict[str, Any]
    izler: list[CikarimIzi]
    catismalar: list[dict[str, Any]] = Field(default_factory=list)
    bos_alanlar: list[str] = Field(
        default_factory=list, description="Metinde bulunamayan alanlar - sifir DEGIL, bilinmiyor"
    )
    turetilmis_alanlar: list[str] = Field(
        default_factory=list,
        description=(
            "Degeri OLAN ama metinden cikarilMAyan alanlar - diger alanlardan "
            "hesaplanir/derlenir (ör. kampanya_avantaji ozeti, "
            "kar_payi_orani_decimal). Kanit izleri yoktur; arayuz bunlari "
            "'metinde bulundu' gibi gostermemelidir."
        ),
    )
    genel_guven: float = 0.0
    hibrit_kullanildi: bool = False
    sure_ms: int = 0
    not_: str | None = Field(None, alias="not")

    model_config = {"populate_by_name": True}


class EtkiEkseni(BaseModel):
    """Etki skorunun BIR ekseni. `durum`:
      olculdu             - yuzdelik hesaplandi
      deger_yok           - bu kampanyada alan kaynakta belirtilmemis
      birim_karisik       - odul farkli birimlerde, siralanamaz
      yetersiz_eksen_kume - kumede tek olculebilir deger var, siralama tanimsiz
    """

    eksen: str
    aciklama: str
    deger: float | None = None
    yuzdelik: float | None = None
    olculebilir_kayit: int = 0
    durum: str
    birim: str | None = None
    birimler: list[str] | None = None


class FinansalSkor(BaseModel):
    """`skor` TEK BASINA anlamli degildir - `eksen_kirilimi` hep yanindadir."""

    skor: float | None = None
    durum: str
    sebep: str | None = None
    eksen_kirilimi: list[EtkiEkseni] = Field(default_factory=list)
    kullanilan_eksen: int = 0
    karsilastirma_kumesi: int = 0
    kampanya_turu: str | None = None


class GeriBildirimBileseni(BaseModel):
    """Musteri geri bildirim bileseni. Su an kaynak tanimli degil; `skor`
    None kalir. SIFIR YAZILMAZ - geri bildirim yoklugu "musteriler memnun
    degil" anlamina gelmez."""

    skor: float | None = None
    durum: str
    ornek_sayisi: int = 0
    sebep: str | None = None


class EtkiSkoruYanit(BaseModel):
    kampanya_id: int | None = None
    banka: str
    kampanya_adi: str
    finansal: FinansalSkor
    musteri_geri_bildirim: GeriBildirimBileseni
    durum: str = Field(..., description="kismi | hesaplanamadi")
    aciklama: str | None = None
    # DENETIM BULGUSU: /karsilastir, /hesapla, /chat, /cikar hepsi audit
    # blogu doner (latency, terminoloji kontrolu, izlenebilirlik) ama bu
    # uc nokta hicbirini API yanitinda tasimiyordu - _audit_kaydet() DB'ye
    # yaziyordu ama Juri Audit Paneli'nde gorunmuyordu.
    # NOT: "AuditBilgisi" burada henuz tanimlanmadigi icin STRING forward
    # reference kullanilir (asagida sinif sirasi AuditBilgisi'nden once) -
    # Pydantic v2 modul sonunda model_rebuild() ile bunu cozer.
    audit: "AuditBilgisi | None" = None


class RakipEkseni(BaseModel):
    """Rakip analizi matrisinin BIR sutunu (Md. 5.7 kriterlerinden biri).

    `durum` uc degerden biri:
      olculdu       - lider secildi, `lider_deger` dolu
      veri_yok      - hicbir kampanyada bu alan yok
      birim_karisik - degerler var ama farkli BIRIMLERDE (yalnizca odul
                      ekseni; 10.000 Mil ile 5.000 TL siralanamaz), bu
                      yuzden lider SECILMEZ
    """

    kriter: str
    alan: str | None = None
    aciklama: str
    daha_iyi: str
    olculebilir_kayit: int
    lider_deger: float | None = None
    durum: str
    birimler: list[str] | None = None


class RakipHucresi(BaseModel):
    deger: float | None = None
    lider: bool = False
    birim: str | None = Field(None, description="Yalnizca odul ekseninde dolu")


class RakipSatiri(BaseModel):
    """Matriste BIR kampanya. Bankalar tek satira sikistirilmaz - bir
    bankanin ayni turde iki kampanyasi varsa iki satir olur (bkz.
    comparison/compare_engine.py::rakip_matrisi)."""

    id: int | None = None
    banka: str
    kampanya_adi: str
    kaynak_url: str
    confidence: float | None = None
    degerler: dict[str, RakipHucresi]
    lider_eksen_sayisi: int
    eksik_alanlar: list[str] = Field(default_factory=list)


class RakipAnaliziYanit(BaseModel):
    kampanya_turu: str | None = None
    eksenler: list[RakipEkseni]
    satirlar: list[RakipSatiri]
    kayit_sayisi: int
    banka_sayisi: int
    audit: "AuditBilgisi | None" = None


class TerimKarti(BaseModel):
    """terminology/sozluk.json'daki BIR kavramin arayuze acilan hali
    (Md. 5.5 - katilim bankaciligi terminolojisine uyum).

    `kaynak` ile `ornek_kaynak` BILEREK ayridir:
      kaynak       = kavramin TANIM otoritesi (sartname, TKBB, BDDK)
      ornek_kaynak = bu ifadeyi GERCEK veride nerede gorduğumuz
    Ikisini tek alanda birlestirmek "tanim" ile "gozlem"i karistirir.
    """

    anahtar: str
    standart_terim: str
    gelenek_karsilik: str
    aciklama: str
    kaynak: str
    sema_alani: list[str] = Field(default_factory=list)
    ornek_kaynak: str | None = None


class AlanDogrulamaOzeti(BaseModel):
    """Tek bir alanin, cevaba giren kayitlar genelindeki dogrulama sayimi.

    UC DURUM AYRI SAYILIR ve bilerek tek bir orana indirgenmez:
    "calistirilmamis"i basarisizlik saymak sistemi haksiz yere kotu,
    basari saymak ise yalanci gosterirdi (bkz. validation/yanit_dogrulama.py).
    """

    alan: str
    dogrulanan: int = Field(0, description="Kaynakta dogrulandi")
    dogrulanamayan: int = Field(
        0, description="Dogrulanamadi - deger SILINMEZ, Verifier'in bilinen siniri var"
    )
    calistirilmamis: int = Field(0, description="Verifier bu alan icin hic calismadi")
    kayit_sayisi: int


class DogrulamaOzeti(BaseModel):
    """Ajan yanitinin dayandigi sayilarin dogrulama durumu.

    `kaynak="kayitli"`: hukum CIKARIM ANINDA verildi, soru sorulurken metin
    yeniden taranmadi - CampaignRecord ham kaynak metni tasimaz. Alan
    bilerek acik: kullaniciya taze bir kontrol yapilmis gibi sunulmaz.
    """

    durum: str = Field(
        ...,
        description=(
            "dogrulandi = kullanilan tum alanlar tum kayitlarda dogrulandi | "
            "kismi = Verifier calisti ama bir kismini onaylayamadi | "
            "calistirilmamis = bu alanlar icin Verifier hic calismadi"
        ),
    )
    kaynak: str = Field("kayitli", description="Kayitli hukum; canli yeniden dogrulama degil")
    alanlar: list[AlanDogrulamaOzeti] = Field(default_factory=list)


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

    # Verifier sonucu (validation/verifier.py) - CampaignRecord.dogrulanan_
    # alanlar ile AYNI sekil ({"alan_adi": bool}). TEK kayda dayanan
    # yanitlar icindir; su an dolduran bir yol yok, sema sozlesmesi
    # bozulmasin diye korunuyor (Havin'in arayuzu bu adlara gore kurulu).
    dogrulanan_alanlar: dict[str, bool] | None = None

    # Ajan yanitinin dayandigi sayilarin dogrulama ozeti. YALNIZCA
    # yapilandirilmis veri kullanan araclar (karsilastirma / toplam
    # maliyet) doldurur; RAG'de None kalir ve bu dogrudur - RAG kaynak
    # parcasini birebir dondurdugu icin orada kontrol tanim geregi hep
    # EVET derdi (bkz. validation/yanit_dogrulama.py).
    dogrulama: DogrulamaOzeti | None = None


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

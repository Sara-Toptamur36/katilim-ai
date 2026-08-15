"""Karsilastirma motoru (SQL Tool).

GUVENLIK ILKESI (rapor Bolum 5.3 / 8): Serbest metinden SQL URETILMEZ.
Kullanicinin yazdigi metin hicbir zaman dogrudan SQL'e girmez. Kriter adi
sabit bir sozlukten secilir; kullanici degerleri yalnizca PARAMETRE olarak
gecirilir. Bu, hem SQL injection riskini hem LLM halusinasyonunu ortadan
kaldirir.

SEFFAFLIK ILKESI (rapor Bolum 5.7 / 15): Eksik veri gizlenmez.
- SQL tarafinda: ORDER BY ... NULLS LAST
- Bellek tarafinda: None degerler siralamanin en sonuna konur
- Her kayitta hangi alanlarin eksik oldugu isaretlenir

Bu modul IKI modda calisir:
  1. Bellekte (Sprint 1): mock/gercek CampaignRecord listesi uzerinde
  2. SQL (Sprint 2+): PostgreSQL uzerinde, ayni ciktiyi uretir
Boylece Sprint 2'de gecis yapilirken cagiran taraf (API, ajan) degismez.
"""

from dataclasses import dataclass
from typing import Any, Sequence

from api.schemas import CampaignRecord


class BilinmeyenKriter(ValueError):
    """Sabit kriter listesinde olmayan bir kriter istendi."""


@dataclass(frozen=True)
class Kriter:
    """Tek bir karsilastirma kriterinin tanimi.

    `alan` degeri KOD ICINDE sabittir - kullanici girdisinden gelmez.
    Bu yuzden SQL'e dogrudan yazilmasi guvenlidir.

    `alan=None` KOMPOZIT bir kriteri isaret eder (bkz. "en_avantajli") -
    tek bir sutuna indirgenemez, birden fazla alt kriterin birlesimidir.
    """

    alan: str | None
    yon: str  # "ASC" | "DESC"
    aciklama: str
    daha_iyi: str  # "dusuk" | "yuksek"  -> kullaniciya aciklama uretmek icin


# Sartname Md. 5.7 ornek listesindeki 4 basit kriter + kompozit "en_avantajli".
# `en_yuksek_tutar` sartnamenin ornek listesinde YOK - Yenilikcilik/Yaraticilik
# degerlendirme kalemine (Bolum 7, ek veri alani) katki icin eklenmis BONUS bir
# kriterdir, sartnamenin 5 kriterinden biri gibi sunulmamalidir (bkz. D1 bulgusu,
# docs/extraction_accuracy_raporu.md).
KRITERLER: dict[str, Kriter] = {
    "en_dusuk_kar_payi": Kriter(
        alan="kar_payi_orani_percent",
        yon="ASC",
        aciklama="En dusuk kar payi orani",
        daha_iyi="dusuk",
    ),
    "en_yuksek_odul": Kriter(
        alan="odul_miktari",
        yon="DESC",
        aciklama="En yuksek odul miktari",
        daha_iyi="yuksek",
    ),
    "en_uzun_vade": Kriter(
        alan="vade_ay",
        yon="DESC",
        aciklama="En uzun vade secenegi",
        daha_iyi="yuksek",
    ),
    "en_dusuk_masraf": Kriter(
        alan="tahsis_ucreti",
        yon="ASC",
        aciklama="En dusuk masraf/tahsis ucreti",
        daha_iyi="dusuk",
    ),
    "en_avantajli": Kriter(
        alan=None,
        yon="DESC",
        aciklama="En avantajli kampanya (kar payi, odul, vade, masraf eksenlerinde karsilastirma)",
        daha_iyi="yuksek",
    ),
    "en_yuksek_tutar": Kriter(
        alan="finansman_tutari",
        yon="DESC",
        aciklama="En yuksek finansman tutari (bonus - sartnamenin 5.7 ornek listesinde yok)",
        daha_iyi="yuksek",
    ),
}

# "en_avantajli" kompoziti OLUSTURAN alt kriterler - Sartname Md. 5.7 ornek
# listesindeki DIGER 4 kriterle birebir ayni (en_yuksek_tutar haric, o listede
# yok). Yeni bir agirlikli formul UYDURULMAZ: sartnamenin kendi Ornek Temsili
# Senaryo-2'sinde gosterdigi gibi ("Kar payi acisindan C Bankasi, vade
# acisindan A Bankasi daha avantajlidir...") eksen eksen kazanan belirlenir,
# en cok eksende one cikan kayit genel kazanan sayilir.
_AVANTAJLI_ALT_KRITERLER = ("en_dusuk_kar_payi", "en_yuksek_odul", "en_uzun_vade", "en_dusuk_masraf")

# SELECT'te donen sabit sutun listesi (kullanici girdisinden gelmez)
_SECILEN_SUTUNLAR = (
    "id",
    "banka",
    "kampanya_adi",
    "kampanya_turu",
    "kar_payi_orani_percent",
    "vade_ay",
    "odul_miktari",
    "odul_birimi",
    "kampanya_avantaji",
    "masraf_durumu",
    "tahsis_ucreti",
    "finansman_tutari",
    "durum",
    "kaynak_url",
    "confidence",
)


def kriter_dogrula(kriter: str) -> Kriter:
    """Kriter sabit listede yoksa hata verir - serbest metin kabul edilmez."""
    if kriter not in KRITERLER:
        raise BilinmeyenKriter(
            f"Bilinmeyen kriter: {kriter!r}. "
            f"Gecerli kriterler: {', '.join(sorted(KRITERLER))}"
        )
    return KRITERLER[kriter]


# ---------------------------------------------------------------------------
# SQL modu (Sprint 2'de PostgreSQL ile kullanilacak)
# ---------------------------------------------------------------------------


def karsilastir_sorgusu(
    kriter: str,
    kampanya_turu: str | None = None,
    yalnizca_aktif: bool = True,
    limit: int = 10,
) -> tuple[str, tuple[Any, ...]]:
    """Sabit, guvenli bir SQL sablonu ve parametrelerini uretir.

    Donen SQL'de kullanici metni YOKTUR; degiskenler %s ile parametrelenir.
    `NULLS LAST`: eksik veri en sona gider, filtrelenip gizlenmez.

    Kompozit kriterler (alan=None, ör. "en_avantajli") tek bir ORDER BY
    sutununa indirgenemez - ilgili sutunlar cekilir, siralama uygulama
    katmaninda (karsilastir_bellekte) hesaplanir. Bu, uydurma bir SQL
    ifadesi uretmekten daha durusttur.
    """
    tanim = kriter_dogrula(kriter)

    kosullar: list[str] = []
    parametreler: list[Any] = []

    if yalnizca_aktif:
        kosullar.append("durum = %s")
        parametreler.append("ACTIVE")

    if kampanya_turu:
        kosullar.append("kampanya_turu = %s")
        parametreler.append(kampanya_turu)

    where = f"WHERE {' AND '.join(kosullar)}" if kosullar else ""
    sutunlar = ", ".join(_SECILEN_SUTUNLAR)

    siralama = f"ORDER BY {tanim.alan} {tanim.yon} NULLS LAST\n" if tanim.alan else ""
    sorgu = (
        f"SELECT {sutunlar}\n"
        f"FROM kampanyalar\n"
        f"{where}\n"
        f"{siralama}"
        f"LIMIT %s"
    ).replace("\n\n", "\n")

    parametreler.append(limit)
    return sorgu, tuple(parametreler)


# ---------------------------------------------------------------------------
# Bellek modu (Sprint 1: mock veri / henuz veritabani yokken)
# ---------------------------------------------------------------------------


def _siralama_anahtari(kayit: CampaignRecord, tanim: Kriter) -> tuple[bool, float]:
    """None degerleri HER ZAMAN en sona iter (NULLS LAST esdegeri).

    Demet ilk ogesi: None ise True -> True her zaman False'tan sonra siralanir,
    dolayisiyla yon ASC de olsa DESC de olsa bos degerler sona gider.
    """
    deger = getattr(kayit, tanim.alan, None)
    if deger is None:
        return (True, 0.0)
    return (False, -float(deger) if tanim.yon == "DESC" else float(deger))


def eksik_alanlari_isaretle(kayit: CampaignRecord) -> list[str]:
    """Kayitta bos olan, karsilastirma acisindan anlamli alanlari listeler."""
    izlenen = (
        "kar_payi_orani_percent",
        "vade_ay",
        "odul_miktari",
        "tahsis_ucreti",
        "finansman_tutari",
        "kampanya_bitis",
    )
    return [a for a in izlenen if getattr(kayit, a, None) is None]


def karsilastir_bellekte(
    kayitlar: Sequence[CampaignRecord],
    kriter: str = "en_dusuk_kar_payi",
    kampanya_turu: str | None = None,
    yalnizca_aktif: bool = False,
    limit: int = 10,
) -> dict[str, Any]:
    """Bellekteki CampaignRecord listesi uzerinde karsilastirma yapar.

    Ciktisi, SQL modunun ciktisiyla AYNI seklidedir; boylece Sprint 2'de
    veritabanina gecerken cagiran taraf degismez.
    """
    tanim = kriter_dogrula(kriter)

    suzulmus = list(kayitlar)
    if yalnizca_aktif:
        suzulmus = [k for k in suzulmus if k.durum.value == "ACTIVE"]
    if kampanya_turu:
        suzulmus = [k for k in suzulmus if k.kampanya_turu.value == kampanya_turu]

    if tanim.alan is None:  # kompozit kriter (en_avantajli)
        return _en_avantajli_bellekte(suzulmus, kriter, tanim, limit)

    sirali = sorted(suzulmus, key=lambda k: _siralama_anahtari(k, tanim))[:limit]

    sonuclar: list[dict[str, Any]] = []
    for sira, kayit in enumerate(sirali, start=1):
        satir = kayit.model_dump(mode="json")
        satir["sira"] = sira
        satir["eksik_alanlar"] = eksik_alanlari_isaretle(kayit)
        satir["kriter_degeri"] = getattr(kayit, tanim.alan, None)
        sonuclar.append(satir)

    # Aciklama, YALNIZCA kriter alaninda gercekten degeri olan kayitlar uzerinden
    # uretilir; eksik veriden "en avantajli" sonucu cikarilmaz.
    degeri_olanlar = [s for s in sonuclar if s["kriter_degeri"] is not None]
    kazanan = degeri_olanlar[0] if degeri_olanlar else None

    return {
        "kriter": kriter,
        "kriter_aciklamasi": tanim.aciklama,
        "sonuclar": sonuclar,
        "kazanan": (
            {
                "banka": kazanan["banka"],
                "kampanya_adi": kazanan["kampanya_adi"],
                "deger": kazanan["kriter_degeri"],
            }
            if kazanan
            else None
        ),
        "veri_eksigi_olan_kayit_sayisi": sum(1 for s in sonuclar if s["eksik_alanlar"]),
        "calistirilan_sql": None,  # bellek modunda SQL calismaz
    }


def _en_avantajli_bellekte(
    kayitlar: Sequence[CampaignRecord], kriter: str, tanim: Kriter, limit: int
) -> dict[str, Any]:
    """"En Avantajlı Kampanya" (Sartname Md. 5.7) - kompozit kriter.

    Sartnamenin kendi Ornek Temsili Senaryo-2'sinde gosterdigi yontem
    birebir uygulanir: her alt kriterde (kar payi, odul, vade, masraf) kim
    one cikiyor tek tek belirlenir; en cok eksende one cikan kayit genel
    kazanan sayilir. Esitlik durumunda (ayni sayida eksende one cikma)
    TEK bir kazanan UYDURULMAZ - "eksik veri gizlenmez" ilkesiyle ayni
    durustluk, esitlik acikca bildirilir.
    """
    kayitlar = list(kayitlar)
    sayac = [0] * len(kayitlar)
    eksen_kirilimi: list[dict[str, Any]] = []

    for alt_kriter in _AVANTAJLI_ALT_KRITERLER:
        alt_tanim = KRITERLER[alt_kriter]
        degerliler = [
            (i, getattr(k, alt_tanim.alan, None)) for i, k in enumerate(kayitlar)
        ]
        degerliler = [(i, d) for i, d in degerliler if d is not None]

        if not degerliler:
            eksen_kirilimi.append(
                {"kriter": alt_kriter, "aciklama": alt_tanim.aciklama, "kazanan_indeksler": [], "deger": None}
            )
            continue

        en_iyi = min(d for _, d in degerliler) if alt_tanim.yon == "ASC" else max(d for _, d in degerliler)
        kazanan_indeksler = [i for i, d in degerliler if d == en_iyi]
        for i in kazanan_indeksler:
            sayac[i] += 1
        eksen_kirilimi.append(
            {"kriter": alt_kriter, "aciklama": alt_tanim.aciklama, "kazanan_indeksler": kazanan_indeksler, "deger": en_iyi}
        )

    sirali_indeksler = sorted(range(len(kayitlar)), key=lambda i: -sayac[i])[:limit]

    sonuclar: list[dict[str, Any]] = []
    for sira, i in enumerate(sirali_indeksler, start=1):
        kayit = kayitlar[i]
        satir = kayit.model_dump(mode="json")
        satir["sira"] = sira
        satir["eksik_alanlar"] = eksik_alanlari_isaretle(kayit)
        satir["kriter_degeri"] = sayac[i]  # kac eksende one ciktigi
        sonuclar.append(satir)

    en_cok = max(sayac, default=0)
    genel_kazanan_indeksleri = [i for i in range(len(kayitlar)) if sayac[i] == en_cok and en_cok > 0]
    kazanan = None
    if len(genel_kazanan_indeksleri) == 1:
        k = kayitlar[genel_kazanan_indeksleri[0]]
        kazanan = {"banka": k.banka, "kampanya_adi": k.kampanya_adi, "deger": en_cok}

    return {
        "kriter": kriter,
        "kriter_aciklamasi": tanim.aciklama,
        "sonuclar": sonuclar,
        "kazanan": kazanan,
        "veri_eksigi_olan_kayit_sayisi": sum(1 for s in sonuclar if s["eksik_alanlar"]),
        "calistirilan_sql": None,
        "eksen_kirilimi": [
            {
                **e,
                "kazananlar": [
                    {"banka": kayitlar[i].banka, "kampanya_adi": kayitlar[i].kampanya_adi}
                    for i in e["kazanan_indeksler"]
                ],
            }
            for e in eksen_kirilimi
        ],
    }


# ---------------------------------------------------------------------------
# Rakip analizi matrisi (Sartname Md. 5.7 - "farkli katilim bankalarina ait
# urunlerin karsilastirilabilir hale getirilmesi")
# ---------------------------------------------------------------------------

# Matriste gosterilen eksenler. en_avantajli (kompozit) BURADA YOK - o bir
# eksen degil, eksenlerin sonucudur; matriste her eksen ayri sutundur.
_MATRIS_EKSENLERI = _AVANTAJLI_ALT_KRITERLER + ("en_yuksek_tutar",)

# Odul ekseni ozel: odul_miktari farkli BIRIMLERDE olabilir (TL, Mil, Gram,
# Worldpuan, ParafPara, Bankkart Lira - altin veri setinde altisi da var).
# 10.000 Mil ile 5.000 TL'yi tek eksende siralamak anlamsizdir; bu yuzden
# odul ekseninde lider YALNIZCA tum olculebilir kayitlar ayni birimdeyse
# secilir (bkz. _odul_birimi_tekil_mi).
_BIRIM_BAGIMLI_EKSENLER = {"en_yuksek_odul"}


def _odul_birimi_tekil_mi(kayitlar: Sequence[CampaignRecord]) -> tuple[bool, set[str]]:
    """Odul miktari OLAN kayitlarin hepsi ayni birimde mi?

    Doner: (tekil_mi, gorulen_birimler). Birim alani bos olan kayitlar
    "bilinmeyen birim" sayilir ve tekilligi bozar - cunku 5.000'in TL mi
    Worldpuan mi oldugunu bilmeden siralamak, bilerek yanlis siralamaktir.
    """
    birimler = {
        (k.odul_birimi or "").strip() or "?"
        for k in kayitlar
        if getattr(k, "odul_miktari", None) is not None
    }
    return (len(birimler) <= 1, birimler)


def rakip_matrisi(
    kayitlar: Sequence[CampaignRecord],
    kampanya_turu: str | None = None,
    yalnizca_aktif: bool = True,
) -> dict[str, Any]:
    """Bir kampanya turundeki tum kampanyalari eksen eksen yan yana koyar.

    /karsilastir TEK bir kritere gore siralar; bu fonksiyon TUM kriterleri
    ayni tabloda gosterir: hangi banka hangi eksende onde, tek bakista
    gorunur (Sartname Md. 5.7).

    TASARIM KARARI - her kampanya KENDI satirinda kalir, bankalar tek satira
    SIKISTIRILMAZ. Bir bankanin ayni turde iki kampanyasi varsa iki satir
    olur. Aksi halde "bu bankanin en dusuk orani X, en uzun vadesi Y" gibi
    bir satir uretilirdi; X ve Y farkli kampanyalardan geliyorsa ortada
    OLMAYAN bir urun tarif edilmis olur. Eksik veriyi gizlememe ilkesinin
    (bkz. modul basligi) ayni mantiktaki uzantisi.

    Doner: {"kampanya_turu", "eksenler", "satirlar", "kayit_sayisi",
            "banka_sayisi"}
    """
    suzulmus = list(kayitlar)
    if yalnizca_aktif:
        suzulmus = [k for k in suzulmus if k.durum.value == "ACTIVE"]
    if kampanya_turu:
        suzulmus = [k for k in suzulmus if k.kampanya_turu.value == kampanya_turu]

    odul_tekil, odul_birimleri = _odul_birimi_tekil_mi(suzulmus)

    eksenler: list[dict[str, Any]] = []
    liderler: dict[str, list[int]] = {}

    for eksen_adi in _MATRIS_EKSENLERI:
        tanim = KRITERLER[eksen_adi]
        degerliler = [
            (i, getattr(k, tanim.alan, None)) for i, k in enumerate(suzulmus)
        ]
        degerliler = [(i, d) for i, d in degerliler if d is not None]

        eksen: dict[str, Any] = {
            "kriter": eksen_adi,
            "alan": tanim.alan,
            "aciklama": tanim.aciklama,
            "daha_iyi": tanim.daha_iyi,
            "olculebilir_kayit": len(degerliler),
            "lider_deger": None,
            "durum": "olculdu",
        }

        if not degerliler:
            eksen["durum"] = "veri_yok"
            liderler[eksen_adi] = []
            eksenler.append(eksen)
            continue

        if eksen_adi in _BIRIM_BAGIMLI_EKSENLER and not odul_tekil:
            # Degerler gosterilir ama LIDER SECILMEZ - farkli birimler
            # arasinda "en yuksek" diye bir sey yoktur.
            eksen["durum"] = "birim_karisik"
            eksen["birimler"] = sorted(odul_birimleri)
            liderler[eksen_adi] = []
            eksenler.append(eksen)
            continue

        en_iyi = (
            min(d for _, d in degerliler)
            if tanim.yon == "ASC"
            else max(d for _, d in degerliler)
        )
        eksen["lider_deger"] = en_iyi
        liderler[eksen_adi] = [i for i, d in degerliler if d == en_iyi]
        eksenler.append(eksen)

    satirlar: list[dict[str, Any]] = []
    for i, kayit in enumerate(suzulmus):
        degerler: dict[str, Any] = {}
        for eksen_adi in _MATRIS_EKSENLERI:
            tanim = KRITERLER[eksen_adi]
            deger = getattr(kayit, tanim.alan, None)
            degerler[eksen_adi] = {
                "deger": deger,
                "lider": i in liderler[eksen_adi],
            }
        # Odul degerinin birimi olmadan anlami yok - hucreyle birlikte tasinir.
        degerler["en_yuksek_odul"]["birim"] = kayit.odul_birimi

        satirlar.append(
            {
                "id": kayit.id,
                "banka": kayit.banka,
                "kampanya_adi": kayit.kampanya_adi,
                "kaynak_url": kayit.kaynak_url,
                "confidence": kayit.confidence,
                "degerler": degerler,
                "lider_eksen_sayisi": sum(
                    1 for e in _MATRIS_EKSENLERI if i in liderler[e]
                ),
                "eksik_alanlar": eksik_alanlari_isaretle(kayit),
            }
        )

    # En cok eksende one cikan ustte; esitlikte banka adina gore - siralama
    # deterministik olsun diye (ayni girdi hep ayni cikti).
    satirlar.sort(key=lambda s: (-s["lider_eksen_sayisi"], s["banka"], s["kampanya_adi"]))

    return {
        "kampanya_turu": kampanya_turu,
        "eksenler": eksenler,
        "satirlar": satirlar,
        "kayit_sayisi": len(satirlar),
        "banka_sayisi": len({s["banka"] for s in satirlar}),
    }


def _en_avantajli_aciklama_uret(sonuc: dict[str, Any]) -> str:
    """Sartname Ornek Temsili Senaryo-2 formatinda eksen eksen aciklama.

    ("Kar payi orani acisindan C Bankasi daha avantajlidir cunku ...")
    """
    satirlar: list[str] = []
    veri_yok_eksenler: list[str] = []

    for eksen in sonuc.get("eksen_kirilimi", []):
        kazananlar = eksen["kazananlar"]
        if not kazananlar:
            veri_yok_eksenler.append(eksen["aciklama"])
            continue
        isimler = " ve ".join(sorted({k["banka"] for k in kazananlar}))
        satirlar.append(f"- {eksen['aciklama']} acisindan {isimler} daha avantajli (deger: {eksen['deger']}).")

    if veri_yok_eksenler:
        satirlar.append(
            f"Not: {', '.join(veri_yok_eksenler)} icin secilen kampanyalarin hicbirinde "
            "veri yok, bu eksen(ler) karsilastirmaya dahil edilemedi."
        )

    kazanan = sonuc.get("kazanan")
    if kazanan:
        satirlar.append(
            f"Genel olarak en avantajli: {kazanan['banka']} ({kazanan['deger']} eksende one cikiyor)."
        )
    else:
        satirlar.append(
            "Genel bir kazanan belirlenemedi: kampanyalar farkli eksenlerde esit sayida one cikiyor "
            "(veya hicbir eksende karsilastirilabilir veri yok)."
        )

    return "\n".join(satirlar)


def aciklama_uret(sonuc: dict[str, Any]) -> str:
    """Karsilastirma sonucundan insan okunur, DETERMINISTIK bir ozet uretir.

    Bu metin LLM tarafindan degil, dogrudan sayilardan uretilir - bu yuzden
    halusinasyon icermez (rapor Bolum 8).
    """
    if sonuc["kriter"] == "en_avantajli":
        return _en_avantajli_aciklama_uret(sonuc)

    kazanan = sonuc.get("kazanan")
    tanim = KRITERLER[sonuc["kriter"]]

    if kazanan is None:
        return (
            f"{tanim.aciklama} karsilastirmasi yapilamadi: "
            "secilen kampanyalarin hicbirinde bu alan belirtilmemis."
        )

    metin = (
        f"{tanim.aciklama} acisindan {kazanan['banka']} one cikiyor "
        f"({kazanan['kampanya_adi']}: {kazanan['deger']})."
    )

    eksik = sonuc.get("veri_eksigi_olan_kayit_sayisi", 0)
    if eksik:
        metin += (
            f" Not: {eksik} kampanyada bazi alanlar kaynakta belirtilmemistir; "
            "bu kayitlar gizlenmemis, siralamanin sonuna alinmistir."
        )
    return metin

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
    """

    alan: str
    yon: str  # "ASC" | "DESC"
    aciklama: str
    daha_iyi: str  # "dusuk" | "yuksek"  -> kullaniciya aciklama uretmek icin


# Sartname Md. 5.7'deki karsilastirma kriterleri
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
    "en_yuksek_tutar": Kriter(
        alan="finansman_tutari",
        yon="DESC",
        aciklama="En yuksek finansman tutari",
        daha_iyi="yuksek",
    ),
}

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

    sorgu = (
        f"SELECT {sutunlar}\n"
        f"FROM kampanyalar\n"
        f"{where}\n"
        f"ORDER BY {tanim.alan} {tanim.yon} NULLS LAST\n"
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


def aciklama_uret(sonuc: dict[str, Any]) -> str:
    """Karsilastirma sonucundan insan okunur, DETERMINISTIK bir ozet uretir.

    Bu metin LLM tarafindan degil, dogrudan sayilardan uretilir - bu yuzden
    halusinasyon icermez (rapor Bolum 8).
    """
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

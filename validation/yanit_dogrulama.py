"""Ajan yanitinin dayandigi sayilarin dogrulama durumunu ozetler.

README "Henuz kurulmayanlar" maddesi: *Verifier'in ajan yanit yoluna
baglanmasi.* Bu modul o baglantinin YAPILANDIRILMIS VERI ayagidir.

--------------------------------------------------------------------------
RAG YOLUNDA NEDEN CANLI VERIFIER CAGRILMIYOR
--------------------------------------------------------------------------
Ilk akla gelen cozum "/chat her yanitta Verifier'i calistirsin" olurdu.
RAG yolunda bu YANLIS olurdu: RAG hicbir cumle URETMEZ, buldugu kaynak
parcasini BIREBIR dondurur (bkz. agent/router.py::rag_aracini_cagir).
Yani "bu sayi kaynak metinde geciyor mu?" sorusunun cevabi tanim geregi
her zaman EVET'tir - kontrol hicbir sey elemez, yalnizca dogrulama
yapilmis IZLENIMI verir. Olmayan bir guvenceyi varmis gibi gostermek,
bu projenin kacindigi seyin ta kendisidir.

Gercek bosluk baska yerdeydi: KARSILASTIRMA ve TOPLAM MALIYET araclari
belge degil, veritabanindaki yapilandirilmis kayitlari kullanir ve
cevapta somut sayi soyler ("A Bankasi %1,89 ile en dusuk kar payina
sahip"). O sayinin bankanin kendi sayfasinda dogrulanip dogrulanmadigi
bilgisi `kampanyalar.dogrulanan_alanlar` sutununda ZATEN duruyordu ama
ajan yanitina hic ulasmiyordu.

--------------------------------------------------------------------------
KAYITLI HUKUM, CANLI YENIDEN DOGRULAMA DEGIL
--------------------------------------------------------------------------
Buradaki ozet, cikarim aninda calisan Verifier'in KAYDEDILMIS sonucudur;
soru sorulurken metin yeniden taranmaz. Sebep basit: CampaignRecord ham
kaynak metni tasimaz, dolayisiyla canli yeniden dogrulama her soruda
263 belgelik ham veriyi okumayi gerektirirdi. Ozet bu yuzden "kayitli"
olarak etiketlenir - kullaniciya taze bir kontrol yapilmis gibi
sunulmaz.

--------------------------------------------------------------------------
UC DURUM AYRI TUTULUR
--------------------------------------------------------------------------
`dogrulanan_alanlar` sozlugunde:
    alan YOK  -> Verifier o alan icin HIC calismadi
    True      -> kaynakta dogrulandi
    False     -> dogrulanamadi; deger SILINMEZ (Verifier'in bilinen
                 siniri var: "vade farksiz" gibi rakam icermeyen
                 ifadeler dogrulanamiyor - bkz. verifier.py)

Bu ucu tek bir bool'a indirmek en buyuk hata olurdu: "calistirilmamis"i
False saymak sistemi haksiz yere kotu, True saymak ise yalanci gosterir.
"""

from __future__ import annotations

from typing import Any, Sequence

from comparison.compare_engine import AVANTAJLI_ALT_KRITERLER, KRITERLER

# Toplam maliyet araci amortisman hesabini `kar_payi_orani_decimal` ve
# `vade_ay` uzerinden yapar. Verifier ise orani YUZDE anahtariyla kaydeder
# (validation/verifier.py::_ALAN_BAGLAM_KELIMELERI) - ayni iddianin farkli
# birimi. Eslemeyi yapmazsak dogrulanmis bir oran "calistirilmamis"
# gorunurdu.
_VERIFIER_ALAN_KARSILIGI = {
    "kar_payi_orani_decimal": "kar_payi_orani_percent",
}


def _verifier_alani(alan: str) -> str:
    return _VERIFIER_ALAN_KARSILIGI.get(alan, alan)


def kriterin_dayandigi_alanlar(kriter: str) -> list[str]:
    """Cevabin GERCEKTEN kullandigi alanlar.

    Kaydin tum alanlarini raporlamak yaniltici olurdu: kullanici "en uzun
    vade" diye sordugunda odul_miktari'nin dogrulanmis olmasi o cevap
    hakkinda hicbir sey soylemez. Yalnizca siralamayi belirleyen eksen(ler)
    raporlanir.
    """
    tanim = KRITERLER.get(kriter)
    if tanim is None:
        return []
    if tanim.alan is not None:
        return [tanim.alan]

    # Kompozit kriter ("en_avantajli"): tek sutuna inmez, alt eksenlerinin
    # hepsi cevaba katkida bulunur.
    return [KRITERLER[alt].alan for alt in AVANTAJLI_ALT_KRITERLER if KRITERLER[alt].alan]


def _alani_ozetle(kayitlar: Sequence[Any], alan: str) -> dict[str, Any]:
    dogrulanan = dogrulanamayan = calistirilmamis = 0

    for kayit in kayitlar:
        sozluk = getattr(kayit, "dogrulanan_alanlar", None) or {}
        if alan not in sozluk:
            calistirilmamis += 1
        elif sozluk[alan]:
            dogrulanan += 1
        else:
            dogrulanamayan += 1

    return {
        "alan": alan,
        "dogrulanan": dogrulanan,
        "dogrulanamayan": dogrulanamayan,
        "calistirilmamis": calistirilmamis,
        "kayit_sayisi": len(kayitlar),
    }


def yanit_dogrulamasini_ozetle(
    kayitlar: Sequence[Any], alanlar: Sequence[str]
) -> dict[str, Any] | None:
    """Verilen kayitlar ve alanlar icin kayitli dogrulama ozeti.

    Kayit ya da alan yoksa None doner - bos bir ozet basmak "dogrulama
    yapildi ama sonuc cikmadi" izlenimi verirdi.
    """
    if not kayitlar or not alanlar:
        return None

    # Cagiran taraf dogal alan adini verir (ör. kar_payi_orani_decimal);
    # Verifier karsiligina burada TEK YERDE cevrilir.
    verifier_alanlari = list(dict.fromkeys(_verifier_alani(a) for a in alanlar))
    alan_ozetleri = [_alani_ozetle(kayitlar, alan) for alan in verifier_alanlari]

    toplam_dogrulanan = sum(o["dogrulanan"] for o in alan_ozetleri)
    toplam_dogrulanamayan = sum(o["dogrulanamayan"] for o in alan_ozetleri)
    toplam_calistirilmamis = sum(o["calistirilmamis"] for o in alan_ozetleri)

    # Durum, UC DURUMU koruyacak sekilde secilir; "kismi" ile
    # "calistirilmamis" ayri tutulur cunku ikisi farkli seyi anlatir:
    # birinde Verifier calisti ve bir kismini onaylayamadi, digerinde
    # hic calismadi.
    if toplam_dogrulanan and not toplam_dogrulanamayan and not toplam_calistirilmamis:
        durum = "dogrulandi"
    elif not toplam_dogrulanan and not toplam_dogrulanamayan:
        durum = "calistirilmamis"
    else:
        durum = "kismi"

    return {
        "durum": durum,
        # Hukum cikarim aninda verildi; bu yanit icin metin yeniden
        # taranmadi (bkz. modul docstring'i).
        "kaynak": "kayitli",
        "alanlar": alan_ozetleri,
    }


def karsilastirma_dogrulamasini_ozetle(
    kayitlar: Sequence[Any], kriter: str
) -> dict[str, Any] | None:
    """Karsilastirma araci icin kisayol: kriterden alanlari kendisi bulur."""
    return yanit_dogrulamasini_ozetle(kayitlar, kriterin_dayandigi_alanlar(kriter))

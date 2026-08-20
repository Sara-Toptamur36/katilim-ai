"""Verifier'in ajan yanit yoluna baglanmasi (validation/yanit_dogrulama.py).

Bu testler iki seyi birden korur:
  1. Ozetin DOGRU sayilmasi (uc durum ayri kalmali),
  2. RAG yolunda ozetin URETILMEMESI - orada kontrol tanim geregi hep
     "evet" derdi ve eleme yapmayan bir guvence izlenimi olurdu.
"""

import pytest

from agent.orchestrator import soru_isle
from agent.router import _bilinen_bankalari_yukle
from api.mock_data import kampanyalari_getir
from validation.yanit_dogrulama import (
    kriterin_dayandigi_alanlar,
    yanit_dogrulamasini_ozetle,
)


def _kayit(banka: str, **alanlar):
    """Mock kaydin kopyasi - yalnizca testin ilgilendigi alanlar degistirilir."""
    k = kampanyalari_getir()[0].model_copy(deep=True)
    k.banka = banka
    for ad, deger in alanlar.items():
        setattr(k, ad, deger)
    return k


@pytest.fixture
def iki_banka():
    bankalar = _bilinen_bankalari_yukle()
    return bankalar[0], bankalar[1]


# ---------------------------------------------------------------------------
# Ozetin kendisi
# ---------------------------------------------------------------------------


def test_uc_durum_ayri_sayilir():
    """dogrulanan / dogrulanamayan / calistirilmamis tek bir orana
    indirgenmez - bu ayrim modulun varlik sebebi."""
    kayitlar = [
        _kayit("A", dogrulanan_alanlar={"vade_ay": True}),
        _kayit("B", dogrulanan_alanlar={"vade_ay": False}),
        _kayit("C", dogrulanan_alanlar={}),  # Verifier bu alan icin hic calismadi
    ]

    ozet = yanit_dogrulamasini_ozetle(kayitlar, ["vade_ay"])

    (alan,) = ozet["alanlar"]
    assert alan["dogrulanan"] == 1
    assert alan["dogrulanamayan"] == 1
    assert alan["calistirilmamis"] == 1
    assert alan["kayit_sayisi"] == 3
    assert ozet["durum"] == "kismi"


def test_hepsi_dogrulanmissa_durum_dogrulandi():
    kayitlar = [
        _kayit("A", dogrulanan_alanlar={"vade_ay": True}),
        _kayit("B", dogrulanan_alanlar={"vade_ay": True}),
    ]
    assert yanit_dogrulamasini_ozetle(kayitlar, ["vade_ay"])["durum"] == "dogrulandi"


def test_hic_calismadiysa_kismi_DEGIL_calistirilmamis_denir():
    """En kritik ayrim: "Verifier hic calismadi" ile "calisti ama
    onaylayamadi" ayni sey degildir. Ilkini basarisizlik saymak sistemi
    haksiz yere kotu, basari saymak yalanci gosterirdi."""
    kayitlar = [_kayit("A", dogrulanan_alanlar={}), _kayit("B", dogrulanan_alanlar={})]

    ozet = yanit_dogrulamasini_ozetle(kayitlar, ["vade_ay"])

    assert ozet["durum"] == "calistirilmamis"
    assert ozet["alanlar"][0]["calistirilmamis"] == 2
    assert ozet["alanlar"][0]["dogrulanamayan"] == 0


def test_ozet_kayitli_hukum_oldugunu_soyler():
    """Canli yeniden dogrulama YAPILMIYOR (CampaignRecord ham metni
    tasimaz); ozet bunu acikca etiketlemeli."""
    kayitlar = [_kayit("A", dogrulanan_alanlar={"vade_ay": True})]
    assert yanit_dogrulamasini_ozetle(kayitlar, ["vade_ay"])["kaynak"] == "kayitli"


def test_kayit_ya_da_alan_yoksa_ozet_uretilmez():
    """Bos ozet basmak "dogrulama yapildi ama sonuc cikmadi" izlenimi
    verirdi."""
    assert yanit_dogrulamasini_ozetle([], ["vade_ay"]) is None
    assert yanit_dogrulamasini_ozetle([_kayit("A")], []) is None


# ---------------------------------------------------------------------------
# Hangi alanlar raporlanir
# ---------------------------------------------------------------------------


def test_yalnizca_siralamayi_belirleyen_eksen_raporlanir():
    """"En uzun vade" sorusunda odul_miktari'nin dogrulanmis olmasi o
    cevap hakkinda hicbir sey soylemez - raporlanmamali."""
    assert kriterin_dayandigi_alanlar("en_uzun_vade") == ["vade_ay"]


def test_kompozit_kriter_tum_alt_eksenleri_raporlar():
    alanlar = kriterin_dayandigi_alanlar("en_avantajli")
    assert set(alanlar) == {
        "kar_payi_orani_percent",
        "odul_miktari",
        "vade_ay",
        "tahsis_ucreti",
    }


def test_ondalik_oran_verifier_yuzde_anahtarina_eslenir():
    """Toplam maliyet araci `kar_payi_orani_decimal` kullanir, Verifier ise
    orani YUZDE anahtariyla kaydeder. Esleme olmasaydi dogrulanmis bir
    oran "calistirilmamis" gorunurdu."""
    kayitlar = [_kayit("A", dogrulanan_alanlar={"kar_payi_orani_percent": True})]

    ozet = yanit_dogrulamasini_ozetle(kayitlar, ["kar_payi_orani_decimal"])

    assert ozet["alanlar"][0]["alan"] == "kar_payi_orani_percent"
    assert ozet["durum"] == "dogrulandi"


def test_bilinmeyen_kriter_alan_uretmez():
    assert kriterin_dayandigi_alanlar("boyle_bir_kriter_yok") == []


# ---------------------------------------------------------------------------
# Ajan yanit yolu - uctan uca
# ---------------------------------------------------------------------------


def test_karsilastirma_yanitinda_dogrulama_ozeti_bulunur(iki_banka):
    a, b = iki_banka
    veri = {
        a: [_kayit(a, kar_payi_orani_percent=1.89,
                   dogrulanan_alanlar={"kar_payi_orani_percent": True})],
        b: [_kayit(b, kar_payi_orani_percent=2.45,
                   dogrulanan_alanlar={"kar_payi_orani_percent": False})],
    }

    sonuc = soru_isle(f"{a} ile {b} arasinda en dusuk kar payi hangisi",
                      lambda banka: veri.get(banka, []))

    ozet = sonuc["audit_ekstra"]["dogrulama"]
    assert sonuc["audit_ekstra"]["cagrilan_arac"] == "sql"
    assert ozet["durum"] == "kismi"
    assert ozet["alanlar"][0]["dogrulanan"] == 1
    assert ozet["alanlar"][0]["dogrulanamayan"] == 1


def test_rag_yolunda_dogrulama_ozeti_URETILMEZ():
    """RAG kaynak parcasini BIREBIR dondurur, cumle uretmez - orada
    "sayi kaynakta var mi" kontrolu tanim geregi hep EVET derdi. Ozet
    basmak, eleme yapmayan bir guvence izlenimi verirdi.

    RAG gercek embedding modeli yuklemesin diye sahte bir arac verilir
    (agent/orchestrator.py::soru_isle bunu bilerek disari acar)."""
    def sahte_rag(soru, kayit_getirici=None):
        return {
            "basarili": True,
            "cevap": "Kaynaklarda bulduklarim: ...",
            "kaynaklar": [{"banka": "X", "metin": "birebir alinti"}],
            "veri": {},
        }

    sonuc = soru_isle("kart kampanyalarinda hangi avantajlar var",
                      lambda banka: [], rag_araci=sahte_rag)

    assert sonuc["audit_ekstra"]["cagrilan_arac"] == "rag"
    assert sonuc["audit_ekstra"]["dogrulama"] is None


def test_sozluk_yolunda_da_ozet_uretilmez():
    """Sozluk belge degil kavram donduruyor - dogrulanacak sayisal
    iddia yok."""
    sonuc = soru_isle("Murabaha nedir", lambda banka: [])
    assert sonuc["audit_ekstra"]["dogrulama"] is None


# ---------------------------------------------------------------------------
# Audit paneli: SQL karsiligi (ayni sinif bosluk - uretiliyor ama tasinmiyordu)
# ---------------------------------------------------------------------------


def test_sohbet_karsilastirmasinda_sql_karsiligi_donuyor(iki_banka):
    """DENETIM BULGUSU: /karsilastir uc noktasi SQL'i uretip Juri Audit
    Paneli'nde gosteriyordu, ajan yolu GOSTERMIYORDU - panel "cagrilan
    arac: sql" diyor ama SQL kartini hic basmiyordu (AuditPanel.jsx bos
    alani gizler). Juri demoda en cok bu yolu kullanir."""
    a, b = iki_banka
    veri = {
        a: [_kayit(a, kar_payi_orani_percent=1.89)],
        b: [_kayit(b, kar_payi_orani_percent=2.45)],
    }

    sonuc = soru_isle(f"{a} ile {b} arasinda en dusuk kar payi hangisi",
                      lambda banka: veri.get(banka, []))

    sql = sonuc["audit_ekstra"]["sql_sorgusu"]
    assert sql is not None
    assert "FROM kampanyalar" in sql
    assert "kar_payi_orani_percent ASC" in sql
    # Kullanici metni SQL'e GIRMEZ - degerler %s ile parametrelenir.
    assert "%s" in sql and a not in sql


def test_iki_yol_ayni_sorguyu_uretiyor(iki_banka):
    """/karsilastir ile /chat farkli SQL gosterirse panel hangisinin
    dogru oldugunu soyleyemez - ikisi ayni ureteci kullanmali."""
    from comparison.compare_engine import karsilastir_sorgusu

    a, b = iki_banka
    veri = {
        a: [_kayit(a, kar_payi_orani_percent=1.89)],
        b: [_kayit(b, kar_payi_orani_percent=2.45)],
    }
    sonuc = soru_isle(f"{a} ile {b} arasinda en dusuk kar payi hangisi",
                      lambda banka: veri.get(banka, []))

    beklenen, _ = karsilastir_sorgusu("en_dusuk_kar_payi")
    assert sonuc["audit_ekstra"]["sql_sorgusu"] == beklenen


def test_rag_ve_sozluk_yolunda_sql_uretilmez():
    """Belge/kavram donduren araclarda SQL yoktur - bos gostermek dogru."""
    assert soru_isle("Murabaha nedir", lambda b: [])["audit_ekstra"]["sql_sorgusu"] is None

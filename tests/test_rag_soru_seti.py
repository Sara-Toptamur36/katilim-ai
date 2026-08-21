"""RAG degerlendirme soru setinin butunlugu (gorev 22).

Bu testler RETRIEVAL'i olcmez - Qdrant/embedding GEREKTIRMEZ. Olctukleri
sey SETIN KENDISIDIR: yer gercegi gercekten altin veriye baglaniyor mu,
kategoriler bekleneni tasiyor mu, elle yazilmis sorular gecerli kayitlara
isaret ediyor mu.

NEDEN AYRI TEST: soru setinin ilk taslaginda elle yazilan 10 sorunun
6'si YANLIS kayda baglanmisti (ör. ZK-001 "saglik taksiti" sanilmisti,
oysa Bankkart Lira kampanyasi). Yanlis yer gercegi olcumu sessizce bozar -
Recall dusuk cikar ve sebebi retrieval sanilir. Bu testler o hatanin
geri gelmesini engeller.
"""

import json
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
SORU_SETI = KOK / "gold_dataset" / "rag_soru_seti.json"
GOLD = KOK / "gold_dataset" / "altin_veri_seti.json"

CEKIMSERLIK_KATEGORILERI = {"alan_disi", "alan_ici_kapsam_disi"}
CEVAPLI_KATEGORILER = {"tam_ad", "kismi_ad", "banka_ve_konu", "dogal_soru"}


@pytest.fixture(scope="module")
def sorular():
    with open(SORU_SETI, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def altin_sluglar():
    with open(GOLD, encoding="utf-8") as f:
        kayitlar = json.load(f)
    return {
        k["kaynak_url"].rstrip("/").split("/")[-1]
        for k in kayitlar
        if k.get("kaynak_url")
    }


@pytest.fixture(scope="module")
def altin_idler():
    with open(GOLD, encoding="utf-8") as f:
        return {k["kayit_id"] for k in json.load(f)}


def test_set_hedef_araliginda(sorular):
    """Gorev 22: 100-200 soru."""
    assert 100 <= len(sorular) <= 200, f"{len(sorular)} soru - hedef 100-200"


def test_tum_kategoriler_temsil_ediliyor(sorular):
    bulunanlar = {s["kategori"] for s in sorular}
    assert bulunanlar == CEKIMSERLIK_KATEGORILERI | CEVAPLI_KATEGORILER


def test_cevapli_sorularin_yer_gercegi_altin_veriden_geliyor(sorular, altin_sluglar):
    """Beklenen her slug elle dogrulanmis altin kayda ait olmali -
    aksi halde yer gercegi UYDURULMUS olurdu."""
    for s in sorular:
        if s["kategori"] in CEKIMSERLIK_KATEGORILERI:
            continue
        assert s["beklenen_sluglar"], f"cevapli soru bos yer gercegi: {s['soru']}"
        for slug in s["beklenen_sluglar"]:
            assert slug in altin_sluglar, f"altin veride yok: {slug} ({s['soru']})"


def test_cekimserlik_sorularinin_beklenen_cevabi_YOKTUR(sorular):
    """Cekimserlik beklenen soruya yer gercegi verilirse, olcum "bulmali"
    sanir ve dogru davranisi (cevap vermemek) HATA olarak sayar."""
    for s in sorular:
        if s["kategori"] in CEKIMSERLIK_KATEGORILERI:
            assert s["beklenen_sluglar"] == [], f"cekimserlik sorusuna cevap atanmis: {s['soru']}"


def test_elle_yazilan_sorular_gecerli_altin_kayda_bagli(sorular, altin_idler):
    """ILK TASLAKTA 6 SORU YANLIS KAYDA BAGLIYDI - bu test o hatayi
    yakalar."""
    elle = [s for s in sorular if s["kategori"] == "dogal_soru"]
    assert elle, "dogal_soru kategorisi bos"
    for s in elle:
        assert s["kayit_id"] in altin_idler, f"gecersiz kayit_id: {s['kayit_id']}"


def test_dogal_sorular_kampanya_adini_ICERMEZ(sorular):
    """Dogal soru, adin kopyasi olursa `tam_ad` kategorisinden farksiz
    kalir ve zorlugu olcmez."""
    with open(GOLD, encoding="utf-8") as f:
        adlar = {k["kayit_id"]: (k.get("kampanya_adi") or "") for k in json.load(f)}

    for s in sorular:
        if s["kategori"] != "dogal_soru":
            continue
        ad = adlar.get(s["kayit_id"], "")
        assert ad.lower() not in s["soru"].lower(), (
            f"dogal soru kampanya adinin kopyasi: {s['soru']}"
        )


def test_sorular_tekrar_etmiyor(sorular):
    """Ayni soru iki kez sayilirsa o sorgu olcumde iki kat agirlik alir."""
    gorulen: dict[tuple[str, str], int] = {}
    for s in sorular:
        anahtar = (s["kategori"], s["soru"].strip().lower())
        gorulen[anahtar] = gorulen.get(anahtar, 0) + 1
    tekrarlar = {k: v for k, v in gorulen.items() if v > 1}
    assert not tekrarlar, f"tekrar eden sorular: {tekrarlar}"


def test_kismi_ad_gercekten_KISALTILMIS(sorular):
    """Kisaltilmamis bir ad `tam_ad`in kopyasi olur, yeni bilgi vermez."""
    tam = {s["kayit_id"]: s["soru"] for s in sorular if s["kategori"] == "tam_ad"}
    for s in sorular:
        if s["kategori"] != "kismi_ad":
            continue
        assert len(s["soru"]) < len(tam.get(s["kayit_id"], "")), (
            f"kismi ad kisaltilmamis: {s['soru']}"
        )


def test_banka_ve_konu_kampanya_adi_ICERMEZ(sorular):
    """Bu kategorinin amaci adi HIC kullanmadan dogru belgeyi bulmak."""
    with open(GOLD, encoding="utf-8") as f:
        adlar = [(k.get("kampanya_adi") or "").lower() for k in json.load(f)]

    for s in sorular:
        if s["kategori"] != "banka_ve_konu":
            continue
        assert not any(ad and ad in s["soru"].lower() for ad in adlar), (
            f"banka_ve_konu sorusu kampanya adi iceriyor: {s['soru']}"
        )


def test_kaynak_alani_elle_mi_turetilmis_mi_soyluyor(sorular):
    """Hangi sorularin insan eliyle yazildigi denetlenebilir kalmali."""
    for s in sorular:
        assert s["kaynak"] in ("elle", "turetilmis"), s

"""Etiketleme sprinti is listesi (gold_dataset/sprint_is_listesi.py).

Bu liste, insan etiketleyicinin ONUNE konan is emridir. Yanlis bir liste
gunlerce bosa emek demektir: liste sayfasina gonderilen etiketleyici ya
zaman kaybeder ya da UYDURMA bir altin kayit uretir. Bu yuzden listenin
kendisi test edilir.
"""

import json
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
GOLD = KOK / "gold_dataset" / "altin_veri_seti.json"

SAHTE_ONEKLER = ("A-", "B-", "C-", "D-")


@pytest.fixture(scope="module")
def rapor():
    from gold_dataset.sprint_is_listesi import is_listesi_uret

    return is_listesi_uret(hedef=200, kota=30)


@pytest.fixture(scope="module")
def etiketli_sluglar():
    with open(GOLD, encoding="utf-8") as f:
        return {
            k["kaynak_url"].rstrip("/").split("/")[-1]
            for k in json.load(f)
            if not k["kayit_id"].startswith(SAHTE_ONEKLER) and k.get("kaynak_url")
        }


def test_zaten_etiketli_kampanya_listeye_GIRMEZ(rapor, etiketli_sluglar):
    """Ayni kampanyayi iki kez etiketlemek hem emek kaybi hem de altin
    sette cift kayit riskidir."""
    tekrarlar = [k["slug"] for k in rapor["liste"] if k["slug"] in etiketli_sluglar]
    assert not tekrarlar, f"zaten etiketli kampanyalar listede: {tekrarlar[:5]}"


def test_liste_sayfalari_ELENIR(rapor):
    """Kategori/liste sayfalarinda cikarilacak TEK bir kampanya yoktur."""
    from gold_dataset.sprint_is_listesi import LISTE_SAYFASI_KALIBI

    sizanlar = [k["slug"] for k in rapor["liste"] if LISTE_SAYFASI_KALIBI.search(k["slug"])]
    assert not sizanlar, f"liste sayfasi is listesine sizmis: {sizanlar}"


def test_elenenler_SESSIZCE_atilmaz(rapor):
    """Yanlis eleme fark edilebilsin diye elenenler raporlanir."""
    assert "liste_sayfasi_elenen" in rapor
    assert rapor["liste_sayfasi_elenen"], "hic liste sayfasi elenmemis - filtre calisiyor mu?"


def test_kota_asilmaz(rapor):
    """Kotanin isi, setin tek bankaya kaymasini engellemek."""
    asanlar = {b: n for b, n in rapor["banka_basina_secilen"].items() if n > 30}
    assert not asanlar, f"kota asilmis: {asanlar}"


def test_liste_tekrarsiz(rapor):
    sluglar = [k["slug"] for k in rapor["liste"]]
    assert len(sluglar) == len(set(sluglar)), "listede tekrar eden kampanya var"


def test_her_kayitta_url_var(rapor):
    """URL olmadan etiketleyici sayfayi acamaz."""
    eksik = [k["slug"] for k in rapor["liste"] if not k.get("url")]
    assert not eksik, f"URL'si olmayan kayitlar: {eksik[:5]}"


def test_liste_deterministik():
    """Ayni girdiyle ayni liste: iki kisi ayni siradan calisabilmeli."""
    from gold_dataset.sprint_is_listesi import is_listesi_uret

    a = [k["slug"] for k in is_listesi_uret(50, 30)["liste"]]
    b = [k["slug"] for k in is_listesi_uret(50, 30)["liste"]]
    assert a == b


def test_baslik_banka_adinin_kendisi_DEGIL(rapor):
    """Ilk surumde baslik olarak "Türkiye Emlak Katilim Bankasi" gibi
    gezinti satirlari seciliyordu - liste okunamaz hale geliyordu."""
    kotu = [
        k["slug"] for k in rapor["liste"]
        if k["baslik"].strip().lower().startswith((k["banka"] or "").lower())
    ]
    assert not kotu, f"baslik banka adiyla basliyor: {kotu[:5]}"


def test_hedefe_ulasilamiyorsa_bu_GIZLENMEZ(rapor):
    """Korpus dengesizligi yuzunden 200 hedefine ulasilamiyor. Rapor
    bunu sayilarla gostermeli ki plan gercege gore yapilsin - "liste
    uretildi" deyip sessiz kalmak yanlis guven verirdi."""
    assert rapor["listelenen"] <= rapor["hedef_yeni_kayit"]
    assert "ulasilabilir_toplam" in rapor
    # Bugunku korpusta hedefe ulasilamiyor; ulasilabilir hale geldiginde
    # bu test kirilir ve durumun degistigi FARK EDILIR.
    assert rapor["ulasilabilir_toplam"] < 200, (
        "Korpus buyumus olabilir - is listesi artik 200 hedefini karsiliyor. "
        "docs/ ve README'deki 'denge ile hacim catisiyor' notu guncellenmeli."
    )

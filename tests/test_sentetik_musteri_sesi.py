"""complaint/tema_siniflandirici.py testleri - Faz 1 T8.

VERI NEREDEN GELIYOR: tests/veri/kapsam_disi/sentetik_musteri_sesi.json.
Ornekler ELLE yazildi, hicbiri gercek bir sikayetten kopyalanmadi, hicbiri
gercek bir bankaya atfedilmiyor ve hicbiri veritabanina/RAG indeksine
girmiyor (bkz. test_sentetik_ornekler_urun_verisine_sizmamis).
"""

import json
from pathlib import Path

import pytest

from complaint.tema_siniflandirici import tema_siniflandir

VERI_YOLU = (
    Path(__file__).parent / "veri" / "kapsam_disi" / "sentetik_musteri_sesi.json"
)


def _veri() -> dict:
    with open(VERI_YOLU, encoding="utf-8") as f:
        return json.load(f)


VERI = _veri()
ORNEKLER = VERI["ornekler"]
ALAN_DISI_ORNEKLER = VERI["alan_disi_ornekler"]
GECERLI_TEMALAR = {t["kod"] for t in VERI["temalar"]}


def test_veri_setinde_10_tema_var():
    assert len(GECERLI_TEMALAR) == 10


def test_her_ornek_gecerli_bir_temaya_atanmis():
    """Veri setinin kendi tutarliligi - JSON'daki 'tema' alani her zaman
    temalar listesinde tanimli olmali."""
    for ornek in ORNEKLER:
        assert ornek["tema"] in GECERLI_TEMALAR, f"{ornek['id']}: bilinmeyen tema"


@pytest.mark.parametrize("ornek", ORNEKLER, ids=lambda o: o["id"])
def test_ornek_dogru_temaya_siniflandirilir(ornek):
    sonuc = tema_siniflandir(ornek["metin"])
    assert sonuc["tema"] == ornek["tema"], (
        f"{ornek['id']} - beklenen: {ornek['tema']}, bulunan: {sonuc['tema']} "
        f"(eslesen: {sonuc['eslesen_ifadeler']}), metin: {ornek['metin']!r}"
    )
    assert sonuc["guven"] > 0
    assert sonuc["eslesen_ifadeler"]


@pytest.mark.parametrize("ornek", ALAN_DISI_ORNEKLER, ids=lambda o: o["id"])
def test_alan_disi_metin_uydurma_tema_almaz(ornek):
    """UYDURMA GUARDI: hicbir temayla ilgisi olmayan metin, zorla bir
    temaya sokulmamali - None donmeli (rapor Bolum 5.7/15 ile ayni ilke)."""
    sonuc = tema_siniflandir(ornek["metin"])
    assert sonuc["tema"] is None, f"{ornek['id']} - uydurma tema atandi: {sonuc}"
    assert sonuc["guven"] == 0.0


def test_sentetik_ornekler_urun_verisine_sizmamis():
    """SIZINTI GUARDI: bu ornekler scraper ciktisinda, altin veri setinde
    veya veritabaninda BULUNMAMALI - urun verisi degil, olcum verisidir
    (bkz. tests/test_karsi_ornekler.py'deki AYNI desen)."""
    kok = Path(__file__).resolve().parent.parent
    aranacak_dizinler = [kok / "scraper" / "raw_data", kok / "gold_dataset"]

    imzalar = [o["metin"] for o in ORNEKLER if len(o["metin"]) > 40]
    assert imzalar, "Sizinti guardi icin yeterince uzun ifade bulunamadi"

    for dizin in aranacak_dizinler:
        if not dizin.exists():
            continue
        for dosya in dizin.rglob("*.json"):
            icerik = dosya.read_text(encoding="utf-8", errors="ignore")
            for imza in imzalar:
                assert imza not in icerik, (
                    f"Sentetik ornek urun verisine sizmis: {dosya} icinde {imza!r}"
                )


def test_olcum_ozeti_raporlanabilir(capsys):
    """Jüri/mentor icin tek bakista skor (test_karsi_ornekler.py'deki
    ayni desen)."""
    dogru = sum(
        1 for o in ORNEKLER if tema_siniflandir(o["metin"])["tema"] == o["tema"]
    )
    alan_disi_temiz = sum(
        1 for o in ALAN_DISI_ORNEKLER if tema_siniflandir(o["metin"])["tema"] is None
    )

    with capsys.disabled():
        print(
            f"\n  Sentetik musteri sesi seti: "
            f"dogru siniflandirma {dogru}/{len(ORNEKLER)} "
            f"(%{100 * dogru / len(ORNEKLER):.2f}), "
            f"alan disi ozgulluk {alan_disi_temiz}/{len(ALAN_DISI_ORNEKLER)}"
        )

    assert dogru == len(ORNEKLER)
    assert alan_disi_temiz == len(ALAN_DISI_ORNEKLER)

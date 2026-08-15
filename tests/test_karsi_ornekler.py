"""KARSI-ORNEK (CHALLENGE) SETI TESTLERI - Sartname Md. 5.5.

NE OLCER: sistemin katilim bankaciligi ile geleneksel bankaciligi
AYIRT EDIP EDEMEDIGINI. Iki yonlu olculur, cunku tek yon yanilticidir:

  1) HASSASIYET  - gelenek ifadeler yakalaniyor mu? (kacirma olcumu)
  2) OZGULLUK    - mesru katilim ifadeleri YANLISLIKLA yakalaniyor mu?
                   (yanlis alarm olcumu)

Yalnizca (1) olculseydi "her cumleyi flagle" diyen bir kontrol %100
alirdi; yalnizca (2) olculseydi "hicbir seyi flagleme" diyen bir kontrol
%100 alirdi. Ikisi birlikte anlamlidir - bu, cikarim tarafindaki
"dolu alan / bos alan dogrulugu" ikilisinin terminoloji karsiligidir.

VERI NEREDEN GELIYOR: tests/veri/gelenek_bankacilik_karsi_ornekleri.json.
Ifadeler ELLE yazildi; hicbiri gercek bir bankadan kopyalanmadi, hicbiri
gercek bir bankaya atfedilmiyor ve hicbiri veritabanina/RAG indeksine
girmiyor. Sartname Md. 5.1 veri setini katilim bankalariyla sinirladigi
icin geleneksel banka verisi TOPLANMAMISTIR - kavram farkini olcmek icin
veri toplamak gerekmez, olcum verisi yeterlidir.
"""

import json
from pathlib import Path

import pytest

from terminology.tutarlilik_kontrolu import (
    GELENEK_TERIM_ESLESTIRMELERI,
    terminoloji_tutarliligini_kontrol_et,
)

# Klasor adi bilerek kendini anlatiyor: bu veri URUN verisi DEGILDIR,
# yalnizca kapsam olcumu icin vardir. Ayrimin kaniti asagidaki
# test_karsi_ornekler_veritabanina_girmemis testidir (bkz.
# docs/kapsam_ve_veri_ayrimi.md).
VERI_YOLU = (
    Path(__file__).parent / "veri" / "kapsam_disi" / "gelenek_bankacilik_karsi_ornekleri.json"
)


def _veri() -> dict:
    with open(VERI_YOLU, encoding="utf-8") as f:
        return json.load(f)


VERI = _veri()
KARSI_ORNEKLER = VERI["karsi_ornekler"]
MESRU_KULLANIMLAR = VERI["mesru_kullanimlar"]
BILINEN_SINIRLAMALAR = VERI["bilinen_sinirlamalar"]


def _yakalanan_kokler(ifade: str) -> set[str]:
    """Bulunan sorunlardaki kelimeleri, hangi KOKTEN geldiklerine cevirir.
    ('faizli' -> 'faiz'), boylece test ek cekimlerine bagimli kalmaz."""
    sonuc = terminoloji_tutarliligini_kontrol_et(ifade)
    kokler = set()
    for sorun in sonuc["bulunan_sorunlar"]:
        kelime = sorun["gelenek_terim"].lower()
        for kural in GELENEK_TERIM_ESLESTIRMELERI:
            if kelime.startswith(kural["kok"]):
                kokler.add(kural["kok"])
    return kokler


@pytest.mark.parametrize("ornek", KARSI_ORNEKLER, ids=lambda o: o["id"])
def test_gelenek_ifade_yakalanir(ornek):
    """Her karsi-ornek tutarsiz isaretlenmeli ve beklenen gelenek
    koklerin TAMAMI yakalanmali."""
    sonuc = terminoloji_tutarliligini_kontrol_et(ornek["ifade"])
    assert sonuc["tutarli"] is False, f"{ornek['id']} tutarsiz isaretlenmedi: {ornek['ifade']!r}"

    yakalanan = _yakalanan_kokler(ornek["ifade"])
    beklenen = set(ornek["beklenen_kokler"])
    assert beklenen <= yakalanan, (
        f"{ornek['id']} - kacirilan kok(ler): {beklenen - yakalanan}, "
        f"yakalanan: {yakalanan}, ifade: {ornek['ifade']!r}"
    )


@pytest.mark.parametrize("ornek", KARSI_ORNEKLER, ids=lambda o: o["id"])
def test_gelenek_ifadeye_katilim_karsiligi_onerilir(ornek):
    """Yakalamak yetmez - Md. 5.5 kavramin DOGRU SINIFLANDIRILMASINI
    istiyor. Her sorun icin bir standart terim onerilmeli."""
    sonuc = terminoloji_tutarliligini_kontrol_et(ornek["ifade"])
    for sorun in sonuc["bulunan_sorunlar"]:
        assert sorun["onerilen"], f"{ornek['id']} - '{sorun['gelenek_terim']}' icin oneri bos"


@pytest.mark.parametrize("ornek", MESRU_KULLANIMLAR, ids=lambda o: o["id"])
def test_mesru_katilim_ifadesi_yanlis_alarm_uretmez(ornek):
    """YANLIS ALARM OLCUMU: gercek katilim bankasi verisinde dogrulanmis
    mesru ifadeler ('faizsiz', 'kredi karti', 'kredi skoru', 'acik kredi',
    'kredi bakiyesi', 'veresiye kredi') flaglenmemelidir."""
    sonuc = terminoloji_tutarliligini_kontrol_et(ornek["ifade"])
    assert sonuc["tutarli"] is True, (
        f"{ornek['id']} YANLIS ALARM - bulunan: {sonuc['bulunan_sorunlar']}, "
        f"ifade: {ornek['ifade']!r}"
    )


@pytest.mark.parametrize("ornek", BILINEN_SINIRLAMALAR, ids=lambda o: o["id"])
def test_bilinen_sinirlama_davranisi_degismedi(ornek):
    """Bu ifade gelenek bankaciligidir ama kontrol onu BILEREK yakalamiyor
    (gerekce: JSON dosyasindaki 'not' alani). Test, kariri DONDURUR:
    biri istisna listesini daraltirsa bu test kirilir ve karar yeniden
    tartisilmis olur. Yesil kalmasi 'sorun yok' demek DEGIL, 'bilinen
    sinirlama hala ayni yerde' demektir."""
    yakalanan = _yakalanan_kokler(ornek["ifade"])
    assert ornek["kacirilan_kok"] not in yakalanan, (
        f"{ornek['id']} artik yakalaniyor - bu IYI bir haber olabilir, ama "
        "once mesru kullanimlarin (MK-002/003/004/008) hala gectigini "
        "dogrulayip bu kaydi karsi_ornekler'e tasiyin."
    )


def test_karsi_ornekler_veritabanina_girmemis():
    """SIZINTI GUARDI: bu ifadelerin hicbiri scraper ciktisinda ya da
    altin veri setinde bulunmamali. Bulunursa, olcum verisi urun verisine
    karismis demektir (mentor raporu P0 - 'kaynak turleri karisma riski')."""
    kok = Path(__file__).resolve().parent.parent
    aranacak_dizinler = [kok / "scraper" / "raw_data", kok / "gold_dataset"]

    # Kisa/genel ifadeler yanlis eslesme uretmesin diye yalnizca yeterince
    # ayirt edici olanlar aranir.
    imzalar = [o["ifade"] for o in KARSI_ORNEKLER if len(o["ifade"]) > 40]
    assert imzalar, "Sizinti guardi icin yeterince uzun ifade bulunamadi"

    for dizin in aranacak_dizinler:
        if not dizin.exists():
            continue
        for dosya in dizin.rglob("*.json"):
            icerik = dosya.read_text(encoding="utf-8", errors="ignore")
            for imza in imzalar:
                assert imza not in icerik, (
                    f"Karsi-ornek ifadesi urun verisine sizmis: {dosya} icinde {imza!r}"
                )


def test_olcum_ozeti_raporlanabilir(capsys):
    """Jüri/mentor icin tek bakista skor. Bu test bir esik DOGRULAMAZ -
    yukaridaki parametreli testler zaten her ornegi tek tek dogruluyor;
    burasi yalnizca toplu sonucu gorunur kilar (pytest -s ile okunur)."""
    yakalanan_sayisi = sum(
        1 for o in KARSI_ORNEKLER
        if terminoloji_tutarliligini_kontrol_et(o["ifade"])["tutarli"] is False
    )
    temiz_sayisi = sum(
        1 for o in MESRU_KULLANIMLAR
        if terminoloji_tutarliligini_kontrol_et(o["ifade"])["tutarli"] is True
    )
    toplam_karsi = len(KARSI_ORNEKLER)
    toplam_mesru = len(MESRU_KULLANIMLAR)

    with capsys.disabled():
        print(
            f"\n  Terminoloji karsi-ornek seti: "
            f"hassasiyet {yakalanan_sayisi}/{toplam_karsi} "
            f"(%{100 * yakalanan_sayisi / toplam_karsi:.2f}), "
            f"ozgulluk {temiz_sayisi}/{toplam_mesru} "
            f"(%{100 * temiz_sayisi / toplam_mesru:.2f}), "
            f"bilinen sinirlama: {len(BILINEN_SINIRLAMALAR)}"
        )

    assert yakalanan_sayisi == toplam_karsi
    assert temiz_sayisi == toplam_mesru

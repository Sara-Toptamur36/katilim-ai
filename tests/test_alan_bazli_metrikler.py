"""Alan bazli Precision / Recall / F1 hesabinin testleri.

NEDEN AYRI METRIK: Iki toplam metrik ("dolu alan dogrulugu %85,94" ve
"bos alan dogrulugu %93,15") sistemin GENEL saglığını gosterir ama hangi
alanin zayif oldugunu soylemez. Ilk calistirmada bu tablo, toplam
metriklerin AYLARDIR gizledigi bir veri kalitesi hatasini ortaya cikardi
(vade_ay recall %14,29 -> gold'da taksit degerleri vade sutununa
yazilmis, bkz. docs/extraction_accuracy_raporu.md).
"""

import pytest

from scraper.scripts.extraction_accuracy import (
    extraction_accuracy_hesapla,
    prf_hesapla,
)


def _sayac(dogru=0, yanlis_deger=0, kacirilan=0, uydurulan=0, dogru_bos=0):
    return {
        "dogru": dogru,
        "yanlis_deger": yanlis_deger,
        "kacirilan": kacirilan,
        "uydurulan": uydurulan,
        "dogru_bos": dogru_bos,
    }


# ---------------------------------------------------------------------------
# prf_hesapla - saf fonksiyon
# ---------------------------------------------------------------------------


def test_kusursuz_alan_yuz_uzerinden_yuz():
    m = prf_hesapla(_sayac(dogru=10, dogru_bos=5))
    assert m["precision"] == 100.0
    assert m["recall"] == 100.0
    assert m["f1"] == 100.0
    assert m["destek"] == 10


def test_kacirma_recalli_dusurur_precisiona_dokunmaz():
    """Motor 10 degerin 6'sini buldu, 4'unu hic bulamadi (None dondu).
    Bulduklari dogru oldugu icin precision bozulmaz."""
    m = prf_hesapla(_sayac(dogru=6, kacirilan=4))
    assert m["precision"] == 100.0
    assert m["recall"] == 60.0


def test_uydurma_precisioni_dusurur_recalle_dokunmaz():
    """Kaynakta olmayan alana deger uretmek yalnizca precision hatasidir -
    kacirilmis bir gercek deger yok."""
    m = prf_hesapla(_sayac(dogru=8, uydurulan=2))
    assert m["precision"] == 80.0
    assert m["recall"] == 100.0


def test_yanlis_deger_HEM_precisioni_HEM_recalli_dusurur():
    """BILINCLI KARAR: gold 1.89 derken motor 10.0 bulduysa hem dogru
    degeri kacirmis (FN) hem yanlis bir deger iddia etmistir (FP).
    Yalnizca FN saymak, finansal uygulamada daha tehlikeli olan 'yanlis
    deger gosterme' hatasini gizlerdi."""
    m = prf_hesapla(_sayac(dogru=8, yanlis_deger=2))
    assert m["fp"] == 2
    assert m["fn"] == 2
    assert m["precision"] == 80.0
    assert m["recall"] == 80.0


def test_hic_olculebilir_ornek_yoksa_None_doner():
    """0.0 dondurmek 'motor bu alanda basarisiz' gibi YANLIS bir izlenim
    yaratirdi; dogru ifade 'bu alan henuz OLCULEMIYOR'dur."""
    m = prf_hesapla(_sayac())
    assert m["precision"] is None
    assert m["recall"] is None
    assert m["f1"] is None
    assert m["destek"] == 0


def test_hic_dogru_bulamayan_alan_sifir_alir():
    """Olculebilir ornek VAR ama hicbiri dogru degil -> 0.0 (None degil)."""
    m = prf_hesapla(_sayac(kacirilan=5, uydurulan=3))
    assert m["recall"] == 0.0
    assert m["precision"] == 0.0
    assert m["f1"] == 0.0


def test_f1_harmonik_ortalamadir():
    m = prf_hesapla(_sayac(dogru=6, kacirilan=4, uydurulan=2))
    # P = 6/8 = 75, R = 6/10 = 60 -> F1 = 2*75*60/(75+60) = 66.67
    assert m["precision"] == 75.0
    assert m["recall"] == 60.0
    assert m["f1"] == pytest.approx(66.67, abs=0.01)


# ---------------------------------------------------------------------------
# Gercek veriyle butunluk
# ---------------------------------------------------------------------------


def test_alan_bazli_sayimlar_toplam_metriklerle_tutarli():
    """Alan bazli sayaclar, ayni gecişte uretilen toplam metriklerle
    aritmetik olarak uyusmali - uyusmuyorsa sayaclardan biri yanlis
    yerde artiyordur."""
    sonuc = extraction_accuracy_hesapla()
    alan_bazli = sonuc["alan_bazli"]

    toplam_tp = sum(m["tp"] for m in alan_bazli.values())
    assert toplam_tp == sonuc["dogru_alan"]

    # Her dolu-alan ornegi ya TP ya FN'dir (yanlis_deger ikisine de girer,
    # bu yuzden destek uzerinden karsilastirilir).
    toplam_destek = sum(m["destek"] for m in alan_bazli.values())
    assert toplam_destek == sonuc["toplam_alan"]

    # `fp`, uydurma ile yanlis-deger'i birlestirdigi icin geri ayrilamaz -
    # bu yuzden ham sayaclar uzerinden dogrulanir.
    ham = sonuc["alan_sayaclari"]
    assert sum(s["uydurulan"] for s in ham.values()) == sonuc["yanlis_pozitif_sayisi"]
    assert (
        sum(s["uydurulan"] + s["dogru_bos"] for s in ham.values())
        == sonuc["bos_alan_olculebilen"]
    )
    assert sum(s["kacirilan"] + s["yanlis_deger"] for s in ham.values()) == len(
        sonuc["hatalar"]
    )


def test_alan_bazli_her_alan_icin_anahtar_uretir():
    from scraper.scripts.extraction_accuracy import ALAN_ESLEME

    alan_bazli = extraction_accuracy_hesapla()["alan_bazli"]
    assert set(alan_bazli) == set(ALAN_ESLEME)
    for m in alan_bazli.values():
        assert {"tp", "fp", "fn", "tn", "destek", "precision", "recall", "f1"} <= m.keys()


def test_etiketlenmemis_alan_sifir_degil_None_raporlanir():
    """taksit_sayisi / erteleme_suresi_ay gold'da henuz etiketlenmedi.
    Bunlari %0 diye raporlamak motoru haksiz yere basarisiz gosterirdi."""
    alan_bazli = extraction_accuracy_hesapla()["alan_bazli"]
    for alan in ("taksit_sayisi", "erteleme_suresi_ay"):
        if alan_bazli[alan]["destek"] == 0:
            assert alan_bazli[alan]["recall"] is None
            assert alan_bazli[alan]["f1"] is None

"""scraper/scripts/extraction_accuracy.py testleri.

NOT: Bu testler belirli bir dogruluk YUZDESI ZORUNLU KILMAZ - dogruluk
Yagmur'un cikarim motorunun kalitesine bagli (onun alani, bkz. rapor
docs/extraction_accuracy_raporu.md) ve kampanya rotasyonuyla dogal olarak
dalgalanir. Burada test edilen: olcum ARACININ KENDISI dogru calisiyor mu.
"""

from scraper.scripts.extraction_accuracy import (
    _degerler_esit_mi,
    extraction_accuracy_hesapla,
)


def test_degerler_esit_mi_sayisal_tolerans():
    assert _degerler_esit_mi(2.99, 2.990001) is True
    assert _degerler_esit_mi(2.99, 3.50) is False


def test_degerler_esit_mi_metin_tam_esitlik_ister():
    assert _degerler_esit_mi("Mil", "Mil") is True
    assert _degerler_esit_mi("Mil", "TL") is False


def test_degerler_esit_mi_none_ile_sayi_esit_degil():
    assert _degerler_esit_mi(100, None) is False


def test_extraction_accuracy_hesapla_calisir_ve_makul_yapi_doner():
    """Gercek scraper ciktisi + Altin Veri Seti uzerinde calistirir - bu
    ortamda scraper ciktisi zaten mevcut oldugu icin canli kayit
    bulunmasi beklenir (0 olursa scraper hic calismamis demektir)."""
    sonuc = extraction_accuracy_hesapla()

    assert 0.0 <= sonuc["accuracy"] <= 100.0
    assert sonuc["toplam_alan"] >= sonuc["dogru_alan"] >= 0
    assert sonuc["canli_kayit_sayisi"] > 0, "Hic canli kayit yok - scraper ciktisi eksik olabilir"
    assert len(sonuc["hatalar"]) == sonuc["toplam_alan"] - sonuc["dogru_alan"]

    for hata in sonuc["hatalar"]:
        assert {"kayit_id", "alan", "beklenen", "bulunan"} <= hata.keys()

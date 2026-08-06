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


# ---------------------------------------------------------------------------
# Yanlis pozitif (bos alan) metrigi
# ---------------------------------------------------------------------------


def test_bos_alan_metrigi_makul_yapi_doner():
    """Ikinci metrik: kaynakta OLMAYAN alana motor deger uyduruyor mu?
    Tek basina 'accuracy' bunu hic olcmuyordu (gold'da bos alanlar
    atlaniyordu) - hicbir alani uyduran bir motor bile cezasiz kaliyordu."""
    sonuc = extraction_accuracy_hesapla()

    assert 0.0 <= sonuc["bos_alan_dogrulugu"] <= 100.0
    assert sonuc["bos_alan_olculebilen"] > 0, (
        "Hic olculebilir bos alan yok - altin veri setindeki "
        "'alan_belirtilmemis' bayraklari kaybolmus olabilir"
    )
    assert 0 <= sonuc["yanlis_pozitif_sayisi"] <= sonuc["bos_alan_olculebilen"]
    assert len(sonuc["yanlis_pozitifler"]) == sonuc["yanlis_pozitif_sayisi"]

    for yp in sonuc["yanlis_pozitifler"]:
        assert {"kayit_id", "alan", "uydurulan"} <= yp.keys()
        assert yp["uydurulan"] is not None, "Yanlis pozitif tanimi geregi deger None olamaz"


def test_bos_alan_orani_dogru_hesaplanir():
    """Oran = (olculebilen - yanlis pozitif) / olculebilen."""
    sonuc = extraction_accuracy_hesapla()

    beklenen = round(
        (sonuc["bos_alan_olculebilen"] - sonuc["yanlis_pozitif_sayisi"])
        / sonuc["bos_alan_olculebilen"]
        * 100,
        2,
    )
    assert sonuc["bos_alan_dogrulugu"] == beklenen


def test_yanlis_pozitif_yalnizca_bayrakli_alanlarda_sayilir():
    """KAPSAM KURALI: gold'da bos olup 'alan_belirtilmemis' ile
    bayraklanMAMIS alanlar olcume girmemeli - orada "kaynakta yok" ile
    "etiketleyici doldurmadi" ayirt edilemez, motoru haksiz cezalandirir.

    Altin veri setinde taksit_sayisi/erteleme_suresi_ay sutunlari hic
    doldurulmamis ve bayraklanmamis; bu alanlardan yanlis pozitif
    gelmemeli."""
    sonuc = extraction_accuracy_hesapla()

    bayraksiz_alanlar = {"taksit_sayisi", "erteleme_suresi_ay"}
    sizanlar = [yp for yp in sonuc["yanlis_pozitifler"] if yp["alan"] in bayraksiz_alanlar]
    assert sizanlar == [], f"Bayraklanmamis alandan yanlis pozitif sizmis: {sizanlar}"


def test_mevcut_donus_anahtarlari_korunuyor():
    """Geriye uyumluluk: hibrit_extraction_accuracy.py ve regresyon
    testleri bu anahtarlara dayanir, yeni metrik eklenirken bozulmamali."""
    sonuc = extraction_accuracy_hesapla()

    assert {
        "accuracy", "toplam_alan", "dogru_alan", "canli_kayit_sayisi", "hatalar"
    } <= sonuc.keys()

"""finansman_tutari cikariminin testleri.

Iki gercek bulgu kilitlenir:

1. BUYUKLUK EKI: T.O.M. Katilim tutarlari kelimeyle yaziyor
   ("250 Bin TL ye kadar"), binlik ayiracli degil. Bu bicim
   taninmadigi surece tutar HIC bulunamiyordu.

2. BAGLAM GUARD: "X TL'ye kadar" tek basina finansman tutari
   DEGILDIR. Olculdu - 9 yanlis pozitifin 3'u bu desenin baglamsiz
   eslesmesinden geliyordu (kart limiti, harcama esigi, iade tavani).
"""

import pytest

from extraction.normalizer import tutara_cevir
from extraction.regex_extractor import kaydi_cikar


# ---------------------------------------------------------------------------
# Buyukluk eki (bin / milyon)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ham,beklenen",
    [
        ("500 TL", 500.0),
        ("50.000 TL", 50000.0),
        ("250 Bin TL", 250_000.0),
        ("250 bin TL", 250_000.0),
        ("1,5 milyon TL", 1_500_000.0),
        ("2 milyar TL", 2_000_000_000.0),
    ],
)
def test_tutara_cevir_buyukluk_ekini_uygular(ham, beklenen):
    assert tutara_cevir(ham) == beklenen


def test_buyukluk_eki_olmayan_kelime_carpan_uygulamaz():
    """'250 TL bin kisiye' gibi ifadelerde 'bin' tutara ait degil -
    desen sayinin HEMEN ardini arar, araya TL girerse eslesmez."""
    assert tutara_cevir("250 TL") == 250.0


def test_bin_ekli_tutar_uctan_uca_cikarilir():
    """Gercek T.O.M. metni (TOM-002) - onceden None donuyordu."""
    r = kaydi_cikar(
        "STANDART PAKET secen musteriler; 250 Bin TL ye kadar yapacaklari "
        "Ozel Okul Odemelerinde kampanya suresi boyunca..."
    )
    assert r["finansman_tutari"] == 250_000.0


# ---------------------------------------------------------------------------
# Baglam guard'i - "X TL'ye kadar" her zaman finansman degildir
# ---------------------------------------------------------------------------


def test_kart_limiti_finansman_tutari_SAYILMAZ():
    """Gercek KT-005 metni: musteri segmentasyonu icin kart limiti."""
    r = kaydi_cikar(
        "Kart limiti; 100.000 TL ve altinda olan musterilere 3.000 Mil, "
        "100.000 TL'den 300.000 TL'ye kadar olan musterilere 6.000 Mil verilecektir."
    )
    assert r["finansman_tutari"] is None


def test_harcama_esigi_finansman_tutari_SAYILMAZ():
    """Gercek TOM-001 metni: kazanim esigi."""
    r = kaydi_cikar(
        "Bu segmentlerde yer alan musteriler 3.500 TL'ye kadar olan hafta sonu "
        "yapilacak restoran harcamalarindan kazanim saglayabilir."
    )
    assert r["finansman_tutari"] is None


def test_iade_tavani_finansman_tutari_SAYILMAZ():
    """Gercek TOM-003 metni."""
    r = kaydi_cikar("Tum Marketlerde Gecerli, 1.000 TL'ye kadar iade!")
    assert r["finansman_tutari"] is None


def test_gercek_finansman_tutari_HALA_bulunur():
    """Guard fazla genis olmamali - acik finansman ifadesi gecmeli."""
    r = kaydi_cikar("100.000 TL'ye kadar Pratik Finansman Kart ile ihtiyaclariniza destek.")
    assert r["finansman_tutari"] == 100_000.0


def test_ilk_eslesme_degil_ilk_GECERLI_eslesme_alinir():
    """Ayni sayfada once gecersiz sonra gecerli aday varsa, gecerli olan
    secilmeli - eskiden kosulsuz ILK eslesme aliniyordu."""
    r = kaydi_cikar(
        "Kampanyada 5.000 TL'ye kadar alisveris puani kazanin. "
        "Ayrica 80.000 TL'ye kadar ihtiyac finansmani kullanabilirsiniz."
    )
    assert r["finansman_tutari"] == 80_000.0


# ---------------------------------------------------------------------------
# Aralik desenine guard UYGULANMAZ
# ---------------------------------------------------------------------------


def test_aralik_deseni_harcama_kelimesine_ragmen_bulunur():
    """OLCULDU: "X TL - Y TL arasi" kalibi gercek veride yalnizca
    finansman/taksitlendirme araliklarinda geciyor. Guard uygulanirsa
    AL-005 gibi GERCEK finansman araliklari yalnizca cumlede 'harcama'
    gectigi icin elenir."""
    r = kaydi_cikar(
        "TROY kredi kartlariniz ile yapacaginiz 1.000 TL- 100.000 TL arasi "
        "saglik harcamalariniza vade farksiz 6 taksit firsati!"
    )
    assert r["finansman_tutari"] == 100_000.0


def test_aralikta_ust_sinir_alinir():
    r = kaydi_cikar("30.000 TL- 500.000 TL arasi okul odemelerinize 6 taksit.")
    assert r["finansman_tutari"] == 500_000.0

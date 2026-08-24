"""Kampanya durumu OKUMA ANINDA hesaplaniyor mu?

--------------------------------------------------------------------------
NEDEN BU TEST VAR
--------------------------------------------------------------------------
Olculdu (24.08.2026, Havin'in arayuz raporu Md. 1): veritabanindaki TUM
kayitlarda durum=BILINMIYOR idi (olcum aninda 251 kayit; Havin 496 saymis,
aradaki fark veritabaninin yeniden yuklenmesinden geliyor). Sebep, `storage.yasam_dongusu
.durum_hesapla` fonksiyonunun URETIM KODUNDA HIC CAGRILMAMASIYDI - yalnizca
testleri vardi. `durum` sutununa hicbir yukleyici yazmiyordu, repository de
`satir.durum or "BILINMIYOR"` diyerek bos degeri oldugu gibi geciriyordu.

Bedeli: comparison/compare_engine.py'nin `yalnizca_aktif` filtresi listeyi
tamamen bosaltiyor, Karsilastirma sayfasi "0 aktif kampanya - 0 banka"
gosteriyordu. Sartname Md. 5.7'nin istedigi rakip analizi tumuyle bostu.

--------------------------------------------------------------------------
NEDEN SUTUNA YAZMIYORUZ DA HER OKUMADA HESAPLIYORUZ
--------------------------------------------------------------------------
Yasam dongusu ZAMANA BAGLI: bugun ACTIVE olan kayit yarin EXPIRED olur.
Sutuna yazilan deger yazildigi anda dogru, ertesi gun yanlistir ve bunu
kimse fark etmez. Tarihlerden okuma aninda hesaplamak, degerin sorulduğu
ana gore hep dogru olmasini garanti eder.
"""

from datetime import date

import pytest

from api.kampanya_repository import _kayda_cevir


class SahteSatir:
    """Kampanya ORM satirinin _kayda_cevir'in okudugu alanlari kadari.

    Gercek DB gerektirmez: bu testler yasam dongusu KARARINI olcer,
    veritabani baglantisini degil.
    """

    def __init__(self, **degerler):
        varsayilan = {
            "id": 1,
            "banka": "Kuveyt Turk",
            "kampanya_adi": "Test Kampanyasi",
            "kampanya_turu": "Belirlenemedi",
            "kar_payi_orani_percent": None,
            "kar_payi_orani_decimal": None,
            "kar_payi_tablosu": None,
            "vade_ay": None,
            "finansman_tutari": None,
            "taksit_sayisi": None,
            "erteleme_suresi_ay": None,
            "odul_miktari": None,
            "odul_birimi": None,
            "kampanya_avantaji": None,
            "masraf_durumu": None,
            "tahsis_ucreti": None,
            "kampanya_baslangic": None,
            "kampanya_bitis": None,
            "durum": None,
            "hedef_kitle": None,
            "kaynak_url": "https://ornek.test/kampanya",
            "belge_tarihi": None,
            "confidence": 0.0,
            "cikarim_yontemi": None,
            "alan_belirtilmemis": {},
            "dogrulanan_alanlar": {},
        }
        varsayilan.update(degerler)
        for ad, deger in varsayilan.items():
            setattr(self, ad, deger)


BUGUN = date(2026, 8, 24)


def test_bitisi_gelecekte_olan_kampanya_ACTIVE_olur():
    """ASIL HATA BUYDU: tarih dolu oldugu halde durum BILINMIYOR kaliyordu."""
    kayit = _kayda_cevir(
        SahteSatir(
            kampanya_baslangic=date(2026, 8, 1),
            kampanya_bitis=date(2026, 12, 31),
        ),
        bugun=BUGUN,
    )
    assert kayit.durum.value == "ACTIVE"


def test_bitisi_gecmiste_olan_kampanya_EXPIRED_olur():
    kayit = _kayda_cevir(
        SahteSatir(
            kampanya_baslangic=date(2026, 1, 1),
            kampanya_bitis=date(2026, 7, 31),
        ),
        bugun=BUGUN,
    )
    assert kayit.durum.value == "EXPIRED"


def test_tarihsiz_kampanya_BILINMIYOR_kalir():
    """Bilgi eksikligi 'suresi dolmus' sayilmaz - kampanyayi haksiz gizler."""
    kayit = _kayda_cevir(SahteSatir(), bugun=BUGUN)
    assert kayit.durum.value == "BILINMIYOR"


def test_henuz_baslamamis_kampanya_ACTIVE_sayilmaz():
    kayit = _kayda_cevir(
        SahteSatir(
            kampanya_baslangic=date(2026, 12, 1),
            kampanya_bitis=date(2026, 12, 31),
        ),
        bugun=BUGUN,
    )
    assert kayit.durum.value != "ACTIVE"


def test_tarih_yoksa_SUTUNDAKI_deger_korunur():
    """Kaynak sayfa 'kampanya sona erdi' diyorsa tarih olmadan da EXPIRED'dir.

    Hesaplama tarihlere bakar; tarih hic yoksa hesaplama BILINMIYOR doner.
    O durumda sutunda duran bilgiyi EZMEK, elde olan tek veriyi atmak olurdu.
    """
    kayit = _kayda_cevir(SahteSatir(durum="EXPIRED"), bugun=BUGUN)
    assert kayit.durum.value == "EXPIRED"


def test_tarih_varsa_ESKIMIS_sutun_degeri_ezilir():
    """Sutundaki deger yazildigi gun dogruydu; bugun tarihler karar verir.

    Bu, sutuna yazmak yerine okuma aninda hesaplamanin ASIL SEBEBI.
    """
    kayit = _kayda_cevir(
        SahteSatir(
            durum="ACTIVE",  # gecen ay yazilmis, artik yanlis
            kampanya_baslangic=date(2026, 1, 1),
            kampanya_bitis=date(2026, 7, 31),
        ),
        bugun=BUGUN,
    )
    assert kayit.durum.value == "EXPIRED"


def test_bugun_verilmezse_gercek_tarih_kullanilir():
    """`bugun` yalnizca test icin; uretimde cagiran taraf gecmez."""
    kayit = _kayda_cevir(
        SahteSatir(kampanya_baslangic=date(2020, 1, 1), kampanya_bitis=date(2020, 1, 2))
    )
    assert kayit.durum.value == "EXPIRED"


@pytest.mark.parametrize(
    "durum_metni", ["ACTIVE", "EXPIRED", "BILINMIYOR"]
)
def test_donen_durum_semadaki_enum_degerlerinden_biri(durum_metni):
    """durum_hesapla'nin ciktisi YasamDongusu enum'uyla birebir eslesmeli.

    Eslesmezse Pydantic dogrulama hatasi verir ve /kampanyalar tumuyle
    500 doner - bu testin amaci o sessiz sozlesme kaymasini yakalamak.
    """
    from api.schemas import YasamDongusu

    assert durum_metni in {d.value for d in YasamDongusu}

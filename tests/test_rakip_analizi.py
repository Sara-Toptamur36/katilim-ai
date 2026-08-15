"""Rakip analizi matrisi testleri (Sartname Md. 5.7).

/karsilastir TEK kritere gore siralar; rakip_matrisi TUM kriterleri ayni
tabloda gosterir. Bu testler ucunu kilitler:

  1. Lider isaretlemesi dogru (esitlikte coklu, bos deger lider olamaz)
  2. Bankalar tek satira SIKISTIRILMAZ - olmayan bir urun tarif edilmez
  3. Odul ekseninde farkli BIRIMLER varsa lider SECILMEZ (10.000 Mil ile
     5.000 TL siralanamaz)
"""

import pytest

from api.schemas import CampaignRecord, KampanyaTuru, YasamDongusu
from comparison.compare_engine import rakip_matrisi


def _kayit(
    banka: str,
    kampanya_adi: str = "Kampanya",
    kar_payi: float | None = None,
    vade: int | None = None,
    odul: float | None = None,
    odul_birimi: str | None = None,
    masraf: float | None = None,
    tutar: float | None = None,
    tur: KampanyaTuru = KampanyaTuru.KONUT,
    durum: YasamDongusu = YasamDongusu.ACTIVE,
) -> CampaignRecord:
    return CampaignRecord(
        banka=banka,
        kampanya_adi=kampanya_adi,
        kaynak_url=f"https://ornek.test/{banka}/{kampanya_adi}",
        kampanya_turu=tur,
        durum=durum,
        kar_payi_orani_percent=kar_payi,
        vade_ay=vade,
        odul_miktari=odul,
        odul_birimi=odul_birimi,
        tahsis_ucreti=masraf,
        finansman_tutari=tutar,
    )


def _eksen(sonuc: dict, kriter: str) -> dict:
    return next(e for e in sonuc["eksenler"] if e["kriter"] == kriter)


def _satir(sonuc: dict, banka: str) -> dict:
    return next(s for s in sonuc["satirlar"] if s["banka"] == banka)


# ---------------------------------------------------------------------------
# Lider isaretlemesi
# ---------------------------------------------------------------------------


def test_her_eksende_lider_isaretlenir():
    kayitlar = [
        _kayit("A", kar_payi=1.95, vade=120, masraf=7500),
        _kayit("B", kar_payi=1.87, vade=96, masraf=0),
    ]
    sonuc = rakip_matrisi(kayitlar)

    # Kar payinda dusuk iyi -> B; vadede yuksek iyi -> A; masrafta dusuk iyi -> B
    assert _satir(sonuc, "B")["degerler"]["en_dusuk_kar_payi"]["lider"] is True
    assert _satir(sonuc, "A")["degerler"]["en_dusuk_kar_payi"]["lider"] is False
    assert _satir(sonuc, "A")["degerler"]["en_uzun_vade"]["lider"] is True
    assert _satir(sonuc, "B")["degerler"]["en_dusuk_masraf"]["lider"] is True


def test_esitlikte_iki_satir_da_lider_olur():
    """Tek bir kazanan UYDURULMAZ - esitlik acikca gosterilir."""
    kayitlar = [_kayit("A", kar_payi=1.90), _kayit("B", kar_payi=1.90)]
    sonuc = rakip_matrisi(kayitlar)
    assert _satir(sonuc, "A")["degerler"]["en_dusuk_kar_payi"]["lider"] is True
    assert _satir(sonuc, "B")["degerler"]["en_dusuk_kar_payi"]["lider"] is True


def test_bos_deger_lider_olamaz():
    """Eksik veri gizlenmez ama avantaj gibi de gosterilmez."""
    kayitlar = [_kayit("A", masraf=None), _kayit("B", masraf=5000)]
    sonuc = rakip_matrisi(kayitlar)
    assert _satir(sonuc, "A")["degerler"]["en_dusuk_masraf"]["lider"] is False
    assert _satir(sonuc, "B")["degerler"]["en_dusuk_masraf"]["lider"] is True
    assert _eksen(sonuc, "en_dusuk_masraf")["olculebilir_kayit"] == 1


def test_hicbir_kayitta_veri_yoksa_eksen_veri_yok_isaretlenir():
    kayitlar = [_kayit("A", kar_payi=1.9), _kayit("B", kar_payi=2.1)]
    eksen = _eksen(rakip_matrisi(kayitlar), "en_dusuk_masraf")
    assert eksen["durum"] == "veri_yok"
    assert eksen["lider_deger"] is None


# ---------------------------------------------------------------------------
# Odul ekseni - birim tuzagi
# ---------------------------------------------------------------------------


def test_farkli_odul_birimlerinde_lider_secilmez():
    """10.000 Mil ile 5.000 TL arasinda "en yuksek" diye bir sey yoktur.
    Degerler gosterilir, lider secilmez."""
    kayitlar = [
        _kayit("A", odul=10000, odul_birimi="Mil"),
        _kayit("B", odul=5000, odul_birimi="TL"),
    ]
    sonuc = rakip_matrisi(kayitlar)
    eksen = _eksen(sonuc, "en_yuksek_odul")

    assert eksen["durum"] == "birim_karisik"
    assert eksen["lider_deger"] is None
    assert sorted(eksen["birimler"]) == ["Mil", "TL"]
    assert all(
        s["degerler"]["en_yuksek_odul"]["lider"] is False for s in sonuc["satirlar"]
    )


def test_ayni_birimde_odul_lideri_secilir():
    kayitlar = [
        _kayit("A", odul=5000, odul_birimi="TL"),
        _kayit("B", odul=7500, odul_birimi="TL"),
    ]
    eksen = _eksen(rakip_matrisi(kayitlar), "en_yuksek_odul")
    assert eksen["durum"] == "olculdu"
    assert eksen["lider_deger"] == 7500


def test_odul_birimi_bos_olan_kayit_tekilligi_bozar():
    """5.000'in TL mi Worldpuan mi oldugunu bilmeden siralamak, bilerek
    yanlis siralamaktir."""
    kayitlar = [
        _kayit("A", odul=5000, odul_birimi="TL"),
        _kayit("B", odul=7500, odul_birimi=None),
    ]
    assert _eksen(rakip_matrisi(kayitlar), "en_yuksek_odul")["durum"] == "birim_karisik"


def test_odul_hucresi_birimi_tasir():
    """Sayinin birimi olmadan anlami yok - hucreyle birlikte gider."""
    sonuc = rakip_matrisi([_kayit("A", odul=0.1, odul_birimi="Gram")])
    assert _satir(sonuc, "A")["degerler"]["en_yuksek_odul"]["birim"] == "Gram"


# ---------------------------------------------------------------------------
# Satir modeli: bankalar sikistirilmaz
# ---------------------------------------------------------------------------


def test_ayni_bankanin_iki_kampanyasi_iki_satir_olur():
    """Tek satira sikistirilsaydi "bu bankanin en dusuk orani X, en uzun
    vadesi Y" denirdi; X ve Y farkli kampanyalardan gelirse ORTADA OLMAYAN
    bir urun tarif edilmis olur."""
    kayitlar = [
        _kayit("A", "Ucuz Kampanya", kar_payi=1.5, vade=24),
        _kayit("A", "Uzun Kampanya", kar_payi=2.5, vade=120),
    ]
    sonuc = rakip_matrisi(kayitlar)

    assert sonuc["kayit_sayisi"] == 2
    assert sonuc["banka_sayisi"] == 1
    ucuz = next(s for s in sonuc["satirlar"] if s["kampanya_adi"] == "Ucuz Kampanya")
    uzun = next(s for s in sonuc["satirlar"] if s["kampanya_adi"] == "Uzun Kampanya")
    assert ucuz["degerler"]["en_dusuk_kar_payi"]["lider"] is True
    assert ucuz["degerler"]["en_uzun_vade"]["lider"] is False
    assert uzun["degerler"]["en_uzun_vade"]["lider"] is True


def test_satirlar_lider_eksen_sayisina_gore_siralanir():
    kayitlar = [
        _kayit("Zayif", kar_payi=3.0, vade=12, masraf=9000),
        _kayit("Guclu", kar_payi=1.0, vade=120, masraf=0),
    ]
    sonuc = rakip_matrisi(kayitlar)
    assert sonuc["satirlar"][0]["banka"] == "Guclu"
    assert sonuc["satirlar"][0]["lider_eksen_sayisi"] == 3


def test_siralama_deterministiktir():
    """Ayni girdi hep ayni cikti - esitlikte banka/kampanya adina gore."""
    kayitlar = [_kayit("C"), _kayit("A"), _kayit("B")]
    ilk = [s["banka"] for s in rakip_matrisi(kayitlar)["satirlar"]]
    ikinci = [s["banka"] for s in rakip_matrisi(list(reversed(kayitlar)))["satirlar"]]
    assert ilk == ikinci == ["A", "B", "C"]


# ---------------------------------------------------------------------------
# Suzme
# ---------------------------------------------------------------------------


def test_yalnizca_aktif_kampanyalar_alinir():
    kayitlar = [
        _kayit("A", durum=YasamDongusu.ACTIVE),
        _kayit("B", durum=YasamDongusu.EXPIRED),
    ]
    sonuc = rakip_matrisi(kayitlar, yalnizca_aktif=True)
    assert [s["banka"] for s in sonuc["satirlar"]] == ["A"]


def test_kampanya_turu_suzgeci_calisir():
    kayitlar = [
        _kayit("A", tur=KampanyaTuru.KONUT),
        _kayit("B", tur=KampanyaTuru.KART),
    ]
    sonuc = rakip_matrisi(kayitlar, kampanya_turu=KampanyaTuru.KART.value)
    assert [s["banka"] for s in sonuc["satirlar"]] == ["B"]


def test_bos_kume_hata_vermez():
    sonuc = rakip_matrisi([])
    assert sonuc["kayit_sayisi"] == 0
    assert sonuc["banka_sayisi"] == 0
    assert all(e["durum"] == "veri_yok" for e in sonuc["eksenler"])


def test_eksik_alanlar_satirda_isaretlenir():
    sonuc = rakip_matrisi([_kayit("A", kar_payi=1.9)])
    assert "vade_ay" in _satir(sonuc, "A")["eksik_alanlar"]


@pytest.mark.parametrize(
    "kriter",
    ["en_dusuk_kar_payi", "en_yuksek_odul", "en_uzun_vade", "en_dusuk_masraf"],
)
def test_sartname_kriterlerinin_hepsi_matriste_var(kriter):
    """Md. 5.7 ornek listesindeki 4 basit kriterin dorduncu de sutun olmali."""
    sonuc = rakip_matrisi([_kayit("A")])
    assert any(e["kriter"] == kriter for e in sonuc["eksenler"])


def test_kompozit_kriter_matriste_sutun_degildir():
    """en_avantajli bir EKSEN degil, eksenlerin SONUCUDUR."""
    sonuc = rakip_matrisi([_kayit("A")])
    assert all(e["kriter"] != "en_avantajli" for e in sonuc["eksenler"])

"""Etki skoru testleri.

Uc seyi kilitler:
  1. YUZDELIK MATEMATIGI - elle hesaplanabilir kucuk kumelerde dogru mu?
  2. CEKIMSERLIK - kume/eksen yetersizse skor URETILMEZ (sifir yazilmaz)
  3. BOS ALAN SIFIR SAYILMAZ - belirtilmemis bir masraf "masrafsiz" degildir
"""

import pytest

from api.schemas import CampaignRecord, KampanyaTuru, YasamDongusu
from comparison.etki_skoru import (
    ASGARI_KUME,
    SKOR_EKSENLERI,
    eksen_yuzdeligi,
    etki_skoru,
    finansal_skor,
    karsilastirilabilir_kume,
)


def _kayit(
    banka: str,
    kar_payi: float | None = None,
    vade: int | None = None,
    odul: float | None = None,
    odul_birimi: str | None = None,
    masraf: float | None = None,
    tur: KampanyaTuru = KampanyaTuru.KONUT,
    durum: YasamDongusu = YasamDongusu.ACTIVE,
    kayit_id: int | None = None,
) -> CampaignRecord:
    return CampaignRecord(
        id=kayit_id,
        banka=banka,
        kampanya_adi=f"{banka} Kampanya",
        kaynak_url=f"https://ornek.test/{banka}",
        kampanya_turu=tur,
        durum=durum,
        kar_payi_orani_percent=kar_payi,
        vade_ay=vade,
        odul_miktari=odul,
        odul_birimi=odul_birimi,
        tahsis_ucreti=masraf,
    )


def _eksen(sonuc: dict, ad: str) -> dict:
    return next(e for e in sonuc["eksen_kirilimi"] if e["eksen"] == ad)


# ---------------------------------------------------------------------------
# Yuzdelik matematigi
# ---------------------------------------------------------------------------


def test_en_iyi_kayit_bir_alir_en_kotu_sifir():
    """Kar payinda DUSUK iyidir: 1.0 en iyi, 3.0 en kotu."""
    kume = [_kayit("A", kar_payi=1.0), _kayit("B", kar_payi=2.0), _kayit("C", kar_payi=3.0)]
    assert eksen_yuzdeligi(kume[0], kume, "en_dusuk_kar_payi")["yuzdelik"] == 1.0
    assert eksen_yuzdeligi(kume[1], kume, "en_dusuk_kar_payi")["yuzdelik"] == 0.5
    assert eksen_yuzdeligi(kume[2], kume, "en_dusuk_kar_payi")["yuzdelik"] == 0.0


def test_yuksek_iyi_eksende_yon_ters_calisir():
    """Vadede YUKSEK iyidir - yon dogru okunmali."""
    kume = [_kayit("A", vade=12), _kayit("B", vade=60), _kayit("C", vade=120)]
    assert eksen_yuzdeligi(kume[2], kume, "en_uzun_vade")["yuzdelik"] == 1.0
    assert eksen_yuzdeligi(kume[0], kume, "en_uzun_vade")["yuzdelik"] == 0.0


def test_esit_degerler_ayni_yuzdeligi_alir():
    """Biri digerine haksizca ustun gosterilmez."""
    kume = [_kayit("A", kar_payi=2.0), _kayit("B", kar_payi=2.0)]
    a = eksen_yuzdeligi(kume[0], kume, "en_dusuk_kar_payi")["yuzdelik"]
    b = eksen_yuzdeligi(kume[1], kume, "en_dusuk_kar_payi")["yuzdelik"]
    assert a == b == 0.5


def test_tek_olculebilir_deger_varken_siralama_yapilmaz():
    """Kime gore "iyi"? Tek degerle yuzdelik tanimsizdir."""
    kume = [_kayit("A", kar_payi=1.5), _kayit("B"), _kayit("C")]
    sonuc = eksen_yuzdeligi(kume[0], kume, "en_dusuk_kar_payi")
    assert sonuc["durum"] == "yetersiz_eksen_kume"
    assert sonuc["yuzdelik"] is None


def test_degeri_olmayan_kayit_o_eksende_olculmez():
    kume = [_kayit("A"), _kayit("B", kar_payi=2.0), _kayit("C", kar_payi=3.0)]
    sonuc = eksen_yuzdeligi(kume[0], kume, "en_dusuk_kar_payi")
    assert sonuc["durum"] == "deger_yok"
    assert sonuc["yuzdelik"] is None


def test_bos_alan_sifir_sayilmaz():
    """Masrafi BELIRTILMEMIS bir kampanya, masrafi 0 olan kampanyayla
    ayni muameleyi gormemeli - biri bilgi, digeri bilgisizlik."""
    belirtilmemis = _kayit("Bos", masraf=None)
    sifir = _kayit("Sifir", masraf=0)
    pahali = _kayit("Pahali", masraf=9000)
    kume = [belirtilmemis, sifir, pahali]

    assert _eksen(finansal_skor(sifir, kume), "en_dusuk_masraf")["yuzdelik"] == 1.0
    assert _eksen(finansal_skor(belirtilmemis, kume), "en_dusuk_masraf")["durum"] == "deger_yok"


# ---------------------------------------------------------------------------
# Cekimserlik
# ---------------------------------------------------------------------------


def test_kucuk_kumede_skor_uretilmez():
    """Altin veri setinde Tasit Finansmani turunde TEK kayit var - rakibi
    olmayan kampanyaya "piyasada onde" denemez."""
    tek = _kayit("Yalniz", kar_payi=1.5, vade=120)
    sonuc = finansal_skor(tek, [tek])
    assert sonuc["durum"] == "yetersiz_kume"
    assert sonuc["skor"] is None
    assert "kampanya var" in sonuc["sebep"]


def test_yeterli_kumede_skor_uretilir():
    kume = [
        _kayit("A", kar_payi=1.0, vade=120),
        _kayit("B", kar_payi=2.0, vade=60),
        _kayit("C", kar_payi=3.0, vade=12),
    ]
    sonuc = finansal_skor(kume[0], kume)
    assert sonuc["durum"] == "olculdu"
    assert sonuc["skor"] == 1.0  # iki eksende de en iyi
    assert sonuc["kullanilan_eksen"] == 2


def test_tek_eksen_olculebiliyorsa_skor_uretilmez():
    """Iki eksen olmadan "genel" bir skor iddia edilemez."""
    kume = [
        _kayit("A", kar_payi=1.0),
        _kayit("B", kar_payi=2.0),
        _kayit("C", kar_payi=3.0),
    ]
    sonuc = finansal_skor(kume[0], kume)
    assert sonuc["durum"] == "yetersiz_eksen"
    assert sonuc["skor"] is None
    assert sonuc["kullanilan_eksen"] == 1


def test_skor_olculen_eksenlerin_ortalamasidir():
    """A: kar payinda en iyi (1.0), vadede en kotu (0.0) -> 0.5"""
    kume = [
        _kayit("A", kar_payi=1.0, vade=12),
        _kayit("B", kar_payi=2.0, vade=60),
        _kayit("C", kar_payi=3.0, vade=120),
    ]
    assert finansal_skor(kume[0], kume)["skor"] == 0.5


# ---------------------------------------------------------------------------
# Odul birimi korumasi
# ---------------------------------------------------------------------------


def test_karisik_odul_birimi_ekseni_devre_disi_birakir():
    kume = [
        _kayit("A", kar_payi=1.0, vade=120, odul=10000, odul_birimi="Mil"),
        _kayit("B", kar_payi=2.0, vade=60, odul=5000, odul_birimi="TL"),
        _kayit("C", kar_payi=3.0, vade=12, odul=1000, odul_birimi="TL"),
    ]
    sonuc = finansal_skor(kume[0], kume)
    odul = _eksen(sonuc, "en_yuksek_odul")

    assert odul["durum"] == "birim_karisik"
    assert odul["yuzdelik"] is None
    assert sorted(odul["birimler"]) == ["Mil", "TL"]
    # Diger iki eksen olculdugu icin skor yine uretilir
    assert sonuc["durum"] == "olculdu"
    assert sonuc["kullanilan_eksen"] == 2


def test_ayni_birimde_odul_ekseni_calisir():
    kume = [
        _kayit("A", kar_payi=1.0, odul=10000, odul_birimi="TL"),
        _kayit("B", kar_payi=2.0, odul=5000, odul_birimi="TL"),
        _kayit("C", kar_payi=3.0, odul=1000, odul_birimi="TL"),
    ]
    odul = _eksen(finansal_skor(kume[0], kume), "en_yuksek_odul")
    assert odul["durum"] == "olculdu"
    assert odul["yuzdelik"] == 1.0
    assert odul["birim"] == "TL"


# ---------------------------------------------------------------------------
# Karsilastirilabilir kume
# ---------------------------------------------------------------------------


def test_farkli_tur_kumeye_girmez():
    """Konut finansmanini kart kampanyasiyla siralamak anlamsizdir."""
    konut = _kayit("A", tur=KampanyaTuru.KONUT)
    kume = karsilastirilabilir_kume(
        konut, [konut, _kayit("B", tur=KampanyaTuru.KART), _kayit("C", tur=KampanyaTuru.KONUT)]
    )
    assert {k.banka for k in kume} == {"A", "C"}


def test_suresi_dolmus_rakipler_kumeye_girmez():
    aktif = _kayit("A")
    kume = karsilastirilabilir_kume(
        aktif, [aktif, _kayit("Eski", durum=YasamDongusu.EXPIRED)]
    )
    assert {k.banka for k in kume} == {"A"}


def test_kayit_kumede_zaten_varsa_iki_kez_eklenmez():
    aktif = _kayit("A", kayit_id=7)
    kume = karsilastirilabilir_kume(aktif, [aktif, _kayit("B", kayit_id=8)])
    assert len(kume) == 2


def test_idsiz_kayitlar_ayni_sanilmaz():
    """DENETIM BULGUSU: id'si None olan iki kayit `None == None` yuzunden
    "ayni kayit" sayiliyordu; henuz veritabanina yazilmamis bir kampanya
    kendi kumesine hic eklenmiyordu."""
    yeni = _kayit("Yeni", kar_payi=1.0)
    baska = _kayit("Baska", kar_payi=2.0)
    assert yeni.id is None and baska.id is None
    assert len(karsilastirilabilir_kume(yeni, [baska])) == 2


def test_suresi_dolmus_kaydin_kendisi_yine_de_olculur():
    """Suresi dolmus bir kampanyayi goruntuleyen kullanici da "bu, bugunku
    tekliflere gore nerede duruyordu?" cevabini alabilmeli."""
    eski = _kayit("Eski", kar_payi=1.0, vade=120, durum=YasamDongusu.EXPIRED)
    aktifler = [_kayit("A", kar_payi=2.0, vade=60), _kayit("B", kar_payi=3.0, vade=12)]
    kume = karsilastirilabilir_kume(eski, [eski, *aktifler])

    assert len(kume) == 3
    assert finansal_skor(eski, [eski, *aktifler])["skor"] == 1.0


# ---------------------------------------------------------------------------
# Bilesik etki skoru
# ---------------------------------------------------------------------------


def test_etki_skoru_musteri_bilesenini_sifir_yazmaz():
    """Geri bildirim yoklugu "musteriler memnun degil" demek DEGILDIR."""
    kume = [
        _kayit("A", kar_payi=1.0, vade=120),
        _kayit("B", kar_payi=2.0, vade=60),
        _kayit("C", kar_payi=3.0, vade=12),
    ]
    sonuc = etki_skoru(kume[0], kume)

    assert sonuc["musteri_geri_bildirim"]["skor"] is None
    assert sonuc["musteri_geri_bildirim"]["durum"] == "veri_yok"
    assert sonuc["durum"] == "kismi"


def test_finansal_hesaplanamazsa_bilesik_de_hesaplanamaz():
    tek = _kayit("Yalniz", kar_payi=1.5)
    sonuc = etki_skoru(tek, [tek])
    assert sonuc["durum"] == "hesaplanamadi"
    assert sonuc["finansal"]["skor"] is None


def test_skor_tek_basina_dondurulmez_kirilim_hep_yaninda():
    """Tek bir sayiya bakip karar vermek, sayinin nereden geldigini
    gizlemek olur."""
    kume = [
        _kayit("A", kar_payi=1.0, vade=120),
        _kayit("B", kar_payi=2.0, vade=60),
        _kayit("C", kar_payi=3.0, vade=12),
    ]
    finansal = etki_skoru(kume[0], kume)["finansal"]
    assert len(finansal["eksen_kirilimi"]) == len(SKOR_EKSENLERI)
    assert finansal["karsilastirma_kumesi"] == 3


@pytest.mark.parametrize("eksen", SKOR_EKSENLERI)
def test_skor_eksenleri_sartname_kriterleridir(eksen):
    """Bonus kriter (en_yuksek_tutar) skora KATILMAZ - sartnamede olmayan
    bir agirlik eklemek olurdu."""
    assert eksen != "en_yuksek_tutar"
    assert len(SKOR_EKSENLERI) == 4


def test_asgari_kume_esigi_belgelenmis_degerde():
    """Esik degisirse test kirilsin - sessizce gevsetilmesin."""
    assert ASGARI_KUME == 3

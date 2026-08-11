"""Karsilastirma motoru testleri.

Ozellikle iki seyi kilitler:
  1. GUVENLIK: serbest metinden SQL uretilemez, kullanici degerleri parametre
  2. SEFFAFLIK: eksik veri gizlenmez, siralamada en sona gider (NULLS LAST)
"""

import pytest

from api.mock_data import MOCK_KAMPANYALAR
from api.schemas import CampaignRecord
from comparison.compare_engine import (
    KRITERLER,
    BilinmeyenKriter,
    aciklama_uret,
    karsilastir_bellekte,
    karsilastir_sorgusu,
    kriter_dogrula,
)

# ---------------------------------------------------------------------------
# Guvenlik: serbest metinden SQL uretilmez
# ---------------------------------------------------------------------------


def test_bilinmeyen_kriter_reddedilir():
    with pytest.raises(BilinmeyenKriter):
        kriter_dogrula("rastgele_bir_sey")


@pytest.mark.parametrize(
    "kotu_girdi",
    [
        "kar_payi; DROP TABLE kampanyalar;--",
        "1=1 OR TRUE",
        "kar_payi_orani_percent",  # gercek sutun adi bile olsa kriter degil
        "'; DELETE FROM kampanyalar; --",
    ],
)
def test_sql_enjeksiyon_denemeleri_kriter_asamasinda_durur(kotu_girdi):
    """Kullanici metni SQL'e ULASAMAZ: kriter sabit sozlukte yoksa hata."""
    with pytest.raises(BilinmeyenKriter):
        karsilastir_sorgusu(kotu_girdi)


def test_kullanici_degeri_sql_metnine_gomulmez():
    """kampanya_turu gibi kullanici degerleri PARAMETRE olarak gecer."""
    zararli = "Konut'; DROP TABLE kampanyalar;--"
    sorgu, parametreler = karsilastir_sorgusu(
        "en_dusuk_kar_payi", kampanya_turu=zararli
    )

    assert "DROP TABLE" not in sorgu
    assert zararli not in sorgu
    assert zararli in parametreler  # deger yalnizca parametre olarak tasindi
    assert sorgu.count("%s") == len(parametreler)


def test_uretilen_sql_nulls_last_icerir():
    """Eksik veri filtrelenmez, en sona gider."""
    sorgu, _ = karsilastir_sorgusu("en_dusuk_kar_payi")
    assert "NULLS LAST" in sorgu


def test_uretilen_sql_dogru_yonde_siralar():
    dusuk, _ = karsilastir_sorgusu("en_dusuk_kar_payi")
    yuksek, _ = karsilastir_sorgusu("en_uzun_vade")
    assert "kar_payi_orani_percent ASC" in dusuk
    assert "vade_ay DESC" in yuksek


def test_tum_kriterler_sql_uretebiliyor():
    for kriter in KRITERLER:
        sorgu, parametreler = karsilastir_sorgusu(kriter)
        assert sorgu.startswith("SELECT")
        assert "FROM kampanyalar" in sorgu
        assert sorgu.count("%s") == len(parametreler)


# ---------------------------------------------------------------------------
# Bellek modu: siralama dogrulugu
# ---------------------------------------------------------------------------


def test_en_dusuk_kar_payi_sartname_ornegiyle_uyusuyor():
    """Sartname Md. 5.7: C Bankasi (%1,87) < A (%1,89) < B (%1,95)."""
    abc = [k for k in MOCK_KAMPANYALAR if k.banka in ("A Bankasi", "B Bankasi", "C Bankasi")]
    sonuc = karsilastir_bellekte(abc, "en_dusuk_kar_payi")

    bankalar = [s["banka"] for s in sonuc["sonuclar"]]
    assert bankalar == ["C Bankasi", "A Bankasi", "B Bankasi"]
    assert sonuc["kazanan"]["banka"] == "C Bankasi"
    assert sonuc["kazanan"]["deger"] == 1.87


def test_en_uzun_vade_dogru_siralar():
    abc = [k for k in MOCK_KAMPANYALAR if k.banka in ("A Bankasi", "C Bankasi")]
    sonuc = karsilastir_bellekte(abc, "en_uzun_vade")
    assert sonuc["kazanan"]["banka"] == "A Bankasi"  # 120 ay > 96 ay


def test_eksik_deger_en_sona_gider_ASC():
    """D Bankasi'nin kar payi orani YOK - listenin sonunda olmali."""
    sonuc = karsilastir_bellekte(MOCK_KAMPANYALAR, "en_dusuk_kar_payi")
    assert sonuc["sonuclar"][-1]["banka"] == "D Bankasi"
    assert sonuc["sonuclar"][-1]["kriter_degeri"] is None


def test_eksik_deger_en_sona_gider_DESC():
    """Yon DESC olsa bile None degerler basa gecmemeli."""
    sonuc = karsilastir_bellekte(MOCK_KAMPANYALAR, "en_uzun_vade")
    son = sonuc["sonuclar"][-1]
    assert son["kriter_degeri"] is None
    # Ilk siradakinin degeri dolu olmali
    assert sonuc["sonuclar"][0]["kriter_degeri"] is not None


def test_eksik_kayit_gizlenmez_listede_kalir():
    """Seffaflik: orani olmayan kayit SILINMEZ, isaretlenerek gosterilir."""
    sonuc = karsilastir_bellekte(MOCK_KAMPANYALAR, "en_dusuk_kar_payi")
    bankalar = [s["banka"] for s in sonuc["sonuclar"]]
    assert "D Bankasi" in bankalar

    d = [s for s in sonuc["sonuclar"] if s["banka"] == "D Bankasi"][0]
    assert "kar_payi_orani_percent" in d["eksik_alanlar"]


def test_kazanan_eksik_veriden_secilmez():
    """Yalnizca kriter alani DOLU olan kayitlar kazanan olabilir."""
    yalniz_bos = [k for k in MOCK_KAMPANYALAR if k.banka == "D Bankasi"]
    sonuc = karsilastir_bellekte(yalniz_bos, "en_dusuk_kar_payi")
    assert sonuc["kazanan"] is None


def test_kampanya_turune_gore_filtreleme():
    sonuc = karsilastir_bellekte(
        MOCK_KAMPANYALAR, "en_dusuk_kar_payi", kampanya_turu="Kart Kampanyasi"
    )
    assert len(sonuc["sonuclar"]) == 1
    assert sonuc["sonuclar"][0]["banka"] == "D Bankasi"


def test_sira_numarasi_eklenir():
    sonuc = karsilastir_bellekte(MOCK_KAMPANYALAR, "en_dusuk_kar_payi")
    siralar = [s["sira"] for s in sonuc["sonuclar"]]
    assert siralar == list(range(1, len(siralar) + 1))


# ---------------------------------------------------------------------------
# Deterministik aciklama uretimi
# ---------------------------------------------------------------------------


def test_aciklama_kazanani_dogru_belirtir():
    abc = [k for k in MOCK_KAMPANYALAR if k.banka in ("A Bankasi", "C Bankasi")]
    metin = aciklama_uret(karsilastir_bellekte(abc, "en_dusuk_kar_payi"))
    assert "C Bankasi" in metin
    assert "1.87" in metin


def test_aciklama_eksik_veriyi_kullaniciya_bildirir():
    metin = aciklama_uret(karsilastir_bellekte(MOCK_KAMPANYALAR, "en_dusuk_kar_payi"))
    assert "belirtilmemis" in metin.lower()


def test_hicbir_veri_yoksa_aciklama_durustce_soyler():
    yalniz_bos = [k for k in MOCK_KAMPANYALAR if k.banka == "D Bankasi"]
    metin = aciklama_uret(karsilastir_bellekte(yalniz_bos, "en_dusuk_kar_payi"))
    assert "yapilamadi" in metin.lower()


# ---------------------------------------------------------------------------
# "en_avantajli" kompozit kriteri (Sartname Md. 5.7 - D1 bulgusu)
# ---------------------------------------------------------------------------


def test_en_avantajli_sartname_senaryo2_ile_uyusuyor():
    """Sartname Ornek Temsili Senaryo-2: 'A Bankasi mi daha avantajli, C
    Bankasi mi?' - kar payi acisindan C, vade acisindan A one cikiyor;
    C'nin ayrica odulu de var (A'da odul belirtilmemis) - C 2 eksende,
    A 1 eksende one cikiyor, genel kazanan C olmali."""
    ac = [k for k in MOCK_KAMPANYALAR if k.banka in ("A Bankasi", "C Bankasi")]
    sonuc = karsilastir_bellekte(ac, "en_avantajli")

    assert sonuc["kazanan"]["banka"] == "C Bankasi"
    assert sonuc["kazanan"]["deger"] == 2  # kar payi + odul eksenlerinde one cikti


def test_en_avantajli_eksen_kirilimi_sartname_metniyle_uyusuyor():
    ac = [k for k in MOCK_KAMPANYALAR if k.banka in ("A Bankasi", "C Bankasi")]
    sonuc = karsilastir_bellekte(ac, "en_avantajli")
    metin = aciklama_uret(sonuc)

    assert "kar payi" in metin.lower() and "c bankasi" in metin.lower()
    assert "vade" in metin.lower() and "a bankasi" in metin.lower()


def test_en_avantajli_esitlikte_tek_kazanan_uydurulmaz():
    """Iki kayit ayni sayida eksende one cikarsa, sahte bir tek kazanan
    secilmez - durustluk ilkesi (rapor Bolum 5.7/15) ile ayni gerekce."""
    esit = [
        CampaignRecord(banka="X Bankasi", kampanya_adi="X Kampanya", kaynak_url="https://x.com", kar_payi_orani_percent=1.5, vade_ay=60),
        CampaignRecord(banka="Y Bankasi", kampanya_adi="Y Kampanya", kaynak_url="https://y.com", kar_payi_orani_percent=1.8, vade_ay=96),
    ]
    sonuc = karsilastir_bellekte(esit, "en_avantajli")
    assert sonuc["kazanan"] is None
    metin = aciklama_uret(sonuc)
    assert "esit" in metin.lower() or "eşit" in metin.lower()


def test_en_avantajli_veri_olmayan_eksen_karsilastirmaya_katilmaz():
    """MOCK_KAMPANYALAR'da hicbir kayitta tahsis_ucreti sayisal olarak
    verilmemis - masraf ekseni sessizce degil, acikca 'veri yok' diye
    bildirilmeli."""
    ac = [k for k in MOCK_KAMPANYALAR if k.banka in ("A Bankasi", "C Bankasi")]
    sonuc = karsilastir_bellekte(ac, "en_avantajli")
    masraf_ekseni = next(e for e in sonuc["eksen_kirilimi"] if e["kriter"] == "en_dusuk_masraf")
    assert masraf_ekseni["kazananlar"] == []

    metin = aciklama_uret(sonuc)
    assert "veri yok" in metin.lower()


def test_en_avantajli_sql_onizlemesi_order_by_uydurmaz():
    """Kompozit kriter tek sutuna indirgenemez - SQL onizlemesinde
    uydurma bir ORDER BY olmamali, ama sorgu yine de gecerli SELECT
    olarak baslamali (test_tum_kriterler_sql_uretebiliyor ile tutarli)."""
    sorgu, _ = karsilastir_sorgusu("en_avantajli")
    assert sorgu.startswith("SELECT")
    assert "ORDER BY" not in sorgu


def test_en_avantajli_kriter_dogrulamadan_geciyor():
    kriter_dogrula("en_avantajli")  # BilinmeyenKriter firlatmamali

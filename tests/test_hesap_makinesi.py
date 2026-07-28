"""Hesap Makinesi testleri.

FINANSAL HESAP OLDUGU ICIN: Bu testler yalnizca "kod calisiyor mu" degil,
"sonuc DOGRU mu" sorusunu da yanitlar. Beklenen degerler elle/bagimsiz
hesaplanmis ve amortisman tablosuyla capraz dogrulanmistir.

Bu fonksiyon yanlis olursa tum sistem yanlis sayi uretir -- bu yuzden
testler normalden daha siki.
"""

import pytest

from calculator.calculator import (
    HesapGirdiHatasi,
    aylik_taksit_hesapla,
    maksimum_finansman_hesapla,
    odeme_plani_uret,
    toplam_maliyet_karsilastir,
)

# ---------------------------------------------------------------------------
# Dogruluk: elle hesaplanmis referans degerler
# ---------------------------------------------------------------------------


def test_anuite_formulu_dogru_sonuc_verir():
    """Referans: 500.000 TL, aylik %1,89, 120 ay.

    Elle hesap:
      (1.0189)^120 = 9.457742
      taksit = 500000 * (0.0189 * 9.457742) / (9.457742 - 1) = 10567.32
    """
    s = aylik_taksit_hesapla(500_000, 0.0189, 120)
    assert s.aylik_taksit == pytest.approx(10567.32, abs=0.01)
    assert s.toplam_odeme == pytest.approx(1_268_078.34, abs=0.5)
    assert s.toplam_kar_payi == pytest.approx(768_078.34, abs=0.5)


def test_toplam_odeme_taksit_carpi_vade_esittir():
    s = aylik_taksit_hesapla(250_000, 0.0195, 60)
    assert s.toplam_odeme == pytest.approx(s.aylik_taksit * s.vade_ay, abs=0.01)


def test_toplam_kar_payi_toplam_eksi_anapara():
    s = aylik_taksit_hesapla(300_000, 0.0187, 96)
    assert s.toplam_kar_payi == pytest.approx(s.toplam_odeme - s.anapara, abs=0.01)


def test_odeme_plani_sifirla_biter():
    """EN GUCLU DOGRULAMA: Amortisman tablosu, taksit hesabindan bagimsiz
    olarak ay ay yurur. Son ayda kalan bakiye 0 degilse formul yanlistir."""
    plan = odeme_plani_uret(500_000, 0.0189, 120)
    assert len(plan) == 120
    assert plan[-1].kalan_bakiye == 0.0


def test_odeme_planinda_anapara_kismi_zamanla_artar():
    """Anuite'de basta kar payi agirlikli, sonda anapara agirliklidir."""
    plan = odeme_plani_uret(500_000, 0.0189, 120)
    assert plan[0].anapara_kismi < plan[-1].anapara_kismi
    assert plan[0].kar_payi_kismi > plan[-1].kar_payi_kismi


def test_odeme_planindaki_anapara_toplami_anaparaya_esit():
    plan = odeme_plani_uret(100_000, 0.02, 24)
    toplam_anapara = sum(satir.anapara_kismi for satir in plan)
    assert toplam_anapara == pytest.approx(100_000, abs=0.5)


# ---------------------------------------------------------------------------
# Sifir oranli kampanya (rapor Bolum 3: Albaraka "Kar payi yok" ornegi)
# ---------------------------------------------------------------------------


def test_sifir_oran_bolme_hatasi_vermez():
    """Formul 0 oranda (1+0)^n - 1 = 0 verir -> 0'a bolme.
    Bu durum ayrica ele alinmali."""
    s = aylik_taksit_hesapla(120_000, 0.0, 12)
    assert s.aylik_taksit == 10_000.0
    assert s.toplam_kar_payi == 0.0
    assert s.toplam_odeme == 120_000.0


def test_sifir_oranda_odeme_plani_da_calisir():
    plan = odeme_plani_uret(120_000, 0.0, 12)
    assert plan[-1].kalan_bakiye == 0.0
    assert all(satir.kar_payi_kismi == 0.0 for satir in plan)


# ---------------------------------------------------------------------------
# Girdi dogrulama: sessizce yanlis sonuc yerine acik hata
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "anapara,oran,vade",
    [
        (0, 0.0189, 120),          # sifir anapara
        (-1000, 0.0189, 120),      # negatif anapara
        (500_000, 0.0189, 0),      # sifir vade
        (500_000, 0.0189, -12),    # negatif vade
        (500_000, -0.01, 120),     # negatif oran
        (500_000, 0.0189, 9999),   # asiri uzun vade
        (10**12, 0.0189, 120),     # asiri buyuk anapara
    ],
)
def test_gecersiz_girdi_reddedilir(anapara, oran, vade):
    with pytest.raises(HesapGirdiHatasi):
        aylik_taksit_hesapla(anapara, oran, vade)


def test_yillik_oran_yanlislikla_girilirse_yakalanir():
    """Yaygin hata: %22,68 yillik orani 0.2268 olarak aylik sanmak.
    Bu, sessizce sacma bir taksit uretmek yerine hata vermeli."""
    with pytest.raises(HesapGirdiHatasi, match="AYLIK"):
        aylik_taksit_hesapla(500_000, 0.2268, 120)


# ---------------------------------------------------------------------------
# Ters hesap: butceden finansman tutari
# ---------------------------------------------------------------------------


def test_maksimum_finansman_taksit_hesabiyla_tutarli():
    """Ters hesap dogruysa: butce ile bulunan anaparayi geri hesaplayinca
    ayni taksit cikmali."""
    butce, oran, vade = 10_567.32, 0.0189, 120
    anapara = maksimum_finansman_hesapla(butce, oran, vade)
    assert anapara == pytest.approx(500_000, abs=50)

    geri = aylik_taksit_hesapla(anapara, oran, vade)
    assert geri.aylik_taksit == pytest.approx(butce, abs=0.5)


def test_sifir_oranda_maksimum_finansman():
    assert maksimum_finansman_hesapla(1_000, 0.0, 12) == 12_000.0


def test_negatif_butce_reddedilir():
    with pytest.raises(HesapGirdiHatasi):
        maksimum_finansman_hesapla(-100, 0.0189, 120)


# ---------------------------------------------------------------------------
# Karsilastirma: dusuk oran her zaman ucuz degildir
# ---------------------------------------------------------------------------


def test_karsilastirma_toplam_maliyete_gore_siralar():
    sonuc = toplam_maliyet_karsilastir([
        {"banka": "A Bankasi", "anapara": 500_000, "aylik_oran": 0.0189, "vade_ay": 120},
        {"banka": "C Bankasi", "anapara": 500_000, "aylik_oran": 0.0187, "vade_ay": 96},
    ])
    # C daha dusuk oran VE daha kisa vade -> toplamda daha ucuz olmali
    assert sonuc.en_dusuk_toplam_maliyet["banka"] == "C Bankasi"
    assert sonuc.secenekler[0]["banka"] == "C Bankasi"


def test_uzun_vade_dusuk_taksit_ama_yuksek_toplam_maliyet():
    """Sartname senaryosundaki gercek tuzak: A Bankasi daha uzun vade
    sunuyor -> aylik taksiti dusuk ama toplam maliyeti yuksek.
    Aciklama bunu kullaniciya SOYLEMELI."""
    sonuc = toplam_maliyet_karsilastir([
        {"banka": "A Bankasi", "anapara": 500_000, "aylik_oran": 0.0189, "vade_ay": 120},
        {"banka": "C Bankasi", "anapara": 500_000, "aylik_oran": 0.0187, "vade_ay": 96},
    ])
    a = [s for s in sonuc.secenekler if s["banka"] == "A Bankasi"][0]
    c = [s for s in sonuc.secenekler if s["banka"] == "C Bankasi"][0]

    assert a["aylik_taksit"] < c["aylik_taksit"]      # A'nin taksiti dusuk
    assert a["toplam_odeme"] > c["toplam_odeme"]      # ama toplami yuksek
    assert "aylik yuku azaltir" in sonuc.aciklama     # kullaniciya aciklaniyor


def test_bos_karsilastirma_cokmez():
    sonuc = toplam_maliyet_karsilastir([])
    assert sonuc.en_dusuk_toplam_maliyet is None
    assert "yok" in sonuc.aciklama.lower()


# ---------------------------------------------------------------------------
# Ozet metni: LLM'e birakilmadan, dogrudan sayilardan uretilir
# ---------------------------------------------------------------------------


def test_ozet_metni_gercek_sayilari_icerir():
    s = aylik_taksit_hesapla(500_000, 0.0189, 120)
    metin = s.ozet_metni()
    assert "10,567.32" in metin
    assert "120 ay" in metin
    assert "1.89" in metin


def test_sonuc_degistirilemez():
    """frozen dataclass: sonuc uretildikten sonra uzerine yazilamaz."""
    s = aylik_taksit_hesapla(500_000, 0.0189, 120)
    with pytest.raises(Exception):
        s.aylik_taksit = 999.0

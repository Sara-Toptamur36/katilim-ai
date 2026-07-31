"""extraction/normalizer.py birim testleri."""

from extraction.normalizer import aya_cevir, tarihe_cevir, turkce_kucult, tutara_cevir, yuzdeye_cevir


def test_turkce_kucult_noktali_i_dogru_kucultur():
    assert turkce_kucult("İndirim") == "indirim"
    assert turkce_kucult("KAR PAYI İÇİN") == "kar payi için"


def test_yuzdeye_cevir_virgullu_yuzdeyi_ondalik_orana_cevirir():
    assert yuzdeye_cevir("%1,89") == 0.0189


def test_yuzdeye_cevir_nokta_ayiracli_ve_bosluklu_yuzdeyi_cevirir():
    assert yuzdeye_cevir("% 2.05") == 0.0205
    assert yuzdeye_cevir("2.05 %") == 0.0205


def test_yuzdeye_cevir_eslesme_yoksa_none_doner():
    assert yuzdeye_cevir("kar payı yoktur") is None


def test_tutara_cevir_binlik_ve_ondalik_ayiraci_dogru_ayirir():
    assert tutara_cevir("500 TL") == 500.0
    assert tutara_cevir("50.000 TL") == 50000.0
    assert tutara_cevir("50.000,50 TL") == 50000.5


def test_tarihe_cevir_nokta_ayiracli_tarihi_iso_formatina_cevirir():
    assert tarihe_cevir("31.12.2026") == "2026-12-31"
    assert tarihe_cevir("31/12/2026") == "2026-12-31"


def test_tarihe_cevir_turkce_ay_adini_iso_formatina_cevirir():
    assert tarihe_cevir("31 Aralık 2026") == "2026-12-31"


def test_tarihe_cevir_gecersiz_girdide_none_doner():
    assert tarihe_cevir("belirsiz bir tarih") is None


def test_aya_cevir_ay_ifadesini_int_dondurur():
    assert aya_cevir("120 ay") == 120
    assert aya_cevir("120 aya kadar") == 120


def test_aya_cevir_yil_ifadesini_aya_cevirir():
    assert aya_cevir("10 yıl") == 120

"""agent/parametre_cikar.py testleri."""

import pytest

from agent.parametre_cikar import eksik_parametreler, hesaplama_parametrelerini_cikar


def test_tum_parametreler_dogru_cikarilir():
    soru = "500.000 TL, %1,99 oranla 24 ay vadeyle taksitim ne kadar olur?"
    p = hesaplama_parametrelerini_cikar(soru)
    assert p["anapara"] == 500000.0
    assert p["aylik_oran_percent"] == 1.99
    assert p["vade_ay"] == 24


def test_yil_cinsinden_vade_aya_cevrilir():
    p = hesaplama_parametrelerini_cikar("100.000 TL, %2 oranla 2 yil vadeyle")
    assert p["vade_ay"] == 24


def test_eksik_alan_none_kalir_uydurulmaz():
    """Rapor Bolum 5.7/15: bulunamayan alan None kalir, tahmini deger
    URETILMEZ."""
    p = hesaplama_parametrelerini_cikar("Taksitimi hesaplar misin?")
    assert p["anapara"] is None
    assert p["aylik_oran_percent"] is None
    assert p["vade_ay"] is None


def test_eksik_parametreler_dogru_listelenir():
    p = {"anapara": 500000.0, "aylik_oran_percent": None, "vade_ay": None}
    assert eksik_parametreler(p) == ["aylik_oran_percent", "vade_ay"]


def test_binlik_ayiracli_tutar_dogru_parse_edilir():
    p = hesaplama_parametrelerini_cikar("1.250.000 TL icin %3 oranla 36 ay")
    assert p["anapara"] == 1250000.0


# ---------------------------------------------------------------------------
# TUTAR - SESSIZ YANLIS CEVAP HATASI (canli /chat testinde bulundu, 14 Agustos)
#
# Eski desen `(\d{1,3}(?:\.\d{3})*...)` binlik ayiraci OLMAYAN sayilarda
# sayinin yalnizca SON UC HANESINI yakaliyordu (regex anchorlu olmadigi
# icin metnin ortasindan eslesme basliyordu):
#     "1234 TL"   -> 234   ve arac basarili=True donup 234 TL icin
#                          odeme plani uretiyordu (SESSIZ YANLIS CEVAP)
#     "500000 TL" -> 000 -> 0.0 -> calculator "Anapara pozitif olmalidir"
# Bu, projenin tum tasariminin onlemeye calistigi hata sinifidir; bu
# yuzden testler once sessiz-yanlis vakayi kilitler.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "soru,beklenen",
    [
        ("1234 TL, %2 oranla 12 ay vadeyle taksitim ne kadar?", 1234.0),
        ("12345 TL, %2 oranla 12 ay vadeyle taksitim ne kadar?", 12345.0),
        ("500000 TL, %2 oranla 24 ay vadeyle taksitim ne kadar?", 500000.0),
        ("75000 TL, %1,5 oranla 36 ay vadeyle", 75000.0),
        ("2000000 TL icin 120 ay", 2000000.0),
    ],
)
def test_binlik_ayiracsiz_tutar_tam_olarak_okunur(soru, beklenen):
    """Kullanicilarin cogu binlik ayiraci yazmaz."""
    assert hesaplama_parametrelerini_cikar(soru)["anapara"] == beklenen


@pytest.mark.parametrize(
    "soru,beklenen",
    [
        ("500.000 TL, %1,99 oranla 24 ay", 500000.0),
        ("1.250.000 TL icin %3 oranla 36 ay", 1250000.0),
        ("1.500.000,50 TL icin %3 oranla 36 ay", 1500000.5),
        ("100.000 ₺ ile %2 oranla 12 ay", 100000.0),
    ],
)
def test_binlik_ayiracli_yazimlar_bozulmadi(soru, beklenen):
    """Duzeltme, calisan yazimlari bozmamali (regresyon kilidi)."""
    assert hesaplama_parametrelerini_cikar(soru)["anapara"] == beklenen


def test_belirsiz_tutar_yazimi_uydurulmaz():
    """'2.79 TL' Turkce yazimda gecerli bir tutar DEGILDIR (nokta binlik
    ayiractir, ardindan uc hane gelmeli). Boyle bir ifadeden tahmini
    deger URETILMEZ - alan None kalir ve kullanicidan bilgi istenir
    (rapor Bolum 5.7/15 seffaflik ilkesi)."""
    assert hesaplama_parametrelerini_cikar("2.79 TL, %2 oranla 12 ay")["anapara"] is None


# ---------------------------------------------------------------------------
# ORAN - iki ayri hata
#   1) "yuzde" kelimesi hic taninmıyordu (yalnizca "%" isareti)
#   2) "%2.79" -> 279.0 (SESSIZ YANLIS): oran cevrimi noktayi BINLIK
#      ayiraci sanip siliyordu. Oranda binlik ayiraci OLMAZ; hem virgul
#      hem nokta ONDALIK ayiracidir.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "soru,beklenen",
    [
        ("500.000 TL, %1,99 oranla 24 ay", 1.99),
        ("500.000 TL, %1.99 oranla 24 ay", 1.99),
        ("500.000 TL, % 2 oranla 24 ay", 2.0),
        ("2.000.000 TL, aylik yuzde 2.79 ile 120 ay", 2.79),
        ("2.000.000 TL, aylik yüzde 2,79 ile 120 ay", 2.79),
        ("2.000.000 TL, aylik YÜZDE 2,79 ile 120 ay", 2.79),
    ],
)
def test_oran_yazim_bicimlerinin_hepsi_tanınir(soru, beklenen):
    assert hesaplama_parametrelerini_cikar(soru)["aylik_oran_percent"] == beklenen


def test_oranda_nokta_binlik_ayiraci_sayilmaz():
    """En kritik oran vakasi: %2.79 -> 279.0 olsaydi hesaplanan taksit
    yuz kat sisecek ama sistem yine 'basarili' diyecekti."""
    p = hesaplama_parametrelerini_cikar("500.000 TL, %2.79 oranla 24 ay")
    assert p["aylik_oran_percent"] == 2.79

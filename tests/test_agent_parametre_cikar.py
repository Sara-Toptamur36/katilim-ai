"""agent/parametre_cikar.py testleri."""

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

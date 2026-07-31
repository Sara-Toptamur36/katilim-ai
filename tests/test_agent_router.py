"""agent/router.py testleri."""

from datetime import date

from agent.router import (
    hesaplama_aracini_cagir,
    karsilastirma_aracini_cagir,
    sozluk_aracini_cagir,
)
from api.schemas import CampaignRecord


def _kayit(banka: str, oran_percent: float | None, oran_decimal: float | None = None) -> CampaignRecord:
    return CampaignRecord(
        banka=banka,
        kampanya_adi=f"{banka} Ornek Kampanya",
        kaynak_url="https://ornek.com",
        kar_payi_orani_percent=oran_percent,
        kar_payi_orani_decimal=oran_decimal if oran_decimal is not None else (
            oran_percent / 100 if oran_percent is not None else None
        ),
    )


# ---------------------------------------------------------------------------
# Calculator Tool
# ---------------------------------------------------------------------------


def test_hesaplama_araci_dogru_hesap_yapar():
    sonuc = hesaplama_aracini_cagir("500.000 TL, %1,99 oranla 24 ay vadeyle taksitim ne kadar olur?")
    assert sonuc["basarili"] is True
    assert sonuc["veri"]["anapara"] == 500000.0
    assert sonuc["veri"]["aylik_taksit"] > 0


def test_hesaplama_araci_eksik_parametrede_sebep_bildirir():
    sonuc = hesaplama_aracini_cagir("Taksitimi hesaplar misin?")
    assert sonuc["basarili"] is False
    assert "anapara" in sonuc["sebep"]


# ---------------------------------------------------------------------------
# Dictionary Tool
# ---------------------------------------------------------------------------


def test_sozluk_araci_bilinen_terimi_bulur():
    sonuc = sozluk_aracini_cagir("Kâr payı oranı ne demek?")
    assert sonuc["basarili"] is True
    assert "Faiz" in sonuc["cevap"] or "faiz" in sonuc["cevap"].lower()


def test_sozluk_araci_alakasiz_terimde_basarisiz_doner():
    sonuc = sozluk_aracini_cagir("Marsta hayat var mi nedir?")
    assert sonuc["basarili"] is False


# ---------------------------------------------------------------------------
# Comparison (SQL) Tool
# ---------------------------------------------------------------------------


def test_karsilastirma_araci_iki_taninan_banka_ile_calisir():
    def sahte_getirici(banka: str) -> list[CampaignRecord]:
        veriler = {
            "Kuveyt Türk": [_kayit("Kuveyt Türk", 1.99)],
            "Albaraka Türk": [_kayit("Albaraka Türk", 1.5)],
        }
        return veriler.get(banka, [])

    soru = "Kuveyt Türk ile Albaraka Türk'ü karsilastir, en dusuk oranli hangisi?"
    sonuc = karsilastirma_aracini_cagir(soru, sahte_getirici)
    assert sonuc["basarili"] is True
    assert sonuc["veri"]["kriter"] == "en_dusuk_kar_payi"


def test_karsilastirma_araci_tek_banka_tespit_edilirse_basarisiz_doner():
    """Rapor Bolum 5.7/15: yetersiz bilgi sessizce yanlis cevaba
    donusturulmez, acikca bildirilir."""
    def sahte_getirici(banka: str) -> list[CampaignRecord]:
        return [_kayit(banka, 1.0)]

    sonuc = karsilastirma_aracini_cagir("Kuveyt Türk'ün orani nedir?", sahte_getirici)
    assert sonuc["basarili"] is False
    assert "banka" in sonuc["sebep"].lower()


def test_karsilastirma_kriteri_soru_metninden_dogru_tespit_edilir():
    def sahte_getirici(banka: str) -> list[CampaignRecord]:
        return [
            CampaignRecord(
                banka=banka,
                kampanya_adi="Ornek",
                kaynak_url="https://ornek.com",
                odul_miktari=1000.0 if banka == "Kuveyt Türk" else 500.0,
                odul_birimi="TL",
            )
        ]

    soru = "Kuveyt Türk ile Albaraka Türk'te en yuksek odul hangisinde?"
    sonuc = karsilastirma_aracini_cagir(soru, sahte_getirici)
    assert sonuc["basarili"] is True
    assert sonuc["veri"]["kriter"] == "en_yuksek_odul"

"""agent/orchestrator.py testleri - Intent Detection + Tool Router
zincirinin uctan uca dogrulamasi (kaynak katmanindan bagimsiz, sahte
kayit_getirici ile)."""

from api.schemas import CampaignRecord


def _sahte_getirici(banka: str) -> list[CampaignRecord]:
    veriler = {
        "Kuveyt Türk": [CampaignRecord(
            banka="Kuveyt Türk", kampanya_adi="Ornek", kaynak_url="https://ornek.com",
            kar_payi_orani_percent=1.99, kar_payi_orani_decimal=0.0199,
        )],
        "Albaraka Türk": [CampaignRecord(
            banka="Albaraka Türk", kampanya_adi="Ornek", kaynak_url="https://ornek.com",
            kar_payi_orani_percent=1.5, kar_payi_orani_decimal=0.015,
        )],
    }
    return veriler.get(banka, [])


def test_hesaplama_sorusu_calculator_araciyla_cevaplanir():
    from agent.orchestrator import soru_isle

    sonuc = soru_isle("500.000 TL, %1,99 oranla 24 ay vadeyle taksitim ne kadar olur?", _sahte_getirici)
    assert sonuc["audit_ekstra"]["intent"] == "hesaplama"
    assert sonuc["audit_ekstra"]["cagrilan_arac"] == "calculator"
    assert sonuc["confidence"] == 1.0
    assert sonuc["fallback"] is False


def test_sozluk_sorusu_dictionary_araciyla_cevaplanir():
    from agent.orchestrator import soru_isle

    sonuc = soru_isle("Kâr payı oranı nedir?", _sahte_getirici)
    assert sonuc["audit_ekstra"]["cagrilan_arac"] == "dictionary"


def test_karsilastirma_sorusu_sql_araciyla_cevaplanir():
    from agent.orchestrator import soru_isle

    sonuc = soru_isle("Kuveyt Türk ile Albaraka Türk'ü karsilastir", _sahte_getirici)
    assert sonuc["audit_ekstra"]["cagrilan_arac"] == "sql"
    assert sonuc["fallback"] is False


def test_bilinmeyen_soru_fallback_araciyla_cevaplanir_ve_sebep_belirtilir():
    """Rapor Bolum 5.7/15: RAG henuz baglanmadigi icin taninmayan sorular
    ACIKCA fallback'e duser, sessizce yanlis/uydurma cevap uretilmez."""
    from agent.orchestrator import soru_isle

    sonuc = soru_isle("Bugun hava nasil?", _sahte_getirici)
    assert sonuc["audit_ekstra"]["cagrilan_arac"] == "fallback"
    assert sonuc["fallback"] is True
    assert sonuc["confidence"] == 0.0
    assert sonuc["audit_ekstra"]["sebep"] is not None


def test_audit_ekstra_tum_alanlari_icerir():
    """Juri Audit Paneli'nin bekledigi alanlarin hepsi VAR olmali
    (rapor Bolum 10.2)."""
    from agent.orchestrator import soru_isle

    sonuc = soru_isle("test", _sahte_getirici)
    for alan in ("intent", "intent_confidence", "cagrilan_arac", "latency_ms", "sebep"):
        assert alan in sonuc["audit_ekstra"], f"Audit alani eksik: {alan}"


def test_latency_olculur():
    from agent.orchestrator import soru_isle

    sonuc = soru_isle("taksit hesapla", _sahte_getirici)
    assert sonuc["audit_ekstra"]["latency_ms"] >= 0

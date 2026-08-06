"""agent/orchestrator.py testleri - Intent Detection + Tool Router
zincirinin uctan uca dogrulamasi (kaynak katmanindan bagimsiz, sahte
kayit_getirici ile)."""

from api.schemas import CampaignRecord


def _sahte_rag(soru: str) -> dict:
    """Kaynak bulamayan sahte RAG araci.

    Bu dosya YONLENDIRME mantigini test eder, retrieval kalitesini degil.
    Gercek RAG kullanilsaydi her test embedding modelini yukleyip Qdrant'a
    baglanirdi (olculdu: 2 sn -> 121 sn). Gercek RAG yolunun uctan uca
    testi tests/test_rag_uctan_uca.py'de, Qdrant yoksa atlanarak yapilir.
    """
    return {
        "basarili": False,
        "cevap": "Bu soruyu yanitlayacak yeterli kaynak bulamadim.",
        "sebep": "Yeterli kaynak bulunamadi (sahte RAG)",
    }


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

    sonuc = soru_isle("500.000 TL, %1,99 oranla 24 ay vadeyle taksitim ne kadar olur?", _sahte_getirici, rag_araci=_sahte_rag)
    assert sonuc["audit_ekstra"]["intent"] == "hesaplama"
    assert sonuc["audit_ekstra"]["cagrilan_arac"] == "calculator"
    assert sonuc["confidence"] == 1.0
    assert sonuc["fallback"] is False


def test_sozluk_sorusu_dictionary_araciyla_cevaplanir():
    from agent.orchestrator import soru_isle

    sonuc = soru_isle("Kâr payı oranı nedir?", _sahte_getirici, rag_araci=_sahte_rag)
    assert sonuc["audit_ekstra"]["cagrilan_arac"] == "dictionary"


def test_karsilastirma_sorusu_sql_araciyla_cevaplanir():
    from agent.orchestrator import soru_isle

    sonuc = soru_isle("Kuveyt Türk ile Albaraka Türk'ü karsilastir", _sahte_getirici, rag_araci=_sahte_rag)
    assert sonuc["audit_ekstra"]["cagrilan_arac"] == "sql"
    assert sonuc["fallback"] is False


def test_kaynak_bulunamayan_soru_fallbacke_duser_ve_sebep_belirtilir():
    """Rapor Bolum 5.7/15: RAG de kaynak bulamazsa sistem ACIKCA
    cekimser kalir - sessizce yanlis/uydurma cevap uretilmez."""
    from agent.orchestrator import soru_isle

    sonuc = soru_isle("Bugun hava nasil?", _sahte_getirici, rag_araci=_sahte_rag)
    assert sonuc["audit_ekstra"]["cagrilan_arac"] == "fallback"
    assert sonuc["fallback"] is True
    assert sonuc["confidence"] == 0.0
    assert sonuc["audit_ekstra"]["sebep"] is not None


def test_audit_ekstra_tum_alanlari_icerir():
    """Juri Audit Paneli'nin bekledigi alanlarin hepsi VAR olmali
    (rapor Bolum 10.2)."""
    from agent.orchestrator import soru_isle

    sonuc = soru_isle("test", _sahte_getirici, rag_araci=_sahte_rag)
    for alan in (
        "intent", "intent_confidence", "cagrilan_arac", "latency_ms", "sebep",
        "extraction_confidence", "regex_basari_orani",
    ):
        assert alan in sonuc["audit_ekstra"], f"Audit alani eksik: {alan}"


def test_karsilastirma_sorusunda_extraction_confidence_doldurulur():
    """Regex motoruyla (extraction/regex_extractor.py) zenginlestirilmis
    kayitlar karsilastirmada kullanildiginda, audit panelindeki
    extraction_confidence/regex_basari_orani ARTIK sabit 0.0/None DEGIL,
    kullanilan kayitlarin gercek guven skorlarindan hesaplanmali."""
    from agent.orchestrator import soru_isle

    def zengin_getirici(banka: str) -> list[CampaignRecord]:
        veriler = {
            "Kuveyt Türk": [CampaignRecord(
                banka="Kuveyt Türk", kampanya_adi="Ornek", kaynak_url="https://ornek.com",
                kar_payi_orani_percent=1.99, confidence=0.8, cikarim_yontemi="regex",
            )],
            "Albaraka Türk": [CampaignRecord(
                banka="Albaraka Türk", kampanya_adi="Ornek", kaynak_url="https://ornek.com",
                kar_payi_orani_percent=1.5, confidence=0.6, cikarim_yontemi="regex",
            )],
        }
        return veriler.get(banka, [])

    sonuc = soru_isle("Kuveyt Türk ile Albaraka Türk'ü karsilastir", zengin_getirici, rag_araci=_sahte_rag)
    assert sonuc["audit_ekstra"]["extraction_confidence"] == 0.7
    assert sonuc["audit_ekstra"]["regex_basari_orani"] == 1.0


def test_hesaplama_sorusunda_extraction_confidence_none_kalir():
    """Kampanya kaydi kullanmayan araclarda (hesaplama/sozluk) bu alanlarin
    anlami yok - sessizce 0 uretmek yerine ACIKCA None kalmali."""
    from agent.orchestrator import soru_isle

    sonuc = soru_isle("500.000 TL, %1,99 oranla 24 ay vadeyle taksitim ne kadar olur?", _sahte_getirici, rag_araci=_sahte_rag)
    assert sonuc["audit_ekstra"]["extraction_confidence"] is None
    assert sonuc["audit_ekstra"]["regex_basari_orani"] is None


def test_arac_yetersiz_kalirsa_raga_geri_cekilir():
    """DENETIM BULGUSU: Anahtar kelime tabanli niyet tespiti dogal
    sorularda yanilabiliyor - "Ziraat Katilim kart kampanyalarinda TAKSIT
    var mi?" yalnizca "taksit" kelimesi yuzunden hesap makinesine gidiyor
    ve kullaniciya "Hesaplama icin su bilgiler eksik: anapara..." deniyordu.
    Oysa bu bir BILGI sorusu ve cevabi kaynaklarda var.

    Secilen arac basarisiz olursa RAG'e geri cekilinmeli."""
    from agent.orchestrator import soru_isle

    def basarili_rag(soru: str) -> dict:
        return {
            "basarili": True,
            "cevap": "Kaynaklarda bulduklarim: ...",
            "kaynaklar": [{"kaynak_url": "https://ornek.com", "similarity_score": 0.9}],
        }

    sonuc = soru_isle(
        "Ziraat Katılım kart kampanyalarında taksit var mı?",
        _sahte_getirici,
        rag_araci=basarili_rag,
    )
    assert sonuc["audit_ekstra"]["cagrilan_arac"] == "rag"
    assert sonuc["fallback"] is False
    assert sonuc["kaynaklar"]
    # Ilk aracin neden yetmedigi audit'te KORUNMALI (juri paneli icin)
    assert "calculator" in (sonuc["audit_ekstra"]["sebep"] or "")


def test_rag_de_bulamazsa_ilk_aracin_cevabi_korunur():
    """Geri cekilme, cevabi UYDURMAYA donusmemeli: RAG de kaynak
    bulamazsa sistem yine acikca cekimser kalir."""
    from agent.orchestrator import soru_isle

    sonuc = soru_isle("taksitimi hesapla", _sahte_getirici, rag_araci=_sahte_rag)
    assert sonuc["fallback"] is True
    assert sonuc["confidence"] == 0.0
    assert sonuc["audit_ekstra"]["sebep"]


def test_latency_olculur():
    from agent.orchestrator import soru_isle

    sonuc = soru_isle("taksit hesapla", _sahte_getirici, rag_araci=_sahte_rag)
    assert sonuc["audit_ekstra"]["latency_ms"] >= 0

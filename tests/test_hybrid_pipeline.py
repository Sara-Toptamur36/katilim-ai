"""extraction/hybrid_pipeline.py testleri (Sprint 2 Gun 3).

Bazi testler ner_ile_cikar/llm_ile_cikar'i monkeypatch ile izole eder
(regex'in doldurdugu bir alanin asla ezilmedigini, gereksiz yere NER/LLM
cagrilmadigini kanitlamak icin - bu, gercek model/servis cagirmadan
DAVRANISI dogrular). Diger testler gercek GLiNER/Ollama servisleriyle
uctan uca calisir (diger test dosyalarindaki AYNI kural).
"""

import json
from pathlib import Path

import extraction.hybrid_pipeline as hp
from extraction.hybrid_pipeline import kaydi_hibrit_cikar

RAW_DATA = Path(__file__).parent.parent / "scraper" / "raw_data"


def test_regex_her_seyi_doldurursa_ner_ve_llm_hic_cagrilmaz(monkeypatch):
    """Performans kurali: regex zaten tum alanlari doldurmussa, NER model
    yuklemesi ve Ollama'ya HTTP istegi gibi pahali islemler HIC
    tetiklenmemeli."""

    def _cagrilirsa_patlat(*args, **kwargs):
        raise AssertionError("NER/LLM cagrilmamali - regex zaten her seyi doldurdu")

    monkeypatch.setattr(hp, "ner_ile_cikar", _cagrilirsa_patlat)
    monkeypatch.setattr(hp, "llm_ile_cikar", _cagrilirsa_patlat)

    def _sahte_regex(ham_metin):
        return {alan: "sahte-deger" for alan in hp._NER_LLM_DESTEKLI_ALANLAR} | {
            "kampanya_turu": None,
            "kampanya_baslangic": None,
            "_izler": {alan: ("sahte", 0.9) for alan in hp._NER_LLM_DESTEKLI_ALANLAR},
        }

    monkeypatch.setattr(hp, "kaydi_cikar", _sahte_regex)

    sonuc = kaydi_hibrit_cikar("herhangi bir metin")
    for alan in hp._NER_LLM_DESTEKLI_ALANLAR:
        assert sonuc["_kaynaklar"][alan] == "regex"


def test_regexin_doldurdugu_alan_ner_tarafindan_ezilmez(monkeypatch):
    """Savunma testi: NER, sadece_bu_alanlar filtresine uymasa/hata
    yapsa bile, hibrit boru hattinin kendi birlestirme mantigi regex'in
    zaten doldurdugu bir alanin uzerine YAZMAMALI."""

    def _sahte_regex(ham_metin):
        alanlar = {alan: None for alan in hp._NER_LLM_DESTEKLI_ALANLAR}
        alanlar.update({"kampanya_turu": None, "kampanya_baslangic": None})
        alanlar["vade_ay"] = 120
        return alanlar | {"_izler": {"vade_ay": ("120 ay", 0.85)}}

    def _hatali_ner(ham_metin, sadece_bu_alanlar=None):
        # sadece_bu_alanlar'i yok sayip vade_ay icin FARKLI (yanlis) bir
        # deger dondurmeye calisan bozuk bir NER simulasyonu.
        return {"vade_ay": 36, "_izler": {"vade_ay": ("36 ay", 0.5)}}

    monkeypatch.setattr(hp, "kaydi_cikar", _sahte_regex)
    monkeypatch.setattr(hp, "ner_ile_cikar", _hatali_ner)
    monkeypatch.setattr(hp, "llm_ile_cikar", lambda *a, **k: {"_izler": {}})

    sonuc = kaydi_hibrit_cikar("herhangi bir metin")
    assert sonuc["vade_ay"] == 120
    assert sonuc["_kaynaklar"]["vade_ay"] == "regex"


def test_ner_doldurdugu_alan_kaynak_olarak_isaretlenir(monkeypatch):
    def _sahte_regex(ham_metin):
        alanlar = {alan: None for alan in hp._NER_LLM_DESTEKLI_ALANLAR}
        alanlar.update({"kampanya_turu": None, "kampanya_baslangic": None})
        return alanlar | {"_izler": {}}

    def _sahte_ner(ham_metin, sadece_bu_alanlar=None):
        return {"erteleme_suresi_ay": 3, "_izler": {"erteleme_suresi_ay": ("3 ay ödemesiz", 0.8)}}

    monkeypatch.setattr(hp, "kaydi_cikar", _sahte_regex)
    monkeypatch.setattr(hp, "ner_ile_cikar", _sahte_ner)
    monkeypatch.setattr(hp, "llm_ile_cikar", lambda *a, **k: {"_izler": {}})

    sonuc = kaydi_hibrit_cikar("3 ay ödemesiz dönem fırsatı.")
    assert sonuc["erteleme_suresi_ay"] == 3
    assert sonuc["_kaynaklar"]["erteleme_suresi_ay"] == "ner"
    assert sonuc["_izler"]["erteleme_suresi_ay"] == ("3 ay ödemesiz", 0.8)


def test_ner_bulamazsa_llm_denenir_ve_kaynak_isaretlenir(monkeypatch):
    def _sahte_regex(ham_metin):
        alanlar = {alan: None for alan in hp._NER_LLM_DESTEKLI_ALANLAR}
        alanlar.update({"kampanya_turu": None, "kampanya_baslangic": None})
        return alanlar | {"_izler": {}}

    def _bos_ner(ham_metin, sadece_bu_alanlar=None):
        return {alan: None for alan in sadece_bu_alanlar} | {"_izler": {}}

    def _sahte_llm(ham_metin, sadece_bu_alanlar=None, model=None):
        return {"hedef_kitle": "Yeni müşteri", "_izler": {"hedef_kitle": ("Yeni müşteri", 0.6)}}

    monkeypatch.setattr(hp, "kaydi_cikar", _sahte_regex)
    monkeypatch.setattr(hp, "ner_ile_cikar", _bos_ner)
    monkeypatch.setattr(hp, "llm_ile_cikar", _sahte_llm)

    sonuc = kaydi_hibrit_cikar("herhangi bir metin")
    assert sonuc["hedef_kitle"] == "Yeni müşteri"
    assert sonuc["_kaynaklar"]["hedef_kitle"] == "llm"


def test_kampanya_turu_ve_baslangic_ner_llme_hic_sorulmaz(monkeypatch):
    """KAPSAM DISI ALANLAR: bu iki alan icin regex bulamazsa None kalir,
    NER/LLM'e hic sorulmamali (ikisi de bu alanlari desteklemiyor)."""
    sorulan_alanlar: list[set] = []

    def _sahte_regex(ham_metin):
        alanlar = {alan: None for alan in hp._NER_LLM_DESTEKLI_ALANLAR}
        alanlar.update({"kampanya_turu": None, "kampanya_baslangic": None})
        return alanlar | {"_izler": {}}

    def _kaydeden_ner(ham_metin, sadece_bu_alanlar=None):
        sorulan_alanlar.append(sadece_bu_alanlar)
        return {alan: None for alan in sadece_bu_alanlar} | {"_izler": {}}

    monkeypatch.setattr(hp, "kaydi_cikar", _sahte_regex)
    monkeypatch.setattr(hp, "ner_ile_cikar", _kaydeden_ner)
    monkeypatch.setattr(hp, "llm_ile_cikar", lambda *a, **k: {"_izler": {}})

    sonuc = kaydi_hibrit_cikar("herhangi bir metin")
    assert sonuc["kampanya_turu"] is None
    assert sonuc["kampanya_baslangic"] is None
    assert "kampanya_turu" not in sorulan_alanlar[0]
    assert "kampanya_baslangic" not in sorulan_alanlar[0]


def test_gercek_veriyle_uctan_uca_calisir():
    """Gercek Albaraka kampanya metniyle GLiNER + Ollama'nin ikisi de
    devrede uctan uca calisir - hicbir hata firlatmadan, tutarli bir
    sonuc uretir."""
    with open(
        RAW_DATA / "albaraka" / "json" / "20260731_albaraka_tr_kampanyalar_detay_vade-farksiz-kampanyasi.json",
        encoding="utf-8",
    ) as f:
        kayit = json.load(f)

    sonuc = kaydi_hibrit_cikar(kayit["ham_metin"])
    assert "_izler" in sonuc
    assert "_kaynaklar" in sonuc
    for alan, kaynak in sonuc["_kaynaklar"].items():
        assert kaynak in ("regex", "ner", "llm")
        assert sonuc[alan] is not None

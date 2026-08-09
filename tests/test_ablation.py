"""Ablation olcumunun testleri (scraper/scripts/ablation.py).

Ablation'in tek amaci "her katman NE KATIYOR?" sorusunu sayiyla
cevaplamak. Bu dosyanin kilitledigi iki tehlikeli yaniltma:

  1. Ollama kapaliyken ucuncu varyant sessizce regex+NER sonucu uretir
     ve tablo "LLM katki yapmadi" gibi okunur.
  2. Bir katman, gold'da ETIKETLENMEMIS alanlari doldurursa F1 farki 0
     cikar - ama katki da hata da olcume yansimamistir. Gercek olcum:
     NER 7 alan doldurdu, 7'si de olcum disi kaldi.
"""

import extraction.hybrid_pipeline as hp
import pytest

from scraper.scripts.ablation import _makro_f1
from scraper.scripts.extraction_accuracy import extraction_accuracy_hesapla


# ---------------------------------------------------------------------------
# Katman anahtarlari
# ---------------------------------------------------------------------------


def _sahte_regex(ham_metin):
    alanlar = {alan: None for alan in hp._NER_LLM_DESTEKLI_ALANLAR}
    alanlar.update({"kampanya_turu": None, "kampanya_baslangic": None})
    return alanlar | {"_izler": {}}


def test_ner_kullan_false_NER_katmanini_hic_cagirmaz(monkeypatch):
    def _patlat(*a, **k):
        raise AssertionError("ner_kullan=False iken NER cagrilmamali")

    monkeypatch.setattr(hp, "kaydi_cikar", _sahte_regex)
    monkeypatch.setattr(hp, "ner_ile_cikar", _patlat)
    monkeypatch.setattr(hp, "llm_ile_cikar", lambda *a, **k: {"_izler": {}})

    hp.kaydi_hibrit_cikar("metin", ner_kullan=False)


def test_llm_kullan_false_LLM_katmanini_hic_cagirmaz(monkeypatch):
    """Ablation'in ortadaki varyanti (regex+NER) buna dayanir - LLM
    cagrilirsa varyant kirlenir ve karsilastirma anlamsizlasir."""

    def _patlat(*a, **k):
        raise AssertionError("llm_kullan=False iken LLM cagrilmamali")

    monkeypatch.setattr(hp, "kaydi_cikar", _sahte_regex)
    monkeypatch.setattr(hp, "ner_ile_cikar", lambda *a, **k: {"_izler": {}})
    monkeypatch.setattr(hp, "llm_ile_cikar", _patlat)

    hp.kaydi_hibrit_cikar("metin", llm_kullan=False)


def test_iki_katman_da_kapaliyken_sonuc_regex_ile_ayni(monkeypatch):
    monkeypatch.setattr(hp, "kaydi_cikar", _sahte_regex)
    monkeypatch.setattr(hp, "ner_ile_cikar", lambda *a, **k: {"vade_ay": 99, "_izler": {"vade_ay": ("99", 0.9)}})
    monkeypatch.setattr(hp, "llm_ile_cikar", lambda *a, **k: {"vade_ay": 88, "_izler": {"vade_ay": ("88", 0.9)}})

    sonuc = hp.kaydi_hibrit_cikar("metin", ner_kullan=False, llm_kullan=False)
    assert sonuc["vade_ay"] is None
    assert sonuc["_kaynaklar"] == {}


def test_varsayilan_davranis_degismedi(monkeypatch):
    """Geriye uyumluluk: parametresiz cagri hala uc katmani da calistirir."""
    cagrilanlar = []
    monkeypatch.setattr(hp, "kaydi_cikar", _sahte_regex)
    monkeypatch.setattr(
        hp, "ner_ile_cikar",
        lambda *a, **k: cagrilanlar.append("ner") or {"_izler": {}},
    )
    monkeypatch.setattr(
        hp, "llm_ile_cikar",
        lambda *a, **k: cagrilanlar.append("llm") or {"_izler": {}},
    )

    hp.kaydi_hibrit_cikar("metin")
    assert cagrilanlar == ["ner", "llm"]


# ---------------------------------------------------------------------------
# Makro F1
# ---------------------------------------------------------------------------


def test_makro_f1_olculemeyen_alanlari_disarida_birakir():
    """None F1'leri 0 sayarsak ortalama haksiz yere duser."""
    sahte = {"alan_bazli": {"a": {"f1": 80.0}, "b": {"f1": 60.0}, "c": {"f1": None}}}
    assert _makro_f1(sahte) == 70.0


def test_makro_f1_hic_olculebilir_alan_yoksa_None():
    assert _makro_f1({"alan_bazli": {"a": {"f1": None}}}) is None


# ---------------------------------------------------------------------------
# Katman katkisi - "gorunmez katki" tuzagi
# ---------------------------------------------------------------------------


def test_regex_only_olcumde_katman_katkisi_bostur():
    """kaydi_cikar `_kaynaklar` uretmez; katki tablosu da bos kalmali."""
    sonuc = extraction_accuracy_hesapla()
    assert sonuc["katman_katkisi"] == {}


def test_katman_katkisi_olcum_disi_ayrimini_yapar():
    """Sahte bir cikarim fonksiyonuyla: bir katman gold'da etiketlenmemis
    bir alani doldurursa 'olcum_disi' sayilmali - F1'e hic yansimadigi
    icin tek basina F1 farkina bakmak yaniltici olur."""

    def _sahte_hibrit(ham_metin: str) -> dict:
        # taksit_sayisi gold'da hic etiketlenmemis -> olcum disi
        return {
            "taksit_sayisi": 12,
            "_izler": {},
            "_kaynaklar": {"taksit_sayisi": "ner"},
        }

    sonuc = extraction_accuracy_hesapla(_sahte_hibrit)
    ner = sonuc["katman_katkisi"]["ner"]
    assert ner["toplam"] > 0
    assert ner["olcum_disi"] == ner["toplam"], (
        "taksit_sayisi gold'da etiketlenmemis; tum katki olcum disi olmali"
    )


def test_katman_katkisi_olculebilir_alani_gorunur_sayar():
    def _sahte_hibrit(ham_metin: str) -> dict:
        # kar_payi_orani_percent gold'da etiketli -> olcume girer
        return {
            "kar_payi_orani_percent": 1.89,
            "_izler": {},
            "_kaynaklar": {"kar_payi_orani_percent": "llm"},
        }

    sonuc = extraction_accuracy_hesapla(_sahte_hibrit)
    llm = sonuc["katman_katkisi"]["llm"]
    assert llm["toplam"] - llm["olcum_disi"] > 0, "En az bir alan olcume girmeliydi"


def test_none_deger_katki_sayilmaz():
    """Katman alani BOS biraktiysa katki degildir."""

    def _sahte_hibrit(ham_metin: str) -> dict:
        return {"vade_ay": None, "_izler": {}, "_kaynaklar": {"vade_ay": "ner"}}

    assert extraction_accuracy_hesapla(_sahte_hibrit)["katman_katkisi"] == {}

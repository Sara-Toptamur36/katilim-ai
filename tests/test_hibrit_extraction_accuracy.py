"""Hibrit boru hattinin (regex + NER + LLM) Extraction Accuracy regresyon testi.

tests/test_regex_extractor_duzeltmeler.py::
test_extraction_accuracy_asgari_esigin_altina_dusmez ile AYNI mantik,
ama extraction/hybrid_pipeline.py::kaydi_hibrit_cikar() icin - NER/LLM
katmanlarinin eklenmesinin regex-only dogruluguna (esik: >=80.0, gercek
olcum %84.38) kiyasla bir REGRESYONA yol acmadigini kilitler.

GERCEK GLiNER + Ollama servislerini kullanir (test_llm_extractor.py'deki
AYNI CI-skip deseni) - CI'da (GitHub Actions, yerel Ollama YOK) bu dosya
otomatik atlanir, bir regresyon degildir.
"""

import pytest
import requests

from extraction.hybrid_pipeline import kaydi_hibrit_cikar
from extraction.llm_extractor import _OLLAMA_URL
from scraper.scripts.extraction_accuracy import extraction_accuracy_hesapla


def _ollama_erisilebilir_mi() -> bool:
    try:
        requests.get(_OLLAMA_URL.replace("/api/generate", "/api/tags"), timeout=2)
        return True
    except requests.RequestException:
        return False


OLLAMA_YOK_MESAJI = "Yerel Ollama servisi calismiyor (ollama serve) - CI'da beklenen durum"

pytestmark = pytest.mark.skipif(not _ollama_erisilebilir_mi(), reason=OLLAMA_YOK_MESAJI)


def test_hibrit_dogruluk_regex_only_esiginin_altina_dusmez():
    """Hibrit boru hatti (regex+NER+LLM), regex-only olcumun kendi
    esiginden (>=80.0) DUSUK olmamali - NER/LLM katmanlari EKLEME
    yapmali, mevcut regex sonuclarini asla EZMEDIGI icin (bkz.
    hybrid_pipeline._katman_sonucunu_birlestir) matematiksel olarak
    dogrulugu DUSUREMEZLER, yalnizca bos alanlari doldurarak
    artirabilir ya da ayni birakabilirler."""
    sonuc = extraction_accuracy_hesapla(kaydi_hibrit_cikar)
    assert sonuc["accuracy"] >= 80.0, (
        f"Hibrit Extraction Accuracy %{sonuc['accuracy']}'e dustu (asgari %80 bekleniyordu). "
        f"Hatalar: {sonuc['hatalar']}"
    )

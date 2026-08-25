"""chunking/retriever.py::getir - RAG_MODE cozumleme testleri.

BILEREK test_qdrant_baglanti.py'nin DISINDA: o dosya tamami Qdrant'a bagli
oldugu icin modul-seviyesinde skip'leniyor. Bu testler `rag_modu`
COZUMLEME mantigini (parametre -> ortam degiskeni -> saglayiciya gore
otomatik varsayilan) dogrular - getir() bu cozumlemeyi qdrant_hazir_mi()
kontrolunden ONCE yaptigi icin Qdrant çalışmadan da test edilebilir
(gecersiz rag_modu -> ValueError, Qdrant kontrolune hic ulasilmadan).
"""

import pytest

import chunking.retriever as retriever
import evren_istemci


@pytest.fixture(autouse=True)
def _evren_pasif(monkeypatch):
    """Testler EVREN aktif/pasif durumunu ACIKCA kontrol eder - ortamdan
    sizan bir EVREN_API_KEY testleri yanlis yola sokmasin."""
    monkeypatch.setattr(evren_istemci, "_API_KEY", "")


def test_gecersiz_rag_modu_reddedilir():
    with pytest.raises(ValueError, match="RAG_MODE"):
        retriever.getir("herhangi bir soru", rag_modu="hibrit-VE-dense-karisik")


def test_evren_pasifken_varsayilan_hibrittir(monkeypatch):
    """qdrant_hazir_mi() False donerse getir() erken cikar - rag_modu
    cozumlemesi bu noktaya kadar zaten calismis olmali, hata verilmemeli."""
    monkeypatch.setattr(retriever, "qdrant_hazir_mi", lambda: False)
    sonuc = retriever.getir("murabaha nedir")
    assert sonuc.sebep == "Vektor veritabanina (Qdrant) erisilemiyor"


def test_evren_aktifken_bile_varsayilan_hibrit_secilir(monkeypatch):
    """EVREN_API_KEY tanimli olsa bile (aktif_mi()=True) varsayilan HALA
    'hibrit'tir (25 Agustos 2026'dan itibaren - bkz. docs/rag_tasarim_ve_
    olcum.md Bulgu 14). Gercek anahtarla olculdugunde EVREN'in bge-m3-
    embed'iyle bile hibrit dense'i hafifce gecti (Genel Recall@5 %84,50 vs
    %83,72) - saglayiciya gore dallanan eski varsayilan (EVREN aktifken
    'dense') bu yuzden kaldirildi."""
    monkeypatch.setattr(evren_istemci, "_API_KEY", "sk-evren-team00-sahte")
    monkeypatch.delenv("RAG_MODE", raising=False)

    cagrilar = {}

    def _sahte_yogun_ara(**kwargs):
        cagrilar["yogun_ara_cagrildi"] = True
        return []

    def _sahte_hibrit_ara(**kwargs):
        cagrilar["hibrit_ara_cagrildi"] = True
        return []

    monkeypatch.setattr(retriever, "qdrant_hazir_mi", lambda: True)
    monkeypatch.setattr(retriever, "yogun_ara", _sahte_yogun_ara)
    monkeypatch.setattr(retriever, "hibrit_ara", _sahte_hibrit_ara)
    monkeypatch.setattr(retriever, "sorguyu_vektore_cevir", lambda s: [0.0])
    monkeypatch.setattr(retriever, "seyrek_vektor_uret", lambda s: {})

    retriever.getir("murabaha nedir")

    assert cagrilar.get("hibrit_ara_cagrildi") is True
    assert "yogun_ara_cagrildi" not in cagrilar


def test_rag_mode_ortam_degiskeni_otomatik_varsayilani_ezer(monkeypatch):
    """EVREN pasif olsa da RAG_MODE=dense acikca verilmisse dense
    kullanilmali - olcum/benchmark amacli manuel zorlama (Sara'nin
    onerisi) her zaman kazanmali."""
    monkeypatch.setenv("RAG_MODE", "dense")

    cagrilar = {}

    def _sahte_yogun_ara(**kwargs):
        cagrilar["dense"] = True
        return []

    def _sahte_hibrit_ara(**kwargs):
        cagrilar["hibrit"] = True
        return []

    monkeypatch.setattr(retriever, "qdrant_hazir_mi", lambda: True)
    monkeypatch.setattr(retriever, "yogun_ara", _sahte_yogun_ara)
    monkeypatch.setattr(retriever, "hibrit_ara", _sahte_hibrit_ara)
    monkeypatch.setattr(retriever, "sorguyu_vektore_cevir", lambda s: [0.0])

    retriever.getir("murabaha nedir")

    assert cagrilar.get("dense") is True
    assert "hibrit" not in cagrilar

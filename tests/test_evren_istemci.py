"""evren_istemci.py testleri.

Iki grup:
  1. PASIF-DURUM testleri (asagida, sartsiz calisir): EVREN_API_KEY tanimli
     olmadigi CI/varsayilan durumda modulun agi hic cagirmadan dogru
     davrandigini dogrular - test_donanim.py'nin "saf mantik, gercek
     donanim gerekmez" ilkesiyle AYNI.
  2. CANLI testler (asagida, EVREN_API_KEY YOKSA atlanir): test_llm_extractor.py
     (Ollama) ve test_qdrant_baglanti.py (Qdrant) ile AYNI skip deseni -
     dis servisin CI'da bulunmamasi bir regresyon degildir.
"""

import pytest

import evren_istemci


def test_anahtar_tanimli_degilse_pasif():
    """CI'da EVREN_API_KEY tanimlanmaz - varsayilan davranis PASIF olmali,
    yerel Ollama/sentence-transformers yoluna sessizce dusulur."""
    if evren_istemci.aktif_mi():
        pytest.skip("Bu ortamda EVREN_API_KEY tanimli - pasif-durum testi atlanir")
    assert evren_istemci.hazir_mi() is False


def test_pasifken_hazir_mi_ag_cagirmaz(monkeypatch):
    """aktif_mi()=False iken hazir_mi() ANINDA False donmeli - _istemciyi_al()
    hic cagirilmamali (agir/network baglantisi denenmemeli)."""
    monkeypatch.setattr(evren_istemci, "_API_KEY", "")

    def _cagirilirsa_patlar():
        raise AssertionError("_istemciyi_al() pasif durumda cagirilmamali")

    monkeypatch.setattr(evren_istemci, "_istemciyi_al", _cagirilirsa_patlar)
    assert evren_istemci.aktif_mi() is False
    assert evren_istemci.hazir_mi() is False


def test_pasifken_sohbet_ile_sor_none_doner(monkeypatch):
    monkeypatch.setattr(evren_istemci, "_API_KEY", "")
    assert evren_istemci.sohbet_ile_sor("herhangi bir prompt") is None


def test_pasifken_gomme_al_none_doner(monkeypatch):
    monkeypatch.setattr(evren_istemci, "_API_KEY", "")
    assert evren_istemci.gomme_al(["herhangi bir metin"]) is None


def test_ozet_pasifken_yerel_yolu_belirtir(monkeypatch):
    monkeypatch.setattr(evren_istemci, "_API_KEY", "")
    cikti = evren_istemci.ozet()
    assert "pasif" in cikti
    assert "EVREN_API_KEY" in cikti


def test_hazir_mi_onbellekli(monkeypatch):
    """aktif_mi()=True olsa da hazir_mi() 30 sn onbelleklenir - servis
    kapaliyken her cagrida ayri ayri baglanti-hatasi beklenmesin
    (extraction/llm_extractor.py::_ollama_hazir_mi ile AYNI gerekce)."""
    monkeypatch.setattr(evren_istemci, "_API_KEY", "sk-evren-team00-sahte")
    evren_istemci._DURUM_CACHE.clear()

    cagri_sayaci = {"n": 0}

    class _SahteIstemci:
        class models:
            @staticmethod
            def list():
                cagri_sayaci["n"] += 1
                raise ConnectionError("ag yok - beklenen (test ortami)")

    monkeypatch.setattr(evren_istemci, "_istemciyi_al", lambda: _SahteIstemci())

    assert evren_istemci.hazir_mi() is False
    assert evren_istemci.hazir_mi() is False  # onbellekten donmeli
    assert cagri_sayaci["n"] == 1


# --- Canli testler (gercek EVREN_API_KEY gerektirir) ---------------------

EVREN_YOK_MESAJI = "EVREN_API_KEY tanimli degil / servise ulasilamiyor - CI'da beklenen durum"
canli = pytest.mark.skipif(not evren_istemci.hazir_mi(), reason=EVREN_YOK_MESAJI)


@canli
def test_canli_sohbet_ile_sor_yanit_doner():
    yanit = evren_istemci.sohbet_ile_sor("Bir cümleyle kendini tanıt.", max_tokens=64)
    assert yanit is not None
    assert len(yanit) > 0


@canli
def test_canli_gomme_al_dogru_boyut_doner():
    vektorler = evren_istemci.gomme_al(["tedarik sözleşmesi"])
    assert vektorler is not None
    assert len(vektorler[0]) == evren_istemci.EMBED_BOYUTU

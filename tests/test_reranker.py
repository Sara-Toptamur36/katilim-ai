"""chunking/reranker.py testleri.

DENETIM BULGUSU (25 Agustos 2026): bu dosya icin daha once HIC birim
testi yoktu - projenin kendi belgesinde ("aylardir olculmeden devrede",
bkz. docs/rag_tasarim_ve_olcum.md) acikca riskli isaretlenmis bir
bilesen, ama fallback davranisi (model yuklenemezse, tahmin hata
firlatirsa) hicbir yerde dogrulanmiyordu.

MODEL INDIRMEDEN TEST EDILEBILIR: `_reranker_yukle` (lru_cache'li) her
testte monkeypatch'lenir - gercek CrossEncoder hicbir zaman yuklenmez,
bu yuzden bu testler agsiz/hizli calisir ve CI'da normal (skip'siz)
kosar.
"""

from __future__ import annotations

import chunking.reranker as reranker


def _parca(sira: int, metin: str = "") -> dict:
    return {"skor": 1.0, "ustveri": {"metin": metin or f"metin-{sira}"}}


def test_bos_liste_bos_doner():
    assert reranker.rerank("soru", [], top_k=5) == []


def test_model_yuklenemezse_orijinal_sira_ve_kesme_korunur(monkeypatch):
    """Model None donerse (sentence_transformers yok / yukleme hatasi)
    rerank_score HIC eklenmeden, orijinal siradaki ilk top_k parca
    donmeli - sessiz bir cokme degil, KADEMELI FALLBACK (projenin geri
    kalaninda kullanilan AYNI sozlesme, bkz. extraction/llm_extractor.py
    ve evren_istemci.py)."""
    monkeypatch.setattr(reranker, "_reranker_yukle", lambda: None)
    parcalar = [_parca(i) for i in range(7)]

    sonuc = reranker.rerank("soru", parcalar, top_k=3)

    assert sonuc == parcalar[:3]
    assert all("rerank_score" not in p for p in sonuc)


def test_basarili_rerank_skora_gore_siralar_ve_keser():
    class _SahteModel:
        def predict(self, girdiler):
            # Girdi sirasina gore azalan skorlar yerine BILEREK TERS bir
            # siralama dondurulur - testin "hicbir sey yapmadan da dogru
            # gorunme" riskini elemek icin: eger rerank() siralamayi
            # GERCEKTEN uygulamiyorsa bu test yakalar.
            return [float(i) for i in range(len(girdiler))]

    parcalar = [_parca(i) for i in range(5)]

    class _SahteYukleyici:
        def __call__(self):
            return _SahteModel()

    import chunking.reranker as r

    onceki = r._reranker_yukle
    r._reranker_yukle = _SahteYukleyici()
    try:
        sonuc = r.rerank("soru", parcalar, top_k=3)
    finally:
        r._reranker_yukle = onceki

    # Skorlar girdi sirasiyla artan (0,1,2,3,4) verildigi icin en yuksek
    # skorlu (buyukten kucuge) ilk 3 parca SON 3 girdi olmali: 4,3,2.
    assert [p["ustveri"]["metin"] for p in sonuc] == ["metin-4", "metin-3", "metin-2"]
    assert [p["rerank_score"] for p in sonuc] == [4.0, 3.0, 2.0]


def test_predict_hata_firlatirsa_orijinal_kesme_ile_devam_eder(monkeypatch):
    class _PatlayanModel:
        def predict(self, girdiler):
            raise RuntimeError("model cokuyor - beklenen (test)")

    monkeypatch.setattr(reranker, "_reranker_yukle", lambda: _PatlayanModel())
    parcalar = [_parca(i) for i in range(4)]

    sonuc = reranker.rerank("soru", parcalar, top_k=2)

    assert sonuc == parcalar[:2]
    assert all("rerank_score" not in p for p in sonuc)


def test_top_k_girdi_sayisindan_buyukse_tum_parcalar_doner():
    class _SahteModel:
        def predict(self, girdiler):
            return [1.0] * len(girdiler)

    parcalar = [_parca(i) for i in range(3)]

    import chunking.reranker as r

    onceki = r._reranker_yukle
    r._reranker_yukle = lambda: _SahteModel()
    try:
        sonuc = r.rerank("soru", parcalar, top_k=10)
    finally:
        r._reranker_yukle = onceki

    assert len(sonuc) == 3


def test_reranker_model_adi_varsayilani():
    assert reranker.RERANKER_MODEL == "cross-encoder/ms-marco-MiniLM-L-6-v2"


def test_reranker_model_adi_ortam_degiskeniyle_ezilebilir(monkeypatch):
    """RERANKER_MODEL modul IMPORT ANINDA okunuyor (donanim.py'deki profil
    sabitleriyle AYNI desen) - degiskenin gercekten okundugunu dogrulamak
    icin modulun yeniden yuklenmesi gerekir."""
    import importlib

    monkeypatch.setenv("KATILIMAI_RERANKER_MODEL", "baska/model-adi")
    try:
        importlib.reload(reranker)
        assert reranker.RERANKER_MODEL == "baska/model-adi"
    finally:
        monkeypatch.delenv("KATILIMAI_RERANKER_MODEL", raising=False)
        importlib.reload(reranker)

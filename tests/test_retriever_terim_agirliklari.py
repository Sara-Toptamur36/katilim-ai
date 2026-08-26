"""chunking/retriever.py::_terim_agirliklari testleri.

NEDEN AYRI DOSYA: bu, "Sorgu Esleme Agirliklari" gorsellestirmesinin
(mimari kiyaslamada "Attention" yasagi yerine onerilen) veri kaynagi -
saf bir fonksiyon, Qdrant/embedding gerektirmez, digerlerinden (2 sn ->
121 sn olculen) izole hizli calisir (bkz. test_retriever_rag_modu.py'nin
ayni gerekcesi).
"""

from chunking.retriever import _terim_agirliklari


def _parca(metin: str) -> dict:
    return {"ustveri": {"metin": metin}}


def test_terim_yok_ise_bos_liste_doner():
    assert _terim_agirliklari([], [_parca("kâr payı oranı")]) == []


def test_parca_yok_ise_tum_terimler_sifir_agirlikli_doner():
    """Cekimser kalindiginda da HANGI kelimenin kaynaksiz kaldigi
    gorunmeli - terimler ATILMAZ, sifir agirlikla listelenir."""
    sonuc = _terim_agirliklari(["kâr", "payı"], [])
    assert sonuc == [
        {"terim": "kâr", "agirlik": 0.0, "eslesti": False},
        {"terim": "payı", "agirlik": 0.0, "eslesti": False},
    ]


def test_tum_parcalarda_gecen_terim_tam_agirlik_alir():
    parcalar = [_parca("kâr payı oranı düşük"), _parca("kâr payı avantajlı")]
    sonuc = _terim_agirliklari(["kâr"], parcalar)
    assert sonuc == [{"terim": "kâr", "agirlik": 1.0, "eslesti": True}]


def test_bazi_parcalarda_gecen_terim_kesirli_agirlik_alir():
    parcalar = [_parca("vade farksız taksit"), _parca("kâr payı oranı")]
    sonuc = _terim_agirliklari(["vade"], parcalar)
    assert sonuc == [{"terim": "vade", "agirlik": 0.5, "eslesti": True}]


def test_hic_gecmeyen_terim_sifir_agirlikli_ama_LISTEDE_KALIR():
    """Yanlis alarm KORUMASI: bir terim hic eslesmese bile listeden
    silinmemeli - kullanicinin hangi kelimesinin karsiliksiz kaldigini
    gormesi tam da bu ozelligin amacidir."""
    parcalar = [_parca("kâr payı oranı")]
    sonuc = _terim_agirliklari(["ödül"], parcalar)
    assert sonuc == [{"terim": "ödül", "agirlik": 0.0, "eslesti": False}]


def test_govde_duyarli_eslesme_ek_farkini_tolere_eder():
    """_terim_ortusmesi ile AYNI govde kurali (GOVDE_ONEK_UZUNLUGU=5,
    GOVDE_ASGARI_TOKEN=7): 'kazanma' sorgusu, metindeki 'kazanın' ile
    govde uzerinden (ikisi de 'kazan' onekine indirgenir) eslesmeli -
    tam token karsilastirmasi Turkce ek farkinda BASARISIZ olurdu
    (bkz. docs/rag_tasarim_ve_olcum.md Bolum 3)."""
    parcalar = [_parca("Worldpuan kazanın, avantajlardan yararlanın")]
    sonuc = _terim_agirliklari(["kazanma"], parcalar)
    assert sonuc == [{"terim": "kazanma", "agirlik": 1.0, "eslesti": True}]


def test_coklu_terim_karisik_agirlik_sirasi_korunur():
    """Bar grafiginin sag sirasinda cizilebilmesi icin donus sirasi
    girdi sirasiyla AYNI olmali."""
    parcalar = [_parca("kâr payı oranı düşük vade")]
    sonuc = _terim_agirliklari(["kâr", "ödül", "vade"], parcalar)
    assert [s["terim"] for s in sonuc] == ["kâr", "ödül", "vade"]
    assert [s["eslesti"] for s in sonuc] == [True, False, True]

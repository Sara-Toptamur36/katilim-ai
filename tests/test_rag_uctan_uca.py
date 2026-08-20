"""RAG uctan uca testleri - GERCEK Qdrant indeksi + embedding modeliyle.

CI'da Qdrant/model yoktur; bu dosya diger dis-servis testleriyle AYNI
desenle atlanir. Ayrica indeks HENUZ KURULMAMISSA da atlanir - indeks
kurmak dakikalar suren bir toplu istir, test icinde yapilmaz
(`python -m chunking.indeksleyici` ile ayrica calistirilir).

Bu dosya RETRIEVAL KALITESINI ve ABSTENTION davranisini dogrular;
yonlendirme mantigi tests/test_agent_orchestrator.py'de sahte RAG ile
hizlica test edilir.
"""

import pytest

from chunking.qdrant_baglanti import VARSAYILAN_KOLEKSIYON, koleksiyon_sayisi, qdrant_hazir_mi


def _indeks_hazir_mi() -> bool:
    if not qdrant_hazir_mi():
        return False
    try:
        sayi = koleksiyon_sayisi(VARSAYILAN_KOLEKSIYON)
    except Exception:
        return False
    return bool(sayi)


INDEKS_YOK_MESAJI = (
    "Qdrant indeksi hazir degil - once 'docker compose up -d qdrant' ve "
    "'python -m chunking.indeksleyici' calistirin (CI'da beklenen durum)"
)

pytestmark = [pytest.mark.skipif(not _indeks_hazir_mi(), reason=INDEKS_YOK_MESAJI), pytest.mark.slow]


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------


def test_alakali_soruda_kaynak_bulunur():
    from chunking.retriever import getir

    sonuc = getir("kâr payı oranı ve vade seçenekleri nedir", limit=3)
    assert sonuc.yeterli_kaynak_var is True
    assert sonuc.parcalar
    assert sonuc.eslesen_terimler


def test_alan_disi_soruda_cekimser_kalinir():
    """KRITIK (rapor Bolum 5.7/15): kaynakta olmayan bir soruya cevap
    UYDURULMAMALI. Spike olcumu, ham vektor benzerliginin bunu tek basina
    ayirt edemedigini gostermisti (alakasiz sorgu bile 0,78 aliyordu) -
    bu yuzden terim ortusmesi olcutu kullaniliyor."""
    from chunking.retriever import getir

    sonuc = getir("Uzay istasyonunda yerçekimi nasıl ölçülür?", limit=3)
    assert sonuc.yeterli_kaynak_var is False
    assert sonuc.sebep


def test_her_parca_provenance_tasir():
    """Rapor Bolum 9: kaynagi gosterilemeyen cevabin degeri yoktur."""
    from chunking.retriever import getir

    sonuc = getir("kampanya koşulları", limit=3)
    for parca in sonuc.parcalar:
        ustveri = parca.get("ustveri") or {}
        assert ustveri.get("kaynak_url"), "Parca kaynak URL tasimiyor"
        assert ustveri.get("banka"), "Parca banka bilgisi tasimiyor"


def test_banka_filtresi_sonuclari_daraltir():
    """Metadata filtresi: soru belirli bir bankayla ilgiliyse yalnizca o
    bankanin belgeleri donmeli."""
    from chunking.retriever import getir

    sonuc = getir("kampanya koşulları", limit=5, banka="Kuveyt Türk")
    if not sonuc.parcalar:
        pytest.skip("Bu bankaya ait indekslenmis parca yok")
    bankalar = {(p.get("ustveri") or {}).get("banka") for p in sonuc.parcalar}
    assert bankalar == {"Kuveyt Türk"}


# ---------------------------------------------------------------------------
# Router / orchestrator entegrasyonu
# ---------------------------------------------------------------------------


def test_rag_araci_kaynakli_yanit_uretir():
    from agent.router import rag_aracini_cagir

    sonuc = rag_aracini_cagir("kâr payı oranı ve vade seçenekleri")
    assert sonuc["basarili"] is True
    assert sonuc["kaynaklar"]
    for kaynak in sonuc["kaynaklar"]:
        assert kaynak["kaynak_url"]
        assert kaynak["similarity_score"] is not None


def test_rag_araci_kayit_getirici_verilmezse_kampanya_id_none_kalir():
    """Geriye donuk uyumluluk: kayit_getirici enjekte edilmezse (bu test
    gibi dogrudan cagrilirsa) kampanya_id sessizce None kalir, hata
    firlatilmaz."""
    from agent.router import rag_aracini_cagir

    sonuc = rag_aracini_cagir("kâr payı oranı ve vade seçenekleri")
    assert sonuc["basarili"] is True
    for kaynak in sonuc["kaynaklar"]:
        assert kaynak["kampanya_id"] is None


def test_rag_araci_kayit_getirici_verilirse_kampanya_id_doldurur():
    """GERCEK veritabani/mock kaynagiyla kampanya_id eslestirmesi -
    Havin'in istedigi, isme gore kirilgan eslestirme yerine dogrudan id."""
    from agent.router import rag_aracini_cagir
    from api.mock_data import kampanyalari_getir

    sonuc = rag_aracini_cagir("kâr payı oranı ve vade seçenekleri", kampanyalari_getir)
    assert sonuc["basarili"] is True
    # Mock veri (A/B/C/D Bankasi) gercek indeksteki (gercek banka) URL'lerle
    # eslesmeyecegi icin hepsi None kalabilir - test, HATA FIRLAMADIGINI ve
    # alanin var oldugunu kilitler; gercek DB ile eslesme
    # test_agent_router.py::test_kampanya_id_bul_* icinde birim testiyle
    # zaten dogrulandi.
    for kaynak in sonuc["kaynaklar"]:
        assert "kampanya_id" in kaynak


def test_rag_araci_chunk_id_ve_belge_tarihi_doldurur():
    """DENETIM BULGUSU (11 Agu): Kaynak semasinda chunk_id/belge_tarihi
    vardi ama rag_aracini_cagir bu iki alani hic set etmiyordu - Pydantic
    sessizce None birakiyordu (audit panelindeki retriever_sonuclari
    doluyken ana kaynaklar listesi eksikti). Md. 11 izlenebilirlik icin
    ikisi de dolu olmali."""
    from agent.router import rag_aracini_cagir

    sonuc = rag_aracini_cagir("kâr payı oranı ve vade seçenekleri")
    assert sonuc["basarili"] is True
    for kaynak in sonuc["kaynaklar"]:
        assert kaynak["chunk_id"], "chunk_id bos - provenance eksik"
        assert kaynak["belge_tarihi"], "belge_tarihi bos - provenance eksik"


def test_rag_araci_kaynak_yoksa_uydurmaz():
    from agent.router import rag_aracini_cagir

    sonuc = rag_aracini_cagir("Mercimek çorbası tarifi nedir?")
    assert sonuc["basarili"] is False
    assert sonuc["sebep"]


def test_orkestrator_bilgi_sorusunu_raga_yonlendirir():
    """Belirli bir araca uymayan soru RAG'e gitmeli ve audit'te
    'bilgi' niyeti + 'rag' araci gorunmeli."""
    from agent.orchestrator import soru_isle

    sonuc = soru_isle("kâr payı oranı ve vade seçenekleri", lambda banka: [])
    assert sonuc["audit_ekstra"]["intent"] == "bilgi"
    assert sonuc["audit_ekstra"]["cagrilan_arac"] == "rag"
    assert sonuc["kaynaklar"], "Kaynaklar yanitta donmedi"
    assert sonuc["audit_ekstra"]["retriever_sonuclari"], "Audit paneli retriever bilgisi bos"

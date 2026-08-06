"""chunking/qdrant_baglanti.py + chunking/embedding.py testleri.

CI'da Qdrant servisi ve embedding modeli bulunmaz; bu dosya
test_kullanici_repository.py / test_llm_extractor.py ile AYNI desenle
atlanir - dis servisin olmamasi bir regresyon degildir.

Embedding modeli agir (~1 GB, ilk yukleme ~12 sn) oldugu icin testler
KISA metinler kullanir; amac model kalitesini olcmek degil, katmanin
teknik olarak dogru calistigini dogrulamaktir.
"""

import pytest

from chunking.qdrant_baglanti import qdrant_hazir_mi

QDRANT_YOK_MESAJI = "Qdrant calismiyor (docker compose up -d qdrant) - CI'da beklenen durum"

pytestmark = pytest.mark.skipif(not qdrant_hazir_mi(), reason=QDRANT_YOK_MESAJI)

TEST_KOLEKSIYONU = "pytest_gecici_koleksiyon"


@pytest.fixture
def temiz_koleksiyon():
    """Her testte sifirdan bir koleksiyon acar, test sonunda siler."""
    from chunking.qdrant_baglanti import istemci_al, koleksiyon_hazirla

    koleksiyon_hazirla(TEST_KOLEKSIYONU, vektor_boyutu=4, sifirla=True)
    yield TEST_KOLEKSIYONU
    istemci = istemci_al()
    if istemci.collection_exists(TEST_KOLEKSIYONU):
        istemci.delete_collection(TEST_KOLEKSIYONU)


def test_koleksiyon_olusturulur_ve_bos_baslar(temiz_koleksiyon):
    from chunking.qdrant_baglanti import koleksiyon_sayisi

    assert koleksiyon_sayisi(temiz_koleksiyon) == 0


def test_olmayan_koleksiyon_none_doner():
    from chunking.qdrant_baglanti import koleksiyon_sayisi

    assert koleksiyon_sayisi("kesinlikle-olmayan-bir-koleksiyon") is None


def test_vektor_yazilir_ve_geri_aranir(temiz_koleksiyon):
    """Yazilan vektorun AYNISI sorgulandiginda en ustte donmeli."""
    from chunking.qdrant_baglanti import ara, koleksiyon_sayisi, parcalari_ekle

    vektorler = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]]
    ustveriler = [
        {"banka": "A Bankasi", "metin": "birinci parca"},
        {"banka": "B Bankasi", "metin": "ikinci parca"},
    ]
    assert parcalari_ekle(vektorler, ustveriler, koleksiyon=temiz_koleksiyon) == 2
    assert koleksiyon_sayisi(temiz_koleksiyon) == 2

    sonuclar = ara([1.0, 0.0, 0.0, 0.0], limit=2, koleksiyon=temiz_koleksiyon)
    assert sonuclar[0]["ustveri"]["banka"] == "A Bankasi"
    assert sonuclar[0]["skor"] > sonuclar[1]["skor"]


def test_ustveri_kaynak_bilgisini_korur(temiz_koleksiyon):
    """Provenance (rapor Bolum 9): kaynak_url geri okunabilmeli - yoksa
    RAG cevabinin nereden geldigi gosterilemez."""
    from chunking.qdrant_baglanti import ara, parcalari_ekle

    parcalari_ekle(
        [[1.0, 0.0, 0.0, 0.0]],
        [{"banka": "A Bankasi", "kaynak_url": "https://ornek.com/kampanya", "metin": "x"}],
        koleksiyon=temiz_koleksiyon,
    )
    ustveri = ara([1.0, 0.0, 0.0, 0.0], limit=1, koleksiyon=temiz_koleksiyon)[0]["ustveri"]
    assert ustveri["kaynak_url"] == "https://ornek.com/kampanya"


def test_vektor_ustveri_sayisi_uyusmazsa_hata_verir(temiz_koleksiyon):
    """Sessizce yanlis eslestirmektense acikca hata vermeli - yanlis
    eslesen bir ustveri, cevabi YANLIS kaynaga baglar."""
    from chunking.qdrant_baglanti import parcalari_ekle

    with pytest.raises(ValueError, match="eslesmiyor"):
        parcalari_ekle([[1.0, 0.0, 0.0, 0.0]], [{"a": 1}, {"b": 2}], koleksiyon=temiz_koleksiyon)


# ---------------------------------------------------------------------------
# Embedding katmani (model gerektirir - ayrica atlanabilir)
# ---------------------------------------------------------------------------


@pytest.fixture
def embedding_modeli():
    """Modeli TEST CALISIRKEN yukler, toplama (collection) aninda DEGIL.

    DENETIM BULGUSU: Ilk yazimda bu kontrol `@pytest.mark.skipif(
    not _model_hazir_mi())` seklinde modul seviyesindeydi. skipif ifadesi
    TOPLAMA aninda calisir - yani Qdrant kapali olup TUM dosya atlanacak
    olsa bile sentence_transformers import edilip ~1 GB'lik model
    yukleniyordu (olculdu: atlanan bir kosuda bile ~55 sn). CI'da model
    onbellekte hic olmadigi icin bu, bosuna 1 GB indirme denemesi
    anlamina gelirdi. Fixture kullanildiginda yukleme yalnizca test
    GERCEKTEN calisacaksa yapilir.
    """
    from chunking.embedding import model_hazir_mi

    hata = model_hazir_mi()
    if hata is not None:
        pytest.skip(f"Embedding modeli yuklenemiyor: {hata}")


def test_embedding_dogru_boyutta_normalize_vektor_uretir(embedding_modeli):
    from chunking.embedding import VEKTOR_BOYUTU, belgeleri_vektore_cevir

    vektorler = belgeleri_vektore_cevir(["kâr payı oranı %1,89", "vade 120 ay"])
    assert len(vektorler) == 2
    assert all(len(v) == VEKTOR_BOYUTU for v in vektorler)

    # normalize_embeddings=True kullanildigi icin uzunluk ~1 olmali
    # (kosinus benzerliginin dogru calismasi buna bagli)
    uzunluk = sum(d * d for d in vektorler[0]) ** 0.5
    assert abs(uzunluk - 1.0) < 0.01


def test_benzer_metinler_alakasizdan_daha_yakin(embedding_modeli):
    """Model Turkce bankacilik metninde anlamli calisiyor mu (kaba kontrol)."""
    from chunking.embedding import belgeleri_vektore_cevir, sorguyu_vektore_cevir

    belgeler = belgeleri_vektore_cevir(
        ["Konut finansmanında kâr payı oranı %1,89'dur.", "Bugün hava çok güzel."]
    )
    sorgu = sorguyu_vektore_cevir("Konut finansmanı kâr payı oranı kaç?")

    benzerlik = [sum(a * b for a, b in zip(sorgu, belge)) for belge in belgeler]
    assert benzerlik[0] > benzerlik[1], "Alakali belge, alakasizdan daha yakin olmali"

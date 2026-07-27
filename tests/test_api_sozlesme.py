"""API sozlesmesi testleri.

AMAC: Havin'in arayuzu bu alan adlarina gore kuruldugu icin, buradaki
alanlarin adi/varligi sessizce degisirse onun kodu bozulur. Bu testler
sozlesmeyi kilitler - CI her push'ta calistirir.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

GECERLI_BASLIK = {"Authorization": "Bearer mock-token-test"}


# ---------------------------------------------------------------------------
# Kimlik dogrulama
# ---------------------------------------------------------------------------


def test_kok_uc_noktasi_kimlik_gerektirmez():
    yanit = client.get("/")
    assert yanit.status_code == 200
    assert yanit.json()["durum"] == "calisiyor"


def test_saglik_kontrolu_calisiyor():
    yanit = client.get("/saglik")
    assert yanit.status_code == 200
    assert yanit.json()["durum"] == "saglikli"


@pytest.mark.parametrize(
    "yol,metot,govde",
    [
        ("/kampanyalar", "get", None),
        ("/karsilastir", "post", {"ids": [1, 2]}),
        ("/chat", "post", {"soru": "test"}),
    ],
)
def test_authorization_header_olmadan_401_doner(yol, metot, govde):
    """Havin'in Gun 1'den dogru header formatini kullanmasini garanti eder."""
    yanit = getattr(client, metot)(yol, json=govde) if govde else client.get(yol)
    assert yanit.status_code == 401


def test_bozuk_authorization_formati_401_doner():
    yanit = client.get("/kampanyalar", headers={"Authorization": "mock-token"})
    assert yanit.status_code == 401


# ---------------------------------------------------------------------------
# /kampanyalar
# ---------------------------------------------------------------------------


def test_kampanyalar_liste_doner():
    yanit = client.get("/kampanyalar", headers=GECERLI_BASLIK)
    assert yanit.status_code == 200
    veri = yanit.json()
    assert isinstance(veri, list)
    assert len(veri) >= 3


def test_kampanya_kaydinda_zorunlu_alanlar_var():
    """CampaignRecord sozlesmesi (rapor Bolum 15)."""
    veri = client.get("/kampanyalar", headers=GECERLI_BASLIK).json()
    kayit = veri[0]

    zorunlu = [
        "banka",
        "kampanya_adi",
        "kampanya_turu",
        "kar_payi_orani_percent",
        "kar_payi_orani_decimal",
        "vade_ay",
        "odul_miktari",
        "odul_birimi",
        "kampanya_baslangic",
        "kampanya_bitis",
        "durum",
        "hedef_kitle",
        "kaynak_url",
        "confidence",
        "alan_belirtilmemis",
    ]
    for alan in zorunlu:
        assert alan in kayit, f"Sozlesme alani eksik: {alan}"


def test_eksik_veri_gizlenmez_isaretlenir():
    """Seffaflik ilkesi (rapor Bolum 5.7/15): eksik alan None kalir ve
    alan_belirtilmemis icinde True olarak bayraklanir."""
    veri = client.get("/kampanyalar", headers=GECERLI_BASLIK).json()

    # D Bankasi kart kampanyasinda kar payi orani YOK ama kayit gizlenmiyor
    kart = [k for k in veri if k["banka"] == "D Bankasi"][0]
    assert kart["kar_payi_orani_percent"] is None
    assert kart["alan_belirtilmemis"].get("kar_payi_orani_percent") is True


def test_banka_filtresi_calisir():
    yanit = client.get("/kampanyalar?banka=A Bankasi", headers=GECERLI_BASLIK)
    assert yanit.status_code == 200
    veri = yanit.json()
    assert len(veri) == 1
    assert veri[0]["banka"] == "A Bankasi"


def test_olmayan_kampanya_404_doner():
    yanit = client.get("/kampanyalar/9999", headers=GECERLI_BASLIK)
    assert yanit.status_code == 404


# ---------------------------------------------------------------------------
# /karsilastir
# ---------------------------------------------------------------------------


def test_karsilastirma_en_dusuk_orani_basa_koyar():
    """Sartname Md. 5.7 ornegi: C Bankasi (%1,87) en avantajli orandir."""
    yanit = client.post(
        "/karsilastir",
        json={"ids": [1, 2, 3], "kriter": "en_dusuk_kar_payi"},
        headers=GECERLI_BASLIK,
    )
    assert yanit.status_code == 200
    sonuclar = yanit.json()["sonuclar"]
    assert sonuclar[0]["banka"] == "C Bankasi"
    assert sonuclar[0]["kar_payi_orani_percent"] == 1.87


def test_karsilastirmada_null_degerler_en_sona_gider():
    """NULLS LAST: orani olmayan kayit listenin BASINA gelmemeli."""
    yanit = client.post(
        "/karsilastir",
        json={"ids": [1, 4], "kriter": "en_dusuk_kar_payi"},
        headers=GECERLI_BASLIK,
    )
    sonuclar = yanit.json()["sonuclar"]
    assert sonuclar[-1]["kar_payi_orani_percent"] is None


def test_tek_kampanya_ile_karsilastirma_reddedilir():
    yanit = client.post(
        "/karsilastir", json={"ids": [1]}, headers=GECERLI_BASLIK
    )
    assert yanit.status_code == 422  # Pydantic: min_length=2


# ---------------------------------------------------------------------------
# /chat  -  audit blogu sozlesmesi
# ---------------------------------------------------------------------------


def test_chat_yanit_verir():
    yanit = client.post(
        "/chat", json={"soru": "A Bankasi'nin konut orani ne?"}, headers=GECERLI_BASLIK
    )
    assert yanit.status_code == 200
    assert "cevap" in yanit.json()


def test_chat_audit_blogu_tum_alanlari_icerir():
    """KRITIK: Havin'in Juri Audit Paneli bu alan adlarina gore kurulur
    (rapor Bolum 10.2). Alanlar Sprint 1'de bos olabilir ama VAR olmalidir."""
    yanit = client.post("/chat", json={"soru": "test"}, headers=GECERLI_BASLIK)
    audit = yanit.json()["audit"]

    beklenen = [
        "intent",
        "intent_confidence",
        "cagrilan_arac",
        "sql_sorgusu",
        "retriever_sonuclari",
        "extraction_confidence",
        "response_confidence",
        "regex_basari_orani",
        "latency_ms",
        "cache_hit",
        "model",
        "temperature",
    ]
    for alan in beklenen:
        assert alan in audit, f"Audit paneli alani eksik: {alan}"


def test_chat_yanitinda_kaynak_ve_confidence_alanlari_var():
    """Provenance sozlesmesi (rapor Bolum 9)."""
    yanit = client.post("/chat", json={"soru": "test"}, headers=GECERLI_BASLIK).json()
    assert "kaynaklar" in yanit
    assert isinstance(yanit["kaynaklar"], list)
    assert "confidence" in yanit
    assert "fallback" in yanit


def test_cok_uzun_soru_reddedilir():
    yanit = client.post(
        "/chat", json={"soru": "a" * 600}, headers=GECERLI_BASLIK
    )
    assert yanit.status_code == 422


def test_bos_soru_reddedilir():
    yanit = client.post("/chat", json={"soru": ""}, headers=GECERLI_BASLIK)
    assert yanit.status_code == 422

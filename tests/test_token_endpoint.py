"""POST /token uctan uca testi - gercek JWT modu.

CI'da postgres olmadigi icin (ve gercek kullanici gerektirdigi icin) SKIP
eder - bkz. test_kampanya_repository.py ile ayni desen.
"""

import uuid

import pytest


def _db_erisilebilir_mi() -> bool:
    try:
        from api.db import engine

        with engine.connect():
            return True
    except Exception:
        return False


DB_YOK_MESAJI = "Yerel PostgreSQL calismiyor (docker compose up -d postgres) - CI'da beklenen durum"

pytestmark = pytest.mark.skipif(not _db_erisilebilir_mi(), reason=DB_YOK_MESAJI)


@pytest.fixture
def gercek_jwt_client(monkeypatch):
    """api.main modulunun kendi GERCEK_JWT_AKTIF kopyasini True yapar
    (import-anindaki `from api.auth import GERCEK_JWT_AKTIF` yuzden
    api.auth.GERCEK_JWT_AKTIF'i degistirmek yetmez, api.main'i de
    monkeypatch etmek gerekir)."""
    from fastapi.testclient import TestClient

    import api.main as main_modulu

    monkeypatch.setenv("JWT_SECRET", "test-icin-gizli-anahtar")
    monkeypatch.setattr(main_modulu, "GERCEK_JWT_AKTIF", True)
    monkeypatch.setattr("api.auth.GERCEK_JWT_AKTIF", True)
    yield TestClient(main_modulu.app)


@pytest.fixture
def test_kullanicisi():
    from api.db import OturumYerel
    from api.kullanici_repository import kullanici_olustur
    from api.models import Kullanici

    ad = f"test-{uuid.uuid4().hex[:8]}"
    oturum = OturumYerel()
    kullanici_olustur(oturum, ad, "test-parola-123", rol="denetleyici")
    oturum.close()

    yield ad, "test-parola-123"

    oturum = OturumYerel()
    oturum.query(Kullanici).filter(Kullanici.kullanici_adi == ad).delete()
    oturum.commit()
    oturum.close()


def test_dogru_bilgilerle_token_alinir(gercek_jwt_client, test_kullanicisi):
    ad, sifre = test_kullanicisi
    yanit = gercek_jwt_client.post("/token", data={"username": ad, "password": sifre})
    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["token_type"] == "bearer"
    assert len(govde["access_token"]) > 10


def test_yanlis_parolada_401_doner(gercek_jwt_client, test_kullanicisi):
    ad, _ = test_kullanicisi
    yanit = gercek_jwt_client.post("/token", data={"username": ad, "password": "yanlis"})
    assert yanit.status_code == 401


def test_alinan_token_korumali_uc_noktada_gecerlidir(gercek_jwt_client, test_kullanicisi):
    ad, sifre = test_kullanicisi
    tok = gercek_jwt_client.post("/token", data={"username": ad, "password": sifre}).json()["access_token"]

    yanit = gercek_jwt_client.get("/kampanyalar", headers={"Authorization": f"Bearer {tok}"})
    assert yanit.status_code == 200


def test_sahte_token_korumali_uc_noktada_401_doner(gercek_jwt_client):
    yanit = gercek_jwt_client.get("/kampanyalar", headers={"Authorization": "Bearer sahte-token"})
    assert yanit.status_code == 401

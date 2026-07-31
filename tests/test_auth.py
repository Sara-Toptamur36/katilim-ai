"""api/auth.py testleri - parola hashleme ve gercek JWT modu.

TASARIM: sifre_hashle/sifre_dogrula ve token_uret/token_dogrula (gercek
modda) DB gerektirmez, her zaman calisir. Gercek modu test etmek icin
GERCEK_JWT_AKTIF modul degiskeni monkeypatch edilir (env degiskeni sadece
import ANINDA okunur, bu yuzden import sonrasi degistirmek gerekir).
"""

import pytest

from api import auth
from api.auth import sifre_dogrula, sifre_hashle, token_dogrula, token_uret


def test_sifre_hashle_duz_metni_asla_donmez():
    hash_deger = sifre_hashle("gizli-parola-123")
    assert hash_deger != "gizli-parola-123"
    assert hash_deger.startswith("$2b$")


def test_sifre_dogrula_dogru_parolada_true_doner():
    hash_deger = sifre_hashle("dogru-parola")
    assert sifre_dogrula("dogru-parola", hash_deger) is True


def test_sifre_dogrula_yanlis_parolada_false_doner():
    hash_deger = sifre_hashle("dogru-parola")
    assert sifre_dogrula("yanlis-parola", hash_deger) is False


def test_sifre_dogrula_bozuk_hashte_hata_firlatmaz_false_doner():
    assert sifre_dogrula("herhangi-bir-sey", "bozuk-hash-degeri") is False


def test_sifre_hashle_her_seferinde_farkli_hash_uretir():
    """bcrypt her cagriya rastgele salt ekler - ayni parola bile farkli
    hash uretmeli (rainbow table saldirilarina karsi)."""
    assert sifre_hashle("ayni-parola") != sifre_hashle("ayni-parola")


# ---------------------------------------------------------------------------
# Gercek JWT modu (GERCEK_JWT_AKTIF=true simulasyonu)
# ---------------------------------------------------------------------------


@pytest.fixture
def gercek_jwt_modu(monkeypatch):
    monkeypatch.setattr(auth, "GERCEK_JWT_AKTIF", True)
    monkeypatch.setenv("JWT_SECRET", "test-icin-gizli-anahtar")
    yield


def test_gercek_modda_uretilen_token_dogrulanir(gercek_jwt_modu):
    tok = token_uret("ayse", rol="denetleyici")
    sonuc = token_dogrula(f"Bearer {tok}")
    assert sonuc == {"kullanici": "ayse", "rol": "denetleyici", "mock": False}


def test_gercek_modda_gecersiz_token_401_verir(gercek_jwt_modu):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as hata:
        token_dogrula("Bearer gecersiz-bir-token")
    assert hata.value.status_code == 401


def test_gizli_anahtar_tanimsizsa_hata_verir(gercek_jwt_modu, monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        token_uret("test")

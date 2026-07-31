"""api/kullanici_repository.py testleri.

CI'da postgres servisi olmadigi icin tum testler yerel DB'ye erisilemezse
SKIP eder (bkz. test_kampanya_repository.py ile ayni desen).
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
def oturum():
    from api.db import OturumYerel
    from api.models import Kullanici

    s = OturumYerel()
    yield s
    # Test sirasinda olusturulan kullanicilari temizle (test-*)
    s.query(Kullanici).filter(Kullanici.kullanici_adi.like("test-%")).delete(synchronize_session=False)
    s.commit()
    s.close()


def _benzersiz_kullanici_adi() -> str:
    return f"test-{uuid.uuid4().hex[:8]}"


def test_kullanici_olustur_ve_getir(oturum):
    from api.kullanici_repository import kullanici_getir, kullanici_olustur

    ad = _benzersiz_kullanici_adi()
    kullanici_olustur(oturum, ad, "gecerli-parola-123", rol="denetleyici")

    bulunan = kullanici_getir(oturum, ad)
    assert bulunan is not None
    assert bulunan.rol == "denetleyici"
    assert bulunan.sifre_hash != "gecerli-parola-123"  # duz metin ASLA saklanmaz


def test_kullanici_dogrula_dogru_bilgilerle_kullanici_doner(oturum):
    from api.kullanici_repository import kullanici_dogrula, kullanici_olustur

    ad = _benzersiz_kullanici_adi()
    kullanici_olustur(oturum, ad, "dogru-parola-123")

    sonuc = kullanici_dogrula(oturum, ad, "dogru-parola-123")
    assert sonuc is not None
    assert sonuc.kullanici_adi == ad


def test_kullanici_dogrula_yanlis_parolada_none_doner(oturum):
    from api.kullanici_repository import kullanici_dogrula, kullanici_olustur

    ad = _benzersiz_kullanici_adi()
    kullanici_olustur(oturum, ad, "dogru-parola-123")

    assert kullanici_dogrula(oturum, ad, "yanlis-parola") is None


def test_kullanici_dogrula_olmayan_kullanicida_none_doner(oturum):
    from api.kullanici_repository import kullanici_dogrula

    assert kullanici_dogrula(oturum, "hic-var-olmayan-kullanici", "her-sey") is None


def test_kullanici_dogrula_pasif_kullaniciyi_reddeder(oturum):
    from api.kullanici_repository import kullanici_dogrula, kullanici_olustur

    ad = _benzersiz_kullanici_adi()
    kullanici = kullanici_olustur(oturum, ad, "dogru-parola-123")
    kullanici.aktif = False
    oturum.commit()

    assert kullanici_dogrula(oturum, ad, "dogru-parola-123") is None

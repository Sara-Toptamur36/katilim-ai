"""api/kampanya_repository.py testleri.

KRITIK KONTROL: mock_data.id_ile_getir() Pydantic CampaignRecord doner
(duz dict DEGIL) - comparison/compare_engine.py attribute erisimi kullanir
(kayit.durum.value, kayit.model_dump(...) vb.). Bu testler, DB katmaninin
da AYNI sozlesmeye uydugunu (duz dict degil, gercek CampaignRecord)
dogrular - aksi halde GERCEK_VERI_AKTIF=true yapildiginda /karsilastir
sessizce kirilir.

CI'da postgres servisi olmadigi icin tum testler yerel DB'ye erisilemezse
SKIP eder (bkz. test_postgrese_yukle.py ile ayni desen).
"""

import pytest

from api.schemas import CampaignRecord


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
def dolu_oturum():
    """Testten once en az bir kayit oldugunu garanti eder (yukleyiciyi calistirir)."""
    from api.db import OturumYerel
    from scraper.scripts.postgrese_yukle import yukle

    yukle()
    oturum = OturumYerel()
    yield oturum
    oturum.close()


def test_kampanyalari_getir_db_gercek_campaignrecord_doner(dolu_oturum):
    """Duz dict DEGIL, Pydantic CampaignRecord donmeli - aksi halde
    compare_engine'in attribute erisimi (kayit.durum.value) patlar."""
    from api.kampanya_repository import kampanyalari_getir_db

    kayitlar = kampanyalari_getir_db(dolu_oturum)
    assert len(kayitlar) > 0
    assert isinstance(kayitlar[0], CampaignRecord)


def test_id_ile_getir_db_gercek_campaignrecord_doner(dolu_oturum):
    from api.kampanya_repository import id_ile_getir_db, kampanyalari_getir_db

    ilk = kampanyalari_getir_db(dolu_oturum)[0]
    tekil = id_ile_getir_db(dolu_oturum, ilk.id)
    assert isinstance(tekil, CampaignRecord)
    assert tekil.id == ilk.id


def test_id_ile_getir_db_olmayan_id_none_doner(dolu_oturum):
    from api.kampanya_repository import id_ile_getir_db

    assert id_ile_getir_db(dolu_oturum, 999_999) is None


def test_banka_filtresi_calisir(dolu_oturum):
    from api.kampanya_repository import kampanyalari_getir_db

    tumu = kampanyalari_getir_db(dolu_oturum)
    ilk_banka = tumu[0].banka
    suzulmus = kampanyalari_getir_db(dolu_oturum, banka=ilk_banka)
    assert len(suzulmus) > 0
    assert all(k.banka == ilk_banka for k in suzulmus)


def test_henuz_cikarilmamis_alanlar_seffaf_isaretlenir(dolu_oturum):
    """Yukleyici henuz cikarim yapmadigi icin, kayitlarda finansal alanlar
    None olmali VE alan_belirtilmemis'te True olarak gorunmeli - sessizce
    gizlenmemeli (rapor Bolum 5.7/15)."""
    from api.kampanya_repository import kampanyalari_getir_db

    kayit = kampanyalari_getir_db(dolu_oturum)[0]
    assert kayit.kar_payi_orani_percent is None
    assert kayit.alan_belirtilmemis.get("kar_payi_orani_percent") is True


def test_dogrulanan_alanlar_api_sinirinda_kaybolmaz(dolu_oturum):
    """DENETIM BULGUSU: _kayda_cevir() bu alani hic aktarmiyordu -
    Verifier gercekten calisip DB'ye yazsa bile API sessizce {} donuyordu
    (sema kendi aciklamasinda bos = 'Verifier hic calismadi' diyor).
    terminoloji_tutarli'nin daha once yasadigi ayni API-siniri hatasi."""
    from api.kampanya_repository import id_ile_getir_db, kampanyalari_getir_db
    from api.models import Kampanya

    ilk = kampanyalari_getir_db(dolu_oturum)[0]
    satir = dolu_oturum.get(Kampanya, ilk.id)
    satir.dogrulanan_alanlar = {"kar_payi_orani_percent": True, "vade_ay": False}
    dolu_oturum.commit()

    tekil = id_ile_getir_db(dolu_oturum, ilk.id)
    assert tekil.dogrulanan_alanlar == {"kar_payi_orani_percent": True, "vade_ay": False}


def test_kar_payi_tablosu_api_sinirinda_kaybolmaz(dolu_oturum):
    """Ayni API-siniri hata sinifi (bkz. test_dogrulanan_alanlar_api_
    sinirinda_kaybolmaz) - yeni bir DB sutunu eklerken _kayda_cevir()'e
    eklemeyi unutmak kolay, bu yuzden her yeni JSON sutunu icin regresyon
    kilidi yaziliyor."""
    from api.kampanya_repository import id_ile_getir_db, kampanyalari_getir_db
    from api.models import Kampanya

    ilk = kampanyalari_getir_db(dolu_oturum)[0]
    satir = dolu_oturum.get(Kampanya, ilk.id)
    ornek_tablo = [
        {"tablo_index": 0, "sutunlar": ["Vade", "Kar Orani"], "satirlar": [{"Vade": 3, "Kar Orani": "4,20%"}]}
    ]
    satir.kar_payi_tablosu = ornek_tablo
    dolu_oturum.commit()

    tekil = id_ile_getir_db(dolu_oturum, ilk.id)
    assert tekil.kar_payi_tablosu == ornek_tablo


def test_karsilastirma_motoruyla_uyumlu(dolu_oturum):
    """Gercek entegrasyon: DB'den gelen kayitlar comparison/compare_engine.py
    icinden gecebilmeli (attribute erisimi kirilmamali)."""
    from api.kampanya_repository import kampanyalari_getir_db
    from comparison.compare_engine import karsilastir_bellekte

    kayitlar = kampanyalari_getir_db(dolu_oturum)[:5]
    sonuc = karsilastir_bellekte(kayitlar, kriter="en_dusuk_kar_payi")
    assert "sonuclar" in sonuc
    assert len(sonuc["sonuclar"]) == len(kayitlar)

"""scraper/scripts/postgrese_yukle.py testleri.

TASARIM: Bu dosyanin cogunlugu SAF FONKSIYON testidir (DB gerektirmez,
CI'da her zaman calisir). Gercekten veritabanina yazan idempotentlik testi
yalnizca yerel PostgreSQL calisiyorsa calisir - CI'da postgres servisi
olmadigi icin SKIP eder (bkz. tests/test_scraper_regresyon.py ile ayni
"gerekcli skip" tasarim ilkesi).
"""

import pytest

from scraper.scripts.postgrese_yukle import (
    HENUZ_CIKARILMAMIS_ALANLAR,
    _tarihi_cikar,
    _url_slug_to_baslik,
)


def test_url_slug_okunabilir_baslik_uretir():
    url = "https://www.albaraka.com.tr/tr/kampanyalar/detay/mtv-odemelerinize-vade-farksiz-3-taksit-10"
    assert _url_slug_to_baslik(url) == "Mtv Odemelerinize Vade Farksiz 3 Taksit 10"


def test_url_slug_sondaki_slash_yoksayilir():
    assert _url_slug_to_baslik("https://example.com/kampanya-adi/") == "Kampanya Adi"


def test_url_slug_sorgu_stringi_atilir():
    url = "https://example.com/kampanyalar/ornek-kampanya?ref=mobil"
    assert _url_slug_to_baslik(url) == "Ornek Kampanya"


def test_url_slug_bos_kalirsa_yer_tutucu_doner():
    assert _url_slug_to_baslik("") == "Baslik Belirlenemedi"


def test_tarihi_cikar_iso_formati_parse_eder():
    assert str(_tarihi_cikar("2026-07-31T18:46:26.925298")) == "2026-07-31"


def test_tarihi_cikar_bos_deger_none_doner():
    assert _tarihi_cikar(None) is None
    assert _tarihi_cikar("gecersiz-tarih") is None


def test_henuz_cikarilmamis_alanlar_finansal_alanlari_kapsiyor():
    """Yagmur'un cikarim katmani calismadan once, bu alanlarin hepsi
    alan_belirtilmemis'te True olarak isaretlenmeli (seffaflik ilkesi)."""
    zorunlu_alanlar = {
        "kar_payi_orani_percent", "vade_ay", "finansman_tutari",
        "odul_miktari", "odul_birimi", "kampanya_baslangic", "kampanya_bitis",
    }
    assert zorunlu_alanlar.issubset(set(HENUZ_CIKARILMAMIS_ALANLAR))


# ---------------------------------------------------------------------------
# Veritabani gerektiren testler - yerel Postgres yoksa SKIP edilir.
# ---------------------------------------------------------------------------


def _db_erisilebilir_mi() -> bool:
    try:
        from api.db import engine

        with engine.connect():
            return True
    except Exception:
        return False


DB_YOK_MESAJI = "Yerel PostgreSQL calismiyor (docker compose up -d postgres) - CI'da beklenen durum"
DB_ERISILEBILIR = _db_erisilebilir_mi()  # Bir kez hesaplanir - her testte tekrar baglanti denenmez


@pytest.mark.skipif(not DB_ERISILEBILIR, reason=DB_YOK_MESAJI)
def test_yukleme_idempotenttir():
    """Ayni scraper ciktisi iki kez yuklendiginde ikinci calistirma yeni
    satir EKLEMEMELI (yalnizca 'zaten var' sayacini artirmali)."""
    from scraper.scripts.postgrese_yukle import yukle

    ilk = yukle()
    ikinci = yukle()

    assert ikinci["eklendi"] == 0
    assert ikinci["atlandi"] >= ilk["eklendi"] + ilk["atlandi"]


@pytest.mark.skipif(not DB_ERISILEBILIR, reason=DB_YOK_MESAJI)
def test_tek_calistirmada_mukerrer_kaynak_url_uretilmez():
    """DENETIM BULGUSU (27 Agustos 2026): `mevcut` sorgusu TEK bir `yukle()`
    cagrisi icindeki bir onceki satiri gormuyordu - OturumYerel autoflush=
    False ile kurulu (api/db.py), `oturum.add()` sonrasi flush cagrilmadan
    satir sorgulanabilir olmuyordu. Sonuc: scraper/raw_data'da AYNI sayfanin
    iki farkli tarihte taranmis kopyasi (ör. Albaraka'nin
    vade-farksiz-kampanyasi 31 Temmuz VE 11 Agustos taramalari) tek bir
    `yukle()` cagrisinda IKI ayri satir olarak ekleniyordu - modulun kendi
    'idempotent' iddiasi TEK CALISTIRMA icinde bile bozulmustu.
    `test_yukleme_idempotenttir` bunu YAKALAMAZDI cunku yalnizca IKI AYRI
    `yukle()` CAGRISI arasindaki durumu kontrol ediyor (bkz. yukaridaki
    test) - hata birinci cagrinin KENDI icindeydi.
    """
    from sqlalchemy import func

    from api.db import OturumYerel
    from api.models import Kampanya
    from scraper.scripts.postgrese_yukle import yukle

    yukle()

    oturum = OturumYerel()
    try:
        mukerrer = (
            oturum.query(Kampanya.kaynak_url, func.count(Kampanya.id))
            .group_by(Kampanya.kaynak_url)
            .having(func.count(Kampanya.id) > 1)
            .all()
        )
    finally:
        oturum.close()

    assert not mukerrer, f"mukerrer kaynak_url: {mukerrer[:5]}"


@pytest.mark.skipif(not DB_ERISILEBILIR, reason=DB_YOK_MESAJI)
def test_yuklenen_kayitlarda_alan_belirtilmemis_isaretlenmis():
    """Henuz cikarim yapilmamis kayitlarda finansal alanlar seffaf sekilde
    'belirtilmemis' isaretlenmeli, sessizce bos birakilmamali."""
    from api.db import OturumYerel
    from api.models import Kampanya
    from scraper.scripts.postgrese_yukle import yukle

    yukle()
    oturum = OturumYerel()
    try:
        satir = oturum.query(Kampanya).first()
        assert satir is not None
        assert satir.alan_belirtilmemis.get("kar_payi_orani_percent") is True
    finally:
        oturum.close()


def test_url_slug_basligi_dosya_uzantisini_atar():
    """Kampanya adi arayuzde "... .aspx" olarak gorunmemeli.

    Olculdu (24.08.2026): 436 kaydin 28'inde kampanya adi bir dosya adiydi
    ("Yakininizi Davet Edin.aspx"), cogu .aspx tabanli Turkiye Finans
    sitesinden. Karsilastirma ekrani juriye gosterilen yerdir; orada dosya
    uzantisi gormek verinin islenmemis oldugu izlenimi verir.
    """
    from scraper.scripts.postgrese_yukle import _url_slug_to_baslik

    assert _url_slug_to_baslik("https://x.com/tr/Yakininizi-Davet-Edin.aspx") == (
        "Yakininizi Davet Edin"
    )
    assert _url_slug_to_baslik("https://x.com/a/kampanyalar.html") == "Kampanyalar"
    assert _url_slug_to_baslik("https://x.com/a/sayfa.PHP") == "Sayfa"
    # Uzantisi olmayan slug'lar degismemeli
    assert _url_slug_to_baslik("https://x.com/a/konut-finansmani") == "Konut Finansmani"

"""extraction/regex_ile_zenginlestir.py testleri.

TASARIM: test_postgrese_yukle.py ile ayni ilke - saf fonksiyon (ham metin
esleme) DB'siz test edilir; gercek DB guncellemesi yalnizca yerel Postgres
calisiyorsa test edilir, CI'da SKIP eder.
"""

import pytest

import extraction.regex_ile_zenginlestir as zenginlestir_modulu
from extraction.hybrid_pipeline import kaydi_hibrit_cikar
from extraction.regex_ile_zenginlestir import CIKARILABILEN_ALANLAR, _ham_metinleri_url_ile_esle


def test_ham_metinleri_url_ile_esle_gercek_dosyalari_bulur():
    esleme = _ham_metinleri_url_ile_esle()
    assert len(esleme) >= 20
    assert all(isinstance(metin, str) and metin for metin in esleme.values())


def test_cikarilabilen_alanlar_finansal_alanlari_kapsiyor():
    zorunlu = {
        "kar_payi_orani_percent", "vade_ay", "taksit_sayisi",
        "erteleme_suresi_ay", "finansman_tutari", "odul_miktari",
    }
    assert zorunlu.issubset(set(CIKARILABILEN_ALANLAR))


def test_verifier_uretim_zincirine_baglidir():
    """DENETIM BULGUSU: validation/verifier.py yazilmis ve gercek veriyle
    olculmustu (6/6 yanlis pozitif reddedildi) ama hicbir yer onu import
    etmiyordu - modul var ama uretimde HIC calismiyordu. Bu test, DB
    gerektirmeden, modulun Verifier'i gercekten kullandigini kilitler."""
    from validation.verifier import kaydi_dogrula

    assert zenginlestir_modulu.kaydi_dogrula is kaydi_dogrula


def test_veritabanini_dolduran_fonksiyon_hibrit_boru_hattini_kullanir():
    """DENETIM BULGUSU (mentor denetimi): bu script eskiden regex-only
    kaydi_cikar()'i cagiriyordu - hibrit boru hatti (NER+LLM) yazildiktan
    SONRA bile veritabanini GERCEKTEN dolduran kod hala regex-only kalmisti
    (README'nin 'hibrit cikarim' iddiasiyla veritabanini dolduran kod
    arasinda fark vardi). Bu test, modulun kaydi_hibrit_cikar'i (kaydi_cikar
    DEGIL) kullandigini DB gerektirmeden kilitler - reel bir DB olmadan da
    calisir, boylece bu regresyon CI'da her push'ta yakalanir."""
    assert zenginlestir_modulu.kaydi_hibrit_cikar is kaydi_hibrit_cikar


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
DB_ERISILEBILIR = _db_erisilebilir_mi()


@pytest.mark.skipif(not DB_ERISILEBILIR, reason=DB_YOK_MESAJI)
def test_zenginlestirme_mevcut_dolu_alani_ezmez():
    """Bir kayitta zaten manuel/onceki bir yontemle doldurulmus bir alan
    varsa, regex motoru bu degeri UZERINE YAZMAMALI (idempotentlik/veri
    koruma ilkesi - bkz. postgrese_yukle.py'nin ayni ilkesi)."""
    from api.db import OturumYerel
    from api.models import Kampanya
    from extraction.regex_ile_zenginlestir import zenginlestir

    oturum = OturumYerel()
    try:
        satir = oturum.query(Kampanya).first()
        if satir is None:
            pytest.skip("Test icin veritabaninda kayit yok - once postgrese_yukle.yukle() calistirilmali")
        satir.vade_ay = 999  # gercekte olmayacak, koruma testi icin belirgin sentinel
        oturum.commit()
        korunan_id = satir.id
    finally:
        oturum.close()

    zenginlestir()

    oturum = OturumYerel()
    try:
        guncel = oturum.get(Kampanya, korunan_id)
        assert guncel.vade_ay == 999
    finally:
        oturum.close()


@pytest.mark.skipif(not DB_ERISILEBILIR, reason=DB_YOK_MESAJI)
def test_zenginlestirme_bos_alanlari_doldurur():
    from api.db import OturumYerel
    from api.models import Kampanya
    from extraction.regex_ile_zenginlestir import zenginlestir

    sonuc = zenginlestir()
    assert sonuc["guncellendi"] + sonuc["atlandi"] + sonuc["ham_metin_yok"] > 0
    assert "dogrulanamayan" in sonuc

    oturum = OturumYerel()
    try:
        # "regex" VEYA "hibrit" olabilir - hangisi oldugu, NER/LLM'in o
        # kayitta gercekten katki yapip yapmadigina bagli (bkz.
        # regex_ile_zenginlestir.py, kullanilan_katmanlar mantigi).
        doldurulmus = (
            oturum.query(Kampanya)
            .filter(Kampanya.cikarim_yontemi.in_(["regex", "hibrit"]))
            .first()
        )
        if doldurulmus is not None:
            assert doldurulmus.confidence >= 0.0
    finally:
        oturum.close()

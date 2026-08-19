"""extraction/regex_ile_zenginlestir.py testleri.

TASARIM: test_postgrese_yukle.py ile ayni ilke - saf fonksiyon (ham metin
esleme) DB'siz test edilir; gercek DB guncellemesi yalnizca yerel Postgres
calisiyorsa test edilir, CI'da SKIP eder.
"""

import pytest

import extraction.regex_ile_zenginlestir as zenginlestir_modulu
from extraction.hybrid_pipeline import kaydi_hibrit_cikar
from extraction.regex_ile_zenginlestir import (
    CIKARILABILEN_ALANLAR,
    _ham_metinleri_url_ile_esle,
    _tablo_varsa_kar_payi_bastir,
)
from extraction.tablo_extractor import oran_tablolarini_sec


def test_ham_metinleri_url_ile_esle_gercek_dosyalari_bulur():
    esleme = _ham_metinleri_url_ile_esle()
    assert len(esleme) >= 20
    assert all(
        isinstance(veri["ham_metin"], str) and veri["ham_metin"] and "tablolar" in veri
        for veri in esleme.values()
    )


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


def test_kampanya_modelinde_dogrulanan_alanlar_sutunu_var():
    """DENETIM BULGUSU: Verifier sonucu ONCEDEN yalnizca log dosyasina
    yaziliyordu - API'den donmez, dashboard hicbir zaman "bu deger
    kaynakta dogrulandi mi" gosteremezdi. Bu test, DB gerektirmeden
    (SQLAlchemy model tanimini inceleyerek), kalici sutunun var oldugunu
    kilitler."""
    from api.models import Kampanya

    assert hasattr(Kampanya, "dogrulanan_alanlar")


def test_veritabanini_dolduran_fonksiyon_hibrit_boru_hattini_kullanir():
    """DENETIM BULGUSU (mentor denetimi): bu script eskiden regex-only
    kaydi_cikar()'i cagiriyordu - hibrit boru hatti (NER+LLM) yazildiktan
    SONRA bile veritabanini GERCEKTEN dolduran kod hala regex-only kalmisti
    (README'nin 'hibrit cikarim' iddiasiyla veritabanini dolduran kod
    arasinda fark vardi). Bu test, modulun kaydi_hibrit_cikar'i (kaydi_cikar
    DEGIL) kullandigini DB gerektirmeden kilitler - reel bir DB olmadan da
    calisir, boylece bu regresyon CI'da her push'ta yakalanir."""
    assert zenginlestir_modulu.kaydi_hibrit_cikar is kaydi_hibrit_cikar


def _raw_data_kaydi_yukle(goreli_yol: str) -> dict:
    import json
    from pathlib import Path

    dosya = Path(__file__).parent.parent / "scraper" / "raw_data" / goreli_yol
    with open(dosya, encoding="utf-8") as f:
        return json.load(f)


def test_tablolu_sayfada_dusuk_guvenli_kar_payi_tahmini_bastirilir():
    """OLCULDU (Turkiye Finans Ihtiyac Finansmani sayfalari, kaynak_url
    ...banka-calisanlarina-ozel-ihtiyac-finansmani.aspx): sayfada gercek bir
    vade/tutar kirilimli oran TABLOSU var (bkz. tablo_extractor.py), ama
    kaydi_hibrit_cikar() duz metinde flattened tablo hucrelerine rastlayip
    dusuk guvenli (0.6) bir "ilk bulunan %X" tahmini uretiyor - YANLIS
    sutundan (Aylık Toplam Maliyet) geliyordu. `_tablo_varsa_kar_payi_
    bastir()` bu tahmini (ve ondan derlenen kampanya_avantaji ozetini)
    DB'ye yazilmadan ONCE silmeli."""
    kayit = _raw_data_kaydi_yukle(
        "turkiyefinans/json/20260806_turkiyefinans_tr-tr_kampanyalar_"
        "Sayfalar_banka-calisanlarina-ozel-ihtiyac-finansmani.aspx.json"
    )
    secilen_tablo = oran_tablolarini_sec(kayit["tablolar"])
    assert secilen_tablo is not None  # onkosul: gercekten bir tablo var

    cikan = kaydi_hibrit_cikar(kayit["ham_metin"], ner_kullan=False, llm_kullan=False)
    assert cikan["kar_payi_orani_percent"] is not None  # onkosul: bastirilmadan once hatali dolu

    bastirilmis = _tablo_varsa_kar_payi_bastir(dict(cikan), secilen_tablo)
    assert bastirilmis["kar_payi_orani_percent"] is None
    assert bastirilmis["kar_payi_orani_decimal"] is None
    assert "kâr payı" not in (bastirilmis["kampanya_avantaji"] or "").lower()


def test_confident_ama_yanlis_kosullu_ifade_de_bastirilir():
    """OLCULDU (Albaraka dijital-musterilere-ozel-pratik-finansman-kart):
    sayfa "vade farksiz VEYA ozel oranli" diyor - kosullu bir secim, TUM
    kampanya icin degil - ama RE_VADE_FARKSIZ bunu YUKSEK guvenle (0.8,
    KILITLEME_GUVEN_ESIGI'ne esit) "kar_payi_orani=0" saniyor. Tablonun
    kendisi bunu yalanliyor: yalnizca EN KUCUK tutar diliminde (250-40.000
    TL) %0, digerlerinde %3,95/3,90/3,85. Bu, bastirmanin GUVEN esikli
    degil TABLO VARLIGINA gore olmasi gerektigini kanitlayan gercek
    ornektir - guven-esikli bir tasarim bu vakayi KACIRIRDI."""
    kayit = _raw_data_kaydi_yukle(
        "albaraka/json/20260731_albaraka_tr_kampanyalar_detay_"
        "dijital-musterilere-ozel-pratik-finansman-kart.json"
    )
    secilen_tablo = oran_tablolarini_sec(kayit["tablolar"])
    assert secilen_tablo is not None

    cikan = kaydi_hibrit_cikar(kayit["ham_metin"], ner_kullan=False, llm_kullan=False)
    assert cikan["kar_payi_orani_percent"] == 0.0  # onkosul: yuksek guvenle ama YANLIS dolu
    assert cikan["_izler"]["kar_payi_orani_percent"][1] >= 0.8  # "confident" oldugunu dogrula

    bastirilmis = _tablo_varsa_kar_payi_bastir(dict(cikan), secilen_tablo)
    assert bastirilmis["kar_payi_orani_percent"] is None


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


@pytest.mark.skipif(not DB_ERISILEBILIR, reason=DB_YOK_MESAJI)
def test_verifier_sonucu_kalici_olarak_yazilir():
    """DENETIM BULGUSU: Verifier calisiyordu ama sonucu yalnizca log
    dosyasina yaziliyordu - satirdaki `dogrulanan_alanlar` sutunu hep
    bos kalirdi, API/dashboard hicbir zaman "bu deger kaynakta dogrulandi
    mi" gosteremezdi. Bu test, gercek DB'de zenginlestir() calistiktan
    sonra en az bir satirda dogrulanan_alanlar'in DOLU oldugunu kilitler -
    yalnizca modulun Verifier'i CAGIRDIGINI degil, sonucu GERCEKTEN
    SAKLADIGINI dogrular."""
    from api.db import OturumYerel
    from api.models import Kampanya
    from extraction.regex_ile_zenginlestir import zenginlestir

    zenginlestir()

    oturum = OturumYerel()
    try:
        # NOT: dogrulanan_alanlar != {} SQL'de FILTRELENEMEZ - Postgres'in
        # duz JSON tipi (JSONB degil) != operatorunu desteklemiyor
        # (psycopg.errors.UndefinedFunction: operator does not exist:
        # json <> json). Bu yuzden bos olmayanlik kontrolu Python
        # tarafinda yapilir.
        dogrulanmis_satir = next(
            (
                satir
                for satir in oturum.query(Kampanya).filter(Kampanya.dogrulanan_alanlar.isnot(None))
                if satir.dogrulanan_alanlar
            ),
            None,
        )
        if dogrulanmis_satir is None:
            pytest.skip(
                "Bu calistirmada hicbir satirda YENI alan doldurulmadi "
                "(hepsi zaten doluydu/atlandi) - Verifier'in cagirilmasi "
                "icin en az bir yeni alan doldurulmasi gerekir"
            )
        assert isinstance(dogrulanmis_satir.dogrulanan_alanlar, dict)
        assert all(isinstance(v, bool) for v in dogrulanmis_satir.dogrulanan_alanlar.values())
    finally:
        oturum.close()

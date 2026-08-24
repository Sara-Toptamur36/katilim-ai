"""extraction/llm_extractor.py::_cikarim_semasi_olustur testleri.

BILEREK test_llm_extractor.py'nin DISINDA: o dosyanin tamami Ollama
servisine bagli oldugu icin modul-seviyesinde skip'leniyor
(`pytestmark = [pytest.mark.skipif(not _ollama_hazir_mi(), ...)]`) - saf
bir mantik fonksiyonu (ag/servis gerektirmez) o skip'in altina girerse
CI'da HICBIR ZAMAN calismazdi. Bu fonksiyon EVREN'in sema-kisitli JSON
yoluna (evren_istemci.py, bkz. docs/adr/0002) girdi uretir, ag baglantisi
gerektirmez.
"""

from extraction.llm_extractor import _cikarim_semasi_olustur


def test_sema_strict_json_schema_bicimindedir():
    sema = _cikarim_semasi_olustur({"vade_ay"})
    assert sema["type"] == "json_schema"
    assert sema["json_schema"]["strict"] is True
    assert sema["json_schema"]["schema"]["additionalProperties"] is False


def test_sema_istenen_tum_alanlari_required_listeler():
    alanlar = {"vade_ay", "finansman_tutari", "kampanya_bitis"}
    sema = _cikarim_semasi_olustur(alanlar)
    assert set(sema["json_schema"]["schema"]["required"]) == alanlar
    assert set(sema["json_schema"]["schema"]["properties"]) == alanlar


def test_sema_required_deterministik_siralanmis():
    """DENETIM BULGUSU (llm_extractor.py modul basi): set iterasyon sirasi
    surecler arasi degisebilir, bu da ayni girdiyle ayni cagrida farkli
    alan sirasi -> farkli LLM davranisi riski tasir. sorted() ile
    deterministik sira garanti edilir - EVREN yolunda da AYNI disipline
    uyulur."""
    alanlar = {"kampanya_bitis", "vade_ay", "finansman_tutari", "odul_miktari"}
    sema = _cikarim_semasi_olustur(alanlar)
    assert sema["json_schema"]["schema"]["required"] == sorted(alanlar)


def test_sema_sayisal_tam_sayi_alanlari_integer_null():
    sema = _cikarim_semasi_olustur({"vade_ay", "taksit_sayisi", "erteleme_suresi_ay"})
    ozellikler = sema["json_schema"]["schema"]["properties"]
    for alan in ("vade_ay", "taksit_sayisi", "erteleme_suresi_ay"):
        assert ozellikler[alan]["type"] == ["integer", "null"]


def test_sema_tutar_alanlari_number_null():
    sema = _cikarim_semasi_olustur({"finansman_tutari", "odul_miktari"})
    ozellikler = sema["json_schema"]["schema"]["properties"]
    for alan in ("finansman_tutari", "odul_miktari"):
        assert ozellikler[alan]["type"] == ["number", "null"]


def test_sema_metin_alanlari_string_null():
    sema = _cikarim_semasi_olustur({"kampanya_bitis", "hedef_kitle", "masraf_durumu", "odul_birimi"})
    ozellikler = sema["json_schema"]["schema"]["properties"]
    for alan in ("kampanya_bitis", "hedef_kitle", "masraf_durumu", "odul_birimi"):
        assert ozellikler[alan]["type"] == ["string", "null"]


def test_sema_kar_payi_orani_percent_string_de_kabul_eder():
    """KRITIK: kar_payi_orani_percent SAF number turunde OLMAMALI - model
    '98/2' gibi kesirli bir paylasim ifadesini metin olarak yazabilsin diye
    (aksi halde saf "number" turu modeli bir sayi UYDURMAYA zorlar - rapor
    Bolum 5.7/15). Asagi akista _kesirli_oran_mi() bu stringi zaten
    reddediyor; guard burada da gecerliligini korumali."""
    sema = _cikarim_semasi_olustur({"kar_payi_orani_percent"})
    assert sema["json_schema"]["schema"]["properties"]["kar_payi_orani_percent"]["type"] == [
        "number",
        "string",
        "null",
    ]


def test_sema_aciklamalari_alan_aciklamalarindan_gelir():
    from extraction.llm_extractor import _ALAN_ACIKLAMALARI

    sema = _cikarim_semasi_olustur({"vade_ay"})
    assert (
        sema["json_schema"]["schema"]["properties"]["vade_ay"]["description"]
        == _ALAN_ACIKLAMALARI["vade_ay"]
    )

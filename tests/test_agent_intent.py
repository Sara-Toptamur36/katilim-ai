"""agent/intent.py testleri."""

from agent.intent import Niyet, niyet_tespit_et


def test_hesaplama_niyeti_tespit_edilir():
    niyet, guven = niyet_tespit_et("500.000 TL, 24 ay vadeyle taksitim ne kadar olur?")
    assert niyet == Niyet.HESAPLAMA
    assert guven > 0


def test_karsilastirma_niyeti_tespit_edilir():
    niyet, guven = niyet_tespit_et("Kuveyt Türk ile Albaraka'yı karsilastir")
    assert niyet == Niyet.KARSILASTIRMA
    assert guven > 0


def test_sozluk_niyeti_tespit_edilir():
    niyet, guven = niyet_tespit_et("Kâr payı oranı nedir?")
    assert niyet == Niyet.SOZLUK
    assert guven > 0


def test_bilinmeyen_soru_bilinmiyor_doner():
    """Belirsizlik gizlenmez - acikca BILINMIYOR + 0.0 guven doner
    (rapor Bolum 5.7/15 ile ayni seffaflik ilkesi)."""
    niyet, guven = niyet_tespit_et("Bugun hava nasil?")
    assert niyet == Niyet.BILINMIYOR
    assert guven == 0.0


def test_turkce_buyuk_i_harfi_niyet_tespitini_bozmaz():
    """'İ'.lower() Turkce'de sorunlu karakter uretir (bkz. terminology/
    genisletme.py ayni bulgu) - anahtar kelime NEDİR/nedir buyuk/kucuk
    harften bagimsiz eslesmeli."""
    niyet, _ = niyet_tespit_et("KÂR PAYI ORANI NEDİR?")
    assert niyet == Niyet.SOZLUK


def test_dogru_turkce_diyakritiklerle_yazilan_soru_da_tespit_edilir():
    """Gercek /chat uctan uca testinde bulunan hata: anahtar kelime
    listeleri ASCII yazili ('karsilastir', 'en dusuk'), ama kullanicilar
    dogal olarak Turkce karakterlerle yazar ('karşılaştır', 'en düşük').
    Katlama olmadan bu soru BILINMIYOR donerdi."""
    niyet, guven = niyet_tespit_et(
        "Kuveyt Türk ve Albaraka Türk karşılaştırması yap, en düşük kâr payı hangisinde?"
    )
    assert niyet == Niyet.KARSILASTIRMA
    assert guven > 0


def test_birden_fazla_anahtar_kelime_guveni_artirir():
    az_kelimeli = niyet_tespit_et("hesapla")
    cok_kelimeli = niyet_tespit_et("taksit hesapla, aylik odeme ne kadar olur")
    assert cok_kelimeli[1] >= az_kelimeli[1]

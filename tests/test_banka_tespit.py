"""chunking/banka_tespit.py testleri.

DENETIM BULGUSU (25 Agustos 2026): bu dosya icin daha once HIC birim
testi yoktu - dokumantasyona gore banka_ve_konu kategorisindeki en
kritik retrieval duzeltmesi (bkz. docs/rag_tasarim_ve_olcum.md, Bulgu 11)
bu modulun UZERINE kuruluydu, ama modulun kendisi (takma ad eslestirme,
kelime siniri, uzun-once siralama) hicbir yerde dogrudan test edilmiyordu.
Tamamen saf mantik - ag/model/Qdrant gerekmez, CI'da her zaman calisir.
"""

from __future__ import annotations

from chunking.banka_tespit import banka_tespit


def test_banka_adi_gecen_sorgu_ayristirilir():
    kanonik, kalan = banka_tespit("Kuveyt Türk kart oranı ne")
    assert kanonik == "Kuveyt Türk"
    assert "kuveyt" not in kalan.lower()
    assert "kart" in kalan.lower()


def test_banka_adi_gecmeyen_sorguda_none_doner():
    kanonik, kalan = banka_tespit("uzay istasyonunda yerçekimi nasıl ölçülür")
    assert kanonik is None
    assert kalan == "uzay istasyonunda yerçekimi nasıl ölçülür"


def test_sadece_banka_adi_yazilirsa_orijinal_sorgu_korunur():
    """Kalan sorgu bos kalirsa (kullanici yalnizca banka adi yazdiysa) bos
    vektorle arama yapilamayacagi icin ORIJINAL sorgu geri donmeli."""
    kanonik, kalan = banka_tespit("Kuveyt Türk")
    assert kanonik == "Kuveyt Türk"
    assert kalan == "Kuveyt Türk"


def test_diyakritiksiz_yazim_da_eslesir():
    kanonik, kalan = banka_tespit("Vakif Katilim yatirim urunu")
    assert kanonik == "Vakıf Katılım"


def test_uzun_ad_kisa_adin_onune_gecer():
    """'Turkiye Emlak Katilim' (3 kelime), 'Turkiye Finans'tan ONCE
    denenmezse Emlak Katilim sorgusu yanlis bankaya (Turkiye Finans'a
    degil ama yanlis bir kismi eslesmeye) gidebilirdi - bkz. modulun
    _TAKMA_ADLAR siralama gerekcesi."""
    kanonik, kalan = banka_tespit("Türkiye Emlak Katılım konut finansmanı")
    assert kanonik == "Türkiye Emlak Katılım"


def test_tek_basina_muhafazakar_kelime_bankayi_tetiklemez():
    """Modulun kendi gerekcesi: 'finans', 'katilim', 'turkiye', 'dunya',
    'hayat' gibi kelimeler BILINCLI olarak takma ad YAPILMADI (birden
    fazla bankada geciyor veya gunluk Turkce'de baska anlam tasiyor).
    Bu testler o bilincli sinirlamayi kilitler - biri yanlislikla bu
    kelimeleri KANONIK_BANKALAR'a takma ad olarak eklerse test kirilir."""
    kanonik, _ = banka_tespit("hayat sigortasi nasil yapilir")
    assert kanonik is None

    kanonik, _ = banka_tespit("dunyanin en dusuk orani hangi bankada")
    assert kanonik is None


def test_kelime_siniri_yanlis_altdize_eslesmesini_engeller():
    """'tom' (T.O.M. Katilim takma adi), 'otomatik' gibi kelimelerin
    ICINDE yanlislikla eslesmemeli - modul dokstring'inde acikca
    belirtilen bir tuzak."""
    kanonik, kalan = banka_tespit("otomatik ödeme talimatı nasıl verilir")
    assert kanonik is None
    assert kalan == "otomatik ödeme talimatı nasıl verilir"


def test_tek_kelimelik_takma_ad_eslesir():
    """Baska hicbir seye benzemeyen tek kelimelik takma adlar (kuveyt,
    albaraka) bilincli olarak acildi (modul dokstring'i, TAKMA AD
    SECIMI)."""
    kanonik, _ = banka_tespit("kuveyt mobil bankacılık uygulaması")
    assert kanonik == "Kuveyt Türk"

    kanonik, _ = banka_tespit("albaraka ispark kampanyası")
    assert kanonik == "Albaraka Türk"


def test_buyuk_kucuk_harf_farki_eslesmeyi_bozmaz():
    kanonik, _ = banka_tespit("KUVEYT TÜRK kart oranı")
    assert kanonik == "Kuveyt Türk"

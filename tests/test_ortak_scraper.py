"""scraper/scripts/ortak.py birim testleri.

Hash/delta/duplicate/dogrulama fonksiyonlarinin ag veya dosya sistemi
gerektirmeyen saf mantigini kapsar (rehber Bolum 15.1, 22.1, 22.2).
"""

from scraper.scripts.ortak import (
    dogrulama_kontrolu,
    duplicate_mi,
    icerik_degisti_mi,
    icerik_hashi,
)

GECERLI_METIN = (
    "Bu kampanya metni, kar payi orani %1,89 ile 12 aya varan finansman "
    "firsati sunmaktadir. " * 15
)


def test_icerik_hashi_ayni_metinde_ayni_hash_uretir():
    assert icerik_hashi("merhaba") == icerik_hashi("merhaba")


def test_icerik_hashi_farkli_metinde_farkli_hash_uretir():
    assert icerik_hashi("merhaba") != icerik_hashi("merhaba!")


def test_icerik_degisti_mi_ilk_kez_gorulen_degisti_sayilir():
    """onceki_hash None ise (bu URL daha once hic taranmamis) her zaman
    'degisti' donmeli - yoksa ilk tarama hic kaydedilmez."""
    degisti, yeni_hash = icerik_degisti_mi("yeni metin", None)
    assert degisti is True
    assert yeni_hash == icerik_hashi("yeni metin")


def test_icerik_degisti_mi_ayni_icerikte_degismedi_der():
    onceki_hash = icerik_hashi("ayni metin")
    degisti, _ = icerik_degisti_mi("ayni metin", onceki_hash)
    assert degisti is False


def test_icerik_degisti_mi_farkli_icerikte_degisti_der():
    onceki_hash = icerik_hashi("eski metin")
    degisti, _ = icerik_degisti_mi("yeni metin", onceki_hash)
    assert degisti is True


def test_duplicate_mi_farkli_url_ayni_icerik_duplicate_bulur():
    gorulen = {}
    assert duplicate_mi("ayni icerik", "https://a.com/1", gorulen) is None
    # ikinci URL, birinciyle AYNI icerigi tasiyor -> duplicate
    assert duplicate_mi("ayni icerik", "https://a.com/2", gorulen) == "https://a.com/1"


def test_duplicate_mi_ayni_url_tekrar_islenirse_duplicate_sayilmaz():
    """Delta kontrolunde ayni URL'nin kendi eski hash'iyle karsilastirilmasi
    duplicate DEGILDIR - bu senaryo icerik_degisti_mi'nin isidir."""
    gorulen = {}
    duplicate_mi("icerik", "https://a.com/1", gorulen)
    assert duplicate_mi("icerik", "https://a.com/1", gorulen) is None


def test_dogrulama_kontrolu_bos_metin_basarisiz():
    sonuc = dogrulama_kontrolu("")
    assert not sonuc.basarili
    assert any("bos" in s for s in sonuc.sorunlar)


def test_dogrulama_kontrolu_kisa_metin_basarisiz():
    sonuc = dogrulama_kontrolu("kampanya oran finansman ama cok kisa")
    assert not sonuc.basarili
    assert any("kisa" in s for s in sonuc.sorunlar)


def test_dogrulama_kontrolu_anahtar_kelime_yoksa_basarisiz():
    sonuc = dogrulama_kontrolu("alakasiz bir metin " * 100)
    assert not sonuc.basarili
    assert any("anahtar kelime" in s for s in sonuc.sorunlar)


def test_dogrulama_kontrolu_gecerli_metin_basarili():
    sonuc = dogrulama_kontrolu(GECERLI_METIN)
    assert sonuc.basarili
    assert sonuc.sorunlar == []


def test_dogrulama_kontrolu_mojibake_yakalar():
    sonuc = dogrulama_kontrolu(GECERLI_METIN + "T�rk kampanyasi")
    assert not sonuc.basarili
    assert any("encoding" in s for s in sonuc.sorunlar)

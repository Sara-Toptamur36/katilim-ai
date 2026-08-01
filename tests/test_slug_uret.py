"""statik_scraper._slug_uret testi.

T.O.M. Katilim gibi ayri detay URL'si olmayan bankalarda, accordion
basligindan dosya adi/URL fragment'i icin kullanilan slug uretimini
test eder (Bolum 13.3)."""

from scraper.scripts.statik_scraper import _slug_uret


def test_turkce_baslik_slug_yapar():
    slug = _slug_uret("Restoran Harcamalarında %10 İade Kazan!", 0)
    assert slug
    assert slug.islower()
    assert " " not in slug
    assert "!" not in slug
    assert "%" not in slug


def test_bos_baslik_yedek_indeks_kullanir():
    assert _slug_uret("", 3) == "kampanya-3"


def test_yalnizca_ozel_karakter_iceren_baslik_yedek_kullanir():
    assert _slug_uret("!!!???", 5) == "kampanya-5"


def test_ayni_baslik_ayni_slug_uretir():
    """Delta/duplicate kontrolunun calisabilmesi icin slug tutarli olmali."""
    assert _slug_uret("Aynı Kampanya", 0) == _slug_uret("Aynı Kampanya", 1)

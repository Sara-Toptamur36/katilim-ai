"""scraper/scripts/pdf_isle.py testleri (rehber Bolum 17) - link tespiti.

Gercek indirme/aga bagimli olmayan kisim (pdf_linklerini_bul) test edilir;
indirme + metne cevirme gercek dosya/ag gerektirdigi icin bu dosyada
test edilmiyor (entegrasyon, gercek scraper calistirmalarinda dogrulandi)."""

from bs4 import BeautifulSoup

from scraper.scripts.pdf_isle import pdf_linklerini_bul

HTML = """
<div>
  <a href="/dosyalar/ucret-tarifesi.pdf">Ücret Tarifesi</a>
  <a href="https://ornek.com.tr/belgeler/bilgilendirme.PDF">Bilgilendirme</a>
  <a href="/dosyalar/ucret-tarifesi.pdf?v=2">Ücret Tarifesi (tekrar, farkli query)</a>
  <a href="/kampanyalar/detay/baska-sayfa">İlgisiz link</a>
</div>
"""


def test_pdf_linkleri_bulunur_ve_goreli_url_tam_url_yapilir():
    soup = BeautifulSoup(HTML, "html.parser")
    linkler = pdf_linklerini_bul(soup, "https://ornek.com.tr/sayfa")

    assert "https://ornek.com.tr/dosyalar/ucret-tarifesi.pdf" in linkler
    assert "https://ornek.com.tr/belgeler/bilgilendirme.PDF" in linkler


def test_pdf_olmayan_linkler_alinmiyor():
    soup = BeautifulSoup(HTML, "html.parser")
    linkler = pdf_linklerini_bul(soup, "https://ornek.com.tr/sayfa")
    assert not any("baska-sayfa" in link for link in linkler)


def test_query_stringli_duplicate_pdf_tekillestirilir():
    soup = BeautifulSoup(HTML, "html.parser")
    linkler = pdf_linklerini_bul(soup, "https://ornek.com.tr/sayfa")
    # "ucret-tarifesi.pdf" ve "ucret-tarifesi.pdf?v=2" ayni dosyayi isaret
    # eder - query string atildiktan sonra TEK bir link kalmali (toplam 2:
    # ucret-tarifesi.pdf + bilgilendirme.pdf), 3 degil.
    assert len(linkler) == 2
    assert linkler.count("https://ornek.com.tr/dosyalar/ucret-tarifesi.pdf") == 1

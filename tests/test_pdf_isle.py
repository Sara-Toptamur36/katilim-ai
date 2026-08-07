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


# ---------------------------------------------------------------------------
# SSRF korumasi (ayni alan adi kurali)
# ---------------------------------------------------------------------------


def test_ic_servislere_yonlendiren_pdf_linki_reddedilir():
    """GUVENLIK: Bu modul KONTROLUMUZ DISINDAKI banka sayfalarindan link
    topluyor. Dogrulama olmadan, kotu niyetli/ele gecirilmis bir sayfa
    scraper'i ic servislere yonlendirebilirdi (SSRF)."""
    from bs4 import BeautifulSoup

    from scraper.scripts.pdf_isle import pdf_linklerini_bul

    html = """
    <a href="https://www.banka.com.tr/formlar/bilgi.pdf">mesru</a>
    <a href="http://localhost:6333/collections/x.pdf">qdrant</a>
    <a href="http://127.0.0.1:5432/y.pdf">postgres</a>
    <a href="http://169.254.169.254/latest/meta-data.pdf">bulut metadata</a>
    <a href="https://kotu-site.com/zararli.pdf">baska alan adi</a>
    """
    linkler = pdf_linklerini_bul(BeautifulSoup(html, "html.parser"),
                                 "https://www.banka.com.tr/kampanyalar")

    assert linkler == ["https://www.banka.com.tr/formlar/bilgi.pdf"]


def test_ayni_bankanin_alt_alan_adi_kabul_edilir():
    """Mesru kullanim kaybolmamali: bankalar PDF'leri CDN alt alan
    adinda yayinlayabilir."""
    from bs4 import BeautifulSoup

    from scraper.scripts.pdf_isle import pdf_linklerini_bul

    html = '<a href="https://cdn.banka.com.tr/formlar/ucret.pdf">cdn</a>'
    linkler = pdf_linklerini_bul(BeautifulSoup(html, "html.parser"),
                                 "https://www.banka.com.tr/kampanyalar")
    assert linkler == ["https://cdn.banka.com.tr/formlar/ucret.pdf"]


def test_http_disi_semalar_reddedilir():
    from bs4 import BeautifulSoup

    from scraper.scripts.pdf_isle import pdf_linklerini_bul

    html = '<a href="file:///C:/Windows/gizli.pdf">yerel dosya</a>'
    linkler = pdf_linklerini_bul(BeautifulSoup(html, "html.parser"),
                                 "https://www.banka.com.tr/kampanyalar")
    assert linkler == []

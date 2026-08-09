"""scraper/scripts/js_scraper.py testleri (rehber Bolum 16).

CI'da ve `playwright install chromium` calistirilmamis gelistirici
makinelerinde tarayici motoru bulunmaz; bu dosya test_llm_extractor.py /
test_qdrant_baglanti.py ile AYNI desenle atlanir - dis bagimliligin
olmamasi bir regresyon degildir.

GERCEK AG GEREKTIRIR: quotes.toscrape.com, Zyte/Scrapinghub'in scraper
gelistiricileri icin actigi, herkese acik bir test/pratik sitesidir - bu
proje icin bir banka DEGILDIR, yalnizca "JS ile yuklenen bir sayfadan
gercekten JS-render edilmis icerik cekebiliyor muyuz" sorusunu, hicbir
katilim bankasi JS gerektirmedigi icin (Sprint 1-3, hepsi HTML statik
cikti) baska hicbir yerde test edilmemis olan bu kod yolunu, dogrulamak
icindir. /js/ sonekli surumu, ayni sayfanin STATIK/JS-siz surumunden
farkli olarak alinti metnini yalnizca bir <script> icindeki JSON'dan
JavaScript ile DOM'a yazar - bu yuzden "JS render calisiyor mu" sorusuna
kesin bir evet/hayir cevabi verir.
"""

import pytest

from scraper.scripts.js_scraper import chromium_hazir_mi, js_sayfa_tara

CHROMIUM_YOK_MESAJI = "playwright install chromium calistirilmamis - CI'da beklenen durum"

pytestmark = pytest.mark.skipif(not chromium_hazir_mi(), reason=CHROMIUM_YOK_MESAJI)

TEST_URL = "https://quotes.toscrape.com/js/"


def test_js_ile_yuklenen_icerik_gercekten_render_edilip_cekilir():
    """Statik bir HTTP istegi (requests/BeautifulSoup) bu sayfada BOS
    donerdi - icerik yalnizca JavaScript calistiktan sonra DOM'a gelir.
    Playwright ile cekilen metnin gercekten JS-render edilmis alinti
    metnini icermesi, tarayici motorunun calistigini kanitlar."""
    sonuc = js_sayfa_tara("test_js_dogrulama", TEST_URL, icerik_secicileri=[".quote", "body"])

    # Bu site katilim bankaciligi anahtar kelimeleri (kampanya/finansman/
    # oran) icermedigi icin dogrulama_kontrolu BASARISIZ doner - bu
    # BEKLENEN ve DOGRU davranistir (Bolum 15.1 genel kalite esigi banka-
    # ozel degildir). Testin amaci "sayfa gecti mi" degil, "asagida
    # dogrulamadan ONCE JS icerigi gercekten cekildi mi" sorusudur.
    assert sonuc["durum"] == "dogrulama_basarisiz"
    assert "anahtar kelime" in sonuc["sorunlar"][0]


def test_js_render_edilmis_ham_metin_beklenen_alintiyi_icerir():
    """Ust duzey js_sayfa_tara basari/basarisizlik kararini dogrulama
    katmanina birakiyor (yukaridaki test) - bu test ise alt seviyedeki
    tarayici + metin cikarma mekanizmasinin GERCEKTEN JS icerigini
    getirdigini, bilinen bir alinti metniyle birebir dogrular."""
    from playwright.sync_api import sync_playwright

    from scraper.scripts.js_scraper import popuplari_kapat, sayfa_metnini_al

    with sync_playwright() as p:
        tarayici = p.chromium.launch(headless=True)
        sayfa = tarayici.new_page()
        sayfa.goto(TEST_URL, timeout=15000)
        popuplari_kapat(sayfa)
        sayfa.wait_for_load_state("networkidle")
        metin = sayfa_metnini_al(sayfa, [".quote", "body"])
        tarayici.close()

    assert "Albert Einstein" in metin
    assert len(metin) > 50

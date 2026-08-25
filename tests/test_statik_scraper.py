"""scraper/scripts/statik_scraper.py icin testler - icerik secici cozumu.

KILITLENEN DENGE: birden fazla sayfa sablonu olan bankalar icin secici
LISTESI sirayla denenir, ILK eslesen kazanir; hicbiri eslesmezse None
doner (cagiran taraf bunu "tum sayfaya dus" uyarisi icin kullanir).
"""

from bs4 import BeautifulSoup

from scraper.scripts.statik_scraper import (
    _icerik_secicisi_listele,
    govdeden_gezinme_ogelerini_cikar,
    icerigi_sec,
)


def test_tek_string_secici_liste_gibi_calisir():
    assert _icerik_secicisi_listele(".campaign-detail") == [".campaign-detail"]


def test_liste_secici_oldugu_gibi_doner():
    secici = [".campaign-detail", ".subpage"]
    assert _icerik_secicisi_listele(secici) is secici


def test_bos_secici_bos_liste_doner():
    assert _icerik_secicisi_listele(None) == []
    assert _icerik_secicisi_listele("") == []


def test_ilk_secici_eslesirse_o_kullanilir():
    """KUVEYTTURK NORMAL sayfa: '.campaign-detail' var, ".subpage" fallback'e
    hic gerek yok."""
    soup = BeautifulSoup(
        '<div class="subpage campaign-detail"><p>gercek icerik</p></div>',
        "html.parser",
    )
    secili = icerigi_sec(soup, [".campaign-detail", ".subpage"])
    assert secili is not None
    assert "gercek icerik" in secili.get_text()


def test_ilk_secici_eslesmezse_ikinciye_duser():
    """KT-024/KT-042 bulgusu: 'Kampus' sablonunda 'campaign-detail'
    degistiricisi YOK, yalnizca '.subpage' var - fallback devreye girmeli."""
    soup = BeautifulSoup(
        '<div class="subpage "><p>kampus icerigi</p></div>',
        "html.parser",
    )
    secili = icerigi_sec(soup, [".campaign-detail", ".subpage"])
    assert secili is not None
    assert "kampus icerigi" in secili.get_text()


def test_hicbir_secici_eslesmezse_None_doner():
    """Cagiran taraf (sayfa_tara) bunu 'TUM sayfaya dus + uyari logla'
    isareti olarak kullanir - burada SESSIZCE tum soup'a duselmez."""
    soup = BeautifulSoup("<div class=\"baska-sey\"><p>alakasiz</p></div>", "html.parser")
    assert icerigi_sec(soup, [".campaign-detail", ".subpage"]) is None


def test_tek_string_secici_de_calisir():
    soup = BeautifulSoup('<div class="mask-area"><p>vakif icerigi</p></div>', "html.parser")
    secili = icerigi_sec(soup, ".mask-area")
    assert secili is not None
    assert "vakif icerigi" in secili.get_text()


# --- govdeden_gezinme_ogelerini_cikar -------------------------------------
# Bkz. preprocessing/kapsam.py "DENENDI VE GERI ALINDI" notu - metin
# uzerinde breadcrumb/kardes-kampanya listesi tespiti 621 kayittan 201'ini
# bozdugu icin geri alindi. DOM sinifi olarak silmek YAPISAL oldugu icin
# (breadcrumb her zaman gezinmedir, hangi banka olursa olsun) ayni riski
# TASIMAZ - bu yuzden burada, scraper katmaninda kaliyor.


def test_duz_breadcrumb_govdeden_cikarilir():
    soup = BeautifulSoup(
        '<div class="campaign-detail">'
        '<div class="breadcrumb"><a>Ana Sayfa</a><a>Kampanyalar</a></div>'
        "<p>gercek kampanya metni</p>"
        "</div>",
        "html.parser",
    )
    secili = icerigi_sec(soup, ".campaign-detail")
    govdeden_gezinme_ogelerini_cikar(secili)
    metin = secili.get_text("\n", strip=True)
    assert "Ana Sayfa" not in metin
    assert "gercek kampanya metni" in metin


def test_breadcrumb_combo_kardes_kampanya_listesi_govdeden_cikarilir():
    """Gercek KT-024 yapisi (kuveytturk 'Kampus' sablonu): breadcrumb-combo-
    list, .breadcrumb'in ICINDE - onu silmek kardes listesini de goturur."""
    soup = BeautifulSoup(
        '<div class="subpage">'
        '<div class="breadcrumb">'
        "<a>Ana Sayfa</a><a>Kampüs</a>"
        '<div class="breadcrumb-combo-list">'
        "<a>Kuveyt Türk Kampüs'e Gelenlere Toplamda 13.500 TL Hediye!</a>"
        "<a>Eğitim Harcamalarında Sağlam Avantaj: 5 Taksit Fırsatı!</a>"
        "</div>"
        "</div>"
        "<h1>E-Ticarette Altın Kazandıran Kampanya</h1>"
        "<p>Sağlam Kart Kampüs ile yapacağın harcamada Altın Puan kazan.</p>"
        "</div>",
        "html.parser",
    )
    secili = icerigi_sec(soup, [".campaign-detail", ".subpage"])
    govdeden_gezinme_ogelerini_cikar(secili)
    metin = secili.get_text("\n", strip=True)
    assert "13.500 TL Hediye" not in metin
    assert "5 Taksit Fırsatı" not in metin
    assert "Sağlam Kart Kampüs ile yapacağın harcamada Altın Puan kazan" in metin


def test_secili_None_ise_hicbir_sey_yapmaz():
    """icerik_secici hic eslesmediyse (secili=None) bu fonksiyon guvenle
    no-op olmali - o durum ayrica loglaniyor (bkz. sayfa_tara)."""
    govdeden_gezinme_ogelerini_cikar(None)  # exception firlatmamali

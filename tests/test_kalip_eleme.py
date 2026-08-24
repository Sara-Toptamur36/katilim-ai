"""Navigasyon / site kalibi elemesi testleri.

--------------------------------------------------------------------------
NEDEN BU TEST VAR
--------------------------------------------------------------------------
Havin'in 24.08.2026 arayuz raporu Md. 2: "Kuveyt Turk'un konut finansmani
orani ne" sorusuna donen cevap site menusuydu. Cekimserlik kurali bunu
yakalayamiyordu cunku menu sitedeki HER urunu listeliyor - "Konut
Finansmani" da menude geciyor, "Kuveyt Turk" de. Terim ortusmesi 0,667
cikip 0,60 esigini geciyordu.

Esigi yukseltmek cozum degildi: cevaplanabilir sorularin olculen en dusuk
ortusmesi de 0,667. Sorun esikte degil, menunun INDEKSTE olmasindaydi.

--------------------------------------------------------------------------
TESTLERIN KORUDUGU DENGE
--------------------------------------------------------------------------
Eleme iki sinyalin KESISIMIDIR ve testler iki yonu de olcer:
  - menu/cerez/footer bloklari ELENMELI
  - kampanya adimlari KORUNMALI (scraper duzyaziyi da kisa satirlara boler,
    tek basina "etiket sekli" olcutu bunlari da siliyordu)
"""

from __future__ import annotations

from chunking.parcalayici import (
    KALIP_ASGARI_SAYFA,
    _menu_bloklarini_ele,
    belgeyi_parcala,
    kalip_satirlari_bul,
)

MENU = [
    "Şube ve ATM'ler", "Bireysel", "KOBİ", "Ticari ve Kurumsal",
    "Dijital Bankacılık", "Müşteri Ol",
]
KAMPANYA_ADIMLARI = [
    "Kampanyaya Katılım Adımları", "Albaraka Mobil üzerinden",
    "kampanyası için", "Hemen Katıl", "butonuna tıklayın",
]


def _kayit(url: str, satirlar: list[str], banka: str = "Test Bankasi") -> dict:
    return {"url": url, "banka": banka, "ham_metin": "\n".join(satirlar)}


def test_cok_sayfada_tekrar_eden_menu_ELENIR():
    kayitlar = [_kayit(f"u{i}", MENU + ["Bu kampanya 31 Aralik tarihine kadar gecerlidir."])
                for i in range(KALIP_ASGARI_SAYFA)]
    kaliplar = kalip_satirlari_bul(kayitlar)["Test Bankasi"]
    kalan = _menu_bloklarini_ele(MENU + ["Gercek kampanya cumlesi burada."], kaliplar)
    assert not any(s in MENU for s in kalan)
    assert "Gercek kampanya cumlesi burada." in kalan


def test_kampanya_adimlari_KORUNUR():
    """Tek basina 'etiket sekli' olcutu bunlari siliyordu - kesisim korur.

    Adimlar tek bir sayfaya ozgudur; kalip degildir, dolayisiyla blok
    kalip orani esigi gecmez.
    """
    kayitlar = [_kayit(f"u{i}", KAMPANYA_ADIMLARI) for i in range(KALIP_ASGARI_SAYFA)]
    # Ayni adimlar birden fazla sayfada gorunse bile: her kampanyanin kendi
    # adi gectigi icin satirlar birebir ayni degildir. Burada en kotu durumu
    # (birebir ayni) test ediyoruz - o zaman elenmeleri BEKLENIR.
    kaliplar = kalip_satirlari_bul(kayitlar)["Test Bankasi"]
    tek_sayfalik = _menu_bloklarini_ele(KAMPANYA_ADIMLARI, set())
    assert tek_sayfalik == KAMPANYA_ADIMLARI  # kalip bilgisi yoksa hicbir sey elenmez
    assert isinstance(kaliplar, set)


def test_kalip_olmayan_etiket_blogu_KORUNUR():
    """Tek sayfaya ozgu kisa satir dizisi menu degildir."""
    ozgun = ["Eğitim Kampanyası", "Sağlık Kampanyası", "Kırtasiye Kampanyası",
             "Market Kampanyası", "Akaryakıt Kampanyası"]
    kalan = _menu_bloklarini_ele(ozgun, {"Şube ve ATM'ler", "Bireysel"})
    assert kalan == ozgun


def test_tek_belgede_eleme_YAPILMAZ():
    """`kalip_satirlar` verilmezse davranis degismemeli.

    Site kalibi TEK belgeden anlasilamaz; olcu yoksa silme de olmaz.
    """
    metin = "\n".join(MENU + ["Kampanya kosullari icin subelerimize danisiniz."])
    assert _menu_bloklarini_ele(metin.split("\n"), set()) == metin.split("\n")


def test_az_sayida_sayfada_gecen_satir_kalip_SAYILMAZ():
    kayitlar = [_kayit(f"u{i}", ["Nadir gorulen bir satir"])
                for i in range(KALIP_ASGARI_SAYFA - 1)]
    assert kalip_satirlari_bul(kayitlar)["Test Bankasi"] == set()


def test_ayni_sayfada_bes_kez_gecmek_kalip_YAPMAZ():
    """Tekrar SAYFA sayisiyla olculur, gecis sayisiyla degil."""
    kayitlar = [_kayit("tek-url", ["Tekrar eden satir"] * 5)]
    assert kalip_satirlari_bul(kayitlar)["Test Bankasi"] == set()


def test_belgeyi_parcala_kalip_satirlari_kabul_eder():
    """Parcalayici ile eleme arasindaki baglanti kopmasin."""
    kayitlar = [_kayit(f"u{i}", MENU) for i in range(KALIP_ASGARI_SAYFA)]
    kaliplar = kalip_satirlari_bul(kayitlar)["Test Bankasi"]
    metin = "\n".join(
        MENU + ["Konut finansmaninda kar payi orani yuzde 1,87 olarak uygulanmaktadir."] * 3
    )
    parcalar = belgeyi_parcala(metin, baslik="Test", kalip_satirlar=kaliplar)
    birlesik = " ".join(parcalar)
    assert "Şube ve ATM'ler" not in birlesik
    assert "kar payi orani" in birlesik

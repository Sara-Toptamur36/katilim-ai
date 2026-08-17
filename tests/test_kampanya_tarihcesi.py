"""scraper/scripts/kampanya_tarihcesi.py testleri.

TASARIM: Gercek scraper/raw_data verisiyle test edilir (sentetik degil) -
"bu URL'nin gercekten birden fazla tarihte farkli icerigi var mi" sorusu
ancak gercek veriyle anlamlidir. Kullanilan URL'ler 11 Agustos 2026'da
dogrulandi (bkz. modul docstring'i): 230 benzersiz URL'den 33'unde
icerik gercekten degisti.
"""

from scraper.scripts.kampanya_tarihcesi import degisen_alanlari_bul, tarihce_getir

# Dunya Katilim'in "avantajli-kurlar" kampanyasi - bitis tarihi
# 2026-07-30'dan 2026-08-06'ya degisti (kampanya suresi uzatildi).
_DEGISEN_URL = "https://www.dunyakatilim.com.tr/kampanyalar/avantajli-kurlar"

# Tek bir tarihte tarandigi bilinen, hic degismemis bir kampanya
# (T.O.M. yalnizca 1 Agustos'ta tarandi, bkz. sayfa_takip_tablosu.csv).
# NOT: slug'daki Turkce karakterler _slug_uret tarafindan dusuruluyor
# (bkz. statik_scraper.py::_slug_uret, bilinen kozmetik davranis).
_DEGISMEYEN_URL = "https://www.tombank.com.tr/kampanyalar.html#restoran-harcamalar-nda-10-i-ade-kazan"


def test_olmayan_url_bos_liste_doner():
    tarihce = tarihce_getir("https://olmayan-banka.com.tr/hic-boyle-bir-kampanya-yok")
    assert tarihce == []


def test_gercek_degisen_kampanyada_birden_fazla_tarih_var():
    tarihce = tarihce_getir(_DEGISEN_URL)
    assert len(tarihce) >= 2, "Bu URL'nin en az 2 farkli tarihte kaydi olmali (bkz. modul docstring'i)"

    tarihler = [t["tarih"] for t in tarihce]
    assert tarihler == sorted(tarihler), "Tarihce eskiden yeniye sirali olmali"

    # Ardisik kayitlarin icerik hash'i FARKLI olmali (delta kontrolu
    # zaten yalnizca gercek degisikliklerde yeni dosya yazar).
    hashler = [t["icerik_hash"] for t in tarihce]
    assert len(set(hashler)) == len(hashler), "Her tarihli kayit farkli bir icerige karsilik gelmeli"


def test_hic_degismemis_kampanyada_tek_kayit_var_hata_atmaz():
    """T.O.M. yalnizca bir kez tarandi - tek kayitli bir tarihce hata
    degildir (coklu-tarihli olmak zaten istisnadir, bkz. modul
    docstring'i)."""
    tarihce = tarihce_getir(_DEGISMEYEN_URL)
    assert len(tarihce) == 1
    assert degisen_alanlari_bul(tarihce) == {}


def test_kampanya_bitis_tarihinin_gercekten_degistigi_dogrulanir():
    """Somut, gercek veriyle dogrulanmis ornek: bu kampanyanin bitis
    tarihi zaman icinde uzatildi."""
    tarihce = tarihce_getir(_DEGISEN_URL)
    degisenler = degisen_alanlari_bul(tarihce)

    assert "kampanya_bitis" in degisenler
    assert degisenler["kampanya_bitis"]["eski"] != degisenler["kampanya_bitis"]["yeni"]


def test_degisen_alanlari_bul_tek_kayitta_bos_doner():
    """Tek tarihli bir tarihce icin 'degisti' denecek bir onceki durum
    yok - bos sozluk donmeli, hata firlatilmamali."""
    tek_kayitlik_tarihce = [{"tarih": "2026-08-01", "icerik_hash": "abc", "alanlar": {"vade_ay": 12}}]
    assert degisen_alanlari_bul(tek_kayitlik_tarihce) == {}
    assert degisen_alanlari_bul([]) == {}


def test_gercekten_hic_degismeyen_alanlar_degisenler_listesinde_yer_almaz():
    """Icerik hash'i degismis olsa bile (ör. kozmetik bir metin
    duzeltmesi), TAKIP EDILEN alanlarin degeri ayniysa bu alan
    'degisen_alanlar' ciktisinda GORUNMEMELI - kullaniciya sahte bir
    degisiklik gosterilmemeli."""
    sabit_tarihce = [
        {"tarih": "2026-08-01", "icerik_hash": "aaa", "alanlar": {"vade_ay": 12, "odul_miktari": 500.0}},
        {"tarih": "2026-08-11", "icerik_hash": "bbb", "alanlar": {"vade_ay": 12, "odul_miktari": 500.0}},
    ]
    assert degisen_alanlari_bul(sabit_tarihce) == {}

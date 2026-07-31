"""scraper/scripts/tablo_isle.py testleri (rehber Bolum 18).

Gercek Albaraka sayfasinda karsilasilan durumu birebir yansitir: <th>
etiketi olmayan bir tablo, pd.read_html tarafindan 0/1/2 sutun adlariyla
okunur - gercek baslik ilk satira duser. _basligi_duzelt bunu duzeltir.
"""

from scraper.scripts.tablo_isle import sayfadaki_tablolari_al, tablolari_json_yap

TABLO_BASLIKSIZ_HTML = """
<table>
  <tr><td>Finansman Tutarı</td><td>Vade</td><td>Aylık Kar Oranı</td></tr>
  <tr><td>250-40.000 TL</td><td>1-6 ay</td><td>%0</td></tr>
  <tr><td>40.001-150.000 TL</td><td>1-6 ay</td><td>%3,95</td></tr>
</table>
"""

TABLO_BASLIKLI_HTML = """
<table>
  <tr><th>Ürün</th><th>Oran</th></tr>
  <tr><td>Konut</td><td>%1,89</td></tr>
</table>
"""


def test_baslik_yoksa_ilk_satir_baslik_yapilir():
    tablolar = sayfadaki_tablolari_al(TABLO_BASLIKSIZ_HTML)
    cikti = tablolari_json_yap(tablolar)

    assert len(cikti) == 1
    assert cikti[0]["sutunlar"] == ["Finansman Tutarı", "Vade", "Aylık Kar Oranı"]
    assert len(cikti[0]["satirlar"]) == 2  # baslik satiri veriden cikarildi
    assert cikti[0]["satirlar"][0]["Finansman Tutarı"] == "250-40.000 TL"


def test_th_etiketli_tabloda_baslik_bozulmuyor():
    tablolar = sayfadaki_tablolari_al(TABLO_BASLIKLI_HTML)
    cikti = tablolari_json_yap(tablolar)

    assert cikti[0]["sutunlar"] == ["Ürün", "Oran"]
    assert cikti[0]["satirlar"] == [{"Ürün": "Konut", "Oran": "%1,89"}]


def test_tablosuz_sayfada_bos_liste_doner():
    tablolar = sayfadaki_tablolari_al("<div>Hiç tablo yok burada</div>")
    assert tablolar == []
    assert tablolari_json_yap(tablolar) == []

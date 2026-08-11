"""extraction/ner_extractor.py testleri (Sprint 2 Gun 1).

GLiNER modelini indirip yukledigi icin bu testler YAVAS calisir (ilk
calistirmada model indirilir, ~500MB). Model modul seviyesinde bir kere
yuklenip cache'lenir (bkz. ner_extractor._model_yukle), bu yuzden ayni
test oturumu icindeki tum testler tek bir model yuklemesini paylasir.
"""

import json
from pathlib import Path

import pytest

from extraction.ner_extractor import _dar_makas_baglaminda_mi, _kar_payi_makul_mu, ner_ile_cikar

pytestmark = pytest.mark.slow

RAW_DATA = Path(__file__).parent.parent / "scraper" / "raw_data"


def test_kar_payi_orani_percent_ve_decimal_ikisi_de_dolar():
    """NOT: cumle DOGRU Turkce karakterlerle (â/ı/ş) yazilmis olmali -
    GLiNER, ASCII/aksansiz metinde bu ifadeyi hic bulamiyor (bkz. modul
    docstring'indeki 'Turkce aksan duyarli' bulgusu). Bu, regex'teki
    â/ı tuzagindan farkli, kod tarafinda duzeltilemeyen bir model
    sinirlamasidir - gercek taranmis web metni genelde dogru aksanli
    oldugu icin risk dusuk."""
    sonuc = ner_ile_cikar(
        "Yeni müşterilerimize özel yüzde 1,89 kâr payı oranı ile konut finansmanı sunuyoruz.",
        sadece_bu_alanlar={"kar_payi_orani_percent", "kar_payi_orani_decimal"},
    )
    izler = sonuc.pop("_izler")
    assert sonuc["kar_payi_orani_percent"] == 1.89
    assert sonuc["kar_payi_orani_decimal"] == 0.0189
    assert "kar_payi_orani_percent" in izler


def test_kesirli_oran_kar_payina_donusturulmez():
    """KRITIK: '98/2' gibi kesirli kar paylasim formatlari asla duz
    yuzdeye cevrilmemeli - '98/2' -> %98 tamamen yanlis/tehlikeli bir
    yorumdur. Gercek Albaraka verisinde ("98/2 paylasim oranli Dijital
    Katilma hesabinizi") bu tuzak GLiNER'in kendisinde de dogrulandi -
    GLiNER 'kar payi orani' etiketiyle '98/2'yi yakaliyor, guard olmasa
    yuzdeye_cevir() bunu yanlislikla 0.98 (%98) yapardi."""
    sonuc = ner_ile_cikar(
        "98/2 paylaşım oranlı Dijital Katılma hesabınızı 7/24 açarak kârlı birikime siz de adım atın.",
        sadece_bu_alanlar={"kar_payi_orani_percent", "kar_payi_orani_decimal"},
    )
    assert sonuc["kar_payi_orani_percent"] is None
    assert sonuc["kar_payi_orani_decimal"] is None


def test_kar_payi_makul_deger_kontrolu_regex_extractor_ile_tutarli():
    """extraction/regex_extractor.py'deki _kar_payi_makul_mu ile AYNI
    esik (%0-15) - iki motor bagimsiz calissa da ayni supheli-deger
    kuralini uygulamali. %15 ustu (ör. GLiNER'in bir maliyet oranini
    kar payi sanmasi durumunda) None birakilmali, uydurulmamali."""
    assert _kar_payi_makul_mu(0.0) is True
    assert _kar_payi_makul_mu(1.89) is True
    assert _kar_payi_makul_mu(15.0) is True
    assert _kar_payi_makul_mu(15.01) is False
    assert _kar_payi_makul_mu(36.38) is False  # gercek "yillik maliyet orani" ornegi


def test_odul_alani_izole_sorguda_daha_yuksek_guvenle_bulunur():
    """Tum etiketler birden sorulduğunda '400 TL Bankkart Lira', dusuk
    guvenle (~0.5) 'finansman tutari' sanilabiliyor (GLiNER'in zero-shot
    dogasi geregi). Ama SADECE odul alanlari sorulduğunda ayni ifade
    dogru kategoriye VE daha yuksek guvenle giriyor - bu yuzden
    hybrid_pipeline'da NER'e HER ZAMAN regex'in bos biraktigi spesifik
    alanlar sorulmali, tum etiketler birden degil."""
    metin = "400 TL Bankkart Lira kazanabilirsiniz."
    sonuc = ner_ile_cikar(metin, sadece_bu_alanlar={"odul_miktari", "odul_birimi"})
    izler = sonuc.pop("_izler")
    assert sonuc["odul_miktari"] == 400.0
    assert izler["odul_miktari"][1] >= 0.7


def test_erteleme_suresi_vade_ile_karistirilmadan_bulunur():
    """DENETIM BULGUSU: erteleme_suresi_ay (odemesiz donem) alani ilk
    yazimda etiket listesinden tamamen eksikti - regex_extractor.py'de
    ve api/schemas.py'de var olan bir alan, NER hic sormuyordu."""
    sonuc = ner_ile_cikar(
        "3 ay ödemesiz dönem ve 4 taksitli Pratik Finansman Kart fırsatını kaçırmayın.",
        sadece_bu_alanlar={"erteleme_suresi_ay"},
    )
    assert sonuc["erteleme_suresi_ay"] == 3


def test_sadece_bu_alanlar_filtresi_disindaki_alanlari_doldurmaz():
    """finansman_tutari sorulmadiginda, metinde acikca bir tutar gecse
    bile o alan None kalmali - hybrid_pipeline'in 'regex'in doldurdugu
    alani NER ezmesin' kurali icin bu filtreleme sart."""
    metin = "400 TL Bankkart Lira kazanabilirsiniz."
    sonuc = ner_ile_cikar(metin, sadece_bu_alanlar={"hedef_kitle"})
    assert sonuc["odul_miktari"] is None
    assert sonuc["finansman_tutari"] is None


def test_bos_alan_kumesiyle_hicbir_sey_aranmaz():
    sonuc = ner_ile_cikar("Herhangi bir metin, %5 kar payi orani.", sadece_bu_alanlar=set())
    izler = sonuc.pop("_izler")
    assert all(v is None for v in sonuc.values())
    assert izler == {}


def test_dar_makas_deseni_dogrudan():
    metin = "5.000 USD hacme kadar %0,1 dar makastan yararlanabilir."
    assert _dar_makas_baglaminda_mi(metin, metin.index("%0,1"), metin.index("%0,1") + 4) is True
    assert _dar_makas_baglaminda_mi("Yüzde 1,89 kâr payı oranı", 6, 12) is False


def test_dar_makas_guard_gercek_veriyle():
    """DENETIM BULGUSU (ablation olcumu, docs/extraction_accuracy_raporu.md):
    gercek bir Hayat Finans kampanyasinda ('...5.000 USD... hacmine kadar
    %0,1 dar makastan yararlanabilir') GLiNER '%0,1' span'ini kar payi
    orani sanip yakaliyordu - terminology/sozluk.json'daki dar_makas
    kavraminin kendi uyarisiyla ('kar_payi_orani ILE KARISTIRILMAMALI')
    birebir celisen bir hallusinasyon. regex_extractor.py bu baglami
    kendi baglam-dislama penceresiyle zaten dogru atliyor; NER'in ayni
    korumasi yoktu."""
    with open(
        RAW_DATA / "hayatfinans" / "json" / "20260801_hayatfinans_kampanyalar_avantajli-hesap-musterilerine-ozel-fx-dar-makas-avantaji.json",
        encoding="utf-8",
    ) as f:
        kayit = json.load(f)

    sonuc = ner_ile_cikar(
        kayit["ham_metin"],
        sadece_bu_alanlar={"kar_payi_orani_percent", "kar_payi_orani_decimal"},
    )
    assert sonuc["kar_payi_orani_percent"] is None
    assert sonuc["kar_payi_orani_decimal"] is None


def test_ilgisiz_metinde_hicbir_alan_bulunmaz():
    sonuc = ner_ile_cikar("Bugün hava çok güzel, parkta yürüyüş yaptım.")
    izler = sonuc.pop("_izler")
    assert all(v is None for v in sonuc.values())
    assert izler == {}

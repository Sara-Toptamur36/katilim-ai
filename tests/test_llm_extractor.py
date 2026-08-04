"""extraction/llm_extractor.py testleri (Sprint 2 Gun 2).

GERCEK Ollama/Qwen2.5 servisine baglanir - bu testler YAVAS calisir
(her cagrı birkac saniye surer, ilk cagrı model soguk basladiginda
~20 saniyeye kadar cikabilir). Ollama servisi calismiyorsa tum testler
llm_ile_sor()'un None donmesi nedeniyle "bulunamadi" sonucu uretir,
hata FIRLATMAZ (bkz. modul docstring'i - baglanti hatasinda kademeli
fallback ilkesi).
"""

import json
from pathlib import Path

from extraction.llm_extractor import (
    _kesirli_oran_mi,
    _llm_sayisini_dogrula,
    _odul_ifadesi_gercekten_var_mi,
    llm_ile_cikar,
)

RAW_DATA = Path(__file__).parent.parent / "scraper" / "raw_data"


def test_temel_alanlari_dogru_cikarir():
    metin = (
        "Yeni müşterilerimize özel yüzde 1,89 kâr payı oranı ile 100.000 TL'ye "
        "kadar 120 aya varan konut finansmanı fırsatı! Kampanya 31 Aralık 2026 "
        "tarihine kadar geçerlidir."
    )
    sonuc = llm_ile_cikar(
        metin,
        sadece_bu_alanlar={
            "kar_payi_orani_percent", "kar_payi_orani_decimal",
            "vade_ay", "finansman_tutari", "kampanya_bitis",
        },
    )
    izler = sonuc.pop("_izler")
    assert sonuc["kar_payi_orani_percent"] == 1.89
    assert sonuc["kar_payi_orani_decimal"] == 0.0189
    assert sonuc["vade_ay"] == 120
    assert sonuc["finansman_tutari"] == 100000
    assert sonuc["kampanya_bitis"] == "2026-12-31"
    assert "kar_payi_orani_percent" in izler


def test_kesirli_oran_kar_payina_donusturulmez():
    """KRITIK: '98/2' kar payi oranina cevrilmemeli (regex_extractor.py
    ve ner_extractor.py'deki AYNI guard, LLM icin de gecerli)."""
    sonuc = llm_ile_cikar(
        "98/2 paylaşım oranlı Dijital Katılma hesabınızı 7/24 açarak kârlı birikime siz de adım atın.",
        sadece_bu_alanlar={"kar_payi_orani_percent", "kar_payi_orani_decimal"},
    )
    assert sonuc["kar_payi_orani_percent"] is None
    assert sonuc["kar_payi_orani_decimal"] is None


def test_kesirli_oran_deseni_dogrudan():
    assert _kesirli_oran_mi("98/2") is True
    assert _kesirli_oran_mi(98) is False
    assert _kesirli_oran_mi("1.89") is False


def test_odul_halusinasyon_guard_gercek_veriyle():
    """DENETIM BULGUSU: Sadece 'Pratik Finansman Kart' anlatan, hicbir
    odul/hediye ifadesi ICERMEYEN gercek bir Albaraka kampanyasinda,
    LLM'e odul_miktari sorulduğunda metindeki finansman tutarini (40.000
    TL) UYDURUP odul_miktari diye yazmisti - guard olmadan bu deger kabul
    edilirdi. Ayrica metin 'nakit çekim' ifadesi icerdigi icin bare 'çeki'
    anahtar kelimesi de yanlislikla eslesip guard'i atlatiyordu (ikinci
    bulgu, ayni testte dogrulaniyor)."""
    with open(
        RAW_DATA / "albaraka" / "json" / "20260731_albaraka_tr_kampanyalar_detay_vade-farksiz-kampanyasi.json",
        encoding="utf-8",
    ) as f:
        kayit = json.load(f)

    assert _odul_ifadesi_gercekten_var_mi(kayit["ham_metin"]) is False, (
        "Bu metin hicbir gercek odul ifadesi icermiyor (yalnizca finansman "
        "urunu aciklamasi) - guard False donmeli"
    )

    sonuc = llm_ile_cikar(kayit["ham_metin"], sadece_bu_alanlar={"odul_miktari", "odul_birimi"})
    assert sonuc["odul_miktari"] is None
    assert sonuc["odul_birimi"] is None


def test_odul_ifadesi_gercekten_varsa_kabul_edilir():
    assert _odul_ifadesi_gercekten_var_mi("400 TL Bankkart Lira kazanabilirsiniz.") is True
    assert _odul_ifadesi_gercekten_var_mi("10.000 Mil'e varan hediye!") is True


def test_odul_anahtar_kelimesi_alt_dize_yanlis_eslesme_yok():
    """DENETIM BULGUSU 2: bare 'çeki', 'nakit çekim' (para cekme)
    icindeki alt-dizeyle yanlislikla eslesiyordu."""
    assert _odul_ifadesi_gercekten_var_mi("ATM'lerden nakit çekim yapamazsınız.") is False


def test_llm_sayisi_dogrulama_belirsiz_string_reddeder():
    """DENETIM BULGUSU 3: regex/NER'deki her sayisal alan bir donusum
    fonksiyonundan geciyordu, LLM'inki ise ilk yazimda hicbir dogrulama
    olmadan dogrudan kaydediliyordu. LLM 'yuz bin TL' yerine sayı
    donduruyor olsa da, bazen Turkce binlik ayiracli bir STRING
    dondurebilir ('100.000') - bu durumda TAHMIN ETMEK YERINE (100.000
    TL mi yoksa 100,0 TL mi?) deger reddedilmeli."""
    assert _llm_sayisini_dogrula(100000) == 100000
    assert _llm_sayisini_dogrula(1.89) == 1.89
    assert _llm_sayisini_dogrula("100.000") is None
    assert _llm_sayisini_dogrula("36") is None
    assert _llm_sayisini_dogrula(True) is None
    assert _llm_sayisini_dogrula(None) is None


def test_kar_payi_alani_sorulmazsa_bos_kalir():
    sonuc = llm_ile_cikar(
        "Yüzde 1,89 kâr payı oranı ile finansman.",
        sadece_bu_alanlar={"hedef_kitle"},
    )
    assert sonuc["kar_payi_orani_percent"] is None
    assert sonuc["kar_payi_orani_decimal"] is None


def test_bos_alan_kumesiyle_hicbir_sey_sorulmaz():
    sonuc = llm_ile_cikar("Herhangi bir metin.", sadece_bu_alanlar=set())
    izler = sonuc.pop("_izler")
    assert all(v is None for v in sonuc.values())
    assert izler == {}


def test_ilgisiz_metinde_hicbir_alan_bulunmaz():
    sonuc = llm_ile_cikar("Bugün hava çok güzel, parkta yürüyüş yaptım.")
    izler = sonuc.pop("_izler")
    assert all(v is None for v in sonuc.values())
    assert izler == {}

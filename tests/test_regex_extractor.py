"""extraction/regex_extractor.py testleri.

Iki katman:
1. Sentetik metinlerle her alanin dogru cikarildigini/yanlis pozitif
   uretmedigini dogrulayan birim testleri (MVP'nin kendi bulgulari -
   vade/taksit/erteleme ayrimi, ucret baglami dislama, kar paysiz vb. -
   buradaki senaryolarla es deger).
2. scraper/raw_data/*/json/*.json altindaki 23 GERCEK banka kampanya
   metnine karsi calistirip hicbir alanin sacma/imkansiz bir deger
   uretmedigini (makulluk) dogrulayan regresyon testi - tıpkı
   tests/test_scraper_regresyon.py'nin Altin Veri Seti ile yaptigi gibi.
"""

import json
from pathlib import Path

import pytest

from extraction.regex_extractor import genel_guven_hesapla, kaydi_cikar

RAW_DATA = Path(__file__).parent.parent / "scraper" / "raw_data"


def test_kar_payi_baglaminda_yuzdeyi_dogru_bulur():
    r = kaydi_cikar("Kampanyaya ozel kar payi orani %1,89'dur.")
    assert r["kar_payi_orani_percent"] == 1.89
    assert r["kar_payi_orani_decimal"] == 0.0189


def test_ucret_baglamindaki_yuzdeyi_kar_payi_sanmaz():
    r = kaydi_cikar("Tahsis ucreti finansman tutarinin %0,5'idir.")
    assert r["kar_payi_orani_percent"] is None


def test_kar_paysiz_ifadesini_sifir_oran_olarak_isaretler():
    r = kaydi_cikar("Bu urun tamamen kar paysizdir.")
    assert r["kar_payi_orani_percent"] == 0.0
    assert r["kar_payi_orani_decimal"] == 0.0


def test_makul_olmayan_yuzdeyi_kar_payi_olarak_atamaz():
    # Baglam kelimesi "kar pay" yakininda olsa bile %40 gibi bu urun
    # sinifi icin imkansiz bir deger atanmamali (mojibake/yanlis
    # eslesme koruma testi - gercek veride bulunan bir hatanin regresyonu).
    r = kaydi_cikar("Kampanyamizin kar payi kosullari asagida %40 seklindedir.")
    assert r["kar_payi_orani_percent"] is None


def test_vade_taksit_ve_erteleme_birbirinden_ayri_cikarilir():
    metin = "12 aya varan taksit imkani ve 2 ay ertelemeli odeme secenegiyle 36 ay vadeli finansman."
    r = kaydi_cikar(metin)
    assert r["taksit_sayisi"] == 12
    assert r["erteleme_suresi_ay"] == 2
    assert r["vade_ay"] == 36


def test_finansman_tutari_ust_limit_kalibini_cikarir():
    r = kaydi_cikar("100.000 TL'ye kadar finansman firsati.")
    assert r["finansman_tutari"] == 100000.0


def test_finansman_tutari_aralik_kalibinda_ust_siniri_alir():
    r = kaydi_cikar("1.000 TL - 100.000 TL arasi finansman saglanir.")
    assert r["finansman_tutari"] == 100000.0


def test_odul_tl_biriminde_dogru_cikarilir():
    r = kaydi_cikar("5.000 TL değerinde alışveriş çeki kazanın.")
    assert r["odul_miktari"] == 5000.0
    assert r["odul_birimi"] == "TL"


def test_odul_mil_biriminde_dogru_cikarilir():
    r = kaydi_cikar("10.000 Mil'e varan hediye kazanin.")
    assert r["odul_miktari"] == 10000.0
    assert r["odul_birimi"] == "Mil"


def test_masrafsiz_ifadesini_yakalar():
    r = kaydi_cikar("Bu kampanyada dosya masrafi alinmamaktadir.")
    assert r["masraf_durumu"] is not None


def test_kampanya_turunu_anahtar_kelimeyle_siniflandirir():
    r = kaydi_cikar("Konut finansmani kampanyasindan yararlanin.")
    assert r["kampanya_turu"] == "Konut Finansmani Kampanyasi"


def test_hicbir_alan_bulunamazsa_hepsi_none_ve_guven_sifir():
    r = kaydi_cikar("Bu metinde yapilandirilmis hicbir finansal bilgi yoktur.")
    izler = r.pop("_izler")
    assert all(deger is None for deger in r.values())
    assert genel_guven_hesapla(izler) == 0.0


def test_kampanya_baslangic_bitis_tarih_araligindan_cikarilir():
    r = kaydi_cikar("Kampanya 1 Ocak 2026 - 31 Aralik 2026 tarihleri arasinda gecerlidir.")
    assert r["kampanya_baslangic"] == "2026-01-01"
    assert r["kampanya_bitis"] == "2026-12-31"


# ---------------------------------------------------------------------------
# Diyakritiksiz (aksansiz) yazim - POST /cikar'a YAPISTIRILAN metin
# ---------------------------------------------------------------------------
# BULGU (17 Agustos, POST /cikar ucundan uca denemesi): kelime tabanli
# alanlar, Turkce diyakritik olmadan yazilmis metinde SESSIZCE bos donuyordu
# (erteleme_suresi_ay, hedef_kitle, kampanya_turu None; kampanya_avantaji
# eksik). Sayisal alanlar (rakam/sembol eslesmesi) etkilenmiyordu.
#
# NEDEN ONEMLI: POST /cikar ucu ve MetinAnalizi ekrani kullaniciyi serbest
# metin YAPISTIRMAYA davet ediyor - Turkce karakter kullanmadan yazan biri
# alanlarin kayboldugunu GORMEZ. Ayrica PDF/OCR kaynakli metinlerde aksan
# kaybi bilinen bir sorundur (bkz. ner_extractor.py Bulgu 4).
#
# Depoda ayni desen baska katmanlarda zaten cozulmus: agent/intent.py::
# turkce_ascii_katla, terminology/genisletme.py::_turkce_kucult,
# dashboard/.../TerminolojiSozlugu.jsx.

_TURKCE_YAZIM = (
    "Aylık %1,89 kâr payı oranı, 120 aya varan vade. Dosya masrafı alınmaz. "
    "Yeni müşterilerimize özeldir. 6 taksit imkânı. 3 ay ödemesiz dönem."
)
_ASCII_YAZIM = (
    "Aylik %1,89 kar payi orani, 120 aya varan vade. Dosya masrafi alinmaz. "
    "Yeni musterilerimize ozeldir. 6 taksit imkani. 3 ay odemesiz donem."
)

# masraf_durumu KASITLI OLARAK DISARIDA: o alan eslesen HAM METIN parcasini
# (kanit izini) tasir, dolayisiyla kullanicinin kendi yazimini yansitmasi
# DOGRUDUR - "Dosya masrafı alınmaz" ile "Dosya masrafi alinmaz" ayni olmak
# zorunda degil. Yalnizca ikisinde de BULUNMUS olmasi gerekir (asagidaki
# ayri test). Geri kalan alanlar ya sayisal ya da sabit etiket/sablon
# uretir - yazimdan BAGIMSIZ olarak birebir ayni olmalidir.
_YAZIMDAN_BAGIMSIZ_ALANLAR = [
    "kar_payi_orani_percent",
    "kar_payi_orani_decimal",
    "finansman_tutari",
    "vade_ay",
    "taksit_sayisi",
    "erteleme_suresi_ay",
    "odul_miktari",
    "odul_birimi",
    "tahsis_ucreti",
    "kampanya_avantaji",
    "kampanya_baslangic",
    "kampanya_bitis",
    "kampanya_turu",
    "hedef_kitle",
]


@pytest.mark.parametrize("alan", _YAZIMDAN_BAGIMSIZ_ALANLAR)
def test_diyakritiksiz_yazim_ayni_sonucu_verir(alan):
    turkce = kaydi_cikar(_TURKCE_YAZIM)
    ascii_yazim = kaydi_cikar(_ASCII_YAZIM)
    assert ascii_yazim[alan] == turkce[alan], (
        f"'{alan}' alani yazima gore degisiyor: "
        f"ASCII={ascii_yazim[alan]!r} vs Turkce={turkce[alan]!r}"
    )


def test_diyakritiksiz_yazimda_da_masraf_durumu_bulunur():
    """masraf_durumu'nun METNI iki yazimda farkli olabilir (kanit izi ham
    metinden alinir) ama alan ikisinde de DOLU olmalidir."""
    assert kaydi_cikar(_ASCII_YAZIM)["masraf_durumu"] is not None
    assert kaydi_cikar(_TURKCE_YAZIM)["masraf_durumu"] is not None


def test_diyakritiksiz_ay_adiyla_yazilan_tarih_de_cikarilir():
    """Tarih alani, olculdu (raw_data taramasi): ASCII'ye katlanmis metinde
    kampanya_bitis 60 belgede, kampanya_baslangic 13 belgede kayboluyordu -
    RE_TARIH'in ay adlari (Şubat/Mayıs/Ağustos/Eylül/Kasım/Aralık)
    diyakritikli yazilmis oldugu icin. Bu, hata raporundaki dort alandan
    daha genis bir yuzey."""
    r = kaydi_cikar("Kampanya 1 Subat 2026 - 31 Aralik 2026 tarihleri arasinda gecerlidir.")
    assert r["kampanya_baslangic"] == "2026-02-01"
    assert r["kampanya_bitis"] == "2026-12-31"


def test_diyakritiksiz_odul_ifadesi_de_cikarilir():
    r = kaydi_cikar("5.000 TL degerinde alisveris ceki kazanin.")
    assert r["odul_miktari"] == 5000.0
    assert r["odul_birimi"] == "TL"


# ---------------------------------------------------------------------------
# Gercek veriyle makulluk regresyonu
# ---------------------------------------------------------------------------


def _gercek_metinleri_yukle() -> list[tuple[str, str]]:
    sonuc = []
    for dosya in sorted(RAW_DATA.glob("*/json/*.json")):
        with open(dosya, encoding="utf-8") as f:
            kayit = json.load(f)
        metin = kayit.get("ham_metin") or kayit.get("normalize_metin") or ""
        if metin:
            sonuc.append((dosya.name, metin))
    return sonuc


GERCEK_METINLER = _gercek_metinleri_yukle()


def test_gercek_kampanya_metinleri_uzerinde_makul_degerler_uretir():
    """23 gercek banka kampanya metninin hicbirinde imkansiz bir deger
    uretilmemeli - motor yanlis eslesme yerine None donmeyi tercih etmeli
    (rapor Bolum 5.7/15 - seffaflik, uydurma yok)."""
    assert len(GERCEK_METINLER) >= 20, "beklenen fixture sayisi degisti, kontrol et"

    for ad, metin in GERCEK_METINLER:
        r = kaydi_cikar(metin)
        if r["kar_payi_orani_percent"] is not None:
            assert 0.0 <= r["kar_payi_orani_percent"] <= 15.0, ad
        if r["vade_ay"] is not None:
            assert 0 < r["vade_ay"] <= 480, ad
        if r["taksit_sayisi"] is not None:
            assert 0 < r["taksit_sayisi"] <= 480, ad
        if r["erteleme_suresi_ay"] is not None:
            assert 0 < r["erteleme_suresi_ay"] <= 60, ad
        if r["finansman_tutari"] is not None:
            assert 0 < r["finansman_tutari"] <= 100_000_000, ad

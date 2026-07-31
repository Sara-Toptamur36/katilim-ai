"""preprocessing/normalizer.py testleri (Zeynep Veri Toplama Rehberi, Sprint 1 Gun 5).

KRITIK KURAL: metni_normalize_et SAYILARI/ORANLARI/TARIHLERI BOZMAMALI -
bu, Yagmur'un cikarim katmaninin isidir (percent/decimal ikili saklama,
bkz. api/schemas.py CampaignRecord). Bu testler ozellikle bu sinirin
ihlal edilmedigini dogrular.
"""

from preprocessing.normalizer import metni_normalize_et


def test_yuzde_orani_bozulmuyor():
    metin = "Kâr payı oranı %1,89 ile 12 aya varan taksit fırsatı"
    assert "%1,89" in metni_normalize_et(metin)


def test_tl_tutari_bozulmuyor():
    metin = "1.000 TL - 300.000 TL arası ödemelerinizi bölün"
    sonuc = metni_normalize_et(metin)
    assert "1.000 TL" in sonuc
    assert "300.000 TL" in sonuc


def test_tarih_bozulmuyor():
    metin = "Kampanya 1.07.2026 - 31.07.2026 tarihleri arasında geçerlidir"
    assert "1.07.2026 - 31.07.2026" in metni_normalize_et(metin)


def test_kesirli_oran_bozulmuyor():
    """Vakif Katilim'in '98/2' gibi kesirli kar paylasim oranlari (rapor
    Bolum 3) da sayisal bir ifade oldugu icin degismemeli."""
    metin = "98/2 kâr paylaşım oranı ile avantajlı finansman"
    assert "98/2" in metni_normalize_et(metin)


def test_coklu_bosluklari_temizler():
    metin = "Bu   metinde    fazla     boşluk var"
    sonuc = metni_normalize_et(metin)
    assert "   " not in sonuc
    assert "Bu metinde fazla boşluk var" == sonuc


def test_coklu_bos_satirlari_iki_ile_sinirlar():
    metin = "Birinci paragraf\n\n\n\n\nİkinci paragraf"
    sonuc = metni_normalize_et(metin)
    assert "\n\n\n" not in sonuc
    assert "\n\n" in sonuc


def test_bas_son_boslugu_kirpar():
    assert metni_normalize_et("   merhaba   ") == "merhaba"


def test_bos_metin_hata_vermez():
    assert metni_normalize_et("") == ""


def test_turkce_karakterler_korunuyor():
    metin = "Şeffaflık, kâr payı, ığdöşçü İĞÜÖŞÇ"
    assert metni_normalize_et(metin) == metin

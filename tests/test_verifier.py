"""validation/verifier.py testleri.

Iki katmanli test stratejisi:
1. Sentetik metinlerle temel format/varyant kurallarini (virgul/nokta,
   binlik ayiraci, baglam penceresi) izole test eder.
2. GERCEK bir hallusinasyon vakasiyla (KT-006, bkz. modul docstring'i)
   modulun asil var olma sebebini kanitlar: naif "sayi metinde var mi"
   kontrolunun yanlislikla dogrulayacagi iki uydurma deger, bu modul
   tarafindan dogru sekilde reddedilir.
"""

import json
from pathlib import Path

from validation.verifier import kaydi_dogrula, sayisal_iddiayi_dogrula

RAW_DATA = Path(__file__).parent.parent / "scraper" / "raw_data"

# ---------------------------------------------------------------------------
# 1) Sentetik metinlerle temel kurallar
# ---------------------------------------------------------------------------


def test_yuzde_virgul_formati_dogrulanir():
    metin = "Kampanya kapsaminda kar payi orani %1,89 olarak uygulanir."
    sonuc = sayisal_iddiayi_dogrula("kar_payi_orani_percent", 1.89, metin)
    assert sonuc.dogrulandi
    assert sonuc.sayi_metinde_bulundu_mu


def test_yuzde_nokta_formati_da_dogrulanir():
    """Kaynak nokta ondalik kullansa bile (bazi otomatik ceviri/CDN
    metinlerinde gorulur) dogrulama calismali."""
    metin = "Profit share rate: %1.89 kar payi oranidir."
    sonuc = sayisal_iddiayi_dogrula("kar_payi_orani_percent", 1.89, metin)
    assert sonuc.dogrulandi


def test_binlik_ayiracli_tutar_dogrulanir():
    metin = "Azami finansman tutari 40.000 TL'dir."
    sonuc = sayisal_iddiayi_dogrula("finansman_tutari", 40000, metin)
    assert sonuc.dogrulandi


def test_tamsayi_alan_ay_baglaminda_dogrulanir():
    metin = "Kampanya 12 ay vade ile sunulmaktadir."
    sonuc = sayisal_iddiayi_dogrula("vade_ay", 12, metin)
    assert sonuc.dogrulandi


def test_kaynakta_hic_gecmeyen_sayi_reddedilir():
    metin = "Bu metinde hicbir sayisal bilgi yoktur, yalnizca genel tanitim."
    sonuc = sayisal_iddiayi_dogrula("kar_payi_orani_percent", 2.5, metin)
    assert not sonuc.dogrulandi
    assert not sonuc.sayi_metinde_bulundu_mu


def test_sayi_var_ama_baglam_yanlis_reddedilir():
    """Sayi metinde geciyor ama ilgisiz bir baglamda (ör. tarih/telefon
    gibi) - bu, KT-006'daki gercek hallusinasyon deseninin sentetik
    kucuk olcekli versiyonudur (asagidaki gercek-veri testine bakin)."""
    metin = "Kampanya 15 Ocak 2026 tarihinde baslar, telefon: 0850 1,89 00."
    sonuc = sayisal_iddiayi_dogrula("kar_payi_orani_percent", 1.89, metin)
    # Sayi teknik olarak metinde var ("1,89") ama kar payi/oran baglaminda
    # DEGIL - dogrulanmamali.
    assert sonuc.sayi_metinde_bulundu_mu
    assert not sonuc.dogrulandi


# ---------------------------------------------------------------------------
# 2) Gercek hallusinasyon vakasi: KT-006
# ---------------------------------------------------------------------------

_KT006_DOSYA = (
    RAW_DATA
    / "kuveytturk"
    / "json"
    / "20260801_kuveytturk_kampanyalar_kendim-icin_kart-kampanyalari_"
    "yeni-saglam-kart-troylulara-ozel-vade-farksiz-5-aya-varan-taksit-imkani.json"
)


def _kt006_ham_metin() -> str:
    with open(_KT006_DOSYA, encoding="utf-8") as f:
        return json.load(f)["ham_metin"]


def test_kt006_gercek_finansman_tutari_dogrulanir():
    """Altin Veri Seti'ndeki GERCEK deger (50000, finansman_tutari) -
    metinde '50.000 TL' olarak, 'tutar' baglaminda geciyor."""
    sonuc = sayisal_iddiayi_dogrula("finansman_tutari", 50000, _kt006_ham_metin())
    assert sonuc.dogrulandi


def test_kt006_uydurulan_odul_miktari_reddedilir():
    """DENETIM BULGUSU (docs/extraction_accuracy_raporu.md): hibrit
    cikarim boru hatti bu kayitta olmayan bir odul_miktari alanina 50000
    degerini uydurdu - Altin Veri Seti bu alani acikca
    alan_belirtilmemis=True ile bayrakliyor.

    Naif bir kontrol bunu YANLISLIKLA dogrulardi: '50.000 TL' metinde
    GERCEKTEN geciyor - ama finansman_tutari (azami taksit tutari)
    baglaminda, odul/hediye baglaminda DEGIL. Bu, Verifier'in var olma
    sebebidir: sayi + yanlis baglam -> reddedilmeli."""
    sonuc = sayisal_iddiayi_dogrula("odul_miktari", 50000, _kt006_ham_metin())
    assert sonuc.sayi_metinde_bulundu_mu, "sayi metinde olmali (finansman_tutari baglaminda)"
    assert not sonuc.dogrulandi, "yanlis alana atanan sayi dogrulanmamali"


def test_kt006_uydurulan_kar_payi_orani_reddedilir():
    """Ikinci DENETIM BULGUSU: ayni kayitta kar_payi_orani_percent=0.0
    de uyduruldu (Altin Veri Seti: alan_belirtilmemis=True). Bu kayit
    'vade farksiz' ifadesi icermez (bkz. ham metin) - yani kaynakta
    kar payinin 0 oldugunu belirten gercek bir ifade yok, LLM bunu
    kendiliginden uretti."""
    sonuc = sayisal_iddiayi_dogrula("kar_payi_orani_percent", 0.0, _kt006_ham_metin())
    assert not sonuc.dogrulandi


def test_kaydi_dogrula_bos_alanlari_atlar():
    """None degerli alanlar icin bir iddia yok - dogrulama sozlugunde
    hic yer almamali (rapor Bolum 15: eksik veri gizlenmez ilkesiyle
    celismez, bu fonksiyon yalnizca VAR OLAN iddialari dogrular)."""
    alanlar = {"kar_payi_orani_percent": 1.89, "vade_ay": None, "finansman_tutari": None}
    metin = "kar payi orani %1,89'dur."
    sonuclar = kaydi_dogrula(alanlar, metin)
    assert set(sonuclar) == {"kar_payi_orani_percent"}
    assert sonuclar["kar_payi_orani_percent"].dogrulandi


def test_kaydi_dogrula_kt006_tum_alanlari_dogru_ayirir():
    """Uctan uca: KT-006'nin hem gercek hem uydurulan alanlarini AYNI
    cagriya verip, dogru olanin gectigini, uydurulanlarin reddedildigini
    tek testte kanitlar."""
    alanlar = {
        "finansman_tutari": 50000,       # GERCEK (gold)
        "odul_miktari": 50000,           # UYDURULMUS (yanlis pozitif)
        "kar_payi_orani_percent": 0.0,   # UYDURULMUS (yanlis pozitif)
    }
    sonuclar = kaydi_dogrula(alanlar, _kt006_ham_metin())

    assert sonuclar["finansman_tutari"].dogrulandi
    assert not sonuclar["odul_miktari"].dogrulandi
    assert not sonuclar["kar_payi_orani_percent"].dogrulandi

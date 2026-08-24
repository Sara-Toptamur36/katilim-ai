"""NER/LLM'in onerdigi kar payi orani baglamla sinaniyor mu?

--------------------------------------------------------------------------
NEDEN BU TEST VAR (olculdu 24.08.2026)
--------------------------------------------------------------------------
regex_extractor bir yuzdeyi kar payina yazmadan once dort koruma uygular
(nakit iade / indirim / ucret baglami / oran tablosu). Korumalar
calistiginda regex None doner.

Ama hibrit boru hatti bu None'i "regex BILEMEDI" diye yorumlayip alani
NER/LLM'e aciyordu. Oysa oradaki None bir bilgisizlik degil, bir KARAR:
"bu yuzde kar payi orani DEGIL". Sonuc, regex'in bilerek reddettigi
degerin sonraki katmanca geri konmasiydi.

Olculen kanit - kart kampanyalarinda regex=None iken hibrit deger
uretiyordu (id 293 %10, 393/394 %15, 399/401 %5). Regex'in deger BULDUGU
kayitlarda (400/420/457) iki katman zaten ayni sonucu veriyordu, yani
kaybedilecek dogru deger yoktu.

Bedeli juriye gosterilecek ekranda gorunur: `en_dusuk_kar_payi` siralamasi
ASC'dir, uydurma dusuk oran her zaman en uste cikar.
"""

from __future__ import annotations

from extraction.hybrid_pipeline import _kar_payi_baglami_reddediyor_mu as reddediyor


def test_nakit_iade_baglamindaki_oran_REDDEDILIR():
    metin = "Biz Kart ile yemek sektorunde yapilan harcamalarin %10'una kadar nakit iade kazanin."
    assert reddediyor(10.0, metin) is True


def test_indirim_baglamindaki_oran_REDDEDILIR():
    metin = "Anlasmali is yerlerinde %25 indirim firsatini kacirmayin."
    assert reddediyor(25.0, metin) is True


def test_gercek_kar_payi_orani_KABUL_EDILIR():
    metin = "Konut finansmaninda %1,87 kar payi orani ile 120 aya varan vade."
    assert reddediyor(1.87, metin) is False


def test_metinde_HIC_gecmeyen_oran_reddedilmez():
    """Yoklugun cezasi bu fonksiyonun isi degil - Verifier'in isi.

    Bu fonksiyon "baglam kar payi mi" sorusunu cevaplar. Metinde hic
    gecmeyen bir degeri burada reddetmek, iki ayri sorumlulugu birbirine
    karistirirdi.
    """
    assert reddediyor(7.5, "Kampanya kosullari icin subelerimize danisiniz.") is False


def test_TEK_gecerli_gecis_yeterlidir_deger_korunur():
    """Supheyle veri atilmaz: bir gecis kar payi baglamindaysa deger kalir.

    Ayni yuzde hem nakit iade hem kar payi cumlesinde geciyorsa, kar payi
    okumasi gercek olabilir - temkinli taraf KORUMAKTIR.
    """
    metin = (
        "Harcamalarinizin %5'i nakit iade olarak hesabiniza yatar. "
        "Ayrica ihtiyac finansmaninda %5 kar payi orani uygulanir."
    )
    assert reddediyor(5.0, metin) is False


def test_cumle_SONUNDAKI_nokta_eslesmeyi_bozmaz():
    """ILERI-BAKIS TUZAGI - bir kez dusuldu, bu test onun bekcisi.

    Desen once `(?![\\d.,])` yazilmisti; cumle sonundaki noktayi da
    eliyordu. "...%5." metinde duruyor ama eslesmiyor, deger "metinde yok"
    sayilip koruma SESSIZCE atlanıyordu - olculdu: id 399/401 bu yuzden
    reddedilmeden geciyordu.
    """
    metin = "Yapilan harcamalara nakit iade orani %5."
    assert reddediyor(5.0, metin) is True


def test_ondalik_devami_olan_yuzde_karistirilmaz():
    """"%5,5" metninde "%5" aranmamali - baska bir sayidir."""
    metin = "Kar payi orani %5,5 olarak uygulanir."
    assert reddediyor(5.0, metin) is False  # "%5" gecisi yok -> karar verilmez


def test_turkce_ondalik_ayraci_da_bulunur():
    metin = "Harcamalarin %3,49'u nakit iade olarak verilir."
    assert reddediyor(3.49, metin) is True


def test_ucret_baglamindaki_oran_REDDEDILIR():
    metin = "Tahsis ucreti finansman tutarinin %2'si olarak alinir."
    assert reddediyor(2.0, metin) is True

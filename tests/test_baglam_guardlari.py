"""Baglam guard'larinin testleri: kar_payi_orani ve odul_miktari.

ORTAK ILKE: bir sayisal kalip TEK BASINA bir kavrami belirtmez. "%10"
bir kar payi da olabilir bir odul orani da; "maksimum 50.000 TL" bir
odul tavani da olabilir bir taksitlendirme tavani da. Karar, sayinin
AYNI CUMLESINDEKI kelimelere bakilarak verilir.

Buradaki senaryolarin hepsi gercek banka metinlerinden alinmistir;
hangi kayittan geldigi test docstring'lerinde yazilidir.
"""

from extraction.regex_extractor import kaydi_cikar


# ---------------------------------------------------------------------------
# kar_payi_orani - genel yuzde fallback'inin dislamalari
# ---------------------------------------------------------------------------


def test_odul_yuzdesi_kar_payi_SAYILMAZ():
    """Gercek TEK-001 metni: "%10" burada bir kazanim orani."""
    r = kaydi_cikar(
        "MTV odemesi yapan musteriler odeme tutarinin %10'u oraninda, "
        "en fazla 500 TL odul kazanabilir."
    )
    assert r["kar_payi_orani_percent"] is None


def test_dar_makas_kar_payi_SAYILMAZ():
    """Gercek HF-005 metni: dar makas doviz/altin alim-satim spreadidir.
    terminology/sozluk.json bunu ZATEN "kar_payi_orani ile
    KARISTIRILMAMALI" diye isaretlemis; kural artik regex'e de bagli."""
    r = kaydi_cikar(
        "Avantajli Hesap musterileri 100.000 USD veya karsiligi islem "
        "hacmine kadar %0,1 dar makastan yararlanabilir."
    )
    assert r["kar_payi_orani_percent"] is None


def test_nakit_iade_yuzdesi_kar_payi_SAYILMAZ():
    r = kaydi_cikar("Restoran harcamalarinizda %10 iade kazanin!")
    assert r["kar_payi_orani_percent"] is None


def test_gercek_kar_payi_orani_HALA_bulunur():
    """Guard fazla genis olmamali."""
    r = kaydi_cikar("Kampanyaya ozel kar payi orani %1,89'dur.")
    assert r["kar_payi_orani_percent"] == 1.89


def test_vade_farksiz_sifir_orani_KORUNUR():
    """Bu kural 4 gercek kayitta dogru calisiyor (AL-002/005/006,
    TOM-002) - dislama listesi onu bozmamali."""
    r = kaydi_cikar("MTV odemelerinize kredi kartiyla vade farksiz 3 taksit!")
    assert r["kar_payi_orani_percent"] == 0.0


def test_ikincil_urundeki_kar_paysiz_ifadesi_ANA_orani_SIFIRLAMAZ():
    """OLCULDU (kar_payi_tablosu zenginlestirme calistirmasi, id=155/158/
    165): Turkiye Finans'in Ihtiyac Finansmani sayfalarinda "Kâr paysız
    2.500 TL'ye kadar Yedek Hesap finansman desteğinden yararlanabilirsiniz"
    cumlesi var - bu ANA kampanyadan AYRI, kucuk tutarli bir ek urunu
    (Yedek Hesap) anlatiyor, guard olmadan sayfanin gercek (tabloda duran,
    vadeye gore degisen) oranini yanlislikla 0.0 yapiyordu."""
    r = kaydi_cikar(
        "Ihtiyac finansmani basvurunuzu hemen yapin. "
        "Kâr paysız 2.500 TL'ye kadar Yedek Hesap finansman desteğinden "
        "yararlanabilirsiniz."
    )
    assert r["kar_payi_orani_percent"] is None


def test_dogrudan_kar_paysiz_ifadesi_HALA_calisir():
    """Guard cok DAR olmamali - ana urunu anlatan dogrudan 'kar paysiz'
    ifadeleri (Yedek Hesap gibi bilinen ikincil urun adi GECMEDEN) hala
    sifir oran olarak isaretlenmeli."""
    r = kaydi_cikar("Bu urun tamamen kar paysizdir.")
    assert r["kar_payi_orani_percent"] == 0.0


def test_komsu_cumledeki_odul_kelimesi_kar_payini_ELEMEZ():
    """Baglam penceresi cumleye kirpilir - onceki cumledeki 'kazanin'
    sonraki cumledeki gercek orani reddetmemeli."""
    r = kaydi_cikar(
        "Kampanyadan 500 TL odul kazanin. Ayrica kar payi orani %1,45 olarak uygulanir."
    )
    assert r["kar_payi_orani_percent"] == 1.45


# ---------------------------------------------------------------------------
# odul_miktari - tavan/limit kalibinin baglam sarti
# ---------------------------------------------------------------------------


def test_taksitlendirme_tavani_odul_SAYILMAZ():
    """Gercek KT-006 metni: "maksimum tutar 50.000 TL" bir
    TAKSITLENDIRME tavani, odul degil."""
    r = kaydi_cikar(
        "Bu harcamaya ait uygulanacak taksitlendirmede maksimum tutar 50.000 TL'dir."
    )
    assert r["odul_miktari"] is None
    assert r["odul_birimi"] is None


def test_odul_tavani_HALA_bulunur():
    """Ayni cumlede odul kelimesi varsa tavan gecerlidir - bu desen 4
    gercek kayitta dogru calisiyor."""
    r = kaydi_cikar(
        "Kampanyadan kazanilabilecek odul miktari, bir takvim yilinda "
        "en fazla 5 gram olacaktir."
    )
    assert r["odul_miktari"] == 5.0
    assert r["odul_birimi"] == "Gram"


def test_sinirli_kalibi_odul_baglaminda_bulunur():
    """Gercek TOM-001 metni."""
    r = kaydi_cikar(
        "Kampanya donemi boyunca kazanilabilecek iade 2.500 TL ile sinirlidir."
    )
    assert r["odul_miktari"] == 2500.0


def test_odul_kelimesi_olmayan_sinirli_kalibi_ELENIR():
    r = kaydi_cikar("Islem basina transfer tutari 10.000 TL ile sinirlidir.")
    assert r["odul_miktari"] is None

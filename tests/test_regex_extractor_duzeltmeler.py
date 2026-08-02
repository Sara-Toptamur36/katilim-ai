"""extraction/regex_extractor.py icin ek testler (Sprint 1 Gun 4 duzeltmeleri).

Sara'nin Extraction Accuracy olcumunun (docs/extraction_accuracy_raporu.md,
%37.5 -> hedef %95) bulduğu somut hatalari ve bunlarin duzeltmelerini
kilitler. tests/test_regex_extractor.py'ye (Sara'nin dosyasi) dokunulmadan,
ayri bir dosyada tutulur.

BILEREK DUZELTILMEYEN, veri setinin kendi notunda zaten isaretlenmis acik
tasarim sorulari (regex bunlari "cozmemeli" - flag'lenmis belirsizlikler):
- KT-006/AL-002/AL-005/AL-006: Altin Veri Seti bazi kayitlarda vade_ay
  alanini "taksit sayisi" anlaminda kullanmis (KT-006 notu: "vade_ay
  alani burada taksit sayisi anlaminda kullanildi, klasik kredi vadesi
  degil - ekiple bu ayrimi konusmak gerekebilir"). Motor bilerek vade
  ve taksit sayisini AYRI tutar (vade_ay=None kalir), bu dogru davranistir.
- AL-001: iki bolumlu bir kampanya (40.000 TL Pratik Finansman Kart +
  100.000 TL vade farksiz alisveris), Altin Veri Seti "ilk kismi" esas
  almis - motor coklu-aday durumunda hangi tutarin "asil" oldugunu
  guvenilir sekilde secemez (NER/LLM katmaninin isi, Sprint 2).
- DK-002: Altin Veri Seti davet-basi birim odulu (0,1 gram) esas almis,
  ama metnin kendisi toplam tavani ("1 grama kadar") one cikariyor -
  hangisinin "dogru" oldugu yorum gerektirir.
"""

import json
from pathlib import Path

from extraction.regex_extractor import kaydi_cikar
from scraper.scripts.extraction_accuracy import extraction_accuracy_hesapla

RAW_DATA = Path(__file__).parent.parent / "scraper" / "raw_data"


# ---------------------------------------------------------------------------
# odul_birimi artik kosulsuz "TL" degil, gercekten eslesen birimi donuyor
# ---------------------------------------------------------------------------


def test_odul_birimi_bankkart_lira_dogru_tespit_edilir():
    r = kaydi_cikar("Anlaşmalı işyerlerinde yapacağınız harcamaya 400 TL Bankkart Lira kazanabilirsiniz.")
    assert r["odul_miktari"] == 400.0
    assert r["odul_birimi"] == "Bankkart Lira"


def test_odul_birimi_parafpara_dogru_tespit_edilir():
    r = kaydi_cikar("Akaryakıt Harcamalarınıza 300 TL ParafPara kazanın!")
    assert r["odul_miktari"] == 300.0
    assert r["odul_birimi"] == "ParafPara"


def test_odul_birimi_worldpuan_dogru_tespit_edilir():
    r = kaydi_cikar("Albaraka Mobil üzerinden ödemenizi yaparak 1.250 TL Worldpuan kazanın!")
    assert r["odul_miktari"] == 1250.0
    assert r["odul_birimi"] == "Worldpuan"


def test_odul_birimi_genel_durumda_hala_tl_doner():
    r = kaydi_cikar("5.000 TL değerinde alışveriş çeki kazanın!")
    assert r["odul_birimi"] == "TL"


# ---------------------------------------------------------------------------
# RE_ODUL_MIL egik/tipografik apostrofu (U+2019) da kapsamali
# ---------------------------------------------------------------------------


def test_odul_mil_egik_apostrofla_da_calisir():
    """Gercek taranmis web metni duz apostrof (') degil egik/tipografik
    apostrof (', U+2019) kullanir - önceden bu yuzden Mil odulleri hic
    yakalanmiyordu (KT-005, Extraction Accuracy raporu)."""
    r = kaydi_cikar("Miles&Smiles kredi kartınız ile 1.000 TL ve üzeri harcamanıza 10.000 Mil’e varan hediye!")
    assert r["odul_miktari"] == 10000.0
    assert r["odul_birimi"] == "Mil"


# ---------------------------------------------------------------------------
# Odul tavan/limit ifadeleri ("en fazla", "maksimum", "ile sinirli")
# ---------------------------------------------------------------------------


def test_odul_tavan_ifadesi_maksimum_ile_yakalanir():
    r = kaydi_cikar("Kampanyadan kazanılabilecek ödül miktarı, bir takvim yılı içerisinde en fazla 5 gram olacaktır.")
    assert r["odul_miktari"] == 5.0
    assert r["odul_birimi"] == "Gram"


def test_odul_tavan_birden_fazla_adayda_en_buyugu_secer():
    """Kisi basi / gunluk / aylik ARA basamak tavanlari, nihai toplamdan
    KUCUK olmalidir - en buyuk deger secilerek dogru toplam bulunur."""
    r = kaydi_cikar(
        "Davet eden kişi, davet ettiği kişinin kampanya koşullarını sağlaması halinde, "
        "kişi başı maksimum 2.000 TL, toplamda 5 kişi için maksimum 10.000 TL nakit ödül kazanabilir."
    )
    assert r["odul_miktari"] == 10000.0
    assert r["odul_birimi"] == "TL"


def test_odul_sinirli_ifadesi_yakalanir():
    r = kaydi_cikar(
        "Kampanya döneminde günlük kazanılabilecek maksimum iade 100 TL, bir takvim ayında "
        "kazanılabilecek maksimum iade ise 500 TL, kampanya dönemi boyunca kazanılabilecek "
        "iade 2.500 TL ile sınırlıdır."
    )
    assert r["odul_miktari"] == 2500.0


def test_odul_bare_iade_kelimesi_kadar_ile_yakalanir():
    r = kaydi_cikar("Tüm Marketlerde Geçerli, 1.000 TL’ye kadar iade!")
    assert r["odul_miktari"] == 1000.0
    assert r["odul_birimi"] == "TL"


# ---------------------------------------------------------------------------
# "Vade farksiz" -> kar payi orani 0 (sifir-oran ifadesi)
# ---------------------------------------------------------------------------


def test_vade_farksiz_kar_payini_sifir_olarak_isaretler():
    r = kaydi_cikar("Kredi kartınızla vade farksız 3 taksit ile ödeyebilirsiniz.")
    assert r["kar_payi_orani_percent"] == 0.0
    assert r["kar_payi_orani_decimal"] == 0.0


# ---------------------------------------------------------------------------
# "Kar orani" da "kar payi" kadar yuksek guvenle taninmali
# ---------------------------------------------------------------------------


def test_kar_orani_ifadesi_kar_payi_kadar_yuksek_guvenle_bulunur():
    r = kaydi_cikar("Aylık kar oranı %1,99, aylık maliyet %0,0862, yıllık maliyet %36,3758.")
    assert r["kar_payi_orani_percent"] == 1.99


def test_maliyet_baglami_kar_payi_ile_karistirilmaz():
    """Duzeltmeden ONCE bu senaryoda 'iade' disi bir maliyet ifadesi kar
    payi orani sanilabiliyordu - simdi 'maliyet' de ucret/masraf gibi
    dislanan baglam kelimeleri arasinda, ayrica 'kar orani' baglamsal
    eslesmesi zaten dogru degeri (%1,99) yuksek guvenle buluyor."""
    r = kaydi_cikar(
        "12 ay vadeli 10.000 TL'lik başvuru için örnek ödeme planı: "
        "Aylık kar oranı %1,99, aylık maliyet %0,0862, yıllık maliyet %36,3758, "
        "ödenecek toplam tutar 12.125,92 TL."
    )
    assert r["kar_payi_orani_percent"] == 1.99


def test_nakit_iade_yuzdesi_kar_payi_sanilmaz():
    """TOM-002 (Extraction Accuracy raporu): '%10 iade' bir cashback
    oranidir, kar payi orani degildir - 'iade' baglaminda genel yuzde
    fallback'i devreye girmemeli (yanlis deger uretmektense None kalmali)."""
    r = kaydi_cikar(
        "Restoran harcamalarında %10 İade Kazan! "
        "750 TL ve üstü her restoran harcamasında %10 iade kazanılabilir."
    )
    assert r["kar_payi_orani_percent"] is None


# ---------------------------------------------------------------------------
# Vade suresi: "vade suresi ... X aydir" (aralarinda kelime olabilir,
# Turkce cekim eki nedeniyle sondaki \b kullanilamaz)
# ---------------------------------------------------------------------------


def test_vade_suresi_araya_kelime_giren_bicimde_yakalanir():
    r = kaydi_cikar("İhtiyaç Finansmanına uygulanacak maksimum vade süresi 36 aydır.")
    assert r["vade_ay"] == 36


# ---------------------------------------------------------------------------
# Bilinen, KASITLI OLARAK duzeltilmeyen belirsizlikler dogru sekilde
# None/beklenmeyen deger uretmeye devam ediyor mu (regresyon degil,
# tasarim karari oldugunu belgelemek icin)
# ---------------------------------------------------------------------------


def test_taksit_sayisi_vade_ile_karistirilmaya_devam_etmez():
    """KT-006 tarzi: 'vade farksiz N taksit' - N, vade_ay'a degil
    taksit_sayisi'na yazilmali. Altin Veri Seti bazi kayitlarda bunu
    vade_ay olarak isaretlemis olsa da (kendi notunda tartismali
    oldugunu belirtiyor), motor kasitli olarak bu ayrimi korur."""
    r = kaydi_cikar("Yeni Sağlam Kart Troy müşterilerine özel 50.000 TL'ye kadar vade farksız 5 taksit fırsatını kaçırmayın!")
    assert r["taksit_sayisi"] == 5
    assert r["vade_ay"] is None


# ---------------------------------------------------------------------------
# Resmi Extraction Accuracy esik regresyonu (rapor Bolum 13 hedefi: >= %95)
# ---------------------------------------------------------------------------


def test_extraction_accuracy_asgari_esigin_altina_dusmez():
    """Sprint 1 Gun 4 duzeltmeleri sonrasi dogruluk %37.5 -> %84.38'e
    cikti. Hedef (%95) henuz karsilanmadi (kalan hatalarin cogu, Altin
    Veri Seti'nin kendi notlarinda isaretledigi acik tasarim sorulari -
    bkz. dosya basi aciklamasi), ama bu esik ileride bir regresyonu
    yakalamak icin var - dusukse CI kirilmali."""
    sonuc = extraction_accuracy_hesapla()
    assert sonuc["accuracy"] >= 80.0, (
        f"Extraction Accuracy %{sonuc['accuracy']}'e dustu (asgari %80 bekleniyordu). "
        f"Hatalar: {sonuc['hatalar']}"
    )

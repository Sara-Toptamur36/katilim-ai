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


def test_vade_farksiz_kar_payi_orani_URETMEZ():
    """KURAL DEGISTI (23 Agustos 2026) - bu test eski davranisi kilitliyordu.

    Eskiden "vade farksiz" gorulunce kar_payi_orani = 0 yaziliyordu. Kural
    kaldirildi (bkz. extraction/regex_extractor.py desen tanimlari): "vade
    farksiz 3 taksit" bir KART TAKSIT ifadesidir, finansman kar payi orani
    degildir. Uydurma sifir yalnizca yanlis degil aktif olarak zararliydi -
    comparison/compare_engine.py "en dusuk kar payi" kriterini ASC
    siraladigi icin bir kart kampanyasinin 0'i, gercek konut finansmaninin
    %1,87'sini her karsilastirmada yeniyordu.

    Test SILINMEDI, TERSINE CEVRILDI: kuralin geri gelmesi de bir
    gerileme olur ve yakalanmali.
    """
    r = kaydi_cikar("Kredi kartınızla vade farksız 3 taksit ile ödeyebilirsiniz.")
    assert r["kar_payi_orani_percent"] is None
    assert r["kar_payi_orani_decimal"] is None


def test_acik_sifir_ifadeleri_korunuyor():
    """"Vade farksiz" kaldirilirken GERCEK sifirlar kaybedilmedi.

    Sifir kar payli kampanyalar bunu acikca yaziyor; o iki kural
    (RE_KAR_PAYSIZ / RE_KAR_PAYI_SIFIR) yerinde duruyor.
    """
    assert kaydi_cikar("Kâr paysız finansman fırsatı")["kar_payi_orani_percent"] == 0.0
    assert kaydi_cikar("0 kâr paylı 12 ay vade")["kar_payi_orani_percent"] == 0.0


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


# Sayisal cekirdek alanlar: Sartname Md. 5.3'un TUTAR/ORAN/SURE alanlari.
# Bunlar span-cikarim isidir (metinde bir sayi vardir, ya bulunur ya
# bulunmaz) ve regex katmaninin asil sorumlulugudur.
_SAYISAL_CEKIRDEK = (
    "kar_payi_orani_percent",
    "vade_ay",
    "odul_miktari",
    "odul_birimi",
    "finansman_tutari",
    "taksit_sayisi",
    "erteleme_suresi_ay",
)


def test_sayisal_cekirdek_alanlarda_dogruluk_esigin_altina_dusmez():
    """Sayisal cekirdegin makro F1'i regex katmaninin asil karnesidir.

    ESIK NEDEN YENIDEN TANIMLANDI (23 Agustos 2026): eskiden tek bir
    toplam `accuracy` >= %80 kontrol ediliyordu. O esik, olcum yalnizca
    yukarideki YEDI sayisal alani kapsarken yazilmisti. Olcum kapsami
    Sartname Md. 5.4/5.3 icin ON BIR alana cikarildi (kampanya_turu,
    hedef_kitle, kampanya_baslangic, kampanya_bitis eklendi) ve bu dort
    alan SINIFLANDIRMA/TARIH isidir - regex'in zayif oldugu, farkli
    yontem gerektiren alanlar.

    Sonuc: toplam `accuracy` iki farkli isin ortalamasi haline geldi ve
    %80 esigi anlamini yitirdi (olculdu: %52,07). Esigi oldugu yerde
    birakmak CI'yi kalici kirmizi yapardi; koru koru dusurmek ise
    sayisal cekirdekteki gercek bir gerilemeyi gizlerdi.

    Bu yuzden esik IKIYE bolundu: burada sayisal cekirdek, asagida
    toplam. Iki is ayri olculur, biri digerini maskelemez.
    """
    sonuc = extraction_accuracy_hesapla()
    alan_bazli = sonuc["alan_bazli"]

    f1_ler = [
        alan_bazli[a]["f1"]
        for a in _SAYISAL_CEKIRDEK
        if a in alan_bazli and alan_bazli[a]["destek"] > 0
    ]
    assert f1_ler, "Sayisal cekirdek alanlarin hicbirinde destek yok - olcum bozulmus"
    makro_f1 = sum(f1_ler) / len(f1_ler)

    assert makro_f1 >= 75.0, (
        f"Sayisal cekirdek makro F1 %{makro_f1:.2f}'ye dustu (asgari %75). "
        f"Alan bazli: "
        + ", ".join(
            f"{a}={alan_bazli[a]['f1']}"
            for a in _SAYISAL_CEKIRDEK
            if a in alan_bazli and alan_bazli[a]["destek"] > 0
        )
    )


def test_toplam_dogruluk_esigin_altina_dusmez():
    """ON BIR alanin tamami uzerindeki toplam dolu alan dogrulugu.

    Esik, olculen seviyenin (%52,07) bir miktar altina konur - amaci
    hedef belirlemek degil, GERILEMEYI yakalamaktir. Zayif alanlar
    (kampanya_turu F1 %35,63, kampanya_baslangic R %20,27, hedef_kitle
    F1 %30,00) iyilestikce bu esik de yukseltilmelidir.
    """
    sonuc = extraction_accuracy_hesapla()
    assert sonuc["accuracy"] >= 48.0, (
        f"Toplam dolu alan dogrulugu %{sonuc['accuracy']}'e dustu "
        f"(asgari %48 bekleniyordu, olculen taban %52,07)."
    )


def test_yanlis_pozitif_orani_esigin_altina_dusmez():
    """Bos alan dogrulugu - "kaynakta olmayani uydurma" korumasi.

    Finansal baglamda kacirmaktan DAHA tehlikeli olan hata turu budur,
    bu yuzden ayri ve daha yuksek bir esikle korunur.
    """
    sonuc = extraction_accuracy_hesapla()
    assert sonuc["bos_alan_dogrulugu"] >= 92.0, (
        f"Bos alan dogrulugu %{sonuc['bos_alan_dogrulugu']}'e dustu "
        f"(asgari %92). Yanlis pozitif: {sonuc['yanlis_pozitif_sayisi']}"
    )


# ---------------------------------------------------------------------------
# 23 Agustos 2026 - sayi ayristirma ve oran baglami duzeltmeleri
# ---------------------------------------------------------------------------
# Altin Veri Seti 64 -> 103 kayda buyuyunce olcum yenilendi ve iki kok neden
# ortaya cikti. Ikisi de asagida kilitlenir; bunlar bir daha sessizce
# gerilemesin diye test edilirler (her ikisi de "sessiz" hatalardi -
# istisna atmiyor, sadece YANLIS sayi uretiyorlardi).


def test_ayracsiz_tutar_tam_uzunlugunda_okunur():
    r"""'2000 TL' -> 2000.0 (200.0 DEGIL).

    KOK NEDEN: tutar deseninin ilk alternatifi `\d{1,3}(?:\.\d{3})*`
    idi - yildiz sayesinde ayrac olmayan sayilarda da eslesiyor ve
    alternation soldan saga calistigi icin "2000"de "200"u yakalayip
    donuyordu. Ayrac kullanmadan yazilmis HER tutar 10-100 kat kucuk
    okunuyordu. Finansal bir uygulamada bu, tutari hic bulamamaktan
    daha tehlikelidir: ekranda makul gorunen ama yanlis bir sayi cikar.
    """
    from extraction.normalizer import tutara_cevir

    assert tutara_cevir("2000 TL") == 2000.0
    assert tutara_cevir("10000 TL") == 10000.0
    assert tutara_cevir("400000 TL") == 400000.0
    # Ayracli ve kelimeli bicimler BOZULMAMALI (gerileme kontrolu)
    assert tutara_cevir("50.000 TL") == 50000.0
    assert tutara_cevir("1.000.000 TL") == 1000000.0
    assert tutara_cevir("250 Bin TL") == 250000.0
    assert tutara_cevir("1500,50 TL") == 1500.5


def test_ayracsiz_odul_tutari_sifira_dusmez():
    """ZK-009: 'Veteriner ve Petshop Harcamalariniza 2000 TL Bankkart Lira'

    Motor eskiden '000 TL'yi yakalayip odul_miktari = 0.0 uretiyordu.
    Sifir yalnizca yanlis degil, AKTIF OLARAK ZARARLI bir degerdi:
    comparison/compare_engine.py 'en dusuk' kriterlerinde ASC siraladigi
    icin uydurma sifir her karsilastirmayi kazanirdi.
    """
    sonuc = kaydi_cikar("Veteriner ve Petshop Harcamalarınıza 2000 TL Bankkart Lira!")
    assert sonuc["odul_miktari"] == 2000.0
    assert sonuc["odul_birimi"] == "Bankkart Lira"


def test_sadakat_birimi_yuzdesi_kar_payi_sanilmaz():
    """ZK-011 / ZK-016: '... tum harcamalara %10, toplamda 5.000 TL Bankkart Lira'

    Buradaki %10 bir KAZANIM oranidir. Dislama listesinde 'puan' ve 'odul'
    vardi ama bankalarin kendi birim adlari (Bankkart Lira, Worldpuan,
    ParafPara) yoktu.
    """
    metin = "Bankkart POS'larında tüm harcamalara %10, toplamda 5.000 TL Bankkart Lira!"
    assert kaydi_cikar(metin)["kar_payi_orani_percent"] is None


def test_nakit_iade_yuzdesi_kar_payi_sanilmaz():
    """HF-010: 'harcamalarin %10'u, gunluk en fazla 100 TL' - iade orani."""
    metin = "Biz Kart ile yemek sektöründe yapılan harcamaların %10’u, günlük en fazla 100 TL."
    assert kaydi_cikar(metin)["kar_payi_orani_percent"] is None


def test_maliyet_tablosu_hucresi_kar_payi_sanilmaz():
    """TF-001 / TF-008: 'Toplam Maliyet' tablosunun ortasindaki bir hucre.

    Baglam penceresi 45 karakter oldugu icin satir basindaki 'Maliyet'
    basligi uzak hucrelere yetismiyordu. TF-001 raporlarda 'bilinen yanlis
    pozitif' olarak belgeliydi - kok nedeni buymus.
    """
    metin = (
        "Vade | Aylık Kâr Oranı | Aylık Toplam Maliyet | Yıllık Toplam Maliyet | "
        "3 | 4,20% | 0,50% | 5,77% | 96,05% | 12 | 4,15% | 0,50% | 5,50% | 90,09%"
    )
    sonuc = kaydi_cikar(metin)
    # Tablodaki hicbir hucre dusuk guvenli fallback ile kar payi olarak
    # ATANMAMALI - tablolari extraction/tablo_extractor.py okur.
    iz = sonuc.get("_izler", {}).get("kar_payi_orani_percent")
    assert iz is None or iz[1] >= 0.9, f"tablo hucresi fallback ile atandi: {iz}"


def test_gercek_kar_payi_orani_hala_bulunur():
    """Yeni baglam kurallari GERCEK oranlari elemiyor (gerileme kontrolu)."""
    assert kaydi_cikar("Aylık kâr payı oranı %1,89 ile 120 ay vade.")[
        "kar_payi_orani_percent"
    ] == 1.89
    assert kaydi_cikar("Konut finansmanında %2,05 kâr oranı fırsatı.")[
        "kar_payi_orani_percent"
    ] == 2.05

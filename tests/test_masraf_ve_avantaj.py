"""masraf_durumu / tahsis_ucreti cikarimi ve kampanya_avantaji derlemesi.

NEDEN AYRI DOSYA: Bu iki alan sartname Md. 5.3'un bekledigi cikti
sutunlarindan ("Masraf Bilgisi", "Kampanya Avantaji") ve tahsis_ucreti
ayrica Md. 5.7'nin "En Dusuk Masraf" karsilastirma kriterinin siraladigi
alandir - yani bos kalirsa o kriter hicbir zaman sonuc uretemez.

Testlerin cogu SENTETIK degil, 234 gercek belgeden alinan GERCEK
cumlelerdir; hangi bankadan geldikleri yorumlarda belirtilmistir.
"""

from extraction.regex_extractor import kampanya_avantajini_olustur, kaydi_cikar

# ---------------------------------------------------------------------------
# masraf_durumu / tahsis_ucreti
# ---------------------------------------------------------------------------


def test_acik_masrafsizlik_ifadesi_tahsis_ucretini_sifirlar():
    """Gercek Turkiye Finans metni: dosya masrafinin alinmadigini ACIKCA
    soyluyor - bu, tahsis ucretinin 0 TL oldugu iddiasini destekler."""
    metin = (
        "Tutarindan bagimsiz tum vadelerde sabit %4.09 kar payi orani, "
        "3 ay erteleme firsati ve yeni musterilere ozel dosya masrafsizlik "
        "avantaji sizi bekliyor."
    )
    r = kaydi_cikar(metin)
    assert r["tahsis_ucreti"] == 0.0
    assert "masrafsizlik" in r["masraf_durumu"].lower()


def test_sifir_komisyon_ifadesi_tahsis_ucretini_sifirlar():
    """Gercek Hayat Finans metni."""
    r = kaydi_cikar("Yeni Yatirim Hesabiniza Sifir Komisyon Orani ile baslayin.")
    assert r["tahsis_ucreti"] == 0.0


def test_baglamsiz_masrafsiz_kelimesi_tahsis_ucreti_iddiasi_URETMEZ():
    """Gercek veride "Masrafsiz" iki belgede TEK BASINA BIR SATIRDA geciyor
    (gezinme menusu/urun etiketi: "Masrafsiz Bankacilik"). Bu, kampanyanin
    masraf durumu hakkinda bir iddia degildir.

    Bilgi kaybedilmez (masraf_durumu doldurulur) ama tahsis_ucreti BOS
    kalir - aksi halde bu kampanya "en dusuk masraf" siralamasinda haksiz
    yere birinci olurdu."""
    r = kaydi_cikar("Kampanyalar\nMasrafsiz\nBize Ulasin")
    assert r["masraf_durumu"] is not None
    assert r["tahsis_ucreti"] is None


def test_oran_olarak_verilen_tahsis_ucreti_TL_alanina_YAZILMAZ():
    """Gercek Turkiye Finans metni. "Binde 5" bir ORANDIR; tahsis_ucreti
    alani TL bekler. Orani finansman tutariyla carpip TL uretmek iki
    cikarilmis degeri birlestirip birim hatasi riski yaratir."""
    metin = (
        "Tahsis ucreti vergiler haric finansman tutarinin binde 5'i "
        "oranindadir."
    )
    r = kaydi_cikar(metin)
    assert r["masraf_durumu"] is not None
    assert r["tahsis_ucreti"] is None


def test_acik_TL_tutari_verilen_masraf_cikarilir():
    r = kaydi_cikar("Dosya masrafi 500 TL olarak uygulanir.")
    assert r["tahsis_ucreti"] == 500.0


def test_ucretsiz_kart_cumlesi_masraf_durumu_URETMEZ():
    """EN YAYGIN GURULTU (234 belgenin 50'sinde geciyor): buradaki
    "ucretsiz" kartin TURUNU niteliyor, kampanyanin masraf durumunu
    DEGIL. Desenler bir masraf kelimesi (masraf/tahsis/komisyon/aidat)
    gecmesini zorunlu kildigi icin eslesmemeli."""
    r = kaydi_cikar("Ucretsiz ve ticari kredi kartlarimiz kampanyaya dahil degildir.")
    assert r["masraf_durumu"] is None
    assert r["tahsis_ucreti"] is None


def test_ucretsiz_sms_cumlesi_masraf_durumu_URETMEZ():
    """Ikinci yaygin gurultu (27 belgede)."""
    metin = "Katilim SMS'i ucretsiz olup; kampanyaya katilabilmek icin SMS gonderilmelidir."
    r = kaydi_cikar(metin)
    assert r["masraf_durumu"] is None
    assert r["tahsis_ucreti"] is None


def test_kvkk_ucretsiz_cumlesi_masraf_durumu_URETMEZ():
    """Ucuncu yaygin gurultu (10 belgede) - KVKK sablonu."""
    metin = "Talebiniz en gec otuz (30) gun icinde ucretsiz olarak sonuclandirilmaktadir."
    assert kaydi_cikar(metin)["masraf_durumu"] is None


# ---------------------------------------------------------------------------
# kampanya_avantaji (DERLEME)
# ---------------------------------------------------------------------------


def test_avantaj_ozeti_cikarilan_alanlardan_derlenir():
    ozet = kampanya_avantajini_olustur(
        {
            "kar_payi_orani_percent": 1.89,
            "finansman_tutari": 50000.0,
            "vade_ay": 120,
            "odul_miktari": 5000.0,
            "odul_birimi": "TL",
        }
    )
    assert "%1,89 kâr payı oranı" in ozet
    assert "50.000 TL'ye kadar finansman" in ozet
    assert "120 ay vade" in ozet
    assert "5.000 TL ödül" in ozet


def test_avantaj_ozeti_sifir_orani_kelimeyle_ifade_eder():
    """"%0 kâr payı oranı" teknik olarak dogru ama kullaniciya anlamsiz
    gelir; sartnamenin kendi ornegi de ("Kâr payi yok") kelime kullaniyor."""
    ozet = kampanya_avantajini_olustur({"kar_payi_orani_percent": 0.0})
    assert ozet == "kâr payı yok (%0)"


def test_avantaj_ozeti_banka_ozel_odul_birimini_korur():
    ozet = kampanya_avantajini_olustur(
        {"odul_miktari": 1250.0, "odul_birimi": "Worldpuan"}
    )
    assert ozet == "1.250 Worldpuan ödül"


def test_avantaj_ozeti_yuvarlanan_ondaligi_bozuk_yazmaz():
    """2.001 iki basamaga yuvarlandiginda ondalik '00' olur; kirpilinca
    bosalir ve naif bir birlestirme '2,' gibi bozuk metin uretirdi."""
    assert kampanya_avantajini_olustur({"kar_payi_orani_percent": 2.001}) == (
        "%2 kâr payı oranı"
    )
    assert kampanya_avantajini_olustur({"odul_miktari": 1500.5, "odul_birimi": "TL"}) == (
        "1.500,5 TL ödül"
    )


def test_avantaj_ozeti_sayisal_olmayan_degerde_PATLAMAZ():
    """REGRESYON: ozet, uc katmanin (regex/NER/LLM) ortak ciktisi uzerinde
    calisir ve sayisal alanlarda her zaman sayi bulunacaginin garantisi
    yoktur (bkz. llm_extractor._llm_sayisini_dogrula - ayni sorunun
    cikarim tarafindaki karsiligi).

    Tip kontrolu olmadan bir string bicimlendirme sirasinda ValueError
    firlatir ve TEK bir kampanyanin bozuk verisi TUM zenginlestirme
    calistirmasini dusururdu. Bozuk alan sessizce atlanmali, saglam
    alanlar ozete girmeye devam etmeli."""
    ozet = kampanya_avantajini_olustur(
        {
            "kar_payi_orani_percent": "sahte-deger",
            "finansman_tutari": ["liste"],
            "odul_miktari": None,
            "taksit_sayisi": 6,
        }
    )
    assert ozet == "6 taksit"


def test_avantaj_ozeti_bool_degeri_sayi_saymaz():
    """Python'da True == 1; tip kontrolu bool'u disarida birakmazsa
    "1 taksit" gibi uydurma bir ifade uretilirdi."""
    assert kampanya_avantajini_olustur({"taksit_sayisi": True}) is None


def test_avantaj_ozeti_hicbir_alan_yoksa_None_doner():
    """Uydurma ozet URETILMEZ - hicbir alan cikarilamadiysa alan bos kalir
    (rapor Bolum 5.7/15)."""
    assert kampanya_avantajini_olustur({}) is None
    assert kampanya_avantajini_olustur({"kar_payi_orani_percent": None}) is None


def test_avantaj_ozeti_yalnizca_dolu_alanlari_icerir():
    ozet = kampanya_avantajini_olustur(
        {"taksit_sayisi": 12, "vade_ay": None, "odul_miktari": None}
    )
    assert ozet == "12 taksit"


def test_avantaj_ozeti_masrafsizligi_ekler():
    ozet = kampanya_avantajini_olustur({"taksit_sayisi": 6, "tahsis_ucreti": 0.0})
    assert ozet == "6 taksit, masraf alınmıyor"


def test_avantaj_ozeti_kaydi_cikar_ciktisinda_dolu_gelir():
    """Uctan uca: ham metin -> kaydi_cikar -> kampanya_avantaji dolu."""
    r = kaydi_cikar("12 aya varan taksit ve 1.250 TL Worldpuan hediye firsati.")
    assert r["kampanya_avantaji"] is not None
    assert "12 taksit" in r["kampanya_avantaji"]


def test_avantaj_ozeti_genel_guven_ortalamasini_bozmaz():
    """Derlenen alan `_izler`e YAZILMAZ - kendi kaynak span'i yoktur ve
    guven ortalamasini suni sekilde sismemelidir."""
    r = kaydi_cikar("12 aya varan taksit firsati.")
    assert r["kampanya_avantaji"] is not None
    assert "kampanya_avantaji" not in r["_izler"]

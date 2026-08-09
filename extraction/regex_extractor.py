"""Regex Tabanli Bilgi Cikarim Motoru (Faz 1 - deterministik katman).

Sartname madde 5.3 "Finansal Bilgi Cikarimi" ve 5.4 "Kampanya Turunun
Belirlenmesi" icin LLM'siz, tamamen deterministik bir temel katman.

NEDEN ONCE BU: Jüri demosunda internet/GPU olmasa bile CALISIR (fallback
garantisi). Nihai mimaride "Regex Pre-filter -> Timeout -> Regex Fallback"
katmani zaten budur. Hizli iterasyon: yeni banka metni geldiginde kaliplari
burada test edip sonra NER/LLM katmanina gecilebilir.

KAYNAK: Bu desenler, Kick-off oncesi (11 Temmuz 2026) 8 banka + T.O.M.
Bank'tan alinan gercek kampanya metinleriyle test edilerek gelistirildi
(rapor Bolum 5.2/5.5 kapsaminda). Md. 8 (proje kodu Kick-off sonrasi
yazilir) geregi, kod BU depoya Kick-off SONRASI commit edilmistir - mentor
ile netlestirildi: onemli olan commit tarihinin Kick-off sonrasi olmasidir.
Desenlerin arkasindaki bulgular (ornegin "12 aya varan taksit vade DEGIL,
taksit sayisidir") ayri ayri gercek banka sayfalari uzerinden dogrulandi.
"""

import re
from typing import Optional

from extraction.normalizer import aya_cevir, tarihe_cevir, tutara_cevir, turkce_kucult, yuzdeye_cevir

# --- Kalip kutuphanesi -----------------------------------------------------
# Her kalip, gercek banka kampanya metinlerinden turetildi (bkz. dosya basi
# aciklamasi). Yorumlar, hangi banka/senaryonun bu kalibi gerekli kildigini
# belgeler - boylece bir kalip degistirildiginde hangi gercek ornegin
# bozulabilecegi onceden bilinir.

# Kar payi orani kalibi "kar pay"/"kar oran" baglamini ZORUNLU kilar. Neden?
# "tahsis ucreti finansman tutarinin %0,5'idir" gibi ifadeler kar payi orani
# SANILABILIYOR (yanlis pozitif). Tam sayi yuzdeler de desteklenir (%0, %5
# gibi; "kar paysiz" kampanyalarda oran gercekten 0 olabiliyor).
# NOT: gercek banka metinlerinde "kar payi" kadar sik "kar orani" da
# geciyor (ör. Kuveyt Turk: "Aylik kar orani %1,99") - ikisi de kapsanir.
RE_KAR_PAYI_SAYI_ONCE = re.compile(
    r"%\s*\d{1,2}(?:[.,]\d{1,4})?(?=[^%\n]{0,25}k[aâ]r\s*(?:pay\w*|oran\w*))", re.IGNORECASE
)
RE_KAR_PAYI_BAGLAM_ONCE = re.compile(
    r"k[aâ]r\s*(?:pay\w*|oran\w*)[^%\n]{0,25}%\s*\d{1,2}(?:[.,]\d{1,4})?", re.IGNORECASE
)
RE_KAR_PAYSIZ = re.compile(r"k[aâ]r\s*pays[ıi]z", re.IGNORECASE)
# "0 kar payli" gibi yuzde isareti OLMADAN sifir oran ifadeleri de var.
RE_KAR_PAYI_SIFIR = re.compile(r"\b0\s*k[aâ]r\s*pay\w*", re.IGNORECASE)
# "Vade farksiz" (katilim bankaciliginda "vade farki" gelenek faiz kavramina
# karsilik gelir - farksiz olmasi kar payi oraninin o islem icin 0 oldugu
# anlamina gelir). Gercek veride en yaygin sifir-oran ifadesi budur (62
# Altin Veri Seti kaydindan 13'unde gorulmustur).
RE_VADE_FARKSIZ = re.compile(r"vade\s*farks[ıi]z", re.IGNORECASE)
# Dusuk guvenli fallback: kisa kampanya basliklarinda "kar payi" kelimesi
# hic gecmeden sadece "%X oranla" denebiliyor. Bu durumda, yakininda ucret/
# masraf/maliyet baglami YOKSA genel yuzdeyi kar payi say (dusuk guven).
RE_KAR_PAYI_GENEL = re.compile(r"%\s*\d{1,2}(?:[.,]\d{1,4})?", re.IGNORECASE)
_UCRET_BAGLAM_DISLAMA_KELIMELERI = [
    "ücret", "masraf", "komisyon", "vergi", "bsmv", "kkdf",
    "peşinat", "ekspertiz", "tahsis", "indirim", "stopaj", "maliyet",
    # "iade": nakit iade/cashback yuzdesi kar payi orani DEGILDIR (ör.
    # "restoran harcamasinda %10 iade" - TOM-002'de bu yuzden kar payi
    # oranina yanlislikla eslesiyordu).
    "iade",
]


def _ucret_baglaminda_mi(metin: str, baslangic: int, bitis: int, pencere: int = 45) -> bool:
    sol = turkce_kucult(metin[max(0, baslangic - pencere):baslangic])
    sag = turkce_kucult(metin[bitis:bitis + pencere])
    return any(k in sol or k in sag for k in _UCRET_BAGLAM_DISLAMA_KELIMELERI)


# Vade ve taksit sayisi gercek banka verisinde SIK KARISIYOR ("12 aya varan
# taksit" bir TAKSIT SAYISIdir, vade DEGIL; "2 ay ertelemeli" ise bambaska
# bir kavramdir - erteleme suresi). Bu yuzden vade kalibi, taksit/erteleme
# baglamiyla catismayacak sekilde "kadar"/"vade(li)" ifadelerine baglandi.
RE_VADE = re.compile(
    r"\d{1,3}\s*ay(?:a)?\s*kadar(?!\s*(?:taksit|varan taksit))(?:\s*vade(?:ye kadar)?)?\s*(?:konut|araç|taşıt|ihtiyaç)?\s*finansman\w*"
    r"|\d{1,3}\s*ay\s*vade(?:ye kadar|li)?"
    r"|\d{1,3}\s*aya?\s*varan\s*vade\w*"
    r"|vade\w*\s+\d{1,3}\s*ay\b"
    # "vade suresi ... 36 aydir" gibi aralarinda 1-3 kelime olabilen
    # bicimler (ör. "uygulanacak maksimum vade suresi 36 aydir"). Sondaki
    # \b KASITLI OLARAK yok - "aydir/aydan" gibi Turkce eklerde "ay" ile
    # ek arasinda kelime siniri OLUSMAZ (ikisi de harf), \b kullanilsaydi
    # bu cok yaygin cekim bicimini kacirirdik.
    r"|vade\s*s[üu]resi(?:\s+\S+){0,4}?\s+\d{1,3}\s*ay"
    r"|\d{1,2}\s*y[ıi]l(?:a kadar)?\s*vade",
    re.IGNORECASE,
)

# "ertelemeli", "oteleme" ve "odemesiz donem" es anlamli - vade DEGIL,
# ayri bir kavram. Baglac kelimesi banka bazinda degisiyor.
RE_ERTELEME = re.compile(
    r"\d{1,2}\s*ay\w*\s*(?:kadar|varan)?\s*(?:ertelemeli|öteleme\w*|ödemesiz\s*dönem)",
    re.IGNORECASE,
)

RE_TAKSIT_SAYISI = re.compile(
    r"\d{1,3}\s*aya?\s*varan\s*taksit\w*"
    r"|\d{1,3}\s*ay\s*taksit\w*"
    r"|\d{1,3}\s*taksit(?:li|le)?\b",
    re.IGNORECASE,
)

# Finansman tutari - gercek veride iki ana kalip: tekli ust limit
# ("100.000 TL'ye kadar") ve aralik ("1.000 TL - 100.000 TL arasi").
RE_TUTAR_ARALIK = re.compile(
    r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*TL\s*[-–]\s*(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*TL\s*aras",
    re.IGNORECASE,
)
RE_TUTAR_UST_LIMIT = re.compile(
    r"\d{1,3}(?:\.\d{3})*(?:,\d+)?\s*TL['’]?(?:ye|ya)?\s*kadar", re.IGNORECASE
)

_TR_AY_ADLARI = r"Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık"
RE_TARIH = re.compile(
    rf"\d{{1,2}}[./]\d{{1,2}}[./]\d{{4}}|\d{{1,2}}\s+(?:{_TR_AY_ADLARI})\s+\d{{4}}", re.IGNORECASE
)
RE_TARIH_ARALIGI = re.compile(
    rf"(\d{{1,2}}\s+(?:{_TR_AY_ADLARI})\s+\d{{4}})\s*[-–]\s*(\d{{1,2}}\s+(?:{_TR_AY_ADLARI})\s+\d{{4}})",
    re.IGNORECASE,
)

# --- Masraf / ucret -------------------------------------------------------
# BU DESENLER 234 GERCEK BELGE TARANARAK YAZILDI. Ilk surumde yalnizca
# asagidaki RE_MASRAFSIZ vardi ve sartnamenin YAPAY ornegindeki cumleden
# ("dosya masrafi alinmamaktadir") turetilmisti - gercek korpusta
# "masraf alinm"/"ucret alinm" ifadesi HIC gecmiyor, bu yuzden
# masraf_durumu 234 belgenin 0'inda doluyordu (olculdu).
#
# GURULTU TUZAGI - "ucretsiz" TEK BASINA ASLA TETIKLEMEZ:
# Korpusta "ucretsiz" 90+ kez geciyor ama neredeyse hepsi kampanyanin
# masraf durumuyla ILGISIZ:
#   "Ucretsiz ve ticari kredi kartlarimiz kampanyaya dahil degildir" (50x)
#   "Katilim SMS'i ucretsiz olup..."                                  (27x)
#   "...otuz (30) gun icinde ucretsiz olarak sonuclandirilmaktadir"    (10x, KVKK)
# Bu yuzden desenler, bir MASRAF KELIMESI (masraf/tahsis/komisyon/aidat)
# gecmesini ZORUNLU kilar. Boylece yukaridaki 87 yanlis pozitifin hicbiri
# eslesmez.
#
# AKSAN TOLERANSI: "ücret" ve "ü/ı/ş" iceren tum masraf kelimeleri
# aksansiz da yazilabiliyor - PDF/OCR kaynakli metinlerde aksan kaybi
# bilinen bir sorundur (bkz. ner_extractor.py, Bulgu 4). Desenler bu
# yuzden hem "ücreti" hem "ucreti" bicimini kabul eder.
RE_MASRAFSIZ = re.compile(
    r"(dosya masraf[ıi]|tahsis [üu]creti|ekspertiz [üu]creti)[^.]{0,40}?"
    r"(al[ıi]nmamaktad[ıi]r|al[ıi]nm[ıi]yor|al[ıi]nmaz|kar[şs][ıi]lanmaktad[ıi]r"
    r"|kar[şs][ıi]lan[ıi]yor|[üu]cretsiz|yoktur|yok)",
    re.IGNORECASE,
)
# IKI GUVEN KADEMESI - "cikardik" ile "sifir oldugunu IDDIA ediyoruz" ayri:
#
# GUCLU: masrafin gercekten alinmadigini soyleyen, baglamli ifadeler.
# Yalnizca BUNLAR tahsis_ucreti=0.0 atar, cunku o alan karsilastirmada
# SIRALAMAYI belirler - yanlis bir 0.0 kampanyayi haksiz yere birinci yapar.
# Gercek veriden: "yeni musterilere ozel dosya masrafsizlik avantaji"
# (Turkiye Finans), "Yeni Yatirim Hesabiniza Sifir Komisyon Orani",
# "aidatsiz Happy Bonus Zero kredi karti" (Altin Veri Seti TF-007).
RE_MASRAF_SIFIR_GUCLU = re.compile(
    r"(?:dosya|tahsis|ekspertiz)\s*masrafs[ıi]z\w*"
    r"|masrafs[ıi]zl[ıi]k\w*"
    r"|s[ıi]f[ıi]r\s*komisyon\w*"
    r"|komisyon\s*(?:al[ıi]nmaz|al[ıi]nmamaktad[ıi]r|yoktur)"
    r"|aidats[ıi]z\b",
    re.IGNORECASE,
)
# ZAYIF: baglamsiz, tek basina gecen "Masrafsiz". Gercek veride bu, iki
# belgede TEK BASINA BIR SATIRDA duruyor (gezinme menusu/urun etiketi:
# "Masrafsiz Bankacilik", "Masrafsiz Banka ve Kredi Karti") - kampanyanin
# masraf durumu hakkinda bir iddia DEGIL. Bu yuzden yalnizca serbest metin
# alanina (masraf_durumu) yazilir, tahsis_ucreti BOS BIRAKILIR: bilgiyi
# gizlemeyiz ama uzerine sayisal bir iddia da kurmayiz.
RE_MASRAF_SIFIR_ZAYIF = re.compile(r"masrafs[ıi]z\w*", re.IGNORECASE)
# Tahsis ucreti gercek veride TL TUTARI OLARAK DEGIL, ORAN olarak
# ifade ediliyor: "Tahsis ucreti vergiler haric finansman tutarinin
# binde 5'i oranindadir" (Turkiye Finans, korpustaki tek gercek ornek).
# Bu ifade masraf_durumu'na METIN olarak yazilir; tahsis_ucreti (TL)
# alanina CEVRILMEZ - bkz. kaydi_cikar icindeki gerekce.
RE_TAHSIS_ORANI = re.compile(
    r"tahsis [üu]creti[^.\n]{0,80}?(?:binde|y[üu]zde|%)\s*\d{1,3}(?:[.,]\d+)?[^.\n]{0,25}",
    re.IGNORECASE,
)
# Acikca TL tutari verilmis masraf ("dosya masrafi 500 TL") - korpusta
# henuz gorulmedi ama bankadan bankaya degistigi icin desen hazir tutulur.
RE_MASRAF_TUTARI = re.compile(
    r"(?:dosya masraf[ıi]|tahsis [üu]creti|ekspertiz [üu]creti)\s*[:=]?\s*"
    r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*(?:TL|₺)",
    re.IGNORECASE,
)

# Odul ifadeleri cok cesitli: "5.000 TL degerinde alisveris ceki",
# "10.000 Mil'e varan hediye" (TL disi birim!), "250 TL ParafPara",
# "2.000 TL'ye varan Bankkart Lira" (banka-ozel sadakat birimleri),
# "1.000 TL'ye kadar iade", "1.250 TL Worldpuan".
# NOT: "nakit ödül"/"ödül" bilerek BURAYA eklenmedi - bu kelimeler genelde
# kisi-basi/birim tutari da tasir (ör. "500 TL nakit ödül... toplamda
# maksimum 10.000 TL"), .search() ILK eslesmeyi aldigi icin erken/yanlis
# (kisi basi) tutari yakalardi. Bu durumlar asagidaki RE_ODUL_TAVAN
# ("en fazla"/"maksimum" tetikleyicili) desenine birakildi.
RE_ODUL = re.compile(
    r"\d{1,3}(?:\.\d{3})*(?:,\d+)?\s*(?:TL|₺)"
    r"(?:['’](?:ye|ya|e|a))?\s*"
    r"(?:değerinde\s*|varan\s*|kadar\s*)?"
    r"(?:alışveriş çeki|alışveriş kartı|hediye çeki|alışveriş puanı|hediye|kazan\w*"
    r"|indirim|bankkart lira|parafpara|worldpuan|nakit iade\w*|iade\b)",
    re.IGNORECASE,
)
# Banka-ozel sadakat birimleri (Mil, Gram) TL disinda oldugu icin ayri
# desenler gerekir. NOT: gercek metinlerde egik/tipografik apostrof (’,
# U+2019) kullanilir, duz apostrof (') degil - ikisi de kapsanmali.
RE_ODUL_MIL = re.compile(r"\d{1,3}(?:\.\d{3})*(?:,\d+)?\s*Mil['’]?[ea]?\s*varan\s*hediye", re.IGNORECASE)
# Tavan/limit ifadeleri: "en fazla 5 gram", "maksimum 10.000 TL", "kişi
# başı maksimum 2.000 TL, toplamda ... maksimum 10.000 TL nakit ödül" gibi
# cok sayida aday oldugunda SONUNCUSU (genelde "toplamda" olan) tercih
# edilir - finditer + son eslesme.
RE_ODUL_TAVAN = re.compile(
    r"(?:en fazla|maksimum)\s+(?:\S+\s+){0,4}?"
    r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*(TL|₺|gram\w*|gr\b)",
    re.IGNORECASE,
)
# "2.500 TL ile sınırlıdır" gibi "sinirli/sinirlidir" ile biten tavan ifadesi.
RE_ODUL_SINIRLI = re.compile(
    r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*(TL|₺)['’]?\s*(?:ile\s+)?s[ıi]n[ıi]rl[ıi]",
    re.IGNORECASE,
)
RE_ODUL_GRAM = re.compile(
    r"\d{1,3}(?:,\d+)?\s*gram\w*\s*(?:['’]?[ea]?\s*kadar\s*)?(?:hediye|kazan\w*)", re.IGNORECASE
)

# Kampanya turu anahtar kelimeleri - degerler api/schemas.py KampanyaTuru
# enum'iyla BIREBIR ayni olmali (Havin/Sara'nin sozlesmesi bozulmasin diye).
KAMPANYA_TURU_ANAHTAR_KELIMELERI = {
    "Konut Finansmani Kampanyasi": ["konut finansman", "ev sahibi", "konut alım"],
    "Tasit Finansmani Kampanyasi": ["taşıt finansman", "araç finansman", "otomobil"],
    "Ihtiyac Finansmani Kampanyasi": ["ihtiyaç finansman"],
    "Kart Kampanyasi": ["kredi kart", "kart avantaj", "kart kampanya", "bankkart"],
    "Alisveris Puani Kampanyasi": ["alışveriş puan", "puan kazan", "parafpara"],
    "Yeni Musteri Kampanyasi": ["yeni müşteri", "yeni ev sahibi olmak isteyen"],
    "Yatirim Urunu Kampanyasi": ["katılım fonu", "yatırım ürün", "birikim"],
    "Finansman Kampanyasi": ["finansman"],
}

HEDEF_KITLE_ANAHTAR_KELIMELERI = {
    "Yeni müşteri": ["yeni müşteri", "yeni ev sahibi olmak isteyen"],
    "Mevcut müşteri": ["mevcut müşteri"],
    "Maaş müşterisi": ["maaş müşteri", "maaş getiren"],
}


def _kar_payi_makul_mu(percent: float) -> bool:
    """Aylik kar payi oranlari gercek veride %0-%10 araliginda gozlemlendi
    (bkz. gold_dataset). %15 ustu bir deger, kodlama bozulmasi (mojibake)
    veya baska bir sayinin (tutar, yil vb.) yanlislikla eslenmesidir - bu
    yuzden ATANMAZ (rapor Bolum 5.7/15: supheli deger, uydurmaktan iyidir
    None birakmak)."""
    return 0.0 <= percent <= 15.0


def _kar_payi_ata(alanlar: dict, izler: dict, span: str, guven: float) -> bool:
    oran = yuzdeye_cevir(span)
    if oran is None or not _kar_payi_makul_mu(round(oran * 100, 4)):
        return False
    alanlar["kar_payi_orani_decimal"] = oran
    alanlar["kar_payi_orani_percent"] = round(oran * 100, 4)
    izler["kar_payi_orani_percent"] = (span, guven)
    return True


def _ilk_eslesme(desen: re.Pattern, metin: str) -> Optional[str]:
    m = desen.search(metin)
    return m.group(0) if m else None


def _odul_birimini_tespit_et(eslesen_metin: str) -> str:
    """RE_ODUL'un eslesen metninde HANGI banka-ozel sadakat biriminin
    gectigini tespit eder. Eskiden bu fonksiyon yoktu, RE_ODUL eslestigi
    surece odul_birimi kosulsuz "TL" atanirdi - bu yuzden Bankkart Lira/
    ParafPara/Worldpuan gibi TL-disi birimler bile yanlislikla "TL" olarak
    kaydediliyordu (Extraction Accuracy raporu, 18/40 hata)."""
    metin_l = turkce_kucult(eslesen_metin)
    if "bankkart lira" in metin_l:
        return "Bankkart Lira"
    if "parafpara" in metin_l:
        return "ParafPara"
    if "worldpuan" in metin_l:
        return "Worldpuan"
    return "TL"


def _kampanya_turunu_tespit_et(metin: str) -> Optional[str]:
    metin_l = turkce_kucult(metin)
    for etiket, kelimeler in KAMPANYA_TURU_ANAHTAR_KELIMELERI.items():
        if any(k in metin_l for k in kelimeler):
            return etiket
    return None


def _hedef_kitleyi_tespit_et(metin: str) -> Optional[str]:
    metin_l = turkce_kucult(metin)
    for etiket, kelimeler in HEDEF_KITLE_ANAHTAR_KELIMELERI.items():
        if any(k in metin_l for k in kelimeler):
            return etiket
    return None


def _tr_sayi(deger: float) -> str:
    """5000.0 -> '5.000', 1500.5 -> '1.500,5' (Turkce binlik/ondalik ayirac).

    Ondalik kismi iki basamaga yuvarlandiktan sonra sifira inebilir
    (ornek: 2.001 -> '2.00'); bu durumda ondalik hic yazilmaz - aksi
    halde '2,' gibi bozuk bir metin uretilirdi.
    """
    if deger == int(deger):
        return f"{int(deger):,}".replace(",", ".")
    tam, ondalik = f"{deger:,.2f}".split(".")
    ondalik = ondalik.rstrip("0")
    tam = tam.replace(",", ".")
    return f"{tam},{ondalik}" if ondalik else tam


def _sayi_ya_da_none(deger) -> Optional[float]:
    """Yalnizca GERCEK sayilari kabul eder; digerlerinde None doner.

    NEDEN GEREKLI: avantaj ozeti, uc katmanin (regex/NER/LLM) ortak
    ciktisi uzerinde calisir ve o alanlarda her zaman sayi bulunacaginin
    garantisi YOKTUR - llm_extractor.py'nin `_llm_sayisini_dogrula`
    guard'i tam da bu yuzden var. Tip kontrolu olmadan bir string,
    bicimlendirme sirasinda ValueError firlatir ve TEK bir kampanyanin
    bozuk verisi TUM zenginlestirme calistirmasini dusururdu.
    Bu fonksiyon sessizce atlar: ozet o alani icermez, cikarim devam eder.
    """
    if isinstance(deger, bool) or not isinstance(deger, (int, float)):
        return None
    return float(deger)


def kampanya_avantajini_olustur(alanlar: dict) -> Optional[str]:
    """Cikarilan yapilandirilmis alanlardan kisa bir avantaj ozeti DERLER.

    BU BIR CIKARIM DEGIL, DERLEMEDIR - ve bu ayrim bilerek yapildi:

    Sartname Md. 5.3'un bekledigi "Kampanya Avantaji" alani, Senaryo-1
    tablosunda kisa ve yapisal ifadelerle gosteriliyor ("5.000 TL alisveris
    ceki", "50.000 TL'ye kadar masraf alinmiyor") - yani zaten cikardigimiz
    alanlarin insan okunur birlesimi.

    NEDEN METINDEN CIKARILMIYOR: Altin Veri Seti'ndeki 58 kaydin
    kampanya_avantaji sutunu ELLE YAZILMIS ozetlerden olusuyor ve cogu
    aritmetik/sentez iceriyor (ornek AL-004: "Her davet edilen ... icin
    500 TL, toplamda 5.000 TL'ye varan Worldpuan"). Boyle bir ozeti ham
    metinden regex ile uretmek mumkun degil; LLM ile uretmek ise SERBEST
    METIN uretmek olurdu - Verifier (validation/verifier.py) sayisal
    iddialari dogruluyor ama uretilmis serbest metnin TAMAMINI
    dogrulamiyor, bu yuzden ozet uretimi hala bilerek deterministik
    tutulur.

    Bu yuzden ozet YALNIZCA dogrulanmis alanlardan, sabit bir sablonla
    kurulur: uydurulacak hicbir yer yoktur, her parcasi bir alana
    geri izlenebilir. Hicbir alan yoksa None doner.
    """
    parcalar: list[str] = []

    oran = _sayi_ya_da_none(alanlar.get("kar_payi_orani_percent"))
    if oran is not None:
        parcalar.append(
            "kâr payı yok (%0)" if oran == 0 else f"%{_tr_sayi(oran)} kâr payı oranı"
        )

    tutar = _sayi_ya_da_none(alanlar.get("finansman_tutari"))
    if tutar is not None:
        parcalar.append(f"{_tr_sayi(tutar)} TL'ye kadar finansman")

    for alan, sablon in (
        ("vade_ay", "{} ay vade"),
        ("taksit_sayisi", "{} taksit"),
        ("erteleme_suresi_ay", "{} ay ödemesiz dönem"),
    ):
        sayi = _sayi_ya_da_none(alanlar.get(alan))
        if sayi is not None:
            parcalar.append(sablon.format(int(sayi)))

    odul = _sayi_ya_da_none(alanlar.get("odul_miktari"))
    if odul is not None:
        birim = alanlar.get("odul_birimi")
        birim = birim if isinstance(birim, str) and birim.strip() else "TL"
        parcalar.append(f"{_tr_sayi(odul)} {birim} ödül")

    if _sayi_ya_da_none(alanlar.get("tahsis_ucreti")) == 0.0:
        parcalar.append("masraf alınmıyor")

    return ", ".join(parcalar) if parcalar else None


def kaydi_cikar(ham_metin: str) -> dict:
    """Tek bir kampanya metnini analiz edip api/schemas.py CampaignRecord
    ile UYUMLU alan adlariyla bir sozluk doner.

    Bulunamayan alanlar None kalir - UYDURMA DEGER URETILMEZ (rapor Bolum
    5.7/15). `_izler` alani, hangi alanin hangi metin parcasindan ve hangi
    guvenle cikarildigini tasir (Juri Audit Paneli / hata ayiklama icin).
    """
    alanlar: dict = {
        "kar_payi_orani_percent": None,
        "kar_payi_orani_decimal": None,
        "finansman_tutari": None,
        "vade_ay": None,
        "taksit_sayisi": None,
        "erteleme_suresi_ay": None,
        "odul_miktari": None,
        "odul_birimi": None,
        "masraf_durumu": None,
        "tahsis_ucreti": None,
        "kampanya_avantaji": None,
        "kampanya_baslangic": None,
        "kampanya_bitis": None,
        "kampanya_turu": None,
        "hedef_kitle": None,
    }
    izler: dict[str, tuple[str, float]] = {}  # alan -> (kaynak_span, guven)

    # --- Kar payi orani -----------------------------------------------
    m = RE_KAR_PAYI_SAYI_ONCE.search(ham_metin)
    if m and _kar_payi_ata(alanlar, izler, m.group(0), 0.9):
        pass
    else:
        m = RE_KAR_PAYI_BAGLAM_ONCE.search(ham_metin)
        sayi_m = re.search(r"%\s*\d{1,2}(?:[.,]\d{1,4})?", m.group(0)) if m else None
        if sayi_m and _kar_payi_ata(alanlar, izler, sayi_m.group(0), 0.9):
            pass
        elif RE_KAR_PAYSIZ.search(ham_metin) or RE_KAR_PAYI_SIFIR.search(ham_metin):
            alanlar["kar_payi_orani_decimal"] = 0.0
            alanlar["kar_payi_orani_percent"] = 0.0
            izler["kar_payi_orani_percent"] = ("kâr paysız / 0 kâr paylı", 0.85)
        elif RE_VADE_FARKSIZ.search(ham_metin):
            # "Vade farksiz" katilim bankaciliginda o islem icin kar payi
            # oraninin 0 oldugu anlamina gelir (Extraction Accuracy raporu +
            # terminology/sozluk.json'daki sifir_oran_ifadesi kavramiyla
            # tutarli). Dogrudan "kar paysiz" kadar yuksek guvenli degil
            # (0.8 < 0.85) - farkli bir ifade oldugu icin.
            alanlar["kar_payi_orani_decimal"] = 0.0
            alanlar["kar_payi_orani_percent"] = 0.0
            izler["kar_payi_orani_percent"] = ("vade farksız", 0.8)
        else:
            for gm in RE_KAR_PAYI_GENEL.finditer(ham_metin):
                if not _ucret_baglaminda_mi(ham_metin, gm.start(), gm.end()):
                    if _kar_payi_ata(alanlar, izler, gm.group(0), 0.6):
                        break

    # --- Finansman tutari ----------------------------------------------
    m = RE_TUTAR_ARALIK.search(ham_metin)
    if m:
        alanlar["finansman_tutari"] = tutara_cevir(m.group(2))
        izler["finansman_tutari"] = (m.group(0), 0.85)
    else:
        m = RE_TUTAR_UST_LIMIT.search(ham_metin)
        if m:
            alanlar["finansman_tutari"] = tutara_cevir(m.group(0))
            izler["finansman_tutari"] = (m.group(0), 0.75)

    # --- Vade / taksit sayisi / erteleme suresi (UC AYRI kavram) -------
    span = _ilk_eslesme(RE_VADE, ham_metin)
    if span:
        alanlar["vade_ay"] = aya_cevir(span)
        izler["vade_ay"] = (span, 0.85)

    span = _ilk_eslesme(RE_ERTELEME, ham_metin)
    if span:
        alanlar["erteleme_suresi_ay"] = aya_cevir(span)
        izler["erteleme_suresi_ay"] = (span, 0.85)

    span = _ilk_eslesme(RE_TAKSIT_SAYISI, ham_metin)
    if span:
        sayi_m = re.search(r"\d+", span)
        alanlar["taksit_sayisi"] = int(sayi_m.group(0)) if sayi_m else None
        izler["taksit_sayisi"] = (span, 0.85)

    # --- Odul miktari/birimi -------------------------------------------
    m = RE_ODUL_MIL.search(ham_metin)
    if m:
        alanlar["odul_miktari"] = tutara_cevir(m.group(0))
        alanlar["odul_birimi"] = "Mil"
        izler["odul_miktari"] = (m.group(0), 0.8)
    else:
        m = RE_ODUL_GRAM.search(ham_metin)
        if m:
            alanlar["odul_miktari"] = tutara_cevir(m.group(0))
            alanlar["odul_birimi"] = "Gram"
            izler["odul_miktari"] = (m.group(0), 0.8)
        else:
            m = RE_ODUL.search(ham_metin)
            if m:
                alanlar["odul_miktari"] = tutara_cevir(m.group(0))
                # ONCEDEN: kosulsuz "TL" atanirdi - Bankkart Lira/ParafPara/
                # Worldpuan gibi TL-disi birimler yanlis kaydediliyordu.
                alanlar["odul_birimi"] = _odul_birimini_tespit_et(m.group(0))
                izler["odul_miktari"] = (m.group(0), 0.8)
            else:
                # Yukaridaki "varan/kadar/degerinde + anahtar kelime"
                # kaliplarinin hicbiri eslesmediyse, tavan/limit ifadelerini
                # dene ("en fazla 5 gram", "maksimum 10.000 TL nakit odul",
                # "2.500 TL ile sinirlidir"). Bunlar dusuk-orta guvenlidir
                # cunku hangi tutarin "asil" oldugu yorum gerektirebilir.
                #
                # BIRDEN FAZLA aday olabilir (gunluk/aylik/kisi-basi ARA
                # basamak tavanlari + nihai toplam) ve hangisinin "asil"
                # oldugu ifadeye gore degisir (ör. TOM-001'de son gecen
                # "sinirlidir" dogru toplamdir; HF-004'te ise metnin
                # BASKA bir yerindeki alakasiz "500 TL ile sinirli" ifadesi
                # "maksimum 10.000 TL"den KUCUK ve yanlis olurdu). Ara
                # basamak tavanlari tanim geregi nihai toplamdan KUCUK
                # olacagi icin, tum adaylar arasindan EN BUYUK degerli
                # olan secilir - bu iki gercek ornekte de dogru sonucu verir.
                adaylar: list[tuple[float, str, str]] = []  # (tutar, birim, span)
                m = RE_ODUL_SINIRLI.search(ham_metin)
                if m:
                    tutar = tutara_cevir(m.group(1))
                    if tutar is not None:
                        adaylar.append((tutar, "TL", m.group(0)))
                for tm in RE_ODUL_TAVAN.finditer(ham_metin):
                    tutar = tutara_cevir(tm.group(1))
                    if tutar is not None:
                        birim_ham = turkce_kucult(tm.group(2))
                        birim = "Gram" if birim_ham.startswith("gr") else "TL"
                        adaylar.append((tutar, birim, tm.group(0)))
                if adaylar:
                    tutar, birim, span = max(adaylar, key=lambda a: a[0])
                    alanlar["odul_miktari"] = tutar
                    alanlar["odul_birimi"] = birim
                    izler["odul_miktari"] = (span, 0.7)

    # --- Masraf bilgisi / tahsis ucreti -----------------------------------
    # Uc kademe: (1) acik TL tutari, (2) acik "masraf alinmaz" ifadesi,
    # (3) oran olarak verilmis tahsis ucreti. Ilk eslesen kazanir.
    m = RE_MASRAF_TUTARI.search(ham_metin)
    if m:
        tutar = tutara_cevir(m.group(1))
        if tutar is not None:
            alanlar["masraf_durumu"] = m.group(0)
            alanlar["tahsis_ucreti"] = tutar
            izler["masraf_durumu"] = (m.group(0), 0.85)
    else:
        span = _ilk_eslesme(RE_MASRAFSIZ, ham_metin) or _ilk_eslesme(
            RE_MASRAF_SIFIR_GUCLU, ham_metin
        )
        if span:
            alanlar["masraf_durumu"] = span
            # "Masraf alinmaz" = tahsis ucreti 0 TL. Bu, karsilastirmanin
            # "en_dusuk_masraf" kriterinin (sartname Md. 5.7) siraladigi
            # alandir - doldurulmazsa o kriter HICBIR ZAMAN sonuc uretemez
            # (olculdu: tahsis_ucreti 234 belgenin 0'inda doluydu).
            alanlar["tahsis_ucreti"] = 0.0
            izler["masraf_durumu"] = (span, 0.8)
        else:
            span = _ilk_eslesme(RE_TAHSIS_ORANI, ham_metin)
            if span:
                # ORAN, TUTAR DEGIL: "finansman tutarinin binde 5'i" bir
                # yuzdedir; tahsis_ucreti alani TL bekler. Orani finansman
                # tutariyla carpip TL uretmek IKI belirsizligi birlestirir
                # (ikisi de cikarilmis deger) ve birim hatasi riski tasir -
                # bu yuzden metin olarak saklanir, tahsis_ucreti BOS BIRAKILIR
                # (rapor Bolum 5.7/15: supheli deger yerine bos birak).
                alanlar["masraf_durumu"] = span
                izler["masraf_durumu"] = (span, 0.8)
            else:
                # Son kademe: baglamsiz "Masrafsiz". Bilgi kaydedilir ama
                # tahsis_ucreti'ne DOKUNULMAZ - bkz. RE_MASRAF_SIFIR_ZAYIF.
                span = _ilk_eslesme(RE_MASRAF_SIFIR_ZAYIF, ham_metin)
                if span:
                    alanlar["masraf_durumu"] = span
                    izler["masraf_durumu"] = (span, 0.5)

    # --- Kampanya suresi: once tarih ARALIGI, sonra tek tarih -----------
    m = RE_TARIH_ARALIGI.search(ham_metin)
    if m:
        alanlar["kampanya_baslangic"] = tarihe_cevir(m.group(1))
        alanlar["kampanya_bitis"] = tarihe_cevir(m.group(2))
        izler["kampanya_bitis"] = (m.group(0), 0.9)
    else:
        span = _ilk_eslesme(RE_TARIH, ham_metin)
        if span:
            alanlar["kampanya_bitis"] = tarihe_cevir(span)
            izler["kampanya_bitis"] = (span, 0.85)

    # --- Kampanya turu / hedef kitle (anahtar kelime siniflandirma) -----
    alanlar["kampanya_turu"] = _kampanya_turunu_tespit_et(ham_metin)
    if alanlar["kampanya_turu"]:
        izler["kampanya_turu"] = (alanlar["kampanya_turu"], 0.7)

    alanlar["hedef_kitle"] = _hedef_kitleyi_tespit_et(ham_metin)
    if alanlar["hedef_kitle"]:
        izler["hedef_kitle"] = (alanlar["hedef_kitle"], 0.7)

    # --- Kampanya avantaji (DERLEME, cikarim degil) -----------------------
    # Diger alanlarin HEPSI belirlendikten SONRA kurulur; bilerek `izler`e
    # YAZILMAZ - kendi basina bir kaynak span'i yoktur ve genel_guven_hesapla
    # ortalamasini suni sekilde sisirmemesi gerekir. Guveni, turetildigi
    # alanlarin guveni kadardir (bkz. kampanya_avantajini_olustur).
    alanlar["kampanya_avantaji"] = kampanya_avantajini_olustur(alanlar)

    alanlar["_izler"] = izler
    return alanlar


def genel_guven_hesapla(izler: dict[str, tuple[str, float]]) -> float:
    """Bulunan alanlarin guven skorlarinin ortalamasi. Hic alan
    bulunamadiysa 0.0 (rapor Bolum 5.7/15: belirsizlik gizlenmez)."""
    if not izler:
        return 0.0
    return round(sum(guven for _, guven in izler.values()) / len(izler), 4)

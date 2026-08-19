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

from extraction.normalizer import (
    aya_cevir,
    tarihe_cevir,
    turkce_ascii_katla,
    turkce_ascii_kucult,
    tutara_cevir,
    yuzdeye_cevir,
)

# --- Diyakritik katlama ----------------------------------------------------
# BULGU (olculdu, 17 Agustos): asagidaki desenler ve anahtar kelime
# listeleri Turkce diyakritiklerle yazilmis - "3 ay ödemesiz dönem" bulunuyor
# ama ayni cumlenin diyakritiksiz yazimi ("3 ay odemesiz donem") SESSIZCE
# bos donuyordu. POST /cikar ucu ve MetinAnalizi ekrani kullaniciyi serbest
# metin yapistirmaya davet ettigi icin bu, kullanicinin goremeyecegi bir
# alan kaybiydi (bkz. normalizer.turkce_ascii_katla docstring'i).
#
# COZUM - HER IKI TARAFI DA KATLA: metin de desen de ayni haritadan gecirilir,
# boylece desenler DOGAL TURKCE yazimiyla okunabilir kalir ama eslesme
# yazimdan bagimsiz olur. Katlama uzunluk KORUDUGU icin (str.translate 1:1)
# katlanmis metindeki offset'ler ham metinde ayni yeri gosterir - kanit izi
# (`izler`) ve masraf_durumu bu sayede KULLANICININ KENDI YAZIMIYLA saklanir.
#
# NOT: bazi desenlerde zaten elle yazilmis [ıi] / [şs] / [üu] / [aâ] gibi
# karakter siniflari var (aksan toleransi icin tek tek eklenmislerdi).
# Katlamadan sonra bunlar [ii] / [ss] / [uu] / [aa] haline gelir - zararsiz,
# yalnizca gereksizdir. Bilerek KALDIRILMADILAR: her biri gercek bir banka
# metnindeki bulguyu belgeliyor ve kaldirmak bu diffi gereksiz genisletirdi.


def _katlanmis_derle(desen: str, bayraklar: int = re.IGNORECASE) -> re.Pattern:
    """Deseni ASCII'ye katlayarak derler - `kaydi_cikar` da metni ayni
    sekilde katladigi icin iki taraf her zaman ayni alfabede karsilasir."""
    return re.compile(turkce_ascii_katla(desen), bayraklar)


def _katla_hepsi(kelimeler: list[str]) -> list[str]:
    """Anahtar kelime listesini katlar. Karsilastirilacak metin de
    `turkce_ascii_kucult`ten gectigi icin iki taraf ayni alfabede olur.

    Modul yuklenirken BIR KEZ calisir - katlamayi her `in` kontrolunde
    tekrarlamak, uzun banka metinlerinde bosuna is olurdu.
    """
    return [turkce_ascii_kucult(k) for k in kelimeler]


def _ham_span(ham_metin: str, m: re.Match, grup: int = 0) -> str:
    """Katlanmis metinde bulunan eslesmenin HAM metindeki karsiligi.

    Katlama uzunluk korudugu icin offset'ler birebir ortusur; boylece
    kanit izinde kullaniciya kendi yazdigi metin gosterilir (ör. metinde
    "Dosya masrafı alınmaz" yaziyorsa iz de oyle olur, "masrafi alinmaz" degil).
    """
    baslangic, bitis = m.span(grup)
    return ham_metin[baslangic:bitis]


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
RE_KAR_PAYI_SAYI_ONCE = _katlanmis_derle(
    r"%\s*\d{1,2}(?:[.,]\d{1,4})?(?=[^%\n]{0,25}k[aâ]r\s*(?:pay\w*|oran\w*))", re.IGNORECASE
)
RE_KAR_PAYI_BAGLAM_ONCE = _katlanmis_derle(
    r"k[aâ]r\s*(?:pay\w*|oran\w*)[^%\n]{0,25}%\s*\d{1,2}(?:[.,]\d{1,4})?", re.IGNORECASE
)
RE_KAR_PAYSIZ = _katlanmis_derle(r"k[aâ]r\s*pays[ıi]z", re.IGNORECASE)
# "0 kar payli" gibi yuzde isareti OLMADAN sifir oran ifadeleri de var.
RE_KAR_PAYI_SIFIR = _katlanmis_derle(r"\b0\s*k[aâ]r\s*pay\w*", re.IGNORECASE)
# "Vade farksiz" (katilim bankaciliginda "vade farki" gelenek faiz kavramina
# karsilik gelir - farksiz olmasi kar payi oraninin o islem icin 0 oldugu
# anlamina gelir). Gercek veride en yaygin sifir-oran ifadesi budur (62
# Altin Veri Seti kaydindan 13'unde gorulmustur).
RE_VADE_FARKSIZ = _katlanmis_derle(r"vade\s*farks[ıi]z", re.IGNORECASE)
# Dusuk guvenli fallback: kisa kampanya basliklarinda "kar payi" kelimesi
# hic gecmeden sadece "%X oranla" denebiliyor. Bu durumda, yakininda ucret/
# masraf/maliyet baglami YOKSA genel yuzdeyi kar payi say (dusuk guven).
RE_KAR_PAYI_GENEL = _katlanmis_derle(r"%\s*\d{1,2}(?:[.,]\d{1,4})?", re.IGNORECASE)
_UCRET_BAGLAM_DISLAMA_KELIMELERI = _katla_hepsi([
    "ücret", "masraf", "komisyon", "vergi", "bsmv", "kkdf",
    "peşinat", "ekspertiz", "tahsis", "indirim", "stopaj", "maliyet",
    # "iade": nakit iade/cashback yuzdesi kar payi orani DEGILDIR (ör.
    # "restoran harcamasinda %10 iade" - TOM-002'de bu yuzden kar payi
    # oranina yanlislikla eslesiyordu).
    "iade",
    # ODUL YUZDESI (olculdu, TEK-001): "odeme tutarinin %10'u oraninda,
    # en fazla 500 TL odul kazanabilirsiniz" - bu bir kazanim orani,
    # kar payi orani DEGIL.
    "ödül", "odul", "kazan", "hediye", "puan",
    # DAR MAKAS (olculdu, HF-005): "%0,1 dar makastan yararlanabilir" -
    # doviz/altin alim-satim spreadi. terminology/sozluk.json bunu ZATEN
    # "kar_payi_orani ILE KARISTIRILMAMALI" diye isaretlemis ama kural
    # regex'e baglanmamisti.
    "makas", "kur",
])


def _ucret_baglaminda_mi(metin: str, baslangic: int, bitis: int, pencere: int = 45) -> bool:
    sol = turkce_ascii_kucult(metin[max(0, baslangic - pencere):baslangic])
    sag = turkce_ascii_kucult(metin[bitis:bitis + pencere])
    return any(k in sol or k in sag for k in _UCRET_BAGLAM_DISLAMA_KELIMELERI)


# OLCULDU (19-20 Agustos, kar_payi_tablosu zenginlestirme calistirmasi):
# Turkiye Finans'in Ihtiyac Finansmani sayfalarinda (id=155/158/165) "Kâr
# paysız 2.500 TL'ye kadar Yedek Hesap finansman desteğinden
# yararlanabilirsiniz." cumlesi var - bu, sayfanin ANA kampanyasindan
# (kendi orani var, bkz. tablo_extractor.py) TAMAMEN AYRI, kucuk tutarli
# bir ek urunu (Yedek Hesap) anlatiyor. RE_KAR_PAYSIZ baglamsiz oldugu icin
# bunu ana kampanyanin orani saniyordu (Verifier de dogrulayamadi -
# "kar_payi_orani_percent": False olarak isaretlendi ama SILINMEDI, bkz.
# regex_ile_zenginlestir.py). "Kar paysiz" ifadesinin gercekten kampanyanin
# kendi urununu anlattigi durumlarla (ör. AL-002/VK-001 - "vade farksiz"
# kalibindan AYRI olarak dogrudan "kar paysiz" diyen kayitlar) karistirmamak
# icin sadece bu BILINEN ikincil urun adiyla sinirlandi.
_IKINCIL_URUN_BAGLAM_DISLAMA_KELIMELERI = _katla_hepsi(["yedek hesap"])


def _ikincil_urun_baglaminda_mi(metin: str, baslangic: int, bitis: int, pencere: int = 60) -> bool:
    # Gercek sayfalarda coklu bosluk/nbsp oluyor ("Yedek  Hesap") - tek
    # boslukla yazilmis dislama kelimesi bunu sessizce kacirir, bu yuzden
    # ardisik boslukla ayrilmis her sey tek bosluga indirgenir.
    sag = re.sub(r"\s+", " ", turkce_ascii_kucult(metin[baslangic:bitis + pencere]))
    return any(k in sag for k in _IKINCIL_URUN_BAGLAM_DISLAMA_KELIMELERI)


# Vade ve taksit sayisi gercek banka verisinde SIK KARISIYOR ("12 aya varan
# taksit" bir TAKSIT SAYISIdir, vade DEGIL; "2 ay ertelemeli" ise bambaska
# bir kavramdir - erteleme suresi). Bu yuzden vade kalibi, taksit/erteleme
# baglamiyla catismayacak sekilde "kadar"/"vade(li)" ifadelerine baglandi.
RE_VADE = _katlanmis_derle(
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
RE_ERTELEME = _katlanmis_derle(
    r"\d{1,2}\s*ay\w*\s*(?:kadar|varan)?\s*(?:ertelemeli|öteleme\w*|ödemesiz\s*dönem)",
    re.IGNORECASE,
)

RE_TAKSIT_SAYISI = _katlanmis_derle(
    r"\d{1,3}\s*aya?\s*varan\s*taksit\w*"
    r"|\d{1,3}\s*ay\s*taksit\w*"
    r"|\d{1,3}\s*taksit(?:li|le)?\b",
    re.IGNORECASE,
)

# Finansman tutari - gercek veride iki ana kalip: tekli ust limit
# ("100.000 TL'ye kadar") ve aralik ("1.000 TL - 100.000 TL arasi").
#
# BUYUKLUK EKI: T.O.M. Katilim tutarlari kelimeyle yaziyor ("250 Bin TL ye
# kadar"), binlik ayiracli degil. Bu bicim desende yoksa tutar HIC
# bulunamaz (olculdu: TOM-002 finansman_tutari None donuyordu).
_TUTAR = r"\d{1,3}(?:\.\d{3})*(?:,\d+)?\s*(?:bin|milyon|milyar)?"

RE_TUTAR_ARALIK = _katlanmis_derle(
    rf"({_TUTAR})\s*TL\s*[-–]\s*({_TUTAR})\s*TL\s*aras", re.IGNORECASE
)
RE_TUTAR_UST_LIMIT = _katlanmis_derle(
    rf"{_TUTAR}\s*TL['’]?\s*(?:ye|ya)?\s*kadar", re.IGNORECASE
)

# BAGLAM GUARD - "X TL'ye kadar" TEK BASINA finansman tutari DEGILDIR.
# Olculdu: 9 yanlis pozitifin 3'u bu desenin baglamsiz eslesmesinden
# geliyordu ve ucu de tamamen farkli kavramlardi:
#   "300.000 TL'ye kadar olan musterilere 6.000 Mil"  -> KART LIMITI
#   "3.500 TL'ye kadar ... restoran harcamalarindan"  -> HARCAMA ESIGI
#   "1.000 TL'ye kadar iade"                          -> IADE TAVANI
# Ayrica AL-001'de iki tutar var - "100.000 TL'ye kadar vade farksiz
# TAKSITLI ALISVERIS" ve "40.000 TL'ye kadar Pratik FINANSMAN Kart";
# baglam olmadan ilk eslesen aliniyordu (yanlis olan).
#
# NEDEN OLUMSUZ LISTE (kar payindaki _ucret_baglaminda_mi ile ayni
# gerekce): olumlu bir "finansman/kredi gecmeli" kurali kurulamaz -
# "kredi karti" kart kampanyalarinin HER YERINDE geciyor ve her tutari
# finansman sanardi. Neyin finansman OLMADIGI daha net tanimlanabilir.
# Bu liste YALNIZCA ust-limit desenine ("X TL'ye kadar") uygulanir -
# aralik desenine ("X TL - Y TL arasi") uygulanmaz, gerekcesi asagida.
#
# "harcama"/"alisveris" LISTEDE OLMALI (olculdu): cikarilinca AL-001
# yanlis tutari secti ("100.000 TL'ye kadar taksitli ALISVERIS", dogrusu
# "40.000 TL'ye kadar Pratik Finansman Kart") ve TOM-001 geri geldi.
# Makro F1: listeli %89,53 / listesiz %87,20.
_TUTAR_BAGLAM_DISLAMA_KELIMELERI = _katla_hepsi([
    "iade", "harcama", "alışveriş", "alisveris", "kazan", "ödül", "odul",
    "hediye", "puan", "mil", "gram", "limit",
    "worldpuan", "parafpara", "bankkart",
])


# CUMLE SINIRI: ". " / "! " / "? " - noktadan SONRA bosluk sart, cunku
# Turkce binlik ayiraci da noktadir ("100.000") ve onu cumle sonu saymak
# sayiyi ortadan bolerdi. Satir sonu (\n) SINIR DEGILDIR: scraper ham
# metinde her HTML blok elemani arasina \n koyuyor, yani AYNI cumle iki
# satira bolunebiliyor (ayni bulgu validation/verifier.py'de de var).
# Katlamaya girmez (harf icermez) - dogrudan derlenir.
_CUMLE_SINIRI = re.compile(r"[.!?]\s")


def _cumleye_kirpilmis_baglam(
    metin: str, baslangic: int, bitis: int, pencere: int
) -> str:
    """Eslesmenin cevresindeki metni AYNI CUMLEYE kirpip kucuk harfe cevirir.

    NEDEN CUMLEYE KIRPILIR (olculdu): duz karakter penceresi cumle sinirini
    asiyor ve komsu cumledeki bir kelime yanlis karar verdiriyordu -
        "5.000 TL'ye kadar alisveris puani KAZANIN. Ayrica 80.000 TL'ye
         kadar ihtiyac FINANSMANI kullanabilirsiniz."
    ikinci tutar, yalnizca ILK cumlede "kazanin" gectigi icin reddediliyordu.
    """
    sol_ham = metin[max(0, baslangic - pencere):baslangic]
    sag_ham = metin[bitis:bitis + pencere]

    sinirlar = list(_CUMLE_SINIRI.finditer(sol_ham))
    sol = sol_ham[sinirlar[-1].end():] if sinirlar else sol_ham
    ilk_sag = _CUMLE_SINIRI.search(sag_ham)
    sag = sag_ham[: ilk_sag.start()] if ilk_sag else sag_ham

    return turkce_ascii_kucult(sol + " " + metin[baslangic:bitis] + " " + sag)


def _tutar_baglaminda_gecersiz_mi(metin: str, baslangic: int, bitis: int, pencere: int = 60) -> bool:
    """Tutarin AYNI CUMLESINDE onu finansman disi kilan bir kelime var mi?"""
    baglam = _cumleye_kirpilmis_baglam(metin, baslangic, bitis, pencere)
    return any(k in baglam for k in _TUTAR_BAGLAM_DISLAMA_KELIMELERI)


# Bir tavan ifadesini ODUL yapan anahtar kelimeler. llm_extractor.py'deki
# _ODUL_ANAHTAR_KELIMELERI ile ayni kume - iki motor da ayni tanimi
# kullanmali, yoksa biri odul sayarken digeri saymaz.
_ODUL_BAGLAM_KELIMELERI = _katla_hepsi([
    "ödül", "odul", "hediye", "kazan", "puan", "mil", "gram",
    "bankkart lira", "parafpara", "worldpuan", "iade",
    "alışveriş çeki", "hediye çeki", "indirim",
])


def _odul_baglaminda_mi(metin: str, baslangic: int, bitis: int, pencere: int = 80) -> bool:
    """Tavan/limit ifadesi ("en fazla X TL") gercekten bir ODULU mu sinirliyor?

    OLCULDU (KT-006): RE_ODUL_TAVAN, "Bu harcamaya ait uygulanacak
    TAKSITLENDIRMEDE maksimum tutar 50.000 TL'dir" cumlesini yakalayip
    50.000 TL'yi odul sandi - oysa bu bir taksitlendirme tavani.
    "en fazla/maksimum + tutar" kalibi tek basina odul belirtmez; ayni
    cumlede bir odul kelimesi de gecmelidir. Desen 4 kayitta DOGRU
    calisiyor (hepsinde "odul"/"kazanilabilecek"/"iade" ayni cumlede),
    bu yuzden desen kaldirilmaz, baglam sarti eklenir.
    """
    baglam = _cumleye_kirpilmis_baglam(metin, baslangic, bitis, pencere)
    return any(k in baglam for k in _ODUL_BAGLAM_KELIMELERI)

_TR_AY_ADLARI = r"Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık"
RE_TARIH = _katlanmis_derle(
    rf"\d{{1,2}}[./]\d{{1,2}}[./]\d{{4}}|\d{{1,2}}\s+(?:{_TR_AY_ADLARI})\s+\d{{4}}", re.IGNORECASE
)
RE_TARIH_ARALIGI = _katlanmis_derle(
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
RE_MASRAFSIZ = _katlanmis_derle(
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
RE_MASRAF_SIFIR_GUCLU = _katlanmis_derle(
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
RE_MASRAF_SIFIR_ZAYIF = _katlanmis_derle(r"masrafs[ıi]z\w*", re.IGNORECASE)
# Tahsis ucreti gercek veride TL TUTARI OLARAK DEGIL, ORAN olarak
# ifade ediliyor: "Tahsis ucreti vergiler haric finansman tutarinin
# binde 5'i oranindadir" (Turkiye Finans, korpustaki tek gercek ornek).
# Bu ifade masraf_durumu'na METIN olarak yazilir; tahsis_ucreti (TL)
# alanina CEVRILMEZ - bkz. kaydi_cikar icindeki gerekce.
RE_TAHSIS_ORANI = _katlanmis_derle(
    r"tahsis [üu]creti[^.\n]{0,80}?(?:binde|y[üu]zde|%)\s*\d{1,3}(?:[.,]\d+)?[^.\n]{0,25}",
    re.IGNORECASE,
)
# Acikca TL tutari verilmis masraf ("dosya masrafi 500 TL") - korpusta
# henuz gorulmedi ama bankadan bankaya degistigi icin desen hazir tutulur.
RE_MASRAF_TUTARI = _katlanmis_derle(
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
RE_ODUL = _katlanmis_derle(
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
RE_ODUL_MIL = _katlanmis_derle(r"\d{1,3}(?:\.\d{3})*(?:,\d+)?\s*Mil['’]?[ea]?\s*varan\s*hediye", re.IGNORECASE)
# Tavan/limit ifadeleri: "en fazla 5 gram", "maksimum 10.000 TL", "kişi
# başı maksimum 2.000 TL, toplamda ... maksimum 10.000 TL nakit ödül" gibi
# cok sayida aday oldugunda SONUNCUSU (genelde "toplamda" olan) tercih
# edilir - finditer + son eslesme.
RE_ODUL_TAVAN = _katlanmis_derle(
    r"(?:en fazla|maksimum)\s+(?:\S+\s+){0,4}?"
    r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*(TL|₺|gram\w*|gr\b)",
    re.IGNORECASE,
)
# "2.500 TL ile sınırlıdır" gibi "sinirli/sinirlidir" ile biten tavan ifadesi.
RE_ODUL_SINIRLI = _katlanmis_derle(
    r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*(TL|₺)['’]?\s*(?:ile\s+)?s[ıi]n[ıi]rl[ıi]",
    re.IGNORECASE,
)
RE_ODUL_GRAM = _katlanmis_derle(
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

# YALNIZCA DEGERLER (aranacak kelimeler) katlanir - ANAHTARLAR katlanmaz:
# onlar cikti etiketidir ve api/schemas.py'deki enum degerleriyle BIREBIR
# ayni kalmalidir ("Yeni müşteri" etiketi "Yeni musteri"ye donusmemeli,
# yoksa Havin/Sara'nin sozlesmesi bozulur).
_KAMPANYA_TURU_KATLANMIS = {
    etiket: _katla_hepsi(kelimeler)
    for etiket, kelimeler in KAMPANYA_TURU_ANAHTAR_KELIMELERI.items()
}
_HEDEF_KITLE_KATLANMIS = {
    etiket: _katla_hepsi(kelimeler)
    for etiket, kelimeler in HEDEF_KITLE_ANAHTAR_KELIMELERI.items()
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


def _ilk_eslesme(desen: re.Pattern, katlanmis: str, ham_metin: str) -> Optional[str]:
    """Deseni KATLANMIS metinde arar, bulunani HAM metinden keserek doner -
    boylece eslesme yazimdan bagimsizdir ama kanit izi kullanicinin kendi
    yazimini korur (bkz. _ham_span)."""
    m = desen.search(katlanmis)
    return _ham_span(ham_metin, m) if m else None


def _odul_birimini_tespit_et(eslesen_metin: str) -> str:
    """RE_ODUL'un eslesen metninde HANGI banka-ozel sadakat biriminin
    gectigini tespit eder. Eskiden bu fonksiyon yoktu, RE_ODUL eslestigi
    surece odul_birimi kosulsuz "TL" atanirdi - bu yuzden Bankkart Lira/
    ParafPara/Worldpuan gibi TL-disi birimler bile yanlislikla "TL" olarak
    kaydediliyordu (Extraction Accuracy raporu, 18/40 hata)."""
    metin_l = turkce_ascii_kucult(eslesen_metin)
    if "bankkart lira" in metin_l:
        return "Bankkart Lira"
    if "parafpara" in metin_l:
        return "ParafPara"
    if "worldpuan" in metin_l:
        return "Worldpuan"
    return "TL"


def _kampanya_turunu_tespit_et(metin: str) -> Optional[str]:
    metin_l = turkce_ascii_kucult(metin)
    for etiket, kelimeler in _KAMPANYA_TURU_KATLANMIS.items():
        if any(k in metin_l for k in kelimeler):
            return etiket
    return None


def _hedef_kitleyi_tespit_et(metin: str) -> Optional[str]:
    metin_l = turkce_ascii_kucult(metin)
    for etiket, kelimeler in _HEDEF_KITLE_KATLANMIS.items():
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

    # TUM desen aramalari KATLANMIS metinde yapilir (diyakritiksiz yazilmis
    # metin de eslessin diye - bkz. dosya basindaki "Diyakritik katlama").
    # Katlama uzunlugu korudugu icin eslesme offset'leri ham metinde ayni
    # yeri gosterir; kanit izleri `_ham_span` ile HAM metinden kesilir.
    # Baglam yardimcilari (_ucret_baglaminda_mi vb.) ham metni alir - onlar
    # kendi icinde `turkce_ascii_kucult` uyguluyor.
    katlanmis = turkce_ascii_katla(ham_metin)

    # --- Kar payi orani -----------------------------------------------
    m = RE_KAR_PAYI_SAYI_ONCE.search(katlanmis)
    if m and _kar_payi_ata(alanlar, izler, _ham_span(ham_metin, m), 0.9):
        pass
    else:
        m = RE_KAR_PAYI_BAGLAM_ONCE.search(katlanmis)
        sayi_m = re.search(r"%\s*\d{1,2}(?:[.,]\d{1,4})?", _ham_span(ham_metin, m)) if m else None
        if sayi_m and _kar_payi_ata(alanlar, izler, sayi_m.group(0), 0.9):
            pass
        elif (
            any(
                not _ikincil_urun_baglaminda_mi(katlanmis, gm.start(), gm.end())
                for gm in RE_KAR_PAYSIZ.finditer(katlanmis)
            )
            or RE_KAR_PAYI_SIFIR.search(katlanmis)
        ):
            alanlar["kar_payi_orani_decimal"] = 0.0
            alanlar["kar_payi_orani_percent"] = 0.0
            izler["kar_payi_orani_percent"] = ("kâr paysız / 0 kâr paylı", 0.85)
        elif RE_VADE_FARKSIZ.search(katlanmis):
            # "Vade farksiz" katilim bankaciliginda o islem icin kar payi
            # oraninin 0 oldugu anlamina gelir (Extraction Accuracy raporu +
            # terminology/sozluk.json'daki sifir_oran_ifadesi kavramiyla
            # tutarli). Dogrudan "kar paysiz" kadar yuksek guvenli degil
            # (0.8 < 0.85) - farkli bir ifade oldugu icin.
            alanlar["kar_payi_orani_decimal"] = 0.0
            alanlar["kar_payi_orani_percent"] = 0.0
            izler["kar_payi_orani_percent"] = ("vade farksız", 0.8)
        else:
            for gm in RE_KAR_PAYI_GENEL.finditer(katlanmis):
                if not _ucret_baglaminda_mi(ham_metin, gm.start(), gm.end()):
                    if _kar_payi_ata(alanlar, izler, _ham_span(ham_metin, gm), 0.6):
                        break

    # --- Finansman tutari ----------------------------------------------
    # ARALIK DESENINE BAGLAM GUARD'I UYGULANMAZ (olculdu): "X TL - Y TL
    # arasi" kalibi gercek veride yalnizca finansman/taksitlendirme
    # araliklarinda geciyor, odul tavanlarinda hic gecmiyor - 9 yanlis
    # pozitifin hicbiri bu desenden gelmedi. Guard uygulanirsa AL-005
    # ("1.000 TL-100.000 TL arasi saglik HARCAMALARINIZA vade farksiz 6
    # taksit") ve AL-006 gibi GERCEK finansman araliklari, yalnizca
    # cumlede "harcama" gectigi icin elenir.
    m = RE_TUTAR_ARALIK.search(katlanmis)
    if m:
        alanlar["finansman_tutari"] = tutara_cevir(_ham_span(ham_metin, m, 2))
        izler["finansman_tutari"] = (_ham_span(ham_metin, m), 0.85)
    else:
        # ILK eslesme degil, ILK GECERLI eslesme (bkz. baglam guard'i):
        # ayni sayfada hem "100.000 TL'ye kadar taksitli ALISVERIS" hem
        # "40.000 TL'ye kadar Pratik FINANSMAN Kart" gecebiliyor.
        for tm in RE_TUTAR_UST_LIMIT.finditer(katlanmis):
            if _tutar_baglaminda_gecersiz_mi(ham_metin, tm.start(), tm.end()):
                continue
            tutar = tutara_cevir(_ham_span(ham_metin, tm))
            if tutar is None:
                continue
            alanlar["finansman_tutari"] = tutar
            izler["finansman_tutari"] = (_ham_span(ham_metin, tm), 0.75)
            break

    # --- Vade / taksit sayisi / erteleme suresi (UC AYRI kavram) -------
    span = _ilk_eslesme(RE_VADE, katlanmis, ham_metin)
    if span:
        alanlar["vade_ay"] = aya_cevir(span)
        izler["vade_ay"] = (span, 0.85)

    span = _ilk_eslesme(RE_ERTELEME, katlanmis, ham_metin)
    if span:
        alanlar["erteleme_suresi_ay"] = aya_cevir(span)
        izler["erteleme_suresi_ay"] = (span, 0.85)

    span = _ilk_eslesme(RE_TAKSIT_SAYISI, katlanmis, ham_metin)
    if span:
        sayi_m = re.search(r"\d+", span)
        alanlar["taksit_sayisi"] = int(sayi_m.group(0)) if sayi_m else None
        izler["taksit_sayisi"] = (span, 0.85)

    # --- Odul miktari/birimi -------------------------------------------
    m = RE_ODUL_MIL.search(katlanmis)
    if m:
        alanlar["odul_miktari"] = tutara_cevir(_ham_span(ham_metin, m))
        alanlar["odul_birimi"] = "Mil"
        izler["odul_miktari"] = (_ham_span(ham_metin, m), 0.8)
    else:
        m = RE_ODUL_GRAM.search(katlanmis)
        if m:
            alanlar["odul_miktari"] = tutara_cevir(_ham_span(ham_metin, m))
            alanlar["odul_birimi"] = "Gram"
            izler["odul_miktari"] = (_ham_span(ham_metin, m), 0.8)
        else:
            m = RE_ODUL.search(katlanmis)
            if m:
                alanlar["odul_miktari"] = tutara_cevir(_ham_span(ham_metin, m))
                # ONCEDEN: kosulsuz "TL" atanirdi - Bankkart Lira/ParafPara/
                # Worldpuan gibi TL-disi birimler yanlis kaydediliyordu.
                alanlar["odul_birimi"] = _odul_birimini_tespit_et(_ham_span(ham_metin, m))
                izler["odul_miktari"] = (_ham_span(ham_metin, m), 0.8)
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
                # BAGLAM SARTI: tavan/limit kalibi tek basina odul
                # belirtmez - ayni cumlede bir odul kelimesi de gecmeli
                # (bkz. _odul_baglaminda_mi, KT-006 bulgusu).
                adaylar: list[tuple[float, str, str]] = []  # (tutar, birim, span)
                for m in RE_ODUL_SINIRLI.finditer(katlanmis):
                    if not _odul_baglaminda_mi(ham_metin, m.start(), m.end()):
                        continue
                    tutar = tutara_cevir(_ham_span(ham_metin, m, 1))
                    if tutar is not None:
                        adaylar.append((tutar, "TL", _ham_span(ham_metin, m)))
                for tm in RE_ODUL_TAVAN.finditer(katlanmis):
                    if not _odul_baglaminda_mi(ham_metin, tm.start(), tm.end()):
                        continue
                    tutar = tutara_cevir(_ham_span(ham_metin, tm, 1))
                    if tutar is not None:
                        birim_ham = turkce_ascii_kucult(_ham_span(ham_metin, tm, 2))
                        birim = "Gram" if birim_ham.startswith("gr") else "TL"
                        adaylar.append((tutar, birim, _ham_span(ham_metin, tm)))
                if adaylar:
                    tutar, birim, span = max(adaylar, key=lambda a: a[0])
                    alanlar["odul_miktari"] = tutar
                    alanlar["odul_birimi"] = birim
                    izler["odul_miktari"] = (span, 0.7)

    # --- Masraf bilgisi / tahsis ucreti -----------------------------------
    # Uc kademe: (1) acik TL tutari, (2) acik "masraf alinmaz" ifadesi,
    # (3) oran olarak verilmis tahsis ucreti. Ilk eslesen kazanir.
    m = RE_MASRAF_TUTARI.search(katlanmis)
    if m:
        tutar = tutara_cevir(_ham_span(ham_metin, m, 1))
        if tutar is not None:
            alanlar["masraf_durumu"] = _ham_span(ham_metin, m)
            alanlar["tahsis_ucreti"] = tutar
            izler["masraf_durumu"] = (_ham_span(ham_metin, m), 0.85)
    else:
        span = _ilk_eslesme(RE_MASRAFSIZ, katlanmis, ham_metin) or _ilk_eslesme(
            RE_MASRAF_SIFIR_GUCLU, katlanmis, ham_metin
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
            span = _ilk_eslesme(RE_TAHSIS_ORANI, katlanmis, ham_metin)
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
                span = _ilk_eslesme(RE_MASRAF_SIFIR_ZAYIF, katlanmis, ham_metin)
                if span:
                    alanlar["masraf_durumu"] = span
                    izler["masraf_durumu"] = (span, 0.5)

    # --- Kampanya suresi: once tarih ARALIGI, sonra tek tarih -----------
    m = RE_TARIH_ARALIGI.search(katlanmis)
    if m:
        alanlar["kampanya_baslangic"] = tarihe_cevir(_ham_span(ham_metin, m, 1))
        alanlar["kampanya_bitis"] = tarihe_cevir(_ham_span(ham_metin, m, 2))
        izler["kampanya_bitis"] = (_ham_span(ham_metin, m), 0.9)
    else:
        span = _ilk_eslesme(RE_TARIH, katlanmis, ham_metin)
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

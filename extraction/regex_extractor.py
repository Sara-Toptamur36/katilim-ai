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
from datetime import date
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
# RE_VADE_FARKSIZ KALDIRILDI (23 Agustos 2026, kart precision duzeltmesi).
#
# GEREKCE (olculdu - extraction_accuracy_raporu.md): "vade farksiz 6 taksit"
# bir KART kampanyasi ifadesidir - finansman kar payi orani DEGILDIR.
# Altin veri setinde bu ifadeyi tasiyan 13 kaydin tamami card_kampanyasi
# turunde ve altin etiketleyenler kar_payi_orani'ni "kaynakta belirtilmemis"
# isaret etmis. Motor ile gold sozlesmesi catisiyor; motor %33 precision
# uretiyordu (40 yanlis pozitifin 13'u buradan). "Vade farksiz" kart taksit
# ozelligini belirtir (vade farki = geleneksel bankaciliktaki faiz eki;
# farksiz = ek uygulama yok), ama bu finansman kar payi oraniyla AYNI SEY
# DEGILDIR - domain analizi gold etiketleyenlerle tutarli.
#
# "Kar paysiz" (RE_KAR_PAYSIZ) ve "0 kar payli" (RE_KAR_PAYI_SIFIR) kurallari
# KORUNUYOR: bunlar dogru sekilde sifir kar payli finansman kampanyalarini
# yakaliyor (ornekleri altin veride dogrulanmis: AL-002, VK-001 vb.).

# Nakit iade / indirim orani - Sartname Md. 5.3 "Indirim Orani" alani.
# NEDEN GEREKLI: "%10 nakit iade" ve "%30 indirim" ifadelerinin gidecek
# bir alan yoktu; kucuk guvenli fallback (RE_KAR_PAYI_GENEL, 0.6) bunlari
# kar_payi_orani'na sokuyordu - olculdu: HF-010, ZK-016 yanlis pozitif.
# Artik bu ifadeler AYRI bir alana (nakit_iade_orani / indirim_orani_percent)
# cikarilir ve kar payi mantigi bu baglamda CALISTIRILMAZ.
RE_NAKIT_IADE = _katlanmis_derle(
    r"%\s*\d{1,2}(?:[.,]\d{1,4})?"
    r"(?:[^%\n]{0,30}(?:nakit\s*iade|cashback|geri\s*iade))"
    r"|(?:nakit\s*iade|cashback)[^%\n]{0,30}%\s*\d{1,2}(?:[.,]\d{1,4})?",
    re.IGNORECASE,
)
RE_INDIRIM_ORANI = _katlanmis_derle(
    r"%\s*\d{1,2}(?:[.,]\d{1,4})?"
    r"(?:[^%\n]{0,25}indirim)"
    r"|(?:indirim)[^%\n]{0,25}%\s*\d{1,2}(?:[.,]\d{1,4})?",
    re.IGNORECASE,
)
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
    # SADAKAT PARA BIRIMLERI (olculdu 23 Agustos: ZK-011, ZK-016).
    # "tum harcamalara %10, toplamda 5.000 TL Bankkart Lira!" - buradaki
    # %10 bir KAZANIM oranidir, kar payi orani degil. Listede zaten "puan"
    # ve "odul" vardi ama bankalarin KENDI birim adlari yoktu; oysa bu
    # birimler depoda baska yerde tanimli (comparison/compare_engine.py
    # BIRIM_BAGIMLI_EKSENLER, altin veri setinde alti ayri birim). Ayni
    # bilgi iki yerde ayri ayri tutulunca biri guncellenip digeri
    # unutuluyordu.
    "bankkart lira", "worldpuan", "parafpara", "bonus", "mil",
    # HARCAMA YUZDESI: bir yuzde "harcama"ya uygulaniyorsa o bir iade/
    # kazanim oranidir (olculdu: ZK-011, ZK-016, HF-010). Bu kelime
    # yalnizca DUSUK GUVENLI fallback'i (0.6) etkiler - metinde acikca
    # "kar payi/kar orani" gecen kayitlar zaten 0.9 guvenli yoldan
    # atanir ve buraya hic ugramaz.
    "harcama",
    # "... TUTARININ %X'i kadar": bir tutarin yuzdesi olarak ifade edilen
    # deger, o urunun kar payi orani DEGIL, ondan turetilen bir kazanim
    # ya da kesintidir (olculdu: HF-008 "transfer tutarinin %0,1'i").
    "tutarın", "tutarin", "transfer",
])

# ORAN TABLOSU ESIGI: Turkiye Finans'in "Aylik/Yillik Toplam Maliyet"
# tablolari bir satirda yan yana bes-alti yuzde tasiyor
# ("3 | 4,20% | 0,50% | 5,77% | 96,05%"). Baglam penceresi 45 karakter
# oldugu icin satirin BASINDAKI "Maliyet" basligi uzaktaki hucrelere
# yetismiyordu ve tablonun ortasindaki bir hucre kar payi orani
# saniliyordu (olculdu: TF-001, TF-008 - TF-001 zaten "bilinen yanlis
# pozitif" olarak belgelenmisti, kok nedeni buymus).
#
# NEDEN SAYIYLA AYIRT EDILIYOR: duz metinde bir cumlenin icinde ucten
# fazla yuzde yan yana gecmez; bu yogunluk TABLO oldugunun kendisi kadar
# guvenilir bir isaretidir. Tablolardaki gercek oranlari zaten ayri bir
# katman okuyor (extraction/tablo_extractor.py), bu yuzden fallback'in
# oraya hic girmemesi dogru davranistir.
_ORAN_TABLOSU_PENCERE = 60
_ORAN_TABLOSU_ASGARI_YUZDE = 3


def _oran_tablosu_baglaminda_mi(metin: str, baslangic: int, bitis: int) -> bool:
    """Eslesmenin cevresi bir oran TABLOSU satiri mi (duz cumle degil)?"""
    pencere = metin[
        max(0, baslangic - _ORAN_TABLOSU_PENCERE) : bitis + _ORAN_TABLOSU_PENCERE
    ]
    return pencere.count("%") >= _ORAN_TABLOSU_ASGARI_YUZDE


def _ucret_baglaminda_mi(metin: str, baslangic: int, bitis: int, pencere: int = 45) -> bool:
    sol = turkce_ascii_kucult(metin[max(0, baslangic - pencere):baslangic])
    sag = turkce_ascii_kucult(metin[bitis:bitis + pencere])
    baglam = sol + " " + sag
    eslesenler = [k for k in _UCRET_BAGLAM_DISLAMA_KELIMELERI if k in baglam]
    if not eslesenler:
        return False
    if eslesenler == ["harcama"] and "vadelendir" in baglam:
        # DENETIM BULGUSU (26 Agustos 2026, KT-032): "harcama" dislama
        # kelimesi normalde "restoran harcamasında %10 iade" gibi bir
        # KAZANIM/cashback oranini elemek icindir (bkz. yukaridaki asil
        # gerekce). Ama "akaryakit harcamalarinizda %2,99 oran ile
        # VADELENDIRILECEKTIR" gibi bir cumlede ayni "harcama" kelimesi
        # gecse de bu bir FINANSMAN/taksit donusum oranidir (kar payi
        # oraninin ta kendisi) - iade degil. "vadelendir" fiili SADECE bu
        # ikinci anlamda kullanilir ("vade farksiz" ile KARISMAZ, farkli
        # kok - dogrulandi: 623 ham dosyanin 2'sinde "vadelendir" geciyor,
        # ikisi de bu tur bir taksit-donusum cumlesi, "harcama" excludeu
        # daha once dogru elemis 5 kayitta (ZK-011/016, HF-008/010,
        # TOM-002) "vadelendir" HIC gecmiyor). Yalnizca "harcama" TEK
        # BASINA eslesen sebep oldugunda uygulanir - baska bir dislama
        # kelimesi (ör. "iade") de varsa bu istisna calismaz.
        return False
    return True


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

# DENETIM BULGUSU (26 Agustos 2026, KT-001 - EVREN/hibrit olcum
# hazirligi): Kuveyt Turk'un finansman sayfalarinda "3 ay vadeli 10.000
# TL'lik basvuru icin ornek odeme plani: Aylik kar orani %2,99, ..."
# gibi tekrarlayan bir SABLON metni var - bu bir ORNEK SENARYO, kampanyanin
# GERCEK vadesi degil (KT-001'in kendi vadesi zaten "belirtilmemis").
# RE_VADE bunu "3 ay vadeli" olarak yakalayip vade_ay=3 uyduruyordu. Ayni
# bulgu llm_extractor.py'de LLM'in urettigi vade_ay icin de gecerliydi
# (bkz. o dosyadaki _vade_ornek_odeme_planindan_mi) - TEK KAYNAK burada
# tutulur, iki motor da ayni deseni kullanir.
_ORNEK_ODEME_PLANI_DESENI = _katlanmis_derle(
    r"ay\w*\s*vadel[iı]\s*[\d.,]+\s*tl['’]?l[iı]k\s*ba[sş]vuru\s*i[cç]in\s*[oö]rnek\s*[oö]deme\s*plan",
    re.IGNORECASE,
)


def _vade_ornek_odeme_planindan_mi(katlanmis: str, baslangic: int, bitis: int, pencere: int = 90) -> bool:
    """Bulunan vade esleşmesi, sablonik bir 'ornek odeme plani' cumlesinden mi geliyor?"""
    return bool(_ORNEK_ODEME_PLANI_DESENI.search(katlanmis[baslangic : bitis + pencere]))


# DENETIM BULGUSU (26 Agustos 2026, DK-001): "Finansman islemlerinde
# minimum 2 ay, maksimum 6 ay vade yapilacaktir" gibi bir cumlede RE_VADE
# yalnizca UST siniri ("6 ay vade") yakalar - alt sinir ("2 ay") ayni
# desene uymaz (hemen ardindan "vade"/"kadar" gelmiyor). Sonuc: sabit tek
# bir vade degil, bir ARALIK ifade eden bu cumleden vade_ay=6 uyduruluyordu
# (gold DK-001 icin "belirtilmemis" diyor). taksit_sayisi'nda zaten
# kurulu olan "COKLU FARKLI DEGER VARSA BOS BIRAK" ilkesiyle AYNI ruh -
# burada tek regex eslesmesi oldugu icin coklu-aday toplama islemez,
# bunun yerine ayni cumlede hem "minimum" hem "maksimum" GECIYOR MU diye
# bakilir (ikisi birlikte, tek bir sabit deger degil bir ARALIK beyan
# eder).
def _vade_araligin_ust_siniri_mi(katlanmis: str, baslangic: int, bitis: int, pencere: int = 60) -> bool:
    baglam = _cumleye_kirpilmis_baglam(katlanmis, baslangic, bitis, pencere)
    return "minimum" in baglam and "maksimum" in baglam


# "ertelemeli", "oteleme" ve "odemesiz donem" es anlamli - vade DEGIL,
# ayri bir kavram. Baglac kelimesi banka bazinda degisiyor.
# "erteleme" (ek olmadan, isim hali) EKLENDI (DENETIM BULGUSU, 26 Agustos
# 2026, KT-040): "3 Ay Erteleme ve %3,49 Oranla 9 Taksit İmkanı!" - sifat
# hali "ertelemeli" degil dogrudan isim hali "erteleme" kullaniyor, mevcut
# desen bunu kapsamiyordu.
RE_ERTELEME = _katlanmis_derle(
    r"\d{1,2}\s*ay\w*\s*(?:kadar|varan)?\s*(?:ertelemeli|erteleme\b|öteleme\w*|ödemesiz\s*dönem)",
    re.IGNORECASE,
)

# "9'a Varan Taksit" (DENETIM BULGUSU, 26 Agustos 2026, ZK-014): bazi
# Ziraat Katilim sayfalari "ay" kelimesini hic yazmadan sadece "X'a Varan
# Taksit" diyor (Amazon'da 9'a Varan Taksit) - "aya?" kalibi "ay" harflerini
# ZORUNLU kildigi icin bunu kacırıyordu (5 dosyada dogrulandi). "ay" YOK
# iken bu ayrimin vade_ay ile karismasi imkansiz - RE_VADE de ayni sekilde
# "ay" harflerini zorunlu kilar.
# "taksite" (-e hali) EKLENDI (DENETIM BULGUSU, 26 Agustos 2026, ZK-030):
# "4 taksite bolunecektir" / "5 taksite bolunur" gibi YONELME HALI cekimi
# (Turkce -e/-a eki) hic kapsanmiyordu, yalnizca "taksitli"/"taksitle"
# ekleri vardi (19 dosyada dogrulandi). Bu ayni zamanda coklu-tier
# sayfalarda (ZK-030: 4/5/6 taksit farkli tutar araliklarina gore) dogru
# "birden fazla farkli deger -> bos birak" davranisinin TETIKLENEBILMESI
# icin de onemli - eskiden bu sayfalarin cogu tek bir aday buluyor
# GORUNUYORDU (aslinda digerleri kacırılıyordu) ve yanlislikla sabit bir
# sayi atiyordu.
RE_TAKSIT_SAYISI = _katlanmis_derle(
    r"\d{1,3}\s*aya?\s*varan\s*taksit\w*"
    r"|\d{1,3}['’]?a\s*varan\s*taksit\w*"
    r"|\d{1,3}\s*ay\s*taksit\w*"
    r"|\d{1,3}\s*taksit(?:li|le|e)?\b",
    re.IGNORECASE,
)

# ARALIK IFADESININ IKINCI SAYISI (olculdu 24 Agustos 2026, KT-021/025):
# "2 ila 9 taksit arasinda secim yaparak" veya "2-7 taksitli islemlere"
# gibi ifadelerde RE_TAKSIT_SAYISI yalnizca ARALIGIN SON sayisini
# yakalar ("9 taksit" / "7 taksitli") - ilk sayidan sonra gelen "ila"
# veya tire, "\d{1,3}\s*taksit" desenine uymadigi icin eslesme oradan
# baslayamaz, ikinci sayidan baslar. Sonuc: kullanicinin SECEBILECEGI
# bir ARALIK, sabit bir taahhut gibi okunur. Gold bu durumlarda dogru
# olarak "belirtilmemis" diyor - tek bir taksit sayisi yok, bir aralik
# var.
# "ile" EKLENDI (DENETIM BULGUSU, 26 Agustos 2026, KT-044): "vade farksiz
# 2 ile 5 taksit arasinda taksitlendirebilirsiniz" - "ile" de "ila" gibi
# aralik baglaci olarak kullanilabiliyor (6 dosyada dogrulandi, hepsi ayni
# "N ile M taksit arasinda" kalibi). "ile" TEK BASINA cok genel bir kelime
# oldugu icin riskli gorunebilir, ama desen ONCESINDE bir RAKAM sartini
# ZATEN tasiyor (\d{1,3}\s*ile) - yani yalnizca "Business Kart ile 5
# taksit" gibi (rakamsiz "ile") ifadeler DEGIL, "2 ile 5 taksit" gibi
# GERCEKTEN iki sayi arasindaki "ile" eslesir.
RE_TAKSIT_ARALIK_ONEKI = re.compile(r"\d{1,3}\s*(?:-|–|ila|ile)\s*$", re.IGNORECASE)


def _taksit_araliginin_ikinci_sayisi_mi(katlanmis: str, baslangic: int, pencere: int = 12) -> bool:
    """Eslesmenin HEMEN ONCESINDE 'N-' veya 'N ila/ile' var mi (aralik ifadesi)?"""
    sol = katlanmis[max(0, baslangic - pencere):baslangic]
    return bool(RE_TAKSIT_ARALIK_ONEKI.search(sol))


# DENENDI VE GERI ALINDI (26 Agustos 2026, ZK-033/ZK-004, olculdu):
# yukaridaki guard'in eledigi araligin ILK sayisini (ör. "3-4 taksitli"teki
# "3") de bir aday olarak eklemek denendi - amac "3-4 taksitli... +5
# taksit" gibi cok kademeli sayfalarda (ZK-030/033) "5"in TEK aday gibi
# gorunup yanlislikla atanmasini onlemekti. ZK-030/033'u DUZELTTI ama
# AYNI "N-M taksitli ... +K taksit" kalibini tasiyan ZK-004'u BOZDU -
# ZK-004'un gold notu acikca "+8, kampanyanin KENDI KATTIGI taksit
# sayisidir (baslik da oyle diyor)" diyor; yani AYNI yuzeysel kalip iki
# kayitta ZIT anlam tasiyor (ZK-030/033'te "+N" KOSULLU bir ek, ZK-004'te
# "+N" kampanyanin TEK ve kesin iddiasi) - bu ayrimi metinden regex ile
# cikarmak mumkun degil (net etki: F1 88,48 -> 88,37, kucuk ama negatif),
# alinmadi.

# Finansman tutari - gercek veride iki ana kalip: tekli ust limit
# ("100.000 TL'ye kadar") ve aralik ("1.000 TL - 100.000 TL arasi").
#
# BUYUKLUK EKI: T.O.M. Katilim tutarlari kelimeyle yaziyor ("250 Bin TL ye
# kadar"), binlik ayiracli degil. Bu bicim desende yoksa tutar HIC
# bulunamaz (olculdu: TOM-002 finansman_tutari None donuyordu).
# ORTAK SAYI PARCASI - ayni kusur eskiden 6 ayri desende tekrarliyordu.
# `\d{1,3}(?:\.\d{3})*` yazimi, ayrac KULLANILMAYAN sayilarda en fazla 3
# hane alabildigi icin "2000 TL"de bastan degil SONDAN eslesiyordu:
# regex "2"den baslayip TL'ye ulasamayinca ilerliyor ve "000 TL"yi
# yakaliyordu -> odul_miktari = 0.0 (olculdu: ZK-009). Sifir degeri hem
# yanlis pozitif uretiyor hem de karsilastirmada "en dusuk" siralamasini
# haksiz kazaniyordu.
#
# Ayracli bicim ONCE denenir ("10.000" tek sayi olarak okunsun, "10" +
# "000" diye ikiye bolunmesin); ayracsiz sayilar `\d+` ile tam uzunlukta
# yakalanir. Tum desenler gruplarsiz (?:...) oldugu icin cagiran taraftaki
# grup numaralari DEGISMEZ.
_SAYI = r"(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?"

_TUTAR = rf"{_SAYI}\s*(?:bin|milyon|milyar)?"

RE_TUTAR_ARALIK = _katlanmis_derle(
    rf"({_TUTAR})\s*TL\s*[-–]\s*({_TUTAR})\s*TL\s*aras", re.IGNORECASE
)
RE_TUTAR_UST_LIMIT = _katlanmis_derle(
    rf"{_TUTAR}\s*TL['’]?\s*(?:ye|ya)?\s*kadar", re.IGNORECASE
)

# "kadar" ICERMEYEN AYRI BIR UST LIMIT IFADESI (olculdu 25 Agustos 2026,
# HF-006): bazi sayfalar "X TL'ye kadar" yerine "(kampanya) ust limit(i)
# X TL('dir)" bicimini kullaniyor - iki desen de "ust sinir" anlamina
# gelir ama farkli kelime sirasindadir, RE_TUTAR_UST_LIMIT bunu YAKALAMAZ.
#
# _tutar_baglaminda_gecersiz_mi UYGULANMAZ: o guard'in dislama listesinde
# "limit" kelimesi var (kart limiti gibi ALAKASIZ "limit" gecislerini
# elemek icin, bkz. RE_TUTAR_UST_LIMIT'in guard'i) - bu desen ise TAM
# OLARAK "ust limit" ifadesine dayandigi icin ayni guard'i uygulamak
# kendi kendini elerdi. Bunun yerine ozgulluk desenin KENDISINDEN gelir:
# "ust limit" + tutar + TL dogrudan yan yana gecmeli, bu ayrimin
# gerektirdigi kesinligi tek basina sagliyor.
RE_TUTAR_UST_LIMIT_BEYANI = _katlanmis_derle(
    rf"üst\s*limit\w*\s+{_TUTAR}\s*TL", re.IGNORECASE
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
# LISTE YENIDEN OLCULDU 25 Agustos 2026 (altin veri seti buyudu):
# "harcama" CIKARILDI, "işlem" ve "para çek" EKLENDI.
# finansman_tutari F1 %48,00 -> %61,54 (P %40,00 -> %63,16).
#
# "harcama" NEDEN CIKTI: yukaridaki eski not "cikarilinca AL-001 yanlis
# tutari secti" diyordu - o olcum ARTIK GECERLI DEGIL. Bugun olculdu:
# AL-001 dogru kaliyor (40.000), AL-005 (100.000), AL-006 (500.000) ve
# TOM-002 (250.000) ise "harcama" YUZUNDEN kaybediliyordu. Sebep:
# gercek finansman kampanyalari da harcamaya uygulanir ("sağlık
# harcamalarınıza vade farksız 6 taksit"), yani kelime finansmani
# finansman-olmayandan AYIRMIYOR. Ayirt edici olan "alışveriş" (listede
# KALDI) - magaza taksit basamaklarinda geciyor, finansman metinlerinde
# gecmiyor. Bilanco: -1 yanlis pozitif (TOM-001), +2 dogru.
#
# "işlem" / "para çek" NEDEN GIRDI: FP'lerin buyuk bolumu ATM/POS
# limitleriydi - "10.000 TL'ye kadar para çekebilir" (TF-007), "günlük
# 5.000 TL'ye kadar para çekme" (TF-011), "tek seferde 200.000 TL'ye
# kadar olan işlemlerde" (DK-010/TEK-020), "350.000 TL'ye Kadar ... POS
# İşlemleri için" (KT-047). Hicbiri finansman tutari degil.
# "atm"/"pos"/"para yat" AYRICA DENENDI: "işlem" onlari zaten kapsadigi
# icin F1'i hic degistirmediler (61,54), eklenmediler.
#
# REDDEDILEN ADAY - "harcamalarından" (yonelme/ayrilma hali ayrimi):
# F1'i 61,54 -> 63,16 cikariyordu ve dilbilgisel gerekcesi makul
# gorunuyordu ("harcamalarınıza" finansman, "harcamalarından" odul).
# ASIRI UYDURMA KONTROLU bunu curuttu: acikca uydurma olan "restoran"
# anahtari BIREBIR AYNI sayiyi veriyor (63,16) - yani kazanc kuraldan
# degil, tek bir kayittan (TOM-001) geliyor. Tek kayitlik bir kural
# genellemez; alinmadi.
# "yedek hesa" (DENETIM BULGUSU, 26 Agustos 2026, TF-005): Turkiye
# Finans sayfalarinda ANA kampanyadan (400.000 TL Ihtiyac Finansmani)
# TAMAMEN AYRI, "Yedek Hesap" adli kucuk-tutarli bir ek urun anlatan
# cumle var - "Yedek Hesabınızı kullanabilir, üstelik 2.500 TL'ye kadar
# kullanımlarınız için kâr payı ödemezsiniz." Bu ayrim RE_KAR_PAYSIZ icin
# zaten _ikincil_urun_baglaminda_mi ile cozulmustu (bkz. yukarida) ama o
# fonksiyon YALNIZCA ILERI yonde bakiyor ve o cagrida "Yedek Hesap"
# esleseden SONRA geliyordu; burada ise tutarin ONCESINDE geciyor. Ayri
# bir kelime EKLEMEK yerine (kod tekrari), ayni bidirectional
# cumle-baglamli guard'a (_TUTAR_BAGLAM_DISLAMA_KELIMELERI, zaten iki
# yonlu bakan _cumleye_kirpilmis_baglam kullanir) katildi. Kok "hesa"da
# (tam "hesap" degil) KESILDI: Turkce unsuz yumusamasi ("hesap" -> "hesabı"
# iyelik/hal ekiyle) yuzunden coktinlenmis "hesap" ASLA "hesabınızı"
# icinde alt-dize olarak gecmez ama "hesa" hem "hesap" hem "hesabı"
# formunda ortaktir.
_TUTAR_BAGLAM_DISLAMA_KELIMELERI = _katla_hepsi([
    "iade", "alışveriş", "alisveris", "kazan", "ödül", "odul",
    "hediye", "puan", "mil", "gram", "limit",
    "işlem", "para çek",
    "worldpuan", "parafpara", "bankkart",
    "yedek hesa",
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


# PENCERE 60 -> 120 DENENDI VE REDDEDILDI (25 Agustos 2026, olculdu):
# KT-023'te "... 250.000 TL arasi yapacagi ilk harcamaya vade farksiz 3
# taksit avantaji KAZANACAKTIR" cumlesi 60 karakterden uzun - dislama
# kelimesi ("kazan") cumlenin 68. karakterinde, pencere=60 onu goremiyor
# ve harcama araligi yanlislikla finansman_tutari saniliyordu. Pencereyi
# 120'ye cikarmak TOM-001'i duzeltti AMA TOM-002'yi BOZDU: "gunluk
# KAZANdiran hesabinda 250.000 TL birikim..." cumlesinde "Kazandiran
# Hesap" bir URUN ADI (gunluk faiz kazandiran mevduat hesabi), "kazan"
# alt-dizesi burada YANLIS POZITIF eslesme - eski dar pencere bu urun
# adina hic ulasamiyordu, genis pencere ulasip DOGRU bir tutari yanlislikla
# eledi. NET ETKI: finansman_tutari F1 %63,41 -> %61,54 (bir FP dustu, bir
# TP kayboldu - kazanc yok) VE KT-023'un kendisi HALA duzelmedi (RE_TUTAR_
# UST_LIMIT ayri bir eslesmeyle "250.000 TL'ye kadar" tutarini BASKA bir
# cumleden buluyor). Pencere 60'ta birakildi; KT-023 "vade farksiz N
# taksit" ifadesiyle baglantili tutarlarin AYRI bir dislama sinyali
# gerektirdigini gosteriyor - bu, "taksit" kelimesini genel dislama
# listesine eklemeyi gerektirir ve olculmeden eklenmedi (bkz. Faz notu).
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

# TEK TARIH - uc bicim (olculdu 23 Agustos 2026, Ziraat Katilim 11 kayit):
# gg.aa.yyyy / gg-aa-yyyy / gg Ay yyyy. Tire ayracli bicim eskiden hic
# desteklenmiyordu - Ziraat Katilim sayfalari "Kampanya Donemi 10-07-2025
# - 31-08-2026" ve "Kampanya 09-08-2026 Tarihinde Sona Ermistir" bicimini
# kullaniyor, ikisi de nokta/slash DEGIL tire kullaniyor. Sonuc: bu
# kayitlarda kampanya_bitis hep BOS kaliyordu (ya da - daha kotusu - motor
# sayfanin ILERISINDEKI baska bir tarihi (ör. "Diger Kampanyalar"
# carousel'indeki "Son Gun dd.mm.yyyy") yanlislikla buluyordu).
_TARIH_TEK = (
    rf"\d{{1,2}}[./]\d{{1,2}}[./]\d{{4}}"
    rf"|\d{{1,2}}-\d{{1,2}}-\d{{4}}"
    rf"|\d{{1,2}}\s+(?:{_TR_AY_ADLARI})\s+\d{{4}}"
)
RE_TARIH = _katlanmis_derle(_TARIH_TEK, re.IGNORECASE)
# Grup sayisi SABIT olmali (cagiran taraf hep grup 1/2 okur) - bu yuzden
# alternasyon ({_TARIH_TEK}) TEK bir yakalama grubunun ICINE alinir,
# hangi bicim eslesirse eslessin grup 1 = baslangic, grup 2 = bitistir.
RE_TARIH_ARALIGI = _katlanmis_derle(
    rf"({_TARIH_TEK})\s*[-–]\s*({_TARIH_TEK})",
    re.IGNORECASE,
)

# SIKISIK ARALIK - Turkce metin araligin ILK tarihini kisaltir
# (olculdu 25 Agustos 2026). Yukaridaki RE_TARIH_ARALIGI iki tarafta da
# TAM tarih bekledigi icin bu iki bicimde HIC eslesmiyordu; sonuc:
# kampanya_baslangic 52 kayitta bos kaliyordu (recall %66,45, precision
# %100 - yani hata tamamen KACIRMA'ydi, uydurma degil).
#
#   "kampanya 1 Agustos - 31 Agustos 2026"  -> ilk tarihte YIL yok
#   "kampanya 1 Temmuz - 31 Agustos 2026"   -> ilk tarihte YIL yok
#   "kampanya 1 - 31 Temmuz 2026"           -> ilk tarihte AY ve YIL yok
#
# Eksik parcalar BITIS tarihinden odunc alinir - metnin kendi mantigi da
# budur ("1 - 31 Temmuz 2026" okuyan insan da ayi ikinci taraftan alir).
#
# IKI DESEN AYRISIKTIR: yil-paylasimli bicimde ilk gunden sonra AY ADI
# gelir, ay-paylasimlida ise dogrudan TIRE gelir. Bu yuzden biri
# digerinin metnine eslesemez; sira guvenlik icin yine de ozelden genele.
#
# SAYI ORTASINDAN BASLAMA KORUMASI - `(?<![\d.,])`. Olculdu ve GERCEK
# HATAYA yol acti: bu koruma olmadan "10.000 TL - 31 Temmuz 2026"
# metninde `\d{1,2}` sayinin SONUNDAKI "00"i gun sanip "2026-07-00"
# uretiyordu. Bu yalnizca yanlis degil, KAYIT DUSURUCU bir degerdi -
# Postgres DATE sutunu reddediyor (DatetimeFieldOverflow) ve
# extraction/regex_ile_zenginlestir.py'nin toplu yazimi komple dusuyordu
# (tests/test_regex_ile_zenginlestir.py yakaladi).
_ARALIK_YIL_PAYLASIMLI = _katlanmis_derle(
    rf"(?<![\d.,])(\d{{1,2}})\s+({_TR_AY_ADLARI})\s*[-–]\s*"
    rf"(\d{{1,2}})\s+({_TR_AY_ADLARI})\s+(\d{{4}})",
    re.IGNORECASE,
)
_ARALIK_AY_PAYLASIMLI = _katlanmis_derle(
    rf"(?<![\d.,])(\d{{1,2}})\s*[-–]\s*(\d{{1,2}})\s+({_TR_AY_ADLARI})\s+(\d{{4}})",
    re.IGNORECASE,
)


def _gecerli_tarih_mi(iso: Optional[str]) -> bool:
    """ISO tarihin TAKVIMDE gercekten var oldugunu dogrular.

    IKINCI SAVUNMA HATTI: yukaridaki lookbehind deseni sayi ortasindan
    baslamayi engeller, ama `tarihe_cevir` gun/ay araligini HIC kontrol
    etmez - "00 Temmuz 2026" verilse "2026-07-00" doner. Cikarim
    katmaninin veritabanini dusurebilecek bir deger uretmemesi gerekir;
    bu yuzden kurulan tarih yazilmadan once dogrulanir.
    """
    if not iso:
        return False
    try:
        date.fromisoformat(iso)
    except ValueError:
        return False
    return True

# SITE FOOTER TARIH DAMGASI (olculdu 23 Agustos 2026, Dunya Katilim - 57
# kayit etkileniyor, 4'u altin veride yanlis pozitif olarak yakalandi:
# DK-001/002/003/004 hepsi AYNI tarihi ("17/08/2026") kampanya_bitis
# olarak aldi). Sebep: sitenin HER sayfasinin footer'inda "Son Guncelleme
# Tarihi: dd/mm/yyyy" damgasi var - bu SITE GENELI bir zaman damgasidir,
# o kampanyanin bitis tarihi degildir. Eski kod _ilk_eslesme ile SAYFADAKI
# ILK tarihi aliyordu ve footer genelde sayfa govdesinden once metne
# giriyordu (kaynak: <footer> HTML govdenin sonunda ama metin cikarma
# sirasi kaynagini garanti etmiyor).
_TARIH_BAGLAM_DISLAMA_KELIMELERI = _katla_hepsi([
    "son güncelleme", "güncelleme tarihi", "yayın tarihi",
    "tüm hakları saklıdır", "telif hakkı",
])


def _tarih_baglaminda_gecersiz_mi(metin: str, baslangic: int, bitis: int, pencere: int = 60) -> bool:
    """Tarihin AYNI CUMLESINDE onu site-geneli bir damga kilan kelime var mi?"""
    baglam = _cumleye_kirpilmis_baglam(metin, baslangic, bitis, pencere)
    return any(k in baglam for k in _TARIH_BAGLAM_DISLAMA_KELIMELERI)


# ILGISIZ KAMPANYA CAROUSEL'I - sayfanin KENDI icerigi biten yerden sonra
# baslayan "Diger Kampanyalar / Ilginizi Cekebilecek Kampanyalar" bolumu.
#
# OLCULDU (23 Agustos 2026, 4 gercek yanlis pozitif): Ziraat Katilim'in
# "A101'de 6 Taksit" sayfasi kendi icerigini bitirdikten sonra "SAYFAYI
# PAYLAS" ve ardindan baska kampanyalarin karti geliyor - "Veteriner ve
# Petshop Harcamalariniza 2000 TL Bankkart Lira!" gibi. Bu BASKA bir
# kampanyanin odulu, "A101'de 6 Taksit"in degil - ama motor tum ham_metin
# icinde arama yaptigi icin ilk gordugu odul ifadesini bu kampanyaya
# yaziyordu (ZK-009, ZK-014, ZK-015, VK-010 - hepsi ayni desen).
#
# NEDEN BASIT "BUL VE KES" YETMEZ (olculdu): "Diger Kampanyalar" gibi
# ayni ifadeler bazi bankalarda NAV MENU OGESI olarak sayfanin en
# BASINDA da geciyor (Turkiye Finans: konum toplam uzunlugun %1,7'sinde;
# Albaraka "Tum Kampanyalar": %3,9'da - "Size Ozel" kisisellestirme
# widget'i). Isareti kosulsuz kesme noktasi saymak bu sayfalarin TUM
# icerigini silerdi. Bu yuzden asagidaki iki koruma birlikte calisir:
#
#   1. Yalnizca corpus'ta CAROUSEL BASLANGICI oldugu DOGRULANMIS
#      ifadeler listelenir (asagida, min konum >= %58 olarak olculdu -
#      "Diger Kampanyalar" / "Tum Kampanyalar" listede YOK, cunku
#      Turkiye Finans/Albaraka'da nav ogesi olarak COK ERKEN cikiyor).
#   2. Yine de ASGARI ORAN esigi var: isaret sayfanin ilk %30'unda
#      geciyorsa GUVENILMEZ sayilir ve kesme yapilmaz - boylece daha
#      once test edilmemis bir bankada ayni ifadenin nav ogesi olarak
#      erken cikma ihtimaline karsi bir guvenlik agi kalir.
_ILGISIZ_ICERIK_DESENLERI = tuple(
    _katlanmis_derle(k)
    for k in (
        "sayfayi paylas",
        "tumunu goster",
        "ilginizi cekebilecek kampanyalar",
        # "İlginizi Çekebilir" (tekil) - Kuveyt Turk/T.O.M. Katilim/
        # Albaraka'nin kullandigi kisa bicim. OLCULDU (24 Agustos 2026):
        # T.O.M. Katilim'in 4 AYRI kampanya sayfasinda (TOM-007/009/011/
        # 012) BIREBIR AYNI carousel metni ("Hadi Alisveris Kredisi ile
        # Klima, Supurge ve Televizyonlarda Vade Farksiz 12 Taksit!")
        # bulundu - motor bunu HER dorduncu sayfaya "kendi" taksit
        # sayisi olarak yaziyordu. Corpus'ta 29 kayitta gecen, en erken
        # konumu %67,6 olan guvenilir bir isaret (esik %30'un uzerinde).
        "ilginizi cekebilir",
    )
)
_ILGISIZ_ICERIK_ASGARI_ORAN = 0.30


def _kendi_icerigine_kirp(ham_metin: str, katlanmis: str) -> tuple[str, str]:
    """Sayfanin KENDI icerigi bitip "diger kampanyalar" basladiginda kirpar.

    Kesme yapilmazsa (guvenilir bir isaret bulunamazsa) girdiler DEGISMEDEN
    doner - bu fonksiyon hicbir zaman mevcut davranisi KOTULESTIRMEZ.
    """
    adaylar = [
        m.start()
        for desen in _ILGISIZ_ICERIK_DESENLERI
        for m in (desen.search(katlanmis),)
        if m is not None
    ]
    esik = len(katlanmis) * _ILGISIZ_ICERIK_ASGARI_ORAN
    gecerli = [a for a in adaylar if a >= esik]
    if not gecerli:
        return ham_metin, katlanmis
    kirpma = min(gecerli)
    return ham_metin[:kirpma], katlanmis[:kirpma]

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
    rf"({_SAYI})\s*(?:TL|₺)",
    re.IGNORECASE,
)

# Odul ifadeleri cok cesitli: "5.000 TL degerinde alisveris ceki",
# "10.000 Mil'e varan hediye" (TL disi birim!), "250 TL ParafPara",
# "2.000 TL'ye varan Bankkart Lira" (banka-ozel sadakat birimleri),
# "1.000 TL'ye kadar iade", "1.250 TL Worldpuan".
# OLCULDU (23 Agustos 2026) - "indirim" anahtar kelimesi KALDIRILMAK
# ISTENDI, OLCUM REDDETTI: ZK-014 ("3.000 TL'ye Varan Indirim") ve VK-010
# ("200 TL Indirim") altin veride odul_miktari = "belirtilmemis" oldugu
# icin yanlis pozitif sayiliyor. "indirim" listeden cikarildiginda:
#     bos alan dogrulugu  %93,16 -> %93,96  (34 -> 30 yanlis pozitif)
#     dolu alan dogrulugu %84,42 -> %83,12  (2 dogru sonuc KAYBEDILDI)
#     makro F1            %78,39 -> %78,60  (+0,21 - gurultu seviyesinde)
# Yani altin veri setinin KENDISI tutarsiz: bazi kayitlarda indirim odul
# sayilmis, bazilarinda sayilmamis. Motoru tek yone cekmek toplam kaliteyi
# artirmiyor, yalnizca hatayi bir sutundan digerine tasiyor. Karar:
# DEGISIKLIK YAPILMADI; cozulmesi gereken yer gold'daki etiket kurali
# (bkz. docs/extraction_accuracy_raporu.md - gold etiket incelemesi).
#
# NOT: "nakit ödül"/"ödül" bilerek BURAYA eklenmedi - bu kelimeler genelde
# kisi-basi/birim tutari da tasir (ör. "500 TL nakit ödül... toplamda
# maksimum 10.000 TL"), .search() ILK eslesmeyi aldigi icin erken/yanlis
# (kisi basi) tutari yakalardi. Bu durumlar asagidaki RE_ODUL_TAVAN
# ("en fazla"/"maksimum" tetikleyicili) desenine birakildi.
# "hoş geldin" (DENETIM BULGUSU, 26 Agustos 2026, AL-018): "1.699 TL Hoş
# Geldin Hediyesi" gibi bir ifadede "TL" ile "hediye" arasina "hoş geldin"
# sifati giriyor, mevcut opsiyonel-kelime grubu ("değerinde"/"varan"/
# "kadar") bunu kapsamiyordu ve tutar hic bulunamiyordu. Yalnizca bu
# BILINEN ifade eklendi (genis bir "herhangi bir kelime" jokeri DENENMEDI -
# bilerek: dosya basindaki "ASIRI UYDURMA KONTROLU" ilkesiyle tutarli,
# genis joker baska baglamlarda alakasiz kelimeleri atlayip yanlis
# pozitif uretebilirdi).
# "bonus" (DENETIM BULGUSU, 26 Agustos 2026, TF-009): "650 TL Bonus
# Kazanın!" - "bonus" kelimesi "TL" ile "kazan" ANKORU arasina giriyor,
# ayni "hoş geldin" bulgusuyla ayni sinif (5 dosyada dogrulandi).
RE_ODUL = _katlanmis_derle(
    rf"{_SAYI}\s*(?:TL|₺)"
    r"(?:['’](?:ye|ya|e|a))?\s*"
    r"(?:değerinde\s*|varan\s*|kadar\s*|hoş\s*geldin\s*|bonus\s*)?"
    r"(?:alışveriş çeki|alışveriş kartı|hediye çeki|alışveriş puanı|hediye|kazan\w*"
    r"|indirim|bankkart lira|parafpara|worldpuan|nakit iade\w*|iade\b)",
    re.IGNORECASE,
)
# Banka-ozel sadakat birimleri (Mil, Gram) TL disinda oldugu icin ayri
# desenler gerekir. NOT: gercek metinlerde egik/tipografik apostrof (’,
# U+2019) kullanilir, duz apostrof (') degil - ikisi de kapsanmali.
#
# "hediye|firsat" (DENETIM BULGUSU, 26 Agustos 2026, KT-020/030/031/041):
# Kuveyt Turk'un Miles&Smiles Business Kart kampanyalari "X Mil'e Varan
# HEDIYE" degil "X Mil'e Varan FIRSAT!" basligini kullaniyor (7 dosyada
# dogrulandi, hepsi gercekten kendi odul miktarini basliginda tasiyan
# kampanyalar - baska hicbir baglamda yanlislikla eslesme riski
# gozlenmedi).
RE_ODUL_MIL = _katlanmis_derle(rf"{_SAYI}\s*Mil['’]?[ea]?\s*varan\s*(?:hediye|fırsat)", re.IGNORECASE)
# Tavan/limit ifadeleri: "en fazla 5 gram", "maksimum 10.000 TL", "kişi
# başı maksimum 2.000 TL, toplamda ... maksimum 10.000 TL nakit ödül" gibi
# cok sayida aday oldugunda SONUNCUSU (genelde "toplamda" olan) tercih
# edilir - finditer + son eslesme.
# "maximum" (Ingilizce yazim, DK-015'te dogrulandi - "kazanilabilecek
# MAXIMUM iade 1.000 TL'dir") gercek banka metinlerinde "maksimum"un
# yaninda kullanilan yaygin bir alternatif yazim.
RE_ODUL_TAVAN = _katlanmis_derle(
    r"(?:en fazla|maksimum|maximum)\s+(?:\S+\s+){0,4}?"
    rf"({_SAYI})\s*(TL|₺|gram\w*|gr\b)",
    re.IGNORECASE,
)
# "2.500 TL ile sınırlıdır" gibi "sinirli/sinirlidir" ile biten tavan ifadesi.
RE_ODUL_SINIRLI = _katlanmis_derle(
    rf"({_SAYI})\s*(TL|₺)['’]?\s*(?:ile\s+)?s[ıi]n[ıi]rl[ıi]",
    re.IGNORECASE,
)
RE_ODUL_GRAM = _katlanmis_derle(
    rf"{_SAYI}\s*gram\w*\s*(?:['’]?[ea]?\s*kadar\s*)?(?:hediye|kazan\w*)", re.IGNORECASE
)

# Kampanya turu anahtar kelimeleri - degerler api/schemas.py KampanyaTuru
# enum'iyla BIREBIR ayni olmali (Havin/Sara'nin sozlesmesi bozulmasin diye).
#
# KART ANAHTARLARI GENISLETILDI (olculdu 25 Agustos 2026, altin veri seti /
# 288 canli+imzali kayit). Eklenen: "kartla", "kart sahip".
#
# NEDEN: eski dort anahtar ("kredi kart", "kart avantaj", "kart kampanya",
# "bankkart") gercek kampanya metinlerinde neredeyse hic gecmiyordu -
# siniflandirilamayan 42 Kart kampanyasinin HICBIRINDE "kredi karti"
# yazmiyor, buna karsilik 22'sinde "...kartla yapilan harcamalarda",
# 6'sinda "kart sahipleri" geciyordu. Bankalar kart urununu tam adiyla
# degil ekli/cogul biciminde yaziyor ("Paraf kartlarla", "Saglam Kart
# sahiplerine"). Alt-dize eslesmesi kullanildigi icin "kartla" ayni
# zamanda "kartlar"/"kartlari"/"kartlarla" bicimlerini de kapsar -
# bu KASITLIDIR, tek anahtarla tum ek varyantlari yakalar.
#
# "paraf" ANAHTARI BILINCLI OLARAK EKLENMEDI: tek basina denendiginde
# F1'i 53,31 -> 71,64 cikariyor ama nihai sete eklendiginde 73,72 ->
# 73,36'ya DUSURUYOR (yeni bir dogru getirmiyor, yalnizca DK-007'yi
# calıyor). "kartla" zaten ayni kayitlari zaten yakaliyor ve markaya
# bagimli degil - bkz. docs/kampanya_turu_olcum_raporu.md.
#
# "parafpara" ANAHTARI "Alisveris Puani"NDA KALDI: kaldirilmasi olculdu,
# F1'i DEGISTIRMEDI (73,72). Sozlukte "Kart Kampanyasi" zaten "Alisveris
# Puani"ndan ONCE geldigi ve ilk eslesme kazandigi icin ParafPara'li kart
# kampanyalari dogru sinifa gidiyor; "parafpara" gercek bir puan
# kampanyasinda hala tek sinyal olabilir, bilgi tasiyan anahtari bedava
# atmanin anlami yok.
#
# SIRA DEGISIKLIGI DENENDI VE ALINMADI: "Kart Kampanyasi"ni en one almak
# nav bastirma OLMADAN +7,20 kazandiriyordu (kok nedeni ortmek pahasina),
# nav bastirma acikken ise F1'i 72,69 -> 71,97'ye DUSURUYOR. Sira
# oldugu gibi birakildi.
#
# "Finansman Kampanyasi"NIN EN SONDA OLMASI KASITLIDIR (dogrulandi):
# tek anahtari "finansman" ve cok genel - one alindiginda F1 73,72 ->
# 60,95'e duser. Sinifi tamamen kaldirmak 73,84 verir (+0,12, 6 destekli
# bir sinifta gurultu duzeyinde); enum uyesi oldugu icin KALDIRILMADI.
KAMPANYA_TURU_ANAHTAR_KELIMELERI = {
    # --- EN OZEL TURLER EN BASTA (25 Agustos 2026, olculdu) -------------
    # Bu uc tur asagidaki genel turlerden ONCE denenmelidir: hepsi ayni
    # zamanda birer KART kampanyasidir ("Saglam Business Kart", "Taksitli
    # POS"), yani "Kart Kampanyasi" once gelseydi ucunu de yutardi.
    # Olculdu: uc sinif EN BASTA -> kampanya_turu F1 %74,09 -> %78,55;
    # ayni uc sinif EN SONDA -> yalnizca %74,55.
    #
    # "ticari" ve "kobi" DENENDI VE ALINMADI: F1'i %47,93'e dusuruyor -
    # iki kelime de bankalarin urun menusunde/altbilgisinde her sayfada
    # geciyor. Ayirt edici olan URUN ADIDIR ("business kart"), sifat degil.
    # "tohum kart" da alinmadi: +0,36 getiriyor ama acikca uydurma olan
    # "fugevet" anahtari +0,22 veriyor - yani kazanc kuraldan degil tek
    # kayittan geliyor (bkz. docs/kampanya_turu_olcum_raporu.md Bolum 12).
    "Ticari Kampanya": ["business kart", "bayi kart", "ihracat"],
    "Sigorta/BES Kampanyasi": ["bireysel emeklilik", "bes planı"],
    "POS Kampanyasi": ["pos kampanya"],
    #
    # "Musteri Ol Kampanyasi" ve "Katilma Hesabi Kampanyasi" BILEREK
    # BURADA YOK - enum'da varlar (api/schemas.py) ama regex kurallari
    # olculdu ve F1'i DUSURDULER: "müşterisi ol"/"müşterimiz ol" -4,46
    # (bu ifade sayfalarin cogunda pazarlama kalibi olarak geciyor),
    # "katılım hesab" -0,28. Kural eklemek yerine bos birakmak, yanlis
    # etiket uretmekten iyidir; bu iki tur NER/LLM katmaninin isi.
    "Konut Finansmani Kampanyasi": ["konut finansman", "ev sahibi", "konut alım"],
    "Tasit Finansmani Kampanyasi": ["taşıt finansman", "araç finansman", "otomobil"],
    "Ihtiyac Finansmani Kampanyasi": ["ihtiyaç finansman"],
    # "Yeni Musteri" KART'TAN ONCE (olculdu 25 Agustos 2026): yeni musteri
    # kazanim kampanyalari genelde bir kart urunuyle sunuluyor, bu yuzden
    # Kart once denendiginde 10 kayit "Kart Kampanyasi"na kayiyordu.
    # Sozlugun kendi ilkesi zaten ozelden genele - yeni musteri kazanimi
    # kart kampanyasindan DAHA OZEL bir niyet.
    # F1 %78,55 -> %79,27; TP 216->218, FP 46->44, FN 72->70 (uc sayacta
    # da iyilesme - hata takasi degil).
    "Yeni Musteri Kampanyasi": ["yeni müşteri", "yeni ev sahibi olmak isteyen"],
    "Kart Kampanyasi": [
        "kredi kart", "kart avantaj", "kart kampanya", "bankkart",
        "kartla", "kart sahip",
    ],
    "Alisveris Puani Kampanyasi": ["alışveriş puan", "puan kazan", "parafpara"],
    "Yatirim Urunu Kampanyasi": ["katılım fonu", "yatırım ürün", "birikim"],
    "Finansman Kampanyasi": ["finansman"],
}

# TEK KAYNAK - api/schemas.py::KampanyaTuru enum'iyla BIREBIR AYNI olmali
# (bkz. o enum'un docstring'i). llm_extractor.py bu tuple'i, LLM'in
# kampanya_turu icin GECERSIZ/hayali bir etiket uydurmasini onlemek
# icin dogrulama/normallestirme amaciyla import eder - regex'in kendi
# KAMPANYA_TURU_ANAHTAR_KELIMELERI sozlugu yalnizca regex'in DENEYIP
# BASARILI oldugu alt kumeyi icerir (ör. "Musteri Ol Kampanyasi" ve
# "Katilma Hesabi Kampanyasi" regex kurali olarak denendi ve F1'i
# dusurdugu icin BILEREK regex sozlugunde YOK - bkz. o dosyadaki
# docstring - ama LLM'in bu iki turu SINIFLANDIRABILMESI icin tam
# enum burada tutulur).
KAMPANYA_TURU_TUM_DEGERLER = (
    "Konut Finansmani Kampanyasi",
    "Ihtiyac Finansmani Kampanyasi",
    "Tasit Finansmani Kampanyasi",
    "Finansman Kampanyasi",
    "Kart Kampanyasi",
    "Alisveris Puani Kampanyasi",
    "Yeni Musteri Kampanyasi",
    "Yatirim Urunu Kampanyasi",
    "Ticari Kampanya",
    "Musteri Ol Kampanyasi",
    "Sigorta/BES Kampanyasi",
    "Katilma Hesabi Kampanyasi",
    "POS Kampanyasi",
    "Belirlenemedi",
)

# HEDEF KITLE - Sartname Md. 5.3 "Hedef Kitle Bilgileri" sutunundaki DORT
# segment. Sartname bu alani serbest metin olarak degil KATEGORI olarak
# tanimliyor: "Yeni Musterilere Ozel", "Mevcut Musterilere Ozel", "Maas
# Musterilerine Ozel", "Belirli Musteri Segmentlerine Yonelik".
#
# NEDEN DORDUNCU SEGMENT EKLENDI (olculdu 23 Agustos 2026): altin veri
# setinde hedef_kitle 299 kayitta dolu ama 177 TEKIL serbest metin degeri
# var ("Ziraat Katilim Bankkart kredi karti sahipleri (ucretsiz ve ticari
# kartlar haric)" gibi). Motor yalnizca ilk uc kategoriyi uretebildigi
# icin alan bazli olcumde F1 = %0,00 cikiyordu - 287 destekle. Bu bir
# motor zayifligi DEGIL, olculemez bir karsilastirmaydi: 177 farkli
# serbest metni 3 kategoriyle tam eslestirmek matematiksel olarak
# imkansiz. Sartnamenin dorduncu segmenti tam bu vakayi karsiliyor.
#
# CATCH-ALL DEGIL - KANIT ISTER: "Belirli segment" yalnizca metinde
# ACIK bir uygunluk ifadesi varsa atanir ("... kart sahipleri", "...
# musterilerine ozel"). Her kayda varsayilan olarak yazilsaydi olcum
# bedava yukselirdi; oyle bir kural bilgi tasimaz.
HEDEF_KITLE_ANAHTAR_KELIMELERI = {
    "Yeni müşteri": [
        "yeni müşteri", "yeni ev sahibi olmak isteyen", "ilk kez",
        "yeni kart müşteri", "müşterimiz olun", "yeni müşterilere",
    ],
    "Maaş müşterisi": ["maaş müşteri", "maaş getiren", "maaşını", "emekli"],
    "Mevcut müşteri": ["mevcut müşteri", "mevcut müşterilere"],
    # "kart sahib" EKLENDI (olculdu 25 Agustos 2026): mevcut anahtarlarin
    # hepsi COGUL/YALIN yazimdi ("kart sahipleri"), sayfalar ise cekimli
    # yaziyor ("kart sahibinin", "kart sahibi olan"). Govdeye inince 18
    # yeni dogru geliyor, 3 yanlis pozitif pahasina:
    #     hedef_kitle F1 %22,78 -> %34,75, precision %69,23 -> %75,00
    #
    # BU ALANDA METRIK YANILTICIDIR - OLCUM KONTROLU SART: gold'da
    # "Belirli segment" baskin sinif (283 kayittan 173'u). Bu yuzden GENIS
    # ates eden her kural bedava kazanir. Olculdu: hicbir bilgi tasimayan
    # saf catch-all "kampanya" (sayfalarin %100'unde geciyor) F1 %88,89
    # veriyor - eklenen gercek anahtarlarin HEPSINDEN yuksek. Dolayisiyla
    # buradaki bir F1 artisi TEK BASINA kanit degildir; anahtarin ates
    # orani ve bilgi tasiyip tasimadigi ayrica bakilmalidir.
    #
    # REDDEDILEN ADAYLAR (F1'i yukseltiyorlardi, yine de alinmadilar):
    #   "faydalanabil"  F1 %78,63, ates orani %57 - uygunluk cumlesinin
    #                   fiili sanildi. KONTROL CURUTTU: pazarlama bicimi
    #                   "faydalanabilirsiniz" (%45,59) ile uygunluk bicimi
    #                   "faydalanabilir" (%46,72) neredeyse AYNI skoru
    #                   veriyor - ayrim bilgi tasimiyor, ikisi de yalnizca
    #                   "detayli kampanya sayfasi" demek.
    #   "kampanyadan"   F1 %83,33, ates orani %78 - ayni sebep.
    #   "kart"          F1 %89,08 - acik catch-all.
    #
    # DENENDI VE HICBIR SEY YAPMADI (korpusta gecmiyor): "kartı bulunan",
    # "kartı olan", "sahibi olan", "kart müşteri", "kart hamil",
    # "sahipleri faydalan", "kullanıcıları faydalan". Bu yedisi birlikte
    # eklendiginde sonuc tek basina "kart sahib"ten DAHA KOTU (%34,48).
    #
    # SONUC: bu alanin recall'u regex ile ~%23'un uzerine cikarilamaz -
    # cikarilabildigi tek yol sinif onceligini somurmek ve o bilgi
    # tasimaz. Gercek cozum uygunluk CUMLESINI cikarip ozetlemektir
    # (NER/LLM katmani); bkz. docs/kampanya_turu_olcum_raporu.md.
    "Belirli segment": [
        "kart sahipleri", "kart sahiplerine", "kartı sahipleri",
        "kart sahib",
        "müşterilerine özel", "sahiplerine özel", "kart müşterileri",
        "kullanıcılarına özel", "üyelerine özel",
    ],
}

# SIRA ONEMLI: bir metin birden fazla ipucu tasiyabilir. Sira ozelden
# genele gider - en bilgi verici segment once yakalanir. "Maas musterisi"
# ilk sirada: maas/emekli ifadesi cok belirgin bir sinyal ve olculdu
# (TF-002) ki "yeni musteri" once denenirse "emekli maasini tasiyan yeni
# musteriler" yanlis segmente dusuyor.
HEDEF_KITLE_SIRASI = ("Maaş müşterisi", "Yeni müşteri", "Mevcut müşteri", "Belirli segment")

# DESEN GENISLETMESI DENENDI VE GERI ALINDI (23 Agustos 2026, olculdu).
#
# Alt-dize yerine regex kullanip "yeni ... musteri" bosluklu kalibi ve
# "yalnizca ... kart ile" uygunluk kosulunu da yakalamayi denedim. Tek
# tek denemelerde dogru calisiyordu (KT-005, ZK-002, TF-002 duzeliyordu)
# ama TOPLAM olcumde geriletti:
#
#     hedef_kitle F1  %30,00 -> %27,59
#     precision       %63,16 -> %48,00
#     recall          %19,67 -> %19,35   (yani yeni dogru sonuc GELMEDI)
#
# Sebep: altin verideki hedef_kitle etiketi bir INSAN OZETI ("Bireysel
# Bankkart kredi karti sahipleri"); o ozet sayfada aynen gecmiyor ve
# sayfadaki uygunluk kosullari cogu zaman segmenti TEK BASINA belirlemeye
# yetmiyor. Genis desenler bu yuzden yalnizca yanlis segment atamasi
# uretti. Bu alanin recall'unu yukseltmek kural genisletmekle degil,
# muhtemelen NER/LLM katmaniyla mumkun - regex'in dogru isi burada
# emin oldugu az sayida vakayi yakalamak.
_HEDEF_KITLE_KATLANMIS = {
    etiket: _katla_hepsi(kelimeler)
    for etiket, kelimeler in HEDEF_KITLE_ANAHTAR_KELIMELERI.items()
}


def hedef_kitle_segmenti(metin: Optional[str]) -> Optional[str]:
    """Serbest metni Sartname Md. 5.3 segmentlerinden birine indirger.

    TEK KAYNAK OLMASI ONEMLI: hem cikarim motoru (kampanya sayfasindan)
    hem dogruluk olcumu (altin verideki serbest metin etiketinden) AYNI
    fonksiyonu cagirir. Iki taraf ayri kural kullanirsa olcum, motorun
    basarisini degil iki kural arasindaki farki olcer.

    IDEMPOTENT OLMAK ZORUNDA (olculdu 25 Agustos 2026): girdi ZATEN bir
    segment etiketiyse oldugu gibi doner. Olcum tarafi bu fonksiyonu IKI
    tarafa da uyguluyor (scraper/scripts/extraction_accuracy.py,
    ALAN_NORMALIZE) - gold serbest metindir ve donusmesi gerekir, ama
    motorun ciktisi zaten etikettir ve ikinci kez donusturulmemelidir.
    Dort etiketin ucu bu ikinci gecisten kendiliginden sag cikiyordu
    ("Yeni müşteri" metni "yeni müşteri" anahtarini icerir), ama
    "Belirli segment" HICBIR anahtarini icermiyor ve None'a dusuyordu:
    motor DOGRU cevabi uretse bile olcum onu kacirma sayiyordu.
    Bedeli olculdu: hedef_kitle'nin 182 kacirmasinin 164'u tam olarak bu
    hucreydi ("Belirli segment" -> None). Guard eklenince, TEK BIR KURAL
    DEGISMEDEN F1 %14,16 -> %22,78.
    """
    if not metin:
        return None
    if metin in HEDEF_KITLE_SIRASI:
        return metin  # zaten etiket - yeniden cozumlemeye calisma
    metin_l = turkce_ascii_kucult(metin)
    for etiket in HEDEF_KITLE_SIRASI:
        if any(k in metin_l for k in _HEDEF_KITLE_KATLANMIS[etiket]):
            return etiket
    return None

# YALNIZCA DEGERLER (aranacak kelimeler) katlanir - ANAHTARLAR katlanmaz:
# onlar cikti etiketidir ve api/schemas.py'deki enum degerleriyle BIREBIR
# ayni kalmalidir ("Yeni müşteri" etiketi "Yeni musteri"ye donusmemeli,
# yoksa Havin/Sara'nin sozlesmesi bozulur).
_KAMPANYA_TURU_KATLANMIS = {
    etiket: _katla_hepsi(kelimeler)
    for etiket, kelimeler in KAMPANYA_TURU_ANAHTAR_KELIMELERI.items()
}
# NOT: hedef kitle icin ayri bir katlanmis sozluk TUTULMUYOR - segment
# kurali `hedef_kitle_segmenti` icinde, cagri aninda katlanarak
# uygulaniyor. Iki yerde iki kopya, olcum tarafiyla motorun ayrisma
# riskini geri getirirdi.


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


# Banka-ozel sadakat birimleri. Degerler altin veri setindeki yazimla
# BIREBIR ayni olmali - olcum tam dize karsilastirmasi yapar.
_ODUL_BIRIMI_ANAHTARLARI = (
    ("bankkart lira", "Bankkart Lira"),
    ("parafpara", "ParafPara"),
    ("worldpuan", "Worldpuan"),
    ("altın puan", "Altin Puan"),
)
_ODUL_BIRIMI_KATLANMIS = tuple(
    (turkce_ascii_kucult(anahtar), birim) for anahtar, birim in _ODUL_BIRIMI_ANAHTARLARI
)


def _odul_birimini_tespit_et(
    ham_metin: str, baslangic: int, bitis: int, pencere: int = 80
) -> str:
    """Odulun HANGI birimde verildigini eslesmenin CUMLESINDEN tespit eder.

    KAPSAM GENISLETILDI (olculdu 25 Agustos 2026). Eskiden yalnizca
    RE_ODUL'un ESLESEN PARCASINA bakiyordu; birim sozcugu ise cogu
    kampanyada o parcanin DISINDA, ayni cumlenin baska yerinde geciyor:

        "600 TL'ye varan ALTIN PUAN firsati! ... maksimum kazanim tutari 600 TL"
                                                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                                 eslesen parca - birim yok

    Sonuc: tutar DOGRU bulunuyor ama birim "TL" yaziliyordu. Olculdu -
    odul_birimi'nin 20 hatasinin 7'si tam olarak buydu (KT-024/029/038/039
    "Altin Puan", KT-022 "Mil", TEK-030 "ParafPara", DK-009).

    CUMLEYE KIRPILMIS pencere kullanilir (duz karakter penceresi degil):
    komsu cumledeki bir birim sozcugu bu odule ait DEGILDIR - ayni gerekce
    _tutar_baglaminda_gecersiz_mi ve _odul_baglaminda_mi'da da var.

    "altın puan" ANAHTARI EKLENDI: Kuveyt Turk'un sadakat birimi; sozlukte
    hic yoktu, bu yuzden dort kampanyada "TL" yaziliyordu.
    """
    baglam = _cumleye_kirpilmis_baglam(ham_metin, baslangic, bitis, pencere)
    for anahtar, birim in _ODUL_BIRIMI_KATLANMIS:
        if anahtar in baglam:
            return birim
    return "TL"


# Menu/altbilgi satiri esigi: bu uzunlugun altinda VE hic cumle izi
# (noktalama/rakam) tasimayan satirlar baglanti etiketi sayilir.
# Duyarlilik olculdu (25 Agustos 2026): 30/40/50/60 esiklerinde F1
# sirasiyla 73,36 / 73,72 / 73,72 / 73,36 - yani sonuc esigin tam
# degerine bagli DEGIL, genis bir platoda ayni. Tek bir sayiya
# ayarlanmis kirilgan bir kural degil.
_MENU_SATIRI_ESIGI = 40
_CUMLE_IZI = re.compile(r"[.,:;!?%0-9]")

# KISA METIN KORUMASI: filtre yalnizca SAYFA gorunumlu girdilerde calisir.
# POST /cikar ucu ve MetinAnalizi ekrani kullaniciyi tek cumlelik metin
# yapistirmaya davet ediyor - "Kredi karti kampanyasi" gibi bir girdi
# kisadir ve noktalama tasimaz, yani menu satiri kriterine UYAR ve
# koruma olmadan tamamen silinip alan SESSIZCE bos donerdi (tam olarak
# tests/test_regex_extractor.py'deki diyakritik bulgusunun ayni turu).
# Olculdu: gercek scrape edilmis sayfalarda en az 8 dolu satir var
# (medyan 32,5), esik bu tabanin altina konmadi. Korumanin altin veri
# seti sonucuna etkisi YOK - 0/3/5/8/10/15 esiklerinin hepsinde F1 73,72.
_ASGARI_SAYFA_SATIRI = 8


def menu_satirlarini_ayikla(metin_l: str) -> str:
    """Sayfa menusu/altbilgi baglantilarini tur siniflandirmasindan cikarir.

    NEDEN VAR (olculdu 25 Agustos 2026, 288 canli+imzali altin kayit):
    kampanya_turu hatalarinin en buyuk tek kaynagi anahtar kelime EKSIGI
    degil, KAMPANYA DISI METINDEN eslesmeydi. "konut finansman" anahtari
    36 kayitta kampanya metninden degil sayfanin alt menusunden
    eslesiyordu:

        ...| finansmanlar | sigortalar | konut finansmani | arac finansmani |...

    Bu 36 kaydin GOLD ETIKETI "Kart Kampanyasi"ydi; motor menuye bakip
    "Konut Finansmani Kampanyasi" diyordu. Yani hata siniflandiricinin
    kelime dagarciginda degil, GIRDI METNININ KAPSAMINDAYDI - hangi
    anahtar eklenirse eklensin menu her sayfada aynen duruyor ve ilk
    eslesmeyi kazanmaya devam ediyordu.

    AYIRT EDICI OZELLIK: menu satirlari kisa, bagimsiz baglanti
    etiketleridir - noktalama ve rakam tasimazlar. Kampanya govde
    cumleleri ("...toplamda 12.500 TL harcama sarti aranir.") her ikisini
    de tasir. Bu yuzden filtre uzunluk + cumle izi ikilisine dayanir;
    kelime listesi tutmaz (banka basina menu metni farklidir, liste
    tutmak her yeni banka eklendiginde sessizce bozulurdu).

    OLCUM (yalniz bu degisiklik, sozluk sabit): kampanya_turu
    F1 %44,32 -> %53,31, precision %48,75 -> %60,62.

    KAPSAMI BILINCLI OLARAK DAR: yalnizca `_kampanya_turunu_tespit_et`
    cagirir. Tutar/tarih/oran desenleri HAM metin uzerinde calismaya
    devam eder - onlar zaten sayi/noktalama iceren satirlarla eslesiyor,
    yani bu filtreden fayda gormezler ama bir regresyon riski tasirlar.
    """
    satirlar = [s for s in (x.strip() for x in metin_l.split("\n")) if s]
    if len(satirlar) < _ASGARI_SAYFA_SATIRI:
        return metin_l  # sayfa degil, yapistirilmis kisa metin - dokunma
    tutulan = [
        s
        for s in satirlar
        if not (len(s) <= _MENU_SATIRI_ESIGI and not _CUMLE_IZI.search(s))
    ]
    # Her satir elendiyse filtre bu girdi icin anlamli degil demektir;
    # bos metin dondurmek alani sessizce None yapardi.
    return "\n".join(tutulan) if tutulan else metin_l


def _kampanya_turunu_tespit_et(metin: str) -> Optional[str]:
    metin_l = menu_satirlarini_ayikla(turkce_ascii_kucult(metin))
    for etiket, kelimeler in _KAMPANYA_TURU_KATLANMIS.items():
        for k in kelimeler:
            idx = metin_l.find(k)
            if idx == -1:
                continue
            if etiket == "Ticari Kampanya" and _ticari_olumsuzlanmis_mi(metin_l, idx, len(k)):
                # DENETIM BULGUSU (26 Agustos 2026, AL-006/010/011/013/014/
                # 016): Albaraka'nin genel kart kampanyalarinda "Business
                # kartlar[in tamami] ... dahil degildir" gibi bir ISTISNA
                # cumlesi var - "business kart" burada kampanyanin KENDISI
                # DEGIL, kampanyadan HARIC TUTULAN bir kart tipi. Eski kural
                # yalnizca kelimenin gecip gecmedigine bakiyordu; bu 6 kayit
                # gercekte "Kart Kampanyasi" iken yanlislikla "Ticari
                # Kampanya" sayiliyordu. Digitle kelimelerdeki (0.7 sabit
                # guven) bu tur bir olumsuzlama baska hicbir kategoride
                # gozlenmedi (yalnizca bu 3 anahtarda - business kart/bayi
                # kart/ihracat - denetlendi), guard bu kategoriye ozgu
                # birakildi.
                continue
            return etiket
    return None


_TICARI_OLUMSUZLAMA_DESENI = re.compile(r"dahil\s*degil", re.IGNORECASE)


def _ticari_olumsuzlanmis_mi(metin_l: str, idx: int, uzunluk: int, pencere: int = 60) -> bool:
    return bool(_TICARI_OLUMSUZLAMA_DESENI.search(metin_l[idx : idx + uzunluk + pencere]))


def _hedef_kitleyi_tespit_et(metin: str) -> Optional[str]:
    """Kampanya metninden hedef kitle SEGMENTINI belirler.

    Paylasilan `hedef_kitle_segmenti` uzerinden gider - olcum tarafi da
    ayni fonksiyonu cagirdigi icin iki taraf hicbir zaman ayrisamaz.
    """
    return hedef_kitle_segmenti(metin)


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


# DENETIM BULGUSU (26 Agustos 2026, zayif alanlarin toplu incelemesi):
# Dunya Katilim (dunyakatilim.com.tr) sayfalarinin ham_metni, sayfanin
# KENDI kampanya icerigi bittikten SONRA "Diğer Kampanyalar" basligiyla
# TAMAMEN ILGISIZ baska kampanyalarin basligini/aciklamasini/bitis
# tarihini, ardindan TUM sitenin footer navigasyon menusunu (ÜRÜN VE
# HİZMETLER, HAKKIMIZDA, ...) iceriyor. Olculdu (DK-008/009/016/023/
# 029/034): bu blokta gecen BASKA bir kampanyanin "6 Aya Varan Taksit"
# gibi ifadeleri, mevcut kaydin KENDI taksit_sayisi'ymis gibi yanlislikla
# eslesiyordu - ayni kirlenme prensipte kampanya_bitis/odul/tutar
# alanlarini da etkileyebilir, sadece bu 6 kayitta rastlantiyla
# taksit_sayisi'ne carpti.
#
# KONUM (sabit karakter indeksi) GUVENLI DEGIL: ayni "Diğer Kampanyalar"
# basligi Turkiye Finans sayfalarinda TEPEDE bir kategori menusu olarak
# geciyor (idx~194-993, gercek icerikten ONCE) - dunyakatilim'in kendi
# araligiyla (idx 687-5052) CAKISIYOR, yani "yeterince ileride mi" gibi
# bir esik ikisini ayirt edemez (olculdu, karsilastirildi).
#
# Bunun yerine sayfanin KENDI marka kimligi kullanilir: yalnizca Dunya
# Katilim'a OZGU, HER sayfanin footer'inda gecen ("© 2026 Dünya Katılım
# Bankası A.Ş...") bir ifade metinde varsa bu kirpma uygulanir - 57/57
# dunyakatilim kaydinda var, diger 6 bankanin 441 kaydinin HICBIRINDE yok
# (dogrulandi). Boylece kaydi_cikar'in imzasi degismez, banka/URL
# parametresi tasimaya gerek kalmaz, 22 cagiran dosya etkilenmez.
_DUNYAKATILIM_KIMLIK_ISARETI = "Dünya Katılım Bankası"
_DUNYAKATILIM_GURULTU_SINIRI = "Diğer Kampanyalar"


def _sayfa_gurultusunu_kirp(ham_metin: str) -> str:
    """Bilinen banka sablonlarinda, gercek kampanya icerigi bittikten
    SONRA gelen ilgisiz "diger kampanyalar" listesini / site geneli
    footer menusunu kirpar. Yalnizca imzasi dogrulanmis sablonlarda
    calisir - eslesme yoksa metin degismeden doner."""
    if _DUNYAKATILIM_KIMLIK_ISARETI in ham_metin:
        idx = ham_metin.find(_DUNYAKATILIM_GURULTU_SINIRI)
        if idx != -1:
            return ham_metin[:idx]
    return ham_metin


def kaydi_cikar(ham_metin: str) -> dict:
    """Tek bir kampanya metnini analiz edip api/schemas.py CampaignRecord
    ile UYUMLU alan adlariyla bir sozluk doner.

    Bulunamayan alanlar None kalir - UYDURMA DEGER URETILMEZ (rapor Bolum
    5.7/15). `_izler` alani, hangi alanin hangi metin parcasindan ve hangi
    guvenle cikarildigini tasir (Juri Audit Paneli / hata ayiklama icin).
    """
    ham_metin = _sayfa_gurultusunu_kirp(ham_metin)
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
        "nakit_iade_orani": None,
        "indirim_orani_percent": None,
    }
    izler: dict[str, tuple[str, float]] = {}  # alan -> (kaynak_span, guven)

    # TUM desen aramalari KATLANMIS metinde yapilir (diyakritiksiz yazilmis
    # metin de eslessin diye - bkz. dosya basindaki "Diyakritik katlama").
    # Katlama uzunlugu korudugu icin eslesme offset'leri ham metinde ayni
    # yeri gosterir; kanit izleri `_ham_span` ile HAM metinden kesilir.
    # Baglam yardimcilari (_ucret_baglaminda_mi vb.) ham metni alir - onlar
    # kendi icinde `turkce_ascii_kucult` uyguluyor.
    katlanmis = turkce_ascii_katla(ham_metin)

    # ILGISIZ KAMPANYA CAROUSEL'I kirpilir (bkz. _kendi_icerigine_kirp
    # docstring'i). TEK NOKTADA yapilir: bu fonksiyondaki HER alan asagida
    # `ham_metin`/`katlanmis` degiskenlerini kullaniyor, tek bir kirpma
    # tum alanlari (odul, tarih, taksit, tutar, kar payi, kampanya_turu)
    # aynı anda korur - her deseni ayri ayri yamak yerine.
    ham_metin, katlanmis = _kendi_icerigine_kirp(ham_metin, katlanmis)

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
        else:
            # RE_VADE_FARKSIZ BURADA ARTIK YOK (23 Agustos 2026).
            # Bkz. desen tanimlari bolumu - kart taksit ifadesi, finansman
            # kar payi degildir.
            # SIRA ONEMLI - YONLENDIRME, ELEMEDEN ONCE GELIR.
            #
            # OLCULDU (23 Agustos 2026): baglam korumalari (_ucret_baglaminda_mi
            # ve _oran_tablosu_baglaminda_mi) once kosuyordu ve nakit iade /
            # indirim yuzdesini `continue` ile atiyordu. Sonuc: yuzde
            # kar_payi'na DOGRU sekilde girmiyordu ama dogru alanina da
            # (nakit_iade_orani / indirim_orani_percent) hic yazilmiyordu -
            # bilgi sessizce kayboluyordu. "Tum harcamalarinizda %10 nakit
            # iade" cumlesinde `harcama` kelimesi ucret dislama listesinde
            # oldugu icin eleme once tetikleniyordu.
            #
            # Dogru sira: bir yuzdenin NE OLDUGU belirlenebiliyorsa once
            # oraya yazilir; yalnizca hicbir alana ait olmadigi anlasilanlar
            # atilir. Eleme, siniflandirmanin yerine gecmemeli.
            for gm in RE_KAR_PAYI_GENEL.finditer(katlanmis):
                # Nakit iade veya indirim baglamindasak kar payi DEGIL -
                # bu yuzden nakit_iade_orani / indirim_orani_percent'e
                # cikarip kar_payi_orani'na GIRME.
                span_ham = _ham_span(ham_metin, gm)
                if RE_NAKIT_IADE.search(katlanmis[max(0, gm.start()-50):gm.end()+50]):
                    yuzde = yuzdeye_cevir(span_ham)
                    if yuzde is not None:
                        # BIRIM: yuzdeye_cevir ONDALIK doner (%10 -> 0.1).
                        # Bu alanlar YUZDE tasiyor (alan adi da oyle diyor:
                        # indirim_orani_percent) - _kar_payi_ata ile ayni
                        # donusum uygulanmali, yoksa "%10 nakit iade"
                        # arayuzde %0,1 olarak gorunur.
                        alanlar["nakit_iade_orani"] = round(yuzde * 100, 4)
                        izler["nakit_iade_orani"] = (span_ham, 0.8)
                    continue  # kar_payi'na girme
                if RE_INDIRIM_ORANI.search(katlanmis[max(0, gm.start()-50):gm.end()+50]):
                    yuzde = yuzdeye_cevir(span_ham)
                    if yuzde is not None:
                        # Ayni birim gerekcesi (bkz. nakit_iade_orani).
                        alanlar["indirim_orani_percent"] = round(yuzde * 100, 4)
                        izler["indirim_orani_percent"] = (span_ham, 0.75)
                    continue  # kar_payi'na girme
                # Buraya gelen yuzde bilinen bir alana ait DEGIL. Simdi
                # elenebilir: ucret/masraf baglami ya da oran tablosu
                # hucresi ise kar payi olarak da atanmamali.
                if _ucret_baglaminda_mi(ham_metin, gm.start(), gm.end()):
                    continue
                if _oran_tablosu_baglaminda_mi(ham_metin, gm.start(), gm.end()):
                    continue
                if _kar_payi_ata(alanlar, izler, span_ham, 0.6):
                    break

    # --- Finansman tutari ----------------------------------------------
    # ARALIK DESENINE DE BAGLAM GUARD'I UYGULANIR (kural degisti,
    # 25 Agustos 2026 - eski kural ve neden dustugu asagida).
    #
    # ESKI KURAL: guard yalnizca ust-limit desenine uygulaniyordu.
    # Gerekcesi olculmus bir gozlemdi: "X TL - Y TL arasi" kalibi o
    # gunku altin veri setinde yalnizca finansman araliklarinda geciyor,
    # 9 yanlis pozitifin hicbiri bu desenden gelmiyordu.
    #
    # NEDEN ARTIK GECERLI DEGIL: altin veri seti buyuyunce gozlem
    # TERSINE dondu. Bugun 18 yanlis pozitifin 9'u TAM DA bu desenden
    # geliyor ve hepsi harcama BASAMAGI, finansman tutari degil:
    #   "5.000 TL - 9.999 TL arasindaki alisverisiniz ile 500 TL" (ZK-020)
    #   "250.000 TL - 1.000.000 TL arasi 2-7 taksitli islemlerde" (ZK-028)
    #   "300 TL - 500.000 TL arasindaki akaryakit harcamalari"    (KT-032)
    #
    # Eski kuralin korkusu ("guard, AL-005/AL-006 gibi GERCEK finansman
    # araliklarini 'harcama' kelimesi yuzunden eler") HAKLIYDI - ama
    # cozum guard'i kapatmak degil, listeden "harcama"yi cikarmakti
    # (bkz. _TUTAR_BAGLAM_DISLAMA_KELIMELERI). Olculdu: AL-005, AL-006
    # ve TOM-002 guard ACIKKEN de dogru bulunuyor.
    #
    # Ust-limit yolundaki gibi ILK GECERLI eslesme alinir, ilk eslesme
    # degil - ayni sayfada once bir harcama basamagi, sonra gercek
    # finansman araligi gecebiliyor.
    for m in RE_TUTAR_ARALIK.finditer(katlanmis):
        if _tutar_baglaminda_gecersiz_mi(ham_metin, m.start(), m.end()):
            continue
        alanlar["finansman_tutari"] = tutara_cevir(_ham_span(ham_metin, m, 2))
        izler["finansman_tutari"] = (_ham_span(ham_metin, m), 0.85)
        break
    if alanlar["finansman_tutari"] is None:
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

        # "X TL'ye kadar" bulunamadiysa "ust limit(i) X TL" denenir - bkz.
        # RE_TUTAR_UST_LIMIT_BEYANI tanimindaki gerekce (guard BILEREK
        # uygulanmaz, ozgulluk desenden gelir).
        if alanlar["finansman_tutari"] is None:
            tm = RE_TUTAR_UST_LIMIT_BEYANI.search(katlanmis)
            if tm:
                tutar = tutara_cevir(_ham_span(ham_metin, tm))
                if tutar is not None:
                    alanlar["finansman_tutari"] = tutar
                    izler["finansman_tutari"] = (_ham_span(ham_metin, tm), 0.75)

    # --- Vade / taksit sayisi / erteleme suresi (UC AYRI kavram) -------
    for vm in RE_VADE.finditer(katlanmis):
        if _vade_ornek_odeme_planindan_mi(katlanmis, vm.start(), vm.end()):
            continue
        if _vade_araligin_ust_siniri_mi(katlanmis, vm.start(), vm.end()):
            continue
        span = _ham_span(ham_metin, vm)
        alanlar["vade_ay"] = aya_cevir(span)
        izler["vade_ay"] = (span, 0.85)
        break

    span = _ilk_eslesme(RE_ERTELEME, katlanmis, ham_metin)
    if span:
        alanlar["erteleme_suresi_ay"] = aya_cevir(span)
        izler["erteleme_suresi_ay"] = (span, 0.85)

    # ARALIK ELENIR, FARKLI DEGERLER TOPLANIR (olculdu 24 Agustos 2026):
    # kaydi_cikar TUM gecerli (aralik-disi) taksit adaylarini toplar.
    # Tek bir FARKLI deger varsa (ayni sayi birden fazla yerde
    # gecebilir - "12 taksit ... 12 aya varan taksit") o deger atanir.
    # BIRDEN FAZLA FARKLI deger varsa alan BOS birakilir - bu, sabit bir
    # tutari degil COK KADEMELI bir teklifi isaret eder ("1.000 TL ve
    # uzerinde 3 taksit, 6.000 TL ve uzerinde 6 taksit" gibi) ve gold bu
    # durumlarda tutarli sekilde "belirtilmemis" diyor: kampanyanin TEK
    # bir taksit sayisi yok, harcama tutarina gore degisen bir tablo var.
    # Uydurma bir sayi (ilk gorulen) SECMEK yerine BOS birakmak, rapor
    # Bolum 5.7/15'teki "supheli deger yerine bos birak" ilkesiyle
    # tutarlidir.
    _taksit_adaylari: dict[int, str] = {}
    for tm in RE_TAKSIT_SAYISI.finditer(katlanmis):
        if _taksit_araliginin_ikinci_sayisi_mi(katlanmis, tm.start()):
            continue
        tm_span = _ham_span(ham_metin, tm)
        sayi_m = re.search(r"\d+", tm_span)
        if sayi_m is None:
            continue
        _taksit_adaylari.setdefault(int(sayi_m.group(0)), tm_span)
    if len(_taksit_adaylari) == 1:
        (_taksit_deger, _taksit_span), = _taksit_adaylari.items()
        alanlar["taksit_sayisi"] = _taksit_deger
        izler["taksit_sayisi"] = (_taksit_span, 0.85)

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
            # DENENDI VE REDDEDILDI (25 Agustos 2026, olculdu iki yonde de):
            # RE_ODUL BIRDEN FAZLA farkli tutarla eslestiginde (1) "belirsizse
            # bos birak" (taksit_sayisi'ndaki kural) VE (2) "en buyugu sec"
            # (RE_ODUL_TAVAN fallback'indeki kural, asagida) ikisi de burada
            # DENENDI. Ilki odul_miktari F1'ini %83,06 -> %77,78'e, dolu alan
            # dogrulugunu %75,8 -> %73,5'e dusurdu (17 kayitta coklu aday var
            # ve BOS birakmak bunlarin cogunda dogru sonucu KACIRDI - ör.
            # AL-004, KT-007, ZK-016). Ikincisi (en buyugu sec) beklenenin
            # aksine DAHA DA KOTU cikti (F1 %82,42, TP 76 -> 75) - RE_ODUL'un
            # dogrudan (sayi-once) deseninde EN BUYUK deger, TAVAN
            # deseninin ("en fazla/maksimum") aksine, GUVENILIR bir "nihai
            # toplam" isareti degil: cogu zaman sayfadaki ILK gecen tutar
            # zaten dogru cevap, sonraki adaylar ya alakasiz ya da daha
            # kucuk bir alt-kalemdir. Sonuc: TOM-008/TOM-010'daki (kulup
            # uyesi/uye olmayan kademesi) yanlis pozitif BILEREK
            # DUZELTILMEDI - .search() (ILK eslesme) davranisi geri
            # birakildi, cunku olculen NET etki her iki alternatifte de
            # olumsuzdu. NER/LLM katmaninin isi (bkz. dosya basi Faz notu).
            m = RE_ODUL.search(katlanmis)
            if m:
                alanlar["odul_miktari"] = tutara_cevir(_ham_span(ham_metin, m))
                alanlar["odul_birimi"] = _odul_birimini_tespit_et(
                    ham_metin, m.start(), m.end()
                )
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
                        adaylar.append((
                            tutar,
                            _odul_birimini_tespit_et(ham_metin, m.start(), m.end()),
                            _ham_span(ham_metin, m),
                        ))
                for tm in RE_ODUL_TAVAN.finditer(katlanmis):
                    if not _odul_baglaminda_mi(ham_metin, tm.start(), tm.end()):
                        continue
                    # INDIRIM TAVANI ODUL DEGIL (olculdu 25 Agustos 2026,
                    # AL-013): "maksimum indirim tutari 1.000 TL" - bu bir
                    # YUZDELIK INDIRIMIN parasal tavanidir, sabit bir odul
                    # DEGILDIR (indirim harcama tutarina gore degisir, tavan
                    # yalnizca ust siniri belirtir). RE_ODUL'un KENDI
                    # deseninde "indirim" zaten anahtar kelime olarak var
                    # (bkz. yukaridaki gerekce - ZK-014/VK-010 "X TL Varan
                    # Indirim" gercekten odul sayilmali) - bu ayrim SADECE bu
                    # TAVAN dalinda gecerlidir, cunku "maksimum/en fazla
                    # indirim" kalibi ile "X TL indirim" kalibi FARKLI
                    # ifadelerdir: biri tavan/esik, digeri dogrudan iddia.
                    if "indirim" in turkce_ascii_kucult(_ham_span(ham_metin, tm)):
                        continue
                    tutar = tutara_cevir(_ham_span(ham_metin, tm, 1))
                    if tutar is not None:
                        birim_ham = turkce_ascii_kucult(_ham_span(ham_metin, tm, 2))
                        # Desen birimi ACIKCA yakaladiysa (gram) o kazanir;
                        # aksi halde birim cumleden cozulur (bkz.
                        # _odul_birimini_tespit_et - "altin puan" vb.).
                        birim = (
                            "Gram"
                            if birim_ham.startswith("gr")
                            else _odul_birimini_tespit_et(ham_metin, tm.start(), tm.end())
                        )
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
    #
    # ILK GECERLI eslesme aranir, ILK eslesme degil (olculdu, DK-001/002/
    # 003/004): Dunya Katilim'in her sayfasinin footer'inda "Son Guncelleme
    # Tarihi: dd/mm/yyyy" damgasi var. Eskiden _ilk_eslesme sayfadaki ILK
    # tarihi alip 4 farkli kampanyaya AYNI (yanlis) bitis tarihini
    # yaziyordu. Simdi her aday _tarih_baglaminda_gecersiz_mi ile elenir;
    # gecerli aday bulunamazsa alan BOS kalir (rapor Bolum 5.7/15: supheli
    # deger uydurmaktan iyidir).
    aralik_gecerli = None
    for am in RE_TARIH_ARALIGI.finditer(katlanmis):
        if _tarih_baglaminda_gecersiz_mi(ham_metin, am.start(), am.end()):
            continue
        aralik_gecerli = am
        break

    if aralik_gecerli is not None:
        alanlar["kampanya_baslangic"] = tarihe_cevir(_ham_span(ham_metin, aralik_gecerli, 1))
        alanlar["kampanya_bitis"] = tarihe_cevir(_ham_span(ham_metin, aralik_gecerli, 2))
        izler["kampanya_bitis"] = (_ham_span(ham_metin, aralik_gecerli), 0.9)
    else:
        # SIKISIK ARALIK - tam aralik bulunamadiysa denenir (bkz.
        # _ARALIK_YIL_PAYLASIMLI / _ARALIK_AY_PAYLASIMLI tanimlari).
        # Eksik parcalar bitis tarihinden odunc alinarak iki tam tarih kurulur.
        sikisik = None
        for m in _ARALIK_YIL_PAYLASIMLI.finditer(katlanmis):
            if _tarih_baglaminda_gecersiz_mi(ham_metin, m.start(), m.end()):
                continue
            yil = _ham_span(ham_metin, m, 5)
            sikisik = (
                f"{_ham_span(ham_metin, m, 1)} {_ham_span(ham_metin, m, 2)} {yil}",
                f"{_ham_span(ham_metin, m, 3)} {_ham_span(ham_metin, m, 4)} {yil}",
                m,
            )
            break
        if sikisik is None:
            for m in _ARALIK_AY_PAYLASIMLI.finditer(katlanmis):
                if _tarih_baglaminda_gecersiz_mi(ham_metin, m.start(), m.end()):
                    continue
                ay, yil = _ham_span(ham_metin, m, 3), _ham_span(ham_metin, m, 4)
                sikisik = (
                    f"{_ham_span(ham_metin, m, 1)} {ay} {yil}",
                    f"{_ham_span(ham_metin, m, 2)} {ay} {yil}",
                    m,
                )
                break

        if sikisik is not None:
            bas, bit, m = sikisik
            # Ikisi de cevrilebiliyorsa yazilir - biri cevrilemezse ortada
            # kalan yarim bir aralik uydurmaktansa tek tarih yoluna dusulur.
            bas_iso, bit_iso = tarihe_cevir(bas), tarihe_cevir(bit)
            if _gecerli_tarih_mi(bas_iso) and _gecerli_tarih_mi(bit_iso):
                alanlar["kampanya_baslangic"] = bas_iso
                alanlar["kampanya_bitis"] = bit_iso
                izler["kampanya_bitis"] = (_ham_span(ham_metin, m), 0.85)

        if alanlar["kampanya_bitis"] is None:
            for tm in RE_TARIH.finditer(katlanmis):
                if _tarih_baglaminda_gecersiz_mi(ham_metin, tm.start(), tm.end()):
                    continue
                span = _ham_span(ham_metin, tm)
                alanlar["kampanya_bitis"] = tarihe_cevir(span)
                izler["kampanya_bitis"] = (span, 0.85)
                break

    # SIRALAMA TUTARLILIGI (27 Agustos 2026, olculdu: VK-577 "14.11.2026 –
    # 15.03.2026 tarihleri arasinda" - kaynak sayfanin KENDI yazdigi aralik
    # ters. Cikarim BURADA "duzeltilmez" - hangi tarafin yanlis oldugu
    # (baslangic yili mi, bitis yili mi) kaynaktan belli degil, birini
    # secmek UYDURMAK olurdu. Bunun yerine `_gecerli_tarih_mi`'nin tek
    # tarih icin yaptigini (takvimde YOK olan degeri reddetme) ikili icin
    # yapariz: baslangic > bitis ise ikisi de BOS BIRAKILIR - iki celiskili
    # tarihten biri dogru gibi davranmak, hicbirini bilmemekten daha
    # yaniltici olurdu (rapor Bolum 5.7/15: supheli deger uydurmaktan
    # iyidir - ayni ilke, ceviklik BOS BIRAKMA CIFTE alan icin).
    if (
        alanlar["kampanya_baslangic"]
        and alanlar["kampanya_bitis"]
        and alanlar["kampanya_baslangic"] > alanlar["kampanya_bitis"]
    ):
        alanlar["kampanya_baslangic"] = None
        alanlar["kampanya_bitis"] = None
        izler.pop("kampanya_bitis", None)

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

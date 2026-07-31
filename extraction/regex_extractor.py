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

# Kar payi orani kalibi "kar pay" baglamini ZORUNLU kilar. Neden? "tahsis
# ucreti finansman tutarinin %0,5'idir" gibi ifadeler kar payi orani
# SANILABILIYOR (yanlis pozitif). Tam sayi yuzdeler de desteklenir (%0, %5
# gibi; "kar paysiz" kampanyalarda oran gercekten 0 olabiliyor).
RE_KAR_PAYI_SAYI_ONCE = re.compile(
    r"%\s*\d{1,2}(?:[.,]\d{1,4})?(?=[^%\n]{0,25}k[aâ]r\s*pay)", re.IGNORECASE
)
RE_KAR_PAYI_BAGLAM_ONCE = re.compile(
    r"k[aâ]r\s*pay\w*[^%\n]{0,25}%\s*\d{1,2}(?:[.,]\d{1,4})?", re.IGNORECASE
)
RE_KAR_PAYSIZ = re.compile(r"k[aâ]r\s*pays[ıi]z", re.IGNORECASE)
# "0 kar payli" gibi yuzde isareti OLMADAN sifir oran ifadeleri de var.
RE_KAR_PAYI_SIFIR = re.compile(r"\b0\s*k[aâ]r\s*pay\w*", re.IGNORECASE)
# Dusuk guvenli fallback: kisa kampanya basliklarinda "kar payi" kelimesi
# hic gecmeden sadece "%X oranla" denebiliyor. Bu durumda, yakininda ucret/
# masraf baglami YOKSA genel yuzdeyi kar payi say (dusuk guven).
RE_KAR_PAYI_GENEL = re.compile(r"%\s*\d{1,2}(?:[.,]\d{1,4})?", re.IGNORECASE)
_UCRET_BAGLAM_DISLAMA_KELIMELERI = [
    "ücret", "masraf", "komisyon", "vergi", "bsmv", "kkdf",
    "peşinat", "ekspertiz", "tahsis", "indirim", "stopaj",
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

RE_MASRAFSIZ = re.compile(
    r"(dosya masraf[ıi]|tahsis ücreti|ekspertiz ücreti)[^.]{0,40}?"
    r"(alınmamaktadır|alınmıyor|karşılanmaktadır|karşılanıyor|ücretsiz|yok)",
    re.IGNORECASE,
)

# Odul ifadeleri cok cesitli: "5.000 TL degerinde alisveris ceki",
# "10.000 Mil'e varan hediye" (TL disi birim!), "250 TL ParafPara",
# "2.000 TL'ye varan Bankkart Lira" (banka-ozel sadakat birimleri).
RE_ODUL = re.compile(
    r"\d{1,3}(?:\.\d{3})*(?:,\d+)?\s*(?:TL|₺)"
    r"(?:['’](?:ye|ya|e|a))?\s*"
    r"(?:değerinde\s*)?(?:varan\s*)?"
    r"(?:alışveriş çeki|alışveriş kartı|hediye çeki|alışveriş puanı|hediye|kazan\w*"
    r"|indirim|bankkart lira|parafpara|nakit iade\w*)",
    re.IGNORECASE,
)
RE_ODUL_MIL = re.compile(r"\d{1,3}(?:\.\d{3})*(?:,\d+)?\s*Mil'?[ea]?\s*varan\s*hediye", re.IGNORECASE)
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
                alanlar["odul_birimi"] = "TL"
                izler["odul_miktari"] = (m.group(0), 0.8)

    # --- Masraf bilgisi ---------------------------------------------------
    span = _ilk_eslesme(RE_MASRAFSIZ, ham_metin)
    if span:
        alanlar["masraf_durumu"] = span
        izler["masraf_durumu"] = (span, 0.75)

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

    alanlar["_izler"] = izler
    return alanlar


def genel_guven_hesapla(izler: dict[str, tuple[str, float]]) -> float:
    """Bulunan alanlarin guven skorlarinin ortalamasi. Hic alan
    bulunamadiysa 0.0 (rapor Bolum 5.7/15: belirsizlik gizlenmez)."""
    if not izler:
        return 0.0
    return round(sum(guven for _, guven in izler.values()) / len(izler), 4)

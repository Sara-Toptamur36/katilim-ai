"""Semantik parcalama: ham kampanya metnini aranabilir parcalara boler.

chunking/spike_qdrant.py'deki NAIF satir bolmenin yerini alir. Spike
raporunun (docs/qdrant_spike_raporu.md) Bulgu 3'unu cozer: naif bolme
yinelenen ve degersiz parcalar uretiyordu - alakasiz bir sorgunun ilk uc
sonucu AYNI yasal uyari metniydi.

TASARIM KARARLARI (hepsi gercek veri incelenerek alindi, 234 kayit):

1. GURULTU FILTRESI: Banka sayfalarinda gezinme menusu ("Ana Sayfa",
   "Kampanyalar"), sosyal medya butonlari ("Facebook'da paylas"), form
   alanlari ("T.C. Kimlik Numarasi") ve tarayici artiklari ("Your browser
   does not support the audio element." - belgelerin %41'inde!) var.
   Bunlar hicbir kampanya bilgisi tasimaz ama parca sayisini sisirir.

2. BASLIK HER PARCAYA EKLENIR: Bir parca ("Kampanya 100.000 TL'ye kadar
   olan basvurularda...") tek basina HANGI kampanyaya ait oldugunu
   soylemez. Baslik onek olarak eklenince hem dense hem sparse arama
   parcayi dogru kampanyaya baglayabilir. Retrieval kalitesine en cok
   katki yapan tek karar budur.

3. TEKILLESTIRME: Ayni metin farkli kampanyalarda tekrar edebiliyor
   (ortak yasal uyarilar). Ayni icerik ikinci kez indekslenmez; ilk
   goruldugu kaydin provenance'i korunur. Boylece sonuc listesi ayni
   metni uc kez gostermez.

4. YUKSEK FREKANSLI SATIRLAR SILINMEZ: Bir satir belgelerin %20'sinde
   geciyor diye ATILMAZ - "Ucretsiz ve ticari kredi kartlarimiz kampanyaya
   dahil degildir" gercek bir kampanya kosuludur ve kullanici bunu
   sorabilir. Ayirt edicilik sorunu, silmekle degil IDF ile cozulur
   (bkz. chunking/seyrek_vektor.py - Qdrant sunucu tarafinda IDF uygular).
"""

from __future__ import annotations

import hashlib
import re

# Hedef parca boyutu: cok kucuk parca baglamsiz kalir, cok buyuk parca
# tek bir sorguya birden fazla konu karistirir. ~700 karakter, gercek
# kampanya kosullarinin ortalama uzunluguna gore secildi.
HEDEF_PARCA_BOYUTU = 700
ASGARI_PARCA_BOYUTU = 60

# Tam eslesen gurultu satirlari (kucuk harfe cevrilip karsilastirilir)
_GURULTU_TAM = {
    "ana sayfa", "kampanyalar", "kendim için", "kendim icin", "hemen başvur",
    "hemen basvur", "kampanyayı paylaş", "kampanyayi paylas", "detaylı bilgi",
    "detayli bilgi", "daha fazla", "tümünü gör", "tumunu gor", "geri dön",
    "geri don", "t.c. kimlik numarası", "t.c. kimlik numarasi", "telefon",
    "doğum tarihi", "dogum tarihi", "ad soyad", "e-posta", "eposta",
    "aydınlatma metni", "aydinlatma metni", "kişisel verilerle ilgili",
    "kisisel verilerle ilgili", "başvuru formu", "basvuru formu",
}

# Icinde gecerse satirin tamamen gurultu oldugunu gosteren kaliplar
_GURULTU_KALIPLARI = [
    re.compile(r"your browser does not support", re.IGNORECASE),
    # Turkce unlu uyumu: "Facebook'DA" ama "LinkedIn'DE" - iki bicim de
    # gecerli (testle yakalandi, ilk yazimda yalnizca 'da/ta' vardi).
    re.compile(r"\b(facebook|twitter|linkedin|whatsapp|instagram|x)'?[dt][ae] payla", re.IGNORECASE),
    re.compile(r"çerez(ler)?i? (kabul|politika)", re.IGNORECASE),
    re.compile(r"cookie", re.IGNORECASE),
    re.compile(r"^\s*(menü|menu|arama|ara|kapat|aç)\s*$", re.IGNORECASE),
]


# --------------------------------------------------------------------------
# NAVIGASYON / SITE KALIBI ELEME
# --------------------------------------------------------------------------
# SORUN (Havin'in 24.08.2026 arayuz raporu, Md. 2): "Kuveyt Turk'un konut
# finansmani orani ne" sorusuna donen cevap site menusuydu - "Finans Portali
# Ozel Bankacilik ... Sube ve ATM'ler Dijital Bankacilik ...". Cekimserlik
# kurali bunu yakalayamiyordu, cunku menu sitedeki HER urunu listeliyor:
# "Konut Finansmani" da menude geciyor, "Kuveyt Turk" de. Terim ortusmesi
# 0,667 cikip 0,60 esigini geciyordu.
#
# Esigi yukseltmek COZUM DEGIL: olculen kalibrasyonda cevaplanabilir
# sorularin en dususu 0,667: esik yukseltilirse gercek sorular da
# cevapsiz kalir. Sorun esikte degil, menunun indekste OLMASINDA.
#
# ELEME OLCUTU - IKI SINYALIN KESISIMI (ikisi de tek basina olculdu ve
# tek basina YETERSIZ cikti):
#   1. ETIKET SEKLI: kisa, cumle sonu noktalamasi olmayan, rakamsiz satir.
#      TEK BASINA: korpusun %31,5'ini siliyordu ve icinde gercek kampanya
#      adimlari vardi ("Albaraka Mobil uzerinden / 'Hemen Katil' butonuna
#      tiklayin") - scraper duzyaziyi da kisa satirlara boluyor.
#   2. SAYFALAR ARASI TEKRAR: ayni satir o bankanin bircok sayfasinda.
#      TEK BASINA: mesru kampanya kosullarini siliyordu ("Islemlerin
#      taksitli olabilmesi icin odeme aninda taksitli secimin yapilmasi
#      gerekmektedir" - 121 sayfanin 44'unde geciyor ama GERCEK kosul).
#
# Kesisim olculdu: 24.009 satirin 4.663'u (%19,4) elendi; silinenler menu,
# cerez bandi ve footer bag listeleri, korunanlar kampanya adimlari. Site
# kalibinin tanimi zaten budur - hem etiket seklinde hem cok sayfada tekrar
# eden metin.
#
# TEKRAR OLCUSU ORAN DEGIL, MUTLAK SAYFA SAYISIDIR. Once "bankanin
# sayfalarinin %30'unda geciyorsa kalip" denmisti; olculdu ve YANLIS cikti:
# Emlak Katilim'in 112 sayfasindan yalnizca 4'u o navigasyon sablonunu
# tasiyor (siteler birden fazla sayfa sablonu kullaniyor), yani menu 33
# sayfalik esigin cok altinda kalip hic elenmiyordu. Site kalibi BIREBIR
# tekrar eder; kac sayfanin YUZDESI oldugu degil, kac AYRI sayfada
# gorundugu anlamlidir.
#
# Taban 4 olculerek secildi:
#   3 -> mesru icerigi de siliyor ("Kampanyaya Katilim Adimlari | Albaraka
#        Mobil uzerinden | 'Hemen Katil' butonuna tiklayin")
#   4 -> menuler siliniyor, kampanya adimlari korunuyor
#   6 -> 4 ile BIREBIR AYNI sonuc
# 4 ile 6 arasinda hicbir fark olmamasi, esigin bicak sirti bir ayar degil
# genis bir plato uzerinde oturdugunu gosteriyor.
KALIP_ASGARI_SAYFA = 4        # satir bu kadar AYRI sayfada geciyorsa site kalibi
MENU_BLOK_ASGARI = 5          # bu kadar art arda etiket satiri bir blok sayilir
MENU_BLOK_KALIP_ORANI = 0.8   # blogun bu orani kalipsa blok elenir
ETIKET_AZAMI_UZUNLUK = 40

_CUMLE_SONU = re.compile(r"[.!?:;]\s*$")
_RAKAM = re.compile(r"\d")


def _etiket_gibi_mi(satir: str) -> bool:
    """Satir bir baglanti etiketi gorunumunde mi (cumle degil)?

    Rakam iceren satirlar disarida: menu etiketleri sayi tasimazken
    kampanya kosullari genellikle tasir ("6 taksit", "500 TL").
    """
    return (
        len(satir) <= ETIKET_AZAMI_UZUNLUK
        and not _CUMLE_SONU.search(satir)
        and not _RAKAM.search(satir)
    )


def kalip_satirlari_bul(kayitlar: list[dict]) -> dict[str, set[str]]:
    """banka -> o bankanin sayfalarinda TEKRAR EDEN satirlar.

    Tekrar SAYFA sayisiyla olculur, gecis sayisiyla degil: ayni satirin tek
    bir sayfada bes kez gecmesi onu site kalibi yapmaz.
    """
    satir_sayfalari: dict[str, dict[str, set[str]]] = {}

    for kayit in kayitlar:
        metin = kayit.get("ham_metin") or kayit.get("normalize_metin") or ""
        if not metin:
            continue
        banka = kayit.get("banka") or ""
        kimlik = kayit.get("url") or kayit.get("kaynak_url") or ""
        banka_satirlari = satir_sayfalari.setdefault(banka, {})
        for ham in metin.split("\n"):
            sade = " ".join(ham.split())
            if sade:
                banka_satirlari.setdefault(sade, set()).add(kimlik)

    return {
        banka: {
            satir
            for satir, sayfalar in satirlar.items()
            if len(sayfalar) >= KALIP_ASGARI_SAYFA
        }
        for banka, satirlar in satir_sayfalari.items()
    }


def _menu_bloklarini_ele(satirlar: list[str], kalip_satirlar: set[str]) -> list[str]:
    """Art arda gelen ve cogu KALIP olan etiket satirlarini atar.

    Tek tek bakildiginda menu etiketi ile kampanya basligi ayirt edilemez;
    ayirt edici olan ARKA ARKAYA gelmeleridir. Bu yuzden eleme satir
    basinda degil BLOK basinda yapilir.
    """
    if not kalip_satirlar:
        return satirlar

    sonuc: list[str] = []
    i = 0
    while i < len(satirlar):
        if not _etiket_gibi_mi(satirlar[i]):
            sonuc.append(satirlar[i])
            i += 1
            continue

        j = i
        while j < len(satirlar) and _etiket_gibi_mi(satirlar[j]):
            j += 1
        blok = satirlar[i:j]

        kalip_orani = sum(s in kalip_satirlar for s in blok) / len(blok)
        if not (len(blok) >= MENU_BLOK_ASGARI and kalip_orani >= MENU_BLOK_KALIP_ORANI):
            sonuc.extend(blok)
        i = j
    return sonuc


def _gurultu_mu(satir: str) -> bool:
    """Satir hicbir kampanya bilgisi tasimiyor mu?"""
    sade = satir.strip()
    if len(sade) < 3:
        return True
    # Turkce 'İ' sorunu: str.lower() bunu 'i'+birlesik nokta yapar, bu da
    # sozlukle karsilastirmayi sessizce bozar (projede daha once uc ayri
    # yerde bulundu - bkz. terminology/genisletme.py, agent/intent.py).
    kucuk = sade.replace("İ", "i").lower()
    if kucuk in _GURULTU_TAM:
        return True
    return any(k.search(sade) for k in _GURULTU_KALIPLARI)


def basligi_bul(metin: str, kaynak_url: str = "") -> str:
    """Belgenin kampanya basligini belirler.

    ONCELIK URL SLUG'INDA - olculerek karar verildi: metin sezgisi
    (ilk 'anlamli uzunluktaki' satir) gercek veride sik yaniliyor;
    ornekleme sonucu yanlis basliklar: "Sektor: Giyim ve Aksesuar"
    (dogrusu "Decathlon'da 4 Taksit"), "Kampanyaya Katilim Adimlari:",
    "Musteri Ol Kampanyalari" (gezinme menusu). URL slug'i ise ayni
    orneklerde tutarli sekilde dogruydu ve zaten kampanyanin kimligidir.

    Metin sezgisi yalnizca slug bilgi vermiyorsa (cok kisa/anlamsiz)
    YEDEK olarak kullanilir.
    """
    from scraper.scripts.postgrese_yukle import _url_slug_to_baslik

    if kaynak_url:
        slug_basligi = _url_slug_to_baslik(kaynak_url)
        # Cok kisa slug'lar ("Lc Waikiki" gibi) tek basina kampanyayi
        # tanimlamaya yetmeyebilir - o durumda metinden destek alinir.
        if len(slug_basligi) >= 20 and slug_basligi != "Baslik Belirlenemedi":
            return slug_basligi

    for satir in metin.split("\n"):
        sade = satir.strip()
        if _gurultu_mu(sade):
            continue
        if 20 <= len(sade) <= 150:
            return sade

    return _url_slug_to_baslik(kaynak_url) if kaynak_url else ""


def _icerik_ozeti(metin: str) -> str:
    """Tekillestirme icin icerik parmak izi (bosluk farklarina duyarsiz)."""
    normalize = " ".join(metin.split()).replace("İ", "i").lower()
    return hashlib.sha256(normalize.encode("utf-8")).hexdigest()


def belgeyi_parcala(
    ham_metin: str,
    baslik: str | None = None,
    hedef_boyut: int = HEDEF_PARCA_BOYUTU,
    kaynak_url: str = "",
    kalip_satirlar: set[str] | None = None,
) -> list[str]:
    """Tek bir belgeyi parcalara boler.

    Her parcanin basina belge basligi eklenir (bkz. modul docstring'i,
    Tasarim Karari 2) - parcanin hangi kampanyaya ait oldugu tek basina
    anlasilabilsin diye.
    """
    if baslik is None:
        baslik = basligi_bul(ham_metin, kaynak_url)

    temiz_satirlar = [
        s.strip() for s in ham_metin.split("\n") if s.strip() and not _gurultu_mu(s)
    ]
    # Navigasyon/site kalibi elemesi - bkz. modulun "NAVIGASYON / SITE
    # KALIBI ELEME" bolumu. `kalip_satirlar` verilmezse davranis DEGISMEZ:
    # tek belgelik cagrilarda (test, tekil kullanim) sayfalar arasi tekrar
    # olcusu zaten yoktur, o yuzden eleme de yapilamaz.
    temiz_satirlar = _menu_bloklarini_ele(temiz_satirlar, kalip_satirlar or set())

    parcalar: list[str] = []
    tampon: list[str] = []
    uzunluk = 0

    for satir in temiz_satirlar:
        # Satir tek basina hedef boyutu asiyorsa kendi parcasi olur
        if uzunluk + len(satir) > hedef_boyut and tampon:
            parcalar.append(" ".join(tampon))
            tampon, uzunluk = [], 0
        tampon.append(satir)
        uzunluk += len(satir) + 1

    if tampon:
        parcalar.append(" ".join(tampon))

    # Basligi onek olarak ekle; baslik zaten parcanin icindeyse tekrarlama
    onekli = []
    for p in parcalar:
        if len(p) < ASGARI_PARCA_BOYUTU:
            continue
        onekli.append(p if baslik and baslik in p else (f"{baslik} — {p}" if baslik else p))
    return onekli


def kayitlari_parcala(kayitlar: list[dict]) -> list[dict]:
    """Birden cok scraper kaydini parcalar ve TEKILLESTIRIR.

    Donen her oge: {"metin": str, "banka": str, "kaynak_url": str,
    "kampanya_adi": str, "erisim_zamani": str}

    Ayni icerik birden fazla kayitta geciyorsa yalnizca ILK gorulen
    indekslenir (Tasarim Karari 3).
    """
    gorulen: set[str] = set()
    sonuc: list[dict] = []

    # Site kalibi TEK BELGEDEN anlasilamaz - "bu satir her sayfada var mi"
    # sorusu ancak tum korpus elde varken cevaplanir. Bu yuzden kalip
    # tespiti burada, parcalama dongusunden ONCE yapilir.
    kaliplar = kalip_satirlari_bul(kayitlar)

    for kayit in kayitlar:
        ham = kayit.get("ham_metin") or ""
        if not ham.strip():
            continue
        kaynak_url = kayit.get("url") or ""
        baslik = basligi_bul(ham, kaynak_url)
        banka_kaliplari = kaliplar.get(kayit.get("banka") or "", set())
        for parca in belgeyi_parcala(
            ham, baslik=baslik, kalip_satirlar=banka_kaliplari
        ):
            ozet = _icerik_ozeti(parca)
            if ozet in gorulen:
                continue
            gorulen.add(ozet)
            sonuc.append(
                {
                    "metin": parca,
                    "banka": kayit.get("banka"),
                    "kaynak_url": kayit.get("url"),
                    "kampanya_adi": baslik,
                    "erisim_zamani": kayit.get("erisim_zamani"),
                }
            )
    return sonuc

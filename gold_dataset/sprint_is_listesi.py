"""Etiketleme sprinti is listesi (gorev 21: 200-300 altin kayit).

--------------------------------------------------------------------------
NE YAPAR
--------------------------------------------------------------------------
Henuz etiketlenmemis kampanyalari bulur, BANKA DENGESINI gozeterek
siralar ve etiketleyiciye somut bir liste verir.

--------------------------------------------------------------------------
CIKARIM MOTORU HALA KULLANILMIYOR - AMA SIRALAMA ARTIK ICERIGE BAKIYOR
--------------------------------------------------------------------------
Degismeyen sert kural: `regex_extractor` - yani OLCULEN motor - bu
dosyada hicbir yerde cagrilmaz. Motorun tahmini bir etiketin degerine
dokunursa olcum dairesel hale gelir ve %100 cikar. Ayni ilkenin etiket
tarafi: gold_dataset/etiketleme_yardimcisi.py "NEDEN CIKARIM MOTORUNUN
CIKTISI KULLANILMIYOR" bolumu.

DEGISEN kisim: onceki surumde siralama yalnizca scraper ustverisine
(banka, url, erisim_zamani) dayaniyordu ve "hicbir icerik sinyali
kullanilmaz" deniyordu. Bu, listenin alfabetik olmasi demekti; Ziraat
havuzunda pes pese 20 tane "X magazasinda N taksit" sayfasi geliyordu.
Set buyudukce ayni kalibin kopyalariyla doluyordu.

Artik siralama HAM METNIN YAPISINA bakiyor: sayfada tarih benzeri bir
dizgi, TL tutari, yuzde, taksit sayisi ya da odul birimi sozcugu gecip
gecmedigi. Bunlar genel kaliplardir; ne motorun ciktisidir ne de bir
DEGER uretirler - yalnizca "bu sayfa hangi alan turlerini barindiriyor"
sorusunu cevaplarlar ve SIRAYI belirlerler. Etiketi insan, kaynaga
bakarak yazar; bu sinyal o karara girmez.

BUNUN BEDELI ACIKCA YAZILIR: bu siralama dagilimi BILEREK icerik
zengini sayfalara kaydirir. Ustunlugu, ayni kalibin yirminci kopyasi
yerine yeni bir taksit degeri ya da yeni bir odul birimi tasiyan
sayfanin one gelmesidir. Sakincasi, "yalin" sayfalarin altin sette
hak ettiginden az temsil edilmesidir. Ikisi de raporda gorunur.

--------------------------------------------------------------------------
AYNI KAMPANYA, IKI ADRES
--------------------------------------------------------------------------
"Zaten etiketli mi" sorusu ilk surumde YALNIZCA URL slug'i esitligiyle
cevaplaniyordu. Yetmedi: Dunya Katilim'in "Altin Kesem" kampanyasi altin
sette `/kampanyalar/altin-kesem` adresiyle duruyor (DK-003), ham korpusta
ise ayni kampanya `/kampanyalar/altin-kesemTicari` adresiyle. Slug'lar
farkli oldugu icin liste bunu YENI is sanip tekrar etiketlemeye
gonderiyordu - o kayit altin sete girseydi ayni kampanya olcumde CIFT
agirlik alacakti.

Bu yuzden slug esitligine ek olarak iki zayif sinyal daha bakilir:
slug'in etiketli bir slug'la ONEK iliskisi, ve turetilmis basligin
etiketli bir kampanya adiyla ayni olmasi. Ikisi de ISARETLER, ELEMEZ -
"bridgestoneda-5-taksit" ile "bridgestoneda-5-taksit-2" pekala iki ayri
kampanya olabilir. Karar, T.O.M. ornegindeki gibi, insanindir.

--------------------------------------------------------------------------
DENGE ILE HACIM CATISIYOR - OLCULMUS GERCEK
--------------------------------------------------------------------------
Ham korpus banka bazinda cok dengesizdir (bkz. ciktidaki tablo): iki
banka toplam kampanyalarin buyuk cogunlugunu olusturur, iki banka ise
3'er kampanyaya sahiptir. Bu yuzden "200-300 kayit" ve "bankalar arasi
denge" AYNI ANDA saglanamaz:

  - Tam denge istenirse tavan, en az kampanyaya sahip bankanin sayisidir
  - Hacim istenirse set kacinilmaz olarak iki bankaya kayar

Bu script ikisinin arasini KOTA ile bulur: her bankadan en fazla `--kota`
kampanya onerilir. Kota disinda kalanlar listeye girmez; boylece hedef
sayiya ulasilirken tek bir bankanin sayfa uslubu olcumu domine etmez.
Kalan dengesizlik ciktida ACIKCA yazilir - gizlenmez.

Kullanim:
    python -m gold_dataset.sprint_is_listesi
    python -m gold_dataset.sprint_is_listesi --hedef 200 --kota 30
"""

from __future__ import annotations

import argparse
import glob
import json
import re
from collections import defaultdict
from pathlib import Path

from extraction.normalizer import turkce_ascii_kucult

KOK = Path(__file__).resolve().parent.parent
GOLD = KOK / "gold_dataset" / "altin_veri_seti.json"
HAM = KOK / "scraper" / "raw_data"
CIKTI = KOK / "gold_dataset" / "sprint_is_listesi.json"

SAHTE_ONEKLER = ("A-", "B-", "C-", "D-")

# KONTROL GEREKTIREN SAYFALAR - kampanya listeleyen kategori sayfalari
# ("diger-kampanyalar.aspx", "kart-kampanyalari.aspx" gibi).
#
# BUNLAR ELENMEZ, ISARETLENIR. Ilk surumde otomatik eleniyorlardi; bu
# YANLISTI ve gerekcesi altin veri setinin kendisinde duruyor: T.O.M.
# Katilim'in UC altin kaydi (TOM-001/002/003) TEK bir sayfadan gelir -
# "kampanyalar.html". Yani bir liste sayfasi pekala etiketlenebilir
# olabilir; banka tum kampanya detaylarini tek sayfaya koymussa oradan
# birden fazla gecerli kayit cikar. (Ilk surumde o sayfa filtreye
# takilmiyordu - yalnizca uzantisi .html oldugu icin, tasarimdan degil
# sanstan. Kalip artik .html'i de kapsiyor: sayfa ISARETLENIR, elenmez.)
#
# Karar insanindir: ekip zaten her kaydi ekran goruntusuyle dogruluyor.
# Bu isaret, o kontrolun yerine gecmez; SIRAYA sokar.
#
# NEDEN URL KALIBI, NEDEN METIN UZUNLUGU DEGIL (olculdu): once "kisa
# sayfa = liste sayfasi" varsayildi, ama 800 karakterlik esik 42 sayfayi
# eliyordu ve bunlarin cogu GERCEK kisa kampanyaydi ("bridgestoneda-5-
# taksit" 514 karakter).
# `default.aspx` de eklendi: Turkiye Finans kampanya kokunu
# `/kampanyalar/Sayfalar/default.aspx` altinda sunuyor ve o sayfa yalnizca
# kategori kutulari icerir ("Finansman Kampanyalari - Detayli Bilgi"),
# tek bir kampanya verisi tasimaz. Adi "default" olan bir sayfa hicbir
# zaman belirli bir kampanya degildir.
KONTROL_GEREK_KALIBI = re.compile(r"(kampanyalar[iı]?|default)(\.aspx|\.html)?$", re.IGNORECASE)

# Basliktan atilacak gezinti satirlari - kampanyayi tanitmazlar.
_GEZINTI_ISARETLERI = ("ana sayfa", "anasayfa", "kampanyalar", "müşteri ol")


def _slug(url: str) -> str:
    return (url or "").rstrip("/").split("/")[-1]


def _sadelestir(metin: str) -> str:
    """Karsilastirma icin sadelestirir: diyakritik katlanir, harf/rakam
    disindaki her sey atilir. Boylece "Altin Kesem!" ile "altin-kesem"
    esit sayilir.

    NOT: `extraction.normalizer` bir NORMALLESTIRICIDIR, cikarim motoru
    degil - modul docstring'indeki yasak regex_extractor icindir. Kurali
    burada kopyalamak, ayni mantigi iki yerde tutmak olurdu.
    """
    from extraction.normalizer import turkce_ascii_kucult

    return re.sub(r"[^a-z0-9]+", "", turkce_ascii_kucult(metin or ""))


# Ayni teklifin AY VARYANTLARI. Olculdu: Albaraka'nin ayni fatura
# kampanyasi altin sette "agustos-ayina-ozel-fatura-kampanyasi" (AL-007),
# ham korpusta ayrica "temmuz-ayina-ozel-fatura-kampanyasi" adresiyle
# duruyor - ayni kod (OFT2026), ayni odul (talimat basina 500 TL,
# toplam 2.000 TL Worldpuan), yalnizca ay farkli.
#
# Ikisini de etiketlemek iki sorun dogurur: (1) o teklif olcumde CIFT
# agirlik alir, (2) metinler neredeyse ayni oldugu icin biri train'e
# digeri test'e duserse sizinti olur - mentor raporunun 5.4 maddesi.
# Karar yine INSANIN: tarihler farkli oldugu icin ekip bunlari ayri
# kayit saymak isteyebilir. Kod yalnizca gorunur kilar.
_AYLAR = ("ocak", "subat", "mart", "nisan", "mayis", "haziran", "temmuz",
          "agustos", "eylul", "ekim", "kasim", "aralik")


def _aysiz(sade: str) -> str:
    for ay in _AYLAR:
        sade = sade.replace(ay, "")
    return sade


def _etiketli_kimlikler() -> tuple[set[str], set[str]]:
    """(etiketli slug'lar, sadelestirilmis etiketli kampanya adlari)."""
    with open(GOLD, encoding="utf-8") as f:
        kayitlar = json.load(f)
    gercek = [k for k in kayitlar if not k["kayit_id"].startswith(SAHTE_ONEKLER)]
    sluglar = {_slug(k["kaynak_url"]) for k in gercek if k.get("kaynak_url")}
    adlar = {_sadelestir(k["kampanya_adi"]) for k in gercek if k.get("kampanya_adi")}
    return sluglar, adlar - {""}


def _etiketli_sluglar() -> set[str]:
    return _etiketli_kimlikler()[0]


def _kopya_suphesi(slug: str, baslik: str, sluglar: set[str], adlar: set[str]) -> str | None:
    """Ayni kampanyanin farkli adresle tekrar listelenmesine karsi zayif
    sinyal. Bulunursa GEREKCE dondurur - etiketleyici kendisi bakabilsin.
    Hicbir kaydi ELEMEZ; bkz. modul docstring'i."""
    # URL PARCASI (#bolum) ONCE BAKILIR: parca, bir sayfanin BOLUMUNU
    # gosterir - taban sayfa etiketliyse o bolum zaten okunmus demektir.
    # Olculdu: T.O.M.'un uc "kampanyalar.html#..." girdisi, altin setteki
    # TOM-001/002/003'un tam karsiligi cikti; liste etiketleyiciyi ayni
    # ise ucuncu kez gonderiyordu. Yine de ELENMEZ: ayni sayfada HENUZ
    # etiketlenmemis baska bolumler de olabilir.
    if "#" in slug and slug.split("#", 1)[0] in sluglar:
        return f"'{slug.split('#', 1)[0]}' sayfasinin bir bolumu; sayfa zaten etiketli"

    sade_slug = _sadelestir(slug)
    # SONDAKI RAKAMLAR ATILIR. Olculdu: altin sette AL-005'in adresi
    # ".../saglik-harcamalarina-vade-farksiz-6-taksit-kampanyasi-1_1",
    # ham korpusta ayni kampanya ".../...-kampanyasi1-2". Sadelestirilmis
    # halleri "...kampanyasi11" ve "...kampanyasi12" - AYNI UZUNLUKTA
    # oldugu icin onek iliskisi kurulamiyor, kayit temiz gorunuyordu.
    # Bankalar slug sonuna surum numarasi ekliyor; sondaki rakamlari
    # atmak bu gurultuyu temizler. Ortadaki rakamlara DOKUNULMAZ -
    # "akaryakit...-300-tl-parafpara" ile "...-400-tl-parafpara" iki
    # AYRI kampanyadir ve ayrik kalmalidir.
    kok_slug = sade_slug.rstrip("0123456789")
    for etiketli in sluglar:
        sade_etiketli = _sadelestir(etiketli)
        if not sade_etiketli or sade_slug == sade_etiketli:
            continue
        # Onek iliskisi: "altin-kesemTicari" -> "altin-kesem"
        if sade_slug.startswith(sade_etiketli) or sade_etiketli.startswith(sade_slug):
            return f"slug '{etiketli}' ile onek iliskisi"
        kok_etiketli = sade_etiketli.rstrip("0123456789")
        if kok_slug and kok_slug == kok_etiketli:
            return f"slug '{etiketli}' ile yalnizca sondaki rakamlarda farkli"
        if _aysiz(kok_slug) and _aysiz(kok_slug) == _aysiz(kok_etiketli):
            return f"slug '{etiketli}' ile yalnizca AY ADINDA farkli"
    if _sadelestir(baslik) in adlar:
        return "baslik, etiketli bir kampanya adiyla ayni"
    return None


def _ham_kampanyalar() -> dict[str, dict]:
    """URL slug -> EN GUNCEL ham kayit.

    Ayni kampanyanin birden fazla tarihli anlik goruntusu olabilir
    (scraper eski taramalari silmez); etiketleme icin en yenisi kullanilir.
    """
    en_guncel: dict[str, dict] = {}
    for yol in glob.glob(str(HAM / "*" / "json" / "*.json")):
        try:
            with open(yol, encoding="utf-8") as f:
                kayit = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        slug = _slug(kayit.get("url"))
        if not slug:
            continue
        mevcut = en_guncel.get(slug)
        if mevcut is None or (kayit.get("erisim_zamani") or "") > (mevcut.get("erisim_zamani") or ""):
            en_guncel[slug] = kayit
    return en_guncel


def _baslik(kayit: dict) -> str:
    """Kampanya basligi ham metnin ilk anlamli satirindan alinir.

    Cikarim motoru CAGRILMAZ (bkz. modul docstring'i) - bu yalnizca
    etiketleyicinin listede kampanyayi tanimasi icin bir etikettir,
    yer gercegi degildir.
    """
    metin = kayit.get("normalize_metin") or kayit.get("ham_metin") or ""
    banka = (kayit.get("banka") or "").lower()

    for satir in metin.split("\n"):
        sade = " ".join(satir.split())
        if len(sade) <= 25:
            continue
        kucuk = sade.lower()
        # Gezinti satiri, banka adinin kendisi ya da kategori basligi
        # kampanyayi TANITMAZ. (Ilk surumde "Türkiye Emlak Katilim
        # Bankasi" satiri baslik olarak seciliyordu.)
        if any(i in kucuk for i in _GEZINTI_ISARETLERI):
            continue
        if banka and kucuk.startswith(banka):
            continue
        # CUMLE ORTASI SATIRLAR BASLIK DEGILDIR. Ziraat sayfalarinda metin
        # magaza adinda bolundugu icin ilk uzun satir cogu zaman
        # "firsatindan yararlanabilirsiniz." gibi bir CUMLE KUYRUGU
        # oluyordu; liste okunamaz hale geliyordu. Baslik buyuk harf ya da
        # rakamla baslar.
        if sade[0].islower():
            continue
        return sade[:80]

    # Hicbir satir uymadiysa slug daha bilgilendiricidir.
    return _slug(kayit.get("url")).replace("-", " ").strip()[:80] or "(baslik yok)"


# METIN BENZERLIGI ESIGI - "ayni kalibin baska magazasi" durumu.
#
# Slug kurallari ayni kampanyanin ayni adresini yakalar; ama bankalar
# ayni kampanya metnini yalnizca magaza adi ve sayi degistirerek
# tekrarliyor: Ziraat'in "abdullah-kigilida-2-taksit" ile
# "desada-2-taksit" sayfalari %98 ayni. Ikisi de etiketlenirse altin
# set ayni cumleyi iki kez tasir; biri train'e digeri test'e duserse
# de sizinti olur (mentor raporu 5.4).
#
# ESIK NEREDEN GELIYOR (olculdu, 63 aday x 57 etiketli sayfa):
#   ortanca benzerlik %42, ortalama %45
#   >=%95: 2 aday   >=%90: 4   >=%85: 7   >=%80: 11   >=%70: 22
# %85 ustu acik bir aykiri bolge. Temiz bir bosluk YOK, dolayisiyla bu
# bir YARGI - bu yuzden eleme degil ISARET.
#
# ISARETLENEN KAYIT NE YAPILACAK: ikizinin altin kaydiyla karsilastir.
# CIKARILAN DEGERLER ayniysa (ayni taksit sayisi, ayni odul) kayit
# olcume hicbir sey katmaz, atlanir. Degerler farkliysa etiketlenebilir.
COK_BENZER_ESIGI = 0.85


def _cok_benzer_ikiz(metin: str, banka: str, etiketli_metinler: dict) -> tuple[str, float] | None:
    """Ayni bankanin etiketli sayfalari icinde en benzerini bulur.

    YALNIZCA AYNI BANKA: kalip metni bankaya ozeldir ve olcumde en
    benzer eslesmelerin TAMAMI ayni bankadan cikti. Bankaya kisitlamak
    hem daha dogru hem de karsilastirma sayisini buyuk olcude azaltir.
    """
    import difflib

    if len(metin) < 200:
        return None
    en_iyi: tuple[str, float] | None = None
    for kayit_id, (kayit_banka, kayit_metni) in etiketli_metinler.items():
        if kayit_banka != banka:
            continue
        olcer = difflib.SequenceMatcher(None, metin, kayit_metni)
        # Ucuz on elemeler: gercek oran bunlarin ustune cikamaz.
        if olcer.real_quick_ratio() < COK_BENZER_ESIGI:
            continue
        if olcer.quick_ratio() < COK_BENZER_ESIGI:
            continue
        oran = olcer.ratio()
        if oran >= COK_BENZER_ESIGI and (en_iyi is None or oran > en_iyi[1]):
            en_iyi = (kayit_id, oran)
    return en_iyi


def _etiketli_metinler(ham: dict) -> dict[str, tuple[str, str]]:
    """kayit_id -> (banka, katlanmis metin). Kaynak sayfasi ham veride
    kalmamis kayitlar disarida kalir - kampanya rotasyonu."""
    from extraction.normalizer import turkce_ascii_kucult

    with open(GOLD, encoding="utf-8") as f:
        kayitlar = json.load(f)
    sonuc = {}
    for k in kayitlar:
        if k["kayit_id"].startswith(SAHTE_ONEKLER):
            continue
        slug = _slug(k.get("kaynak_url") or "")
        kaynak = ham.get(slug)
        if not kaynak:
            continue
        sonuc[k["kayit_id"]] = (
            k.get("banka") or "",
            turkce_ascii_kucult(kaynak.get("normalize_metin") or ""),
        )
    return sonuc


# ---------------------------------------------------------------------------
# YAPISAL PROFIL - "bu sayfa hangi alan turlerini barindiriyor"
# ---------------------------------------------------------------------------
# Bunlar OLCUM yapmaz, DEGER uretmez: yalnizca sayfada o turden bir sey
# gecip gecmedigini soyler. regex_extractor'in kaliplariyla ilgisi yoktur
# ve onun ciktisi hicbir sekilde okunmaz (bkz. modul docstring'i).
_TARIH_IZI = re.compile(
    r"\d{1,2}[./]\d{1,2}[./]\d{4}"
    r"|\d{1,2}\s+(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos"
    r"|Eylül|Ekim|Kasım|Aralık)"
)
_TUTAR_IZI = re.compile(r"\d{1,3}(?:\.\d{3})+\s*TL")
_YUZDE_IZI = re.compile(r"%\s?\d")
_TAKSIT_IZI = re.compile(r"(\d{1,2})\s*taksit", re.IGNORECASE)

# Odul birimi sozcukleri - katlanmis metinde aranir.
_ODUL_IZLERI = {
    "parafpara": re.compile(r"parafpara"),
    "bankkart lira": re.compile(r"bankkart lira"),
    "worldpuan": re.compile(r"worldpuan"),
    "mil": re.compile(r"\bmil\b"),
    "gram": re.compile(r"\bgram\b"),
    "nakit iade": re.compile(r"nakit iade"),
}


def _uzunluk_bandi(n: int) -> str:
    if n < 800:
        return "kisa"
    return "orta" if n < 2000 else "uzun"


def _yapisal_belirtecler(metin: str) -> set[str]:
    """Sayfayi CESITLILIK acisindan tanimlayan belirtec kumesi.

    Secim bu kumeler uzerinden yapilir: hicbir yeni belirtec getirmeyen
    bir sayfa, altin sete zaten temsil edilen bir kalibi bir kez daha
    eklemekten baska is yapmaz.
    """
    katlanmis = turkce_ascii_kucult(metin)
    belirtecler: set[str] = {f"uzunluk={_uzunluk_bandi(len(metin))}"}

    var_tarih = bool(_TARIH_IZI.search(metin))
    var_tutar = bool(_TUTAR_IZI.search(metin))
    var_yuzde = bool(_YUZDE_IZI.search(metin))
    if var_tarih:
        belirtecler.add("tarih")
    if var_tutar:
        belirtecler.add("tutar")
    if var_yuzde:
        belirtecler.add("yuzde")

    for ham_sayi in set(_TAKSIT_IZI.findall(metin)):
        sayi = int(ham_sayi)
        # 24'ten buyuk "taksit" sayisi neredeyse her zaman baska bir
        # sayinin yanlis eslesmesidir (ornegin bir madde numarasi).
        if 1 < sayi <= 24:
            belirtecler.add(f"taksit={sayi}")

    for ad, kalip in _ODUL_IZLERI.items():
        if kalip.search(katlanmis):
            belirtecler.add(f"odul={ad}")

    # KOSUL YAPISI: hangi alan turlerinin BIRLIKTE bulundugu, tek tek
    # bulunmalarindan farkli bir sayfa turudur ("tarihli + tutarli
    # kademeli odul" ile "tarihsiz duz taksit" ayni sey degildir).
    yapi = "+".join(
        ad for ad, var in (("tarih", var_tarih), ("tutar", var_tutar),
                           ("yuzde", var_yuzde),
                           ("taksit", bool(_TAKSIT_IZI.search(metin))))
        if var
    )
    belirtecler.add(f"yapi={yapi or 'yalin'}")
    return belirtecler


# ---------------------------------------------------------------------------
# KUMELEME - ayni kalibin kopyalari tek bir kumede toplanir
# ---------------------------------------------------------------------------
# Onceki surumde benzerlik yalnizca ISARETLENIYORDU; liste hala her
# kopyayi ayri is olarak gosteriyordu. Artik secim SAYFA degil KUME
# uzerinden yapilir: bir kumeden en fazla bir temsilci listeye girer ve
# uyelerinden biri zaten etiketliyse kume tumuyle listeden duser.
#
# Kumeleme BANKA ICINDE yapilir: kalip metni bankaya ozeldir ve olculen
# en benzer eslesmelerin tamami ayni bankadan cikmisti.
_KUME_ONBELLEK: dict[str, dict[str, list[dict]]] = {}


def _kumele(ham: dict) -> dict[str, list[dict]]:
    """banka -> kume listesi. Her kume: {"uyeler": [kayit], ...}"""
    import difflib

    banka_sayfalar: dict[str, list[dict]] = defaultdict(list)
    for slug, kayit in sorted(ham.items()):
        banka_sayfalar[kayit.get("banka") or "BILINMIYOR"].append(
            {**kayit, "_slug": slug,
             "_katlanmis": turkce_ascii_kucult(kayit.get("normalize_metin") or "")}
        )

    sonuc: dict[str, list[dict]] = {}
    for banka, sayfalar in banka_sayfalar.items():
        kumeler: list[dict] = []
        for sayfa in sayfalar:
            metin = sayfa["_katlanmis"]
            # Cok kisa sayfalar birbirine "benziyor" gorunur; kumelemeye
            # sokmadan her biri kendi kumesi sayilir.
            if len(metin) >= 200:
                for kume in kumeler:
                    olcer = difflib.SequenceMatcher(None, metin, kume["_temsil_metin"])
                    if olcer.real_quick_ratio() < COK_BENZER_ESIGI:
                        continue
                    if olcer.quick_ratio() < COK_BENZER_ESIGI:
                        continue
                    if olcer.ratio() >= COK_BENZER_ESIGI:
                        kume["uyeler"].append(sayfa)
                        break
                else:
                    kumeler.append({"uyeler": [sayfa], "_temsil_metin": metin})
            else:
                kumeler.append({"uyeler": [sayfa], "_temsil_metin": metin})
        sonuc[banka] = kumeler
    return sonuc


def _kumeleri_al(ham: dict) -> dict[str, list[dict]]:
    """Kumeleme pahalidir (bankalar icinde O(n^2) metin karsilastirmasi)
    ve testler is_listesi_uret'i birden fazla kez cagirir - sonuc ayni
    korpus icin onbellege alinir."""
    imza = f"{len(ham)}:{max((k.get('erisim_zamani') or '') for k in ham.values())}"
    if imza not in _KUME_ONBELLEK:
        _KUME_ONBELLEK[imza] = _kumele(ham)
    return _KUME_ONBELLEK[imza]


def _gerekce_metni(yeni: set[str], tumu: set[str] | None = None) -> str:
    """Kaydin NEDEN secildigini insan diliyle yazar - liste takip
    edilebilir olmali, "kod boyle sectti" yeterli degil.

    Yapisal ozellik uzayi kucuktur (~30 belirtec) ve hizla doyar; o
    noktadan sonra secim "en zengin kalan sayfa" olcutune duser. O
    durumda bile kaydin NE TASIDIGI yazilir, yoksa listenin ikinci
    yarisi gerekcesiz gorunur."""
    if not yeni:
        if tumu:
            # uzunluk bandi burada gurultudur; ayirt edici olan
            # yapi/taksit/odul belirtecleridir.
            onemli = sorted(b for b in tumu if not b.startswith("uzunluk="))
            return ("yeni ozellik yok; kalan havuzun en zengin sayfasi - "
                    "tasidigi: " + ", ".join(onemli))
        return "kalan havuzdan; yeni bir yapisal ozellik getirmiyor"
    parcalar = []
    taksitler = sorted(int(b.split("=")[1]) for b in yeni if b.startswith("taksit="))
    if taksitler:
        parcalar.append("yeni taksit degeri " + ", ".join(str(t) for t in taksitler))
    oduller = sorted(b.split("=", 1)[1] for b in yeni if b.startswith("odul="))
    if oduller:
        parcalar.append("yeni odul birimi " + ", ".join(oduller))
    yapilar = sorted(b.split("=", 1)[1] for b in yeni if b.startswith("yapi="))
    if yapilar:
        parcalar.append("yeni kosul yapisi " + ", ".join(yapilar))
    for ad, etiket in (("tarih", "ilk kez tarih tasiyor"),
                       ("tutar", "ilk kez TL tutari tasiyor"),
                       ("yuzde", "ilk kez yuzde tasiyor")):
        if ad in yeni:
            parcalar.append(etiket)
    uzunluk = sorted(b.split("=", 1)[1] for b in yeni if b.startswith("uzunluk="))
    if uzunluk:
        parcalar.append("yeni metin uzunlugu bandi " + ", ".join(uzunluk))
    return "; ".join(parcalar)


def is_listesi_uret(hedef: int, kota: int) -> dict:
    """Etiketlenecek kampanyalari KUME bazinda secer.

    Onceki surum sayfa bazindaydi: ayni kalibin her kopyasi ayri is
    olarak listeleniyor, benzerlik yalnizca ISARETLENIYORDU. Sonuc,
    etiketleyicinin listede pes pese yirmi tane "X magazasinda N taksit"
    gormesiydi.

    Artik:
      1. Sayfalar banka icinde %85 benzerlikle kumelenir.
      2. Bir uyesi zaten etiketliyse kume TUMUYLE duser - kapsanmis bir
         kalip ikinci kez etiketlenmez.
      3. Kalan her kumeden TEK temsilci alinir.
      4. Temsilciler, altin sette HENUZ BULUNMAYAN yapisal ozellik
         getirenlerden baslanarak siralanir (bkz. _yapisal_belirtecler).
      5. Banka kotasi dagilimin tek bankaya kaymasini engeller.
    """
    etiketli, etiketli_adlar = _etiketli_kimlikler()
    ham = _ham_kampanyalar()
    etiketli_metinler = _etiketli_metinler(ham)
    kumeler_banka = _kumeleri_al(ham)

    kontrol_gerek: list[dict] = []
    aday_kumeler: dict[str, list[dict]] = {}
    ozet: list[dict] = []

    for banka, kumeler in sorted(kumeler_banka.items()):
        adaylar: list[dict] = []
        kapsanan = 0
        for kume in kumeler:
            uyeler = kume["uyeler"]
            sluglar = [u["_slug"] for u in uyeler]
            # URL PARCASI DA KAPSAR: T.O.M.'un uc altin kaydi (TOM-001/002/
            # 003) "kampanyalar.html" adresinden geliyor; ham korpusta ayni
            # sayfa ayrica "kampanyalar.html#restoran-harcamalar..." gibi
            # BOLUM adresleriyle de duruyor. Duz slug esitligi bunlari
            # kapsanmis saymadigi icin uc kayit yeniden listeleniyordu.
            if any(sl in etiketli or sl.split("#", 1)[0] in etiketli
                   for sl in sluglar):
                kapsanan += 1
                continue

            # Kontrol gerektiren sayfalar (bosluklu adres, kategori
            # kalibi) ana listeye girmez ama ATILMAZ - insan bakar.
            uygun, kontrole = [], []
            for u in uyeler:
                if " " in u["_slug"] or KONTROL_GEREK_KALIBI.search(u["_slug"]):
                    kontrole.append(u)
                else:
                    uygun.append(u)
            for u in kontrole:
                kontrol_gerek.append({
                    "slug": u["_slug"],
                    "banka": u.get("banka"),
                    "url": u.get("url"),
                    "metin_uzunlugu": len(u.get("normalize_metin") or ""),
                })
            if not uygun:
                continue

            for u in uygun:
                u["_belirtec"] = _yapisal_belirtecler(u.get("normalize_metin") or "")
            # Temsilci: en cok yapisal ozellik tasiyan sayfa. Esitlikte
            # slug - ayni girdiyle ayni liste cikmali.
            temsilci = sorted(uygun, key=lambda u: (-len(u["_belirtec"]), u["_slug"]))[0]
            adaylar.append({"temsilci": temsilci,
                            "uyeler": sorted(u["_slug"] for u in uyeler)})

        aday_kumeler[banka] = adaylar
        ozet.append({
            "banka": banka,
            "ham_kampanya": sum(len(k["uyeler"]) for k in kumeler),
            "kume": len(kumeler),
            "kapsanan_kume": kapsanan,
            "aday_kume": len(adaylar),
        })
    ozet.sort(key=lambda o: -o["aday_kume"])

    # ALTIN SETTE ZATEN TEMSIL EDILEN OZELLIKLER: secim bunlarin
    # uzerine ne kattigina bakar, bos sayfadan baslamaz.
    gorulmus: set[str] = set()
    for slug in etiketli:
        kaynak = ham.get(slug)
        if kaynak:
            gorulmus |= _yapisal_belirtecler(kaynak.get("normalize_metin") or "")
    baslangic_ozellik = len(gorulmus)

    secilenler: list[dict] = []
    alinan: dict[str, int] = defaultdict(int)
    kalan = {b: list(v) for b, v in aday_kumeler.items()}
    bankalar = sorted(kalan)

    while len(secilenler) < hedef:
        eklendi = False
        for banka in bankalar:
            if len(secilenler) >= hedef:
                break
            if alinan[banka] >= kota or not kalan[banka]:
                continue
            # EN COK YENI OZELLIK GETIREN kume. Esitlikte once daha
            # zengin sayfa, sonra slug (deterministiklik).
            en_iyi = sorted(
                kalan[banka],
                key=lambda a: (-len(a["temsilci"]["_belirtec"] - gorulmus),
                               -len(a["temsilci"]["_belirtec"]),
                               a["temsilci"]["_slug"]),
            )[0]
            kalan[banka].remove(en_iyi)

            t = en_iyi["temsilci"]
            yeni_ozellikler = t["_belirtec"] - gorulmus
            gorulmus |= t["_belirtec"]
            baslik = _baslik(t)
            secilenler.append({
                "sira": len(secilenler) + 1,
                "banka": banka,
                "baslik": baslik,
                "url": t.get("url"),
                "slug": t["_slug"],
                "son_tarama": (t.get("erisim_zamani") or "")[:10],
                # NEDEN SECILDI - liste takip edilebilir olmali.
                "secim_gerekcesi": _gerekce_metni(yeni_ozellikler, t["_belirtec"]),
                "yeni_ozellikler": sorted(yeni_ozellikler),
                "yapisal_ozellikler": sorted(t["_belirtec"]),
                # Kumedeki diger sayfalar: bu temsilci onlari da temsil
                # eder, ayrica etiketlenmezler.
                "kume_uyeleri": [sl for sl in en_iyi["uyeler"] if sl != t["_slug"]],
                # Emniyet agi: kumeleme tek gecislidir, temsilciye
                # benzemeyip baska bir etiketli sayfaya benzeyen bir
                # sayfa buradan yakalanir.
                "muhtemel_kopya": _kopya_suphesi(
                    t["_slug"], baslik, etiketli, etiketli_adlar
                ),
                "cok_benzer": _cok_benzer_ikiz(
                    turkce_ascii_kucult(t.get("normalize_metin") or ""),
                    banka, etiketli_metinler
                ),
            })
            alinan[banka] += 1
            eklendi = True
        if not eklendi:
            break  # tum kotalar doldu ya da aday kalmadi

    return {
        "hedef_yeni_kayit": hedef,
        "banka_basina_kota": kota,
        "benzerlik_esigi": COK_BENZER_ESIGI,
        "mevcut_altin_kayit": len(etiketli),
        "listelenen": len(secilenler),
        "ulasilabilir_toplam": len(etiketli) + len(secilenler),
        "toplam_kume": sum(o["kume"] for o in ozet),
        "kapsanan_kume": sum(o["kapsanan_kume"] for o in ozet),
        "aday_kume": sum(o["aday_kume"] for o in ozet),
        "kalan_kume": {b: len(v) for b, v in sorted(kalan.items()) if v},
        "ozellik_kapsami": {"baslangic": baslangic_ozellik, "bitis": len(gorulmus)},
        "kontrol_gerek": kontrol_gerek,
        "banka_ozeti": ozet,
        "banka_basina_secilen": dict(sorted(alinan.items())),
        "liste": secilenler,
    }


def main() -> None:
    a = argparse.ArgumentParser(description="Etiketleme sprinti is listesi")
    a.add_argument("--hedef", type=int, default=200, help="Kac YENI kayit etiketlenecek")
    a.add_argument("--kota", type=int, default=45,
                   help="Banka basina azami kampanya (kume temsilcisi)")
    a.add_argument("--goster", type=int, default=15, help="Ekranda kac satir gosterilsin")
    s = a.parse_args()

    r = is_listesi_uret(s.hedef, s.kota)

    print("=" * 74)
    print("  ETIKETLEME SPRINTI - IS LISTESI")
    print("=" * 74)
    print(f"\n  Mevcut altin kayit : {r['mevcut_altin_kayit']}")
    print(f"  Hedef yeni kayit   : {r['hedef_yeni_kayit']}  "
          f"(banka basina kota {r['banka_basina_kota']})")
    print(f"  Benzerlik esigi    : %{r['benzerlik_esigi'] * 100:.0f}")
    print(f"  Listelenebilen     : {r['listelenen']}")
    print(f"  Ulasilabilir toplam: {r['ulasilabilir_toplam']}")
    print(f"  Yapisal ozellik kapsami: {r['ozellik_kapsami']['baslangic']} "
          f"-> {r['ozellik_kapsami']['bitis']}")

    print(f"\n  KUME DAGILIMI (ayni kalibin kopyalari tek kumede)")
    print("  Banka                 sayfa   kume  kapsanan  aday  secilen  kalan")
    print("  " + "-" * 68)
    for o in r["banka_ozeti"]:
        secilen = r["banka_basina_secilen"].get(o["banka"], 0)
        kalan = r["kalan_kume"].get(o["banka"], 0)
        print(f"  {o['banka'][:20]:<20}{o['ham_kampanya']:>7}{o['kume']:>7}"
              f"{o['kapsanan_kume']:>10}{o['aday_kume']:>6}{secilen:>9}{kalan:>7}")
    print("  " + "-" * 68)
    print(f"  {'TOPLAM':<20}{sum(o['ham_kampanya'] for o in r['banka_ozeti']):>7}"
          f"{r['toplam_kume']:>7}{r['kapsanan_kume']:>10}{r['aday_kume']:>6}"
          f"{r['listelenen']:>9}{sum(r['kalan_kume'].values()):>7}")

    if r["ulasilabilir_toplam"] < 200:
        eksik = 200 - r["ulasilabilir_toplam"]
        print(f"\n  UYARI: kota {r['banka_basina_kota']} ile 200'e {eksik} kayit "
              f"KALIYOR.\n  Kotayi yukseltmek hacmi artirir ama seti buyuk bankalara "
              f"kaydirir;\n  denge korunacaksa eksik bankalardan YENI VERI toplanmalidir.")
    elif sum(r["kalan_kume"].values()):
        print(f"\n  200 hedefi karsilaniyor. Kotaya takilip listeye giremeyen "
              f"{sum(r['kalan_kume'].values())} benzersiz kume var;\n  hacim daha da "
              f"gerekirse kota yukseltilebilir (denge bedeliyle).")

    kg = r["kontrol_gerek"]
    if kg:
        print(f"\n  KONTROL GEREK ({len(kg)} sayfa) - kategori sayfasi OLABILIR,")
        print("  ama T.O.M. ornegindeki gibi coklu kampanya sayfasi da olabilir")
        print("  (TOM-001/002/003 tek sayfadan cikti). Once bunlara bakin:")
        for x in sorted(kg, key=lambda z: -z["metin_uzunlugu"])[:8]:
            print(f"    [{(x['banka'] or '')[:14]:<14}] {x['slug'][:40]:<40} "
                  f"{x['metin_uzunlugu']:>6} krk")

    supheli = [k for k in r["liste"] if k.get("muhtemel_kopya") or k.get("cok_benzer")]
    if supheli:
        print(f"\n  EMNIYET AGI ({len(supheli)} kayit) - kumeleme kacirmis olabilir,")
        print("  etiketlemeden once ikizine bakin:")
        for k in supheli[:8]:
            sebep = k.get("muhtemel_kopya") or (
                f"%{k['cok_benzer'][1] * 100:.0f} benzer <-> {k['cok_benzer'][0]}")
            print(f"    {k['sira']:>3}. {k['slug'][:38]:<38} ({sebep})")

    print(f"\n  Ilk {s.goster} kayit (banka | neden secildi):\n")
    for k in r["liste"][:s.goster]:
        temsil = f"  [+{len(k['kume_uyeleri'])} benzer sayfayi temsil ediyor]" if k["kume_uyeleri"] else ""
        # SLUG DA YAZILIR: Ziraat sayfalarinin bir kisminda kampanya
        # basligi metinde HIC gecmiyor (sayfa dogrudan kosullarla
        # basliyor); orada sayfayi taniyan tek sey slug'dir.
        print(f"  {k['sira']:>3}. [{k['banka'][:14]:<14}] {k['baslik'][:50]}")
        print(f"       {k['slug'][:64]}")
        print(f"       -> {k['secim_gerekcesi']}{temsil}")

    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=2)
    print(f"\n  Tam liste: {CIKTI.relative_to(KOK)}")


if __name__ == "__main__":
    main()

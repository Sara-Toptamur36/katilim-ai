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
Ham korpus banka bazinda dengesizdir (bkz. ciktidaki tablo). Bu yuzden
"200-300 kayit" ve "bankalar arasi denge" AYNI ANDA saglanamaz:

  - Tam denge istenirse tavan, en az kampanyaya sahip bankanin sayisidir
  - Hacim istenirse set kacinilmaz olarak en buyuk bankalara kayar

Bu script ikisinin arasini KOTA ile bulur: her bankadan en fazla `--kota`
kampanya onerilir. Kota disinda kalanlar listeye girmez; boylece hedef
sayiya ulasilirken tek bir bankanin sayfa uslubu olcumu domine etmez.
Kalan dengesizlik ciktida ACIKCA yazilir - gizlenmez.

GUNCELLEME (22 Agustos 2026): 21 Agustos'taki sitemap.xml taramasi 4
bankada +198 kampanya bulunca dengesizligin sekli degisti - "iki banka
cogunluk, iki banka 3'er kampanya" artik dogru degil (bkz. ciktidaki
guncel tablo: en kucuk banka bile artik 3'ten fazla, ama en buyuk uc
banka 80-109 arasinda). Kota=30 ile ulasilabilir toplam artik 200
hedefini asiyor (bkz. tests/test_sprint_is_listesi.py::
test_hedef_karsilaniyorsa_bu_GIZLENMEZ) - yani darbogaz artik korpus
hacmi degil, ETIKETLEME SURESI.

Kullanim:
    python -m gold_dataset.sprint_is_listesi
    python -m gold_dataset.sprint_is_listesi --hedef 200 --kota 30
"""

from __future__ import annotations

import argparse
import glob
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from extraction.normalizer import TR_AY_ADLARI, tutara_cevir, turkce_ascii_kucult

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
    """Kampanya basligi, ham metnin SLUG'A EN COK BENZEYEN satiridir.

    Cikarim motoru CAGRILMAZ (bkz. modul docstring'i) - bu yalnizca
    etiketleyicinin listede kampanyayi tanimasi icin bir etikettir,
    yer gercegi degildir.

    NEDEN "ILK UZUN SATIR" DEGIL (olculdu): o kural liste boyunca
    okunamaz basliklar uretti -
      "10 Temmuz 2026 - 7 Agustos 2026"              (tarih araligi)
      "Bankkart Lira kazanabilmek icin alisveris.."  (cumle ortasi)
      "Saat&Saat Magazalarindan ve"                  (cumle parcasi)
    Ziraat ve Emlak sayfalari kampanya adini basliga koymuyor; metin
    kampanya doneminden ya da kosul cumlesinden basliyor.

    SLUG kampanyanin kimligini tasir ("mobilya-alisverisinize-1500-tl-
    bankkart-lira"). Bu yuzden aday satirlar slug kelimeleriyle ORTUSME
    oranina gore puanlanir; hicbir satir ortusmuyorsa slug'in kendisi
    okunabilir hale getirilip kullanilir. Uydurma yok: her iki durumda da
    gosterilen sey sayfanin kendi metni ya da kendi adresidir.
    """
    metin = kayit.get("normalize_metin") or kayit.get("ham_metin") or ""
    banka = turkce_ascii_kucult(kayit.get("banka") or "")
    slug = kayit.get("_slug") or _slug(kayit.get("url") or "")
    # AYIRT EDICI SLUG KELIMELERI. Ziraat'in slug'larinin neredeyse
    # hepsinde "bankkart" ve "lira" gecer; o kelimelerle eslesen bir
    # satir kampanyayi TANITMAZ. Olculdu: "Bankkart Lira kazanabilirsiniz."
    # cumle kuyrugu %40 ortusme aliyor ve baslik secilebiliyordu.
    # Bankanin slug'larinda YAYGIN olan kelimeler elenir; geriye kampanyayi
    # ayirt eden kelimeler kalir ("mobilya", "alisverisinize", "1500").
    yaygin = _yaygin_slug_kelimeleri(kayit.get("banka") or "")
    slug_kelimeleri = {
        k for k in re.split(r"[^a-z0-9]+", turkce_ascii_kucult(slug))
        if len(k) >= 4 and k not in yaygin
    }

    if not slug_kelimeleri:
        # Slug ayirt edici kelime tasimiyor: metinden secilecek bir
        # satirin kampanyayi TANITTIGINI dogrulayamayiz. Ilk surum bu
        # durumda "ilk uygun satiri" aliyordu ve cumle kuyruklari
        # baslik oluyordu.
        return _sluga_gore_baslik(slug)

    en_iyi: tuple[float, int, str] | None = None
    for sira, satir in enumerate(metin.split("\n")):
        sade = " ".join(satir.split())
        if not (25 < len(sade) <= 110):
            continue
        kucuk = turkce_ascii_kucult(sade)
        if any(i in kucuk for i in _GEZINTI_ISARETLERI):
            continue
        if banka and kucuk.startswith(banka):
            continue
        if sade[0].islower():
            continue  # cumle ortasi
        # CUMLE SONU BAGLACI = SATIR YARIM KALMIS. Olculdu: korpus
        # buyudukten sonra "Paraf ile A101 Magazalarinda ve" ve
        # "Hizli Cicek mobil uygulamasindan dilediginiz urunu sepete
        # ekleyin," gibi satirlar baslik seciliyordu - ikisi de slug'la
        # ortusuyor ama kampanyayi TANITMIYOR, cumlenin ortasindan
        # kesilmis.
        if sade.rstrip().endswith((" ve", " ile", " veya", ",", ";", ":")):
            continue
        satir_kelimeleri = {
            k for k in re.split(r"[^a-z0-9]+", kucuk) if len(k) >= 4
        }
        # KOK ESLESMESI - Turkce eklerini asmak icin. Olculdu: slug
        # "hepsiburadada" (bulunma eki slug'a girmis), sayfadaki basliksa
        # "Hepsiburada'da" -> kelime kelime eslesme SIFIR veriyor ve
        # sayfanin gercek basligi reddedilip slug'a dusuluyordu.
        # Ilk 6 karakter karsilastirmasi eki asar, farkli kelimeleri
        # birlestirmeye yetmez ("mobilya" vs "mobile" gibi cakismalar
        # 6 karakterde ayrisir).
        koku = lambda k: k[:6]
        satir_kokleri = {koku(k) for k in satir_kelimeleri}
        eslesen = sum(1 for k in slug_kelimeleri if koku(k) in satir_kokleri)
        ortusme = eslesen / len(slug_kelimeleri)
        # ESIK 0.6 VE KONUM ONCELIKLI - ikisi de olculdu.
        #
        # Ortusme TEK BASINA "baslik" ile "kosul cumlesi"ni ayirmiyor:
        # "Kampanyaya Trendyol Dolap uygulamasindan yapilacak..." cumlesi
        # slug'daki tek ayirt edici kelimeyle (%100) esleserek baslik
        # seciliyordu. Iki duzeltme birlikte calisiyor:
        #   - esik 0.6: ayirt edici kelimelerin YARIDAN FAZLASI gecmeli,
        #     boylece "alisveris" gibi tek bir genel kelimeyle eslesen
        #     parcalar elenir,
        #   - konum onceligi: esigi gecen EN ERKEN satir kazanir, cunku
        #     baslik sayfada kosullardan ONCE durur.
        aday = (-sira, ortusme, sade[:80])
        if ortusme >= 0.6 and (en_iyi is None or aday > en_iyi):
            en_iyi = aday

    if en_iyi:
        return en_iyi[2]
    # Hicbir satir slug'i tanitmiyor: adresin kendisi daha bilgilendirici.
    return _sluga_gore_baslik(slug)


_YAYGIN_ONBELLEK: dict[str, set[str]] = {}


def _yaygin_slug_kelimeleri(banka: str) -> set[str]:
    """Bir bankanin slug'larinin en az yarisinda gecen kelimeler."""
    if banka in _YAYGIN_ONBELLEK:
        return _YAYGIN_ONBELLEK[banka]
    sluglar = [
        _slug(k.get("url") or "")
        for k in _ham_kampanyalar().values()
        if (k.get("banka") or "") == banka
    ]
    sayac: Counter[str] = Counter()
    for sl in sluglar:
        sayac.update({
            k for k in re.split(r"[^a-z0-9]+", turkce_ascii_kucult(sl)) if len(k) >= 4
        })
    # ESIK NEDEN %20 (olculdu): satir kaliplari icin kullanilan %50, slug
    # kelimeleri icin fazla katiydi - Ziraat'in 109 slug'inda yalnizca
    # "taksit" yakalaniyordu; "bankkart" (31) ve "lira" (30) kaciyor ve
    # "Bankkart Lira kazanabilirsiniz." cumle kuyrugu baslik seciliyordu.
    # Ziraat'te 30 (lira) ile 12 (toplam) arasinda dogal bir bosluk var,
    # yani %13-%30 arasindaki her esik AYNI kumeyi verir - secim bicak
    # sirti degil. %10'a inince "indirim" gibi ayirt edici kelimeler de
    # elenmeye basliyor.
    esik = max(3, int(len(sluglar) * 0.20))
    _YAYGIN_ONBELLEK[banka] = {k for k, n in sayac.items() if n >= esik}
    return _YAYGIN_ONBELLEK[banka]


def _sluga_gore_baslik(slug: str) -> str:
    """"mobilya-alisverisinize-1500-tl-bankkart-lira-0" ->
    "Mobilya Alisverisinize 1500 TL Bankkart Lira" """
    govde = slug.split("#", 1)[0]
    for uzanti in (".aspx", ".html", ".htm"):
        if govde.lower().endswith(uzanti):
            govde = govde[: -len(uzanti)]
    kelimeler = [k for k in re.split(r"[-_]+", govde) if k]
    # Sondaki surum numaralari kampanyayi tanitmaz.
    while kelimeler and kelimeler[-1].isdigit():
        kelimeler.pop()
    duzgun = []
    for k in kelimeler:
        duzgun.append(k.upper() if k.lower() in ("tl", "qr", "mtv", "kdv") else k.capitalize())
    return " ".join(duzgun)[:80] or slug[:80]


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

# ---------------------------------------------------------------------------
# KARSILASTIRMA METNI - banka kalibi CIKARILIR
# ---------------------------------------------------------------------------
# OLCULEN HATA: ilk surum sayfalari HAM haliyle karsilastiriyordu. Dunya
# Katilim sayfalarinin 12.337 karakterinin ~10.000'i her sayfada ayni
# menu/altbilgi oldugu icin BIRBIRIYLE ALAKASIZ iki kampanya %87 benzer
# cikiyordu: "LC Waikiki'de 300 TL indirim" ile "Avantajli Kurlar". Kalip
# satirlar cikarilinca ayni cift %11'e dusuyor.
#
# Yani esik degil OLCUM yanlisti: agir menulu bankalarda her sayfa her
# sayfaya benziyor, hafif menulu bankalarda benzemiyordu. Bu, Dunya
# Katilim'in tum sayfalarinin sahte kumelere dusmesine ve gercek
# kampanyalarin listeden silinmesine yol aciyordu.
#
# Karsi kontrol: gercekten ayni olan ciftler kalip cikarildiktan SONRA da
# yuksek kaliyor (Emlak akaryakit 300/400 TL surumleri %98 -> %98).
_KALIP_ONBELLEK: dict[str, dict[str, set[str]]] = {}


def _banka_kaliplari(ham: dict) -> dict[str, set[str]]:
    """banka -> o bankanin sayfalarinin en az yarisinda gecen satirlar."""
    imza = f"{len(ham)}:{max((k.get('erisim_zamani') or '') for k in ham.values())}"
    if imza in _KALIP_ONBELLEK:
        return _KALIP_ONBELLEK[imza]

    banka_satirlar: dict[str, list[set[str]]] = defaultdict(list)
    for kayit in ham.values():
        metin = turkce_ascii_kucult(kayit.get("normalize_metin") or "")
        banka_satirlar[kayit.get("banka") or "BILINMIYOR"].append(
            {sat.strip() for sat in metin.split("\n") if sat.strip()}
        )

    sonuc: dict[str, set[str]] = {}
    for banka, sayfalar in banka_satirlar.items():
        sayac: Counter[str] = Counter()
        for satirlar in sayfalar:
            sayac.update(satirlar)
        # En az 2 sayfada VE sayfalarin en az yarisinda gecen satir kaliptir.
        esik = max(2, len(sayfalar) // 2)
        sonuc[banka] = {sat for sat, n in sayac.items() if n >= esik}
    _KALIP_ONBELLEK[imza] = sonuc
    return sonuc


def _karsilastirma_metni(metin: str, kalip: set[str]) -> str:
    """Katlanmis metinden banka kalibi cikarilmis hali."""
    return "\n".join(
        sat for sat in turkce_ascii_kucult(metin).split("\n")
        if sat.strip() and sat.strip() not in kalip
    )


def _oran(a: str, b: str) -> float:
    """Iki metnin benzerlik orani.

    autojunk=False SART: varsayilan autojunk, uzunlugu 200'u gecen IKINCI
    dizide sik gecen ogeleri "gurultu" sayip atar. Bunun iki sonucu var -
    olcum ARGUMAN SIRASINA gore degisir (ayni cift icin %86 ve %83
    olculdu) ve uzun metinlerde oran carpitilir. Kaynak kodu satirlari
    icin tasarlanmis bir sezgiseldir, dogal metinde isimize yaramaz.
    """
    import difflib

    olcer = difflib.SequenceMatcher(None, a, b, autojunk=False)
    # real_quick_ratio/quick_ratio gercek oranin UST SINIRLARIDIR ve ucuzdur;
    # esigin altinda kalan cift icin pahali ratio() hic calistirilmaz.
    # (Ilk surumde bunlar autojunk ile birlikte kaldirilmisti ve kumeleme
    # dakikalarca surer hale gelmisti.)
    if olcer.real_quick_ratio() < COK_BENZER_ESIGI:
        return 0.0
    if olcer.quick_ratio() < COK_BENZER_ESIGI:
        return 0.0
    return olcer.ratio()


def _cok_benzer_ikiz(metin: str, banka: str, etiketli_metinler: dict,
                     profil: frozenset | None = None) -> tuple[str, float] | None:
    """Ayni bankanin etiketli sayfalari icinde en benzerini bulur.

    YALNIZCA AYNI BANKA: kalip metni bankaya ozeldir ve olcumde en
    benzer eslesmelerin TAMAMI ayni bankadan cikti. Bankaya kisitlamak
    hem daha dogru hem de karsilastirma sayisini buyuk olcude azaltir.
    """
    if len(metin) < 200:
        return None
    en_iyi: tuple[str, float] | None = None
    for kayit_id, (kayit_banka, kayit_metni, kayit_profili) in etiketli_metinler.items():
        if kayit_banka != banka or len(kayit_metni) < 200:
            continue
        # FARKLI PROFIL = FARKLI DEGER TASIYOR. Ziraat'in "2 taksit" ve
        # "6 taksit" sayfalari metin olarak %91 ayni ama kopya degiller;
        # burada isaretlenmeleri emniyet agini gurultuye bogar ve gercek
        # kopyayi gorunmez kilar. Ayrica pahali karsilastirmayi da atlar.
        if profil is not None and profil != kayit_profili:
            continue
        oran = _oran(metin, kayit_metni)
        if oran >= COK_BENZER_ESIGI and (en_iyi is None or oran > en_iyi[1]):
            en_iyi = (kayit_id, oran)
    return en_iyi


def _etiketli_metinler(ham: dict) -> dict[str, tuple[str, str, frozenset]]:
    """kayit_id -> (banka, katlanmis metin). Kaynak sayfasi ham veride
    kalmamis kayitlar disarida kalir - kampanya rotasyonu."""
    kaliplar = _banka_kaliplari(ham)
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
        banka = kaynak.get("banka") or k.get("banka") or ""
        ham_metin = kaynak.get("normalize_metin") or ""
        sonuc[k["kayit_id"]] = (
            banka,
            _karsilastirma_metni(ham_metin, kaliplar.get(banka, set())),
            frozenset(_yapisal_belirtecler(ham_metin)),
        )
    return sonuc


# ---------------------------------------------------------------------------
# YAPISAL PROFIL - "bu sayfa hangi alan turlerini barindiriyor"
# ---------------------------------------------------------------------------
# Bunlar OLCUM yapmaz, DEGER uretmez: yalnizca sayfada o turden bir sey
# gecip gecmedigini soyler.
#
# regex_extractor CAGRILMAZ VE CAGRILMAMALI: o, olculen motordur; ciktisi
# siraya girerse olcum dairesel olur. Buna karsilik `extraction.normalizer`
# bir NORMALLESTIRICIDIR - bicim bilgisi tasir, karar uretmez - ve
# kullanilir.
#
# ILK SURUMDEKI HATA: tutar ve ay adlari burada ELLE yeniden yazilmisti.
# Kopya hem gereksizdi hem de ZAYIFTI: tutar deseni binlik ayiraci ZORUNLU
# kiliyordu (`\d{1,3}(?:\.\d{3})+`), yani "500 TL" hic gorulmuyordu ve
# T.O.M.'un kelimeyle yazdigi "250 Bin TL" bicimi de gorulmuyordu - oysa o
# bicim normalizer'da zaten olculup belgelenmis bir bulgudur
# (bkz. normalizer._BUYUKLIK_EKLERI aciklamasi).
_TARIH_IZI = re.compile(
    r"\d{1,2}[./]\d{1,2}[./]\d{4}"
    r"|\d{1,2}\s+(?:" + "|".join(TR_AY_ADLARI) + r")\b",
    re.IGNORECASE,
)
# Tutar ADAYLARINI bulur; DEGERE cevirmeyi normalizer.tutara_cevir yapar.
# (normalizer._TUTAR_DESENI bir arayici degil, izole edilmis bir dizgiyi
# ayristirmak icindir - sayfa taramasinda her sayiya eslesirdi.)
_TUTAR_IZI = re.compile(
    r"\d{1,3}(?:\.\d{3})*(?:,\d+)?\s*(?:bin|milyon|milyar)?\s*(?:TL|₺)",
    re.IGNORECASE,
)
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


# BILINEN SINIRLILIK - YAN MENU KIRLILIGI (olculdu, 23 Agustos 2026)
# Kaynak sayfalar JS ile yeniden tarandiktan sonra Ziraat sayfalari
# "diger kampanyalar" yan menusunu de tasiyor. O menudeki kampanyalarin
# taksit sayilari da metne giriyor: ZK-012 (Alarko, 6 taksit) ve ZK-017
# (BAUHAUS, 3 taksit) sayfalarinin ikisi de {3,5,6,9,12} kumesini
# uretiyor ve profilleri AYNILASIYOR.
#
# Kalip temizligi bunu cozmez: yan menu her sayfada FARKLI kampanyalari
# listeledigi icin hicbir satir "bankanin yarisinda geciyor" esigini
# gecmiyor.
#
# ETKISI OLCULDU: eleme "metin >=%85 VE profil ayni" kosuluna bagli
# oldugu icin YANLIS ELEME URETMIYOR - farkli Ziraat kampanyalarinin
# govde metni birbirine benzemiyor (kuyruktaki 56 Ziraat kaydinin hicbiri
# elenmedi). Zarar yalnizca SIRALAMA kalitesinde: o sayfalarda "yeni
# taksit degeri" sinyali gurultulu.
#
# Cozulecekse dogru yer burasi degil, TARAMA tarafidir: sayfanin kendi
# icerik bolgesini hedefleyen bir secici, yan menuyu bastan disarida
# birakir (bkz. js_scraper.GENEL_ICERIK_ADAYLARI).
def _yapisal_belirtecler(metin: str) -> set[str]:
    """Sayfayi CESITLILIK acisindan tanimlayan belirtec kumesi.

    Secim bu kumeler uzerinden yapilir: hicbir yeni belirtec getirmeyen
    bir sayfa, altin sete zaten temsil edilen bir kalibi bir kez daha
    eklemekten baska is yapmaz.
    """
    # METIN UZUNLUGU BELIRTEC DEGILDIR - olculdu ve cikarildi. Ilk surumde
    # "uzunluk=kisa/orta/uzun" bir belirtecti; Hayat Finans'in "Bana Bunu
    # Al" (Troy) ve Xiaomi sayfalari %92 ayni metin, ayni taksit sayisi ve
    # ayni tutar bandini tasidigi halde YALNIZCA uzunluk bandi farkli oldugu
    # icin "farkli profil" sayilip ikisi de altin sete girmisti. Uzunluk bir
    # DEGER degildir; cesitlilik olcutu olarak kullanilmasi sahte ayrim
    # uretiyor.
    katlanmis = turkce_ascii_kucult(metin)
    belirtecler: set[str] = set()

    tarihler = _TARIH_IZI.findall(metin)
    tutarlar = _TUTAR_IZI.findall(metin)
    var_tarih, var_tutar = bool(tarihler), bool(tutarlar)
    var_yuzde = bool(_YUZDE_IZI.search(metin))

    if var_tarih:
        belirtecler.add("tarih")
        # Sayfada BIRDEN FAZLA tarih izi olmasi (baslangic + bitis +
        # odul yukleme tarihi gibi) tek tarihli bir sayfadan farkli bir
        # cikarim problemidir. Bu bir SAYIMDIR, anlamsal tarih ayristirma
        # DEGIL: "1-31 Agustos 2026" tek iz olarak gecer.
        if len(tarihler) > 1:
            belirtecler.add("tarih_coklu")
    if var_yuzde:
        belirtecler.add("yuzde")

    # TUTAR BUYUKLUK BANDI: "200 TL odul" ile "1.000.000 TL finansman"
    # ayni belirtec olmamali - ilk surumde ikisi de sadece "tutar"di ve
    # siralama aralarindaki farki goremiyordu.
    #
    # Cevirme isini normalizer.tutara_cevir yapar: Turkce binlik/ondalik
    # ayiraci ve "bin/milyon/milyar" ekleri onun sorumlulugudur. Burada
    # elle ayristirmak, ayni kurali ikinci bir yerde tutmak olurdu -
    # ustelik projenin daha once yasadigi "1.89 -> 189" hatasinin aynisini
    # davet ederdi.
    degerler = set()
    for ham_tutar in tutarlar:
        deger = tutara_cevir(ham_tutar)
        if deger is None:
            continue
        degerler.add(deger)
        for esik, ad in ((1_000_000, "1m+"), (100_000, "100b+"), (10_000, "10b+"),
                         (1_000, "1b+"), (0, "1b-")):
            if deger >= esik:
                belirtecler.add(f"tutar={ad}")
                break
    # KADEMELI ODUL: uc ya da daha fazla FARKLI tutar tasiyan sayfa
    # ("300 TL / 750 TL / 1.750 TL / 3.000 TL") duz bir sayfadan farkli
    # bir cikarim problemidir.
    if len(degerler) >= 3:
        belirtecler.add("kademeli_tutar")

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
    kaliplar = _banka_kaliplari(ham)
    banka_sayfalar: dict[str, list[dict]] = defaultdict(list)
    for slug, kayit in sorted(ham.items()):
        banka = kayit.get("banka") or "BILINMIYOR"
        banka_sayfalar[banka].append(
            {**kayit, "_slug": slug,
             "_katlanmis": _karsilastirma_metni(kayit.get("normalize_metin") or "",
                                                kaliplar.get(banka, set()))}
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
                    if _oran(metin, kume["_temsil_metin"]) >= COK_BENZER_ESIGI:
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


def _profile_gore_bol(kumeler: list[dict]) -> list[dict]:
    """Her kumeyi, uyelerinin yapisal profiline gore alt kumelere ayirir.

    Ayni metin + ayni profil = gercek kopya, tek temsilci.
    Ayni metin + FARKLI profil = farkli deger tasiyan sayfa, ayri kalir.
    """
    bolunmus: list[dict] = []
    for kume in kumeler:
        gruplar: dict[frozenset, list[dict]] = {}
        for uye in kume["uyeler"]:
            if "_belirtec" not in uye:
                uye["_belirtec"] = _yapisal_belirtecler(uye.get("normalize_metin") or "")
            gruplar.setdefault(frozenset(uye["_belirtec"]), []).append(uye)
        for _, uyeler in sorted(gruplar.items(), key=lambda g: g[1][0]["_slug"]):
            bolunmus.append({"uyeler": uyeler, "_kume_boyu": len(kume["uyeler"])})
    return bolunmus


def _gerekce_metni(yeni: set[str], tumu: set[str] | None = None) -> str:
    """Kaydin NEDEN secildigini insan diliyle yazar - liste takip
    edilebilir olmali, "kod boyle sectti" yeterli degil.

    Yapisal ozellik uzayi kucuktur (~30 belirtec) ve hizla doyar; o
    noktadan sonra secim "en zengin kalan sayfa" olcutune duser.

    O DURUMDA BELIRTEC LISTESI BURAYA YAZILMAZ: kaydin ne tasidigi zaten
    `yapisal_ozellikler` alaninda duruyor ve her iki raporda da onun
    yaninda gosteriliyor. Ilk surum listeyi buraya da dokuyordu; sonuc,
    ayni bilginin iki kez ve bir kez de ham belirtec adlariyla
    ("tutar=10b+") insan yuzlu bir alanda gorunmesiydi.
    """
    if not yeni:
        n = len(tumu) if tumu else 0
        return (f"yeni ozellik yok; havuzun en zengin sayfasi ({n} yapisal ozellik)"
                if n else "kalan havuzdan; yeni bir yapisal ozellik getirmiyor")
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
    return "; ".join(parcalar)


def is_listesi_uret(hedef: int, kota: int | None = None) -> dict:
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
      5. Banka kotasi (verilmisse) dagilimin tek bankaya kaymasini
         engeller. `kota=None` kotayi tumuyle kaldirir - havuzdaki her
         benzersiz kume listeye girer ve dagilim korpusun kendi
         dengesizligini yansitir. O dengesizlik raporda gorunur.
    """
    etiketli, etiketli_adlar = _etiketli_kimlikler()
    ham = _ham_kampanyalar()
    # KAYNAK SAYFASI HAM VERIDE OLMAYAN ETIKETLI KAYITLAR (kampanya
    # rotasyonu). Onlarla METIN karsilastirmasi YAPILAMAZ, dolayisiyla
    # kume kapsamasi da calismaz. Olculmus ornek: DK-003'un adresi
    # "/kampanyalar/altin-kesem" artik korpusta yok; ayni kampanya
    # "/kampanyalar/altin-kesemTicari" adresiyle duruyor ve kume
    # kapsamasi bunu goremedigi icin listeye giriyordu.
    #
    # Bu kayitlar icin ELIMIZDEKI TEK KANIT slug kurallaridir; orada
    # isaretlemekle yetinmeyip DISLIYORUZ. Kaynagi duran kayitlarda ise
    # metin+profil karsilastirmasi zaten calisir - slug kurali orada
    # yalnizca emniyet agi olarak kalir.
    kaynaksiz_etiketli = {sl for sl in etiketli if sl not in ham}
    etiketli_metinler = _etiketli_metinler(ham)
    kumeler_banka = _kumeleri_al(ham)
    kaliplar = _banka_kaliplari(ham)

    kontrol_gerek: list[dict] = []
    aday_kumeler: dict[str, list[dict]] = {}
    ozet: list[dict] = []

    for banka, kumeler in sorted(kumeler_banka.items()):
        adaylar: list[dict] = []
        kapsanan = 0
        # KUMEYI YAPISAL PROFILE GORE BOL.
        #
        # NEDEN: kalip satirlar cikarildiktan sonra Ziraat'in
        # "bauhausta-3-taksit" ve "alfemoda-5-taksit" sayfalari ayni kumeye
        # dusuyor - metin gercekten neredeyse ayni. Ama TAKSIT DEGERI farkli
        # ve o, olculen bir alandir. Kumeden tek temsilci alsaydik "3 taksit"
        # ya da "5 taksit"ten biri altin sette hic gorunmezdi.
        #
        # Bu yuzden birim KUME degil, (kume x yapisal profil) ciftidir:
        # ayni metnin ayni degerleri tasiyan kopyalari tek temsilciye iner,
        # farkli deger tasiyanlar ayri ayri kalir.
        bolunmus = _profile_gore_bol(kumeler)
        for kume in bolunmus:
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
            # Kaynagi kaybolmus bir etiketli kaydin adres ikizi mi?
            if kaynaksiz_etiketli and any(
                _kopya_suphesi(sl, "", kaynaksiz_etiketli, set()) for sl in sluglar
            ):
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
            # METIN KUMESI: yalnizca metne bakan kaba kumeleme.
            "metin_kumesi": len(kumeler),
            # SECIM BIRIMI: (metin kumesi x yapisal profil). kapsanan/aday/
            # secilen sayilari BUNUN uzerinden verilir - ilk surumde ust
            # satirda metin kumesi, alt satirlarda secim birimi yaziliyordu
            # ve tablo "kume 11, kapsanan 12" gibi imkansiz satirlar
            # uretiyordu.
            "kume": len(bolunmus),
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
    benzer_atlanan: list[dict] = []
    alinan: dict[str, int] = defaultdict(int)
    kalan = {b: list(v) for b, v in aday_kumeler.items()}
    bankalar = sorted(kalan)

    while len(secilenler) < hedef:
        eklendi = False
        for banka in bankalar:
            if len(secilenler) >= hedef:
                break
            if (kota is not None and alinan[banka] >= kota) or not kalan[banka]:
                continue
            # EN COK YENI OZELLIK GETIREN kume. Esitlikte once daha
            # zengin sayfa, sonra slug (deterministiklik).
            # KUMELEME TEK GECISLIDIR: bir aday, kendi kumesinin
            # temsilcisine benzemeyip BASKA bir etiketli sayfaya benzeyebilir.
            # Olculdu: "mobilya-...-4000-tlye-varan-parafpara" temsilciye
            # takilmadan listeye giriyor ama TEK-009 ile hem metni hem
            # yapisal profili ayni cikiyordu.
            #
            # Bu yuzden emniyet agi artik yalnizca ISARETLEMIYOR, ELIYOR.
            # Elenen kayit ATILMIYOR - `benzer_atlanan` altinda gerekcesiyle
            # raporlaniyor ki karar denetlenebilsin.
            en_iyi = None
            while kalan[banka]:
                aday = sorted(
                    kalan[banka],
                    key=lambda a: (-len(a["temsilci"]["_belirtec"] - gorulmus),
                                   -len(a["temsilci"]["_belirtec"]),
                                   a["temsilci"]["_slug"]),
                )[0]
                kalan[banka].remove(aday)
                at = aday["temsilci"]
                ikiz = _cok_benzer_ikiz(
                    _karsilastirma_metni(at.get("normalize_metin") or "",
                                         kaliplar.get(banka, set())),
                    banka, etiketli_metinler, frozenset(at["_belirtec"]),
                )
                if ikiz is None:
                    en_iyi = aday
                    break
                benzer_atlanan.append({
                    "slug": at["_slug"],
                    "banka": banka,
                    "url": at.get("url"),
                    "ikiz": ikiz[0],
                    "oran": round(ikiz[1], 3),
                    "gerekce": (f"altin setteki {ikiz[0]} ile metin benzerligi "
                                f"%{ikiz[1] * 100:.0f} VE yapisal profil ayni"),
                })
            if en_iyi is None:
                continue

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
                # Slug kurallari YALNIZCA ISARETLER (eleme yapmaz):
                # kaynagi duran kayitlarda metin+profil karsilastirmasi
                # zaten karar verdi, slug benzerligi tek basina bir
                # kampanyayi silmeye yetmez ("...-300-tl" ile "...-400-tl"
                # iki ayri kampanyadir).
                "muhtemel_kopya": _kopya_suphesi(
                    t["_slug"], baslik, etiketli, etiketli_adlar
                ),
                # Buraya gelen kayitta bu ALAN HER ZAMAN None'dir - dolu
                # olsaydi yukaridaki dongude elenirdi. Cikti sozlesmesinin
                # bir parcasi olarak birakildi.
                "cok_benzer": None,
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
        "benzer_atlanan": benzer_atlanan,
        "kontrol_gerek": kontrol_gerek,
        "banka_ozeti": ozet,
        "banka_basina_secilen": dict(sorted(alinan.items())),
        "liste": secilenler,
    }


def main() -> None:
    a = argparse.ArgumentParser(description="Etiketleme sprinti is listesi")
    a.add_argument("--hedef", type=int, default=200, help="Kac YENI kayit etiketlenecek")
    a.add_argument("--kota", type=int, default=None,
                   help="Banka basina azami kampanya; verilmezse KOTA YOK")
    a.add_argument("--goster", type=int, default=15, help="Ekranda kac satir gosterilsin")
    s = a.parse_args()

    r = is_listesi_uret(s.hedef, s.kota)

    print("=" * 74)
    print("  ETIKETLEME SPRINTI - IS LISTESI")
    print("=" * 74)
    print(f"\n  Mevcut altin kayit : {r['mevcut_altin_kayit']}")
    kota_metni = ("kota YOK" if r["banka_basina_kota"] is None
                  else f"banka basina kota {r['banka_basina_kota']}")
    print(f"  Hedef yeni kayit   : {r['hedef_yeni_kayit']}  ({kota_metni})")
    print(f"  Benzerlik esigi    : %{r['benzerlik_esigi'] * 100:.0f}")
    print(f"  Listelenebilen     : {r['listelenen']}")
    print(f"  Ulasilabilir toplam: {r['ulasilabilir_toplam']}")
    print(f"  Yapisal ozellik kapsami: {r['ozellik_kapsami']['baslangic']} "
          f"-> {r['ozellik_kapsami']['bitis']}")

    print(f"\n  KUME DAGILIMI (ayni kalibin kopyalari tek kumede)")
    print("  Banka                 sayfa  metin   secim  kapsanan  aday  secilen  kalan")
    print("  " + " " * 27 + "kumesi  birimi")
    print("  " + "-" * 76)
    for o in r["banka_ozeti"]:
        secilen = r["banka_basina_secilen"].get(o["banka"], 0)
        kalan = r["kalan_kume"].get(o["banka"], 0)
        print(f"  {o['banka'][:20]:<20}{o['ham_kampanya']:>7}{o['metin_kumesi']:>7}"
              f"{o['kume']:>8}{o['kapsanan_kume']:>10}{o['aday_kume']:>6}"
              f"{secilen:>9}{kalan:>7}")
    print("  " + "-" * 76)
    print(f"  {'TOPLAM':<20}{sum(o['ham_kampanya'] for o in r['banka_ozeti']):>7}"
          f"{sum(o['metin_kumesi'] for o in r['banka_ozeti']):>7}"
          f"{r['toplam_kume']:>8}{r['kapsanan_kume']:>10}{r['aday_kume']:>6}"
          f"{r['listelenen']:>9}{sum(r['kalan_kume'].values()):>7}")

    if r["ulasilabilir_toplam"] < 200:
        eksik = 200 - r["ulasilabilir_toplam"]
        print(f"\n  UYARI: 200 hedefine {eksik} kayit KALIYOR.")
        if r["banka_basina_kota"] is not None:
            print(f"  Kota {r['banka_basina_kota']} kaldirilirsa "
                  f"{sum(r['kalan_kume'].values())} kume daha eklenir.")
        else:
            # KOTA YOKKEN acik kalan tek yol veri toplamaktir - bu,
            # korpusun kendisinin yetmedigi anlamina gelir.
            print("  Kota YOK; havuzdaki her benzersiz kume zaten listede.")
            print("  Aradaki fark ancak YENI VERI TOPLAYARAK kapanir.")
    elif sum(r["kalan_kume"].values()):
        kalan = sum(r["kalan_kume"].values())
        # NEDEN LISTEYE GIREMEDILER: kota mi, hedef mi? Ikisi farkli sey ve
        # farkli cozumleri var. Ilk surum kota YOKKEN bile "kotaya takildi"
        # diyordu - okuyan yanlis dugmeye basardi.
        sebep = ("banka kotasina takildi" if r["banka_basina_kota"] is not None
                 else f"hedef ({r['hedef_yeni_kayit']}) doldugu icin siraya alinmadi")
        print(f"\n  Hedef karsilaniyor. Listeye giremeyen {kalan} benzersiz "
              f"kume {sebep};\n  daha fazla hacim gerekirse --hedef "
              f"yukseltilebilir.")

    kg = r["kontrol_gerek"]
    if kg:
        print(f"\n  KONTROL GEREK ({len(kg)} sayfa) - kategori sayfasi OLABILIR,")
        print("  ama T.O.M. ornegindeki gibi coklu kampanya sayfasi da olabilir")
        print("  (TOM-001/002/003 tek sayfadan cikti). Once bunlara bakin:")
        for x in sorted(kg, key=lambda z: -z["metin_uzunlugu"])[:8]:
            print(f"    [{(x['banka'] or '')[:14]:<14}] {x['slug'][:40]:<40} "
                  f"{x['metin_uzunlugu']:>6} krk")

    ba = r["benzer_atlanan"]
    if ba:
        print(f"\n  BENZER OLDUGU ICIN ATLANDI ({len(ba)} sayfa) - altin sette")
        print("  ayni metni VE ayni yapisal profili tasiyan bir kayit zaten var:")
        for x in sorted(ba, key=lambda z: -z["oran"])[:10]:
            print(f"    {x['slug'][:44]:<44} %{x['oran'] * 100:.0f} <-> {x['ikiz']}")

    supheli = [k for k in r["liste"] if k.get("muhtemel_kopya")]
    if supheli:
        print(f"\n  ADRES BENZERLIGI ISARETI ({len(supheli)} kayit) - ELENMEDI,")
        print("  cunku metin+profil karsilastirmasi bunlari FARKLI buldu")
        print("  (ornegin ayni kampanyanin 300 TL ve 400 TL surumleri).")
        print("  Yine de etiketlemeden once ikizine bakmakta fayda var:")
        for k in supheli[:8]:
            print(f"    {k['sira']:>3}. {k['slug'][:38]:<38} ({k['muhtemel_kopya']})")

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

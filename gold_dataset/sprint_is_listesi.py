"""Etiketleme sprinti is listesi (gorev 21: 200-300 altin kayit).

--------------------------------------------------------------------------
NE YAPAR
--------------------------------------------------------------------------
Henuz etiketlenmemis kampanyalari bulur, BANKA DENGESINI gozeterek
siralar ve etiketleyiciye somut bir liste verir.

--------------------------------------------------------------------------
NEDEN CIKARIM MOTORU KULLANILMIYOR
--------------------------------------------------------------------------
Sira belirlemek icin kampanya turu bilinse ise yarardi - ama o bilgi
yalnizca regex_extractor'dan gelir. Motorun tahmini yanlissa sprint
yanlis yere yonlenir ve bu, olcumu besleyen setin daginimini SESSIZCE
carpitir. Bu yuzden onceliklendirme YALNIZCA scraper ustverisine
(banka, url, erisim_zamani) dayanir - hicbir tahmin kullanilmaz.

Ayni ilkenin etiket tarafi: gold_dataset/etiketleme_yardimcisi.py
"NEDEN CIKARIM MOTORUNUN CIKTISI KULLANILMIYOR" bolumu.

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
        return sade[:80]

    # Hicbir satir uymadiysa slug daha bilgilendiricidir.
    return _slug(kayit.get("url")).replace("-", " ")[:80]


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


def is_listesi_uret(hedef: int, kota: int) -> dict:
    etiketli, etiketli_adlar = _etiketli_kimlikler()
    ham = _ham_kampanyalar()
    etiketli_metinler = _etiketli_metinler(ham)

    banka_ham: dict[str, list[dict]] = defaultdict(list)
    kontrol_gerek: list[dict] = []
    for slug, kayit in ham.items():
        # BOSLUKLU ADRES = BOZUK TARAMA. Olculdu: Emlak Katilim'in
        # ".../kampanya/Paraf ile Hepsiburada'da ... Firsati!" adresi
        # (URL'de kodlanmamis bosluk) kampanya sayfasi yerine BANKANIN
        # ANA SAYFASINI dondurmus - 4.581 karakterin tamami menu, doviz
        # kuru ve baska kampanyalarin tanitim kutusu. Sayfada kampanyanin
        # kendisine dair TEK cumle yok, dolayisiyla etiketlenemez.
        # Korpusta tek ornek; yine de ELENMEZ, kontrole gonderilir -
        # sayfa yeniden taranirsa gecerli hale gelebilir.
        if (" " in slug or KONTROL_GEREK_KALIBI.search(slug)) and slug not in etiketli:
            # ASIL LISTEDEN AYRILIR ama ATILMAZ: kategori sayfasi olabilir
            # de, T.O.M. ornegindeki gibi coklu kampanya sayfasi da
            # olabilir. Insan bakar, karar verir.
            kontrol_gerek.append({
                "slug": slug,
                "banka": kayit.get("banka"),
                "url": kayit.get("url"),
                "metin_uzunlugu": len(kayit.get("normalize_metin") or ""),
            })
            continue
        banka_ham[kayit.get("banka") or "BILINMIYOR"].append({**kayit, "_slug": slug})

    ozet = []
    aday_havuzu: dict[str, list[dict]] = {}
    for banka, kayitlar in banka_ham.items():
        etiketsiz = [k for k in kayitlar if k["_slug"] not in etiketli]
        # Deterministik sira: ayni girdiyle her calistirmada AYNI liste.
        etiketsiz.sort(key=lambda k: k["_slug"])
        aday_havuzu[banka] = etiketsiz
        ozet.append({
            "banka": banka,
            "ham_kampanya": len(kayitlar),
            "etiketli": len(kayitlar) - len(etiketsiz),
            "etiketsiz": len(etiketsiz),
        })
    ozet.sort(key=lambda o: -o["etiketsiz"])

    # KOTALI DONUSUMLU SECIM: her turda her bankadan bir kampanya alinir.
    # Boylece hedef sayiya ulasilirken liste tek bankaya kaymaz; kota
    # dolan banka turdan cikar.
    secilenler: list[dict] = []
    bankalar = sorted(aday_havuzu)
    alinan: dict[str, int] = defaultdict(int)
    tur = 0
    while len(secilenler) < hedef:
        eklendi = False
        for banka in bankalar:
            if len(secilenler) >= hedef:
                break
            havuz = aday_havuzu[banka]
            if tur >= len(havuz) or alinan[banka] >= kota:
                continue
            kayit = havuz[tur]
            baslik = _baslik(kayit)
            secilenler.append({
                "sira": len(secilenler) + 1,
                "banka": banka,
                "baslik": baslik,
                "url": kayit.get("url"),
                "slug": kayit["_slug"],
                "son_tarama": (kayit.get("erisim_zamani") or "")[:10],
                # None ise supheli degil; dolu ise ETIKETLEMEDEN ONCE bakilir.
                "muhtemel_kopya": _kopya_suphesi(
                    kayit["_slug"], baslik, etiketli, etiketli_adlar
                ),
                # None ise benzer ikizi yok; dolu ise (kayit_id, oran).
                "cok_benzer": _cok_benzer_ikiz(
                    turkce_ascii_kucult(kayit.get("normalize_metin") or ""),
                    banka, etiketli_metinler
                ),
            })
            alinan[banka] += 1
            eklendi = True
        if not eklendi:
            break  # havuz tukendi ya da tum kotalar doldu
        tur += 1

    return {
        "hedef_yeni_kayit": hedef,
        "banka_basina_kota": kota,
        "mevcut_altin_kayit": len(etiketli),
        "listelenen": len(secilenler),
        "ulasilabilir_toplam": len(etiketli) + len(secilenler),
        "kontrol_gerek": kontrol_gerek,
        "banka_ozeti": ozet,
        "banka_basina_secilen": dict(sorted(alinan.items())),
        "liste": secilenler,
    }


def main() -> None:
    a = argparse.ArgumentParser(description="Etiketleme sprinti is listesi")
    a.add_argument("--hedef", type=int, default=200, help="Kac YENI kayit etiketlenecek")
    a.add_argument("--kota", type=int, default=30, help="Banka basina azami kampanya")
    a.add_argument("--goster", type=int, default=15, help="Ekranda kac satir gosterilsin")
    s = a.parse_args()

    r = is_listesi_uret(s.hedef, s.kota)

    print("=" * 74)
    print("  ETIKETLEME SPRINTI - IS LISTESI")
    print("=" * 74)
    print(f"\n  Mevcut altin kayit : {r['mevcut_altin_kayit']}")
    print(f"  Hedef yeni kayit   : {r['hedef_yeni_kayit']}  (banka basina kota {r['banka_basina_kota']})")
    print(f"  Listelenebilen     : {r['listelenen']}")
    print(f"  Ulasilabilir toplam: {r['ulasilabilir_toplam']}")

    print("\n  Banka                  ham  etiketli  etiketsiz  secilen")
    print("  " + "-" * 56)
    for o in r["banka_ozeti"]:
        secilen = r["banka_basina_secilen"].get(o["banka"], 0)
        print(f"  {o['banka']:<22}{o['ham_kampanya']:>4}{o['etiketli']:>10}{o['etiketsiz']:>11}{secilen:>9}")

    if r["ulasilabilir_toplam"] < 200:
        print(
            f"\n  UYARI: kota {r['banka_basina_kota']} ile 200'e ULASILAMIYOR."
            f"\n  Kotayi yukseltmek hacmi artirir ama seti iki bankaya kaydirir;"
            f"\n  denge korunacaksa eksik bankalardan YENI VERI toplanmalidir."
        )

    kg = r["kontrol_gerek"]
    if kg:
        print(f"\n  KONTROL GEREK ({len(kg)} sayfa) - kategori sayfasi OLABILIR,")
        print("  ama T.O.M. ornegindeki gibi coklu kampanya sayfasi da olabilir")
        print("  (TOM-001/002/003 tek sayfadan cikti). Once bunlara bakin:")
        for x in sorted(kg, key=lambda z: -z["metin_uzunlugu"])[:8]:
            print(f"    [{(x['banka'] or '')[:14]:<14}] {x['slug'][:40]:<40} {x['metin_uzunlugu']:>6} krk")

    benzer = [k for k in r["liste"] if k.get("cok_benzer")]
    if benzer:
        print(f"\n  COK BENZER ({len(benzer)} kayit) - ayni kalibin baska magazasi.")
        print("  Ikizinin altin kaydiyla karsilastir: CIKARILAN DEGERLER ayniysa")
        print("  kayit olcume bir sey katmaz, atla; farkliysa etiketle:")
        for k in sorted(benzer, key=lambda z: -z["cok_benzer"][1])[:10]:
            kid, oran = k["cok_benzer"]
            print(f"    {k['sira']:>3}. {k['slug'][:40]:<40} %{oran*100:.0f} <-> {kid}")

    supheli = [k for k in r["liste"] if k.get("muhtemel_kopya")]
    if supheli:
        print(f"\n  MUHTEMEL KOPYA ({len(supheli)} kayit) - ayni kampanya farkli")
        print("  adresle listeye girmis OLABILIR. Etiketlemeden once bakin;")
        print("  cift kayit, olcumde o kampanyaya CIFT agirlik verir:")
        for k in supheli[:8]:
            print(f"    {k['sira']:>3}. {k['slug'][:38]:<38} ({k['muhtemel_kopya']})")

    print(f"\n  Ilk {s.goster} kayit:\n")
    for k in r["liste"][:s.goster]:
        print(f"  {k['sira']:>3}. [{k['banka'][:14]:<14}] {k['baslik'][:52]}")

    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=2)
    print(f"\n  Tam liste: {CIKTI.relative_to(KOK)}")


if __name__ == "__main__":
    main()

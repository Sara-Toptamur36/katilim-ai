"""Altin Veri Seti'nde eksik kalan alanlari etiketlemeyi hizlandirir.

SORUN: `taksit_sayisi` ve `erteleme_suresi_ay` sutunlari Altin Veri
Seti'nde HIC yoktu; bu yuzden scraper/scripts/extraction_accuracy.py bu
iki alani ne dolu-alan dogrulugunda ne de yanlis pozitif olcumunde
sayabiliyordu. 58 kaydi elle taramak ise gunler surerdi.

BU BETIK NE YAPAR: her altin kaydin KAYNAK METNINDE ilgili kavramin
gecip gecmedigine bakar ve etiketleyiciye karar icin gereken cumleleri
gosterir. Boylece is ikiye ayrilir:

  1. Kavram metinde HIC gecmiyor  -> hucre BOS kalir (yazilacak sey yok)
  2. Geciyor                      -> aday cumleler gosterilir, deger secilir

Olculdu (9 Agustos 2026): 36 canli kayittan taksit icin yalnizca 8'i,
erteleme icin yalnizca 2'si gercek karar gerektiriyor.

HUCREYE 'yok' YAZILMAZ: Excel'in "1. Nasil Doldurulur" sayfasi (satir 34)
bunu acikca yasaklar - bos hucre zaten "kaynakta belirtilmemis" demektir.
Bos hucrenin OLCUME girmesi icin sutunun etiketlemesinin bittiginin
kaydedilmesi gerekir: excel_to_json.py'de sutun adini INCELENMEMIS_ALANLAR
listesinden INCELENMIS_ALANLAR listesine tasi. Bu betigin sonunda hatirlatilir.

>>> NEDEN CIKARIM MOTORUNUN CIKTISI KULLANILMIYOR (kritik) <<<
Bu betik, extraction/regex_extractor.py'yi CAGIRMAZ ve onun bulduklarini
onermez. Altin Veri Seti motorun OLCULDUGU referanstir; referansi motorun
kendi ciktisiyla doldurmak olcumu dairesel hale getirir ve dogrulugu
tanim geregi %100 gosterirdi. Burada yalnizca HAM METIN kelime bazinda
aranir; kararı her zaman insan verir.

KULLANIM:
    python gold_dataset/etiketleme_yardimcisi.py
    python gold_dataset/etiketleme_yardimcisi.py --alan erteleme_suresi_ay
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.scripts.gold_eslesme import scraper_kaydini_bul  # noqa: E402

GOLD = Path(__file__).resolve().parent / "altin_veri_seti.json"

# Sahte (sartname ornegi) kayitlarin kaynak metni yoktur.
SAHTE_ONEKLER = ("A-", "B-", "C-", "D-")

# Alan -> (kavrami arayan desen, etiketleyiciye hatirlatma)
#
# DESENLER BILEREK GENISTIR: amac karari VERMEK degil, karar icin gereken
# cumleyi ONUNE GETIRMEK. Fazladan aday gostermek, gercek bir degeri
# kacirmaktan iyidir - eleme insanin isidir.
ALANLAR = {
    "taksit_sayisi": (
        re.compile(r"taksit", re.IGNORECASE),
        "Kac TAKSIT? ('12 aya varan taksit' -> 12). Vade DEGIL.",
    ),
    "erteleme_suresi_ay": (
        re.compile(r"ertele|öteleme|oteleme|ödemesiz|odemesiz", re.IGNORECASE),
        "Kac AY ertelemeli/odemesiz donem? ('2 ay ertelemeli' -> 2).",
    ),
    "finansman_tutari": (
        # Tutar ile finansman/kredi kelimesi AYNI cumlede olmali - yoksa
        # her "500 TL" (odul, harcama esigi, ucret) aday olurdu.
        re.compile(
            r"(?:finansman|kredi)\w*[^.\n]{0,60}?\d[\d.,]*\s*(?:TL|₺)"
            r"|\d[\d.,]*\s*(?:TL|₺)[^.\n]{0,60}?(?:finansman|kredi)",
            re.IGNORECASE,
        ),
        "Kullandirilan FINANSMAN tutari (TL). Odul/hediye tutari DEGIL - "
        "NER bu ikisini karistiriyor, bkz. docs/extraction_accuracy_raporu.md.",
    ),
    "odul_birimi": (
        re.compile(
            r"worldpuan|bankkart lira|parafpara|\bmil\b|\bgram\b|puan|nakit iade",
            re.IGNORECASE,
        ),
        "Odulun BIRIMI (TL / Mil / Gram / Worldpuan / ParafPara / Bankkart Lira). "
        "odul_miktari bos ise birim de genelde bostur - ama once metne bak.",
    ),
}

# --------------------------------------------------------------------------
# SPAN KIPI (--span) icin ek desenler
# --------------------------------------------------------------------------
# Yukaridaki ALANLAR "hangi BOS alan doldurulmali?" sorusuna bakar. Span
# kipi ise TERSI soruyu sorar: "bu DOLU degerin kaynaktaki gerekcesi hangi
# cumle?" - o yuzden olculen tum alanlari kapsamasi gerekir.
#
# DAIRESELLIK KURALI BURADA DA GECERLI (bkz. dosya basi): desenler ham
# metinde KAVRAM arar; regex_extractor'in bulduklarini onermez. Aday
# cumleyi gosterir, secimi insan yapar.
SPAN_DESENLERI = {
    **{alan: desen for alan, (desen, _) in ALANLAR.items()},
    "kar_payi_orani": re.compile(r"k[aâ]r\s*pay|k[aâ]r\s*oran|vade\s*farks[ıi]z|%", re.IGNORECASE),
    "vade_ay": re.compile(r"vade|\d{1,3}\s*ay", re.IGNORECASE),
    "odul_miktari": re.compile(r"ödül|odul|hediye|kazan|iade|puan|mil|gram", re.IGNORECASE),
    "masraf_durumu": re.compile(r"masraf|[üu]cret|komisyon|tahsis|dosya", re.IGNORECASE),
    "kampanya_bitis": re.compile(r"tarihleri|ge[çc]erli|son\s*g[üu]n|\d{1,2}[./]\d{1,2}[./]\d{4}", re.IGNORECASE),
    "hedef_kitle": re.compile(r"m[üu]şteri|musteri|emekli|[çc]ift[çc]i|[öo]ğrenci|ogrenci|personel", re.IGNORECASE),
}

# Kanit cumlesi cikarirken kullanilacak pencere
CUMLE_BOLUCU = re.compile(r"(?<=[.!?])\s+|\n")
AZAMI_KANIT = 6


def _kanit_cumleleri(metin: str, desen: re.Pattern) -> list[str]:
    """Kavramin gectigi cumleleri, tekrarsiz ve kisaltilmis olarak doner."""
    bulunan: list[str] = []
    gorulen: set[str] = set()
    for cumle in CUMLE_BOLUCU.split(metin):
        sade = " ".join(cumle.split())
        if not sade or not desen.search(sade):
            continue
        anahtar = sade.lower()
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        bulunan.append(sade if len(sade) <= 160 else sade[:157] + "...")
        if len(bulunan) >= AZAMI_KANIT:
            break
    return bulunan


def _gercek_kayitlar() -> list[dict]:
    with open(GOLD, encoding="utf-8") as f:
        return [k for k in json.load(f) if not k["kayit_id"].startswith(SAHTE_ONEKLER)]


def rapor_uret(alan: str) -> dict:
    desen, hatirlatma = ALANLAR[alan]
    yok, karar_gerek, kaynaksiz = [], [], []

    for kayit in _gercek_kayitlar():
        kid = kayit["kayit_id"]
        if kayit.get(alan) is not None:
            continue  # zaten etiketlenmis
        if kayit["alan_belirtilmemis"].get(alan) is True:
            continue  # zaten "yok" isaretli

        scraper_kaydi = scraper_kaydini_bul(kayit)
        if scraper_kaydi is None:
            kaynaksiz.append(kid)
            continue

        metin = scraper_kaydi.get("ham_metin") or ""
        kanitlar = _kanit_cumleleri(metin, desen)
        if kanitlar:
            karar_gerek.append((kid, kayit.get("kampanya_adi") or "", kanitlar))
        else:
            yok.append(kid)

    return {
        "alan": alan,
        "hatirlatma": hatirlatma,
        "yok": yok,
        "karar_gerek": karar_gerek,
        "kaynaksiz": kaynaksiz,
    }


def rapor_yazdir(rapor: dict) -> None:
    alan = rapor["alan"]
    print(f"\n{'=' * 74}")
    print(f"  {alan}")
    print(f"  {rapor['hatirlatma']}")
    print("=" * 74)

    yok = rapor["yok"]
    print(
        f"\n[1] KAYNAK METINDE HIC GECMIYOR -> hucreyi BOS BIRAK ({len(yok)} kayit)"
        "\n    Yazilacak bir sey yok; hucreler zaten bos. Bunlar, sutunun"
        "\n    etiketlemesi bittiginde 'kaynakta belirtilmemis' sayilacak."
    )
    if yok:
        for i in range(0, len(yok), 8):
            print("    " + "  ".join(yok[i:i + 8]))

    karar = rapor["karar_gerek"]
    print(f"\n[2] GECIYOR -> degeri sen sec ({len(karar)} kayit)")
    for kid, ad, kanitlar in karar:
        print(f"\n  {kid}  {ad[:58]}")
        for c in kanitlar:
            print(f"      | {c}")

    kaynaksiz = rapor["kaynaksiz"]
    print(f"\n[3] KAYNAK METNI YOK - kampanya siteden kaldirilmis ({len(kaynaksiz)} kayit)")
    if kaynaksiz:
        for i in range(0, len(kaynaksiz), 8):
            print("    " + "  ".join(kaynaksiz[i:i + 8]))
        print(
            "    Bunlar zaten Extraction Accuracy olcumunun DISINDA\n"
            "    (scraper_kaydini_bul None donuyor). Ekran goruntusunden\n"
            "    etiketlemek su an olcume hicbir sey katmaz; kampanya geri\n"
            "    gelirse degerlendirilir."
        )


def span_raporu_yazdir(azami_kayit: int | None = None) -> None:
    """DOLU degerler icin kanit cumlesi adaylari gosterir.

    Cikti, `kanit_spanlari` alanina YAPISTIRILACAK bicimde uretilir.
    Secilen cumle kaynak metinde BIREBIR gecmelidir - tests/
    test_altin_veri_butunlugu.py bunu her kosuda dogrular, yani elle
    "ozetlenmis" bir cumle sessizce gecemez.
    """
    kayitlar = _gercek_kayitlar()
    girilmis = sum(1 for k in kayitlar if k.get("kanit_spanlari"))
    print(chr(10) + "=" * 74)
    print("  KANIT SPANI DOLDURMA")
    print(f"  {len(kayitlar)} kayit | spani girilmis: {girilmis}")
    print("  Secilen cumle kaynak metinde BIREBIR gecmeli (test dogrular).")
    print("=" * 74)

    # `azami_kayit` GOSTERILEN kayit sayisini sinirlar, taranani degil:
    # ilk kayitlarin kaynagi siteden kaldirilmis olabilir (kampanya
    # rotasyonu) ve girdiyi bastan kesmek bos bir rapor uretirdi.
    gosterilen = 0

    for kayit in kayitlar:
        if azami_kayit and gosterilen >= azami_kayit:
            break
        if kayit.get("kanit_spanlari"):
            continue  # zaten girilmis

        scraper_kaydi = scraper_kaydini_bul(kayit)
        if scraper_kaydi is None:
            continue  # kampanya siteden kaldirilmis
        metin = scraper_kaydi.get("normalize_metin") or scraper_kaydi.get("ham_metin") or ""

        # Yalnizca DOLU alanlarin kaniti istenir - bos alanin kaniti olmaz
        # (bkz. test_kanit_spani_yalnizca_DOLU_alanlara_verilir).
        dolu = [a for a in SPAN_DESENLERI if kayit.get(a) not in (None, "", [])]
        if not dolu:
            continue

        gosterilen += 1
        print(chr(10) + f"  {kayit['kayit_id']}  {(kayit.get('kampanya_adi') or '')[:56]}")
        for alan in dolu:
            adaylar = _kanit_cumleleri(metin, SPAN_DESENLERI[alan])[:3]
            if not adaylar:
                continue
            print(f"    {alan} = {kayit.get(alan)!r}")
            for c in adaylar:
                print(f"        | {c}")


def main() -> int:
    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument("--alan", choices=sorted(ALANLAR), help="Yalnizca bu alan")
    ayristirici.add_argument(
        "--span", action="store_true",
        help="DOLU degerler icin kanit cumlesi adaylari goster (kanit_spanlari)",
    )
    ayristirici.add_argument("--azami", type=int, help="Span kipinde kac kayit gosterilsin")
    secim = ayristirici.parse_args()

    if secim.span:
        span_raporu_yazdir(secim.azami)
        return 0

    alanlar = [secim.alan] if secim.alan else sorted(ALANLAR)
    for alan in alanlar:
        rapor_yazdir(rapor_uret(alan))

    print(f"\n{'=' * 74}")
    print("  ETIKETLEME BITINCE, SIRASIYLA:")
    print("    1) python gold_dataset/excel_to_json.py")
    print("    2) excel_to_json.py'de sutun adini INCELENMEMIS_ALANLAR'dan")
    print("       INCELENMIS_ALANLAR'a tasi  <-- yanlis pozitif olcumu")
    print("       ANCAK bundan sonra acilir")
    print("    3) python gold_dataset/excel_to_json.py   (kapsami dogrula)")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())

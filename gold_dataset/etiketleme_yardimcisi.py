"""Altin Veri Seti'nde eksik kalan alanlari etiketlemeyi hizlandirir.

SORUN: `taksit_sayisi` ve `erteleme_suresi_ay` sutunlari Altin Veri
Seti'nde HIC yoktu; bu yuzden scraper/scripts/extraction_accuracy.py bu
iki alani ne dolu-alan dogrulugunda ne de yanlis pozitif olcumunde
sayabiliyordu. 58 kaydi elle taramak ise gunler surerdi.

BU BETIK NE YAPAR: her altin kaydin KAYNAK METNINDE ilgili kavramin
gecip gecmedigine bakar ve etiketleyiciye karar icin gereken cumleleri
gosterir. Boylece is ikiye ayrilir:

  1. Kavram metinde HIC gecmiyor  -> "yok" (tek bakista karar, kanit net)
  2. Geciyor                      -> aday cumleler gosterilir, deger secilir

Olculdu (9 Agustos 2026): 36 canli kayittan taksit icin yalnizca 8'i,
erteleme icin yalnizca 2'si gercek karar gerektiriyor. Kalan 60 alan
"yok" olarak isaretlenebilir.

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
ALANLAR = {
    "taksit_sayisi": (
        re.compile(r"taksit", re.IGNORECASE),
        "Kac TAKSIT? ('12 aya varan taksit' -> 12). Vade DEGIL.",
    ),
    "erteleme_suresi_ay": (
        re.compile(r"ertele|öteleme|oteleme|ödemesiz|odemesiz", re.IGNORECASE),
        "Kac AY ertelemeli/odemesiz donem? ('2 ay ertelemeli' -> 2).",
    ),
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
    print(f"\n[1] KAYNAK METINDE HIC GECMIYOR -> Excel'de `yok` yaz ({len(yok)} kayit)")
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
            "    Bu kayitlar zaten Extraction Accuracy olcumunun DISINDA\n"
            "    (scraper_kaydini_bul None donuyor). BOS birakmak dogrudur -\n"
            "    `yok` yazmak, dogrulanamayan bir iddia kaydetmek olurdu."
        )


def main() -> int:
    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument("--alan", choices=sorted(ALANLAR), help="Yalnizca bu alan")
    secim = ayristirici.parse_args()

    alanlar = [secim.alan] if secim.alan else sorted(ALANLAR)
    for alan in alanlar:
        rapor_yazdir(rapor_uret(alan))

    print(f"\n{'=' * 74}")
    print("  Etiketledikten sonra:  python gold_dataset/excel_to_json.py")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())

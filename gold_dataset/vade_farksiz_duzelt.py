"""Altin Veri Seti'ndeki "vade farksiz" kar payi etiketlerini tek kurala baglar.

SORUN (olculdu 23 Agustos 2026): korpusta "vade farksiz" gecen kayitlar
gold'da UC FARKLI sekilde etiketlenmisti - ayni kanit, uc karar:

    kar_payi_orani = 0        31 kayit
    "belirtilmemis" bayrakli  13 kayit
    bos / bayraksiz (taslak)  17 kayit

Bu, iki ayri commit'in ZIT yonde karar vermesinden dogdu:

  * `baa7b07` gold'a "vade farksiz kampanyalara kar payi orani sifir
    yazildi" dedi (bir kismina).
  * `3cb0fb5` motordan RE_VADE_FARKSIZ kuralini KALDIRDI; gerekcesi
    (extraction/regex_extractor.py, desen tanimlari bolumu): "vade
    farksiz 6 taksit" bir KART TAKSIT ifadesidir, finansman kar payi
    orani DEGILDIR.

Ikisi ayri ayri savunulabilir ama BIRLIKTE tutarsiz. Olculen sonuc:
gold 0 diyor, motor None donuyor -> 33 kacirma, kar_payi_orani recall
%90,91'den %15,38'e dustu. Kimse kombinasyonu yeniden olcmemis.

SECILEN KURAL - motorun (dogru) domain gerekcesi esas alinir:
"vade farksiz" TEK BASINA kar payi orani kaniti DEGILDIR.

  * Gercekten sifir kar payli kampanyalar bunu ACIKCA yaziyor
    ("kar paysiz", "0 kar payli") ve motorda o kurallar KORUNUYOR
    (RE_KAR_PAYSIZ / RE_KAR_PAYI_SIFIR). Yani gercek sifirlar
    kaybolmuyor - yalnizca zayif kanit reddediliyor.
  * Etkilenen kayitlarin buyuk cogunlugu (24/30) zaten Kart
    Kampanyasi turunde; bir kart taksit ozelligini finansman orani
    saymak, karsilastirmada da zarar veriyordu: uydurma 0,
    `en_dusuk_kar_payi` siralamasini (ASC) her zaman kazaniyor ve
    gercek konut finansmaninin %1,87'sini yeniyordu.

BU BETIK NE YAPAR: kanit olarak YALNIZCA "vade farksiz" tasiyan
kayitlarin `kar_payi_orani` hucresini Excel'de BOSALTIR. Excel'de bos
hucre, incelenmis bir sutunda "kaynakta belirtilmemis" demektir
(bkz. excel_to_json.py) - yani bu kayitlar zaten oyle etiketlenmis
13 kayitla AYNI duruma gelir.

DOKUNMADIGI KAYITLAR: metninde "kar paysiz" veya "0 kar payli" gecenler
(motor da bunlari 0 buluyor, dogru etiket) ve sayisal bir oran yazilmis
olanlar.

Kullanim:
    python -m gold_dataset.vade_farksiz_duzelt          # yalnizca rapor
    python -m gold_dataset.vade_farksiz_duzelt --yaz    # Excel'e uygula
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
GOLD = KOK / "gold_dataset" / "altin_veri_seti.json"
EXCEL = KOK / "gold_dataset" / "altin_veri_seti.xlsx"
SAYFA = "2. Altin Veri Seti"

RE_VADE_FARKSIZ = re.compile(r"vade\s*farks[ıi]z", re.IGNORECASE)
# Motorda KORUNAN kurallarin aynisi - burada da ayni ifadeleri "gercek
# sifir kaniti" sayariz ki iki taraf ayni seyi soylesin.
RE_ACIK_SIFIR = re.compile(r"k[aâ]r\s*pays[ıi]z|\b0\s*k[aâ]r\s*pay", re.IGNORECASE)


def etkilenen_kayitlar() -> tuple[list[dict], list[dict]]:
    """(bosaltilacaklar, dokunulmayanlar) - ikisi de gerekceleriyle."""
    from scraper.scripts.gold_eslesme import scraper_kaydini_bul

    gold = json.loads(GOLD.read_text(encoding="utf-8"))
    bosalt: list[dict] = []
    koru: list[dict] = []

    for kayit in gold:
        if kayit.get("kar_payi_orani") != 0:
            continue  # yalnizca sifir yazilmis hucreler ilgilendiriyor
        ham = scraper_kaydini_bul(kayit)
        if ham is None:
            continue  # kampanya rotasyona girmis, kaynak metin yok
        metin = ham.get("ham_metin") or ""

        if RE_ACIK_SIFIR.search(metin):
            koru.append({
                "kayit_id": kayit["kayit_id"],
                "sebep": "metinde acikca 'kar paysiz' / '0 kar payli' geciyor",
            })
        elif RE_VADE_FARKSIZ.search(metin):
            bosalt.append({
                "kayit_id": kayit["kayit_id"],
                "kampanya_turu": kayit.get("kampanya_turu"),
                "sebep": "tek kanit 'vade farksiz' - kart taksit ifadesi",
            })
        else:
            koru.append({
                "kayit_id": kayit["kayit_id"],
                "sebep": "sifirin kaynagi belirlenemedi - elle incelenmeli",
            })

    return bosalt, koru


def excele_yaz(bosalt: list[dict]) -> int:
    """Etkilenen satirlarin kar_payi_orani hucresini bosaltir."""
    import openpyxl

    wb = openpyxl.load_workbook(EXCEL)
    sh = wb[SAYFA]
    basliklar = [c.value for c in sh[1]]
    sutun = {b: i + 1 for i, b in enumerate(basliklar)}
    satir = {
        sh.cell(r, 1).value: r
        for r in range(2, sh.max_row + 1)
        if sh.cell(r, 1).value
    }

    hedefler = {b["kayit_id"] for b in bosalt}
    yazilan = 0
    for kid in hedefler:
        r = satir.get(kid)
        if r is None:
            continue
        # Guvenlik agi (aday_deger_yaz.py ile ayni desen): bu betik imza
        # sutununa ASLA dokunmamali.
        imza_oncesi = sh.cell(r, sutun["giren_kisi"]).value

        sh.cell(r, sutun["kar_payi_orani"]).value = None
        # Oran periyodu yalnizca oranin kendisi icin anlamli - oran
        # kalkinca yalniz basina kalmamali.
        if "oran_periyodu" in sutun:
            sh.cell(r, sutun["oran_periyodu"]).value = None

        # Kanit spani da temizlenir; kalirsa "degeri yok ama kaniti var"
        # gibi celiskili bir satir uretir ve butunluk testi haklı olarak
        # sikayet eder.
        if "kanit_spanlari" in sutun:
            hucre = sh.cell(r, sutun["kanit_spanlari"])
            satirlar = [
                s
                for s in (hucre.value or "").split("\n")
                if s.strip() and not s.startswith("kar_payi_orani:")
            ]
            hucre.value = "\n".join(satirlar) if satirlar else None

        assert sh.cell(r, sutun["giren_kisi"]).value == imza_oncesi, \
            f"{kid}: imza sutunu degismis"
        yazilan += 1

    wb.save(EXCEL)
    return yazilan


def main() -> None:
    a = argparse.ArgumentParser(
        description="'vade farksiz' kar payi etiketlerini tek kurala baglar"
    )
    a.add_argument("--yaz", action="store_true", help="Excel'e uygula")
    args = a.parse_args()

    bosalt, koru = etkilenen_kayitlar()

    print(f"Bosaltilacak  : {len(bosalt)} kayit")
    turler: dict[str, int] = {}
    for b in bosalt:
        turler[b["kampanya_turu"] or "?"] = turler.get(b["kampanya_turu"] or "?", 0) + 1
    for t, c in sorted(turler.items(), key=lambda x: -x[1]):
        print(f"    {t:35} {c}")
    print("    " + ", ".join(sorted(b["kayit_id"] for b in bosalt)))
    print()
    print(f"Dokunulmayan  : {len(koru)} kayit")
    for k in koru:
        print(f"    {k['kayit_id']:10} {k['sebep']}")

    if not args.yaz:
        print()
        print("Rapor modu - Excel'e yazmak icin --yaz ekleyin.")
        return

    yazilan = excele_yaz(bosalt)
    print()
    print(f"Excel guncellendi: {yazilan} satir")
    print("Simdi JSON'u yeniden uretin:")
    print("    python gold_dataset/excel_to_json.py")


if __name__ == "__main__":
    main()

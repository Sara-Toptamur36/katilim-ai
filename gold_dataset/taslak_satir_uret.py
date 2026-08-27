"""Etiketleme kuyrugundan Excel'e TASLAK satir iskeleti acar.

--------------------------------------------------------------------------
NE YAPAR, NE YAPMAZ
--------------------------------------------------------------------------
YAPAR: sprint_is_listesi'ndeki adaylar icin satirin KIMLIK alanlarini
doldurur - kayit_id, banka, kampanya_adi, kaynak_url. Bunlar korpusta
zaten yazili degerlerdir; buraya kopyalanmalari bir cikarim degil,
aktarimdir.

YAPMAZ: OLCULEN hicbir alani doldurmaz - kar_payi_orani, vade_ay,
finansman_tutari, odul_miktari, masraf_durumu, hedef_kitle,
taksit_sayisi, erteleme_suresi_ay, kampanya tarihleri bos kalir.
`giren_kisi` de bos kalir.

--------------------------------------------------------------------------
NEDEN OLCULEN ALANLARI DOLDURMUYOR
--------------------------------------------------------------------------
Altin veri seti, cikarim motorunun kendisine karsi olculdugu referanstir.
Referansi otomatik bir cikarimla doldurmak, sinavi kopya kagidiyla
degerlendirmektir - sonuc her zaman yuksek cikar ve hicbir sey ifade
etmez (Calisma Rehberi, Kural 5). Bu betigin isi, insanin sayfaya
bakmadan once yaptigi mekanik islerden kurtarmaktir: dogru kayit_id'yi
bulmak, URL'yi kopyalamak, bankayi yazmak.

`giren_kisi` bos birakilir ve bu ONEMLIDIR: imzasiz satir olcumun
disindadir (bkz. excel_to_json, "IMZASIZ KAYIT HICBIR IDDIA TASIMAZ").
Satir ancak insan sayfaya bakip imzaladiginda olcume girer.

--------------------------------------------------------------------------
KULLANIM
--------------------------------------------------------------------------
    python gold_dataset/taslak_satir_uret.py --sayi 20            # onizleme
    python gold_dataset/taslak_satir_uret.py --sayi 20 --yaz      # Excel'e ac
    python gold_dataset/taslak_satir_uret.py --banka "Kuveyt Türk" --sayi 10

Acilan satirlari doldurmak icin: her satirin kaynak_url'sini acin,
degerleri okuyun, girin ve EN SON giren_kisi'yi imzalayin.
Okumayi kolaylastirmak icin: python gold_dataset/ham_metin_goster.py KT-018
"""

from __future__ import annotations

import ortam_yukle  # noqa: F401 - side effect: .env process ortamina yuklenir

import argparse
import json
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

GOLD = KOK / "gold_dataset" / "altin_veri_seti.json"
EXCEL = KOK / "gold_dataset" / "altin_veri_seti.xlsx"
IS_LISTESI = KOK / "gold_dataset" / "sprint_is_listesi.json"

# Bu betigin ASLA yazmadigi alanlar - olculen alanlar ve imza.
YAZILMAYAN_ALANLAR = frozenset({
    "kar_payi_orani", "maliyet_orani", "oran_periyodu", "vade_ay",
    "finansman_tutari", "odul_miktari", "odul_birimi", "kampanya_avantaji",
    "masraf_durumu", "kampanya_baslangic", "kampanya_bitis", "hedef_kitle",
    "taksit_sayisi", "erteleme_suresi_ay", "kanit_spanlari",
    "giren_kisi", "giris_tarihi", "ekran_goruntusu",
})

BANKA_ONEKLERI = {
    "Albaraka Türk": "AL",
    "Dünya Katılım": "DK",
    "Hayat Finans": "HF",
    "Kuveyt Türk": "KT",
    "T.O.M. Katılım": "TOM",
    "Türkiye Emlak Katılım": "TEK",
    "Türkiye Finans": "TF",
    "Vakıf Katılım": "VK",
    "Ziraat Katılım": "ZK",
}


def _sonraki_idler(kayitlar: list[dict]) -> dict[str, int]:
    """Banka -> kullanilabilir sonraki numara.

    Kural 6: kayit_id uydurulmaz, o bankanin en buyuk numarasi bir
    artirilir. Bosluk varsa doldurulmaz - eski bir ID'yi yeniden
    kullanmak, silinmis bir kaydin gecmisiyle karismaya yol acar."""
    en_buyuk: dict[str, int] = {}
    for k in kayitlar:
        m = re.fullmatch(r"([A-Z]+)-(\d+)", k.get("kayit_id") or "")
        if m:
            onek, no = m.group(1), int(m.group(2))
            en_buyuk[onek] = max(en_buyuk.get(onek, 0), no)
    return en_buyuk


def taslaklari_planla(sayi: int, banka_suzgeci: str | None = None) -> list[dict]:
    from gold_dataset.sprint_is_listesi import _ham_kampanyalar, _slug

    with open(GOLD, encoding="utf-8") as f:
        mevcut = json.load(f)
    with open(IS_LISTESI, encoding="utf-8") as f:
        is_listesi = json.load(f)

    mevcut_urller = {(k.get("kaynak_url") or "").rstrip("/") for k in mevcut}
    sonraki = _sonraki_idler(mevcut)
    ham = _ham_kampanyalar()

    plan: list[dict] = []
    for aday in is_listesi["liste"]:
        if len(plan) >= sayi:
            break
        banka = aday["banka"]
        if banka_suzgeci and banka != banka_suzgeci:
            continue
        url = (aday.get("url") or "").rstrip("/")
        if url in mevcut_urller:
            continue  # zaten altin sette

        onek = BANKA_ONEKLERI.get(banka)
        if not onek:
            continue
        sonraki[onek] = sonraki.get(onek, 0) + 1

        kaynak = ham.get(_slug(url)) or {}
        # Kampanya adi korpusta yazili baslikitir - cikarilmis bir deger
        # degil, sayfanin kendi basligi.
        baslik = (kaynak.get("baslik") or aday.get("baslik") or "").strip()

        plan.append({
            "kayit_id": f"{onek}-{sonraki[onek]:03d}",
            "banka": banka,
            "kampanya_adi": baslik,
            "kaynak_url": aday["url"],
            "_gerekce": aday.get("secim_gerekcesi", ""),
            "_metin_var": bool(kaynak.get("normalize_metin")),
        })
    return plan


def excele_ac(plan: list[dict]) -> int:
    import openpyxl

    wb = openpyxl.load_workbook(EXCEL)
    sh = wb["2. Altin Veri Seti"]
    basliklar = [c.value for c in sh[1]]
    sutun = {b: i + 1 for i, b in enumerate(basliklar)}

    # Guvenlik agi: yazmamamiz gereken bir sutuna yanlislikla deger
    # gitmesin diye yalnizca izin verilen sutunlar kullanilir.
    yazilabilir = {"kayit_id", "banka", "kampanya_adi", "kaynak_url",
                   "kampanya_turu", "notlar"}
    assert not (yazilabilir & YAZILMAYAN_ALANLAR)

    ilk_bos = sh.max_row + 1
    for sira, satir in enumerate(plan):
        r = ilk_bos + sira
        for alan in ("kayit_id", "banka", "kampanya_adi", "kaynak_url"):
            sh.cell(r, sutun[alan]).value = satir[alan]
        sh.cell(r, sutun["notlar"]).value = (
            "TASLAK - alanlar doldurulmadi, sayfaya bakilmadi. "
            "Degerleri girip giren_kisi'yi imzalayin."
        )
    wb.save(EXCEL)
    return len(plan)


def main() -> None:
    a = argparse.ArgumentParser(description="Kuyruktan taslak satir iskeleti acar")
    a.add_argument("--sayi", type=int, default=20, help="Kac satir acilacak")
    a.add_argument("--banka", help="Yalnizca bu banka")
    a.add_argument("--yaz", action="store_true", help="Excel'e yaz")
    s = a.parse_args()

    plan = taslaklari_planla(s.sayi, s.banka)
    if not plan:
        print("Acilacak yeni satir bulunamadi.")
        return

    print(f"{'KAYIT':<9} {'BANKA':<24} {'METIN':<6} BASLIK")
    print("-" * 96)
    for p in plan:
        metin = "var" if p["_metin_var"] else "YOK"
        print(f"{p['kayit_id']:<9} {p['banka']:<24} {metin:<6} {p['kampanya_adi'][:52]}")

    metinsiz = [p["kayit_id"] for p in plan if not p["_metin_var"]]
    print(f"\nToplam {len(plan)} satir.")
    if metinsiz:
        print(f"Ham metni olmayan {len(metinsiz)}: {metinsiz}")
        print("  (bunlarda sayfayi tarayicida acmak gerekir)")

    print("\nOLCULEN ALANLAR BOS ACILIR - deger ve imza insana aittir.")
    if s.yaz:
        n = excele_ac(plan)
        print(f"\n{n} taslak satir Excel'e eklendi: {EXCEL}")
        print("Simdi: python gold_dataset/excel_to_json.py")
    else:
        print("\n(Excel'e acmak icin --yaz)")


if __name__ == "__main__":
    main()

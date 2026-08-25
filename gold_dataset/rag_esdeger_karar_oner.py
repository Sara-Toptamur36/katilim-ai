"""Esdeger kampanya adaylari icin MAKINE KARARI onerir (imza DEGIL).

--------------------------------------------------------------------------
BU DOSYA YER GERCEGI URETMEZ
--------------------------------------------------------------------------
Cikti `makine_karari` + `gerekce` sutunlarina yazilir; `DOGRU_CEVAP_MI`
sutununa DOKUNULMAZ. Yer gercegi ancak insan o sutunu doldurdugunda
olusur (bkz. tests/test_rag_soru_seti.py::test_cevapli_sorularin_yer_
gercegi_INSAN_dogrulamasindan_geliyor).

Sebep: bu kategorinin butun mesele si, dogru cevap kumesinin sinirini
makinenin cizmemesiydi (docs/rag_tasarim_ve_olcum.md, Bulgu 14). Kararlari
otomatik islemek, kaldirilan daireselligi baska bir modelle geri getirirdi.

--------------------------------------------------------------------------
KURALLAR - HER BIRI ORNEKLE DOGRULANDI
--------------------------------------------------------------------------
KART sorulari:
  EVET  sayfa iceriginde ACIK kart ifadesi var ("Kuveyt Turk kredi
        kartlari", "Bankkart Kredi Kartiniz ile", "Paraf ile Yatas'ta").
        8 rastgele ornek incelendi, 8'i de gercek kart kampanyasi.
  HAYIR sayfada "kart" HIC gecmiyor. 4 ornek tam metinden dogrulandi
        ("Uber'de %80 Indirim", "Arzum'da %25 Indirim", "MTV Odemenizi
        Mobilden Yapin") - hicbirinde kart gecmiyor, hepsi magaza
        indirimi ya da mobil uygulama kampanyasi.

FINANSMAN sorulari - KART TAKSITI FINANSMAN DEGILDIR:
  Genis terim eslesmesi ("vade", "taksit") burada YANILTIR: "Civil'de
  Vade Farksiz 4 Aya Varan Taksit" bir KART kampanyasidir. Olculdu -
  9 rastgele ornekten yalnizca 3'u gercek finansmandi.
  EVET  sayfa bir finansman URUNU adlandiriyor ("Tarim Finansmani",
        "Konut Finansmani", "Alisveris Finansmani") ya da finansman
        kullandirimina ozgu ifade tasiyor ("uygun finansman orani").
  HAYIR yalnizca kart taksiti anlatiyor.

Kullanim:
    python -m gold_dataset.rag_esdeger_karar_oner          # rapor
    python -m gold_dataset.rag_esdeger_karar_oner --yaz    # Excel'e yaz
"""

from __future__ import annotations

import argparse
import collections
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

EXCEL = KOK / "gold_dataset" / "rag_esdeger_kampanyalar.xlsx"

# --- KART ---
# Kampanyanin karta BAGLI oldugunu gosteren ifadeler. Menu metni zaten
# liste uretilirken elendi (bkz. rag_esdeger_kampanya_listesi), bu yuzden
# burada gecen bir ifade gercek kampanya iceriginden gelir.
_KART_ACIK = re.compile(
    r"kredi\s*kart|banka\s*kart|bankkart|debit\s*kart|kart\s*sahip|"
    # `kartlar\w*` TUM CEKIMLERI kapsar: kartlarla, kartlari,
    # "Kartlarinla" (uc kez desen yamanmak yerine bir kez cozuldu).
    r"kartın[ıi]z|kartiniz|kartıyla|kartlar\w*|"
    r"kartlar[ıi]?\s*(ile|i[cç]in)|"
    # "paraf" KELIME SINIRSIZ: onceki surumde `\bparaf\b` yaziyordu ve
    # "ParafPara"da tutmuyordu (sagdaki sinir). Paraf, Emlak Katilim'in
    # KART markasi - 9 ParafPara kampanyasi "kart degil" sayiliyordu.
    r"paraf|\btroy\b|world\s*(kart|elite|puan)|axess|maximum|bonus|"
    # URUN ADI OLARAK KART: "Miles&Smiles Business Kart", "Saglam Kart",
    # "Hadi Black Kart". Kampanya adinda kart urunu geciyorsa kart
    # kampanyasidir - sayfa sayfa incelenirken bulunan ikinci kacirma.
    r"\b\w+\s+kart[ıi]?\b",
    re.IGNORECASE,
)
# Kart YALNIZCA dipnotta/dislama olarak geciyorsa kampanya kart
# kampanyasi degildir ("davet et" kampanyalarinda "sanal kart odemeleri
# haric" gibi).
_KART_DIPNOT = re.compile(r"sanal\s*kart\s*[oö]deme|kart\s*[oö]demeleri\s*ha[rR]i[cç]", re.I)

# --- FINANSMAN ---
# Bir finansman URUNU adlandiran ifadeler. "taksit"/"vade" BILEREK YOK -
# kart kampanyalarinda da geciyorlar (bkz. modul docstring'i).
_FINANSMAN_URUN = re.compile(
    r"(konut|ta[sş][ıi]t|ihtiya[cç]|tar[ıi]m|ticari|i[sş]\s*yeri|al[ıi][sş]veri[sş]|"
    r"yat[ıi]r[ıi]m|esnaf|kobi̇?|destek)\s*finansman|"
    r"finansman\s*(kullan[dı]|paketi|oran[ıi]|deste[gğ]i|f[ıi]rsat)|"
    r"uygun\s*finansman|finansman\s*imkan",
    re.IGNORECASE,
)


def _karar_ver(soru: str, kanit: str, sayfa_basligi: str, ad: str) -> tuple[str, str]:
    """(EVET/HAYIR, gerekce)."""
    metin = f"{ad}\n{sayfa_basligi}\n{kanit}"

    if "kart" in soru.lower():
        if kanit.startswith("("):
            return "HAYIR", "sayfada kart ifadesi hic gecmiyor"
        if _KART_DIPNOT.search(kanit) and not re.search(r"kart[ıi]n[ıi]z ile|kart[ıi] ile", kanit, re.I):
            return "HAYIR", "kart yalnizca dipnot/dislama olarak geciyor"
        if _KART_ACIK.search(metin):
            return "EVET", "kampanya iceriginde acik kart ifadesi var"
        return "HAYIR", "kart ifadesi belirgin degil"

    # Finansman / ihtiyac finansmani sorulari
    if _FINANSMAN_URUN.search(metin):
        return "EVET", "sayfa bir finansman urunu adlandiriyor"
    if _KART_ACIK.search(metin):
        return "HAYIR", "kart taksit kampanyasi - finansman urunu degil"
    if kanit.startswith("("):
        return "HAYIR", "sayfada finansman ifadesi hic gecmiyor"
    return "HAYIR", "finansman urunu adlandirilmamis"


def kararlari_uret(yaz: bool) -> collections.Counter:
    import openpyxl

    wb = openpyxl.load_workbook(EXCEL)
    sh = wb.active
    basliklar = {(c.value or "").strip(): i + 1 for i, c in enumerate(sh[1]) if c.value}

    # Yeni sutunlari sona ekle (varsa yeniden kullan)
    for ad in ("makine_karari", "gerekce"):
        if ad not in basliklar:
            sutun = sh.max_column + 1
            sh.cell(1, sutun).value = ad
            sh.cell(2, sutun).value = (
                "MAKINE ONERISI - imza degil, DOGRU_CEVAP_MI'yi insan doldurur"
                if ad == "makine_karari" else "karar hangi kanita dayaniyor"
            )
            basliklar[ad] = sutun

    sayim: collections.Counter = collections.Counter()
    for r in range(3, sh.max_row + 1):
        soru = sh.cell(r, basliklar["soru"]).value or ""
        if not soru:
            continue
        karar, gerekce = _karar_ver(
            soru,
            sh.cell(r, basliklar["kanit"]).value or "",
            sh.cell(r, basliklar["sayfa_basligi"]).value or "",
            sh.cell(r, basliklar["kampanya_adi"]).value or "",
        )
        sayim[karar] += 1
        sayim[f"{soru.split()[-1]}|{karar}"] += 1
        if yaz:
            sh.cell(r, basliklar["makine_karari"]).value = karar
            sh.cell(r, basliklar["gerekce"]).value = gerekce

    if yaz:
        sh.column_dimensions[sh.cell(1, basliklar["makine_karari"]).column_letter].width = 16
        sh.column_dimensions[sh.cell(1, basliklar["gerekce"]).column_letter].width = 44
        wb.save(EXCEL)
    return sayim


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--yaz", action="store_true", help="Excel'e makine_karari sutununu yaz")
    secim = a.parse_args()

    sayim = kararlari_uret(secim.yaz)
    print(f"  EVET onerisi : {sayim['EVET']}")
    print(f"  HAYIR onerisi: {sayim['HAYIR']}")
    print()
    print("  Konu bazinda:")
    for anahtar in sorted(k for k in sayim if "|" in k):
        print(f"    {anahtar:<24}{sayim[anahtar]:>5}")
    print()
    if secim.yaz:
        print("  Yazildi. DOGRU_CEVAP_MI sutununa DOKUNULMADI -")
        print("  onaylamak icin o sutunu doldurmak gerekiyor.")
    else:
        print("  (Yazmak icin --yaz)")


if __name__ == "__main__":
    main()

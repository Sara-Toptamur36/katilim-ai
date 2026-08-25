"""banka_ve_konu sorulari icin ESDEGER KAMPANYA isaretleme listesi uretir.

--------------------------------------------------------------------------
NEDEN GEREKLI (docs/rag_tasarim_ve_olcum.md, Bulgu 14)
--------------------------------------------------------------------------
`banka_ve_konu` sorulari "banka + tur" formatindadir ("Ziraat Katilim
kart") ve kampanya adi tasimaz. O bankanin o turdeki HER kampanyasi
meshru cevaptir, ama `beklenen_sluglar` yalnizca ALTIN SETTE etiketlenmis
olanlari icerir. Olculdu: 28 sorunun gold'da 55 dogru cevabi var,
korpusta esdegeri 344 - kapsama %16. Sonuc olarak bu kategorinin recall'u
retrieval kalitesini degil GOLD KAPSAMASINI olcuyor.

--------------------------------------------------------------------------
NEDEN OTOMATIK GENISLETILEMEZ
--------------------------------------------------------------------------
Korpustaki `kampanya_turu` MAKINE tarafindan uretilir (olculen F1 ~%78).
Onu dogrudan dogru-cevap listesine koymak, RAG olcumunu cikarim motorunun
kendi ciktisina bagimli kilar - altin veri setinin 5. kuralinin (yer
gercegi otomatik cikarimla doldurulmaz) yasakladigi dairesellik.

Bu yuzden makine yalnizca ADAY onerir; karari insan verir.

--------------------------------------------------------------------------
BU BETIK NE URETIR
--------------------------------------------------------------------------
Her aday kampanya icin, kararin 293 URL acmadan verilebilmesi gereken
bilgiyi toplar:

    soru              hangi soru icin aday
    kampanya_adi      kaynak sayfadaki ad
    makine_turu       motorun atadigi tur (ONERI - dogrulanacak olan bu)
    kanit             motorun o turu neden atadigini gosteren cumle
    gold_da_var_mi    zaten dogru cevap listesinde mi
    retrieval_top5    sistem bu kaydi su an donduruyor mu (oncelik sinyali)
    kaynak_url        supheye dusuldugunde acilacak adres
    DOGRU_CEVAP_MI    <- ELLE DOLDURULACAK TEK SUTUN (EVET / HAYIR)

Kullanim:
    python -m gold_dataset.rag_esdeger_kampanya_listesi
    python -m gold_dataset.rag_esdeger_kampanya_listesi --retrieval  # top5 sutunu da doldur (yavas)
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

CIKTI = KOK / "gold_dataset" / "rag_esdeger_kampanyalar.xlsx"

# Motorun "Kart Kampanyasi" vb. atarken baktigi anahtar kelimeler -
# kanit cumlesini bulmak icin AYNI listeden okunur, kopyalanmaz.
from extraction.regex_extractor import (  # noqa: E402
    KAMPANYA_TURU_ANAHTAR_KELIMELERI,
    turkce_ascii_kucult,
)
from scraper.scripts.rag_degerlendirme import (  # noqa: E402
    _BELIRSIZLIK_ESIGI,
    _TUR_ESLEME,
    _indekste_olan_sluglar,
)


def _ham_metinler() -> dict[str, str]:
    esleme: dict[str, str] = {}
    for dosya in (KOK / "scraper" / "raw_data").glob("*/json/*.json"):
        try:
            kayit = json.loads(dosya.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        url = kayit.get("url")
        metin = kayit.get("ham_metin") or kayit.get("normalize_metin")
        if url and metin:
            esleme[url] = metin
    return esleme


def _kanit_cumlesi(metin: str, tur: str) -> str:
    """Motorun bu turu NEDEN atadigini gosteren cumle.

    Insanin kararini hizlandirir: "kartla" kelimesi gercekten kart
    kampanyasindan mi geliyor yoksa gecerken mi gecmis, tek bakista
    gorunur.
    """
    kucuk = turkce_ascii_kucult(metin)
    for anahtar in KAMPANYA_TURU_ANAHTAR_KELIMELERI.get(tur, []):
        yer = kucuk.find(turkce_ascii_kucult(anahtar))
        if yer < 0:
            continue
        pencere = metin[max(0, yer - 70) : yer + 90]
        return " ".join(pencere.split())
    return ""


def adaylari_topla(retrieval: bool = False) -> list[dict]:
    from api.db import OturumYerel
    from api.models import Kampanya

    oturum = OturumYerel()
    try:
        kampanyalar = oturum.query(Kampanya).all()
    finally:
        oturum.close()

    sayim = collections.Counter(
        (k.banka, k.kampanya_turu) for k in kampanyalar if k.kampanya_turu
    )
    bankalar = {b for b, _ in sayim}
    mevcut = _indekste_olan_sluglar()
    metinler = _ham_metinler()

    sorular = json.loads(
        (KOK / "gold_dataset" / "rag_soru_seti.json").read_text(encoding="utf-8")
    )

    satirlar: list[dict] = []
    for soru_kaydi in sorular:
        if soru_kaydi.get("kategori") != "banka_ve_konu":
            continue
        beklenen = [s for s in soru_kaydi["beklenen_sluglar"] if s in mevcut]
        if not beklenen:
            continue

        soru = soru_kaydi["soru"]
        banka = next((b for b in bankalar if soru.startswith(b)), None)
        tur = next(
            (
                v
                for anahtar, v in sorted(_TUR_ESLEME.items(), key=lambda x: -len(x[0]))
                if soru.lower().endswith(anahtar)
            ),
            None,
        )
        if not (banka and tur) or sayim.get((banka, tur), 0) <= _BELIRSIZLIK_ESIGI:
            continue  # zaten olculebilir - elle is gerektirmiyor

        top5: set[str] = set()
        if retrieval:
            from chunking.retriever import getir

            sonuc = getir(soru, limit=5, exact=True)
            top5 = {
                (p.get("ustveri") or {}).get("kaynak_url", "").rstrip("/").split("/")[-1]
                for p in sonuc.parcalar
            }

        for k in kampanyalar:
            if k.banka != banka or k.kampanya_turu != tur:
                continue
            slug = (k.kaynak_url or "").rstrip("/").split("/")[-1]
            satirlar.append(
                {
                    "soru": soru,
                    "kampanya_adi": k.kampanya_adi,
                    "makine_turu": k.kampanya_turu,
                    "kanit": _kanit_cumlesi(metinler.get(k.kaynak_url, ""), tur),
                    "gold_da_var_mi": "EVET" if slug in beklenen else "",
                    "retrieval_top5": "EVET" if slug in top5 else "",
                    "kaynak_url": k.kaynak_url,
                    "slug": slug,
                    "DOGRU_CEVAP_MI": "EVET" if slug in beklenen else "",
                }
            )
    return satirlar


def excele_yaz(satirlar: list[dict]) -> None:
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = openpyxl.Workbook()
    sh = wb.active
    sh.title = "Esdeger Kampanyalar"

    basliklar = [
        "soru", "kampanya_adi", "makine_turu", "kanit",
        "gold_da_var_mi", "retrieval_top5", "kaynak_url", "slug",
        "DOGRU_CEVAP_MI",
    ]
    sh.append(basliklar)
    sh.append([
        "hangi soru icin aday",
        "kaynak sayfadaki ad",
        "motorun ONERISI - dogrulanacak olan bu",
        "motor bu turu neden atadi",
        "zaten dogru cevap listesinde",
        "sistem su an donduruyor mu",
        "supheye dusunce ac",
        "(otomatik)",
        "<< ELLE DOLDUR: EVET / HAYIR >>",
    ])

    kalin = Font(bold=True)
    sari = PatternFill("solid", fgColor="FFF2CC")
    for hucre in sh[1]:
        hucre.font = kalin
    for hucre in sh[2]:
        hucre.font = Font(italic=True, size=9)
    for satir in (1, 2):
        sh.cell(satir, len(basliklar)).fill = sari

    for s in satirlar:
        sh.append([s[b] for b in basliklar])

    genislik = {"soru": 30, "kampanya_adi": 44, "makine_turu": 22, "kanit": 70,
                "gold_da_var_mi": 14, "retrieval_top5": 14, "kaynak_url": 46,
                "slug": 34, "DOGRU_CEVAP_MI": 20}
    for i, b in enumerate(basliklar, start=1):
        sh.column_dimensions[sh.cell(1, i).column_letter].width = genislik[b]
    for satir in sh.iter_rows(min_row=3):
        satir[3].alignment = Alignment(wrap_text=True, vertical="top")

    sh.freeze_panes = "A3"
    wb.save(CIKTI)


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument(
        "--retrieval",
        action="store_true",
        help="retrieval_top5 sutununu da doldur (gomme modeli yuklenir, yavas)",
    )
    secim = a.parse_args()

    satirlar = adaylari_topla(retrieval=secim.retrieval)
    excele_yaz(satirlar)

    sorulara_gore = collections.Counter(s["soru"] for s in satirlar)
    zaten = sum(1 for s in satirlar if s["gold_da_var_mi"] == "EVET")

    print(f"  {CIKTI.name} yazildi")
    print(f"  toplam aday      : {len(satirlar)}")
    print(f"  zaten gold'da    : {zaten} (satirlari onceden EVET isaretli)")
    print(f"  karar bekleyen   : {len(satirlar) - zaten}")
    print()
    print("  Soru bazinda:")
    for soru, n in sorulara_gore.most_common():
        print(f"    {soru[:36]:<38}{n:>5} aday")
    print()
    print("  Doldurduktan sonra:")
    print("    python -m gold_dataset.rag_soru_seti_guncelle")


if __name__ == "__main__":
    main()

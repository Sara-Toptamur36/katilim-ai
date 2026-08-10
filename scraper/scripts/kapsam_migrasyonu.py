"""Daha once taranmis kayitlara kapsam kirpmasini uygular (tek seferlik).

NEDEN AYRI BIR BETIK: preprocessing/kapsam.py artik statik_scraper'a
bagli, yani YENI taramalar temiz gelecek. Ama scraper/raw_data'daki
mevcut kayitlar eski (kirpilmamis) metinle duruyor ve olcum onlari
kullaniyor. Yeniden tarama yapmak veriyi degistirirdi (kampanya
rotasyonu - bkz. tests/test_scraper_regresyon.py), bu yuzden yalnizca
saklanan metne ayni kirpma uygulanir.

GUVENLI: yalnizca kirpmanin GERCEKTEN bir sey degistirdigi dosyalar
yeniden yazilir; digerlerine dokunulmaz. `--kuru` ile once ne olacagini
gorebilirsiniz.

Kullanim:
    python -m scraper.scripts.kapsam_migrasyonu --kuru
    python -m scraper.scripts.kapsam_migrasyonu
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from preprocessing.kapsam import kampanya_govdesini_ayikla

RAW_DATA = Path(__file__).resolve().parents[1] / "raw_data"


def migrasyon(kuru: bool = False) -> dict:
    degisen: list[tuple[str, int, int]] = []
    dokunulmayan = 0

    for dosya in sorted(RAW_DATA.glob("*/json/*.json")):
        try:
            with open(dosya, encoding="utf-8") as f:
                kayit = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        ham = kayit.get("ham_metin") or ""
        kirpilmis = kampanya_govdesini_ayikla(ham)
        if kirpilmis == ham:
            dokunulmayan += 1
            continue

        degisen.append((kayit.get("url") or dosya.name, len(ham), len(kirpilmis)))
        if not kuru:
            kayit["ham_metin"] = kirpilmis
            with open(dosya, "w", encoding="utf-8") as f:
                json.dump(kayit, f, ensure_ascii=False, indent=2)

    return {"degisen": degisen, "dokunulmayan": dokunulmayan}


def main() -> int:
    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument("--kuru", action="store_true", help="Yazmadan sadece raporla")
    secim = ayristirici.parse_args()

    sonuc = migrasyon(kuru=secim.kuru)
    print(f"Dokunulmayan kayit : {sonuc['dokunulmayan']}")
    print(f"Kirpilan kayit     : {len(sonuc['degisen'])}")
    for url, once, sonra in sonuc["degisen"]:
        print(f"  {once:>6} -> {sonra:>6} karakter  ({once - sonra} silindi)  {url}")
    if secim.kuru and sonuc["degisen"]:
        print("\n(kuru calistirma - hicbir dosya yazilmadi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

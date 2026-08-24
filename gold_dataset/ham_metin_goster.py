"""Bir kaydin kaynak metnini okunabilir bicimde ekrana getirir.

Etiketlerken sayfayi tarayicida acmak en dogrusudur; ama sayfa kampanya
rotasyonuyla kaybolduysa ya da hizlica bakmak gerekiyorsa korpustaki ham
metin buradan okunur.

DEGER CIKARMAZ, YORUM YAPMAZ - yalnizca metni gosterir. Hangi satirin
hangi alana ait oldugu kararini okuyan verir.

Kullanim:
    python gold_dataset/ham_metin_goster.py KT-018
    python gold_dataset/ham_metin_goster.py KT-018 --tam     # kisaltmadan
    python gold_dataset/ham_metin_goster.py --url https://...
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

GOLD = KOK / "gold_dataset" / "altin_veri_seti.json"

# Sayisal/donemsel iz tasiyan satirlar - okuyanin gozu once oraya gitsin
# diye isaretlenir. Isaret bir IDDIA DEGILDIR, yalnizca dikkat cekmedir.
ILGINC = re.compile(
    r"\d|kâr pay|kar pay|vade|taksit|ötelem|erteleme|ödemesiz|masraf|dosya"
    r"|kampanya dönemi|geçerli|son gün|hediye|iade|puan|indirim",
    re.IGNORECASE,
)

# "Diger Kampanyalar" bolumu BASKA kampanyalara aittir (Calisma Rehberi A2).
BASKA_KAMPANYA_BASLIGI = re.compile(
    r"diğer kampanya|benzer kampanya|ilgini çekebilec|size özel diğer",
    re.IGNORECASE,
)


def _kaydi_bul(kayit_id: str) -> dict:
    with open(GOLD, encoding="utf-8") as f:
        for k in json.load(f):
            if k["kayit_id"] == kayit_id:
                return k
    raise SystemExit(f"Kayit bulunamadi: {kayit_id}")


def goster(url: str, baslik: str, tam: bool) -> None:
    from gold_dataset.sprint_is_listesi import _ham_kampanyalar, _slug

    kaynak = _ham_kampanyalar().get(_slug(url))
    if not kaynak:
        print(f"Korpusta ham metin yok: {url}")
        print("Sayfayi tarayicida acin ya da: "
              f"python gold_dataset/kaynak_tazele.py --kayit <ID>")
        return

    metin = kaynak.get("normalize_metin") or ""
    print("=" * 78)
    print(f"{baslik or kaynak.get('baslik') or '(baslik yok)'}")
    print(f"{url}")
    print(f"anlik goruntu: {(kaynak.get('erisim_zamani') or '?')[:19]} | "
          f"{len(metin)} karakter")
    print("=" * 78)

    kesildi = False
    for satir in metin.split("\n"):
        sade = " ".join(satir.split())
        if not sade:
            continue
        if BASKA_KAMPANYA_BASLIGI.search(sade) and not tam:
            print("\n--- 'Diger Kampanyalar' bolumu basliyor - buradan sonrasi")
            print("--- BASKA kampanyalara aittir, degerleri buradan almayin.")
            print("--- (tamamini gormek icin --tam)")
            kesildi = True
            break
        isaret = " *" if ILGINC.search(sade) else "  "
        print(f"{isaret} {sade}")

    if not kesildi:
        print()
    print("-" * 78)
    print("* isareti yalnizca DIKKAT CEKER - hangi degerin hangi alana")
    print("  ait oldugu kararini siz verirsiniz.")


def main() -> None:
    a = argparse.ArgumentParser(description="Kaydin kaynak metnini gosterir")
    a.add_argument("kayit_id", nargs="?", help="Ornek: KT-018")
    a.add_argument("--url", help="Kayit yerine dogrudan URL")
    a.add_argument("--tam", action="store_true",
                   help="'Diger Kampanyalar' bolumunu de goster")
    s = a.parse_args()

    if s.url:
        goster(s.url, "", s.tam)
    elif s.kayit_id:
        kayit = _kaydi_bul(s.kayit_id)
        goster(kayit.get("kaynak_url") or "", kayit.get("kampanya_adi") or "", s.tam)
    else:
        a.error("kayit_id ya da --url verin")


if __name__ == "__main__":
    main()

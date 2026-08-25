"""TASLAK/insan doğrulaması bekleyen İMZALI kayıtları tarar, denetim_raporu.json'ı üretir.

NEDEN GEREKLI: mevcut denetim_raporu.json elle yazilmisti ve bayatlamisti -
25 Agustos 2026'da olculdu: yalnizca 10 kayit listeliyordu, gercekte 45
IMZALI kayit "notlar" alaninda TASLAK notu tasiyordu (yani olculen 298
kayittan 45'i teknik olarak imzali ama insan dogrulamasi/ekran goruntusu
hala BEKLIYOR). Bu script raporu yeniden uretilebilir kilar - dosya elle
guncellenmez, bu betik calistirilir.

YALNIZCA IMZALI kayitlar taranir: imzasiz taslaklar zaten hicbir olcume
girmiyor (bkz. excel_to_json.py, "Taslak (imzasiz)" sayaci) - onlari burada
tekrar listelemek ayni bilgiyi iki yerde tutmak olurdu. Bu raporun konusu
DAHA DAR ve daha tehlikeli bir durum: satir teknik olarak IMZALI (olculen
sette sayiliyor) ama etiketleyicinin kendi notu hala dogrulama BEKLEDIGINI
soyluyor.

Kullanim:
    python -m gold_dataset.denetim_raporu_uret
"""

from __future__ import annotations

import json
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
GOLD = KOK / "gold_dataset" / "altin_veri_seti.json"
CIKTI = KOK / "gold_dataset" / "denetim_raporu.json"

TUR = "NOT YENIDEN OKUNMALI"
NOT_UZUNLUGU = 200


def _slug(url: str) -> str:
    return (url or "").rstrip("/").split("/")[-1]


def taslak_kayitlari_topla() -> list[dict]:
    """İmzalı ama notunda hâlâ TASLAK geçen kayıtları döndürür."""
    gold = json.loads(GOLD.read_text(encoding="utf-8"))
    kayitlar: list[dict] = []
    for k in gold:
        if not (k.get("giren_kisi") or "").strip():
            continue  # imzasiz taslak - zaten olcum disi, bu raporun konusu degil
        notlar = k.get("notlar") or ""
        if "TASLAK" not in notlar:
            continue
        kirpilmis = (
            notlar if len(notlar) <= NOT_UZUNLUGU
            else notlar[:NOT_UZUNLUGU].rstrip() + "..."
        )
        kayitlar.append({
            "kayit_id": k["kayit_id"],
            "tur": TUR,
            "not": kirpilmis,
            "slug": _slug(k.get("kaynak_url") or ""),
        })
    return kayitlar


def main() -> None:
    kayitlar = taslak_kayitlari_topla()
    CIKTI.write_text(json.dumps(kayitlar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Yazildi: {CIKTI.relative_to(KOK)}")
    print(f"  Imzali ama TASLAK notu tasiyan kayit: {len(kayitlar)}")


if __name__ == "__main__":
    main()

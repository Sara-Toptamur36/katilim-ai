"""Gold veri seti icin banka-katmanli, kampanya-sizintisiz train/test split.

NEDEN GEREKLI: Mentorluk raporu II (Bolum 5.4) "banka bazli ve zaman bazli
split kullanin: ayni kampanyanin farkli snapshot'lari train ve test arasinda
sizmamali" diyor. Bugun gold_dataset/altin_veri_seti.json'da her kampanyanin
tek bir zaman noktasi etiketli (henuz coklu-snapshot etiketleme yok), ama
split MANTIGI simdiden dogru kurulmali: gruplama daima kaynak_url uzerinden
yapilir, boylece ileride ayni kampanyanin ikinci bir zaman noktasi
etiketlendiginde otomatik olarak aynı tarafta (train VEYA test, ikisi
birden degil) kalir - split scripti tekrar yazilmasi gerekmez.

NEDEN training/ DEGIL gold_dataset/ ALTINDA: docs/kapsam_ve_veri_ayrimi.md
Bolum 4'teki karar - bos bir training/ dizini acmak, egitim yapmadigimiz
halde egitim yapiyormus izlenimi verir. Bu script bir split URETIR, egitim
YAPMAZ; dolayisiyla zaten var olan gold_dataset/ altinda kalir.

NEDEN ORNEK KAYITLAR (giren_kisi=ORNEK) HARIC TUTULUR: A/B/C/D Bankasi
kayitlari sartname Md. 5 ornek tablosundan kopyalanmis referans kayitlardir,
gercek banka verisi degildir (bkz. dosyanin kendi notlari alani). Split'e
girerlerse hem train hem test setini gercek olmayan veriyle kirletir.

Kullanim:
    python -m gold_dataset.split_manifest_uret
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

KOK = Path(__file__).resolve().parent
GOLD_DOSYASI = KOK / "altin_veri_seti.json"
CIKTI_DOSYASI = KOK / "split_manifest_v1.json"

TEST_ORANI = 0.2
TOHUM = 42  # deterministik - ayni veriyle her calistirmada AYNI split uretir


def _gercek_kayitlari_yukle() -> list[dict]:
    with open(GOLD_DOSYASI, encoding="utf-8") as f:
        kayitlar = json.load(f)
    return [k for k in kayitlar if k.get("giren_kisi") != "ORNEK"]


def _kaynak_url_gruplari(kayitlar: list[dict]) -> dict[str, list[dict]]:
    """kaynak_url'ye gore gruplar - ayni kampanyanin (ileride eklenecek)
    birden fazla zaman noktasi etiketi hep AYNI grupta kalir."""
    gruplar: dict[str, list[dict]] = defaultdict(list)
    for kayit in kayitlar:
        gruplar[kayit["kaynak_url"]].append(kayit)
    return dict(gruplar)


def split_uret() -> dict:
    """Banka-katmanli split: her bankanin kendi kampanya URL'leri ayri ayri
    train/test'e bolunur (bir bankanin TUMU train'e, digerinin TUMU test'e
    dusmesin diye) - ama bolme birimi daima kaynak_url'dir, tek tek kayit
    degil (bkz. modul docstring'i)."""
    kayitlar = _gercek_kayitlari_yukle()
    url_gruplari = _kaynak_url_gruplari(kayitlar)

    banka_bazinda_urller: dict[str, list[str]] = defaultdict(list)
    for url, grup in url_gruplari.items():
        banka = grup[0]["banka"]
        banka_bazinda_urller[banka].append(url)

    rastgele = random.Random(TOHUM)
    train_urller: list[str] = []
    test_urller: list[str] = []

    for banka, urller in sorted(banka_bazinda_urller.items()):
        siralanmis = sorted(urller)  # deterministik baslangic sirasi
        rastgele.shuffle(siralanmis)
        test_sayisi = max(1, round(len(siralanmis) * TEST_ORANI)) if len(siralanmis) >= 3 else 0
        test_urller.extend(siralanmis[:test_sayisi])
        train_urller.extend(siralanmis[test_sayisi:])

    def _kayit_idler(urller: list[str]) -> list[str]:
        idler = []
        for url in urller:
            idler.extend(k["kayit_id"] for k in url_gruplari[url])
        return sorted(idler)

    manifest = {
        "surum": "v1",
        "olusturulma_yontemi": "banka-katmanli, kaynak_url gruplu split (gold_dataset/split_manifest_uret.py)",
        "test_orani_hedef": TEST_ORANI,
        "tohum": TOHUM,
        "toplam_kayit": len(kayitlar),
        "toplam_kampanya_url": len(url_gruplari),
        "train": _kayit_idler(train_urller),
        "test": _kayit_idler(test_urller),
        "banka_bazinda_ozet": {
            banka: {
                "toplam_url": len(urller),
                "test_url": max(1, round(len(urller) * TEST_ORANI)) if len(urller) >= 3 else 0,
            }
            for banka, urller in sorted(banka_bazinda_urller.items())
        },
    }
    return manifest


def kaydet() -> Path:
    manifest = split_uret()
    with open(CIKTI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return CIKTI_DOSYASI


if __name__ == "__main__":
    yol = kaydet()
    manifest = split_uret()
    print(f"Manifest yazildi: {yol}")
    print(f"Train: {len(manifest['train'])} kayit, Test: {len(manifest['test'])} kayit")

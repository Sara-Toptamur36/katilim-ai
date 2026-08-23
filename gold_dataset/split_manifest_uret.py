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

NEDEN ATAMALAR DONDURULUR: onceki surum her calistirmada butun URL listesini
bastan karistiriyordu. Tohum sabit olsa da shuffle'in sonucu LISTE ICERIGINE
baglidir - etiketleme sprintinde 3 yeni kayit eklemek mevcut 103 kaydin
19'unu taraf degistiriyordu (olculdu). Bunun bedeli agirdir: test setinde
olculmus bir kayit sonraki koşuda train'e gecerse, o olcum artik bagimsiz
degildir ve "test setimize hic dokunmadik" denemez.

Bu yuzden bir URL bir kez taraf aldiktan sonra ORADA KALIR. Yalnizca daha
once gorulmemis URL'ler atanir. Etiketleme sprinti boyunca test seti
buyuyebilir ama icindekiler yer degistirmez.

Kullanim:
    python -m gold_dataset.split_manifest_uret
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

KOK = Path(__file__).resolve().parent
GOLD_DOSYASI = KOK / "altin_veri_seti.json"
CIKTI_DOSYASI = KOK / "split_manifest_v1.json"

TEST_ORANI = 0.2


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


def _onceki_atamalar() -> dict[str, str]:
    """Daha once yazilmis manifest'ten url -> 'train'/'test' haritasi.

    Manifest kayit_id tutar, ama bolme birimi URL'dir; eslemeyi gold
    dosyasindan kurariz. Manifest yoksa (ilk uretim) bos doner."""
    if not CIKTI_DOSYASI.exists():
        return {}
    with open(CIKTI_DOSYASI, encoding="utf-8") as f:
        onceki = json.load(f)
    with open(GOLD_DOSYASI, encoding="utf-8") as f:
        kayit_url = {k["kayit_id"]: k["kaynak_url"] for k in json.load(f)}

    atamalar: dict[str, str] = {}
    for taraf in ("train", "test"):
        for kayit_id in onceki.get(taraf, []):
            url = kayit_url.get(kayit_id)
            if url:  # silinmis kayit varsa atlanir
                atamalar[url] = taraf
    return atamalar


def _sira_anahtari(url: str) -> str:
    """URL'nin kendi hash'i - atama sirasi listenin icerigine degil,
    URL'nin kendisine bagli olsun diye. Ayni URL her zaman ayni yerde."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def split_uret() -> dict:
    """Banka-katmanli, ATAMASI DONDURULMUS split.

    Daha once taraf almis her URL tarafinda kalir; yalnizca yeni URL'ler
    atanir. Yeni URL'ler banka bazinda, o bankanin test orani hedefin
    altinda kaldigi surece test'e gider - boylece set buyudukce oran
    hedefe yaklasir ama eski atamalar hic bozulmaz."""
    kayitlar = _gercek_kayitlari_yukle()
    url_gruplari = _kaynak_url_gruplari(kayitlar)
    onceki = _onceki_atamalar()

    banka_bazinda_urller: dict[str, list[str]] = defaultdict(list)
    for url, grup in url_gruplari.items():
        banka = grup[0]["banka"]
        banka_bazinda_urller[banka].append(url)

    train_urller: list[str] = []
    test_urller: list[str] = []
    korunan = 0

    for _banka, urller in sorted(banka_bazinda_urller.items()):
        eski_test = [u for u in urller if onceki.get(u) == "test"]
        eski_train = [u for u in urller if onceki.get(u) == "train"]
        yeni = sorted((u for u in urller if u not in onceki), key=_sira_anahtari)
        korunan += len(eski_test) + len(eski_train)

        test_urller.extend(eski_test)
        train_urller.extend(eski_train)

        # Bu bankada kac URL test'te olmali - eskiler dahil toplam hedef.
        toplam = len(urller)
        hedef_test = max(1, round(toplam * TEST_ORANI)) if toplam >= 3 else 0
        acik = max(0, hedef_test - len(eski_test))

        test_urller.extend(yeni[:acik])
        train_urller.extend(yeni[acik:])

    def _kayit_idler(urller: list[str]) -> list[str]:
        idler = []
        for url in urller:
            idler.extend(k["kayit_id"] for k in url_gruplari[url])
        return sorted(idler)

    test_kumesi = set(test_urller)
    manifest = {
        "surum": "v1",
        "olusturulma_yontemi": (
            "banka-katmanli, kaynak_url gruplu, atamasi dondurulmus split "
            "(gold_dataset/split_manifest_uret.py)"
        ),
        "test_orani_hedef": TEST_ORANI,
        "onceki_surumden_korunan_url": korunan,
        "yeni_atanan_url": len(url_gruplari) - korunan,
        "toplam_kayit": len(kayitlar),
        "toplam_kampanya_url": len(url_gruplari),
        "train": _kayit_idler(train_urller),
        "test": _kayit_idler(test_urller),
        "banka_bazinda_ozet": {
            banka: {
                "toplam_url": len(urller),
                "test_url": sum(1 for u in urller if u in test_kumesi),
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

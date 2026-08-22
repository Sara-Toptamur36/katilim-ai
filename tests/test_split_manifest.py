"""gold_dataset/split_manifest_uret.py testleri - gercek gold veri setiyle."""

import json
from pathlib import Path

from gold_dataset.split_manifest_uret import _gercek_kayitlari_yukle, split_uret

_GOLD_DOSYASI = Path(__file__).resolve().parent.parent / "gold_dataset" / "altin_veri_seti.json"


def test_ornek_kayitlar_disarida_birakilir():
    """A/B/C/D Bankasi (giren_kisi=ORNEK) gercek veri degildir, split'e
    girmemeli."""
    kayitlar = _gercek_kayitlari_yukle()
    assert all(k.get("giren_kisi") != "ORNEK" for k in kayitlar)

    # SABIT SAYI TUTULMUYOR: burada once `== 58` yaziyordu ve etiketleme
    # sprinti (gorev 21, hedef 200-300 kayit) her yeni kayitta bu testi
    # kiriyordu. Sabit sayi, insanlari testi YAMAMAYA alistirir ve testin
    # asil isini - yukleyicinin ORNEK kayitlari elemesi - golgeler.
    # Beklenen sayi dosyanin kendisinden hesaplanir.
    with open(_GOLD_DOSYASI, encoding="utf-8") as f:
        beklenen = sum(1 for k in json.load(f) if k.get("giren_kisi") != "ORNEK")
    assert len(kayitlar) == beklenen
    assert kayitlar, "gercek kayit kalmadi - suzgec fazla mi eliyor?"


def test_ayni_kaynak_url_iki_tarafta_birden_olmaz():
    """Ayni kampanyanin (kaynak_url) kayitlari hem train hem test'te
    gorunmemeli - bu, mentorun 5.4'teki sizinti uyarisinin dogrudan testi."""
    manifest = split_uret()
    with open(_GOLD_DOSYASI, encoding="utf-8") as f:
        tum_kayitlar = {k["kayit_id"]: k["kaynak_url"] for k in json.load(f)}

    train_urller = {tum_kayitlar[kid] for kid in manifest["train"]}
    test_urller = {tum_kayitlar[kid] for kid in manifest["test"]}
    assert train_urller & test_urller == set()


def test_tum_gercek_kayitlar_tam_bir_kez_yer_alir():
    manifest = split_uret()
    tum_idler = set(manifest["train"]) | set(manifest["test"])
    assert len(tum_idler) == manifest["toplam_kayit"]
    assert len(manifest["train"]) + len(manifest["test"]) == manifest["toplam_kayit"]


def test_split_deterministik():
    """Ayni tohumla iki kez calistirinca AYNI sonuc cikmali - reproducibility."""
    m1 = split_uret()
    m2 = split_uret()
    assert m1["train"] == m2["train"]
    assert m1["test"] == m2["test"]


def test_test_seti_bos_degil_ve_makul_oranda():
    manifest = split_uret()
    assert len(manifest["test"]) > 0
    oran = len(manifest["test"]) / manifest["toplam_kayit"]
    assert 0.05 <= oran <= 0.35  # hedef %20, ama kucuk banka gruplarinda yuvarlama oynar


def test_her_banka_kendi_icinde_bolunur():
    """Kucuk bankalar (3'ten az URL) test'e hic girmeyebilir (istatistiksel
    olarak anlamsiz olur) - ama 3+ URL'si olan bankalarin test payi olmali."""
    manifest = split_uret()
    for banka, ozet in manifest["banka_bazinda_ozet"].items():
        if ozet["toplam_url"] >= 3:
            assert ozet["test_url"] >= 1, f"{banka} icin test payi bekleniyordu"

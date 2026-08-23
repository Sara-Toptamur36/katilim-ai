"""gold_dataset/split_manifest_uret.py testleri - gercek gold veri setiyle."""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from gold_dataset import split_manifest_uret as split_modulu
from gold_dataset.split_manifest_uret import (
    _gercek_kayitlari_yukle,
    _url_kume_anahtarlari,
    split_uret,
)

_GOLD_DIZINI = Path(__file__).resolve().parent.parent / "gold_dataset"
_GOLD_DOSYASI = _GOLD_DIZINI / "altin_veri_seti.json"
_MANIFEST_DOSYASI = _GOLD_DIZINI / "split_manifest_v1.json"


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
        beklenen = sum(
            1 for k in json.load(f)
            if k.get("giren_kisi") != "ORNEK"
            and (k.get("giren_kisi") or "").strip()
        )
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


def test_yazili_manifest_ile_uretilen_ayni():
    """Depodaki manifest, bugunku veriyle uretilenle ayni olmali.

    Kirilirsa: gold sete kayit eklenmis ama manifest yeniden uretilmemis.
    Cozum testi degistirmek degil, `python -m gold_dataset.split_manifest_uret`
    calistirip cikan manifesti commit etmektir."""
    with open(_MANIFEST_DOSYASI, encoding="utf-8") as f:
        yazili = json.load(f)
    uretilen = split_uret()
    assert yazili["train"] == uretilen["train"]
    assert yazili["test"] == uretilen["test"]


def test_yeni_kayit_eklenince_eski_atamalar_degismez():
    """Etiketleme sprintinin ana sizinti riski.

    Onceki surum her calistirmada butun listeyi bastan karistiriyordu; 3
    yeni kayit eklemek mevcut 103 kaydin 19'unu taraf degistiriyordu. Test
    setinde olculmus bir kayit sonraki koşuda train'e gecerse o olcum artik
    bagimsiz degildir. Bu test, bir URL taraf aldiktan sonra ORADA
    KALDIGINI dogrular."""
    taban = split_uret()

    with tempfile.TemporaryDirectory() as gecici:
        gecici_yol = Path(gecici)
        shutil.copy(_GOLD_DOSYASI, gecici_yol / "gold.json")
        shutil.copy(_MANIFEST_DOSYASI, gecici_yol / "manifest.json")

        with open(gecici_yol / "gold.json", encoding="utf-8") as f:
            kayitlar = json.load(f)
        bankalar = ["Kuveyt Türk", "Ziraat Katılım", "Türkiye Emlak Katılım", "Vakıf Katılım"]
        kayitlar.extend(
            {
                "kayit_id": f"SIMULE-{i:03d}",
                "banka": bankalar[i % len(bankalar)],
                "kaynak_url": f"https://simule.test/kampanya-{i}",
                "giren_kisi": "Test",
            }
            for i in range(12)
        )
        with open(gecici_yol / "gold.json", "w", encoding="utf-8") as f:
            json.dump(kayitlar, f, ensure_ascii=False)

        # Modul seviyesindeki yollari gecici kopyaya cevirip geri koyariz -
        # gercek gold dosyasi ve manifest bu testten etkilenmez.
        gercek_gold, gercek_cikti = split_modulu.GOLD_DOSYASI, split_modulu.CIKTI_DOSYASI
        try:
            split_modulu.GOLD_DOSYASI = gecici_yol / "gold.json"
            split_modulu.CIKTI_DOSYASI = gecici_yol / "manifest.json"
            genisletilmis = split_uret()
        finally:
            split_modulu.GOLD_DOSYASI, split_modulu.CIKTI_DOSYASI = gercek_gold, gercek_cikti

    eski_test, eski_train = set(taban["test"]), set(taban["train"])
    yeni_test, yeni_train = set(genisletilmis["test"]), set(genisletilmis["train"])

    kacan = eski_test & yeni_train
    sizan = eski_train & yeni_test
    assert not kacan, f"test'ten train'e kayan kayitlar: {sorted(kacan)}"
    assert not sizan, f"train'den test'e kayan kayitlar: {sorted(sizan)}"
    # Simule URL'ler korpusta olmadigi icin kumelenemez; her biri kendi
    # kumesi sayilir.
    assert genisletilmis["yeni_atanan_kume"] == 12


def test_imzasiz_taslak_split_e_girmez():
    """Etiketleme kuyrugundan acilan taslaklar olcum disidir.

    Taslak satirin butun olculen alanlari bostur; split'e girerse test
    seti hakkinda hicbir sey soylenemeyen kayitlarla dolar. Kayit
    imzalandigi anda kendiliginden split'e girer."""
    with open(_GOLD_DOSYASI, encoding="utf-8") as f:
        gold = json.load(f)
    imzasiz = {k["kayit_id"] for k in gold if not (k.get("giren_kisi") or "").strip()}

    manifest = split_uret()
    icerdekiler = set(manifest["train"]) | set(manifest["test"])
    sizanlar = imzasiz & icerdekiler
    assert not sizanlar, f"imzasiz taslak split'e girmis: {sorted(sizanlar)}"


def test_ayni_sablon_kumesi_iki_tarafa_bolunmez():
    """Sablon sizintisi - olculdu ve kapatildi.

    URL bazli split iki AYRI kampanyayi farkli taraflara koyabiliyordu,
    oysa metinleri neredeyse ayniydi: "Akaryakit Harcamalariniza 300 TL
    ParafPara" (TEK-003, train) ile "Ucak Bileti Harcamalariniza 2.000 TL
    ParafPara" (TEK-006, test) ayni kalibin iki ornegi. Motor kalibi
    train'de gorup test'te taniyacagi icin olcum siserdi. Ayni durum
    KT-012/KT-014'te de vardi.

    Bu, mentorluk raporu II Bolum 5.4'teki sizinti uyarisinin daha ince
    hali: ayni kampanya degil, ayni SABLON."""
    manifest = split_uret()
    with open(_GOLD_DOSYASI, encoding="utf-8") as f:
        kayit_url = {k["kayit_id"]: k["kaynak_url"] for k in json.load(f)}

    kume_anahtari, sorun = _url_kume_anahtarlari(sorted(set(kayit_url.values())))
    if sorun:
        pytest.skip(f"kumeleme yapilamadi: {sorun}")

    def kumeler(kayit_idler):
        return {kume_anahtari[kayit_url[kid]] for kid in kayit_idler}

    ortak = kumeler(manifest["train"]) & kumeler(manifest["test"])
    assert not ortak, f"ayni sablon kumesi hem train hem test'te: {sorted(ortak)}"


def test_kumeleme_sessizce_atlanmaz():
    """Kumeleme calismadiysa manifest bunu SOYLEMELI.

    Sessiz dususte split sizintisiz GORUNUR ama degildir - uretilen
    manifest'e bakan biri farki anlayamaz."""
    manifest = split_uret()
    assert "kumeleme" in manifest
    assert manifest["kumeleme"] == "uygulandi" or \
        manifest["kumeleme"].startswith("UYGULANAMADI - "), manifest["kumeleme"]


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

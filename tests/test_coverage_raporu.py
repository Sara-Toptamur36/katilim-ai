"""scraper/scripts/coverage_raporu.py testleri.

TASARIM: kampanya_tarihcesi testleriyle ayni ilke - gercek scraper/raw_data
verisiyle test edilir (sentetik degil), Docker/Postgres GEREKMEZ (bkz. script
docstring'i - bu scriptin butun amaci Docker'siz calisabilmek)."""

from scraper.scripts.coverage_raporu import (
    _banka_kod_ad_haritasi,
    _en_son_kayitlar,
    _gold_sayilari_banka_bazinda,
    _snapshot_istatistikleri,
    _url_gruplari_ve_banka_haritasi,
    alan_ekseni,
    banka_ekseni,
    rapor_uret,
)


def test_rapor_dort_ekseni_de_icerir():
    rapor = rapor_uret()
    assert "## 1. Banka ekseni" in rapor
    assert "## 2. Urun ailesi ekseni" in rapor
    assert "## 3. Zaman ekseni" in rapor
    assert "## 4. Alan ekseni" in rapor


def test_banka_ekseni_toplam_snapshot_raw_data_ile_tutarli():
    """Banka bazinda snapshot toplami, tum raw_data dosya sayisiyla ayni
    olmali - kayip/cift sayim regresyonuna karsi kilit."""
    kod_ad = _banka_kod_ad_haritasi()
    url_gruplari, banka_of_url = _url_gruplari_ve_banka_haritasi(kod_ad)
    snapshot_ist = _snapshot_istatistikleri(url_gruplari, banka_of_url)
    gold = _gold_sayilari_banka_bazinda(kod_ad)

    satirlar = banka_ekseni(snapshot_ist, gold)
    toplam_snapshot = sum(s["snapshot"] for s in satirlar)
    toplam_dosya = sum(len(kayitlar) for kayitlar in url_gruplari.values())
    assert toplam_snapshot == toplam_dosya
    assert toplam_snapshot >= 200, "Beklenenden az raw_data kaydi bulundu - kaynak yolu degismis olabilir"


def test_gold_sayilari_toplami_gold_dataset_ile_tutarli():
    """Ornek/referans kayit (A-001) haric, banka bazinda gold sayilarinin
    toplami gercek gold_dataset kayit sayisina esit olmali."""
    import json
    from pathlib import Path

    kod_ad = _banka_kod_ad_haritasi()
    gold = _gold_sayilari_banka_bazinda(kod_ad)

    gold_dosyasi = Path(__file__).resolve().parents[1] / "gold_dataset" / "altin_veri_seti.json"
    with open(gold_dosyasi, encoding="utf-8") as f:
        ham_kayitlar = json.load(f)

    from scraper.scripts.gold_eslesme import KOD_HARITASI

    beklenen_toplam = sum(
        1 for k in ham_kayitlar if KOD_HARITASI.get(k.get("kayit_id", "").split("-")[0])
    )
    assert sum(gold.values()) == beklenen_toplam


def test_alan_ekseni_yuzdeler_0_100_araliginda():
    kod_ad = _banka_kod_ad_haritasi()
    url_gruplari, _ = _url_gruplari_ve_banka_haritasi(kod_ad)
    en_son = _en_son_kayitlar(url_gruplari)

    satirlar = alan_ekseni(en_son)
    assert len(satirlar) > 0
    for s in satirlar:
        assert 0.0 <= s["yuzde"] <= 100.0
        assert s["dolu"] <= s["toplam"]


def test_en_son_kayitlar_her_url_icin_tek_kayit_doner():
    """Coklu versiyonlu (delta) kampanyalarda en son kayit secilmeli -
    urun ailesi/alan eksenleri ayni kampanyayi iki kez saymamali."""
    kod_ad = _banka_kod_ad_haritasi()
    url_gruplari, _ = _url_gruplari_ve_banka_haritasi(kod_ad)
    en_son = _en_son_kayitlar(url_gruplari)

    assert len(en_son) == len(url_gruplari)
    for url, kayit in en_son.items():
        tum_zamanlar = [k.get("erisim_zamani") or "" for k in url_gruplari[url]]
        assert kayit.get("erisim_zamani") == max(tum_zamanlar)

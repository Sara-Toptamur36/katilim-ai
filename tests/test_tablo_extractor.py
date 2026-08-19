"""extraction/tablo_extractor.py testleri.

GERCEK scraper/raw_data kayitlariyla test edilir (sentetik degil) -
sutun basliklarindaki zero-width space / nbsp gibi gercek-dunya
gariplikleri sentetik veride yeniden uretmek yaniltici olurdu.
"""

import json
from pathlib import Path

from extraction.tablo_extractor import oran_tablolarini_sec

RAW_DATA = Path(__file__).parent.parent / "scraper" / "raw_data"


def _kaydi_yukle(goreli_yol: str) -> dict:
    with open(RAW_DATA / goreli_yol, encoding="utf-8") as f:
        return json.load(f)


def test_tablo_yoksa_none_doner():
    assert oran_tablolarini_sec(None) is None
    assert oran_tablolarini_sec([]) is None


def test_oransiz_odul_tablosunu_elerse():
    """Dunya Katilim'in 'davet et kazan' tablosu (Biriken Altin / Davet
    Edilen Yeni Musteri Sayisi) bir odul kademesi tablosudur, kar payi
    oraniyla ilgisi yoktur - secilmemeli."""
    kayit = _kaydi_yukle(
        "dunyakatilim/json/20260818_dunyakatilim_kampanyalar_davetetkazan.json"
    )
    assert oran_tablolarini_sec(kayit["tablolar"]) is None


def test_turkiye_finans_iki_farkli_oran_tablosunu_da_secer():
    """TF sayfasinda 'sigortali'/'sigortasiz' icin AYRI iki oran tablosu
    var, ikisi de gercek kar payi verisi tasiyor - ikisi de secilmeli,
    aralarinda otomatik SECIM YAPILMAMALI (bkz. modul docstring'i)."""
    kayit = _kaydi_yukle(
        "turkiyefinans/json/"
        "20260806_turkiyefinans_tr-tr_kampanyalar_Sayfalar_"
        "banka-calisanlarina-ozel-ihtiyac-finansmani.aspx.json"
    )
    secilen = oran_tablolarini_sec(kayit["tablolar"])
    assert secilen is not None
    assert len(secilen) == 2
    for tablo in secilen:
        assert any("vade" in s.lower() for s in tablo["sutunlar"])
        assert any("oran" in s.lower() for s in tablo["sutunlar"])
        assert len(tablo["satirlar"]) == 6

    # Gorunmez karakterler temizlenmis olmali (kaynakta '​Va​de' idi)
    assert "​" not in secilen[0]["sutunlar"][0]
    # Degerler DEGISTIRILMEMIS olmali - ilk satirin orani kaynaktaki gibi kalmali
    ilk_satir = secilen[0]["satirlar"][0]
    oran_degeri = next(v for k, v in ilk_satir.items() if "oran" in k.lower())
    assert oran_degeri in ("4,20%", "5,20%")


def test_albaraka_vade_tutar_kirilimli_tabloyu_secer_ama_indirgemez():
    """Albaraka'nin tablosunda AYNI vade araliginda FARKLI tutar dilimine
    gore farkli oran var (0% ve 3,95% ayni '1-6 ay' vadesinde) - bu
    modulun neden TEK bir sayi UYDURMADIGININ tam kaniti."""
    kayit = _kaydi_yukle(
        "albaraka/json/"
        "20260731_albaraka_tr_kampanyalar_detay_"
        "dijital-musterilere-ozel-pratik-finansman-kart.json"
    )
    secilen = oran_tablolarini_sec(kayit["tablolar"])
    assert secilen is not None
    assert len(secilen) == 1
    oranlar = {
        satir["Aylık Kar Oranı"] for satir in secilen[0]["satirlar"]
    }
    assert "0%" in oranlar
    assert "3,95%" in oranlar

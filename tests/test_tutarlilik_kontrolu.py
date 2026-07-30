"""Terminoloji Tutarlilik Kontrolu testleri (Sartname Md. 5.5, Sprint 1 Gun 3)."""

import json
from pathlib import Path

import pytest

from terminology.tutarlilik_kontrolu import terminoloji_tutarliligini_kontrol_et

GOLD_DATASET_YOLU = Path(__file__).parent.parent / "gold_dataset" / "altin_veri_seti.json"


@pytest.mark.parametrize(
    "metin,beklenen_terim",
    [
        ("Bu urunun faiz orani %1,89dur.", "faiz"),
        ("Faizli bir kredi urunudur.", "faizli"),
        ("Mevduat hesabi acabilirsiniz.", "mevduat"),
        ("Bu bir kredi basvurusudur.", "kredi"),
        ("Krediyle odeme yapabilirsiniz.", "krediyle"),
    ],
)
def test_gelenek_terim_dogru_tespit_edilir(metin, beklenen_terim):
    sonuc = terminoloji_tutarliligini_kontrol_et(metin)
    assert sonuc["tutarli"] is False
    bulunan_terimler = [s["gelenek_terim"].lower() for s in sonuc["bulunan_sorunlar"]]
    assert beklenen_terim.lower() in bulunan_terimler


@pytest.mark.parametrize(
    "metin",
    [
        "Faizsiz finansman firsati",
        "Kredi kartiyla odeyin",
        "Kredi kartindan harcama yapabilirsiniz",
        "Kredi bakiyeniz yeterlidir",
        "Kredi limitine gore kademeli mil kazanirsiniz",
        "Tamamen alakasiz bir cumle",
    ],
)
def test_mesru_kullanimlar_yanlis_alarm_vermez(metin):
    sonuc = terminoloji_tutarliligini_kontrol_et(metin)
    assert sonuc["tutarli"] is True
    assert sonuc["bulunan_sorunlar"] == []


def test_onerilen_standart_terim_dogru():
    sonuc = terminoloji_tutarliligini_kontrol_et("Faiz orani dusuktur.")
    assert sonuc["bulunan_sorunlar"][0]["onerilen"] == "Kâr Payı"


def test_birden_fazla_sorun_hepsi_yakalanir():
    sonuc = terminoloji_tutarliligini_kontrol_et(
        "Bu urunun faiz orani vardir ve bir kredi basvurusu gerektirir."
    )
    assert sonuc["tutarli"] is False
    assert len(sonuc["bulunan_sorunlar"]) == 2


def test_altin_veri_setinde_musteriye_gorunen_metinde_yanlis_alarm_yok():
    """Ajanin gorecegi/uretecegi metin turu (kampanya_avantaji, masraf_durumu,
    hedef_kitle) - 'notlar' alani DAHIL DEGIL, cunku o Sara'nin dahili veri
    girisi notu, ajan yanitina hic karismayacak. Gercek 62 kayittaki musteri
    metninde sifir yanlis alarm bekleniyor (kredi kartlarinin hepsi 'kredi
    kart*' / 'kredi bakiye*' / 'kredi limit*' istisnasina giriyor)."""
    with open(GOLD_DATASET_YOLU, encoding="utf-8") as f:
        data = json.load(f)

    yanlis_alarmlar = []
    for kayit in data:
        metin = " ".join(
            [
                kayit.get("kampanya_avantaji") or "",
                kayit.get("masraf_durumu") or "",
                kayit.get("hedef_kitle") or "",
            ]
        )
        sonuc = terminoloji_tutarliligini_kontrol_et(metin)
        if not sonuc["tutarli"]:
            yanlis_alarmlar.append((kayit["kayit_id"], sonuc["bulunan_sorunlar"]))

    assert yanlis_alarmlar == [], f"Musteri metninde yanlis alarm(lar): {yanlis_alarmlar}"

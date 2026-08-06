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
        # Zeynep'in 129 kayitlik tam scraper verisiyle (9 banka) yapilan
        # taramada bulunan ek mesru bilesikler:
        "Kredi skorunuz basvuru sonucunu etkileyebilir",
        "Basvurunuz kredi notunuza gore degerlendirilir",
        "Talepler bankamizin kredi ve tahsis politikalari cercevesinde degerlendirilir",
        "Toplam acik kredi bakiyesi 250 Bin TL siniri gecemez",
        "Taksitli veya Veresiye Kredi bakiyesi kontrol edilir",
    ],
)
def test_mesru_kullanimlar_yanlis_alarm_vermez(metin):
    sonuc = terminoloji_tutarliligini_kontrol_et(metin)
    assert sonuc["tutarli"] is True
    assert sonuc["bulunan_sorunlar"] == []


@pytest.mark.parametrize(
    "metin,beklenen_terim",
    [
        # "İhtiyaç Kredisi" duzenleyici/yasal bir sinif adi olarak
        # kullanilsa da, katilim bankalarinin PAZARLADIGI standart terim
        # degildir (bkz. Turkiye Finans: "resmi olarak Ihtiyac Kredisi
        # olarak da nitelendirilmekte") - bilerek flaglenmeye devam eder.
        ("Bu urun resmi olarak İhtiyaç Kredisi olarak da nitelendirilmektedir.", "kredisi"),
        # Bir banka sitesinin kendi menu/kategori adi "Mevduat
        # Kampanyalari" olsa bile, ajan yanitinda bu kelime gecerse
        # flaglenmelidir - kaynagi ne olursa olsun ayni kural gecerli.
        ("Kart Kampanyaları, Mevduat Kampanyaları, Sigorta Kampanyaları", "mevduat"),
    ],
)
def test_bilerek_flaglenmeye_devam_eden_durumlar(metin, beklenen_terim):
    """Her 'kredi'/'mevduat' gecen cumle mesru degildir - istisnalar dar
    ve kanitli tutulmali, asiri genisletilmemeli."""
    sonuc = terminoloji_tutarliligini_kontrol_et(metin)
    assert sonuc["tutarli"] is False
    bulunan_terimler = [s["gelenek_terim"].lower() for s in sonuc["bulunan_sorunlar"]]
    assert beklenen_terim.lower() in bulunan_terimler


# Alarm vermesi BEKLENEN sayfalar - her biri, bankanin kendi metninde
# gercekten gelenek bankacilik terimi kullanmasindan kaynaklanir (yanlis
# pozitif DEGIL). Dosya adindaki tarih onekinden bagimsiz olmasi icin
# yalnizca sayfa slug'i tutulur: ayni sayfa farkli tarihlerde tekrar
# tarandiginda (Zeynep'in periyodik taramalari) bu liste degismez.
#
# NOT: Bu test bilerek SAYI yerine KALIP kontrol eder. Onceden
# "len(alarmlar) <= 3" seklindeydi; veri 129 -> 234 kayda buyuyunce
# (10 banka tam tarama + ayni sayfalarin ikinci tarama tarihi) test
# gercek bir hata olmadigi halde kirildi. Kalip tabanli kontrol hem
# veri buyumesine hem yeniden taramaya dayaniklidir, ama YENI bir
# yanlis pozitif cikarsa yine de yakalar.
ALARM_VERMESI_BEKLENEN_SAYFALAR = {
    # Turkiye Finans: site menusundeki "Mevduat Kampanyalari" kategori linki
    "turkiyefinans_tr-tr_kampanyalar_Sayfalar_Biten-Kampanyalar",
    # Turkiye Finans: "resmi olarak Ihtiyac Kredisi olarak da nitelendirilmekte"
    # - duzenleyici sinif adi, ama katilim bankasinin PAZARLADIGI terim degil
    "turkiyefinans_tr-tr_kampanyalar_Sayfalar_banka-calisanlarina-ozel-ihtiyac-finansmani",
    "turkiyefinans_tr-tr_kampanyalar_Sayfalar_kamu-calisanlarina-ozel-ihtiyac-finansmani",
    # Hayat Finans: yasal uyari metninde "uygun gormedigi kredi
    # basvurularini onaylamama hakkina sahiptir" - bankanin kendi
    # metninde gelenek terim; test_bilerek_flaglenmeye_devam_eden_
    # durumlar'daki ayni ilke geregi (kaynagi ne olursa olsun ayni
    # kural gecerli) flaglenmeye devam etmeli.
    "hayatfinans_kampanyalar_bana-bunu-al-is-ortagim-ile-troy-magaza-firsatlari",
    "hayatfinans_kampanyalar_xiaomi-urunlerinde-finansman-avantaji",
}


def test_gercek_scraper_verisinde_yalnizca_bilinen_sayfalar_alarm_veriyor():
    """Zeynep'in tam scraper verisi uzerinde kosuldugunda, YALNIZCA
    yukarida gerekcesi belgelenmis sayfalarda alarm olmali - hicbiri
    regex/mesru urun adi kaynakli yanlis alarm olmamali.

    Yeni bir dosya alarm verirse test kirilir; o zaman karar verilmeli:
    (a) gercek bir gelenek-terim kullanimi mi -> listeye gerekcesiyle
    eklenir, (b) yanlis pozitif mi -> tutarlilik_kontrolu.py'deki
    istisna listesi duzeltilir.
    """
    raw_data = Path(__file__).parent.parent / "scraper" / "raw_data"
    dosyalar = sorted(raw_data.glob("*/json/*.json"))
    assert len(dosyalar) >= 100, "beklenen fixture sayisi degisti, kontrol et"

    beklenmeyen_alarmlar = []
    for dosya in dosyalar:
        with open(dosya, encoding="utf-8") as f:
            kayit = json.load(f)
        metin = kayit.get("ham_metin") or ""
        sonuc = terminoloji_tutarliligini_kontrol_et(metin)
        if not sonuc["tutarli"] and not any(
            slug in dosya.stem for slug in ALARM_VERMESI_BEKLENEN_SAYFALAR
        ):
            beklenmeyen_alarmlar.append((dosya.name, sonuc["bulunan_sorunlar"]))

    assert beklenmeyen_alarmlar == [], (
        f"Beklenmeyen yanlis alarm(lar): {beklenmeyen_alarmlar}"
    )


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

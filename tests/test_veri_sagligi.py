"""Veritabanindaki kampanya verisi makul mu? (veri sagligi bekcisi)

--------------------------------------------------------------------------
NEDEN BU TEST VAR
--------------------------------------------------------------------------
DENETIM BULGUSU (25.08.2026): iki kayitta `vade_ay = 999` duruyordu. Bu
deger hicbir kaynak metinde gecmiyordu - `tests/test_regex_ile_zenginlestir
.py`'nin "mevcut dolu alani ezme" testinin SENTINEL degeriydi. Test onu
veritabanina yaziyor ama GERI ALMIYORDU (`finally` yalnizca oturumu
kapatiyordu), yani her test kosumu kalici bir kayit bozuyordu.

Bedeli olculdu: `en_uzun_vade` karsilastirmasinda "999 ay" EN USTTE
cikiyordu - juriye gosterilecek Sartname Md. 5.7 ekraninin lider satiri
sahteydi. Siralama ASC/DESC oldugu icin absurt degerler her zaman uca
gider; yani bu tur bir kirlilik en gorunur yerde patlar.

--------------------------------------------------------------------------
BU TEST NEYI KORUR
--------------------------------------------------------------------------
Kaynagi ne olursa olsun (test sentinel'i, hatali cikarim, elle mudahale)
veritabaninda FIZIKSEL OLARAK ANLAMSIZ bir deger birikirse yakalar.
Cikarimin DOGRULUGUNU olcmez - o baska testlerin isi; burada yalnizca
"bu sayi gercek dunyada mumkun mu" sorusu sorulur.

Canli PostgreSQL gerektirir; yoksa SKIP eder (CI'da beklenen durum,
test_kampanya_repository.py ile ayni desen).
"""

from __future__ import annotations

import pytest


def _db_erisilebilir_mi() -> bool:
    try:
        from api.db import engine

        with engine.connect():
            return True
    except Exception:  # noqa: BLE001 - erisilemiyorsa test atlanir
        return False


DB_YOK_MESAJI = (
    "Yerel PostgreSQL calismiyor (docker compose up -d postgres) - CI'da beklenen durum"
)

pytestmark = pytest.mark.skipif(not _db_erisilebilir_mi(), reason=DB_YOK_MESAJI)

# alan -> (alt_sinir, ust_sinir) - GERCEK DUNYA sinirlari, istatistiksel degil.
# Ust sinirlar cömert secildi: amac supheli veriyi degil, IMKANSIZ veriyi
# yakalamak. Dar bir aralik, gercek ama sira disi bir kampanyayi yanlislikla
# hata sayardi.
MAKUL_ARALIKLAR = {
    "kar_payi_orani_percent": (0, 100),
    "vade_ay": (1, 360),          # 30 yil - konut finansmaninin ustu
    "taksit_sayisi": (1, 36),
    "erteleme_suresi_ay": (1, 24),
    "nakit_iade_orani": (0, 100),
    "indirim_orani_percent": (0, 100),
}


@pytest.fixture(scope="module")
def kayitlar():
    from api.db import OturumYerel
    from api.models import Kampanya

    oturum = OturumYerel()
    try:
        tumu = oturum.query(Kampanya).all()
    finally:
        oturum.close()
    if not tumu:
        pytest.skip("Veritabaninda kayit yok - once postgrese_yukle.yukle() calistirilmali")
    return tumu


@pytest.mark.parametrize("alan", sorted(MAKUL_ARALIKLAR))
def test_sayisal_alanlar_makul_araliktadir(kayitlar, alan):
    """ASIL YAKALANAN HATA: vade_ay=999 (test sentinel'i DB'de kalmisti)."""
    alt, ust = MAKUL_ARALIKLAR[alan]
    kotu = [
        (k.id, getattr(k, alan))
        for k in kayitlar
        if getattr(k, alan, None) is not None and not (alt <= getattr(k, alan) <= ust)
    ]
    assert not kotu, (
        f"{alan} icin {alt}-{ust} disinda deger var: {kotu[:5]}. "
        "Kaynagi test sentinel'i olabilir - testlerin paylasilan veritabanina "
        "yazdigi degeri geri aldigindan emin olun."
    )


def test_tarih_mantigi_tutarli(kayitlar):
    """Baslangic, bitisten sonra olamaz."""
    ters = [
        (k.id, k.kampanya_baslangic, k.kampanya_bitis)
        for k in kayitlar
        if k.kampanya_baslangic and k.kampanya_bitis
        and k.kampanya_baslangic > k.kampanya_bitis
    ]
    assert not ters, f"baslangic > bitis olan kayitlar: {ters[:5]}"


def test_kimlik_alanlari_bos_degil(kayitlar):
    """banka / kampanya_adi / kaynak_url izlenebilirligin temelidir.

    Bunlar bossa kaydin kaynagi gosterilemez; rapor Bolum 9'un provenance
    iddiasi o kayit icin cokerdi.
    """
    eksik = [
        k.id for k in kayitlar
        if not (k.banka and k.kampanya_adi and k.kaynak_url)
    ]
    assert not eksik, f"kimlik alani bos olan kayitlar: {eksik[:5]}"


def test_kaynak_url_mukerrer_degil(kayitlar):
    """Ayni sayfa iki kayda bolunmus olmamali - yukleyici kaynak_url ile
    tekillestiriyor, mukerrer varsa o mantik kirilmis demektir."""
    gorulen: dict[str, int] = {}
    mukerrer = []
    for k in kayitlar:
        if k.kaynak_url in gorulen:
            mukerrer.append((gorulen[k.kaynak_url], k.id, k.kaynak_url))
        else:
            gorulen[k.kaynak_url] = k.id
    assert not mukerrer, f"mukerrer kaynak_url: {mukerrer[:3]}"


def test_durum_semadaki_degerlerden_biri(kayitlar):
    """Sutunda enum disi bir metin varsa /kampanyalar tumuyle 500 doner."""
    from api.schemas import YasamDongusu

    gecerli = {d.value for d in YasamDongusu}
    kotu = [(k.id, k.durum) for k in kayitlar if k.durum and k.durum not in gecerli]
    assert not kotu, f"gecersiz durum degeri: {kotu[:5]}"

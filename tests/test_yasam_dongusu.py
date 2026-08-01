"""storage/yasam_dongusu.py testleri (rehber Sprint 2 Gün 4).

KRITIK KURAL: Tarih bilgisi YOKSA sonuç 'BILINMIYOR' olmalı, 'EXPIRED'
DEĞİL - bilgi eksikliğini süresi dolmuş saymak şartnamenin şeffaflık
ilkesine (rapor Bölüm 5.7/15) aykırıdır ve gerçekte aktif olabilecek
kampanyaları kullanıcıdan saklar.
"""

from datetime import date

from storage.yasam_dongusu import durum_hesapla

BUGUN = date(2026, 8, 1)


def test_bitis_gecmisse_expired():
    sonuc = durum_hesapla(date(2026, 1, 1), date(2026, 7, 31), bugun=BUGUN)
    assert sonuc == "EXPIRED"


def test_bitis_bugunse_active():
    sonuc = durum_hesapla(date(2026, 1, 1), BUGUN, bugun=BUGUN)
    assert sonuc == "ACTIVE"


def test_bitis_gelecekteyse_active():
    sonuc = durum_hesapla(date(2026, 1, 1), date(2026, 12, 31), bugun=BUGUN)
    assert sonuc == "ACTIVE"


def test_baslangic_gelecekteyse_bilinmiyor():
    """Henuz baslamamis bir kampanya EXPIRED/ACTIVE degil, BILINMIYOR olmali."""
    sonuc = durum_hesapla(date(2026, 12, 1), date(2027, 1, 1), bugun=BUGUN)
    assert sonuc == "BILINMIYOR"


def test_baslamis_bitis_belirtilmemis_active():
    sonuc = durum_hesapla(date(2026, 1, 1), None, bugun=BUGUN)
    assert sonuc == "ACTIVE"


def test_hicbir_tarih_yoksa_bilinmiyor_expired_degil():
    """EN KRITIK TEST: sartname B/C Bankasi ornegindeki 'Kampanya Suresi:
    Belirtilmemis' durumu - EXPIRED sayilip gizlenmemeli."""
    sonuc = durum_hesapla(None, None, bugun=BUGUN)
    assert sonuc == "BILINMIYOR"
    assert sonuc != "EXPIRED"


def test_yalnizca_bitis_var_gecmisteyse_expired():
    sonuc = durum_hesapla(None, date(2026, 1, 1), bugun=BUGUN)
    assert sonuc == "EXPIRED"


def test_bugun_verilmezse_gercek_tarihi_kullanir():
    """bugun parametresi verilmezse date.today() kullanilmali - bariz
    gecmis bir tarih EXPIRED donmeli."""
    sonuc = durum_hesapla(date(2000, 1, 1), date(2000, 12, 31))
    assert sonuc == "EXPIRED"

"""Veritabanındaki tüm kampanyaların durum alanını günceller.

NEDEN GEREKLI: Veritabanına yazılırken durum hep "BILINMIYOR" olarak
kaydediliyor. Bu script tarihlerden durumu hesaplayıp günceller.
"""
from datetime import date

from api.db import oturum_al
from api.models import Kampanya
from storage.yasam_dongusu import durum_hesapla

def guncelle_tum_durumlar():
    """Tüm kampanyaların durum alanını tarihlerden hesaplayıp güncelle."""
    oturum = next(oturum_al())
    bugun = date.today()
    
    kampanyalar = oturum.query(Kampanya).all()
    
    print(f"Toplam {len(kampanyalar)} kampanya bulundu.")
    
    active_sayisi = 0
    expired_sayisi = 0
    bilinmiyor_sayisi = 0
    
    for kampanya in kampanyalar:
        eski_durum = kampanya.durum
        
        # Durumu hesapla
        yeni_durum = durum_hesapla(
            kampanya.kampanya_baslangic,
            kampanya.kampanya_bitis,
            bugun=bugun
        )
        
        # Eğer hesaplanan durum BILINMIYOR ise ama sutunda başka bir değer varsa onu koru
        if yeni_durum == "BILINMIYOR" and eski_durum and eski_durum != "BILINMIYOR":
            yeni_durum = eski_durum
        
        kampanya.durum = yeni_durum
        
        if yeni_durum == "ACTIVE":
            active_sayisi += 1
        elif yeni_durum == "EXPIRED":
            expired_sayisi += 1
        else:
            bilinmiyor_sayisi += 1
        
        if eski_durum != yeni_durum:
            print(f"  ID {kampanya.id}: {eski_durum} -> {yeni_durum} (Başlangıç: {kampanya.kampanya_baslangic}, Bitiş: {kampanya.kampanya_bitis})")
    
    oturum.commit()
    
    print(f"\n=== ÖZET ===")
    print(f"ACTIVE: {active_sayisi}")
    print(f"EXPIRED: {expired_sayisi}")
    print(f"BILINMIYOR: {bilinmiyor_sayisi}")
    print(f"\nVeritabanı güncellendi.")

if __name__ == "__main__":
    guncelle_tum_durumlar()

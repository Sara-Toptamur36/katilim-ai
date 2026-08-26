"""Qdrant indeksini güncelle - eksik belgeleri ekle."""
import sys
from chunking.indeksleyici import indeksle

print("=" * 80)
print("QDRANT İNDEKS GÜNCELLEME")
print("=" * 80)

print("\n⚠️  DİKKAT: Mevcut indeks SIFIRLANACAK ve tüm belgeler yeniden indekslenecek.")
print("Bu işlem birkaç dakika sürebilir.\n")

try:
    sonuc = indeksle(sifirla=True, ilerleme_yaz=True)
    
    print("\n" + "=" * 80)
    print("✅ İNDEKSLEME TAMAMLANDI")
    print("=" * 80)
    print(f"\n📊 SONUÇ:")
    print(f"   • Ham belge sayısı: {sonuc['belge_sayisi']}")
    print(f"   • Üretilen chunk sayısı: {sonuc['parca_sayisi']}")
    print(f"   • Qdrant'a yazılan: {sonuc['yazilan']}")
    print(f"   • Koleksiyondaki toplam: {sonuc['koleksiyondaki_kayit']}")
    print(f"\n⏱️  SÜRE:")
    print(f"   • Parçalama: {sonuc['sureler_sn']['parcalama']} sn")
    print(f"   • İndeksleme: {sonuc['sureler_sn']['indeksleme']} sn")
    print("\n✅ Qdrant indeksi güncel!")
    print("=" * 80)
    
except Exception as e:
    print(f"\n❌ HATA: {e}")
    print("\nQdrant çalışıyor mu kontrol edin:")
    print("  docker compose ps")
    print("\nQdrant'ı başlatmak için:")
    print("  docker compose up -d qdrant")
    sys.exit(1)

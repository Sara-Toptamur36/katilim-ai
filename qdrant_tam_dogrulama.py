"""Qdrant durumunu TAM olarak doğrula ve 513 vs 623 farkını analiz et."""
import json
from pathlib import Path
from chunking.indeksleyici import ham_kayitlari_yukle
from chunking.parcalayici import kayitlari_parcala
from chunking.qdrant_baglanti import koleksiyon_sayisi, VARSAYILAN_KOLEKSIYON, qdrant_hazir_mi

print("=" * 80)
print("QDRANT DURUM DOĞRULAMA VE 513 vs 623 ANALİZİ")
print("=" * 80)

# 1. QDRANT DURUM KONTROLÜ
print("\n1. QDRANT BAĞLANTI KONTROLÜ")
print("-" * 80)
qdrant_ok = qdrant_hazir_mi()
print(f"Qdrant hazır mı: {'✅ EVET' if qdrant_ok else '❌ HAYIR'}")

if not qdrant_ok:
    print("\n❌ QDRANT ÇALIŞMIYOR!")
    print("Başlatmak için: docker compose up -d qdrant")
    exit(1)

# 2. KOLEKSIYON DURUM KONTROLÜ
print("\n2. KOLEKSIYON DURUMU")
print("-" * 80)
chunk_sayisi = koleksiyon_sayisi(VARSAYILAN_KOLEKSIYON)
print(f"Koleksiyon adı: {VARSAYILAN_KOLEKSIYON}")
print(f"Chunk sayısı: {chunk_sayisi}")

# 3. HAM KORPUS ANALİZİ (GERÇEK KAYNAK)
print("\n3. HAM KORPUS ANALİZİ (scraper/raw_data/*/json/*.json)")
print("-" * 80)

RAW_DATA = Path("scraper/raw_data")
banka_detay = {}
toplam_dosya = 0
basarili_yukle = 0
basarisiz_yukle = 0

for banka_dir in sorted(RAW_DATA.iterdir()):
    if banka_dir.is_dir():
        json_dir = banka_dir / "json"
        if json_dir.exists():
            json_files = list(json_dir.glob("*.json"))
            dosya_sayisi = len(json_files)
            
            # Her bankadan kaç tanesinin başarıyla yüklendiğini kontrol et
            yuklenebilen = 0
            for f in json_files:
                try:
                    with open(f, encoding="utf-8") as jf:
                        json.load(jf)
                    yuklenebilen += 1
                except:
                    pass
            
            banka_detay[banka_dir.name] = {
                'toplam_dosya': dosya_sayisi,
                'yuklenebilen': yuklenebilen,
                'basarisiz': dosya_sayisi - yuklenebilen
            }
            toplam_dosya += dosya_sayisi
            basarili_yukle += yuklenebilen
            basarisiz_yukle += (dosya_sayisi - yuklenebilen)

print(f"Toplam JSON dosyası: {toplam_dosya}")
print(f"Başarıyla yüklenen: {basarili_yukle}")
print(f"Başarısız/bozuk: {basarisiz_yukle}")
print(f"\nBanka bazlı detay:")
for banka, detay in sorted(banka_detay.items()):
    print(f"  {banka:20s}: {detay['toplam_dosya']:3d} dosya → {detay['yuklenebilen']:3d} yüklendi" + 
          (f" ({detay['basarisiz']} BOZUK)" if detay['basarisiz'] > 0 else ""))

# 4. INDEKSLEYICI FONKSIYONU ILE KONTROL
print("\n4. İNDEKSLEYİCİ FONKSİYONU KONTROLÜ")
print("-" * 80)
kayitlar = ham_kayitlari_yukle()
print(f"ham_kayitlari_yukle() sonucu: {len(kayitlar)} kayıt")

# 5. PARCALAMA KONTROLÜ
print("\n5. PARCALAMA ANALİZİ")
print("-" * 80)
parcalar = kayitlari_parcala(kayitlar)
print(f"Üretilen chunk sayısı: {len(parcalar)}")
print(f"Ortalama chunk/belge: {len(parcalar)/len(kayitlar):.2f}")

# 6. "513 BELGE" NEREDEN GELDİ?
print("\n6. '513 BELGE' KAYNAĞINI ARAMA")
print("-" * 80)

# Logs klasöründe eski rapor var mı?
logs_dir = Path("logs")
if logs_dir.exists():
    for log_file in logs_dir.glob("*.json"):
        try:
            with open(log_file, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    belge = data.get('belge_sayisi', data.get('belge', None))
                    if belge and belge == 513:
                        print(f"  ✅ BULUNDU: {log_file.name}")
                        print(f"     Tarih: {data.get('kuruldu', 'N/A')}")
                        print(f"     Belge: {belge}")
                        print(f"     Chunk: {data.get('parca_sayisi', 'N/A')}")
        except:
            pass

# gold_dataset klasöründe eski manifest var mı?
manifest_files = [
    "gold_dataset/split_manifest_v1.json",
    "gold_dataset/kaynak_tazeleme_raporu.json"
]
for manifest in manifest_files:
    if Path(manifest).exists():
        try:
            with open(manifest, encoding="utf-8") as f:
                data = json.load(f)
                # Herhangi bir yerde 513 sayısı var mı?
                if "513" in str(data) or (isinstance(data, dict) and any(v == 513 for v in data.values() if isinstance(v, int))):
                    print(f"  ⚠️  {manifest} içinde 513 referansı bulundu")
        except:
            pass

# 7. SENKRONIZASYON DURUMU
print("\n7. SENKRONIZASYON DURUMU")
print("-" * 80)
print(f"Ham korpus (kaynak): {len(kayitlar)} belge")
print(f"Üretilen chunk: {len(parcalar)} chunk")
print(f"Qdrant'taki chunk: {chunk_sayisi} chunk")

senkron = (len(parcalar) == chunk_sayisi)
print(f"\nDurum: {'✅ SENKRON' if senkron else '❌ SENKRON DEĞİL'}")

if not senkron:
    fark = abs(len(parcalar) - chunk_sayisi)
    print(f"Fark: {fark} chunk")
    print(f"\n⚠️  DİKKAT: Qdrant yeniden indekslenme li!")
    print("Komut: python qdrant_guncelle.py")
else:
    print("\n✅ Qdrant tamamen güncel!")

# 8. SONUÇ RAPORU
print("\n" + "=" * 80)
print("📊 SONUÇ RAPORU")
print("=" * 80)

print(f"""
MEVCUT DURUM:
  • Ham korpus: {len(kayitlar)} belge
  • Üretilen chunk: {len(parcalar)} chunk
  • Qdrant chunk: {chunk_sayisi} chunk
  • Durum: {'✅ DOĞRU' if senkron else '❌ YANLIŞ'}

513 vs {len(kayitlar)} FARKI:
  • Fark: {len(kayitlar) - 513} belge
  • Muhtemel sebep: {'Yeni scraping yapıldı, ham korpus büyüdü' if len(kayitlar) > 513 else 'Veri silindi veya eski rapor'}

DOĞRU SAYI HANGISI?
  • DOĞRU: {len(kayitlar)} belge (mevcut ham korpus)
  • 513: {'ESKİ değer - eski rapor/manifest' if len(kayitlar) != 513 else 'GÜNCEL'}

SORUN ÇÖZÜLDÜ MÜ?
  • {'✅ EVET - Qdrant güncel ve senkron' if senkron else '❌ HAYIR - Yeniden indeksleme gerekli'}
""")

print("=" * 80)

# Detaylı rapor kaydet
rapor = {
    "tarih": "2026-08-26",
    "qdrant_hazir": qdrant_ok,
    "koleksiyon": VARSAYILAN_KOLEKSIYON,
    "ham_korpus_belge": len(kayitlar),
    "uretilen_chunk": len(parcalar),
    "qdrant_chunk": chunk_sayisi,
    "senkron": senkron,
    "banka_detay": banka_detay,
    "toplam_dosya": toplam_dosya,
    "basarili_yukle": basarili_yukle,
    "basarisiz_yukle": basarisiz_yukle
}

with open('qdrant_dogrulama_raporu.json', 'w', encoding='utf-8') as f:
    json.dump(rapor, f, ensure_ascii=False, indent=2)

print("📄 Detaylı rapor: 'qdrant_dogrulama_raporu.json'")

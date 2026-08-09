# Donanım Tanılama Raporu

**Makine:** Zeynep'in geliştirme makinesi (Windows 11, RTX 4060 Laptop GPU)
**Tarih:** 9 Ağustos 2026
**Amaç:** `donanim_testi.py`'nin ürettiği ham çıktı + bulguların yorumu — Sara'nın
kendi makinesi bu testi tamamlayamadığı için, GPU'lu bir makinede alınan referans
ölçüm olarak paylaşılıyor.

## Ham çıktı

```
==============================================================
1) DONANIM
==============================================================
  Isletim sistemi : Windows 11
  Python          : 3.13.2

=== KatilimAI donanim profili ===
GPU                  : NVIDIA GeForce RTX 4060 Laptop GPU (8188 MB VRAM)
CPU cekirdek         : 28
Secilen profil       : gpu
  gerekce            : Model VRAM'e sigiyor. Genis baglam penceresi kullanilir - hicbir belge kirpilmaz; cikarim hizli oldugu icin zaman asimi kisaltilir.

LLM baglam penceresi : 16384
LLM zaman asimi      : 300 sn
Embedding yigin      : 128

==============================================================
2) SERVISLER
==============================================================
  Qdrant      : KAPALI  -> docker compose up -d qdrant
  Ollama      : CALISIYOR
  PostgreSQL  : KAPALI  -> docker compose up -d postgres

==============================================================
3) EMBEDDING HIZI
==============================================================
  ilk cagri (model yuklemesi dahil) :  221.7 sn
  20 metin (toplu)                  :    1.5 sn
  parca basina                      :   0.07 sn
  ~734 parcalik tam indeksleme tahmini: 1 dakika

==============================================================
4) LLM HIZI (Ollama)
==============================================================
  test metni: 513 token (baglam=16384, girdi siniri=15284)
  sure                              :   10.4 sn
  cikarilan alanlar                 : HICBIRI
  UYARI: hicbir alan cikarilamadi - zaman asimi ya da baglam sorunu olabilir

==============================================================
5) DEGERLENDIRME
==============================================================
  Bu makine GUCLU profilde (NVIDIA GeForce RTX 4060 Laptop GPU, 8188 MB VRAM).
  Juri demosu icin uygun; tum belgeler kirpilmadan islenir.
```

## Yorum (script'in kendisinin bilemeyeceği bağlam)

**Docker kurulu değil** — Qdrant/PostgreSQL "KAPALI" görünüyor, bu makine
seçimiyle ilgili, kod hatası değil.

**Embedding:** ilk çağrı 221,7sn sürdü — bu model indirme/yükleme maliyeti
(HuggingFace'ten `intfloat/multilingual-e5-base`, tek seferlik). Sonrasında
parça başına ~0,07sn — tüm 734 parçalık indeks ~1 dakikada çıkar. Hızlı.

**LLM: "HİÇBİRİ" uyarısı yanıltıcı olabilir — kontrol ettim.** Script'in seçtiği
örnek metin, Albaraka'nın **"98/2 paylaşım oranlı" bir katılma hesabı**
kampanyasıydı (bkz. `scraper/raw_data/albaraka/json/20260731_..._10.json`).
İstenen 3 alan için gerçek durum:

- `vade_ay`, `finansman_tutari`: bu bir **mevduat/katılma hesabı**, finansman
  ürünü değil — bu alanlar kaynakta zaten **yok**. Boş dönmesi doğru davranış,
  hata değil.
- `kar_payi_orani_percent`: burada gerçek ve ilginç bir bulgu var. Metin oranı
  **"98/2" formatında** veriyor, yüzde işareti yok — tam olarak şartnamenin
  Md. 5.2'de kendi örneği olarak verdiği "farklı ifade biçimi" durumu ("98/2
  kâr paylaşım oranı — yüzde değil, bambaşka bir gösterim"). LLM bunu
  yakalayıp dönüştürememiş. **Bu, donanımla ilgili değil, gerçek bir çıkarım
  kapsamı boşluğu** — Yağmur'a iletilecek somut bir örnek.

**Sonuç:** Bu makine GPU profilinde, jüri demosu için uygun. LLM hızı iyi
(10,4sn/çağrı). Asıl aksiyon maddesi donanım değil: "98/2" gibi oran
formatlarının çıkarım katmanına eklenmesi.

# Kapsam ve Veri Ayrımı

**Amaç:** Bu depodaki her veri kümesinin *ne olduğunu*, *nerede durduğunu* ve
*hangi testin bunu kanıtladığını* tek yerde göstermek.

Gerekçe basit: "kapsam dışı veriyi ürün verisine karıştırmadık" bir **iddiadır**.
Bir klasör adı da iddiadır. Kanıt, her push'ta çalışan bir testtir. Bu belge
iddiaları testlere bağlar.

---

## 1. Veri kümeleri

| Küme | Yer | Ne içerir | Üretim akışına girer mi? |
|---|---|---|---|
| **Ham kampanya metinleri** | `scraper/raw_data/<banka>/{raw,json}/` | 9 katılım bankasının kendi sayfalarından toplanan kampanya metinleri, kaynak URL ve tarihiyle | ✅ Evet — çıkarımın girdisi |
| **Altın Veri Seti** | `gold_dataset/altin_veri_seti.{json,xlsx}` | Elle doğrulanmış 58 referans kayıt (+ ekran görüntüsü kanıtı) | ⚠️ Yalnızca **ölçüm** — motorun çıktısı buradan doldurulmaz |
| **Terminoloji sözlüğü** | `terminology/sozluk.json` | 31 katılım bankacılığı kavramı, geleneksel karşılığı ve tanım kaynağı | ✅ Evet — Sözlük aracı ve terminoloji kontrolü |
| **Kapsam dışı karşı-örnekler** | `tests/veri/kapsam_disi/` | 24 geleneksel bankacılık ifadesi + 10 meşru katılım ifadesi + 1 bilinen sınırlama | ❌ **Hayır** — yalnızca ölçüm |

### Ham veri dağılımı (263 kayıt / 9 banka)

| Banka | Kayıt |
|---|---|
| Türkiye Emlak Katılım | 100 |
| Ziraat Katılım | 90 |
| Albaraka Türk | 16 |
| Türkiye Finans | 16 |
| Kuveyt Türk | 13 |
| Hayat Finans | 12 |
| Dünya Katılım | 10 |
| T.O.M. Katılım | 3 |
| Vakıf Katılım | 3 |

BDDK listesindeki 10. kuruluş (Adil Katılım) gerekçeli olarak hariçtir — ürün
ve kampanya yayımlamıyor. Kapsam kararı README'de ve
[`docs/sayfa_takip_tablosu.md`](sayfa_takip_tablosu.md)'de belgelidir.

---

## 2. Kapsam dışı karşı-örnek seti

### Neden var?

Şartname Md. 5.5, modelin katılım bankacılığına özgü kavramları geleneksel
bankacılıktan **ayırt edebilmesini** istiyor. Bir yeteneği iddia etmek yetmez,
ölçmek gerekir. Ölçmek için de sistemin *yanlış* cevap vermesi gereken örnekler
lazım.

### Neden veri toplamadık?

Şartname Md. 5.1 veri setini şöyle tanımlıyor:

> *"Veri seti BDDK'nın resmî web sitesinde yer alan Katılım Bankacılığı alanında
> faaliyet gösteren kuruluşların tümünü içermelidir."*

Geleneksel bankalar bu listede değil. Dolayısıyla geleneksel banka verisi
**toplanmamıştır**. Kavram farkını ölçmek için veri toplamak gerekmez; ölçüm
verisi yeterlidir.

### Nasıl üretildi?

İfadeler **elle yazılmıştır**. Hiçbiri gerçek bir bankanın sayfasından
kopyalanmamış, hiçbiri gerçek bir bankaya atfedilmemiştir. Bu bilinçli bir
tercihtir: gerçek bir bankaya ait olmayan bir cümleyi o bankaya atfetmek,
projenin kaynak dürüstlüğü ilkesiyle çelişirdi.

Üretim yöntemi, veri dosyasının kendi içinde `_uretim_yontemi` alanında da
yazılıdır.

### İki yönlü ölçüm

Set bilerek iki gruptan oluşur, çünkü **tek yön ölçmek yanıltıcıdır**:

| Grup | Sayı | Beklenen davranış | Ölçtüğü şey |
|---|---|---|---|
| `karsi_ornekler` | 24 | Yakalanmalı ve doğru karşılık önerilmeli | **Hassasiyet** — kaçırma var mı? |
| `mesru_kullanimlar` | 10 | Yakalanmamalı | **Özgüllük** — yanlış alarm var mı? |
| `bilinen_sinirlamalar` | 1 | Yakalanmıyor, gerekçesi yazılı | Kararın dondurulması |

Yalnızca hassasiyet ölçülseydi, "her cümleyi işaretle" diyen bir kontrol %100
alırdı. Yalnızca özgüllük ölçülseydi, "hiçbir şeyi işaretleme" diyen bir kontrol
%100 alırdı. İkisi birlikte anlamlıdır — bu, çıkarım tarafındaki *"dolu alan /
boş alan doğruluğu"* ikilisinin terminoloji karşılığıdır.

**Güncel sonuç: hassasiyet 24/24 (%100), özgüllük 10/10 (%100).**

### Meşru kullanımlar nereden geldi?

Özgüllük grubu uydurulmadı; **gerçek katılım bankası verisinde doğrulanmış**
ifadelerden seçildi:

- `faizsiz` — katılım bankaları kendilerini böyle tanımlar
- `kredi kartı` — yerleşik ürün adı, katılım bankaları da kullanır
- `kredi skoru`, `kredi politikası` — sektör-standart; Albaraka, Vakıf Katılım
  ve Türkiye Finans sayfalarında görülmüştür
- `açık kredi`, `veresiye kredi` — T.O.M. Katılım sayfasında geçen meşru bileşikler
- `kredi bakiyesi` — kart ekosisteminde yerleşik jargon (Altın Veri Seti TOM-002)

Bu yüzden özgüllük testi gerçek bir regresyon kilididir: biri istisna listesini
daraltırsa, gerçek banka metinlerinde yanlış alarm başlar ve test kırılır.

### Bilinen sınırlama

Bir ifade (`BS-001`) geleneksel bankacılıktır ama kontrol onu **bilerek
yakalamıyor**. Sebebi ve neden düzeltilmediği veri dosyasında yazılıdır; bir test
bu kararı dondurur. Yeşil kalması "sorun yok" demek değil, "bilinen sınırlama hâlâ
aynı yerde" demektir. Biri istisnayı daraltırsa test kırılır ve karar yeniden
tartışılmış olur.

---

## 3. Ayrımın kanıtı

| İddia | Kanıt |
|---|---|
| Karşı-örnekler ürün verisine karışmadı | `tests/test_karsi_ornekler.py::test_karsi_ornekler_veritabanina_girmemis` — `scraper/raw_data` ve `gold_dataset` içindeki tüm JSON dosyalarını tarar, karşı-örnek ifadelerinden birini bulursa test kırılır |
| Altın veri seti motorun çıktısından doldurulmadı | `tests/test_gold_etiketleme.py` — etiketleme yardımcısının `extraction` modülünü **import etmediğini** `ast` ile denetler |
| Sistem geleneksel ifadeleri ayırt ediyor | `tests/test_karsi_ornekler.py` — 24 + 10 parametreli test |
| Ölçüm özeti görünür | `pytest tests/test_karsi_ornekler.py -s` çıktısında hassasiyet/özgüllük satırı basılır |

Bu testler CI'da her push'ta çalışır.

---

## 4. Neden dizin yapısını yeniden düzenlemedik

Bir öneri olarak `training/` ve `production/` diye üst düzey ayrım gündeme geldi.
Uygulanmadı, iki gerekçeyle:

1. **`training/` dizini açmak, eğitim yapmadığımız hâlde eğitim yapıyormuş
   izlenimi verir.** Bu depoda fine-tuning yoktur. Boş bir `training/` dizini,
   README ile kodun farklı şey söylediği duruma örnek olurdu — ki kaçınmaya
   çalıştığımız şey tam olarak budur.
2. **Klasör adı bir iddiadır, test bir kanıttır.** Ayrımı adlandırmak yerine
   *doğrulamayı* seçtik. Karşı-örnek verisi `tests/veri/kapsam_disi/` altındadır:
   konumu (test klasörü) ve adı (kapsam dışı) birlikte kendini anlatır, ama
   güvence adından değil testten gelir.

---

## 5. Şu an kapsam dışı olanlar

| Veri | Durum | Gerekçe |
|---|---|---|
| Geleneksel banka ürün/kampanya verisi | Toplanmadı | Şartname Md. 5.1 veri setini katılım bankalarıyla sınırlar |
| Sentetik kampanya verisi | Üretilmedi | Tek kaynak türü tutmak, kaynak güveni sorununu kaynağında ortadan kaldırır |

Bu tablo, kapsam değiştikçe güncellenmelidir. Yeni bir veri türü sisteme
girecekse, girmeden önce buraya bir satır ve ona karşılık gelen bir ayrım testi
eklenmelidir.

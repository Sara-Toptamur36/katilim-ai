# `kampanya_turu` Sınıflandırıcısı — Ölçüm ve Karar Raporu

**Tarih:** 25 Ağustos 2026
**Ölçüm kümesi:** Altın Veri Seti — 288 kayıt (imzalı **ve** sitede hâlâ canlı)
**Araç:** `python -m scraper.scripts.extraction_accuracy`
**Değişen dosya:** `extraction/regex_extractor.py`

---

## 1. Neden bu çalışma yapıldı

Veritabanındaki 436 kampanyanın 56'sında `kampanya_turu` boştu. Bunlar bayat veri
değildi — güncel motor da hepsinde `None` dönüyordu, yani gerçek bir kapsam açığıydı.

Ancak **körlemesine anahtar kelime eklenemezdi**: `KAMPANYA_TURU_ANAHTAR_KELIMELERI`
sözlüğünde ilk eşleşen etiket kazanır, dolayısıyla bir türü düzelten değişiklik
başka bir türü sessizce bozabilir. Bu yüzden önce **taban ölçüldü**, sonra her aday
tek tek ölçüldü, F1'i düşüren hiçbir aday alınmadı.

---

## 2. Taban ölçüm (değişiklik öncesi)

```
alan                       destek   TP   FP   FN      P%      R%     F1%
kampanya_turu                 288  117  123  171   48.75   40.62   44.32
```

Hata dökümü — **171 FN'nin yalnızca 48'i "hiç etiket üretilmedi"**, kalan
**123'ü YANLIŞ etiket**. Yani asıl sorun boş bırakma değil, yanlış sınıflandırmaydı.

### Karışıklık matrisi (gold → motor), en sık 6

| Adet | Gold etiketi | Motorun dediği |
|---:|---|---|
| 38 | Kart Kampanyasi | *(None)* |
| **36** | **Kart Kampanyasi** | **Konut Finansmani Kampanyasi** |
| 18 | Kart Kampanyasi | Alisveris Puani Kampanyasi |
| 16 | Ticari Kampanya | Kart Kampanyasi |
| 7 | Yeni Musteri Kampanyasi | Kart Kampanyasi |
| 6 | Yeni Musteri Kampanyasi | Konut Finansmani Kampanyasi |

---

## 3. Kök neden: hata anahtar kelimede değil, GİRDİ METNİNDE

36 kayıtta `"konut finansman"` anahtarı kampanya metninden değil **sayfanın alt
menüsünden** eşleşiyordu:

```
... | finansmanlar | sigortalar | altin bankaciligi | konut finansmani | arac finansmani | ...
```

Bu 36 kaydın hepsi gerçekte kart kampanyasıydı. Menü her sayfada aynen durduğu için
**hangi anahtar eklenirse eklensin** menü ilk eşleşmeyi kazanmaya devam edecekti —
yani sözlüğe dokunmak bu hatayı asla çözemezdi.

İkinci bulgu: gold kümesinde **hiç "Konut Finansmani Kampanyasi" etiketi yok**
(0 kayıt), buna karşılık motor bu etiketi 52 kez üretiyordu. Sınıfın tamamı yanlış
pozitif üretiyordu.

Ayırt edici özellik: menü satırları **kısa, bağımsız bağlantı etiketleridir**;
noktalama ve rakam taşımazlar. Kampanya gövde cümleleri
("…toplamda 12.500 TL harcama şartı aranır.") her ikisini de taşır.

---

## 4. Kullanıcının uyarısı ölçüldü: "paraf eklersen parafpara'yı çalar"

**Ölçüm bu endişeyi doğrulamadı — durum tam tersiydi.**

Sözlükte `"Kart Kampanyasi"` **zaten** `"Alisveris Puani Kampanyasi"`ndan **önce**
geliyor, ilk eşleşme kazandığı için Kart tarafına eklenen bir anahtar puan
kampanyalarını çalamaz. Ölçülen gerçek durum bunun aynası:

| Etiket | Gold'daki kayıt | TP | **FP** |
|---|---:|---:|---:|
| Alisveris Puani Kampanyasi | 2 | 1 | **36** |

`"parafpara"` anahtarı, gold'da **Kart Kampanyasi** etiketli 35 kaydı çalıyordu.
Yani çalınan taraf ParafPara değil, ParafPara'nın çaldığı taraf Kart'tı.

Kontrol ölçümü: `"parafpara"` anahtarını `Alisveris Puani`den **çıkarmak F1'i hiç
değiştirmedi** (73,72 → 73,72). Bu yüzden **çıkarılmadı** — sıralama zaten koruma
sağlıyor ve anahtar gerçek bir puan kampanyasında hâlâ tek sinyal olabilir.

> Not — gold etiket tutarsızlığı: geriye kalan 2 "Alisveris Puani" kaydı (DK-006,
> DK-007) metninde **hiç puan geçmeyen**, mağaza iş birlikli taksit kampanyalarıdır.
> 35 ParafPara kaydı "Kart Kampanyasi" etiketlenirken bu ikisinin "Alisveris Puani"
> etiketlenmesi bir etiketleme tutarsızlığıdır. Ölçümü bozmamak için gold'a
> **dokunulmadı** — bu, `docs/gold_etiket_inceleme.md` kapsamında ayrıca ele alınmalı.

---

## 5. Denenen adaylar ve ölçüm sonuçları

Ablasyon — üç değişiklik ayrı ayrı ve birlikte:

| # | Aday | TP | FP | FN | P% | R% | **F1%** | Δ |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A0 | **TABAN** (değişiklik yok) | 117 | 123 | 171 | 48,75 | 40,62 | **44,32** | — |
| 1 | Yalnız menü bastırma | 137 | 89 | 151 | 60,62 | 47,57 | 53,31 | +8,99 |
| 2 | Yalnız sıralama (Kart en öne) | 136 | 104 | 152 | 56,67 | 47,22 | 51,52 | +7,20 |
| 3 | Yalnız yeni Kart anahtarları | 159 | 109 | 129 | 59,33 | 55,21 | 57,19 | +12,87 |
| 4 | Menü bastırma + sıralama | 135 | 91 | 153 | 59,73 | 46,88 | 52,53 | +8,21 |
| **5** | **Menü bastırma + anahtar (sıralama YOK)** | 201 | 64 | 87 | 75,85 | 69,79 | **72,69** | **+28,37** |
| 6 | Sıralama + anahtar (menü bastırma YOK) | 194 | 74 | 94 | 72,39 | 67,36 | 69,78 | +25,46 |
| 7 | Üçü birden | 199 | 66 | 89 | 75,09 | 69,10 | 71,97 | +27,65 |

**Sıralama değişikliği ALINMADI.** Tek başına +7,20 kazandırıyor ama bunu kök nedeni
(menü kirliliği) örterek yapıyor; menü bastırma açıkken ise F1'i **düşürüyor**
(72,69 → 71,97). Menü kirliliği giderildiğinde sıralamaya gerek kalmıyor.

### Kart anahtar kelimelerinin tek tek katkısı

Menü bastırma açık, sıralama sabit. Referans: yeni anahtar yok → F1 53,31.

| Eklenen anahtar (tek başına) | F1% | Δ |
|---|---:|---:|
| `kartla` | 72,32 | +19,01 |
| `paraf` | 71,64 | +18,33 |
| `kart ile` | 57,90 | +4,59 |
| `kart sahip` | 55,38 | +2,07 |
| `kartınız` | 55,28 | +1,97 |

Set karşılaştırması:

| Set | P% | R% | **F1%** |
|---|---:|---:|---:|
| **`kartla` + `kart sahip`  ← SEÇİLEN** | 77,69 | 70,14 | **73,72** |
| `kartla` + `kart sahip` + `kartınız` | 77,48 | 70,49 | 73,82 |
| `kartla` + `kart sahip` + `paraf` | 77,31 | 69,79 | 73,36 |
| 5'li set (hepsi) | 75,85 | 69,79 | 72,69 |
| yalnız `kart` (en genel) | 73,61 | 68,75 | 71,10 |

**`paraf` eklenmedi.** Tek başına güçlü ama nihai sette F1'i düşürüyor (−0,36);
`kartla` aynı kayıtları zaten yakalıyor ve markaya bağımlı değil.
**`kartınız` eklenmedi.** Kazancı +0,10 — 288 kayıtta tek bir kaydın gürültüsü;
bu büyüklükte bir farkı kural eklemek için gerekçe saymıyoruz.

### Menü eşiği duyarlılığı (aşırı uydurma kontrolü)

| Eşik (karakter) | 30 | **40** | 50 | 60 |
|---|---:|---:|---:|---:|
| F1% | 73,36 | **73,72** | 73,72 | 73,36 |

Sonuç geniş bir platoda sabit — tek bir sayıya ayarlanmış kırılgan bir kural değil.

---

## 6. `Finansman Kampanyasi` en sonda mı olmalı? (doğrulandı)

Kullanıcının sorduğu soru: tek anahtarı `"finansman"` ve çok genel; son sırada
olması kasıtlı mı, kaza mı?

| Konum | **F1%** |
|---|---:|
| **En sonda (mevcut) ← korundu** | **73,72** |
| Finansman türlerinden hemen sonra | 62,41 |
| En önde | 60,95 |
| Sınıf tamamen kaldırılsa | 73,84 |

**Son sırada olması taşıyıcıdır** — öne alınması 12,77 puan kaybettirir. Sınıfın
tamamen kaldırılması +0,12 verir; 6 destekli bir sınıfta bu gürültü düzeyindedir ve
`api/schemas.py::KampanyaTuru` enum üyesi olduğu için **kaldırılmadı**.

---

## 7. Uygulanan değişiklik

`extraction/regex_extractor.py`, iki nokta:

1. **`menu_satirlarini_ayikla()`** — yeni. Kısa (≤40 karakter) **ve** noktalama/rakam
   içermeyen satırları sınıflandırma metninden çıkarır. Yalnızca
   `_kampanya_turunu_tespit_et` çağırır; tutar/tarih/oran desenleri **ham metin**
   üzerinde çalışmaya devam eder (gereksiz regresyon riski alınmadı).
2. **`KAMPANYA_TURU_ANAHTAR_KELIMELERI["Kart Kampanyasi"]`** — `"kartla"` ve
   `"kart sahip"` eklendi. Alt-dize eşleşmesi kullanıldığı için `"kartla"` aynı
   zamanda `kartlar` / `kartları` / `kartlarla` biçimlerini de kapsar; bu kasıtlıdır.

Sözlük **sırası değiştirilmedi**, hiçbir anahtar **silinmedi**.

---

## 8. Sonuç — tam ölçüm, değişiklik öncesi/sonrası

```
                          ÖNCE                          SONRA
1) Dolu alan doğruluğu  : %49.63 (602/1213)   →   %56.64 (687/1213)
2) Boş alan doğruluğu   : %94.13 (1635/1737)  →   %94.13 (1635/1737)   [değişmedi]
   Makro F1             : %60.38              →   %63.06
```

| Alan | Önce F1% | Sonra F1% | Δ |
|---|---:|---:|---:|
| **kampanya_turu** | **44,32** | **73,72** | **+29,40** |
| kampanya_bitis | 67,80 | 67,80 | 0 |
| hedef_kitle | 14,16 | 14,16 | 0 |
| kampanya_baslangic | 30,43 | 30,43 | 0 |
| taksit_sayisi | 76,45 | 76,45 | 0 |
| odul_miktari | 81,28 | 81,28 | 0 |
| odul_birimi | 79,14 | 79,14 | 0 |
| finansman_tutari | 48,00 | 48,00 | 0 |
| kar_payi_orani_percent | 63,16 | 63,16 | 0 |
| erteleme_suresi_ay | 88,89 | 88,89 | 0 |
| vade_ay | 70,59 | 70,59 | 0 |

**Hiçbir alan gerilemedi.** Diğer alanların satırları birebir aynı — menü
bastırmanın kapsamı bilerek yalnızca `kampanya_turu` ile sınırlı tutulduğu için.

### Boş (`None`) kalan kayıtlar — tüm scrape korpusu (513 sayfa)

| | TABAN | Sonra |
|---|---:|---:|
| `kampanya_turu` boş | 77 | **43** |
| yanlış "Konut Finansmani" | 79 | **4** |

Kullanıcının verdiği örnek kampanyalar (doğrulandı):

| Kampanya | Önce | Sonra |
|---|---|---|
| Paraf ile A101'de Vade Farksız 6 Aya Varan Taksit | *(None)* | Kart Kampanyasi |
| Paraf ile Dyson'da 9 Aya Varan Taksit | *(None)* | Kart Kampanyasi |
| Biletinial'da %20 İndirim | *(None)* | Kart Kampanyasi |
| Kahve Keyfiniz Albaraka'dan | *(None)* | *(None)* |

---

## 9. Bilerek yapılmayanlar

- **Kalan 43 boş kayıt** ağırlıkla Albaraka'nın GastroClub/mobil uygulama üzerinden
  verilen mağaza indirimleridir; metinlerinde kart ürününden **hiç söz edilmez**.
  Bunlara "Kart Kampanyasi" demek kanıtsız bir iddia olurdu. Doğru çözüm
  `KampanyaTuru` enum'una bir **"Mağaza İş Birliği / Ayrıcalık Kampanyası"** sınıfı
  eklemektir — bu bir şema değişikliğidir ve Havin/Sara ile sözleşme konuşması ister.
- **Ölçüm tavanı:** gold'da enum'da bulunmayan 39 etiket var — Ticari Kampanya (18),
  Musteri Ol (9), Belirlenemedi (4), Sigorta/BES (2), Katilma Hesabi (2),
  Yatirim Kampanyasi (2), POS (2). Motor bunları **tanım gereği** hiç bulamaz;
  ulaşılabilir maksimum recall ≈ %86,5. Kalan 86 FN'nin 39'u budur.
- **Gold etiket düzeltmesi yapılmadı** (bkz. §4 notu). Ölçümü kendi lehine
  düzeltmek, ölçümün anlamını yok eder.

---

## 10. Bu çalışmayla ilgisi olmayan, açık kalan kırmızı test

`tests/test_regex_extractor_duzeltmeler.py::test_sayisal_cekirdek_alanlarda_dogruluk_esigin_altina_dusmez`
**şu anda kırmızı** — ama bu **değişiklikten önce de kırmızıydı**.

Doğrulama yöntemi: eski sınıflandırıcı (menü ayıklama yok + eski Kart anahtarları)
çalışma anında geri takılıp ölçüm yeniden koşuldu:

```
DEĞİŞİKLİK ÖNCESİ  kampanya_turu F1            : 44,32
DEĞİŞİKLİK ÖNCESİ  sayısal çekirdek makro F1   : 72,50   (test eşiği 75,0)
DEĞİŞİKLİK SONRASI sayısal çekirdek makro F1   : 72,50   (birebir aynı)
```

Sayısal çekirdek yedi alanın hiçbiri bu değişiklikten etkilenmiyor (menü ayıklamanın
kapsamı bilerek yalnızca `_kampanya_turunu_tespit_et` ile sınırlı). En zayıf halka
`finansman_tutari`: 20 destekte 18 yanlış pozitif, P %40,00 / F1 %48,00.

**Eşiğe dokunulmadı.** Kırmızı bir testi, sebebini çözmeden yeşile boyamak ölçümün
anlamını yok eder; bu ayrı bir iş olarak ele alınmalı.

---

## 11. Süit durumu — 48 kırmızı testin tamamı hesaba katıldı

Tam süit (`pytest -m "not slow"`): **1222 passed, 48 failed, 11 skipped** (20 dk 48 sn).

Her başarısızlığın bu değişiklikten gelip gelmediği **ölçülerek** ayrıldı. Yöntem:
`_kampanya_turunu_tespit_et` ve `menu_satirlarini_ayikla` depoda yalnızca
`regex_extractor.py` içinde kullanılıyor (dış import yok), bu yüzden eski davranışı
çalışma anında geri takan bir pytest eklentisiyle aynı testler yeniden koşuldu ve
başarısız kümeler karşılaştırıldı.

| Grup | Adet | Kanıt | Sonuç |
|---|---:|---|---|
| `test_scraper_regresyon` (36) + `test_sprint_is_listesi` (1) + `test_tutarlilik_kontrolu` (1) | 38 | Eski sınıflandırıcıyla koşuldu → **birebir aynı 38 test**; küme farkı iki yönde de boş | Değişiklikten bağımsız |
| `test_sayisal_cekirdek_alanlarda_dogruluk_esigin_altina_dusmez` | 1 | Makro F1 önce de sonra da **72,50** (eşik 75,0) | Değişiklikten bağımsız |
| `test_rag_soru_seti::test_cevapli_sorularin_yer_gercegi_altin_veriden_geliyor` | 1 | İzole koşuda eski kodla da yeni kodla da **aynı şekilde kırmızı** | Değişiklikten bağımsız |
| `test_rag_kalip_kirliligi` | 8 | İzole koşuda **hem eski hem yeni kodla YEŞİL** (ikisinde de 1 failed / 17 passed) | Süit sırası/durumuna bağlı |

**Bu değişikliğe atfedilebilen başarısızlık: 0.**

### DÜZELTME: "48 kırmızı test" ölçümün kendisinden geliyordu

> Yukarıdaki §11 tablosu, ilk yazıldığı hâlinde `test_rag_kalip_kirliligi.py`'deki
> 8 başarısızlığı "süit sırasına bağlı gerçek bir yalıtım sorunu" diye
> raporluyordu. **Bu yorum yanlıştı ve geri alındı.**

Gün sonunda, tek bir pytest süreci koşarken alınan temiz ölçüm:

```
5 failed, 1270 passed, 11 skipped, 46 deselected   (15 dk 39 sn)
```

RAG kalıp testlerinin 8'i de geçiyor; `test_scraper_regresyon` 36 değil **2**
kırmızı veriyor — ve bu 2 kayıt (TF-011, ZK-027) dosyanın tek başına koşulduğu
ölçümdekiyle **birebir aynı**.

**Kök neden ölçüm yönteminde:** 48 başarısızlık veren koşu başlatıldığında,
`slow` testleri de içeren başka bir tam süit koşusu **aynı anda** çalışıyordu.
Her iki süreç de ~1 GB'lık gömme modeli, cross-encoder, GLiNER ve Ollama
yüklüyordu. Arka planda alınan yığın dökümlerinden biri tam da bir
`transformers` model materyalizasyonu sırasındaydı. Kaynak baskısı altında
model yüklemesi düşünce `chunking/retriever.py::getir` istisna fırlatıyor ve
dosyadaki **zıt iddialı testler bile birlikte** kırmızıya dönüyor — nitekim
"yeterli kaynak olmalı" ve "çekimser kalmalı" testleri aynı anda düşmüştü; bu
zaten iddiaların yanlışlanmadığının, çağrının patladığının işaretiydi.

**Alınan ders (yöntem):** ağır model yükleyen bir süitte paralel koşu, ölçümü
sessizce bozar. Bu depoda süit **seri** koşulmalı; aksi hâlde kırmızılar
kodun değil, ölçüm ortamının raporudur.

Kalan 5 kırmızının hepsi bu değişikliklerden bağımsız olarak doğrulanmıştır
(bkz. yukarıdaki tablo).

---

# İkinci tur — 25 Ağustos 2026, aynı gün

Aşağıdaki üç bölüm, ilk turdan sonra sırayla ele alınan üç ayrı konudur.

---

## 12. Şema açığı: korpusta olup enum'da olmayan türler

### Bulgu

302 imzalı altın kayıttan **33'ü**, `api/schemas.py::KampanyaTuru` enum'unda
karşılığı **olmayan** bir etiket taşıyordu:

| Gold etiketi | Kayıt |
|---|---:|
| Ticari Kampanya | 18 |
| Musteri Ol Kampanyasi | 9 |
| Sigorta/BES Kampanyasi | 2 |
| Katilma Hesabi Kampanyasi | 2 |
| POS Kampanyasi | 2 |

Bu bir etiketleme özensizliği **değildi** — kayıtlar okundu: hepsi gerçek ve
ayırt edici türler (Sağlam Business Kart, bayi kartı, e-ihracat, esnaf/tüzel,
BES planı, taksitli POS). **Şema veriden küçüktü.**

İki somut zararı vardı:

1. **Ölçüm tavanı** — motor yalnızca enum değerlerini üretebildiği için bu 33
   kayıt, motor ne yaparsa yapsın hata sayılıyordu.
2. **Çalışma zamanı riski** — `CampaignRecord.kampanya_turu` alanı `KampanyaTuru`
   ile **tipli**. Zenginleştirme boru hattından gelen "Ticari Kampanya" gibi bir
   değer, API yanıtında Pydantic doğrulamasını düşürürdü.

### Sözleşme etkisi (denetlendi)

- DB sütunu `String(100)` (`api/models.py`), Postgres enum'u **değil** → migration gerekmez.
- Arayüzde sabit tür listesi yok (`dashboard/src/` tarandı).
- Yalnızca **ekleme** yapıldı, hiçbir değer değiştirilmedi/silinmedi → geriye dönük uyumlu.

### Ölçüm — kurallar tek tek denendi

Taban: F1 %74,09.

| Aday | TP | FP | FN | **F1%** | Karar |
|---|---:|---:|---:|---:|---|
| Ticari: `business kart`, `bayi kart` | 210 | 52 | 78 | 76,36 | ara adım |
| **+ `ihracat`** | 212 | 50 | 76 | **77,09** | **alındı** |
| + `ticari`, `kobi` | 133 | 134 | 155 | 47,93 | **RED** — menüde her sayfada geçiyor |
| + `esnaf` / `çiftçi` / `tüzel` | — | — | — | 75,59 / 75,45 / 75,95 | **RED** — hepsi tabanın altında |
| + `tohum kart` | 213 | 49 | 75 | 77,45 | **RED** — aşağıya bakınız |
| Sigorta/BES: `bireysel emeklilik`, `bes planı` | 214 | 48 | 74 | 77,82 | **alındı** |
| + `sigorta` | 202 | 60 | 86 | 73,45 | **RED** |
| POS: `pos kampanya` | 214 | 48 | 74 | 77,82 | **alındı** |
| Müşteri Ol: `müşterisi ol`, `müşterimiz ol` | 203 | 68 | 85 | 72,63 | **RED** — pazarlama kalıbı |
| Katılma Hesabı: `katılım hesab` | 212 | 52 | 76 | 76,81 | **RED** |
| **ÜÇÜ BİRDEN, sözlüğün EN BAŞINDA** | **216** | **46** | **72** | **78,55** | **SEÇİLEN** |
| Üçü birden ama EN SONDA | 205 | 57 | 83 | 74,55 | sıralama şart |

**Sıralama neden şart:** bu türlerin hepsi aynı zamanda birer kart kampanyasıdır
("Sağlam Business Kart", "Taksitli POS"). `Kart Kampanyasi` önce gelseydi üçünü
de yutardı — 4,00 puanlık fark tam olarak bu.

### Aşırı uydurma kontrolü — `tohum kart` neden alınmadı

`tohum kart` F1'i 77,09 → 77,45 çıkarıyordu (+0,36). Kontrol olarak, açıkça
uydurma olan bir marka adı denendi:

| Anahtar | F1% |
|---|---:|
| `tohum kart` | 77,45 |
| `fugevet` *(uydurma kontrol)* | 77,31 |
| `proemtia` *(uydurma kontrol)* | 77,09 |

Kazanç uydurma kontrolle **aynı büyüklük sınıfında** — yani kuraldan değil tek
bir kayıttan geliyor. Alınmadı.

### Motorun üretemediği iki tür — bilinçli boşluk

`Musteri Ol Kampanyasi` ve `Katilma Hesabi Kampanyasi` **enum'a eklendi ama
motora kural eklenmedi.** Denenen kurallar F1'i düşürdü (−4,46 ve −0,28).
Enum'da bulunmalarının sebebi ölçümün "imkânsız etiket" üretmemesi; bunlar
regex'in ayırt edemediği vakalardır ve NER/LLM katmanının işidir.
**Boş bırakmak, yanlış etiketlemekten iyidir.**

---

## 13. Gold etiket tutarsızlığı

### Yapılan: ad kayması normalizasyonu (2 kayıt)

`Yatirim Kampanyasi` → `Yatirim Urunu Kampanyasi` (TF-012, KT-046). Aynı kavram
iki farklı adla yazılmış; enum'daki kanonik. Bu bir yargı değil, yeniden
adlandırmadır.

Uygulama, deponun yerleşik deseniyle yapıldı — **XLSX tek doğru kaynak, JSON
ondan üretilir** (`docs/PROJE_TANITIMI.md`): yeni betik
`gold_dataset/kampanya_turu_etiket_duzelt.py` (varsayılan kuru koşu, `--yaz` ile
uygular, imza sütununa dokunmaz), ardından `excel_to_json.py`.

Doğrulama — git HEAD'e karşı fark: **302 → 302 kayıt, tam 2 alan değişti**,
başka hiçbir hücre etkilenmedi. Etki: `kampanya_turu` F1 73,72 → 74,09.

### Yapılmayan: "Alisveris Puani" mislabel'ı

`Alisveris Puani Kampanyasi` etiketli **5 kaydın hiçbiri puan kampanyası değil**:

| Kayıt | Kampanya | Gerçekte |
|---|---|---|
| VK-004 | Otel Rezervasyonlarında 2.500 TL İndirim | indirim |
| VK-005 | VKart TROY'la idefix'te 3.000 TL İndirim | indirim |
| DK-005 | TROY Kartla İdefix'te 3.000 TL İndirim | indirim |
| DK-006 | Hepsiburada'da Peşin Fiyatına 9 Aya Varan Taksit | taksit |
| DK-007 | N11'de Peşin Fiyatına 3 Taksit Fırsatı | taksit |

Buna karşılık gerçekten ParafPara **puanı veren** 35 kampanya `Kart Kampanyasi`
etiketli. Etiket, anlamının tersine kullanılmış.

**Düzeltilmedi — çünkü hedef sınıf henüz yok.** Bu 5 kayıt ile §14'teki 40 boş
kayıt aynı olguyu anlatıyor: kart üzerinden verilen **mağaza iş birliği**
kampanyaları. Doğru çözüm ikisini birden karşılayan bir sınıftır; onu da
etiketlemeden ekleyemem (§14).

---

## 14. Kalan 40 boş kayıt — ve neden burada durdum

Tüm scrape korpusunda (513 sayfa) `kampanya_turu` boş kalan kayıt sayısı, bu
oturumun başındaki **77'den 40'a** indi:

| | Oturum başı | Şimdi |
|---|---:|---:|
| boş (`None`) | 77 | **40** |
| yanlış "Konut Finansmani" | 79 | **4** |

Kalan 40'ın ezici çoğunluğu Albaraka'nın GastroClub/mobil uygulama üzerinden
verdiği mağaza indirimleri ("EspressoLab'de haftada 1 kahve hediyesi",
"Uber harcamalarınızda %80 indirim"). Metinlerinde **kart ürününden hiç söz
edilmiyor** — bunlara "Kart Kampanyasi" demek kanıtsız bir iddia olurdu.

Bunları kapatacak sınıf **"Mağaza İş Birliği Kampanyası"** olurdu ve §13'teki 5
mislabel'ı da çözerdi. **Eklemedim.** Gerekçe: altın veri setinde bu etiketi
taşıyan **tek bir kayıt bile yok**, yani kuralı ölçemem. Ölçülmemiş bir kalite
değişikliğini varsayılan yola sokmak, bu raporun baştan sona uyduğu kuralın —
ve deponun kendi kuralının — ihlali olurdu.

**Ön koşul:** bu 40 kaydın (ve VK-004/005, DK-005/006/007'nin) altın veri
setinde etiketlenmesi. Ondan sonra sınıf eklenip kuralı ölçülebilir.

---

## 15. Oturum sonu — birikmiş ölçüm

```
                          BAŞLANGIÇ                     SON
1) Dolu alan doğruluğu  : %49.63 (602/1213)   →   %57.79 (701/1213)
2) Boş alan doğruluğu   : %94.13              →   %94.70
   Makro F1 (11 alan)   : %60.38              →   %64.73
   Sayısal çekirdek     : %72.50              →   %74.44
```

| Alan | Başlangıç F1% | Son F1% | Δ |
|---|---:|---:|---:|
| **kampanya_turu** | 44,32 | **78,55** | **+34,23** |
| **finansman_tutari** | 48,00 | **61,54** | **+13,54** |
| kampanya_bitis | 67,80 | 67,80 | 0 |
| hedef_kitle | 14,16 | 14,16 | 0 |
| kampanya_baslangic | 30,43 | 30,43 | 0 |
| taksit_sayisi | 76,45 | 76,45 | 0 |
| odul_miktari | 81,28 | 81,28 | 0 |
| odul_birimi | 79,14 | 79,14 | 0 |
| kar_payi_orani_percent | 63,16 | 63,16 | 0 |
| erteleme_suresi_ay | 88,89 | 88,89 | 0 |
| vade_ay | 70,59 | 70,59 | 0 |

**Hiçbir alan gerilemedi.**

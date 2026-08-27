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
| **Sentetik müşteri sesi seti** | `tests/veri/kapsam_disi/sentetik_musteri_sesi.json` | 46 tema örneği + 2 alan dışı + 13 PII örneği + 7 yineleme çifti + 6 önem/4 çözüm/4 spam/2 entity-resolution örneği + 2 bilinen sınırlama | ❌ **Hayır** — yalnızca ölçüm; veritabanına da girmez (bkz. §6) |

### Ham veri dağılımı (300 kayıt / 9 banka)

Güncel banka bazlı dağılım (tekil kampanya + snapshot ayrımıyla) için bkz.
[md6_veri_bolumu.md § 1.3](md6_veri_bolumu.md#13-banka-bazlı-dağılım) veya
`docs/veri_coverage.md` (`python -m scraper.scripts.coverage_raporu` ile
yeniden üretilebilir).

| Banka | Kayıt |
|---|---|
| Ziraat Katılım | 111 |
| Türkiye Emlak Katılım | 103 |
| Albaraka Türk | 16 |
| Türkiye Finans | 16 |
| Hayat Finans | 18 |
| Kuveyt Türk | 15 |
| Dünya Katılım | 15 |
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
| Sentetik şikayet örnekleri ürün verisine karışmadı | `tests/test_sikayet_hatti_sentetik.py::test_v11_ornekleri_urun_verisine_sizmamis` — aynı tarama, PII desenli örnekler için |
| Şikayet hattı veritabanına yazmıyor | `tests/test_sikayet_hatti_sentetik.py` içinde `kaydet()` **hiç çağrılmaz**; `test_sentetik_kaynak_icin_izin_yok` izin kapısının bu kaynak için de kapalı olduğunu doğrular |

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
| Gerçek şikayet platformu verisi (Şikayetvar vb.) | Toplanmadı | Kurumsal/hukuki (KVKK) onay tamamlanmadı; izin kapısı kapalı — bkz. §6 |

Bu tablo, kapsam değiştikçe güncellenmelidir. Yeni bir veri türü sisteme
girecekse, girmeden önce buraya bir satır ve ona karşılık gelen bir ayrım testi
eklenmelidir.

---

## 6. Sentetik müşteri sesi seti (şikayet hattı)

Veri edinme kararının tam gerekçesi ve açık soruların resmi cevabı için bkz.
[`docs/veri_edinme_politikasi.md`](veri_edinme_politikasi.md).

### Neden gerçek veri toplamadık?

Şikayet hattı (`complaint/`) **kod olarak hazır, veri olarak boş**. Sebebi
`complaint/izin_kapisi.py`'de yazılı: kurumsal/hukuki (KVKK) onay tamamlanmadığı
için hiçbir kaynak için izin kaydı yoktur, dolayısıyla `hazirla()` gerçek bir
kaynak için `IzinYok` fırlatır.

Bu kapı **açılmadı**, etrafından da dolaşılmadı:

- `logs/sikayet_izin_durumu.json` **oluşturulmadı**
- `complaint/izin_kapisi.py` **değiştirilmedi** — dev bypass'ı eklenmedi
- `complaint/toplama.py::kaydet` **çağrılmadı** — `sikayetler` tablosuna tek
  satır bile yazılmadı
- Gerçek veri çeken hiçbir modül yazılmadı

Şartname açısından da bir eksiklik doğmuyor: Md. 5.1 veri setini **katılım
bankalarının resmî web siteleriyle** tanımlıyor; şikayet platformu bu kapsamda
değil, müşteri sesi katmanı projenin kendi eklentisidir. Buna karşılık Md. 16
üçüncü taraf hakları ve KVKK uyumunu takımın sorumluluğuna veriyor.

Ölçüm için gerçek veri **gerekmez**: `izin_zorunlu=False`, `toplama.py`
docstring'inde tam olarak sentetik ölçüm için tanımlı bir yoldur. Bayrak
verilmediğinde kapı normal çalışır — bunu `test_sentetik_kaynak_icin_izin_yok`
kilitler.

### Neden setin veritabanına girmesi de yasak?

Veri dosyasının kendi `_aciklama` alanı bunu şart koşuyor: *"içeriği
veritabanına, altın veri setine ve RAG indeksine ASLA girmez"*. Somut gerekçe:
`GET /musteri-sesi/yogunluk-ozeti` gerçek `sikayetler` tablosunu okuyor. Sentetik
satır yazsaydık endpoint bugünkü doğru `kapsam_durumu: "izin_yok"` cevabından
`"veri_var"`a döner ve jüriye **gerçek olmayan bir şikayet yoğunluğu**
göstermiş olurduk.

### v1.0 → v1.1: ölçülen boşluk

v1.0'da yalnızca tema sınıflandırması ölçülüyordu — yani `hazirla()` hattının
6 adımından biri. 27 Ağustos 2026'da sayıldı:

| v1.0 durumu | Sonuç |
|---|---|
| 22 örneğin PII içereni | **0** — PII katmanı hiç ölçülmüyordu |
| 22 örneğin `insan_kontrolu_gerekir` tetikleyeni | **0** |
| 22 içerik hash'inin tekil olanı | **22/22** — yineleme mantığı hiç çalışmıyordu |

v1.1 bu boşluğu kapatıyor. Mevcut 20 örnek ve 2 alan dışı örnek
**değiştirilmedi**.

### İki yönlü ölçüm (aynı ilke, şikayet tarafında)

| Grup | Sayı | Beklenen davranış | Ölçtüğü şey |
|---|---|---|---|
| `pii_ornekleri` | 9 | Maskelenmeli | **Hassasiyet** — TCKN, IBAN, kart, telefon, e-posta kaçtı mı? |
| `pii_karsi_ornekleri` | 4 | Maskelenmemeli | **Özgüllük** — müşteri no, referans no, tutar, tarih silindi mi? |
| `yineleme_ciftleri` | 5 | Aynı hash | **Yakalama** — noktalama/harf/boşluk farkı aynı şikayeti ayırıyor mu? |
| `yineleme_karsi_ciftleri` | 2 | Farklı hash | **Özgüllük** — normalizasyon farklı şikayetleri birleştiriyor mu? |
| `bilinen_sinirlamalar` | 2 | Değişmemeli | Kararın dondurulması |

Tek yön ölçmek yanıltıcı olurdu: yalnızca hassasiyet ölçülseydi "her rakam
dizisini sil" diyen bir kontrol %100 alır, şikayetin finansal içeriği yok
olurdu. Bu, §2'deki terminoloji ölçümüyle **aynı** disiplindir.

**Güncel sonuç:** PII hassasiyet 9/9, PII özgüllük 4/4, yineleme yakalama 5/5,
yineleme özgüllük 2/2, maskeleme sonrası tema 13/13.

### Bilinen sınırlamalar

| Kod | Sınır | Etki |
|---|---|---|
| `SM-BS1` | Kişi adı içeren metin `bulunanlar={}` üretir ve `insan_kontrolu_gerekir` **False** kalır — metin sessizce "temiz" sayılır. `pii_temizleme.py` docstring'i bu metinlerin bayrakla işaretlendiğini söylüyor; uygulamada bayrak `bool(sayac)` olduğu için yalnızca regex ile yakalanan PII varsa True dönüyor. | Faz 1'de **yok** (sette gerçek ad yok, gerçek veri toplanmıyor). Gerçek veri ingest edilmeden önce kapatılması gereken bir açık — Faz 2 kapılarından biri. |
| `SM-BS2` | Maske komşu boşluğu yutabiliyor (`[IBAN]hesabima`). | Kozmetik. Tema eşleşmesi alt-dize temelli olduğu için sınıflandırmayı bozmuyor — `SM-P02` bunu kanıtlıyor. |

Karşı-örnek setindeki `BS-001` ile aynı mantık: yeşil test "sorun yok" demek
değil, **"bilinen sınırlama hâlâ aynı yerde"** demektir. Biri davranışı
değiştirirse test kırılır ve karar yeniden tartışılmış olur.

### v1.1 → v1.2: severity, resolution, entity resolution (27 Ağustos 2026)

Mentor geri bildirimi iki kavramsal boşluk işaret etti: "şikâyet = negatif
duygu" varsayımı hatalıydı (ciddiyet ve çözüm durumu ayrı boyutlardır) ve
kampanya eşleştirmesi tek bir blend skora sıkıştırılmıştı (banka/ürün türü
gibi daha güvenilir seviyeler, kampanya eşiği geçemediğinde kayboluyordu).
Karar ve gerekçe [ADR 0003](adr/0003-sikayet-onem-cozum-entity-resolution.md)'te;
burada yalnızca ölçüm özetlenir.

| Grup | Sayı | Ölçtüğü şey |
|---|---|---|
| `onem_ornekleri` | 6 | `complaint/onem_derecesi.py` — YUKSEK/ORTA/DUSUK, varsayılan ORTA |
| `cozum_ornekleri` | 4 | `complaint/cozum_tespiti.py` — cozuldu/kismen/cozulmedi/bilinmiyor, varsayılan bilinmiyor |
| `dusuk_bilgi_ornekleri` + karşıları | 2+2 | `complaint/toplama.py::_dusuk_bilgi_supheli_mi` — spam/düşük-bilgi işareti, hassasiyet+özgüllük |

Üç seviyeli entity resolution (`complaint/kampanya_eslestirme.py::EslesmeSonucu.banka_eslesti`,
`.urun_turu_guven`) ayrı bir Python sınıf üzerinden test edilir
([`tests/test_sikayet_hatti_sentetik.py`](../tests/test_sikayet_hatti_sentetik.py)
§12) — JSON veri setine değil, sentetik bir kampanya nesnesine ihtiyaç duyar.
Dashboard'da [`MusteriSesi.jsx`](../dashboard/src/pages/MusteriSesi.jsx)
içinde sabit bir demo kartıyla da gösterilir (canlı hesaplama değil —
`sikayet_hatti_olcum_raporu.json` ile aynı örnek).

**Güncel sonuç:** önem derecesi 6/6, çözüm durumu 4/4, düşük-bilgi yakalama
2/2, düşük-bilgi özgüllük 2/2, üç seviye (banka/ürün türü/kampanya) bağımsız
doğrulandı.

**Kapsam dışı bırakılan (bilerek):** anlamsal (paraphrase) yakın-tekrar
tespiti ve `dedup_group_id` — `icerik_hash` zaten tam eşleşmeler için bir
grup anahtarıdır, paraphrase tespiti embedding/ML katmanı gerektirir ve
projenin kural tabanlı tasarım tercihiyle çelişir (bkz. ADR 0003).

### v1.2 → v1.3: veri seti çeşitliliği genişletildi (27 Ağustos 2026)

Kendi kendini denetim: `tema_siniflandirici.py::_TEMA_IFADELERI` içindeki 60
ifadenin **27'si (%45) hiçbir örnek tarafından hiç tetiklenmiyordu** — bir
ifadede yazım/regex hatası olsa hiçbir test bunu yakalamazdı. `ornekler`
grubu **20 → 40**'a çıkarıldı (tema başına 2 → 4); yeni 20 örnek mümkün
olduğunca daha önce kullanılmamış ifadeleri hedefler ve cümle yapısı/
uzunluk/üslup bakımından ilk 20'den bilerek farklıdır.

**500'e çıkarılmadı — bilinçli tercih.** Tüm örnekler tek oturumda elle
yazıldığından ham sayıyı büyütmek dilsel çeşitliliği artırmaz, yapay bir öz
güven üretir (bkz. [`docs/veri_edinme_politikasi.md`](veri_edinme_politikasi.md)
§3). Odak noktası ham sayı değil, kural setinin test edilmeyen kısmını
kapatmaktı.

`onem_derecesi.py`'ye 3. bir sinyal eklendi: metinde somut bir TL/₺ tutarı
geçmesi (temadan bağımsız YUKSEK sinyali; COMMUNICATION_AMBIGUITY bu
sinyalden muaftır). Bu olmadan `YUKSEK`, yalnızca 2/10 temaya bağlıydı ve
"önem derecesi" fiilen temanın gizli bir yeniden etiketlemesiydi.

**SM-021, mentor geri bildirimindeki "kampanya çok güzel ama ödülüm
yatmadı" örneğini birebir uygular** — olumlu bir ifadeyle başlar, kural
tabanlı sınıflandırıcının buna aldanmadığını kanıtlar (bkz. ADR 0003).

**Güncel sonuç:** tema sınıflandırma doğruluğu 40/40 (%100), önem derecesi
6/6 (tutar-bahsi sinyali dahil).

### v1.3 → v1.4: kalan kapsama boşluğu kapatıldı, entity resolution veri kaynağına taşındı (27 Ağustos 2026)

v1.3 sonrası aynı ölçüm tekrarlandı: 60 ifadenin **9'u (%15) hâlâ hiç
tetiklenmiyordu** (çoğunlukla REWARD_NOT_CREDITED'in zengin 10-ifadelik
listesinde). `ornekler` grubu **40 → 46**'ya çıkarıldı — bu sefer tema
başına uniform değil, **tam olarak kalan boşluğa hedefli** (5 yeni
REWARD_NOT_CREDITED, 1'er yeni ELIGIBILITY_MISMATCH/INSTALLMENT_MATURITY/
ACTIVATION_REGISTRATION örneği). Sonuç: **60 ifadenin 60'ı (%100)** artık
en az bir örnekte tetikleniyor.

Bu, "40 az mı?" sorusunun somut cevabıdır: sayıyı büyütmenin kendisi amaç
değildi, **ölçülmüş bir kapsama boşluğunu sıfırlamak** amaçtı — boşluk
kapandığında ekleme durdu.

**`entity_resolution_ornekleri` grubu eklendi.** 3 seviyeli entity
resolution demosu önceden hem `sikayet_hatti_olcum.py` hem
`tests/test_sikayet_hatti_sentetik.py` içine **ayrı ayrı gömülüydü** —
iki kopyanın senkron kalması elle takip gerektiriyordu. Artık tek kaynak
(JSON), iki tüketici. İkinci bir kontrol-grubu senaryosu (`SM-ER2`) da
eklendi: spesifik kampanya adı da geçince Seviye 3'ün de eşiği aştığını
gösterir — üç seviyenin birbirini **engellemediğini**, yalnızca birbirinden
**bağımsız** ölçüldüğünü kanıtlar.

**Güncel sonuç:** tema sınıflandırma doğruluğu 46/46 (%100), entity
resolution 2/2 senaryo beklenenle uyumlu.

### Yeniden üretim

```bash
python sikayet_hatti_olcum.py
```

`sikayet_hatti_olcum_raporu.json` üretir. Aynı ölçümler
`pytest tests/test_sikayet_hatti_sentetik.py -s` ile CI'da kilitlidir.

# KatılımAI — Proje Tanıtımı

**Takım:** PeacewAI · Fırat Üniversitesi, Yapay Zekâ ve Veri Mühendisliği
**Yarışma:** TEKNOFEST 2026 Yapay Zekâ Dil Ajanları — 2. Senaryo
**Depo:** `Sara-Toptamur36/katilim-ai`
**Bu belgenin tarihi:** 23 Ağustos 2026

Bu belge, projeyi hiç bilmeyen birinin okuyup **ne yaptığımızı, neden öyle
yaptığımızı ve bundan sonra ne yapacağımızı** anlaması için yazıldı. Nasıl
yapılacağı ayrı belgede: [`CALISMA_REHBERI.md`](CALISMA_REHBERI.md).

---

## 1. Problem

Türkiye'deki katılım bankaları kampanyalarını kendi sitelerinde, her biri
farklı bir düzende, serbest metin olarak yayımlıyor. Bir müşteri "hangi
bankada MTV ödemem 3 taksite bölünür" diye sorduğunda cevabı bulmak için
dokuz ayrı siteyi gezmesi gerekiyor.

**KatılımAI**, bu sayfaları toplayıp yapılandırılmış bilgiye çeviren ve
üstüne kaynak gösteren bir dil ajanı. Cevabın her cümlesi bir banka
sayfasından geliyor; sistem uydurmuyor.

### Neden zor

Bu, "metinden sayı çıkar" probleminden daha ince. Somut tuzaklar:

| Tuzak | Örnek | Yanlış cevap |
|---|---|---|
| Oran gibi görünen ama oran olmayan | "98/2 kâr paylaşım oranı" | `kar_payi_orani = 98` |
| Eşik ile tutarı karıştırmak | "1.000 TL üzeri alışverişe 100 TL iade" | `finansman_tutari = 1000` |
| Taksit ile vadeyi karıştırmak | "vade farksız 3 taksit" | `vade_ay = 3` |
| İndirim ile kâr payını karıştırmak | "%30'a varan indirim" | `kar_payi_orani = 30` |
| Yan menüdeki başka kampanya | Sayfanın altındaki "Diğer Kampanyalar" | Başka kampanyanın taksiti |

Bu tuzakların **hepsi** projede gerçekten yaşandı ve altın veri setinde
karşı örnek olarak duruyor.

---

## 2. Mimari — katmanlar ve neden var oldukları

```
scraper/      →  chunking/  →  agent/     →  api/  →  dashboard/
(sayfa topla)   (indeksle)     (soru çöz)    (uç)     (arayüz)
                                  ↑
                          extraction/ · validation/ · calculator/
                          (bilgi çıkar) (doğrula)    (hesapla)
                                  ↑
                            gold_dataset/
                            (ÖLÇÜM REFERANSI)
```

### `scraper/` — sayfa toplama
Dokuz bankanın kampanya sayfalarını indirir, `raw_data/<banka>/json/`
altına anlık görüntü olarak yazar. **Eski görüntüler silinmez** — bir
etiketin hangi metinden çıkarıldığı geriye dönük görülebilmeli.

İki tarayıcı var: statik (`statik_scraper.py`) ve JS'li
(`js_scraper.py`). Bazı bankalar kampanya tarihini JavaScript ile
basıyor; statik tarayıcı onu göremiyor. Bu, projede **gerçek veri
hatasına yol açtı** (bkz. bölüm 5).

### `chunking/` — indeksleme ve arama
Sayfaları anlamsal parçalara böler, `multilingual-e5-base` ile
gömüler, Qdrant'a yazar. Arama **hibrit**: yoğun (anlam) + seyrek
(BM25, kelime) vektörler RRF ile birleşiyor, sonra bir cross-encoder
yeniden sıralıyor.

### `extraction/` — bilgi çıkarım motoru
Üç katmanlı: **regex → GLiNER (sıfır atışlı NER) → LLM**. Regex hızlı
ve deterministik; jüri demosunda internet/GPU olmasa bile çalışır.
Güven eşiği `0.8` — üstündeki regex sonucu kilitlenir, LLM'e
sorulmaz.

### `validation/` — doğrulayıcı (Verifier)
Ajanın söylediği her sayıyı kaynağa geri sorar. Ölçüldü: 6/6 yanlış
pozitifi reddetti, 41 gerçek iddianın 37'sini onayladı.

### `gold_dataset/` — ölçüm referansı
**Projenin en kritik parçası.** İnsan eliyle etiketlenmiş kampanya
kayıtları; çıkarım motorunun doğruluğu buna karşı ölçülüyor.

---

## 3. Kritik tasarım kararları

Bunlar "tercih" değil, **ölçümün anlamlı olması için zorunlu** kurallar.
Her biri gerçek bir hatanın ardından yazıldı.

### 3.1 Dairesellik yasağı — en önemli kural

> **Altın veri seti, çıkarım motorunun ÖLÇÜLDÜĞÜ referanstır.
> Motorun çıktısı altın sete giremez.**

Girerse ölçüm kendi kendini onaylar ve **tanım gereği %100** çıkar.
Sistem hiçbir şey öğrenmemiş olur ama mükemmel görünür.

Pratikte: `regex_extractor` (ölçülen motor) etiketleme ve iş listesi
üreten hiçbir kodda çağrılmaz. Etiket, insanın kaynağı okuyup verdiği
karardır.

**Sınır nerede:** `extraction/normalizer.py` bir *normalleştiricidir* —
"1.000 TL" ifadesini 1000 sayısına çevirir, hangi alana ait olduğuna
karar vermez. Onu kullanmak serbest. Yasak olan, **karar üreten**
motorun çıktısını kullanmak.

### 3.2 Boş hücrenin İKİ anlamı var

Bir alan boşsa bu iki farklı şey olabilir:

- **"Kaynakta belirtilmemiş"** — sayfa bu bilgiyi vermiyor. Motor oraya
  bir şey yazarsa bu **yanlış pozitiftir** ve ölçülür.
- **"Henüz incelenmedi"** — kimse bakmadı. Motor oraya ne yazarsa yazsın
  **ölçüme girmez**.

İkisi Excel'de aynı görünür. Ayrımı `excel_to_json.py` içindeki
`INCELENMIS_ALANLAR` listesi yapar: listedeki bir sütunun boş hücresi
"kaynakta yok" sayılır.

**Bu bir sütunu listeye eklemek, tüm kayıtların o sütununun gözden
geçirilmiş olduğunu iddia etmektir.** Yalan söylerse ölçüm bozulur.

23 Ağustos'ta ölçüldü: `taksit_sayisi` 80 kayıtta, `erteleme_suresi_ay`
97 kayıtta "incelenmemiş" durumdaydı — yani motor oralara serbestçe
uydurabilirdi. Kapatıldı.

### 3.3 Kanıt cümlesi (kanıt spanı)

Her dolu değerin yanında, o değeri haklı çıkaran **kaynak cümlesi**
durur:

```
taksit_sayisi: 3
kanit_spanlari: {"taksit_sayisi": "vade farksız 3 taksit avantajından yararlanın"}
```

Cümle kaynakta **birebir** geçmek zorunda; test bunu kontrol ediyor.
"Yaklaşık doğru" elle yazılmış bir cümle geçmez.

**Neden gerekli:** kampanya sayfaları dönüyor. 14 kaydın kaynak sayfası
şu an korpusta yok — o değerlerin neden öyle girildiğinin cevabı, kanıt
cümlesi girilmediyse kayboldu. Span, etiketleme anındaki gerekçeyi
dondurur.

### 3.4 Çekimserlik (abstention)

RAG, sorunun kelimelerinin bulunan parçalarla örtüşmesini ölçüyor
(`ASGARI_TERIM_ORTUSMESI = 0.60`). Örtüşme düşükse **cevap vermiyor**:

> "Bu soruyu yanıtlayacak yeterli kaynak bulamadım. Yanlış bilgi
> vermektense cevap vermemeyi tercih ediyorum."

Bankacılık bilgisinde uydurma cevap, cevapsızlıktan pahalıdır.

### 3.5 Filtrelemek yerine işaretlemek

103 kaydın 37'sinin kampanya süresi dolmuş. İlk refleks "süresi
dolmuşları arama sonuçlarından çıkar" olur. **Yapmadık.**

Sebep: tarih yanlış çıkarılmışsa filtre **geçerli** bir kampanyayı
sessizce görünmez yapar — jüri demosunda fark edilmesi en zor hata
türü budur. Bunun yerine kaynak her zaman gösteriliyor, yanına rozet
konuyor: **⚠ Süresi dolmuş — 2026-07-31**.

Bilinmeyen tarih "aktif" varsayılmıyor; "bilinmiyor" diyor. Bilmediğimiz
bir şeyi iddia etmiyoruz.

### 3.6 Eleme değil işaretleme (etiketleme kuyruğunda da)

Aynı ilke iş listesinde de geçerli. Kategori sayfası gibi görünen bir
sayfa otomatik elenmiyor, **insan kontrolüne** gönderiliyor. Gerekçesi
altın setin kendisinde: T.O.M. Katılım'ın üç kaydı (TOM-001/002/003)
tek bir `kampanyalar.html` sayfasından çıkmış. Yani "liste sayfası"
pekâlâ etiketlenebilir olabilir.

### 3.7 İkili doğruluk metriği

Tek bir "doğruluk" sayısı yanıltıcı olurdu. İki ayrı ölçü tutuyoruz:

- **Dolu alan doğruluğu** — motor bir değer bulduğunda doğru mu?
- **Boş alan doğruluğu** — kaynakta olmayan bir şeyi uydurmuyor mu?

Yanlış bir değer **hem** yanlış pozitif **hem** yanlış negatif sayılır.
Uydurmak, bulamamaktan iki kat pahalı.

---

## 4. Bugüne kadar ne yapıldı

### Sayılarla durum (23 Ağustos 2026)

| Ölçü | Değer |
|---|---|
| Altın veri seti | **103 kayıt**, hepsi insan doğrulamalı |
| Kanıt cümlesi girilmiş kayıt | 70 / 103 |
| Ham korpus | **511 sayfa**, 9 banka |
| Etiketleme kuyruğu | **200 aday** |
| Ulaşılabilir toplam | **301 kayıt** (şartname hedefi 200–300) |
| Ekran görüntüsü | 103 / 103 |
| Test | 64 dosya, hepsi geçiyor |

### Banka dağılımı

| Banka | Korpus | Altın set |
|---|---:|---:|
| Kuveyt Türk | 121 | 17 |
| Ziraat Katılım | 118 | 17 |
| Türkiye Emlak Katılım | 112 | 15 |
| Dünya Katılım | 57 | 9 |
| Albaraka Türk | 45 | 12 |
| Hayat Finans | 22 | 9 |
| Türkiye Finans | 18 | 8 |
| T.O.M. Katılım | 13 | 6 |
| Vakıf Katılım | 5 | 10 |

> Vakıf Katılım'ın 10 kaydı var ama korpusta 5 sayfası kalmış — kampanya
> rotasyonu. Kayıtlar geçerli (ekran görüntüleri var), yalnızca kaynak
> metin artık diskte yok.

---

## 5. Yol boyunca bulunan ve düzeltilen gerçek hatalar

Bunlar belgelendi çünkü **hepsi tekrar edebilir**. Her biri, kodda o
bölümün başındaki yorumda anlatılıyor.

### 5.1 Statik tarayıcı sayfanın bir kısmını görmüyordu
ZK-017 (BAUHAUS): anlık görüntü 997 karakter, canlı sayfa 1.775. Eksik
olan blok: **"Kampanya Dönemi / 01-04-2025 - 31-08-2026"**. Kayıt bu
eksik metinden etiketlendiği için tarihleri boş kaldı ve notuna
"Kampanya tarihi sayfada YOK" yazıldı — ikisi de yanlıştı.

**Etkilenen:** 7 Ziraat kaydı. **Çözüm:** `kaynak_tazele.py` ile
sayfalar JS'li tarayıcıyla yeniden çekildi, 39 anlık görüntü büyüdü
(bazıları iki katına).

### 5.2 Taksit ile vade karışmıştı
Aynı ifade bazı kayıtlarda `taksit_sayisi`, bazılarında `vade_ay`
yazılmıştı. `vade_ay` **ölçülen** bir sütun olduğu için bu, motoru
kendi hatası olmayan bir şeyden cezalandırıyordu.

**Etkilenen:** 9 kayıt. Dokuzuncusu (KT-001) otomatik uyarıya
takılmıyordu çünkü kampanya adında "N Taksit" geçmiyor — elle bulundu.

**Ayrım:** taksit bir ADETTIR ("3 taksit" = 3 ödeme), vade bir
SÜREDİR ("12 ay vade"). MTV, vergi, alışveriş ödemesinde "vade"
kavramı yoktur.

### 5.3 "Geçerlilik tarihi" yazımı kalıptan kaçıyordu
Denetim kalıbı "Kampanya Dönemi" ve "tarihleri arasında" arıyordu;
Vakıf Katılım **"Kampanya Geçerlilik Tarihi"** diyor. Üç kayıt
(VK-009, VK-010, TF-005) gözden kaçtı. TF-005'in notunda "bitiş tarihi
sayfada belirtilmemiş" yazıyordu — oysa yazıyordu.

### 5.4 Aynı soruya iki farklı cevap
Etiketleme araçları **en yeni** anlık görüntüyü okuyordu, doğrulama
testi ise `adaylar[0]` ile **en eskisini**. Tazelenmiş sayfadan yazılan
kanıt cümlesi, testin baktığı eski metinde bulunamayıp "kırık"
görünüyordu.

### 5.5 Kesme işareti farkı
Altın sette `BAUHAUS'ta` (düz kesme, U+0027), sayfada `BAUHAUS’ta`
(tipografik, U+2019). Üç regresyon testi "sayfa değişmiş" diyordu;
kampanya oradaydı.

### 5.6 Sessiz başarısızlık — en tehlikelisi
Yazdığım tarih kontrolü `except ImportError: return []` ile hatayı
yutuyordu. Betik `python gold_dataset/excel_to_json.py` diye
çalıştırılınca `sys.path[0]` repo kökü olmadığı için import başarısız
oluyor — yani **kontrol hiç çalışmıyor ama çıktı "Uyarı yok" diyordu.**

Artık atlanırsa sebebini yazıyor, ve iki test bunu koruyor.

### 5.7 Benzerlik ölçümü yanlış kuruluydu
Dünya Katılım sayfalarının 12.337 karakterinin ~10.000'i her sayfada
aynı menü. Ham karşılaştırmada **alakasız iki kampanya %87 benzer**
çıkıyordu. Banka kalıbı çıkarılınca aynı çift **%11**. Bu ölçümle bir
gerçek kampanyayı kopya sanıp silmek üzereydik.

Ayrıca `difflib.SequenceMatcher` varsayılan `autojunk` ile **simetrik
değil** — aynı çift için argüman sırasına göre %86 ve %83 verdi.

---

## 6. Ölçüm durumu

`python gold_dataset/excel_to_json.py` her çalıştığında yazdırıyor:

```
Yanlis pozitif olcum kapsami:
  kar_payi_orani       olculebilir=87/103
  vade_ay              olculebilir=95/103
  odul_miktari         olculebilir=58/103
  masraf_durumu        olculebilir=100/103
  taksit_sayisi        olculebilir=71/103
  erteleme_suresi_ay   olculebilir=97/103
  ...
```

"Ölçülebilir" = o kayıtta alan ya dolu ya da "kaynakta yok" işaretli.
Yani motorun oraya uydurma yazması **yakalanır**.

`INCELENMEMIS_ALANLAR` listesi 23 Ağustos'ta **boşaldı** — şemadaki her
ölçülen sütun artık yanlış pozitif ölçümüne giriyor.

---

## 7. Bilinen sınırlılıklar (bilerek kabul edilenler)

### 7.1 Yan menü kirliliği
JS'li tarama, Ziraat sayfalarına "diğer kampanyalar" menüsünü de
getiriyor. O menüdeki taksit sayıları metne giriyor ve iş listesindeki
"yeni taksit değeri" sinyalini gürültülü yapıyor.

**Yanlış eleme üretmiyor** (ölçüldü: 56 Ziraat kaydının hiçbiri
elenmedi) çünkü eleme "metin ≥%85 **ve** profil aynı" koşuluna bağlı.
Çözülecekse doğru yer tarama tarafındaki içerik seçicisi.

### 7.2 RAG indeksinde tarih yok
İndeks payload'ı yalnızca `metin · banka · kaynak_url · kampanya_adi ·
erisim_zamani` taşıyor. `retriever.getir()` içindeki `hedef_tarih`
parametresi **çalışmıyor** — baktığı `valid_at_start`/`valid_at_end`
alanları payload'da hiç yok. Açılırsa arama boş döner ve RAG her soruya
"kaynak bulamadım" der.

Kodda açık uyarı var. Çalışır hale getirmek isteyen önce indeksleyiciye
tarihleri eklemeli ve indeksi yeniden kurmalı.

### 7.3 Korpus yaşlanıyor
37 kaydın kampanya süresi dolmuş. Çıkarım ölçümü için sorun değil —
metin gerçek, değerler gerçek. Demoda rozet gösteriliyor.

### 7.4 Kampanya türü dağılımı çarpık
103 kaydın 53'ü "Kart Kampanyası". Gerçek dünyada da öyle, ama ölçüm
bu türe ağırlıklı.

---

## 8. Ne bekliyoruz

**Kısa vade (şartname teslimi):** 200–300 altın kayıt hedefi artık
korpusla ulaşılabilir (301). Kuyrukta 200 aday hazır ve her satırda
neden seçildiği yazıyor.

**Ölçüm:** 185 soruluk RAG değerlendirme seti hazır ama henüz
çalıştırılmadı (`scraper/scripts/rag_degerlendirme.py`). GPU'lu
makinede çalıştırılacak.

**Demo:** Tamamen yerel çalışıyor — Ollama + Qdrant + FastAPI + React.
İnternet gerekmiyor. Regex katmanı, LLM erişilemezse bile cevap
üretiyor.

---

## 9. Nerede ne var

| Yol | İçerik |
|---|---|
| `gold_dataset/altin_veri_seti.xlsx` | **Altın veri seti — tek doğru kaynak.** JSON ondan üretilir |
| `gold_dataset/altin_veri_seti.json` | Üretilen dosya, **elle düzenlenmez** |
| `gold_dataset/sprint_is_listesi.json` | Etiketleme kuyruğu, 200 aday |
| `gold_dataset/ekran_goruntuleri/` | Her kaydın kaynak sayfası görüntüsü |
| `gold_dataset/dogrulama.html` | Doğrulama sayfası (üretilir) |
| `scraper/raw_data/<banka>/json/` | Ham sayfa anlık görüntüleri |
| `docs/` | Tasarım ve ölçüm raporları |
| `tests/` | 64 test dosyası |

---

**Devamı:** [`CALISMA_REHBERI.md`](CALISMA_REHBERI.md) — kalan işlerin
adım adım nasıl yapılacağı.

# Md. 6 — Proje Dokümantasyonu (Tam Metin)

**Amaç:** Şartname Md. 6'nın istediği 10 dokümantasyon kalemini **tek yerde**
toplamak. İçeriğin çoğu depoda zaten vardı (README + ayrı raporlar); bu
belge onları dağıtmadan, sadece **tek bir okuma sırasına** diziyor. Her
bölüm, tam derinliği için ilgili kaynağa bağlantı verir — burada tekrar
yazılan metin değil, o kaynağın özetidir.

Güncelleme tarihi: 19 Ağustos 2026. Tüm sayılar depodaki komutlarla yeniden
üretilebilir (her bölümde ilgili komut yazılıdır).

---

## İçindekiler

1. [Sistem mimarisi ve veri akışı](#1-sistem-mimarisi-ve-veri-akışı)
2. [Kullanılan NLP yaklaşımı](#2-kullanılan-nlp-yaklaşımı)
3. [Model/kural yapısının açıklaması](#3-modelkural-yapısının-açıklaması)
4. [Kullanılan veri seti ve açıklaması](#4-kullanılan-veri-seti-ve-açıklaması)
5. [Veri ön işleme adımları](#5-veri-ön-işleme-adımları)
6. [Bankalar arası karşılaştırma nasıl yapılıyor](#6-bankalar-arası-karşılaştırma-nasıl-yapılıyor)
7. [Projenin çalıştırılması — kurulum ve adımlar](#7-projenin-çalıştırılması--kurulum-ve-adımlar)
8. [Karşılaşılan problemler ve çözüm yaklaşımları](#8-karşılaşılan-problemler-ve-çözüm-yaklaşımları)
9. [Model çıktı örnekleri](#9-model-çıktı-örnekleri)
10. [Performans değerlendirme yöntemi](#10-performans-değerlendirme-yöntemi)

---

## 1. Sistem mimarisi ve veri akışı

KatılımAI, ham kampanya metninden karşılaştırılabilir yapılandırılmış
veriye ve **kaynak gösteren** doğal dil yanıtlarına uzanan uçtan uca bir
sistemdir. Dört bağımsız ama izlenebilir katmandan oluşur:

```
Banka kaynakları (BDDK listesi)
        ↓
Scraper (statik + JS + PDF) → SHA-256 delta kontrolü
        ↓
Normalizasyon → Regex + NER + LLM hibrit çıkarım
        ↓
   ┌────────────────┬─────────────────┐
   ↓                                  ↓
PostgreSQL                 Semantik parçalama → Embedding
(ACTIVE/EXPIRED)            + BM25 seyrek vektör → Qdrant
   └────────────────┬─────────────────┘
                    ↓
            AJAN ORKESTRATÖRÜ
    Intent Detection → Tool Router
        ↓      ↓      ↓      ↓      ↓
      SQL  Calculator Dict  RAG  Fallback
                    ↓        └─ hibrit arama (yoğun+seyrek, RRF)
                    ↓           + abstention + citation
    Response Generator → Terminoloji Kontrolü
    → Verifier (çıkarımda kullanılıyor; ajan yanıt yoluna henüz bağlı değil)
                    ↓
    Dashboard · Chatbot · Jüri Audit Paneli
```

Sistemi bir "dil ajanı" yapan katman, kullanıcı niyetini anlayıp doğru
aracı seçen orkestrasyondur. **Sayısal karşılaştırma sabit SQL
şablonlarıyla, hesaplamalar saf Python fonksiyonlarıyla yapılır — LLM'e
bırakılmaz.** Bu ayrım tasarımın merkezindedir: finansal bir sistemde
LLM'in halüsinasyon riski kabul edilemez, bu yüzden LLM yalnızca *bağlamsal
yorumlama* gerektiren yerlerde (bilgi çıkarımı, serbest metin yanıtı)
kullanılır; *sayı üretmesi gereken hiçbir yerde* kullanılmaz.

Tam kaynak: [`README.md`](../README.md) (mimari diyagram ve "Tasarım
İlkeleri" bölümü).

---

## 2. Kullanılan NLP yaklaşımı

Üç farklı NLP yöntemi, **birbirinin yerine değil, birbirini tamamlayacak**
şekilde kademeli olarak çalışır:

| Yöntem | Görev | Neden bu yöntem |
|---|---|---|
| **Kural tabanlı (regex)** | Yüksek kesinlikli, biçimsel kalıplar: "%1,89", "120 aya kadar", "Kâr paysız" | Deterministik, hızlı, yanlış-pozitif riski en düşük katman — önce bu denenir |
| **Bilgi çıkarımı (NER, GLiNER zero-shot)** | Regex'in kaçırdığı bağlamsal/dolaylı ifadeler | Etiket şeması biz tanımladık, model **eğitilmedi** — etiket adını söyleyip zero-shot sorguladık |
| **Üretken çıkarım (LLM, Qwen2.5-7B)** | Regex ve NER'in ikisinin de bulamadığı, tamamen dolaylı ifadeler | Yalnızca istem (prompt) yazıldı, `temperature=0`, ağırlıklara dokunulmadı |

Üç katman **birbirinin üzerine yazmaz**: her katman kendi bulduğu değeri bir
*aday* olarak üretir; bir çözümleyici (resolver) en yüksek güvenli adayı
seçer ve 0,8 güven eşiğini geçen alanları kilitler
(`extraction/hybrid_pipeline.py::KILITLEME_GUVEN_ESIGI`). Bu, mentörlük
sürecinde bulunan "regex kilitleme riski" bulgusuna verilen doğrudan
yanıttır — regex yanlışsa artık geri dönüşü yok değildir, bir sonraki
katman düzeltebilir (ama tersine, yüksek güvenli bir regex sonucu da
gereksiz yere ezilmez).

**Ne yapılmadı, açıkça:** Hiçbir modelin ağırlığı güncellenmedi — adapter
yok, LoRA yok, gradient adımı yok, eğitim verisi yok. Bu bilinçli bir
kapsam kararıdır, gerekçesi [`kapsam_ve_veri_ayrimi.md`](kapsam_ve_veri_ayrimi.md)
§4'te ve okunacak tam metin [`nasil_anlatiyoruz.md`](nasil_anlatiyoruz.md)'de
yazılıdır — video/sunum/doküman yazarken **bu belgedeki ortak metin ve
"söylemeyeceğiz/söyleyeceğiz" tablosu** birebir kullanılmalıdır. Bu ayrımın
CI'da kalıcı korunması için bir iddia dürüstlüğü bekçisi
(`tests/test_iddia_durustlugu.py`) vardır: dokümanlarda yasak bir eğitim
iddiası kalıbı geçerse test kırmızı verir.

Serbest bilgi soruları için kullanılan RAG (Retrieval-Augmented
Generation) ayrı bir mekanizmadır — model ağırlığında bilgi saklamak
yerine güncel belgelerden kanıt getirir, üzerine serbest metin üretmez.
Tam tasarım: [`rag_tasarim_ve_olcum.md`](rag_tasarim_ve_olcum.md).

---

## 3. Model/kural yapısının açıklaması

### 3.1 Kullanılan üç model — hiçbirine dokunulmadı

| Katman | Model | Sürüm | Ne yapıldı |
|---|---|---|---|
| Bağlamsal çıkarım | `urchade/gliner_multi-v2.1` | sabit | Zero-shot, etiket şeması bizim |
| Üretken çıkarım | `qwen2.5:7b-instruct-q4_K_M` (Ollama) | sabit | Yalnızca istem, `temperature=0` |
| Gömme (RAG) | `intfloat/multilingual-e5-base` | sabit | Olduğu gibi kullanıldı |

Sürümler `requirements.txt`'te `==` ile sabitlenmiştir (bkz. Bölüm 7).

### 3.2 Kural yapısı (regex katmanı)

`extraction/regex_extractor.py` — her finansal alan (kâr payı oranı, vade,
taksit sayısı, erteleme süresi, ödül miktarı/birimi, finansman tutarı,
masraf durumu) için ayrı, bağlam-duyarlı desenler içerir. Bir sayı deseni
**tek başına** bir kavramı tanımlamaz — yakınındaki anahtar kelime (ör.
"kâr pay", "taksit", "ödül") de kontrol edilir; aksi hâlde "%10 indirim"
gibi ilgisiz bir yüzde kâr payı sanılabilir (gerçek bir hata, ölçülüp
düzeltildi — bkz. Bölüm 8).

### 3.3 Çözümleyici (resolver) yapısı

`extraction/hybrid_pipeline.py` — her katmanın adayları `_adaylar` ve
çakışmaları `_catismalar` olarak taşınır; final değer güven skoru + kaynak
güvenilirliği ile seçilir. `validation/verifier.py`, seçilen değerin kaynak
metinde (değer + bağlam) gerçekten geçtiğini ayrıca doğrular — bu sonuç artık
`dogrulanan_alanlar` sütununda kalıcıdır ve panelde görünür.

---

## 4. Kullanılan veri seti ve açıklaması

Tam metin: [`md6_veri_bolumu.md`](md6_veri_bolumu.md) §1 — burada özet:

- **Kaynak:** BDDK listesindeki 10 katılım bankasından 9'u (Adil Katılım
  gerekçeli hariç — ürün/kampanya sayfası yayımlamıyor).
- **Ham veri:** 251 tekil kampanya, 300 zaman damgalı anlık görüntü (delta
  kontrolü nedeniyle iki sayı farklı — bkz. bağlantılı belge §1.2).
- **Altın Veri Seti:** `gold_dataset/altin_veri_seti.json` — 58 elle
  doğrulanmış referans kayıt, her biri ekran görüntüsü kanıtıyla. Motorun
  çıktısından **doldurulmamıştır** (`tests/test_gold_etiketleme.py` bunu
  statik analizle kilitler).
- **Terminoloji sözlüğü:** `terminology/sozluk.json` — 31 katılım
  bankacılığı kavramı, geleneksel karşılığı ve tanım kaynağıyla.

---

## 5. Veri ön işleme adımları

Tam metin: [`md6_veri_bolumu.md`](md6_veri_bolumu.md) §2 — burada özet:

1. **HTML ayrıştırma** (`statik_scraper.py`) — banka-özel CSS seçicileriyle.
2. **JS ayrıştırma** (`js_scraper.py`) — Playwright, bugün hiçbir banka
   ihtiyaç duymuyor ama hazır ve test edilmiş.
3. **PDF ayrıştırma** (`pdf_isle.py`) — taranmış PDF tespiti dahil.
4. **Tablo ayrıştırma** (`tablo_isle.py`) — `pandas.read_html`.
5. **Türkçe normalizasyon** (`preprocessing/normalizer.py`) — sayı/oran/
   tarih ifadelerini bozmadan diyakritik/büyük-küçük harf varyasyonlarını
   normalize eder.
6. **Sayfa kapsamı ayıklama** (`preprocessing/kapsam.py`) — sayfa sonundaki
   çapraz kampanya bloklarını temizler (dar kapsamlı, ölçülmüş bir hatayı
   düzeltir — bkz. Bölüm 8).
7. **SHA-256 delta kontrolü** — içerik değişmemişse yeniden yazılmaz;
   bu hem idempotentlik hem de değişim tarihçesi özelliğinin temelidir.

---

## 6. Bankalar arası karşılaştırma nasıl yapılıyor

Şartname Md. 5.7'nin istediği "farklı katılım bankalarına ait ürünlerin
karşılaştırılabilir hale getirilmesi" üç farklı uç noktada, üç farklı
soruya cevap verecek şekilde uygulanmıştır — hepsi `comparison/` paketinde:

| Uç nokta | Soru | Yöntem |
|---|---|---|
| `POST /karsilastir` | "Seçtiğim N kampanyadan hangisi bu kriterde en iyi?" | Tek kritere göre sabit SQL şablonuyla sıralama; `en_avantajli` kompoziti şartnamenin kendi Örnek Senaryo-2'sindeki gibi eksen-eksen kazanan belirler (ağırlıklı formül **uydurulmaz**) |
| `GET /rakip-analizi` | "Bu pazarda kim nerede duruyor?" | Md. 5.7'nin tüm kriterleri, tüm kampanyalar için tek tabloda; ödül birimi karışıksa (Mil vs TL gibi) kazanan **seçilmez**, "karşılaştırılamaz" denir |
| `GET /kampanyalar/{id}/etki` | "Bu iyi bir kampanya mı?" | Kampanya kendi türündeki diğerleriyle kıyaslanır, her eksende yüzdelik dilimi hesaplanır; veri azsa (asgari 3 kampanya, 2 eksen) skor hiç üretilmez |

Üçünde de ortak ilke: **eksik veri gizlenmez**, uydurma sıralama/skor
üretilmez; hangi kampanyanın hangi alanı eksik olduğu ayrıca işaretlenir.

Ayrıca `scraper/scripts/kampanya_tarihcesi.py` + `GET
/kampanyalar/{id}/tarihce` — bir kampanyanın **zaman içindeki** değişimini
gösterir (statik karşılaştırmanın tamamlayıcısı — bkz. Bölüm 9, somut örnek).

---

## 7. Projenin çalıştırılması — kurulum ve adımlar

**Gereksinimler:** Python 3.11+, Docker Desktop, Node.js 18+ (dashboard için).

```bash
# 1) Altyapı (PostgreSQL, Qdrant, Ollama)
docker compose up -d

# 2) Python ortamı
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS/Linux
pip install -r requirements.txt

# 3) Veritabanı şeması
alembic upgrade head

# 4) API  →  http://localhost:8000/docs (Swagger)
uvicorn api.main:app --reload

# 5) Dashboard
cd dashboard && npm install && npm run dev
```

**Tek komutla (backend):** `python demo_baslat.py` — 1, 3, 4. adımları
servislerin gerçekten hazır olmasını bekleyerek tek seferde yapar;
`--mock` bayrağıyla Docker/DB hiç gerekmez.

**Çevrimdışı hazırlık kontrolü:** `python cevrimdisi_hazirlik_kontrolu.py`
— Ollama modeli, embedding modeli ve Docker imajlarının önceden internetten
indirilip yerel önbelleğe alındığını doğrular (Md. 5.9 on-premise
gereksinimi).

**Test çalıştırma:** `pytest -m "not slow"` (~2 dakika, LLM/Qdrant
gerektirmeyen 700+ test) veya `pytest` (tam paket, gerçek servisler
gerekir).

Tam ayrıntı ve ortam değişkenleri: [`README.md`](../README.md) "Kurulum ve
Çalıştırma" bölümü.

---

## 8. Karşılaşılan problemler ve çözüm yaklaşımları

Bu proje boyunca bulunan hataların ortak özelliği: **hiçbiri "çalışmıyor"
demiyordu.** Hepsi ya yanlış cevabı doğru gibi veriyordu, ya da doğru
cevabı hiç göstermiyordu — test edilmediği sürece görünmeyen, bir jüri
demosunda en kötü anda ortaya çıkabilecek türden hatalar. En önemlileri:

| Problem | Bulgu | Çözüm |
|---|---|---|
| **Regex kilitleme riski** | İlk katmanın doldurduğu alan sonraki katmanca düzeltilemiyordu | Aday + uzlaştırıcı mimarisi, 0,8 güven eşiği (Bölüm 2, 3) |
| **Sayfa kapsamı kirlenmesi** | Bir bankanın sayfası başka kampanyaların tutarını içeriyordu, çıkarım motoru bunu kendi kampanyasınınmış gibi okuyordu | `preprocessing/kapsam.py` — dar kapsamlı, yalnızca açık yönlendirme kalıbını temizler |
| **NER'in görünmeyen zararı** | Bir katmanın ölçülen F1 katkısı 0 çıktığında bu "zararsız" sanılabiliyordu, oysa "ölçülemedi" de olabilirdi | Ölçülebilirlik denetimi eklendi; GLiNER'in `finansman_tutari` alanındaki görünmez bozulması bulunup o alandan çıkarıldı |
| **Hesaplama aracında sessiz yanlış rakam** | "1234 TL" → 234,0 ve "%2,79" → 279,0 gibi, hata göstermeden yanlış sonuç üretiliyordu | Tutar/oran çözümleyicileri ayrıştırıldı, Türkçe ondalık formatına geçildi, sınır koşulları test edildi |
| **Diyakritik-duyarlı çıkarım** | Türkçe karakter kullanılmadan yazılan metinde alanlar sessizce boş dönüyordu | Uzunluk-koruyan katlama; üretim verisinde etki ölçüldü (0/300), yeni "metin yapıştır" ucunda risk gerçek olduğu için (263 belgenin %33'ü) düzeltildi |
| **Panelde görünürlük kopukluğu** (3 ayrı örnek) | Veri API katmanında zaten üretiliyordu ama yanıt şemasında karşılığı olmadığı için Pydantic sessizce düşürüyordu (kaynak alıntısı, doğrulama sütunu, kampanya tarihçesi, etki/rakip analizi audit bloğu) | Şemalara eksik alanlar eklendi, her biri uçtan uca test edildi |
| **Demo gününü kurtaran gecikme bulgusu** | İlk sohbet sorusu gömme modelini yüklediği için 54,9–81 sn sürüyordu, arayüz 10 sn'de zaman aşımına uğruyordu | İstemci zaman aşımı 90 sn'ye çıkarıldı + sunucu tarafında model ısıtma açılışa taşındı |

Her birinin tam ölçümü, kanıtı ve kod referansı:
[`extraction_accuracy_raporu.md`](extraction_accuracy_raporu.md).

---

## 9. Model çıktı örnekleri

### 9.1 Çıkarım — önce/sonra (hesaplama hatası düzeltmesi)

| Girdi | Eski çıktı | Doğrusu |
|---|---|---|
| `1234 TL` | `234,0` (başarılı=True) | `1234,0` |
| `%2.79` | `279,0` | `2,79` |

### 9.2 Çıkarım — diyakritik düzeltmesi (önce/sonra)

| Alan | "3 ay ödemesiz dönem" öncesi | Düzeltme sonrası |
|---|---|---|
| erteleme süresi | boş | 3 |
| hedef kitle | boş | Yeni müşteri |
| kampanya türü | boş | Yeni Müşteri Kampanyası |

### 9.3 POST /cikar — kanıt izli çıktı

Serbest metin yapıştırıldığında her alan, hangi katmanın doldurduğu, metindeki
kanıtı (`kaynak_span`), güveni ve Verifier'ın doğrulayıp doğrulamadığıyla
birlikte döner. Üç kanıt sınıfı ayrıştırılır:

| Sınıf | Anlamı | Örnek |
|---|---|---|
| `span` | Kanıt, metinden birebir kesilmiş alıntı | "12 ay vade" |
| `siniflandirma` | Kanıt bir etiket, metinde aynen geçmez | "Yeni Müşteri Kampanyası" |
| `türetilmiş` | Değer başka alanlardan hesaplanmış | ondalık kâr payı |

### 9.4 Kampanya değişim tarihçesi — gerçek örnek

Dünya Katılım'ın "avantajlı kurlar" kampanyası:

```json
{"kampanya_bitis": {"eski": "2026-07-30", "yeni": "2026-08-06"}}
```

Kampanya süresi uzatılmış — bu, sitenin sessizce güncellediği bir koşulun
otomatik olarak görünür kılınmasıdır (`GET /kampanyalar/{id}/tarihce`).

### 9.5 RAG — kaynaklı yanıt

Serbest bilgi sorularında sistem kaynak parçasını **birebir** döndürür,
üzerine cümle üretmez. Kaynak bulunamazsa: *"Bu soruyu yanıtlayacak yeterli
kaynak bulamadım."* — uydurma cevap üretilmez (bkz. Bölüm 10, Abstention).

---

## 10. Performans değerlendirme yöntemi

Metodoloji notu: sistem **tek bir "doğruluk" yüzdesiyle** raporlanmaz.
"Dolu alan" (bir alanı kaçırmak) ve "boş alan" (kaynakta olmayan bir değeri
uydurmak) doğruluğu **ayrı** ölçülür — yanlış bir değer hem yanlış-pozitif
hem yanlış-negatif sayılır (hata iki kez cezalandırılır). Bu, tek bir sayı
vermekten daha zor ama daha dürüsttür.

| Metrik | Değer | Yeniden üretim komutu |
|---|---|---|
| Makro F1 (çıkarım, 7 alan) | %98,28 | `python -m scraper.scripts.extraction_accuracy` |
| Makro Precision / Recall | %97,34 / %99,38 | (aynı komut) |
| Dolu alan doğruluğu | %98,48 (65/66) | (aynı komut) |
| Boş alan doğruluğu (yanlış pozitif) | %99,17 (120/121) | (aynı komut) |
| Ablation (regex / regex+NER / tam hibrit) | — | `python -m scraper.scripts.ablation` |
| Terminoloji hassasiyet / özgüllük | 24/24 · 10/10 | `pytest tests/test_karsi_ornekler.py -s` |
| RAG Recall@3 / @5 | %93,75 / %93,75 | `python -m scraper.scripts.rag_degerlendirme` |
| RAG Abstention (alan dışı soru) | %100 | (aynı komut) |
| Otomatik test | 774 test, 0 hata | `pytest -m "not slow"` |

**Dürüstçe raporlanan bilinen kısıtlar** (jürinin sorması beklenir):

1. **RAG Recall@5 gerilemesi** (%96,88→%93,75): indeks 733→817 parçaya
   büyüyünce adı neredeyse aynı iki kampanya ("...Sağlık Harcamalarına Vade
   Farksız 6 Taksit" / "...Eğitim Harcamalarınıza...") ayrışamaz oldu. Kod
   gerilemesi değil, korpus büyümesinin doğal sonucu; doğru müdahale
   (cross-encoder reranker) henüz yapılmadı, bilinçli olarak "sonraki iş"
   listesinde.
2. **Recall@1 deterministik değil** — Qdrant'ın varsayılan yaklaşık
   araması nedeniyle koşudan koşuya oynayabiliyor (29/30/29 ölçüldü);
   kesin arama (`exact=True`) ile ölçüm önerisi belgelenmiştir.
3. **Verifier ajan yanıt yoluna henüz bağlı değil** — çıkarım hattında
   çalışıyor ve sonucu panelde görünüyor, ama sohbet yanıtları bu
   kontrolden geçmiyor.

Tam ölçüm metodolojisi ve tüm ablation/karşı-örnek sonuçları:
[`extraction_accuracy_raporu.md`](extraction_accuracy_raporu.md),
[`rag_tasarim_ve_olcum.md`](rag_tasarim_ve_olcum.md).

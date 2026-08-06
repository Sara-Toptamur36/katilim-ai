# KatılımAI

Takım: **PeacewAI** — Fırat Üniversitesi, Yapay Zekâ ve Veri Mühendisliği

`BilisimVadisi2026` · Türkiye Açık Kaynak Platformu

---

## Durum

| Sprint | İçerik | Durum |
|---|---|---|
| **Sprint 1** | API sözleşmesi, uç noktalar, veri toplama, terminoloji sözlüğü, dashboard iskeleti | ✅ Tamamlandı |
| **Sprint 2** | Karşılaştırma motoru, hesap makinesi, hibrit çıkarım (regex+NER+LLM), PostgreSQL | ✅ Tamamlandı |
| **Sprint 3** | Ajan orkestratör, chatbot arayüzü | ✅ Tamamlandı |
| | Semantik chunking + embedding + Qdrant indeksleme | ✅ Tamamlandı |
| **Sprint 4** | Intent tespiti, Jüri Audit Paneli, gerçek JWT kimlik doğrulama | ✅ Tamamlandı |
| | RAG: hibrit arama + kaynaklı yanıt + abstention | ✅ Tamamlandı |

### Ölçülebilir durum

| Gösterge | Değer |
|---|---|
| Kapsanan katılım bankası | **9 / 10** (BDDK listesi; Adil Katılım gerekçeli hariç — ürün/kampanya yayımlamıyor) |
| Toplanan gerçek kampanya kaydı | **234** ham kayıt |
| Altın Veri Seti (elle doğrulanmış referans) | **58** kayıt + ekran görüntüsü kanıtı |
| Çıkarım — dolu alan doğruluğu | **~%86–89** (hibrit: regex+NER+LLM; aşağıdaki sapma notuna bakınız) |
| Çıkarım — dolu alan doğruluğu (yalnızca regex, deterministik) | **%84,38** |
| Çıkarım — boş alan doğruluğu (yanlış pozitif) | **%91,78** — 6 yanlış pozitif |
| RAG — indekslenen parça | **734** (234 belgeden, tekilleştirilmiş) |
| RAG — Recall@5 | **%96,88** (31/32 kampanya) |
| RAG — abstention doğruluğu | **%100** (5/5 alan dışı soruda cevap üretilmedi) |
| Otomatik test | **358** test, CI her push'ta çalışır |

> Çıkarım kalitesi **tek bir yüzdeyle** değil iki metrikle raporlanır: bir
> alanı *kaçırmak* ile kaynakta olmayan bir değeri *uydurmak* farklı
> ağırlıkta hatalardır ve ikincisi finansal kararlarda daha tehlikelidir.
> Yöntem ve tespit edilen yanlış pozitifler:
> [`docs/extraction_accuracy_raporu.md`](docs/extraction_accuracy_raporu.md)
>
> **Çalıştırmalar arası sapma:** LLM katmanı `temperature=0` ile çağrılsa da
> `hibrit_extraction_accuracy.py` her çalıştırmada birebir aynı yüzdeyi
> vermeyebilir (ölçüldü: aynı veri setinde %89,06 ↔ %87,5 arası oynama) —
> Ollama'nın kendi çalışma zamanı determinizmi tam garanti etmiyor. Bu bir
> regresyon değildir; script'i tekrar çalıştırıp farklı bir sayı görmek
> normaldir, birkaç çalıştırmanın ortalaması tek bir çalıştırmadan daha
> güvenilir bir gösterge kabul edilmelidir.

**Şu an:** Uç noktalar gerçek verilerle çalışır. Veri kaynağı `GERCEK_VERI_AKTIF`
ortam değişkeniyle seçilir (`false` = mock/sözleşme testi verisi, `true` = PostgreSQL).
Serbest/açık uçlu bilgi soruları RAG ile **kaynak göstererek** yanıtlanır;
kaynak bulunamazsa sistem **cevap uydurmak yerine açıkça çekimser kalır.**

---

## Problem

Katılım bankaları kampanya ve ürün bilgilerini standart olmayan, doğal dilde metinlerle paylaşır. Aynı bilgi bankadan bankaya tamamen farklı ifade edilir:

- `"%1,99 oranla 12 aya varan taksit"` — sayısal ve net
- `"98/2 kâr paylaşım oranı"` — yüzde değil, bambaşka bir gösterim
- `"Kâr payı yok. Beklemek yok."` — hiç sayı içermeyen üçüncü bir biçim

Ödül birimleri bile değişkendir: Mil, Gram, Bankkart Lira, ParafPara, Worldpuan.

Bu çeşitlilik, banka çalışanlarının ve son kullanıcıların ürünleri karşılaştırmasını zorlaştırır.

## Çözüm

Ham kampanya metninden karşılaştırılabilir yapılandırılmış veriye ve **kaynak gösteren** doğal dil yanıtlarına uzanan uçtan uca bir sistem:

Hedef mimari — `[✓]` kurulu ve çalışıyor, `[ ]` henüz kodlanmadı:

```
Banka kaynaklari (BDDK listesi)                              [✓]
        ↓
Scraper (statik + JS + PDF) → SHA-256 delta kontrolu         [✓]
        ↓                      (OCR henuz yok)               [ ]
Normalizasyon → Regex + NER + LLM hibrit cikarim             [✓]
        ↓
   ┌────────────────┬─────────────────┐
   ↓                                  ↓
PostgreSQL                 Semantik parcalama → Embedding
(ACTIVE/EXPIRED)      [✓]  + BM25 seyrek vektor → Qdrant    [✓]
   └────────────────┬─────────────────┘
                    ↓
            AJAN ORKESTRATOR                                 [✓]
    Intent Detection → Tool Router
        ↓      ↓      ↓      ↓      ↓
      SQL  Calculator Dict  RAG  Fallback
      [✓]     [✓]    [✓]   [✓]    [✓]
                    ↓        └─ hibrit arama (yogun+seyrek, RRF)
                    ↓           + abstention + citation
    Response Generator → Terminoloji Kontrolu                [✓]
    → Verifier                                              [ ]
                    ↓
    Dashboard · Chatbot · Juri Audit Paneli                  [✓]
```

**Sistemi bir "dil ajanı" yapan katman:** kullanıcı niyetini anlayıp doğru aracı seçen orkestrasyon. Sayısal karşılaştırma sabit SQL şablonlarıyla, hesaplamalar saf Python fonksiyonlarıyla yapılır — LLM'e bırakılmaz.

---

## Kurulum

### Gereksinimler
- Python 3.11+
- Docker Desktop
- Node.js 18+ (dashboard için)

### 1. Depoyu klonla
```bash
git clone <repo-adresi>
cd katilim-ai
```

### 2. Altyapı servislerini başlat
```bash
docker compose up -d
```
Bu, PostgreSQL (5432), Qdrant (6333) ve Ollama (11434) servislerini ayağa kaldırır.

Doğrulama:
```bash
docker ps
```

### 3. Python ortamı
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 4. Veritabanı şemasını uygula
```bash
alembic upgrade head
```

> **Ekip kuralı:** Şemayı değiştiren kişi migration dosyasını da commit'ler.
> Diğerleri `git pull` sonrası `alembic upgrade head` çalıştırır.

### 5. API'yi başlat
```bash
uvicorn api.main:app --reload
```

- API: http://localhost:8000
- **Swagger (interaktif dokümantasyon): http://localhost:8000/docs**

### 6. Dashboard
```bash
cd dashboard
npm install
npm run dev
```

### 7. (İsteğe bağlı) Gerçek veriyi yükle

Scraper çıktısını PostgreSQL'e aktarıp çıkarım motoruyla zenginleştirir:

```bash
python -m scraper.scripts.postgrese_yukle
python -m extraction.regex_ile_zenginlestir
```

Ardından API'yi gerçek veriyle çalıştırmak için `GERCEK_VERI_AKTIF=true` verin.

### 8. RAG indeksini kur

Chatbot'un serbest bilgi sorularını kaynak göstererek yanıtlaması için:

```bash
python -m chunking.indeksleyici
```

Ham kampanya metinlerini semantik olarak parçalar, hem anlamsal (embedding)
hem kelime (BM25) vektörü üretip Qdrant'a yazar. Tek seferlik toplu bir
iştir (~700 parça, birkaç dakika); indeks Qdrant volume'ünde kalır.

Retrieval kalitesini ölçmek için:
```bash
python -m scraper.scripts.rag_degerlendirme
```

### 9. (İsteğe bağlı) Yerel LLM

Hibrit çıkarımın LLM katmanı için:

```bash
ollama pull qwen2.5:7b-instruct-q4_K_M
```

> Ollama kurulu değilse sistem çalışmaya devam eder — LLM katmanı atlanır,
> regex + NER sonuçları kullanılır. GPU'suz makinelerde tek bir LLM çağrısı
> birkaç dakika sürebilir.

---

## API Kullanımı

Tüm uç noktalar `Authorization` başlığı gerektirir:

```
Authorization: Bearer <token>
```

Gerçek JWT doğrulaması `JWT_AKTIF=true` ortam değişkeniyle açılır. Varsayılan
(`false`) modda herhangi bir token kabul edilir — **başlık formatı iki modda da
aynıdır**, bu yüzden arayüz kodu geçişte hiç değişmez.

### Uç noktalar

| Metot | Yol | Açıklama |
|---|---|---|
| GET | `/` | Servis bilgisi (kimlik gerektirmez) |
| GET | `/saglik` | Health check |
| POST | `/token` | Kullanıcı adı/parola ile JWT alma (yalnızca `JWT_AKTIF=true` iken) |
| GET | `/kampanyalar` | Kampanya listesi (`?banka=` `?kampanya_turu=` ile filtreli) |
| GET | `/kampanyalar/{id}` | Tek kampanya detayı |
| POST | `/karsilastir` | Kampanya karşılaştırma |
| POST | `/hesapla` | Taksit/kâr payı hesabı (saf Python, LLM kullanılmaz) |
| POST | `/chat` | Doğal dilde soru-cevap (audit bilgisiyle) |

### Örnek

```bash
curl -H "Authorization: Bearer test-token" \
     "http://localhost:8000/kampanyalar?banka=Kuveyt%20T%C3%BCrk"
```

Gerçek JWT modunda kullanıcı oluşturma:

```bash
python -m api.scripts.kullanici_ekle
```

---

## Tasarım İlkeleri

**1. Eksik veri gizlenmez, işaretlenir.**
Bir alan kaynakta yoksa `null` bırakılır ve `alan_belirtilmemis` içinde bayraklanır. Karşılaştırmada `NULLS LAST` ile en sona gider — filtrelenip yok sayılmaz.

**2. Sayısal işler LLM'e bırakılmaz.**
Karşılaştırma sabit, parametreli SQL şablonlarıyla yapılır (serbest metinden SQL üretilmez). Taksit/kâr payı hesapları saf Python fonksiyonlarıdır.

**3. Her kayıt kaynağını taşır.**
Her kampanya kaydında kaynak URL ve belge tarihi tutulur; hangi alanı hangi
çıkarım katmanının (regex/NER/LLM) doldurduğu ve güven skoru izlenir.
*(Chunk ID ve benzerlik skoru alanları API sözleşmesinde hazırdır, RAG
bağlandığında dolacaktır — şu an boş döner.)*

**4. Şeffaflık iki kitleye ayrılır.**
Banka çalışanı iş odaklı dashboard'u görür; jüri/geliştirici, çağrılan aracı,
tespit edilen niyeti, çalıştırılan SQL'i, güven skorlarını ve gecikmeyi
gösteren ayrı bir Audit Paneli'ni.

**5. Bir katman çalışmazsa sistem durmaz.**
Hibrit çıkarımda regex → NER → LLM kademeli çalışır; Ollama kapalıysa veya
yanıt vermezse LLM katmanı sessizce atlanır ve deterministik katmanların
sonucu döner. Aynı şekilde niyet tespit edilemezse sistem uydurma cevap
üretmek yerine durumu açıkça bildirir.

**6. RAG kaynaksız cevap üretmez.**
Serbest bilgi soruları hibrit arama (anlamsal embedding + BM25 kelime araması,
RRF ile birleştirilir) ile yanıtlanır. Yanıt, bulunan kaynak parçalarını
**birebir** gösterir; üzerine serbest metin üretilmez — böylece halüsinasyon
yapısal olarak imkânsızdır.

Kaynak yeterli değilse sistem **cevap vermez.** Bu karar ham benzerlik
skoruna göre değil, sorunun ayırt edici terimlerinin kaynaklarda gerçekten
geçip geçmediğine göre verilir. Gerekçesi ölçüldü: yalnızca vektör
benzerliğine bakıldığında "uzay istasyonunda yerçekimi" gibi tamamen alakasız
bir soru bile 0,78 skor alıyordu
([`docs/qdrant_spike_raporu.md`](docs/qdrant_spike_raporu.md), Bulgu 2) —
yani skor eşiği tek başına yanlış pozitif üretirdi.

Eşik tahminle değil ölçümle seçildi; yöntem, kalibrasyon ve sonuçlar:
[`docs/rag_tasarim_ve_olcum.md`](docs/rag_tasarim_ve_olcum.md)

### Henüz kurulmayanlar (dürüstlük notu)

Aşağıdakiler hedef mimaride yer alır ancak **bu depoda henüz kodlanmamıştır**;
tasarım ilkesi olarak sunulmakla birlikte çalışan bir özellik değildir:

- **Verifier:** yanıttaki her sayının kaynak pasajda/araç çıktısında geçtiğini
  doğrulayan katman (`validation/` klasörü şu an boş).
- **Zaman aşımına bağlı otomatik fallback:** ölçülmüş bir p95 eşiğine göre
  deterministik katmana düşme.
- **LLM ile yanıt özetleme:** RAG şu an bulduğu kaynak parçalarını *birebir*
  döndürür, üzerine serbest metin üretmez — bu, halüsinasyonu yapısal olarak
  imkânsız kılar. Özetleme ancak Verifier ile birlikte güvenli olur.

---

## Proje Yapısı

```
katilim-ai/
├── api/              # FastAPI: uc noktalar, sema, kimlik dogrulama
├── scraper/          # Veri toplama (Zeynep)
├── preprocessing/    # Turkce normalizasyon
├── terminology/      # Katilim bankaciligi terminoloji sozlugu (Yagmur)
├── extraction/       # Regex + NER + LLM hibrit cikarim (Yagmur)
├── validation/       # (planlandi) Verifier - henuz bos
├── chunking/         # RAG: parcalayici, embedding, seyrek vektor, retriever, indeksleyici
├── storage/          # PostgreSQL + Qdrant erisimi
├── comparison/       # Karsilastirma motoru - SQL Tool (Sara)
├── calculator/       # Hesap makinesi araci (Sara)
├── agent/            # Ajan orkestrator + tool router (Sara)
├── dashboard/        # React + Ant Design arayuz (Havin)
├── gold_dataset/     # Altin Veri Seti (dogrulama referansi)
├── tests/            # Sozlesme, cikarim, regresyon ve entegrasyon testleri
└── docs/             # Proje dokumantasyonu + olcum raporlari
```

## Ekip ve Sorumluluklar

| Kişi | Sorumluluk |
|---|---|
| **Sara Toptamur** (Takım Kaptanı) | API, ajan orkestrasyon, karşılaştırma motoru, hesap makinesi, koordinasyon |
| **Yağmur Ekici** | NLP, bilgi çıkarımı, terminoloji, embedding, RAG |
| **Zeynep Sönmez** | Veri toplama, PDF/OCR, ön işleme, PostgreSQL, sistem testleri |
| **Havin Karagöz** | React arayüz, UI/UX, karşılaştırma ekranları, Jüri Audit Paneli |

---

## Teknoloji Yığını

Tüm bileşenler açık kaynaklıdır (şartname Md. 5.10 / 8):

| Katman | Teknoloji | Lisans |
|---|---|---|
| Veri toplama | Requests, BeautifulSoup4, Playwright | Apache-2.0 / MIT / BSD |
| PDF | pypdf | BSD |
| Bilgi çıkarımı | regex, GLiNER (`urchade/gliner_multi-v2.1`) | MIT / Apache-2.0 |
| Yerel LLM | Qwen2.5-Instruct (GGUF Q4_K_M), Ollama | Apache-2.0 / MIT |
| Yapılandırılmış çıktı | Pydantic | MIT |
| Vektör veritabanı | Qdrant | Apache-2.0 |
| İlişkisel veritabanı | PostgreSQL | PostgreSQL License |
| API | FastAPI, SQLAlchemy, Alembic | MIT |
| Arayüz | React, Ant Design | MIT |

**Kullanılmayanlar:** özel/custom lisanslı LLM'ler, AGPL kütüphaneler, kapalı kaynak bulut API'leri, ücretli servisler.

> **NER model tercihi:** Önce BERTurk (`dbmdz/bert-base-turkish-cased`) denendi;
> bu checkpoint NER için fine-tune edilmemiş olduğundan span çıkarımında
> kullanılamadı. Yerine zero-shot çalışan GLiNER seçildi — gerekçe
> [`extraction/ner_extractor.py`](extraction/ner_extractor.py) başında belgelenmiştir.
>
> **OCR:** Taranmış/görüntü PDF'ler için OCR bu depoda kurulu değildir
> (Tesseract binary'si ayrı yerel kurulum gerektirir). Metin tabanlı PDF'ler
> pypdf ile işlenir; taranmış bir PDF'te metin boş dönerse kayıt düşük güven
> skoruyla işaretlenir, sessizce doğru varsayılmaz.

**Sürüm sabitleme:** Tüm Python bağımlılıkları `requirements.txt`'te tam sürümle
(`==`), Docker imajları da sabit etiketle sabitlenmiştir — aynı commit her
makinede aynı sürümlerle kurulur.

---

## Test

```bash
pytest tests/ -v
```

CI, `main` dalına her push'ta testleri ve sızmış sır taramasını otomatik çalıştırır.

Bazı testler dış servis gerektirir ve servis yoksa **hata vermez, atlanır**:

| Test grubu | Gereksinim | Servis yoksa |
|---|---|---|
| Veritabanı testleri | PostgreSQL (`docker compose up -d postgres`) | atlanır |
| LLM / hibrit testleri | Ollama + Qwen2.5 modeli | atlanır |
| Vektör arama testleri | Qdrant (`docker compose up -d qdrant`) + embedding modeli | atlanır |

Bu yüzden CI'da (dış servis yok) test sayısı yerelden düşük görünür — bu bir
regresyon değil, beklenen durumdur.

Çıkarım doğruluğunu Altın Veri Seti'ne karşı ölçmek için:

```bash
python -m scraper.scripts.extraction_accuracy         # yalnizca regex
python -m scraper.scripts.hibrit_extraction_accuracy  # regex + NER + LLM
```

---

## Lisans

[Apache License 2.0](LICENSE)

Şartname madde 8 gereği, tüm kaynak kodlar, veri kümeleri ve diğer bileşenler yarışma bitiş tarihinde Apache License 2.0 ile lisanslanarak Türkiye Açık Kaynak Platformu GitHub hesabında paylaşılacaktır.

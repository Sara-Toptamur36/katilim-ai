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
| Çıkarım — dolu alan doğruluğu (yalnızca regex, deterministik) | **%96,88** |
| Çıkarım — boş alan doğruluğu (yanlış pozitif) | **%98,36** — 2 yanlış pozitif (122 ölçülebilir alan) |
| Çıkarım — alan bazlı makro F1 (regex) | **%93,72** (6 ölçülebilir alan; kırılım aşağıda) |
| RAG — indekslenen parça | **734** (234 belgeden, tekilleştirilmiş) |
| RAG — Recall@5 | **%96,88** (31/32 kampanya) |
| RAG — abstention doğruluğu | **%100** (5/5 alan dışı soruda cevap üretilmedi) |
| Otomatik test | **442** test, CI her push'ta çalışır |

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

Hedef mimari — `[✓]` kurulu ve çalışıyor, `[~]` modül hazır ama bu yola
henüz bağlanmadı, `[ ]` henüz kodlanmadı:

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
    → Verifier (modul hazir, cikarimda kullaniliyor;
      ajan yanit yoluna henuz baglanmadi)                    [~]
                    ↓
    Dashboard · Chatbot · Juri Audit Paneli                  [✓]
```

**Sistemi bir "dil ajanı" yapan katman:** kullanıcı niyetini anlayıp doğru aracı seçen orkestrasyon. Sayısal karşılaştırma sabit SQL şablonlarıyla, hesaplamalar saf Python fonksiyonlarıyla yapılır — LLM'e bırakılmaz.

---

## Kurulum ve Çalıştırma

**Gereksinimler:** Python 3.11+, Docker Desktop, Node.js 18+ (dashboard için).
Tüm Python bağımlılıkları sürümleriyle sabitlenmiş olarak
[`requirements.txt`](requirements.txt) dosyasındadır.

```bash
# 1) Altyapı (PostgreSQL 5432, Qdrant 6333, Ollama 11434)
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

> **Ekip kuralı:** Şemayı değiştiren kişi migration dosyasını da commit'ler;
> diğerleri `git pull` sonrası `alembic upgrade head` çalıştırır.

### Tek komutla demo (backend)

Adım 1, 3, 4'ü (Docker + alembic + API, servislerin gerçekten hazır olması
beklenerek) tek seferde yapar — adım atlama/sıra karıştırma riskini kaldırır.
Arayüz (adım 5) ayrı kalır, farklı bir terminalde `cd dashboard && npm run dev`
ile başlatılır.

```bash
python demo_baslat.py          # gercek veriyle (Docker + PostgreSQL + Qdrant)
python demo_baslat.py --mock   # mock veriyle, Docker/DB GEREKMEZ
```

### Çevrimdışı hazırlık kontrolü

Md. 5.9 (on-premise), sistemin internetsiz çalışabilmesini gerektirir; ama
Ollama modeli, embedding modeli ve Docker imajları **ilk kullanımda**
internetten iner. Demo günü internet olmayabileceği için, internet varken
önceden bir kez çalıştırıp hepsi `[OK]` olana kadar eksikleri tamamlayın:

```bash
python cevrimdisi_hazirlik_kontrolu.py
```

### Gerçek veriyi yükle (isteğe bağlı)

```bash
python -m scraper.scripts.postgrese_yukle      # ham veriyi PostgreSQL'e aktar
python -m extraction.regex_ile_zenginlestir    # finansal alanları çıkar
python -m chunking.indeksleyici                # RAG indeksini kur (~700 parça)
ollama pull qwen2.5:7b-instruct-q4_K_M         # hibrit çıkarımın LLM katmanı
```

API'yi gerçek veriyle çalıştırmak için `GERCEK_VERI_AKTIF=true` verin.
Ollama kurulu değilse sistem çalışmaya devam eder — LLM katmanı atlanır,
regex + NER sonuçları kullanılır.

**Veri seti** depoya dâhildir: [`gold_dataset/`](gold_dataset/) (elle
doğrulanmış referans + ekran görüntüleri), [`scraper/raw_data/`](scraper/raw_data/)
(ham kampanya metinleri).

### Donanım profili

Sistem çalıştığı makineye göre **kendini otomatik ayarlar** — LLM çıkarım
süresi donanıma göre 10 kattan fazla değişiyor, tek sabit ayar iki makineye
birden uymuyor. Makineyi test etmek için:

```bash
python donanim_testi.py           # donanım + servisler + embedding/LLM hız ölçümü
python donanim_testi.py --hizli   # LLM testini atla (uzun sürer)
```

Çıktı; donanımı, seçilen profili, servislerin (Qdrant/Ollama/PostgreSQL)
durumunu, ölçülmüş embedding ve LLM sürelerini ve tam indeksleme tahminini
içerir — olduğu gibi paylaşılabilir. Ayarları kalıcı değiştirmek için
[`.env.ornek`](.env.ornek) dosyasını `.env` olarak kopyalayın.

| Profil | Ne zaman | Bağlam | Zaman aşımı | Kırpılan belge |
|---|---|---|---|---|
| **gpu** | VRAM ≥ 8 GB | 16384 | 300 sn | **0 / 234** |
| **cpu** | GPU yok **veya** VRAM < 8 GB | 4096 | 900 sn | 12 / 234 |

Otomatik seçim ezilebilir:

```bash
KATILIMAI_PROFIL=gpu          # profili zorla (gpu | cpu)
LLM_BAGLAM_PENCERESI=16384    # tek ayarı ezle
LLM_ZAMAN_ASIMI=600
EMBEDDING_YIGIN_BOYUTU=128
```

> **Neden bağlam penceresi açıkça gönderilir:** Ollama, istekte `num_ctx`
> verilmezse modeli 4096 ile servis eder (model 32768 desteklese bile) ve
> uzun promptu **sessizce kırpar** — hata dönmez, yalnızca çıkarım kalitesi
> düşer. Bu, `ollama ps` çıktısıyla doğrulanmış gerçek bir tuzaktır.

### Uç noktalar

Tümü `Authorization: Bearer <token>` başlığı ister. Gerçek JWT doğrulaması
`JWT_AKTIF=true` ile açılır; **başlık formatı iki modda da aynıdır**, bu yüzden
arayüz kodu geçişte değişmez.

| Metot | Yol | Açıklama |
|---|---|---|
| GET | `/` · `/saglik` | Servis bilgisi / health check (kimlik gerektirmez) |
| POST | `/token` | Kullanıcı adı-parola ile JWT (yalnızca `JWT_AKTIF=true`) |
| GET | `/kampanyalar` | Kampanya listesi (`?banka=` `?kampanya_turu=`) |
| GET | `/kampanyalar/{id}` | Tek kampanya detayı |
| POST | `/karsilastir` | Kampanya karşılaştırma |
| POST | `/hesapla` | Taksit/kâr payı hesabı (saf Python, LLM yok) |
| POST | `/chat` | Doğal dilde soru-cevap (kaynak + audit bilgisiyle) |

```bash
curl -H "Authorization: Bearer test-token" \
     "http://localhost:8000/kampanyalar?banka=Kuveyt%20T%C3%BCrk"
```

---

## Tasarım İlkeleri

**1. Eksik veri gizlenmez, işaretlenir.**
Bir alan kaynakta yoksa `null` bırakılır ve `alan_belirtilmemis` içinde bayraklanır. Karşılaştırmada `NULLS LAST` ile en sona gider — filtrelenip yok sayılmaz.

**2. Sayısal işler LLM'e bırakılmaz.**
Karşılaştırma sabit, parametreli SQL şablonlarıyla yapılır (serbest metinden SQL üretilmez). Taksit/kâr payı hesapları saf Python fonksiyonlarıdır.

Şartname Md. 5.7'nin örnek kriter listesindeki 5 kriter (`comparison/compare_engine.py`):

| Kriter | Alan |
|---|---|
| En Düşük Kâr Payı Oranı (`en_dusuk_kar_payi`) | `kar_payi_orani_percent` |
| En Yüksek Ödül Miktarı (`en_yuksek_odul`) | `odul_miktari` |
| En Uzun Vade Seçeneği (`en_uzun_vade`) | `vade_ay` |
| En Düşük Masraf (`en_dusuk_masraf`) | `tahsis_ucreti` |
| En Avantajlı Kampanya (`en_avantajli`) | kompozit — diğer 4 kriterin eksen eksen karşılaştırması, Örnek Temsili Senaryo-2'deki yöntemle birebir |

`en_avantajli` tek bir ağırlıklı formül uydurmaz: her alt kriterde hangi kampanyanın öne çıktığı ayrı ayrı belirlenir (`- Kâr payı oranı açısından C Bankası daha avantajlı ...` biçiminde), en çok eksende öne çıkan genel kazanan sayılır; eşitlikte tek bir kazanan uydurulmaz. Ayrıca şartnamenin listesinde olmayan bonus bir kriter de var: `en_yuksek_tutar` (`finansman_tutari`).

**Bonus: Toplam Maliyet Karşılaştırma.** `en_avantajli` ve diğer kriterler ham alanları (oran/vade/masraf) sıralar; ama "düşük oran = ucuz demek değildir" — uzun vadeli düşük oranlı bir kampanya, kısa vadeli yüksek oranlıdan toplamda daha pahalı olabilir. `/chat`'e "500.000 TL için X Bankası ile Y Bankası'nın **toplam maliyetini karşılaştır**" diye sorulduğunda (`agent/router.py::toplam_maliyet_aracini_cagir`, `calculator/calculator.py::toplam_maliyet_karsilastir`), her bankanın kendi oran/vadesiyle gerçek bir amortisman hesabı yapılır — LLM'e bırakılmaz, saf Python.

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
sonucu döner.

Ajan tarafında da aynı kademelilik var: seçilen araç yetersiz kalırsa
sistem vazgeçmez, soruyu RAG'e sorar. Gerekçesi ölçüldü — *"Ziraat Katılım
kart kampanyalarında **taksit** var mı?"* sorusu yalnızca "taksit" kelimesi
yüzünden hesap makinesine gidiyor ve kullanıcıya *"Hesaplama için şu
bilgiler eksik: anapara…"* deniyordu; oysa bu bir bilgi sorusu ve cevabı
kaynaklarda var. Hangi aracın neden yetmediği audit kaydında korunur.
RAG de kaynak bulamazsa sistem yine **açıkça çekimser kalır.**

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

**7. Kapsam dışı veri gizlenmez, ayrıldığı kanıtlanır.**
Sistemin katılım bankacılığı ile geleneksel bankacılığı ayırt edebildiğini
*ölçebilmek* için geleneksel bankacılık ifadelerinden bir karşı-örnek seti
tutulur. Bu ifadeler **yalnızca kapsam sınıflandırması ve Scope Guard ölçümü**
amacıyla kullanılır; üretim kampanya veritabanına ve RAG indeksine **dâhil
edilmez**. İfadeler elle yazılmıştır — hiçbiri gerçek bir bankadan
kopyalanmamış, hiçbiri gerçek bir bankaya atfedilmemiştir
([`tests/veri/kapsam_disi/`](tests/veri/kapsam_disi/)).

Bu bir iddia olarak bırakılmaz. Ayrımı, her push'ta çalışan bir test
doğrular — karşı-örnek ifadelerinin `scraper/raw_data` ve `gold_dataset`
içinde geçmediğini tarar:

```
tests/test_karsi_ornekler.py::test_karsi_ornekler_veritabanina_girmemis
```

Set aynı zamanda bir **ölçüm aracıdır**: 24 geleneksel bankacılık ifadesi
yakalanmalı (hassasiyet), 10 meşru katılım ifadesi yakalanmamalıdır
(özgüllük). Tek yön ölçülseydi "her cümleyi işaretle" diyen bir kontrol de
tam not alırdı. Güncel sonuç: **24/24 ve 10/10**, bir bilinen sınırlama
belgeli. Ayrıntı: [`docs/kapsam_ve_veri_ayrimi.md`](docs/kapsam_ve_veri_ayrimi.md)

### Henüz kurulmayanlar (dürüstlük notu)

Aşağıdakiler hedef mimaride yer alır ancak **bu depoda henüz tamamlanmamıştır**;
tasarım ilkesi olarak sunulmakla birlikte uçtan uca çalışan bir özellik değildir:

- **Verifier'ın ajan yanıt yoluna bağlanması:** `validation/verifier.py`
  yazıldı ve gerçek veriyle ölçüldü (6/6 yanlış pozitif doğru şekilde
  reddedildi, 41 gerçek iddianın 37'si onaylandı — yöntem ve bilinen
  sınırlar modülün kendi başlığında belgelidir), ancak şu an yalnızca
  **çıkarım** tarafındaki sayısal iddiaları doğrular; `/chat` yanıt
  zincirinde çağrılmaz. Bu yolda doğrulanacak *üretilmiş* bir sayı
  olmadığı için (RAG birebir alıntı döndürür) şimdilik gerekmiyor;
  LLM ile özetleme eklenirse ikisi **birlikte** bağlanmalıdır.
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
├── preprocessing/    # Turkce normalizasyon + sayfa kapsami ayiklama
├── terminology/      # Katilim bankaciligi terminoloji sozlugu (Yagmur)
├── extraction/       # Regex + NER + LLM hibrit cikarim (Yagmur)
├── validation/       # Verifier - sayisal iddialari kaynak metne karsi dogrular
├── chunking/         # RAG: parcalayici, embedding, seyrek vektor, retriever, indeksleyici
├── storage/          # PostgreSQL + Qdrant erisimi
├── comparison/       # Karsilastirma motoru - SQL Tool (Sara)
├── calculator/       # Hesap makinesi araci (Sara)
├── agent/            # Ajan orkestrator + tool router (Sara)
├── dashboard/        # React + Ant Design arayuz (Havin)
├── gold_dataset/     # Altin Veri Seti (dogrulama referansi)
├── tests/            # Sozlesme, cikarim, regresyon ve entegrasyon testleri
├── docs/             # Proje dokumantasyonu + olcum raporlari
├── donanim.py        # Donanim profili (GPU/VRAM tespiti + ayarlar)
└── donanim_testi.py  # Tanilama + hiz olcumu (baska makinede calistirilir)
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
python -m scraper.scripts.ablation                    # katman katkisi tablosu
```

Ölçüm çıktısı **alan bazlı precision/recall/F1** de basar; `ablation`
ise üç varyantı (regex / +NER / +NER+LLM) karşılaştırıp her katmanın
katkısını ayrıştırır. Sonuçlar ve yorumu:
[`docs/extraction_accuracy_raporu.md`](docs/extraction_accuracy_raporu.md)

---

## Lisans

[Apache License 2.0](LICENSE)

Şartname madde 8 gereği, tüm kaynak kodlar, veri kümeleri ve diğer bileşenler yarışma bitiş tarihinde Apache License 2.0 ile lisanslanarak Türkiye Açık Kaynak Platformu GitHub hesabında paylaşılacaktır.

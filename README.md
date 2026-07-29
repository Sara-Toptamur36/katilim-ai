# KatılımAI

Takım: **PeacewAI** — Fırat Üniversitesi, Yapay Zekâ ve Veri Mühendisliği

`BilisimVadisi2026` · Türkiye Açık Kaynak Platformu

---

## Durum

| Sprint | İçerik | Durum |
|---|---|---|
| **Sprint 1** (1. hafta) | API sözleşmesi, mock uç noktalar, veri toplama (3 banka), terminoloji sözlüğü, dashboard iskeleti | 🚧 Devam ediyor |
| Sprint 2 (2. hafta) | Karşılaştırma motoru, hesap makinesi, hibrit çıkarım, PostgreSQL | ⬜ Planlandı |
| Sprint 3 (3. hafta) | Ajan orkestratör, chunking + embedding + Qdrant, chatbot arayüzü | ⬜ Planlandı |
| Sprint 4 (4. hafta) | RAG, Intent Classifier, Jüri Audit Paneli, güvenlik sertleştirme | ⬜ Planlandı |

**Şu an:** Uç noktalar mock veri döndürmektedir. Gerçek mantık sprint sprint bağlanacaktır.

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

```
Banka kaynaklari (BDDK/TKBB dogrulamali)
        ↓
Scraper (statik + JS + PDF/OCR) → SHA-256 delta kontrolu
        ↓
Normalizasyon → Regex + NER + LLM hibrit cikarim → Validator
        ↓
   ┌────────────────┬─────────────────┐
   ↓                                  ↓
PostgreSQL                    Embedding (bge-m3) → Qdrant
(ACTIVE/EXPIRED)                      ↓
   └────────────────┬─────────────────┘
                    ↓
            AJAN ORKESTRATOR
    Intent Detection → Tool Router
        ↓      ↓      ↓      ↓      ↓
      SQL  Calculator Dict  RAG  Fallback
                    ↓
    Response Generator → Terminoloji Kontrolu
    → Verifier → Provenance Injection
                    ↓
    Dashboard · Chatbot · Juri Audit Paneli
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

### 6. Dashboard (Sprint 1'de eklenecek)
```bash
cd dashboard
npm install
npm run dev
```

---

## API Kullanımı

Tüm uç noktalar `Authorization` başlığı gerektirir:

```
Authorization: Bearer <token>
```

> Sprint 1-3'te herhangi bir token kabul edilir (mock doğrulama).
> Sprint 4'te gerçek JWT devreye girer — **başlık formatı değişmez**,
> yalnızca doğrulama sertleşir. Bu sayede arayüz kodu hiç değişmez.

### Uç noktalar

| Metot | Yol | Açıklama |
|---|---|---|
| GET | `/` | Servis bilgisi (kimlik gerektirmez) |
| GET | `/saglik` | Health check |
| GET | `/kampanyalar` | Kampanya listesi (`?banka=` `?kampanya_turu=` ile filtreli) |
| GET | `/kampanyalar/{id}` | Tek kampanya detayı |
| POST | `/karsilastir` | Kampanya karşılaştırma |
| POST | `/chat` | Doğal dilde soru-cevap (audit bilgisiyle) |

### Örnek

```bash
curl -H "Authorization: Bearer test-token" \
     "http://localhost:8000/kampanyalar?banka=C%20Bankasi"
```

---

## Tasarım İlkeleri

**1. Eksik veri gizlenmez, işaretlenir.**
Bir alan kaynakta yoksa `null` bırakılır ve `alan_belirtilmemis` içinde bayraklanır. Karşılaştırmada `NULLS LAST` ile en sona gider — filtrelenip yok sayılmaz.

**2. Sayısal işler LLM'e bırakılmaz.**
Karşılaştırma sabit, parametreli SQL şablonlarıyla yapılır (serbest metinden SQL üretilmez). Taksit/kâr payı hesapları saf Python fonksiyonlarıdır.

**3. Her cevap kaynağını gösterir.**
Kaynak URL, belge tarihi, chunk ID ve benzerlik skoru yanıta iliştirilir.

**4. Her cevap doğrulanır.**
Verifier, LLM yanıtındaki sayıların aracın döndürdüğü ham sonuçta gerçekten bulunup bulunmadığını kontrol eder.

**5. Canlı demo güvenliği.**
Bir sorgu 5 saniye içinde yanıtlanamazsa sistem otomatik olarak deterministik katmana düşer.

**6. Şeffaflık iki kitleye ayrılır.**
Banka çalışanı iş odaklı dashboard'u görür; jüri/geliştirici, çağrılan aracı, çalıştırılan SQL'i, güven skorlarını ve gecikmeyi gösteren ayrı bir Audit Paneli'ni.

---

## Proje Yapısı

```
katilim-ai/
├── api/              # FastAPI: uc noktalar, sema, kimlik dogrulama
├── scraper/          # Veri toplama (Zeynep)
├── preprocessing/    # Turkce normalizasyon
├── terminology/      # Katilim bankaciligi terminoloji sozlugu (Yagmur)
├── extraction/       # Regex + NER + LLM hibrit cikarim (Yagmur)
├── validation/       # Pydantic sema + confidence + consistency
├── chunking/         # Semantik chunking + embedding (Yagmur)
├── storage/          # PostgreSQL + Qdrant erisimi
├── comparison/       # Karsilastirma motoru - SQL Tool (Sara)
├── calculator/       # Hesap makinesi araci (Sara)
├── agent/            # Ajan orkestrator + tool router (Sara)
├── dashboard/        # React + Ant Design arayuz (Havin)
├── gold_dataset/     # Altin Veri Seti (dogrulama referansi)
├── tests/            # API sozlesme testleri
└── docs/             # Proje dokumantasyonu
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
| PDF / OCR | pypdf, pytesseract / PaddleOCR | BSD / Apache-2.0 |
| Bilgi çıkarımı | regex, BERTurk, GLiNER | MIT / Apache-2.0 |
| Yerel LLM | Qwen2.5-Instruct (GGUF Q4_K_M), Ollama | Apache-2.0 / MIT |
| Yapılandırılmış çıktı | Pydantic | MIT |
| Vektör veritabanı | Qdrant | Apache-2.0 |
| İlişkisel veritabanı | PostgreSQL | PostgreSQL License |
| API | FastAPI, SQLAlchemy, Alembic | MIT |
| Arayüz | React, Ant Design | MIT |

**Kullanılmayanlar:** özel/custom lisanslı LLM'ler, AGPL kütüphaneler, kapalı kaynak bulut API'leri, ücretli servisler.

---

## Test

```bash
pytest tests/ -v
```

CI, `main` dalına her push'ta testleri ve sızmış sır taramasını otomatik çalıştırır.

---

## Lisans

[Apache License 2.0](LICENSE)

Şartname madde 8 gereği, tüm kaynak kodlar, veri kümeleri ve diğer bileşenler yarışma bitiş tarihinde Apache License 2.0 ile lisanslanarak Türkiye Açık Kaynak Platformu GitHub hesabında paylaşılacaktır.

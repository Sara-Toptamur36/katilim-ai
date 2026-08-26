# KatılımAI — Jüri Dokümantasyonu

> **TEKNOFEST 2026 · Yapay Zekâ Dil Ajanları Yarışması · Senaryo 2**
> Takım **PeacewAI** — Fırat Üniversitesi, Yapay Zekâ ve Veri Mühendisliği
> Depo: <https://github.com/Sara-Toptamur36/katilim-ai> · Lisans: Apache-2.0

---

## Bu belge nasıl okunmalı

Bu belge, jürinin projeyi **doğrulayarak** okuyabilmesi için hazırlandı. Üç kural:

1. **Her sayının bir tarihi ve bir üretim komutu vardır.** Sayı verildiği yerde,
   hangi veri kümesinde ve hangi tarihte ölçüldüğü de yazar. Ölçüm komutları
   §29'da toplu hâlde.
2. **Ölçülmemiş şeye "ölçüldü" denmez.** Eksik olan ölçümler §25'te açıkça
   listelenir. Bu belgede geçen hiçbir sayı tahmin değildir.
3. **Bilinmeyen alanlar işaretlidir.** `⚠ EKİP DOLDURACAK` etiketi taşıyan
   satırlar, bu belge yazılırken depodan doğrulanamayan bilgilerdir; uydurma
   yerine boş bırakılmıştır.

**Ölçüm tarihleri (bu belgenin temel aldığı kesit):**

| Ne | Tarih | Nerede ölçüldü |
| --- | --- | --- |
| Veri hacmi (kampanya/banka dağılımı) | 26 Ağustos 2026 | Canlı PostgreSQL |
| Çıkarım doğruluğu (11 alan) | 26 Ağustos 2026 | 291 canlı kayıt |
| RAG Recall / çekimserlik | 25 Ağustos 2026 | 1875 parçalık indeks |
| Otomatik test | 26 Ağustos 2026 | GitHub Actions CI |

> **Neden RAG'in tarihi farklı:** Canlı RAG indeksi 26 Ağustos'ta 2127 parçaya
> büyüdü, ama Recall o boyutta **yeniden ölçülmedi**. Arayüzde ve bu belgede
> ikisi ayrı ayrı gösterilir — büyümüş indeksin sayısını ölçülmüş gibi sunmak
> yanlış olurdu. Bu, bilinen ve kayıtlı bir eksiktir (§25).

---

## 0. Proje Kimliği

| Soru | Cevap |
| --- | --- |
| **0.1** Resmî ad | **KatılımAI** |
| **0.2** Takım | **PeacewAI** — Fırat Üniversitesi, Yapay Zekâ ve Veri Mühendisliği |
| **0.4** Tek cümle | KatılımAI, 9 katılım bankasının dağınık ve standart olmayan kampanya metinlerini karşılaştırılabilir yapılandırılmış veriye çeviren ve her cevabı kaynağıyla gösteren bir dil ajanıdır. |
| **0.10** GitHub | <https://github.com/Sara-Toptamur36/katilim-ai> (herkese açık) |
| **0.11** Sunum tarihi/yeri | ⚠ EKİP DOLDURACAK |

### 0.3 Takım üyeleri ve sorumluluklar

| Kişi | Sorumluluk |
| --- | --- |
| **Sara Toptamur** (Takım Kaptanı) | API, ajan orkestrasyon, karşılaştırma motoru, hesap makinesi, koordinasyon |
| **Yağmur Ekici** | NLP, bilgi çıkarımı, terminoloji, embedding, RAG |
| **Zeynep Sönmez** | Veri toplama, PDF, ön işleme, PostgreSQL, sistem testleri |
| **Havin Karagöz** | React arayüz, UI/UX, karşılaştırma ekranları, Jüri Audit Paneli |

### 0.5–0.6 Problem ve önemi

Katılım bankaları kampanya bilgisini standart olmayan, doğal dilde metinlerle
paylaşır. **Aynı bilgi bankadan bankaya tamamen farklı ifade edilir:**

- `"%1,99 oranla 12 aya varan taksit"` — sayısal ve net
- `"98/2 kâr paylaşım oranı"` — yüzde değil, bambaşka bir gösterim
- `"Kâr payı yok. Beklemek yok."` — hiç sayı içermeyen üçüncü bir biçim

Ödül birimleri bile değişkendir: Mil, Gram, Bankkart Lira, ParafPara, Worldpuan.

Bu çeşitlilik, banka çalışanının ve son kullanıcının ürünleri **karşılaştırmasını
imkânsıza yakın** hâle getirir. Finansal kararların yanlış okunan bir orana
dayanması, doğrudan maddi sonuç doğurur.

### 0.7 Hedef kullanıcılar

| Kullanıcı | Ne için kullanır | Sistemdeki rol |
| --- | --- | --- |
| Banka çalışanı | Rakip analizi, kampanya karşılaştırma | `banka_calisani` |
| Denetleyici | Çıkarım izi denetimi | `denetleyici` |
| Yönetici | Genel bakış + denetim | `yonetici` |
| Müşteri / son kullanıcı | Soru-cevap, hesap makinesi | `musteri` (self-servis kayıt) |
| Jüri / demo kullanıcısı | Audit Paneli, Çıkarım Denetimi | Tüm denetim ekranları açık (§20.3) |

### 0.8–0.9 Şartname ve değerlendirme

Proje **Senaryo 2**'ye cevap verir. Şartname maddeleriyle eşleşme §30'da.

**0.9 Değerlendirme ağırlıkları:** ⚠ EKİP DOLDURACAK — *soru setinde
"%20 Fonksiyonellik · %20 Teknik Mimari · %20 On-Premise · %30 Model Başarısı ·
%10 Yenilikçilik" örneği geçiyor, ancak bu belge yazılırken şartname metni
depoda bulunmadığı için doğrulanamadı. Sunumdan önce şartnameden teyit edilmeli.*

---

## 1. Problem ve Çözüm

**1.1–1.3** Bugün kullanıcı bu problemi **elle** çözüyor: her bankanın sitesine
tek tek girip kampanyaları okuyup kafasında karşılaştırıyor. Eksiklikler: (a)
ölçek — 9 banka × onlarca kampanya, (b) standart yokluğu — aynı bilgi farklı
biçimlerde, (c) tazelik — kampanyalar sessizce değişiyor veya kaldırılıyor, (d)
terminoloji — "faiz" ile "kâr payı" karıştırılıyor.

**1.4 Temel çözüm:** Ham metinden karşılaştırılabilir yapılandırılmış veriye ve
**kaynak gösteren** doğal dil yanıtlarına uzanan uçtan uca bir hat.

**1.5–1.7 Diğer chatbotlardan farkı — üç yapısal karar:**

1. **RAG kaynağı birebir döndürür, üzerine metin üretmez.** Halüsinasyon
   "azaltılmaz", **yapısal olarak imkânsız** kılınır: model serbest cümle
   kurmadığı için uyduramaz.
2. **Sayısal işler LLM'e bırakılmaz.** Karşılaştırma sabit parametreli SQL
   şablonlarıyla, hesaplamalar saf Python fonksiyonlarıyla yapılır. Serbest
   metinden SQL üretilmez.
3. **Kaynak yetersizse sistem cevap vermez.** Çekimserlik kararı ham benzerlik
   skoruna değil, sorunun ayırt edici terimlerinin kaynaklarda gerçekten geçip
   geçmediğine bakar (§8.16).

**1.6 Neden ajan mimarisi:** Kullanıcı soruları tek tip değil — "en düşük kâr
payı hangisi" bir SQL sorusu, "500.000 TL'nin taksiti ne olur" bir hesap, "murabaha
nedir" bir sözlük sorusu, "X kampanyasının şartları" bir RAG sorusu. Hepsini tek
bir LLM promptuna vermek, deterministik olabilecek işleri olasılıklı hâle
getirirdi.

**1.9 Genel amaçlı LLM'ler bu problemi neden çözmüyor:** güncel kampanya verisine
sahip değiller (veri tazeliği), kaynak gösteremezler (denetlenebilirlik) ve
kurumsal veriyi dışarı göndermeyi gerektirirler (on-premise gereksinimi §21).

**1.10 "Vade farksız" vakası — ölçülmüş bir hata:** İki ayrı commit **zıt yönde**
karar verdi: biri altın veriye `kar_payi_orani = 0` yazdı, diğeri motordan aynı
kuralı kaldırdı. İkisi ayrı ayrı savunulabilirdi, birlikte tutarsızdı ve kâr payı
recall'unu **%90,91 → %15,38**'e düşürdü. Kombinasyonu kimse yeniden ölçmediği
için fark edilmedi. Düzeltme sonrası kâr payı F1 **%26,09 → %80,00**.
Artık `tests/test_olcum_kapsami.py` bu kombinasyonu **imkânsız kılıyor**.

> Bu vaka projenin ölçüm disiplininin neden var olduğunu gösterir: iki doğru
> kararın birleşimi yanlış olabilir ve bunu yalnızca **yeniden ölçüm** yakalar.

---

## 2. Sistem Mimarisi

### 2.1–2.7 Teknoloji yığını

| Katman | Teknoloji | Lisans |
| --- | --- | --- |
| Arayüz | React, Vite, Ant Design | MIT |
| API | FastAPI, SQLAlchemy, Alembic | MIT |
| İlişkisel VT | PostgreSQL | PostgreSQL License |
| Vektör VT | Qdrant | Apache-2.0 |
| Embedding | `intfloat/multilingual-e5-base` (768 boyut) | MIT |
| Yerel LLM | Qwen2.5-Instruct GGUF Q4_K_M (Ollama) | Apache-2.0 / MIT |
| Bulut LLM (ops.) | EVREN `llm-fast` | TEKNOFEST kaynağı |
| NER | GLiNER `urchade/gliner_multi-v2.1` | Apache-2.0 |
| Yapılandırılmış çıktı | Pydantic | MIT |
| Veri toplama | Requests, BeautifulSoup4, Playwright | Apache-2.0 / MIT / BSD |
| PDF | pypdf | BSD |

**Kullanılmayanlar:** özel/custom lisanslı LLM'ler, AGPL kütüphaneler, kapalı
kaynak bulut API'leri, ücretli servisler.

> **Fine-tuning yoktur.** Kullanılan modeller açık kaynak ve **olduğu gibi**,
> sürümü sabitlenmiş biçimde çalışır. Bu kural `tests/test_iddia_durustlugu.py`
> ile korunur: bir belgeye yanlışlıkla eğitim iddiası yazılırsa CI kırmızı verir.
> **Yeniliğimiz modeli eğitmek değil, hangi katmanın ne kadar katkı verdiğini
> (ve nerede zarar verdiğini) ölçmüş olmak.**

### 2.8–2.9 Altı katman ve akış

```
Banka kaynakları (BDDK listesi)                              [✓]
        ↓
1. VERİ TOPLAMA: Scraper (statik + JS + PDF)
   → SHA-256 delta kontrolü                                  [✓]
        ↓                      (OCR henüz yok)               [ ]
2. ÖN İŞLEME: Türkçe normalizasyon + sayfa kapsamı ayıklama  [✓]
        ↓
3. ÇIKARIM: Regex → GLiNER → LLM hibrit + Resolver           [✓]
        ↓
   ┌────────────────┬─────────────────┐
   ↓                                  ↓
4. DEPOLAMA                  Semantik parçalama → Embedding
   PostgreSQL           [✓]  + BM25 seyrek vektör → Qdrant   [✓]
   └────────────────┬─────────────────┘
                    ↓
5. AJAN ORKESTRATÖR                                          [✓]
   Intent Detection → Tool Router
        ↓      ↓      ↓      ↓      ↓
      SQL  Calculator Dict  RAG  Fallback
      [✓]     [✓]    [✓]   [✓]    [✓]
                    ↓        └─ hibrit arama (yoğun+seyrek, RRF)
                    ↓           + abstention + citation
   Response Generator → Terminoloji Kontrolü                 [✓]
   → Zaman aşımı tabanlı fallback                            [✓]
   → Verifier (karşılaştırma + toplam maliyet yoluna bağlı)  [✓]
                    ↓
6. SUNUM: Dashboard · Chatbot · Jüri Audit Paneli            [✓]
```

`[✓]` kurulu ve çalışıyor · `[ ]` henüz kodlanmadı

### 2.10 On-Premise tasarım kararları

| Servis | Yerel mi? | Not |
| --- | --- | --- |
| PostgreSQL | ✅ Tamamen yerel | Docker, port 5432 |
| Qdrant | ✅ Tamamen yerel | Docker, port 6333 |
| Ollama + Qwen2.5 | ✅ Tamamen yerel | Docker, port 11434 |
| Embedding modeli | ✅ Yerel | İlk indirmeden sonra çevrimdışı |
| EVREN | ⚠ Çevrimiçi, **opsiyonel** | `EVREN_API_KEY` yoksa devreye girmez |

**EVREN devreye girmeden önce sistem neyle çalışıyordu:** yerel Qwen2.5 ile —
ve **hâlâ öyle çalışabilir**. EVREN, LLM katmanında Ollama'ya **alternatif bir
sağlayıcıdır**; mimari ve çıktı sözleşmesi değişmez.

Çevrimdışı hazırlık kontrolü: `python cevrimdisi_hazirlik_kontrolu.py`
Bu betik EVREN'i **offline sonucuna dahil etmez** — EVREN tanım gereği
çevrimiçidir, ayrı bir "opsiyonel" başlığı altında raporlanır.

### 2.12 Servisler arası iletişim

REST/HTTP. Arayüz → FastAPI (JSON), FastAPI → PostgreSQL (SQLAlchemy),
FastAPI → Qdrant (HTTP), FastAPI → Ollama (HTTP), FastAPI → EVREN
(OpenAI-uyumlu HTTP). Mesaj kuyruğu veya gRPC kullanılmaz.

### 2.13 Donanım gereksinimleri

Sistem çalıştığı makineye göre **kendini otomatik ayarlar** — LLM çıkarım
süresi donanıma göre 10 kattan fazla değişir.

| Profil | Ne zaman | Bağlam | Zaman aşımı | Kırpılan belge |
| --- | --- | --- | --- | --- |
| **gpu** | VRAM ≥ 8 GB | 16384 | 300 sn | **0 / 234** |
| **cpu** | GPU yok **veya** VRAM < 8 GB | 4096 | 900 sn | 12 / 234 |

**Asgari:** Python 3.11+, Docker Desktop, Node.js 18+. GPU **zorunlu değil**
(CPU profili çalışır, yalnızca yavaştır). Makineyi ölçmek için:
`python donanim_testi.py`

> **Bilinen tuzak (ölçülmüş):** Ollama, istekte `num_ctx` verilmezse modeli
> 4096 ile servis eder (model 32768 desteklese bile) ve uzun promptu **sessizce
> kırpar** — hata dönmez, yalnızca kalite düşer. Bu yüzden bağlam penceresi
> açıkça gönderilir.

---

## 3. Veri Kaynakları

| Soru | Cevap |
| --- | --- |
| **3.1** Kaynak | 9 katılım bankasının **resmî kampanya sayfaları** |
| **3.2** Taranan banka | **10** (BDDK listesi) |
| **3.3** Veri yayımlayan | **9** — Adil Katılım gerekçeli hariç: ürün/kampanya yayımlamıyor |
| **3.4** Yapılandırılmış kayıt | **536** (PostgreSQL, 26 Ağustos) |
| **3.5** Anlık görüntü | **623** · tekil taranmış sayfa: **525** |

### Üç sayı neden farklı — bu bir tutarsızlık değil

| Sayı | Ne ölçer |
| --- | --- |
| **525** | `scraper/raw_data`'daki **tekil URL** sayısı (ham sayfa) |
| **623** | Toplam **anlık görüntü** — aynı URL'nin farklı tarihli taramaları dahil |
| **536** | PostgreSQL'de **yapılandırılmış kayıt** sayısı |

Scraper eski taramaları **silmez** — değişiklik takibi (SHA-256 delta) bunu
gerektirir. Bu fazlalık bir artık değil, bir **özelliğin girdisi**: aynı URL'nin
birden fazla tarihli kaydı olması o kampanyanın **gerçekten güncellendiği**
anlamına gelir.

### 3.9 Banka bazında dağılım (canlı, 26 Ağustos)

| Banka | Kampanya | Sayfa türü | Not |
| --- | --- | --- | --- |
| Kuveyt Türk | 110 | HTML | Çerez duvarı — Playwright seçicisi |
| Ziraat Katılım | 109 | HTML | |
| Vakıf Katılım | 100 | HTML | |
| Türkiye Emlak Katılım | 84 | HTML | |
| Dünya Katılım | 45 | HTML | |
| Albaraka Türk | 37 | HTML | Mobil-kod kampanyaları zor (§7.7 EX-AL) |
| Türkiye Finans | 25 | HTML | Maliyet tablosu — ayrı katman okur |
| T.O.M. Katılım | 13 | HTML | Dijital banka |
| Hayat Finans | 13 | HTML | Dijital banka |
| **Adil Katılım** | **—** | — | **Kapsam dışı**: kampanya/ürün yayımlamıyor |
| **Toplam** | **536** | | |

> **Düşük sayı ≠ tarama eksikliği.** T.O.M. Katılım ve Hayat Finans'ta 13'er
> kampanya olması bir kapsam boşluğu değil, o bankaların sitesinde **o an yayında
> olan** kampanya sayısıdır. Bu ayrım arayüzde de açıkça yazar.

### 3.6–3.8, 3.10 Toplama ve delta motoru

**Yöntemler:** statik HTML (requests + BeautifulSoup4), JavaScript render
(Playwright — çerez duvarı ve dinamik listeler için), PDF (pypdf).
**OCR kurulu değildir** (§25).

**3.10 SHA-256 delta motoru:** Her taramada sayfa içeriğinin hash'i alınır.
Hash değişmemişse **yeni dosya yazılmaz**. Değişmişse yeni tarihli bir anlık
görüntü eklenir — eski silinmez.

Bu, "değişti" demenin ötesine geçmeyi sağlar: 251 kampanyanın **40**'ında içerik
değişmiş, ama bunların yalnızca **25**'inde izlenen bir alan (oran, vade, tutar,
ödül, tarih) gerçekten farklılaşmış. Kalan 15'i yalnızca metin düzeltmesi.
**Kozmetik değişiklik bildirimi gürültüdür.**

Ölçülmüş örnek: Dünya Katılım'ın "avantajlı kurlar" kampanyasının bitiş tarihi
`2026-07-30 → 2026-08-06` olmuş — süre uzatılmış.

```python
from scraper.scripts.kampanya_tarihcesi import tarihce_getir, degisen_alanlari_bul
tarihce = tarihce_getir("https://www.dunyakatilim.com.tr/kampanyalar/avantajli-kurlar")
degisen_alanlari_bul(tarihce)
# {'kampanya_bitis': {'eski': '2026-07-30', 'yeni': '2026-08-06'}}
```

**3.11 Etik scraping:** Her banka yapılandırmasında `crawl_delay: 1` (saniye)
tanımlı — sitelere yük bindirilmez. Yalnızca herkese açık kampanya sayfaları
taranır; giriş gerektiren hiçbir alan taranmaz.

**3.12 Kampanya kaldırılırsa:** Kayıt **silinmez**, `EXPIRED` olarak işaretlenir
ve tarihçede kalır. Ölçülmüş örnek: T.O.M. Katılım'ın 3 kampanyasından 2'si
(restoran ve market iade) 18 Ağustos taramasında sitede bulunamadı — **canlı sayfa
elle kontrol edilerek** scraper hatası olmadığı doğrulandı.

---

## 4. PostgreSQL

**4.2 `kampanyalar` tablosunun izlenen alanları:** `banka`, `kampanya_adi`,
`kampanya_turu`, `kaynak_url`, `kar_payi_orani_percent`, `vade_ay`,
`finansman_tutari`, `odul_miktari`, `odul_birimi`, `taksit_sayisi`,
`erteleme_suresi_ay`, `tahsis_ucreti`, `masraf_durumu`, `kampanya_baslangic`,
`kampanya_bitis`, `hedef_kitle`, `kar_payi_tablosu`, `alan_belirtilmemis`,
`dogrulanan_alanlar`, `belge_tarihi`.

**4.3 Sayı farkları:** §3'teki tabloda açıklandı (525 ham / 623 snapshot / 536 kayıt).

**4.7 Kampanya türü sınıflandırması (Md. 5.4)** — canlı dağılım:

| Tür | Adet | Oran |
| --- | --- | --- |
| Kart Kampanyası | 400 | %74,6 |
| *(Belirlenemedi — `NULL`)* | 61 | %11,4 |
| Ticari Kampanya | 17 | %3,2 |
| Finansman Kampanyası | 13 | %2,4 |
| Yeni Müşteri Kampanyası | 12 | %2,2 |
| İhtiyaç Finansmanı | 10 | %1,9 |
| Yatırım Ürünü | 8 | %1,5 |
| Taşıt Finansmanı | 6 | %1,1 |
| Konut Finansmanı / Sigorta-BES / POS | 3+3+3 | %1,7 |

Sınıflandırma **otomatiktir** (anahtar kelime + LLM katmanı). F1: **%81,88**
(23 Ağustos'ta %35,63 idi — §7).

**4.8 `alan_belirtilmemis` neden önemli:** `null` iki farklı şey anlamına
gelebilir — "kaynakta yok" veya "çıkaramadık". Bu ayrım finansal kararda
kritiktir: masrafın "belirtilmemiş" olması "masraf yok" demek **değildir**.
Bu yüzden alan `null` bırakılır **ve** `alan_belirtilmemis` içinde bayraklanır;
karşılaştırmada `NULLS LAST` ile en sona gider, filtrelenip yok sayılmaz.

**4.9 Migration:** Alembic. Ekip kuralı: *şemayı değiştiren kişi migration
dosyasını da commit'ler; diğerleri `git pull` sonrası `alembic upgrade head`
çalıştırır.*

**4.10 Yedekleme:** ⚠ EKİP DOLDURACAK — *Docker volume (`pgdata`) kalıcıdır;
ayrı bir otomatik yedekleme politikası bu depoda tanımlı değildir.*

---

## 5. Veri Çıkarım Sistemi

### 5.1–5.2 Çıkarılan alanlar — **11 alan ölçülüyor**

`kar_payi_orani_percent`, `vade_ay`, `finansman_tutari`, `odul_miktari`,
`odul_birimi`, `taksit_sayisi`, `erteleme_suresi_ay`, `kampanya_turu`,
`hedef_kitle`, `kampanya_baslangic`, `kampanya_bitis`

Ayrıca ölçüm dışı tutulan alanlar: `tahsis_ucreti`, `masraf_durumu`,
`kar_payi_tablosu`, `kampanya_avantaji`.

### 5.3–5.8 Pipeline ve çatışma çözümü

```
Regex  →  GLiNER  →  Qwen2.5 / EVREN llm-fast  →  Resolver
(det.)    (zero-shot NER)   (yapılandırılmış çıktı)   (çatışma)
```

- **5.4 Regex:** sayısal çekirdek — oran, vade, tutar, taksit, ödül, erteleme, tarih.
- **5.5 NER:** metinde geçen ama desene oturmayan varlıklar (ödül birimi, segment).
- **5.6 LLM:** regex/NER'in boş bıraktığı **sınıflandırma** alanları
  (`kampanya_turu`, `hedef_kitle`) — ölçülen katkı: makro F1 %80,66 → **%82,50**.
- **5.7–5.8 Resolver:** Katmanlar çatışırsa **daha yüksek güvenli ve kaynakta
  doğrulanmış** olan kazanır. Regex bir değeri **bilerek reddettiyse** (düşük
  güven, yanlış bağlam) NER/LLM onu geri koyamaz — bu bilinçli bir kısıttır.

### 5.9–5.10 Uydurma değer üretmeme garantisi

Üç mekanizma birlikte:

1. **Bulunamayan alan `null` kalır ve adıyla listelenir** — sıfır yazılmaz.
   Arayüzde "Belirtilmemiş" görünür.
2. **Verifier**, her sayısal değeri kaynak metinde (değer + bağlam) arar;
   sonucu `dogrulanan_alanlar` sütununda kalıcılaşır (§16.10).
3. **Kanıt spanı** (`kaynak_span`) — değerin metinde birebir geçtiği cümle
   saklanır ve Çıkarım Denetimi ekranında gösterilir (§17).

> **Uydurma sıfırın gerçek zararı ölçüldü:** Tutar ayrıştırmasındaki bir hata
> `"10000 TL"`yi **100.0** okuyordu; `ZK-009`'da ödül miktarı **0.0** çıkıyordu.
> Bu yalnızca yanlış değil **aktif olarak zararlıydı**: `en_dusuk_kar_payi`
> kriteri ASC sıraladığı için uydurma sıfır **her karşılaştırmayı kazanıyordu**.
> Altı ayrı desende tekrarlayan kusur tek bir `_SAYI` parçasına çekildi.

### 5.12 GLiNER

Hazır, **zero-shot** model: `urchade/gliner_multi-v2.1`. Sıfırdan eğitilmedi.
Önce BERTurk (`dbmdz/bert-base-turkish-cased`) denendi; bu checkpoint NER için
fine-tune edilmemiş olduğundan span çıkarımında **kullanılamadı** — gerekçe
`extraction/ner_extractor.py` başında belgelenmiştir.

### 5.14 Kanıt spanı (evidence span)

Değerin metinde birebir geçtiği alıntı. **Neden önemli:** bir sayının doğru
olduğunu iddia etmekle, o sayının kaynakta nerede yazdığını göstermek farklı
şeylerdir. Jüriye `Çıkarım Denetimi` ekranında alan alan gösterilir.

### 5.16–5.17 Çözülmüş kök nedenler (26 Ağustos)

| Problem | Kök neden | Sonuç |
| --- | --- | --- |
| **İlgisiz kampanya listesi** | Sayfanın kendi içeriği bittikten sonra gelen *başka* kampanyaların taksit/ödül ifadeleri o kaydın değeri sanılıyordu | Sayfa kapsamı ayıklaması |
| **İstisna cümlesi olumlu sanılıyordu** | *"Business kartlar dahil değildir"* ifadesi kampanyayı "Ticari Kampanya" yapıyordu | `kampanya_turu` %35,63 → **%81,88** |
| **Türkçe çekim ekleri** | Desende `"6 taksite"`, `"3 Ay Erteleme"` yoktu | `taksit_sayisi` **%89,50** |
| **Maliyet tablosu yanlış pozitifi** (`TF-001`, `TF-008`) | Bir satırda yan yana 5-6 yüzde (`3 \| 4,20% \| 0,50% \| 5,77%`); 45 karakterlik bağlam penceresi satır başındaki `Maliyet` başlığına yetişemiyordu | Tablolar ayrı katman okur (`tablo_extractor.py`) |

---

## 6. Altın Veri Seti (Gold Dataset)

| Soru | Cevap |
| --- | --- |
| **6.2** Toplam kayıt | **302** |
| **6.3** İnsan doğrulaması | **302 / 302** — tamamı imzalı, taslak kalmadı |
| **6.4** Ekran görüntüsü | **298** dosya (`gold_dataset/ekran_goruntuleri/`) — kanıt arşivi |
| **6.5** Kim doğruluyor | Takım üyeleri; her kayıt kaynağa karşı elle kontrol edilip imzalanır |

**6.1 Neden var:** Ölçüm için bir referans olmadan "doğruluk" iddiası
edilemez. Altın veri seti, motorun çıktısının karşılaştırıldığı **insan
doğrulamalı** referanstır.

**6.6–6.7 Dairesellik yasağı:** Altın veri seti **üretim sistemine bağlanmaz.**
Motor kendi ürettiği veriyle ölçülemez — bu, sınavı kendi cevap anahtarıyla
yapmak olurdu. Yasak testle korunur.

**6.8–6.10 Train/test ayrımı:** Kümelendirme temellidir. Benzer kampanyalar
(ör. `AL-005` ve `AL-006` — adları neredeyse aynı: *"…Vade Farksız 6 Taksit
Kampanyası"*) aynı kümede tutulur ve **birlikte** aynı tarafa düşer.
Küme haritası `gold_dataset/kume_haritasi.json`, bölme kaydı
`gold_dataset/split_manifest_v1.json`.

**6.12 `split_manifest_v1.json` ne güvence sağlar:** bölmenin **sabit ve
denetlenebilir** olduğunu — ölçümden ölçüme rastgele değişip sonuçları
kıyaslanamaz hâle getirmediğini.

**6.15 Eşdeğer kampanya işaretlemesi:** RAG ölçümünde "doğru cevap" bazen tek
bir kampanya değildir — korpusta içerik olarak eşdeğer birden fazla kampanya
olabilir. Bunlar `rag_esdeger_kampanya_listesi.py` ile işaretlenir; aksi hâlde
sistem **doğru** bir kampanyayı getirdiği hâlde "kaçırdı" sayılırdı (§9.9).

---

## 7. Çıkarım Metrikleri

> **Ölçüm:** 26 Ağustos 2026 · **291 canlı kayıt** · 11 alan
> **Komut:** `python -m scraper.scripts.extraction_accuracy`
> **Rapor:** [`cikarim_dogruluk_raporu.json`](../cikarim_dogruluk_raporu.json)

| Metrik | Hibrit (çalışan sistem) | Regex-only (deterministik taban) |
| --- | --- | --- |
| **7.1** Dolu alan doğruluğu | **%81,68** | %77,40 |
| **7.2** Boş alan doğruluğu (yanlış pozitif kontrolü) | **%96,88** | %97,45 |
| **7.3** Makro F1 | **%82,50** | %80,66 |
| Makro Precision | %82,78 | %83,12 |
| Makro Recall | %84,12 | %81,24 |

### 7.10 Alan bazlı F1 (11 alan)

| Alan | Regex-only | **Hibrit** | 23 Ağustos | Not |
| --- | --- | --- | --- | --- |
| `kampanya_baslangic` | %97,67 | **%97,67** | R %20,27 | Precision %100 |
| `kampanya_bitis` | %95,90 | **%95,69** | — | |
| `erteleme_suresi_ay` | %94,74 | **%94,74** | — | |
| `odul_birimi` | %90,43 | **%90,82** | — | |
| `odul_miktari` | %89,36 | **%90,36** | — | |
| `taksit_sayisi` | %88,48 | **%89,50** | — | |
| `kampanya_turu` | %81,88 | **%81,88** | %35,63 | ↑ Md. 5.4 |
| `kar_payi_orani_percent` | %80,00 | **%80,00** | %26,09 | ↑ "vade farksız" düzeltmesi |
| `finansman_tutari` | %72,73 | **%72,73** | — | |
| `vade_ay` | %61,54 | **%57,14** | — | ⚠ hibritte **düştü** |
| `hedef_kitle` | %34,48 | **%56,95** | R %19,67 | ↑ En büyük LLM katkısı |

**7.5 En başarılı alan:** `kampanya_baslangic` (%97,67)
**7.6 En problemli alan:** `vade_ay` (%57,14) ve `hedef_kitle` (%56,95)

> **Dürüstlük notu — `vade_ay` hibritte düştü** (%61,54 → %57,14). LLM katmanı
> her alanda iyileştirme yapmaz; bu alanda **zarar verdi**. Bunu gizlemiyoruz:
> katman katkısı alan bazında farklıdır ve tek bir ortalama bunu saklar.

### 7.7 Bilinen hatalar (açıkça raporlanır)

| Kod | Alan | Açıklama |
| --- | --- | --- |
| **EX-AL** | Kampanya avantajı (Albaraka) | Albaraka Mobil üzerinden **kodla** alınan indirim kampanyalarında (13 kayıt) metinde hiç "kart" geçmiyor; mevcut desenler yakalayamıyor |
| **DK-002** | Ödül miktarı (Dünya Katılım) | Gold *davet başına birim* ödülü, motor metnin öne çıkardığı *toplam tavanı* esas alıyor — hangisinin doğru olduğu **yorum gerektiriyor**, bilerek açık bırakıldı |

### Hâlâ açık iki alan — gerekçesiyle

- **`kampanya_baslangic`**: R %95,45'e çıktı ama kalan kaçırmalar çoğu sayfada
  başlangıç tarihinin **hiç yazmamasından** kaynaklanıyor — motorun ulaşabileceği
  bir bilgi değil.
- **`hedef_kitle`**: Gold'daki baskın sınıf ("Belirli segment", ~140 kayıt) bir
  **insan çıkarımıdır** — etiketi yazan kişi ürün adından anlam çıkarmış, o cümle
  metinde aynen geçmiyor. Kural genişleterek kapatılabilecek bir boşluk değil;
  **denendi ve ölçümle reddedildi**.

### 7.11–7.12 Yanlış pozitif ve üretim

Boş alan doğruluğu %96,88 → 291 kayıt × 11 alan üzerinden yanlış pozitif oranı
**%3,12**. En çok `kar_payi_orani` ve `finansman_tutari` alanlarında görülür
(tablolu sayfalar).

> **Neden iki ayrı metrik:** Bir alanı *kaçırmak* ile kaynakta olmayan bir değeri
> *uydurmak* farklı ağırlıkta hatalardır ve **ikincisi finansal kararlarda daha
> tehlikelidir.** Tek bir yüzde bu ikisini birbirinin arkasına saklardı.

---

## 8. RAG Sistemi

| Parametre | Değer |
| --- | --- |
| **8.3–8.4** Chunking | Semantik parçalama · hedef **700** karakter · asgari **60** |
| **8.6** Embedding | `intfloat/multilingual-e5-base` — **768** boyut |
| **8.7–8.8** Qdrant (ölçümün yapıldığı) | **1875** parça / **513** belge (25 Ağustos) |
| **8.7–8.8** Qdrant (canlı, güncel) | **2127** parça / **623** belge (26 Ağustos) |
| **8.10** Top-K | Üretimde **limit=3** (`agent/router.py`); ölçümde k=1/3/5 |
| **8.16** Çekimserlik eşiği | Leksikal örtüşme **≥ 0,60** |

### 8.14 Hibrit arama (Dense + Sparse + RRF)

**Dense embedding neden yeterli değil:** anlamsal benzerlik, kampanya adı gibi
**ayırt edici özel isimleri** yeterince ağırlıklandırmıyor. **Sparse BM25** kelime
eşleşmesini geri getirir. İkisi **RRF (Reciprocal Rank Fusion)** ile birleştirilir.

### 8.16 Çekimserlik — neden skor eşiği değil, leksikal örtüşme

```
Örtüşme = |Soru kökleri ∩ Kaynak kökleri| / |Soru kökleri|
Eşik    : ≥ 0,60
```

**Gerekçe ölçüldü:** Yalnızca vektör benzerliğine bakıldığında *"uzay
istasyonunda yerçekimi"* gibi **tamamen alakasız** bir soru bile **0,78** skor
alıyordu ([`docs/qdrant_spike_raporu.md`](qdrant_spike_raporu.md), Bulgu 2).
Ayrıca RRF skoru bir **sıralama** birleştirme skorudur — en üstteki sonuç sorgu
alakalı olsun olmasın ~1,0 civarı alır. **İkisi de eşik için kullanılamaz.**

### 8.12–8.13 Kaynak gösterimi ve çekimserlik

RAG yanıtında **chunk ID, benzerlik skoru ve kaynak parçanın birebir metni**
(`Kaynak.metin`) döner. Sistem üzerine serbest metin üretmez.
Kaynak yetersizse **cevap vermez** — uydurmaz.

### 8.18 EVREN Qdrant

Yerel Qdrant kullanılıyor. EVREN'in hibrit getirme ve rerank uçları
**bu istemciden çağrılmaz** — dokümantasyonun kendi ölçümünde hibrit+rerank
saf yoğun aramadan **düşük** çıkıyordu (0,55 vs 0,95). Gerekçe:
[`docs/adr/0002-evren-cikarim-entegrasyonu.md`](adr/0002-evren-cikarim-entegrasyonu.md)

---

## 9. RAG Değerlendirmesi

> **Ölçüm:** 25 Ağustos 2026 · **1875** parçalık indeks · `exact=True`
> **Komut:** `python -m scraper.scripts.rag_degerlendirme`

| Metrik | Değer | Not |
| --- | --- | --- |
| **9.3** Recall@1 | **%72,09** | HNSW yaklaşık arama nedeniyle koşular arası oynar |
| **9.4** Recall@3 | **%84,50** | |
| **9.5** Recall@5 | **%87,60** | |
| **9.6** Çekimserlik — alan dışı | **%86,67** (13/15) | |
| **9.6** Çekimserlik — alan içi kapsam dışı | **%40,0** izole · **%90,0** uçtan uca | §9.11 |

**9.1–9.2 Soru seti:** Depoda **185** soruluk kategorili set var; yukarıdaki
Recall değerleri bunun `exact=True` ile koşulan **129** sorgulu alt kümesinde
ölçüldü. Kategoriler ve son kategori bazlı kırılım:

| Kategori | Recall@5 | Not |
| --- | --- | --- |
| Tam ad | %97,87 (46/47) | Kampanya adı birebir veriliyor |
| Kısmi ad | %95,35 (41/43) | |
| Doğal soru | %87,50 (14/16) | |
| **Banka + konu** | **%52,17** (12/23) | **En zor** — kampanya adı verilmiyor |

**9.7 Başarısız örnekler var ve raporlanıyor:** `banka_ve_konu` kategorisi
kasıtlı olarak zor tasarlandı — kullanıcı kampanya adını bilmeden *"X bankası
kart kampanyası"* diye soruyor. Leksikal arama kampanya adına dayandığı için
ayırt edicilik kayboluyor. **Bu bir kod hatası değil**, dense-arama sınırının
doğal sonucu — ve **reranker ihtiyacını** gösteriyor.

**9.9 Birden fazla doğru cevap:** Eşdeğer kampanyalar işaretlenir (§6.15);
sistem eşdeğerlerden birini getirdiğinde **isabet** sayılır.

**9.11 `alan_ici_kapsam_disi` çekimserliği neden düşüktü ve nasıl çözüldü:**
"hesap açmak için hangi belgeler gerekli", "şifremi unuttum", "TMSF güvencesi"
gibi sorular **alan içi ama kapsam dışı**. "hesap", "belge", "şifre" kelimeleri
kampanya metinlerinin genel bankacılık dağarcığından olduğu için leksikal
örtüşme **yanlışlıkla** %60 eşiğini aşıyordu.

Tam dağılım ölçüldü: bu kategorinin aralığı (0,50–0,83) gerçekten cevaplanabilir
soruların aralığıyla **iç içe** — yani **eşiği yükseltmek bu sorunu çözmez**,
gerçek soruları da susturur. **Doğru çözüm:** RAG'e hiç sormadan, **niyet
katmanında** ayıklamak → `KAPSAM_DISI` niyeti eklendi (§10). Uçtan uca
çekimserlik böylece **%90,0**'a çıktı.

> Bu, projenin ölçüm disiplininin bir örneğidir: "eşiği yükselt" ilk akla gelen
> çözümdü, **ölçüm onu reddetti** ve doğru katmanı gösterdi.

**9.10 EVREN standalone karşılaştırması:** ⚠ EKİP DOLDURACAK — *soru setinde
Recall@1 %21,88 / Recall@3 %49,38 / Recall@5 %62,50 / MRR 0,4157 değerleri
geçiyor; bu belge yazılırken depoda bu ölçümün çıktısı bulunamadı. Bkz.
`docs/adr/0002-evren-cikarim-entegrasyonu.md`.*

---

## 10. AI Ajan

### 10.1–10.2 Araçlar ve niyetler

| Niyet | Araç | Ne yapar |
| --- | --- | --- |
| `HESAPLAMA` | `hesaplama_aracini_cagir` | Taksit/kâr payı — **saf Python** |
| `KARSILASTIRMA` | `karsilastirma_aracini_cagir` | Sabit parametreli SQL şablonu |
| `TOPLAM_MALIYET` | `toplam_maliyet_aracini_cagir` | Gerçek amortisman hesabı |
| `SOZLUK` | `sozluk_aracini_cagir` | 31 kavramlık terminoloji |
| `BILGI` | `rag_aracini_cagir` | Hibrit arama + kaynak |
| `KAPSAM_DISI` | *(araç yok)* | Kibarca kapsam dışı olduğunu söyler |

**10.3 Tool seçimini kim yapar:** LLM **değil** — `agent/intent.py` içindeki
deterministik anahtar kelime eşleştirmesi. `BILGI` niyeti anahtar kelimeyle
tespit **edilmez**: açık uçlu olduğu için kelime listesiyle yakalanamaz; hiçbir
araç eşleşmediğinde orkestratör RAG'e gider.

**10.4 Karar zinciri:**
```
Soru → Niyet tespiti (+güven) → Araç seçimi → Araç çalıştırma
     → Verifier → Terminoloji kontrolü → Yanıt (+kaynak +audit)
```

**10.5 Yanlış araç seçilirse — kademeli fallback:** Sistem vazgeçmez, soruyu
RAG'e sorar. **Gerekçe ölçüldü:** *"Ziraat Katılım kart kampanyalarında **taksit**
var mı?"* sorusu yalnızca "taksit" kelimesi yüzünden hesap makinesine gidiyor ve
kullanıcıya *"Hesaplama için şu bilgiler eksik: anapara…"* deniyordu — oysa bu
bir **bilgi sorusu** ve cevabı kaynaklarda var. Hangi aracın **neden** yetmediği
audit kaydında korunur.

**10.11 Paralel araç çağrısı:** Hayır — tek araç seçilir, yetersizse RAG'e
düşülür. Bu bilinçli: paralel çağrı denetlenebilirliği zorlaştırırdı.

**10.12 EVREN `router` modeli:** Kullanılmıyor. Niyet tespiti deterministik
yerel katmanla yapılır — çevrimdışı çalışabilirlik (Md. 5.9) için.

---

## 11. Terminoloji Sistemi

**11.1** Sözlükte **31 kavram** var (`terminology/sozluk.json`), her biri
**geleneksel karşılığı + tanım kaynağıyla**.

**11.6 Otuz bir kavramın tam listesi:**

| # | Kavram | # | Kavram | # | Kavram |
| --- | --- | --- | --- | --- | --- |
| 1 | `kar_payi_orani` *(≠ faiz)* | 12 | `nakit_iade` | 23 | `ozel_cari_hesap` |
| 2 | `finansman_maliyeti` | 13 | `murabaha` | 24 | `vade_farki` |
| 3 | `katilim_fonu` *(≠ mevduat)* | 14 | `icare` | 25 | `pesin_fiyat` |
| 4 | `masrafsiz_finansman` | 15 | `musaraka` | 26 | `tahsis_ucreti` |
| 5 | `avantajli_finansman` | 16 | `mudaraba` | 27 | `erken_odeme_indirimi` |
| 6 | `vade_suresi` | 17 | `selem` | 28 | `gecikme_bedeli` |
| 7 | `odul_miktari` | 18 | `istisna` | 29 | `danisma_kurulu` |
| 8 | `kesirli_kar_paylasimi` | 19 | `karz_i_hasen` | 30 | `finansman_tutari` |
| 9 | `sifir_oran_ifadesi` | 20 | `tekaful` | 31 | `hedef_kitle` |
| 10 | `odemesiz_donem` | 21 | `kira_sertifikasi` | | |
| 11 | `dar_makas` | 22 | `kar_zarar_katilma` | | |

**11.2 En kritik olanlar:** `kar_payi_orani` (geleneksel karşılığı: *faiz*),
`katilim_fonu` (*mevduat*), `vade_farki`, `kar_zarar_katilma` — bunlar
karıştırıldığında yanıt yalnızca yanlış değil, **fıkhî olarak da hatalı** olur.

**11.4 Geleneksel terminoloji nasıl engelleniyor:** Yanıt üretildikten sonra
**terminoloji kontrolü** çalışır; geleneksel bankacılık terimi tespit edilirse
katılım bankacılığı karşılığına yönlendirilir.

**11.7 Kullanıcı "faiz" derse:** Sistem soruyu reddetmez — kavramı **düzeltir**
ve katılım bankacılığındaki karşılığını (`kâr payı`) açıklar. Amaç engellemek
değil, doğru terminolojiyi öğretmektir.

**11.8** Sözlük **manuel** yönetilir (`terminology/sozluk.json`); sürümü
`rule_version` olarak `/sistem/tazelik` yanıtında döner
(ör. `sozluk-376da8806612`).

---

## 12. Kapsam Ölçümü (Scope Guard)

**12.5 Sonuç: hassasiyet 24/24 · özgüllük 10/10**

| Ölçüm | Ne test eder | Sonuç |
| --- | --- | --- |
| **Hassasiyet** | 24 geleneksel bankacılık ifadesi **yakalanmalı** | **24/24** |
| **Özgüllük** | 10 meşru katılım ifadesi **yakalanmamalı** | **10/10** |

> **Neden iki yön birden ölçülür:** Tek yön ölçülseydi *"her cümleyi işaretle"*
> diyen aptal bir kontrol de **tam not** alırdı. Özgüllük olmadan hassasiyet
> anlamsızdır.

**12.3–12.4 Karşı-örnek seti:** İfadeler **elle yazılmıştır** — hiçbiri gerçek
bir bankadan kopyalanmamış, hiçbiri gerçek bir bankaya atfedilmemiştir.

**Bu bir iddia olarak bırakılmaz.** Her push'ta çalışan bir test, karşı-örnek
ifadelerinin `scraper/raw_data` ve `gold_dataset` içinde geçmediğini tarar:

```
tests/test_karsi_ornekler.py::test_karsi_ornekler_veritabanina_girmemis
```

**12.7 Kapsam katmanları:** (1) Niyet katmanında `KAPSAM_DISI` tespiti,
(2) terminoloji sözlüğü eşleşmesi, (3) leksikal örtüşme (≥0,60).
*EVREN `router` modeli kullanılmıyor (§10.12).*

---

## 13. Hesap Makinesi

**13.3 Hesaplamayı LLM neden yapmıyor:** Aritmetik deterministik bir iştir;
olasılıklı bir modele bırakmak, doğru cevabı **şansa** bağlamaktır. Finansal
hesapta bu kabul edilemez.

**13.4 Fonksiyonlar** (`calculator/calculator.py`, saf Python):
`aylik_taksit_hesapla`, `odeme_plani_uret`, `maksimum_finansman_hesapla`,
`toplam_maliyet_karsilastir`

**13.8 Aylık taksit formülü:**
```
Aylık Taksit = Anapara × [ r × (1+r)^n ] / [ (1+r)^n − 1 ]
```
`r` = aylık kâr payı oranı (kampanya kaydındaki `kar_payi_orani_percent`,
`oran_periyodu` aylık/yıllık ayrımıyla normalize edilir),
`n` = vade (`vade_ay`). Girdiler `_girdileri_dogrula()` ile sınırlanır.

**13.9 KKDF / BSMV:** ⚠ **Uygulanmadı.** Bu depodaki hesap makinesi vergi
kalemlerini **hesaplamaz**; yalnızca anapara/oran/vade üzerinden taksit ve toplam
maliyet üretir. *Soru setindeki %15 KKDF / %5 BSMV oranları bu kodda yoktur —
uydurma sonuç göstermemek için burada açıkça belirtilir.*

**13.10 Toplam maliyet — neden oran tek başına yetmez:** *"Düşük oran = ucuz
demek değildir."* Uzun vadeli düşük oranlı bir kampanya, kısa vadeli yüksek
oranlıdan **toplamda daha pahalı** olabilir. `/chat`'e *"500.000 TL için X ile
Y'nin toplam maliyetini karşılaştır"* dendiğinde her bankanın kendi oran/vadesiyle
**gerçek amortisman hesabı** yapılır.

**13.11 PDF/Excel dışa aktarma:** Yok.

---

## 14. Müşteri Sesi (Complaint Insight) — **SENTETİK DEMO**

> ⚠️ **KVKK ŞEFFAFLIK BEYANI:** Bu modül **gerçek şikâyet verisi kullanmaz.**
> Veri seti tamamen sentetiktir; hiçbir gerçek şikâyetten kopyalanmamış ve
> hiçbir gerçek bankaya atfedilmemiştir. Her API yanıtı ve her ekran bunu
> açıkça belirtir.

| Soru | Cevap |
| --- | --- |
| **14.4** Sentetik örnek | **20** örnek + **2** alan dışı örnek |
| **14.5–14.6** Tema | **10** tema |
| **14.11** Üretim yöntemi | **Elle yazıldı** (LLM değil, şablon değil) |
| **14.8–14.9** Eğitimde kullanılıyor mu | **Hayır** — yalnızca demo/sınıflandırıcı testi |

**14.6 On tema:** `REWARD_NOT_CREDITED` (ödül yatmadı) ·
`ELIGIBILITY_MISMATCH` (koşul uyuşmazlığı) · `INSTALLMENT_MATURITY` (taksit/vade) ·
`MERCHANT_MCC_SCOPE` (işyeri kapsam dışı) · `ACTIVATION_REGISTRATION` (aktivasyon) ·
`DATE_EXPIRY` (tarih uyuşmazlığı) · `CARD_PRODUCT_MISMATCH` (kart/ürün) ·
`FEE_CHARGE` (beklenmeyen ücret) · `COMMUNICATION_AMBIGUITY` (iletişim belirsizliği) ·
`SERVICE_RESOLUTION` (çözüm süreci)

**14.7 Sınıflandırıcı:** Kural tabanlı ifade eşleştirme
(`complaint/tema_siniflandirici.py`). **Hiçbir ifade eşleşmezse tema
uydurulmaz — `None` döner.**

**14.10 Sızma koruması testle kilitli:**
```
tests/test_sentetik_musteri_sesi.py::test_sentetik_ornekler_urun_verisine_sizmamis
```

### Şikâyet hattı — dört kırmızı çizgi **koda gömülü**

| Kırmızı çizgi | Kodda karşılığı |
| --- | --- |
| Ham metin izin kapısı geçmeden diske yazılmaz | İzin kaydı yoksa `IzinYok` fırlar; `kaydet()` izni **ikinci kez** sorar |
| PII temizliği kayıttan **önce** | `hazirla()` ham metni ne döner ne loglar |
| Şikâyet verisi kampanya tablosuna karışmaz | Ayrı tablo, kampanyalara **foreign key yok** |
| **"Şikâyet oranı" denmez** | `yogunluk_ozeti()` yüzde üretmez; **adet** döner, alan adı `gozlenen_yogunluk` |

Varsayılan **her zaman izin yokluğudur**: dosya yoksa, bozuksa ya da alanları
eksikse "izin var" sayılmaz.

**Eşleşme bir hipotezdir.** Güven 0,50 eşiğinin altındaysa bağ kurulmaz ve
*neden* kurulmadığı yazılır. İki kampanya aynı güveni alırsa yine bağ kurulmaz:
rastgele birini seçmek **olmayan bir kesinlik üretmek** olurdu.

**14.13 Gerçek veri nasıl gelecek:** Kurumsal/hukuki (KVKK) onay sürecinden
sonra, Faz 2'de. Onay gelene kadar `sikayetler` tablosu **boş kalır**.

---

## 15. Kampanya Karşılaştırma

**15.7 Şartname Md. 5.7'nin 5 kriteri + 1 bonus** (`comparison/compare_engine.py`):

| Kriter | Alan |
| --- | --- |
| En Düşük Kâr Payı Oranı | `kar_payi_orani_percent` |
| En Yüksek Ödül Miktarı | `odul_miktari` |
| En Uzun Vade Seçeneği | `vade_ay` |
| En Düşük Masraf | `tahsis_ucreti` |
| **En Avantajlı Kampanya** | kompozit — aşağıya bakınız |
| *(bonus)* En Yüksek Tutar | `finansman_tutari` |

**15.8 "En avantajlı" nasıl hesaplanıyor — ağırlıklı formül YOK:**
Sistem tek bir ağırlıklı skor **uydurmaz**. Her alt kriterde hangi kampanyanın
öne çıktığı **ayrı ayrı** belirlenir (*"Kâr payı oranı açısından C Bankası daha
avantajlı…"*), **en çok eksende öne çıkan** genel kazanan sayılır. **Eşitlikte
tek bir kazanan uydurulmaz.** Yöntem, şartnamedeki Örnek Temsili Senaryo-2 ile
birebir aynıdır.

> Ağırlık atamak (*"kâr payı %40, ödül %30…"*) bilimsel görünen ama **temelsiz**
> bir seçim olurdu — hangi ağırlığın doğru olduğunu söyleyen bir kaynak yok.

**15.4–15.5 Eksik alan:** Gizlenmez. `NULLS LAST` ile en sona gider,
filtrelenip yok sayılmaz; arayüzde "Belirtilmemiş" görünür.

**15.9** Canlı DB sorgusu — önbellek yok.

---

## 16. Audit Sistemi (Jüri Audit Paneli)

**16.1 Amaç:** Jüri/geliştirici için, sistemin bir soruya **nasıl** cevap
verdiğini adım adım göstermek. Banka çalışanı iş odaklı dashboard'u görür;
denetim ayrı bir panelde.

**16.2–16.5 Kaydedilenler:**
🎯 Algılanan niyet + güven skoru · 🛠️ Çağrılan araç + parametreleri ·
🔍 Çalıştırılan SQL + sonuçları · 📊 Retriever benzerlik skorları + chunk'lar ·
🛡️ Güven skorları · ⏱️ Yanıt süresi + cache durumu · ✅ Kaynakta doğrulama

**16.10 Üç durumlu doğrulama — bilerek ayrı sayılır:**

| Durum | Anlamı |
| --- | --- |
| `dogrulandi` | Kullanılan tüm alanlar, tüm kayıtlarda kaynakta doğrulandı |
| `kismi` | Verifier çalıştı ama bir kısmını onaylayamadı — **değer silinmez** |
| `calistirilmamis` | Bu alanlar için Verifier hiç çalışmadı |

> **Bunları tek bir orana indirgemek en büyük hata olurdu:** "çalıştırılmamış"ı
> başarısızlık saymak sistemi haksız yere kötü, başarı saymak **yalancı**
> gösterirdi.

Yalnızca **sıralamayı belirleyen eksen(ler)** raporlanır — "en uzun vade"
sorusunda ödül miktarının doğrulanmış olması o cevap hakkında bilgi vermez.

**RAG yolunda özet bilerek üretilmez (`None`)** ve bu doğrudur: RAG hiçbir cümle
üretmez, kaynağı birebir döndürür. Orada "bu sayı kaynakta geçiyor mu?" kontrolü
tanım gereği **her zaman evet** derdi — hiçbir şey elemeyen, yalnızca doğrulama
yapılmış **izlenimi** veren bir kontrol olurdu.

**16.15 `ExtractionAudit` vs `DecisionTrace`:**
- `DecisionTrace` → **bir sorunun** karar zinciri (çalışma zamanı)
- `ExtractionAudit` → **bir kampanyanın** çıkarım izi (veri kalitesi)

---

## 17. Çıkarım Denetimi (Extraction Audit)

**17.1–17.8** Bir kampanya seçilir; her alan için gösterilir:
**Alan · Mevcut değer · Çıkarım katmanı (regex/GLiNER/LLM) · Güven · Gold
referansı · Doğrulama durumu · Kanıt (evidence span)**

**17.9 Üç model farklı değer üretirse:** Resolver'ın seçtiği gösterilir; diğer
katmanların adayları **"diğer adaylar"** olarak ayrıca listelenir — çatışma
gizlenmez.

**17.10** Gold değer ile model çıktısı uyuşmadığında satır işaretlenir.

> **Ekranda açıkça yazan dürüstlük notu:** *"Bu ölçümde NER (GLiNER) devre
> dışıydı — raporlanan hibrit gerçekte regex + LLM'dir. NER'in katkısı
> ölçülmemiştir."* (§25)

---

## 18. Arayüz

**18.1–18.2** 8 ana sayfa:

| Sayfa | Amaç | Veri kaynağı |
| --- | --- | --- |
| Genel Bakış | Hacim, kapsam, dağılım, tazelik | `/sistem/tazelik`, `/kampanyalar` |
| AI Asistan | Doğal dil soru-cevap | `/chat`, `/chat/stream` |
| Kampanyalar | Liste + detay + tarihçe | `/kampanyalar*` |
| Karşılaştırma | 5+1 kriter matrisi | `/karsilastir`, `/rakip-analizi` |
| Hesap Makinesi | Taksit/maliyet | `/hesapla` |
| Metin Analizi | Serbest metinden çıkarım (Md. 6 demo) | `/cikar` |
| Jüri Audit Paneli | Karar zinciri + Model Metrikleri + Veri Kaynakları | Çalışma zamanı |
| Çıkarım Denetimi | Kampanya bazlı çıkarım izi | `/audit/extraction/{id}` |

**18.4–18.5 Mock vs gerçek:** `GERCEK_VERI_AKTIF` ortam değişkeni belirler.
`false` = 4 kayıtlık mock (A/B/C/D Bankası — sözleşme testi verisi),
`true` = canlı PostgreSQL (536 kayıt). Arayüzde üst barda **"🟢 CANLI VERİ"**
rozeti bu durumu her sayfada gösterir.

**18.6 Offline:** API'ye ulaşılamıyorsa arayüz **uydurma veri göstermez** —
dürüstçe "Veri alınamadı" der ve statik ölçüm değerlerine düşer (tarihi belirtilerek).

**18.8** Responsive — 640/900/1000/1200/1400 px kırılım noktaları tanımlı.

---

## 19. API

**19.1–19.2 Uç noktalar** (tümü `Authorization: Bearer <token>` ister; `/` ve
`/saglik` hariç):

| Metot | Yol | Açıklama |
| --- | --- | --- |
| GET | `/` · `/saglik` | Servis bilgisi / health check |
| GET | `/sistem/tazelik` | Veri/RAG indeksi güncelliği |
| POST | `/token` | JWT (yalnızca `JWT_AKTIF=true`) |
| POST | `/kayit` | Self-servis kayıt — rol **her zaman** `musteri` |
| POST | `/kullanici/sifre-degistir` | Şifre değiştirme |
| GET | `/kampanyalar` | Liste (`?banka=` `?kampanya_turu=`) |
| GET | `/kampanyalar/{id}` | Detay |
| GET | `/kampanyalar/{id}/etki` | Etki skoru |
| GET | `/kampanyalar/{id}/tarihce` | Değişim tarihçesi |
| GET | `/rakip-analizi` | Rakip matrisi |
| GET | `/terminoloji` | 31 kavram (Md. 5.5) |
| POST | `/cikar` | Serbest metinden çıkarım (Md. 6 demo) |
| POST | `/karsilastir` | Karşılaştırma |
| POST | `/hesapla` | Taksit/kâr payı (saf Python) |
| POST | `/chat` | Soru-cevap (kaynak + audit) |
| POST | `/chat/stream` | Aynı yanıt, SSE |
| GET | `/audit/extraction/{id}` | Çıkarım izi |
| POST | `/musteri-sesi/siniflandir` | Tema sınıflandırma (sentetik) |
| GET | `/musteri-sesi/ornekler` | Sentetik demo seti |
| GET | `/musteri-sesi/yogunluk-ozeti` | Tema bazında **adet** (oran değil) |

**19.6 Kimlik doğrulama:** `Authorization: Bearer <token>` **her iki modda da
aynı formatta** — bu yüzden arayüz kodu mock↔gerçek geçişinde değişmez.
`JWT_AKTIF=true` ile HS256 doğrulama açılır.

**19.9 Swagger:** Aktif — <http://localhost:8000/docs>

```bash
curl -H "Authorization: Bearer test-token" \
     "http://localhost:8000/kampanyalar?banka=Kuveyt%20T%C3%BCrk"
```

---

## 20. Güvenlik

| Soru | Cevap |
| --- | --- |
| **20.4** Şifre saklama | **bcrypt** (`bcrypt.hashpw` + `gensalt`) — düz metin **asla** saklanmaz |
| **20.5–20.6** API anahtarı | `.env` (git'e **girmez**, `.gitignore`'da); `.env.ornek` şablon |
| **20.8** SQL injection | SQLAlchemy parametreli sorgular; **serbest metinden SQL üretilmez** |

**20.1–20.3 Rol bazlı erişim:** Roller `musteri`, `banka_calisani`,
`denetleyici`, `yonetici`. `/kayit` ile açılan hesabın rolü **her zaman**
`musteri`'dir — rol **istemciden kabul edilmez**.

> **Jüri erişimi:** Metin Analizi ve Çıkarım Denetimi ekranları **tüm giriş
> yapmış kullanıcılara açıktır**, böylece jüri kendi hesabıyla denetim
> yapabilir. `/cikar` uç noktasındaki rol kısıtı yalnızca `JWT_AKTIF=true`
> modunda devreye girer.

**20.9 EVREN API anahtarı:** `.env` dosyasında, git geçmişinde **yoktur**.
CI'da her push'ta **sızmış sır taraması** çalışır.

**20.10–20.11 KVKK:** Sistem kişisel veri toplamaz. Şikâyet hattında PII
temizliği **kayıttan önce** zorunludur ve izin kapısı olmadan ham metin diske
yazılmaz (§14).

---

## 21. Çevrimdışı / Demo Modu

**21.1–21.5** PostgreSQL ✅ yerel · Qdrant ✅ yerel · Ollama + Qwen2.5 ✅ yerel ·
Embedding ✅ yerel

**21.6 İnternet kesilirse chatbot çalışır mı: EVET.** Tüm yığın yereldir.
EVREN kapalıyken sistem **tam işlevle** devam eder — LLM katmanı yerel Qwen2.5'e
düşer.

**21.10 EVREN yoksa:** Yerel Qwen2.5 (Ollama) devreye girer. Ollama da yoksa
LLM katmanı **sessizce atlanır** ve deterministik katmanların (regex + NER)
sonucu döner — sistem durmaz, yalnızca hibrit katkı kaybolur
(makro F1 %82,50 → %80,66).

**21.11–21.12 Demo kurulumu:**

```bash
git clone https://github.com/Sara-Toptamur36/katilim-ai.git
cd katilim-ai
docker compose up -d                    # PostgreSQL + Qdrant + Ollama
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python demo_baslat.py                   # Docker + alembic + API tek komutta
cd dashboard && npm install && npm run dev
```

> **Demo öncesi zorunlu adım — ölçülmüş tuzak:** Gömme modelini açılışta
> yükleyin. Isıtma olmadan sürecin ilk `/chat` sorusu modeli beklemek zorunda
> kalır (**ölçüldü: 81 sn**) ve arayüz zaman aşımına uğrar.
> `demo_baslat.py` bunu zaten açar; elle: `KATILIMAI_MODEL_ISIT=true uvicorn api.main:app`

**Çevrimdışı hazırlık kontrolü** (internet varken bir kez çalıştırın):
```bash
python cevrimdisi_hazirlik_kontrolu.py
```

---

## 22. Testler

| Soru | Cevap |
| --- | --- |
| **22.1** Geçen test | **1278** (CI, `-m "not slow"`) · 0 hata · 90 atlandı |
| Test dosyası | **81** |
| Yavaş test — grup 1 | **34** (`SLOW_test_sprint_is_listesi.py`, `PYTEST_SLOW_TESTS=1`) |
| Yavaş test — grup 2 | **46** (`@pytest.mark.slow`, `pytest -m "slow"`) |

> **İki yavaş test grubu karıştırılmamalı:** Grup 1 modül seviyesinde **ortam
> değişkeniyle** atlanır (sprint iş listesi üretimi 3+ dakika sürüyor). Grup 2
> **marker ile deselect** edilir (Ollama/GLiNER/Qdrant gerektirir). İkisi
> birbirinden bağımsız mekanizmalardır.

**22.10 Komutlar:**
```bash
pytest tests/ -v                  # tümü
pytest tests/ -m "not slow"       # CI'nin çalıştırdığı
```

**22.8 Dairesellik yasağı testleri:** `tests/test_olcum_kapsami.py` (çelişkili
etiket kombinasyonunu imkânsız kılar), `tests/test_karsi_ornekler.py`
(karşı-örneklerin üretim verisine sızmadığını tarar),
`tests/test_sentetik_musteri_sesi.py` (sentetik verinin sızmadığını tarar),
`tests/test_iddia_durustlugu.py` (belgelere eğitim iddiası yazılmasını engeller).

**Dış servis gerektiren testler — servis yoksa hata vermez, atlanır:**

| Grup | Gereksinim |
| --- | --- |
| Veritabanı | PostgreSQL |
| LLM / hibrit | Ollama + Qwen2.5 |
| Vektör arama | Qdrant + embedding modeli |

Bu yüzden CI'da test sayısı yerelden düşük görünür — **regresyon değil, beklenen
durumdur.**

**22.11 Coverage oranı:** ⚠ EKİP DOLDURACAK — *bu depoda coverage raporu
üretilmiyor.*

---

## 23. MLOps / CI-CD

| Soru | Cevap |
| --- | --- |
| **23.1–23.3** GitHub Actions | ✅ Her push'ta test + sızmış sır taraması |
| **23.4** Security scan | ✅ Sır taraması |
| **23.5–23.6** Docker Compose | `postgres` · `qdrant` · `ollama` (+ `pgdata`, `qdrantdata`, `ollamadata` volume'leri) |
| **23.7** Deployment | GitHub Pages (statik arayüz) — `deploy-pages.yml` |
| **23.8** Versiyonlama | `dataset_version`, `rag_index_version`, `model_version`, `rule_version` → `/sistem/tazelik` |
| **23.9–23.10** MLflow / DVC | Kullanılmıyor |

**Sürüm sabitleme:** Tüm Python bağımlılıkları `requirements.txt`'te tam sürümle
(`==`), Docker imajları sabit etiketle. **Aynı commit her makinede aynı
sürümlerle kurulur.**

> **GitHub Pages'te backend çalışmaz.** Pages yalnız statik dosya sunar.
> `VITE_API_BASE_URL` tanımlı değilse yayınlanan site `localhost:8000`'e istek
> atar ve dış ziyaretçilerde dürüstçe **"Veri alınamadı"** gösterir — bu bir hata
> değil, **uydurma veri göstermemenin sonucudur**.

---

## 24. Veri Tazeliği

**24.8 `/sistem/tazelik` tam yanıtı** (canlı örnek, 26 Ağustos):

```json
{
  "son_tarama": "2026-08-26T01:42:23", "tarama_gun_once": 0,
  "rag_indeks_kuruldu": "2026-08-26T07:37:13", "rag_indeks_gun_once": 0,
  "rag_parca_sayisi": 2127, "rag_belge_sayisi": 623,
  "indeks_ham_veriden_eski_mi": false,
  "tekil_kampanya": 525, "anlik_goruntu": 623,
  "dataset_version": "298imzali-2026-08-24",
  "rag_index_version": "2127parca-2026-08-26",
  "model_version": "qwen2.5:7b-instruct-q4_K_M",
  "rule_version": "sozluk-376da8806612",
  "demo_mode": false
}
```

**24.6 İndeks bayatsa:** `indeks_ham_veriden_eski_mi` alanı **üç değerli**:
`true` / `false` / `null`. **`null` = "bilinmiyor"** — ve bu `false` ile
karıştırılmaz. *"İndeks eski"* ile *"indeks durumu bilinmiyor"* farklı şeylerdir;
bilinmeyen için tahmin üretilmez.

**24.7 Bilinen tazelik problemi (açıkça):** Canlı RAG indeksi **2127 parça /
623 belge**, ama Recall **1875 parça / 513 belge** üzerinde ölçüldü.
Arayüzde ikisi **ayrı ayrı** gösterilir:
- Hero kartı → *"ÖLÇÜM İNDEKSİ (Recall): 1875 parça · canlı indeks 2127 parça"*
- Sistem Sağlığı kartı → *"CANLI RAG İNDEKSİ: 2127 parça / 623 belgeden"*

---

## 25. Sınırlılıklar (dürüstlük notu)

> Bu bölüm eksiksizdir. Aşağıdakiler hedef mimaride yer alır ancak bu depoda
> **henüz tamamlanmamıştır**.

### 25.1 En büyük beş sınırlılık

1. **Ablation (katman katkısı ayrıştırması) yapılmadı.** 26 Ağustos'ta hibrit
   pipeline uçtan uca koşturuldu, ama `ablation.py`'nin ürettiği **üçlü
   karşılaştırma** (regex / +NER / +NER+LLM) yapılmadı.
2. **O koşuda NER katmanı devre dışıydı.** GLiNER bu makinede yüklenirken
   çöküyor (torch/Windows yerel hatası) → raporlanan "hibrit" gerçekte
   **regex + LLM**'dir. **NER'in katkısı "yok" değil, "ölçülmedi"dir.**
3. **RAG Recall güncel indekste yeniden ölçülmedi.** İndeks 1875 → 2127 parçaya
   büyüdü; ölçüm 1875'te kaldı.
4. **LLM katmanı deterministik değil.** `temperature=0` ile bile koşular arası
   oynuyor (**ölçüldü: %89,06 ↔ %87,5**). Hibrit sayı "kesin" değil, **ölçülmüş
   bir aralığın temsilcisidir**; regex-only sayı tekrar üretilebilirdir.
5. **Müşteri Sesi yalnızca sentetik veriyle çalışıyor.** Hat kurulu, veri yok —
   eksik olan tek şey kurumsal/hukuki (KVKK) onaydır.

### Diğer eksikler

- **LLM ile yanıt özetleme yok.** RAG kaynağı birebir döndürür. Bu bilinçli:
  özetleme ancak Verifier ile **birlikte** güvenli olur.
- **OCR kurulu değil.** Taranmış/görüntü PDF'ler işlenemez (Tesseract ayrı yerel
  kurulum ister). Metin tabanlı PDF'ler pypdf ile işlenir; taranmış bir PDF'te
  metin boş dönerse kayıt **düşük güvenle işaretlenir**, sessizce doğru
  varsayılmaz.
- **Müşteri geri bildirim bileşeni yok.** Etki skorunun ikinci yarısı;
  gösterge `veri_yok` döner — **sıfır yazılmaz**, çünkü geri bildirim yokluğu
  "müşteriler memnun değil" anlamına gelmez.
- **KKDF/BSMV vergi hesabı yok** (§13.9).
- **Test coverage ölçülmüyor** (§22.11).

### 25.3 Çıkarımın zayıf olduğu alanlar
`vade_ay` (%57,14) · `hedef_kitle` (%56,95) · `finansman_tutari` (%72,73)

### 25.4 RAG'in başarısız olduğu sorular
`banka_ve_konu` kategorisi (%52,17) — kampanya adı verilmeden sorulan sorular.

### 25.6 Canlı olmayan metrikler
Çıkarım metrikleri (26 Ağustos ölçümü), RAG metrikleri (25 Ağustos ölçümü),
Scope Guard (24/24, 10/10). Hacim/dağılım metrikleri **canlıdır**.

---

## 26. Gelecek Geliştirmeler

| # | Plan |
| --- | --- |
| 26.1–26.2 | Banka kotası ve korpus büyütme — 9 banka kapsandı, kampanya sayısı taramayla artıyor |
| 26.3 | Altın veri seti 302'den büyütülecek |
| **26.4** | **Fine-tuning yapılmayacak** — mimari tercih, iddia edilmiyor |
| 26.5 | Complaint Insight gerçek anonimleştirilmiş veriyle (KVKK onayı sonrası, Faz 2) |
| 26.6 | RAG otomatik yeniden indeksleme + **güncel indekste Recall yeniden ölçümü** |
| 26.10 | Reranker eklenmesi — `banka_ve_konu` kategorisindeki %52,17 için ölçülmüş ihtiyaç |
| — | **Ablation'ın GPU'lu makinede tamamlanması** (§25) |

---

## 27. Demo Senaryosu

**27.1 İlk ekran:** Genel Bakış — canlı veri rozeti, kapsam, dağılım.

**27.2–27.3 İlk chatbot sorusu:**
> *"Kuveyt Türk'ün konut finansmanı kampanyalarında kâr payı oranı nedir?"*
→ `BILGI` niyeti → RAG aracı → kaynak parçası **birebir** + chunk ID + skor.

**Karşılaştırma sorusu:**
> *"En düşük kâr payı oranlı kart kampanyası hangisi?"*
→ `KARSILASTIRMA` niyeti → SQL şablonu → `NULLS LAST` ile eksikler sonda.

**Toplam maliyet sorusu (bonus):**
> *"500.000 TL için Kuveyt Türk ile Ziraat Katılım'ın toplam maliyetini karşılaştır"*
→ `TOPLAM_MALIYET` → saf Python amortisman.

**27.6–27.8 Audit'e geçiş:** Sol menü → **Jüri Audit Paneli** → karar zinciri
(niyet → araç → SQL/retriever → doğrulama → süre).

**27.9–27.10 Çıkarım Denetimi:** Sol menü → **Çıkarım Denetimi** → veri
zenginliğine göre sıralı kampanya seç → alan alan katman/güven/gold/kanıt.

**27.12 Müşteri Sesi:** Sentetik örnek → tema sınıflandırma → ekranda
**"sentetik demo"** uyarısı gösterilir.

**27.13 Süre:** ⚠ EKİP DOLDURACAK — *prova ile ölçülmeli, hedef ≤ 5 dk.*

### 27.14 Kurtarma planları

| Sorun | Kurtarma |
| --- | --- |
| EVREN yanıt vermiyor | **Otomatik** — yerel Qwen2.5'e düşer, sistem durmaz |
| Ollama kapalı | **Otomatik** — LLM katmanı atlanır, regex+NER sonucu döner |
| Qdrant kopuk | RAG çekimser kalır; SQL/hesap/sözlük araçları çalışmaya devam eder |
| PostgreSQL erişilemiyor | `python demo_baslat.py --mock` — Docker/DB **gerekmez** |
| Frontend yüklenmiyor | Swagger `/docs` üzerinden uç noktalar canlı gösterilebilir |
| İlk soru çok yavaş | Model ısıtması yapılmamış → `KATILIMAI_MODEL_ISIT=true` |

---

## 28. EVREN Entegrasyonu

**28.1 Kullanılan modeller — yalnızca ikisi:**

| Model | KatılımAI'daki kullanım |
| --- | --- |
| `llm-fast` | ✅ **Hibrit çıkarımın LLM katmanı** (opsiyonel sağlayıcı) |
| `bge-m3-embed` | ⚠ İstemcide tanımlı, üretim yolunda **kullanılmıyor** |
| `llm-large` | ❌ Kullanılmıyor — ölçümde `llm-fast` ile **fark bulunamadı** (5/5 görev) |
| `router`, `vlm`, `guard`, `rerank`, `bge-m3-sparse`, `bge-m3-colbert` | ❌ Kullanılmıyor |

**Neden `llm-fast`:** JSON üretimi/sınıflandırma gibi **biçim ağırlıklı**
görevlerde `llm-large` ile ölçülmüş fark **yok** (5/5 görev). `llm-large`'ın öne
çıktığı alanlar (kültürel/tarihî bilgi, video) bu projenin görev profiline
girmiyor.

**Neden hibrit getirme ve rerank çağrılmıyor:** EVREN dokümantasyonunun **kendi
ölçümünde** hibrit+rerank saf yoğun aramadan **düşük** çıkıyordu (0,55 vs 0,95).

**28.4 Fallback:** `EVREN_API_KEY` yoksa `evren_istemci.py`'nin tüm fonksiyonları
**pasif döner** ve sistem yerel Qwen2.5 ile çalışır.

**28.5 EVREN'in ölçülmüş etkisi — ve bulunan hata:**
EVREN entegrasyonunda **sessiz bir hata** bulundu ve düzeltildi: `llm-fast`
varsayılan olarak bir *"düşünme zinciri"* üretiyordu, bu da `max_tokens`
sınırını tüketip çağrıyı **sessizce boş döndürüyordu**
(`finish_reason=length`, `content=null`). Çözüm:
`chat_template_kwargs.enable_thinking=false`.

Düzeltme sonrası hibrit ölçüm mümkün oldu: makro F1 **%80,66 → %82,50**.

**28.3 Kimlik doğrulama:** OpenAI-uyumlu, `EVREN_API_KEY` ile Bearer token.
Anahtar `.env`'de, **git geçmişinde yok**.

**28.2 Takım Qdrant URL'si:** Kullanılmıyor — yerel Qdrant tercih edildi
(çevrimdışı çalışabilirlik, Md. 5.9).

---

## 29. Tüm ölçümlerin üretim komutları

> Yukarıdaki **her sayı** aşağıdaki komutlarla yeniden üretilebilir.

```bash
python -m scraper.scripts.extraction_accuracy         # dolu/boş alan doğruluğu + alan bazlı F1
python -m scraper.scripts.hibrit_extraction_accuracy  # regex + NER + LLM
python -m scraper.scripts.ablation                    # katman katkısı (⚠ henüz koşulmadı)
python -m scraper.scripts.rag_degerlendirme           # RAG Recall@k + çekimserlik
pytest tests/test_karsi_ornekler.py -s                # kapsam ölçümü (hassasiyet/özgüllük)
pytest tests/ -m "not slow"                           # CI'nin çalıştırdığı test takımı
```

**Sağlayıcı seçimi ölçümde de geçerlidir:** `.env`'de `EVREN_API_KEY` tanımlıysa
hibrit ölçüm EVREN `llm-fast`'i, tanımlı değilse yerel Ollama'yı kullanır.
Aynı komut, **hangi sağlayıcının kullanıldığını çıktının başında yazar** — iki
koşunun sayıları karıştırılmasın diye.

### Ölçüm raporları

| Rapor | İçerik |
| --- | --- |
| [`cikarim_dogruluk_raporu.json`](../cikarim_dogruluk_raporu.json) | Alan bazlı F1, regex vs hibrit, NER durumu |
| [`docs/extraction_accuracy_raporu.md`](extraction_accuracy_raporu.md) | Çıkarım yöntemi + yanlış pozitif analizi |
| [`docs/rag_tasarim_ve_olcum.md`](rag_tasarim_ve_olcum.md) | RAG tasarımı, eşik kalibrasyonu, bulgular |
| [`docs/kapsam_ve_veri_ayrimi.md`](kapsam_ve_veri_ayrimi.md) | Scope Guard ölçümü |
| [`docs/md6_dokumantasyon.md`](md6_dokumantasyon.md) | Md. 6'nın 10 kalemi tek belgede |
| [`docs/adr/0002-evren-cikarim-entegrasyonu.md`](adr/0002-evren-cikarim-entegrasyonu.md) | EVREN model seçim gerekçesi |

---

## 30. Şartname maddesi → karşılık

| Madde | Konu | Karşılığı |
| --- | --- | --- |
| **Md. 5.3** | Hedef kitle, kampanya süresi | Ölçüme dahil (`hedef_kitle` %56,95, `kampanya_bitis` %95,69) |
| **Md. 5.4** | Kampanya türü sınıflandırması | `kampanya_turu` F1 **%81,88**, 11 tür |
| **Md. 5.5** | Terminoloji | **31 kavram**, `/terminoloji` |
| **Md. 5.6** | Normalizasyon | Oran/vade/tutar/tarih normalizasyonu (`preprocessing/`) |
| **Md. 5.7** | Karşılaştırma kriterleri | **5 kriter + 1 bonus** (`comparison/compare_engine.py`) |
| **Md. 5.9** | On-premise / çevrimdışı | Tüm yığın yerel; `cevrimdisi_hazirlik_kontrolu.py` |
| **Md. 5.10 / 8** | Açık kaynak | Tümü açık kaynak, Apache-2.0 (§2.1) |
| **Md. 6** | Dokümantasyon (10 kalem) | [`docs/md6_dokumantasyon.md`](md6_dokumantasyon.md) + `/cikar` demo ekranı |
| **Md. 9** | Veri erişimi | `requirements.txt` · kurulum adımları · `gold_dataset/` + `scraper/raw_data/` |

---

*Bu belge 26 Ağustos 2026'da, depodaki koda ve canlı ölçümlere karşı
doğrulanarak hazırlandı. `⚠ EKİP DOLDURACAK` etiketli satırlar, doğrulanamadığı
için bilerek boş bırakılmıştır.*

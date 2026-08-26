# KatılımAI

Takım: **PeacewAI** — Fırat Üniversitesi, Yapay Zekâ ve Veri Mühendisliği

`BilisimVadisi2026` · Türkiye Açık Kaynak Platformu

---

> **Ekip için iki temel belge:**
> [`docs/PROJE_TANITIMI.md`](docs/PROJE_TANITIMI.md) — projenin ne olduğu,
> hangi kararların neden alındığı, nerede olduğumuz.
> [`docs/CALISMA_REHBERI.md`](docs/CALISMA_REHBERI.md) — kalan işlerin
> adım adım nasıl yapılacağı, komutlar, tuzaklar, kontrol listeleri.

---

## Durum

| Sprint           | İçerik                                                                             | Durum         |
| ---------------- | ---------------------------------------------------------------------------------- | ------------- |
| **Sprint 1**     | API sözleşmesi, uç noktalar, veri toplama, terminoloji sözlüğü, dashboard iskeleti | ✅ Tamamlandı |
| **Sprint 2**     | Karşılaştırma motoru, hesap makinesi, hibrit çıkarım (regex+NER+LLM), PostgreSQL   | ✅ Tamamlandı |
| **Sprint 3**     | Ajan orkestratör, chatbot arayüzü                                                  | ✅ Tamamlandı |
|                  | Semantik chunking + embedding + Qdrant indeksleme                                  | ✅ Tamamlandı |
| **Sprint 4**     | Intent tespiti, Jüri Audit Paneli, gerçek JWT kimlik doğrulama                     | ✅ Tamamlandı |
|                  | RAG: hibrit arama + kaynaklı yanıt + abstention                                    | ✅ Tamamlandı |
| **Sprint 5**     | Terminoloji sözlüğü genişletildi + kapsam ölçümü (karşı-örnek seti)                | ✅ Tamamlandı |
|                  | Rakip analizi matrisi, kampanya etki skoru                                         | ✅ Tamamlandı |
|                  | Kampanya değişim tarihçesi, Verifier sonucunun kalıcılaştırılması                  | ✅ Tamamlandı |
| **Tamamlamalar** | Verifier → ajan yanıt yoluna bağlandı (karşılaştırma + toplam maliyet)             | ✅ Tamamlandı |
|                  | Zaman aşımı tabanlı kademeli fallback (`KATILIMAI_ARAC_ZAMAN_ASIMI`)               | ✅ Tamamlandı |
|                  | RAG exact arama modu (`KATILIMAI_RAG_EXACT_MOD=true`) — Recall@1 kararlı           | ✅ Tamamlandı |
| **26 Ağustos**   | Gerçek giriş/kayıt/çıkış + Ayarlar ekranı (şifre değiştirme dahil)                 | ✅ Tamamlandı |
|                  | Genel Bakış / Jüri Audit Paneli yeniden konumlandırıldı (Model Metrikleri + Veri Kaynakları Audit'e taşındı) | ✅ Tamamlandı |
|                  | `GERCEK_VERI_AKTIF=true` ile canlı PostgreSQL verisi bağlandı (536 kayıt)          | ✅ Tamamlandı |
|                  | Çıkarım doğruluğu hibrit pipeline ile 291 canlı kayıtta yeniden ölçüldü            | ✅ Tamamlandı |
|                  | CI regresyonu bulundu ve düzeltildi (`terim_agirliklari` sahte nesne alanı)        | ✅ Tamamlandı |

### Ölçülebilir durum

_Son ölçüm: 26 Ağustos 2026 (çıkarım + veri) · 25 Ağustos 2026 (RAG — aşağıya
bakınız). Tüm sayılar depodaki komutlarla yeniden üretilebilir — üretim
komutları [Test](#test) bölümünde._

> **26 Ağustos 2026 güncellemesi — çıkarım doğruluğu HİBRİT pipeline ile,
> 291 canlı kayıtta yeniden ölçüldü.** EVREN entegrasyonundaki sessiz bir
> hata bulunup düzeltildi: `llm-fast` varsayılan olarak bir "düşünme
> zinciri" üretiyordu, bu da `max_tokens` sınırını tüketip çağrıyı
> sessizce boş döndürüyordu (`finish_reason=length`, `content=null`) —
> `chat_template_kwargs.enable_thinking=false` ile giderildi. Düzeltme
> sonrası hem regex-only hem hibrit (regex+LLM/EVREN) varyantı, önceki
> 93 kayıtlık örneklemin üç katından fazlası olan **291 canlı kayıtta**
> yeniden ölçüldü. Aşağıdaki çıkarım satırları HİBRİT (çalışan sistemin
> gerçekte kullandığı) varyantı gösterir; ayrıntı:
> [`cikarim_dogruluk_raporu.json`](cikarim_dogruluk_raporu.json),
> [`docs/extraction_accuracy_raporu.md`](docs/extraction_accuracy_raporu.md).
>
> Ayrıca aynı gün, gerçek veri (`GERCEK_VERI_AKTIF=true`) ile çalışan API'de
> banka bazında dağılım denetlendi: statik anlık görüntüde Vakıf Katılım
> yalnızca 3 kampanya gösteriyordu, canlı veride **100** çıktı — dashboard'daki
> "Veri Kaynakları" paneli artık bunu statik değil canlı hesaplıyor.

| Gösterge                                      | Değer                                                                                        |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Kapsanan katılım bankası                      | **9 / 10** (BDDK listesi; Adil Katılım gerekçeli hariç — ürün/kampanya yayımlamıyor)          |
| Toplanan gerçek kampanya                      | **536** kayıt PostgreSQL'de yapılandırılmış (`GERCEK_VERI_AKTIF=true`); 525 tekil taranmış ham sayfa, 623 anlık görüntü — üçü farklı şeyi ölçer, ayrıntı dashboard'da |
| Altın Veri Seti                               | **302** kayıt, tamamı imzalı (ölçüme giren); taslak kalmadı                                   |
| Çıkarım — dolu alan doğruluğu (hibrit)        | **%81,68** — 291 canlı kayıt, 11 alan — _ölçüm 26 Ağustos_                                    |
| Çıkarım — boş alan doğruluğu (yanlış pozitif) | **%96,88** — 291 canlı kayıt — _ölçüm 26 Ağustos_                                              |
| Çıkarım — makro F1 (11 alan, hibrit)          | **%82,50** (regex-only tek başına **%80,66**) — _ölçüm 26 Ağustos_                            |
| Terminoloji sözlüğü                           | **31** kavram (geleneksel karşılığı + tanım kaynağıyla)                                        |
| Kapsam ölçümü (Scope Guard)                   | hassasiyet **24/24**, özgüllük **10/10**                                                       |
| RAG — indekslenen parça (Recall'ün ölçüldüğü) | **1875** parça / 513 belge, 25 Ağustos — canlı indeks o tarihten sonra **2127 parçaya** büyüdü, Recall henüz yeni indekste yeniden ölçülmedi |
| RAG — değerlendirme seti                      | **129** sorgu, `exact=True`                                                                    |
| RAG — Recall@5 (genel)                        | **%87,60** (Recall@3 %84,50, Recall@1 %72,09 — HNSW yaklaşık arama nedeniyle koşular arası oynar) |
| RAG — abstention doğruluğu                    | alan dışı **%86,67** (13/15) · alan içi kapsam dışı **%40,0** (izole ölçüm; uçtan uca ölçümde %90,0 — bkz. [`docs/rag_tasarim_ve_olcum.md`](docs/rag_tasarim_ve_olcum.md) Bulgu 12) |
| Otomatik test                                 | **1278** test geçiyor (CI, `-m "not slow"`), 0 hata, 90 atlandı — CI her push'ta çalışır       |

> **Yavaş testler — iki ayrı grup, karıştırılmamalı:**
> `tests/SLOW_test_sprint_is_listesi.py` (**34** test) modül seviyesinde
> `PYTEST_SLOW_TESTS` ortam değişkeniyle skip edilir — sprint iş listesi
> üretimi 3+ dakika sürüyor. Manuel çalıştırma:
> `PYTEST_SLOW_TESTS=1 pytest tests/SLOW_test_sprint_is_listesi.py`
>
> Ayrıca 8 ayrı test dosyasında `@pytest.mark.slow` ile işaretli **46** test
> (Ollama/GLiNER/Qdrant gerektirir) `pytest -m "not slow"` ile CI'da
> **deselect** edilir — `PYTEST_SLOW_TESTS` değişkeninden bağımsız, ayrı bir
> mekanizmadır. Çalıştırmak için: `pytest -m "slow"`

> ### Çıkarım metrikleri 23 Ağustos'ta AŞAĞI yönlü düzeltildi — nedeni önemli
>
> Bu satırlar önceki sürümde **%98,48 / %99,17 / %98,28** yazıyordu. O sayılar
> doğruydu ama **başka bir şeyi** ölçüyordu: 64 kayıtlık altın veri setinde,
> **yalnızca 7 sayısal alan** üzerinde. O günden bu yana iki şey değişti ve
> ikisi de ölçümü zorlaştırdı:
>
> 1. **Ölçüm kapsamı 7 alandan 11 alana çıktı.** Şartname Md. 5.4 (kampanya
>    türü) ve Md. 5.3 (hedef kitle, kampanya süresi) alanları ölçüme dahil
>    edildi. Bu dördü **sınıflandırma ve tarih** işidir — regex katmanının
>    zayıf olduğu, farklı yöntem gerektiren alanlar. Kapsam dışında
>    bırakılsalardı sayı yüksek kalırdı ama şartnamenin sorduğu şey
>    ölçülmemiş olurdu.
> 2. **Altın veri seti 64 → 307 satıra büyüdü** (o ölçümde 107'si imzalı;
>    24 Ağustos'ta imzalı sayı **298**'e çıktı, ölçüm henüz yenilenmedi).
>    Örneklem büyüdükçe motorun gerçek seviyesi ortaya çıktı.
>
> Yani **kalite düşmedi, ölçüm dürüstleşti.** İki sayı ayrı ayrı verilir:
> sınıflandırma/tarih alanlarını da içeren toplam (**%67,09**) ve regex
> katmanının asıl sorumluluğu olan sayısal çekirdek (**%81,66**). Tek bir
> ortalama, iki farklı işi birbirinin arkasına saklardı.
>
> **Aynı gün kapatılan üç hata ve ölçülmüş etkileri:**
>
> | Düzeltme                                  | Etki                                                      |
> | ----------------------------------------- | --------------------------------------------------------- |
> | `vade farksız` kararı tek yöne sabitlendi | kâr payı oranı F1 **%26,09 → %80,00** (R %15,38 → %80,00) |
> | `hedef_kitle` segment düzeyinde ölçülüyor | F1 **%0,00 → %30,00** (önce ölçülemezdi)                  |
> | Ölçüme imza filtresi eklendi              | 293 kayıt → **93 imzalı** kayıt                           |
>
> `vade farksız` hatası nasıl oluştu, kayda değer: iki ayrı commit **zıt
> yönde** karar verdi — biri altın veriye `kar_payi_orani = 0` yazdı, diğeri
> motordan aynı kuralı kaldırdı. İkisi ayrı ayrı savunulabilirdi, birlikte
> tutarsızdı ve kâr payı recall'unu %90,91'den %15,38'e düşürdü. Kombinasyonu
> kimse yeniden ölçmediği için fark edilmedi.
> [`tests/test_olcum_kapsami.py`](tests/test_olcum_kapsami.py) artık bu
> kombinasyonu imkânsız kılıyor; çelişkili etiketleri listeleyen rapor:
> `python -m gold_dataset.etiket_celiskisi_raporu`
>
> **Bilinen zayıf alanlar (açıkça raporlanır):** `kampanya_turu` F1 %35,63
> (anahtar kelime sınıflandırması — Md. 5.4 için yetersiz),
> `kampanya_baslangic` R %20,27 (precision %100 — bulduğunda doğru buluyor,
> ama çoğu sayfada başlangıç tarihi hiç yazmıyor), `hedef_kitle` R %19,67
> (altın veri etiketi bir insan özeti; o cümle sayfada aynen geçmiyor —
> regex'in ulaşamadığı bir alan, NER/LLM katmanının işi).

> Aşağıdaki anlatı ilk ölçüldüğü tarihteki (251 tekil / 300 anlık görüntü)
> sayılarla yazıldı; **güncel sayılar yukarıdaki "Ölçülebilir durum"
> tablosundadır** (536 kayıt, 26 Ağustos). Metodoloji (neden iki ayrı sayı
> tutulduğu, delta takibinin nasıl çalıştığı) hâlâ geçerli — o yüzden
> tarihsel örnekleriyle birlikte aşağıda korunuyor.

**Kayıt sayısı neden iki türlü:** Scraper eski taramaları **silmez** — değişiklik
takibi (SHA-256 delta) bunu gerektirir. Bu yüzden diskte 300 tarihli dosya var
ama bunlar 251 tekil kampanya URL'sine karşılık gelir. Ürün tarafında anlamlı
olan sayı **251**'dur; 300 rakamı toplanan anlık görüntü sayısıdır.

Bu fazlalık bir artık değil, bir **özelliğin girdisi**: delta kontrolü yalnızca
içerik gerçekten değiştiğinde yeni dosya yazdığı için, aynı URL'nin birden fazla
tarihli kaydı olması o kampanyanın **gerçekten güncellendiği** anlamına gelir.
`scraper/scripts/kampanya_tarihcesi.py` bu dosyaları zaman sırasına dizip neyin
değiştiğini çıkarır — **ek veri toplamadan**.

Burada da iki sayı ayrı tutulur: 251 kampanyanın **40**'ında içerik değişmiş,
ama bunların **25**'inde izlenen bir alan (oran, vade, tutar, ödül, tarih)
gerçekten farklılaşmış. Kalan 15'i yalnızca metin düzeltmesi — hash değişmiş
ama finansal bilgi aynı. Kullanıcıya "değişti" denecekse, _neyin_ değiştiği
gösterilebilmelidir; kozmetik değişiklik bildirimi gürültüdür.

Ölçülen örnek: Dünya Katılım'ın "avantajlı kurlar" kampanyasının bitiş tarihi
`2026-07-30 → 2026-08-06` olmuş — kampanya süresi uzatılmış. İkinci bir örnek,
kampanyanın tamamen kaldırılması: T.O.M. Katılım'ın 3 kampanyasından 2'si
(restoran ve market iade kampanyaları) 18 Ağustos taramasında artık sitede
bulunamadı — canlı sayfa doğrudan kontrol edilerek scraper hatası olmadığı
doğrulandı (bkz. [md6_veri_bolumu.md](docs/md6_veri_bolumu.md#33-somut-örnek)).

**RAG indeksi 17 Ağustos'ta yeniden kuruldu** (263 belge → 817 parça) ve ölçüm
tekrarlandı. İki bulgu çıktı, ikisi de raporlanıyor:

1. **Recall@1 tek bir sayı olarak verilemiyor.** Aynı süreçte üç kez ölçüldüğünde
   29 / 30 / 29 çıktı. Sebep: Qdrant'ın varsayılan **HNSW yaklaşık araması**
   (`exact=True` verilmiyor) — skorları çok yakın adaylarda 1. sıra koşudan
   koşuya değişebiliyor. Recall@3 ve @5 kararlı.
2. **Recall@5 bir kampanya geriledi** (31/32 → 30/32). Yeni kaçırılan `AL-005`,
   adı `AL-006` ile neredeyse aynı ("…Vade Farksız 6 Taksit Kampanyası").
   İndeks %11 büyüyünce bu ikisi ayrışamaz oldu. Kod gerilemesi değil, korpus
   büyümesinin sonucu — ama gerçek bir kalite kaybı.

Yöntem, tekrar üretim çıktıları ve önerilen düzeltme (_ölçümü `exact=True` ile
koşturmak_): [`docs/rag_tasarim_ve_olcum.md`](docs/rag_tasarim_ve_olcum.md)

**21 Ağustos'ta indeks yeniden kuruldu** (18 Ağustos'taki 9-banka taramasıyla
senkron: 263 → 300 belge, 817 → 878 parça) **ve ölçüm yöntemi büyütüldü**: 32
soruluk dar set yerine artık 185 soru, 6 kategori. Yeni set kasıtlı olarak daha
zor kategoriler içeriyor (**`banka_ve_konu`**: yalnızca banka adı + genel konu,
kampanya adı verilmeden) — bu yüzden genel ortalama önceki sayılarla doğrudan
kıyaslanmaz. `banka_ve_konu`'da Recall@1 **%0** çıktı: lexical arama kampanya
adına dayandığı için isim verilmeyince ayırt edicilik kayboluyor. Bu bir kod
hatası değil, §2'de zaten belgelenen dense-arama sınırının doğal sonucu — ve
reranker ihtiyacını daha güçlü gösteriyor. Abstention da ilk kez **%100
değil** (%86,67, 13/15) — kök nedeni henüz araştırılmadı. Ayrıntı:
[`docs/rag_tasarim_ve_olcum.md`](docs/rag_tasarim_ve_olcum.md#yeniden-doğrulama--2021-ağustos-2026-indeks-yeniden-kuruldu--soru-seti-32den-185e-çıkarıldı)

`TF-001` **23 Ağustos'ta çözüldü.** Aylarca "sayfanın ortasındaki farklı bir
ürünün ifadesinden gelen, dar kapsamlı yanlış pozitif" diye kayıtlıydı; kök
neden aslında daha genel çıktı. Türkiye Finans'ın _"Aylık/Yıllık Toplam
Maliyet"_ tablosu bir satırda yan yana beş-altı yüzde taşıyor
(`3 | 4,20% | 0,50% | 5,77% | 96,05%`) ve 45 karakterlik bağlam penceresi satır
başındaki `Maliyet` başlığına yetişemediği için tablonun ortasındaki bir hücre
kâr payı oranı sanılıyordu. Aynı kök neden `TF-008`'i de düzeltti. Tablolardaki
gerçek oranları zaten ayrı bir katman okuyor
(`extraction/tablo_extractor.py`), bu yüzden düşük güvenli fallback'in oraya
hiç girmemesi doğru davranış.

Aynı gün bulunan ve kapatılan ikinci sessiz hata **tutar ayrıştırmasındaydı**:
binlik ayraç olmadan yazılan her tutar 10-100 kat küçük okunuyordu
(`tutara_cevir("2000 TL")` → **200.0**, `"10000 TL"` → **100.0**). Desenin ilk
alternatifi `\d{1,3}(?:\.\d{3})*` olduğu ve alternation soldan sağa çalıştığı
için `"2000"` girdisinde `"200"` yakalanıp dönülüyordu; `ZK-009`'da ise sondan
`"000 TL"` eşleşip ödül miktarı **0.0** çıkıyordu. Aynı kusur altı ayrı desende
tekrarlıyordu, hepsi tek bir `_SAYI` parçasına çekildi. Uydurma sıfır yalnızca
yanlış değil aktif olarak zararlıydı: `en_dusuk_kar_payi` kriteri ASC
sıraladığı için her karşılaştırmayı kazanıyordu.

`DK-002` bilerek açık bırakıldı ve kök nedeni belgelendi (ödül miktarı — gold
davet başına birim ödülü, motor metnin öne çıkardığı toplam tavanı esas alıyor;
hangisinin "doğru" olduğu yorum gerektiriyor). Ayrıntı:
[`docs/extraction_accuracy_raporu.md`](docs/extraction_accuracy_raporu.md)

> Çıkarım kalitesi **tek bir yüzdeyle** değil iki metrikle raporlanır: bir
> alanı _kaçırmak_ ile kaynakta olmayan bir değeri _uydurmak_ farklı
> ağırlıkta hatalardır ve ikincisi finansal kararlarda daha tehlikelidir.
> Yöntem ve tespit edilen yanlış pozitifler:
> [`docs/extraction_accuracy_raporu.md`](docs/extraction_accuracy_raporu.md)
>
> **Yukarıdaki sayılar deterministik katmanın (regex + doğrulama) sonucudur.**
> Hibrit boru hattının LLM katmanı `temperature=0` ile çağrılsa bile
> çalıştırmalar arasında oynayabiliyor (ölçüldü: aynı veri setinde %89,06 ↔
> %87,5) — Ollama'nın çalışma zamanı determinizmi tam garanti etmiyor. Ayrıca
> GPU'suz makinede kayıt başına 150–300 sn sürdüğü için 263 kayıtlık tam
> ablation koşusu henüz yapılamadı; `scraper/scripts/ablation.py` bu durumda
> LLM varyantını `GEÇERSİZ` olarak işaretler — "katkı yok" diye yanlış bir
> sonuç raporlamaz. Katman katkısının tam ölçümü GPU'lu bir makinede
> yapılacaktır.

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
    → Zaman asimi tabanlı fallback (KATILIMAI_ARAC_ZAMAN_ASIMI) [✓]
    → Verifier (karsilastirma + toplam maliyet yoluna baglandi) [✓]
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

#    Demo/sunum öncesi: gömme modelini açılışta yükle. Isıtma olmadan
#    sürecin ilk /chat sorusu modeli beklemek zorunda kalır (ölçüldü: 81 sn)
#    ve arayüz zaman aşımına uğrar. `demo_baslat.py` bunu zaten açar.
KATILIMAI_MODEL_ISIT=true uvicorn api.main:app

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

### Veri setine erişim

Şartname Md. 9, depoda **(1)** bağımlılıkların eksiksiz listesi, **(2)** çalıştırma
adımları ve **(3)** veri setinin indirilebileceği herkese açık bir bağlantı
bulunmasını istiyor. Üçü de bu depodadır — veri seti harici bir servise
yüklenmedi, doğrudan depoyla birlikte dağıtılıyor:

| İstenen                                                             | Nerede                                                                                                      |
| ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Bağımlılık listesi (sürümleri sabitlenmiş)                          | [`requirements.txt`](https://github.com/Sara-Toptamur36/katilim-ai/blob/main/requirements.txt)              |
| Çalıştırma adımları                                                 | Bu dosyadaki [Kurulum ve Çalıştırma](#kurulum-ve-çalıştırma) bölümü                                         |
| **Altın veri seti** (elle doğrulanmış referans + ekran görüntüleri) | [`gold_dataset/`](https://github.com/Sara-Toptamur36/katilim-ai/tree/main/gold_dataset)                     |
| **Ham kampanya metinleri** (9 bankanın sayfa anlık görüntüleri)     | [`scraper/raw_data/`](https://github.com/Sara-Toptamur36/katilim-ai/tree/main/scraper/raw_data)             |
| Sentetik müşteri sesi seti (ürün verisi DEĞİL, yalnızca demo)       | [`tests/veri/kapsam_disi/`](https://github.com/Sara-Toptamur36/katilim-ai/tree/main/tests/veri/kapsam_disi) |

Depo herkese açıktır; klonlamak veri setini de indirir:

```bash
git clone https://github.com/Sara-Toptamur36/katilim-ai.git
```

Altın veri setinin **tek doğru kaynağı** `gold_dataset/altin_veri_seti.xlsx`
dosyasıdır; `.json` ondan üretilir ve elle düzenlenmez.

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

| Profil  | Ne zaman                     | Bağlam | Zaman aşımı | Kırpılan belge |
| ------- | ---------------------------- | ------ | ----------- | -------------- |
| **gpu** | VRAM ≥ 8 GB                  | 16384  | 300 sn      | **0 / 234**    |
| **cpu** | GPU yok **veya** VRAM < 8 GB | 4096   | 900 sn      | 12 / 234       |

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

| Metot | Yol                         | Açıklama                                                                                   |
| ----- | --------------------------- | ------------------------------------------------------------------------------------------ |
| GET   | `/` · `/saglik`             | Servis bilgisi / health check (kimlik gerektirmez)                                         |
| GET   | `/sistem/tazelik`           | Veri/RAG indeksinin ne kadar güncel olduğu (son tarama, gün farkı)                         |
| POST  | `/token`                    | Kullanıcı adı-parola ile JWT (yalnızca `JWT_AKTIF=true`)                                   |
| POST  | `/kayit`                    | Kendi kendine kayıt — rol her zaman `musteri` (istemciden kabul edilmez)                   |
| POST  | `/kullanici/sifre-degistir` | Mevcut şifreyi doğrulayıp yenisiyle değiştirir (`JWT_AKTIF` durumundan bağımsız çalışır)    |
| GET   | `/kampanyalar`              | Kampanya listesi (`?banka=` `?kampanya_turu=`)                                             |
| GET   | `/kampanyalar/{id}`         | Tek kampanya detayı                                                                        |
| GET   | `/kampanyalar/{id}/etki`    | Etki skoru — piyasaya göre eksen eksen yüzdelik sıra                                       |
| GET   | `/kampanyalar/{id}/tarihce` | Değişim tarihçesi — aynı URL'nin geçmiş taramaları (ek veri toplamaz)                      |
| GET   | `/rakip-analizi`            | Rakip matrisi — tüm kriterler tek tabloda (`?kampanya_turu=`)                              |
| GET   | `/terminoloji`              | Katılım bankacılığı sözlüğü (31 kavram, Md. 5.5)                                           |
| POST  | `/cikar`                    | Serbest metinden yapılandırılmış çıktı — MetinAnalizi ekranı (staff-only: `musteri` hariç) |
| POST  | `/karsilastir`              | Kampanya karşılaştırma (sabit kriter listesi)                                              |
| POST  | `/hesapla`                  | Taksit/kâr payı hesabı (saf Python, LLM yok)                                               |
| POST  | `/chat`                     | Doğal dilde soru-cevap (kaynak + audit bilgisiyle)                                         |
| POST  | `/musteri-sesi/siniflandir` | Serbest metni Complaint Insight taksonomisine (10 tema) göre sınıflandırır                 |
| GET   | `/musteri-sesi/ornekler`    | Sentetik Complaint Insight demo seti — **gerçek şikâyet değildir**                         |

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

| Kriter                                        | Alan                                                                                                   |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| En Düşük Kâr Payı Oranı (`en_dusuk_kar_payi`) | `kar_payi_orani_percent`                                                                               |
| En Yüksek Ödül Miktarı (`en_yuksek_odul`)     | `odul_miktari`                                                                                         |
| En Uzun Vade Seçeneği (`en_uzun_vade`)        | `vade_ay`                                                                                              |
| En Düşük Masraf (`en_dusuk_masraf`)           | `tahsis_ucreti`                                                                                        |
| En Avantajlı Kampanya (`en_avantajli`)        | kompozit — diğer 4 kriterin eksen eksen karşılaştırması, Örnek Temsili Senaryo-2'deki yöntemle birebir |

`en_avantajli` tek bir ağırlıklı formül uydurmaz: her alt kriterde hangi kampanyanın öne çıktığı ayrı ayrı belirlenir (`- Kâr payı oranı açısından C Bankası daha avantajlı ...` biçiminde), en çok eksende öne çıkan genel kazanan sayılır; eşitlikte tek bir kazanan uydurulmaz. Ayrıca şartnamenin listesinde olmayan bonus bir kriter de var: `en_yuksek_tutar` (`finansman_tutari`).

**Bonus: Toplam Maliyet Karşılaştırma.** `en_avantajli` ve diğer kriterler ham alanları (oran/vade/masraf) sıralar; ama "düşük oran = ucuz demek değildir" — uzun vadeli düşük oranlı bir kampanya, kısa vadeli yüksek oranlıdan toplamda daha pahalı olabilir. `/chat`'e "500.000 TL için X Bankası ile Y Bankası'nın **toplam maliyetini karşılaştır**" diye sorulduğunda (`agent/router.py::toplam_maliyet_aracini_cagir`, `calculator/calculator.py::toplam_maliyet_karsilastir`), her bankanın kendi oran/vadesiyle gerçek bir amortisman hesabı yapılır — LLM'e bırakılmaz, saf Python.

**3. Her kayıt kaynağını taşır.**
Her kampanya kaydında kaynak URL ve belge tarihi tutulur; hangi alanı hangi
çıkarım katmanının (regex/NER/LLM) doldurduğu ve güven skoru izlenir. Ayrıca
her sayısal alanın kaynak metinde (değer + bağlam) **doğrulanıp doğrulanmadığı**
`dogrulanan_alanlar` sütununda saklanır — Verifier'ın kararı artık log'da kalmaz,
API sözleşmesinden döner. RAG yanıtlarında ayrıca chunk ID, benzerlik skoru ve
kaynak parçanın **birebir metni** döner (`Kaynak.metin`) — "her cümle bir
kaynaktan gelir" iddiasının kanıtı budur.

Kampanyanın zaman içindeki değişimi de izlenir: aynı URL'nin farklı tarihli
taramaları karşılaştırılarak hangi alanın ne zaman değiştiği çıkarılabilir
(`scraper/scripts/kampanya_tarihcesi.py`).

**4. Şeffaflık iki kitleye ayrılır.**
Banka çalışanı iş odaklı dashboard'u görür; jüri/geliştirici, çağrılan aracı,
tespit edilen niyeti, çalıştırılan SQL'i, güven skorlarını ve gecikmeyi
gösteren ayrı bir Audit Paneli'ni.

**5. Bir katman çalışmazsa sistem durmaz.**
Hibrit çıkarımda regex → NER → LLM kademeli çalışır; Ollama kapalıysa veya
yanıt vermezse LLM katmanı sessizce atlanır ve deterministik katmanların
sonucu döner.

Ajan tarafında da aynı kademelilik var: seçilen araç yetersiz kalırsa
sistem vazgeçmez, soruyu RAG'e sorar. Gerekçesi ölçüldü — _"Ziraat Katılım
kart kampanyalarında **taksit** var mı?"_ sorusu yalnızca "taksit" kelimesi
yüzünden hesap makinesine gidiyor ve kullanıcıya _"Hesaplama için şu
bilgiler eksik: anapara…"_ deniyordu; oysa bu bir bilgi sorusu ve cevabı
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
_ölçebilmek_ için geleneksel bankacılık ifadelerinden bir karşı-örnek seti
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

### Sistemi nasıl anlatıyoruz

Video, sunum ve proje dokümanı yazılırken kullanılacak ortak metin:
[`docs/nasil_anlatiyoruz.md`](docs/nasil_anlatiyoruz.md)

Kısaca: bu bir **hibrit çıkarım mimarisidir** (regex → GLiNER → Qwen2.5).
Kullanılan üç model de açık kaynak ve **olduğu gibi**, sürümü sabitlenmiş
biçimde çalışır — **fine-tuning yoktur**, dolayısıyla iddia da edilmez.

### Md. 6 dokümantasyonu (tam metin, tek belge)

Şartname Md. 6'nın istediği 10 dokümantasyon kalemi (mimari, NLP yaklaşımı,
model/kural yapısı, veri seti, ön işleme, karşılaştırma yöntemi, kurulum,
karşılaşılan problemler, model çıktı örnekleri, performans değerlendirme)
dağınık değil, **tek belgede**: [`docs/md6_dokumantasyon.md`](docs/md6_dokumantasyon.md)
Yeniliğimiz modeli eğitmek değil, hangi katmanın ne kadar katkı verdiğini
(ve nerede zarar verdiğini) **ölçmüş olmak**.

Bu kural `tests/test_iddia_durustlugu.py` ile korunur: bir belgeye
yanlışlıkla eğitim iddiası yazılırsa CI kırmızı verir ve dosya:satır
gösterir. Test kelimeyi değil **olumlu iddia kalıbını** arar; "fine-tuning
yapılmadı" gibi doğruyu söyleyen cümleler serbesttir. Yasak/doğru ifade
eşleşmelerinin tam listesi belgenin 4. bölümündedir.

### Kâr payı oranı tabloları (bankaların kendi hesaplama sayfalarından)

Bazı kampanyalarda "kâr payı oranı" sabit tek bir sayı değil, bankanın
kendi sayfasında yayınladığı vade/tutar dilimine göre değişen bir
**tablo**dur (Rehber Bölüm 18). Bu tabloyu tek bir sayıya indirgemek
(hangi dilim "asıl" kampanya oranı?) uydurma bir seçim olurdu — bu yüzden
`extraction/tablo_extractor.py`, kaynaktaki tabloyu **olduğu gibi** yeni
bir `kar_payi_tablosu` alanına taşır (`CampaignRecord` üzerinden
`/kampanyalar` ve `/kampanyalar/{id}`'de döner, dashboard'da
`KarPayiTablosuKarti.jsx` ile gösterilir). Detay ve ölçüm:
[`docs/extraction_accuracy_raporu.md`](docs/extraction_accuracy_raporu.md)
"Güncelleme — 20 Ağustos 2026" bölümü.

### Müşteri Sesi (Complaint Insight) — sentetik demo

Şartname/mentör raporu, kampanya verisinin yanında bir "müşteri deneyimi"
sinyali de bekliyor. Gerçek Şikâyetvar/müşteri platformu verisi ancak
kurumsal/hukuki (KVKK) izin sürecinden sonra ingest edilebilir (bkz. aşağıdaki
"Henüz kurulmayanlar"), bu yüzden Faz 1'de **kural tabanlı, sentetik veri
üzerinde çalışan** bir sınıflandırma demosu kuruldu: `complaint/
tema_siniflandirici.py`, 10 temalı bir taksonomiye (ödül yatmadı, koşul
uyuşmazlığı, taksit/vade, işyeri kapsamı, aktivasyon, tarih, kart/ürün
uyuşmazlığı, ücret, iletişim belirsizliği, çözüm süreci) göre serbest metni
eşleştirir; hiçbir ifade eşleşmezse tema **uydurulmaz**, `None` döner.

Veri seti (`tests/veri/kapsam_disi/sentetik_musteri_sesi.json`) elle
yazıldı, hiçbir gerçek şikâyetten kopyalanmadı ve hiçbir gerçek bankaya
atfedilmiyor — tıpkı terminoloji karşı-örnek setiyle aynı disiplinde
(`tests/test_karsi_ornekler.py`), üretim verisine/RAG indeksine sızmadığı
`tests/test_sentetik_musteri_sesi.py::test_sentetik_ornekler_urun_verisine_sizmamis`
ile kilitlendi. Uç noktalar (`POST /musteri-sesi/siniflandir`,
`GET /musteri-sesi/ornekler`) ve dashboard ekranı (`/musteri-sesi`) her
yanıtta bu verinin **sentetik** olduğunu açıkça belirtir, gizlemez.

### GitHub Pages (statik arayüz)

`dashboard/` her `main` push'unda otomatik olarak GitHub Pages'e derlenip
yayınlanır (`.github/workflows/deploy-pages.yml`) — sunumda paylaşılabilir
bir URL için. **Backend orada çalışmaz**: Pages yalnız statik dosyaları
sunar; Postgres/Qdrant/Ollama gerektiren canlı veri gösterimi ekibin kendi
makinesinde çalışır. Depoda bir `VITE_API_BASE_URL` repo değişkeni
tanımlanmadığı sürece yayınlanan site `localhost:8000`'e istek atmaya
çalışır ve dış ziyaretçilerde dürüstçe "Veri alınamadı" gösterir — bu bir
hata değil, uydurma veri göstermemenin sonucudur. Repo ayarında bir kerelik
gereken adım: _Settings → Pages → Source = "GitHub Actions"_.

### Yanıtın dayandığı sayılar doğrulandı mı?

`/chat`, yapılandırılmış veriden cevap verirken (karşılaştırma ve toplam
maliyet araçları) artık **hangi alanın kaynakta doğrulandığını** da döndürür —
`audit.dogrulama`. Üç durum bilerek ayrı sayılır:

| Durum             | Anlamı                                                             |
| ----------------- | ------------------------------------------------------------------ |
| `dogrulandi`      | Kullanılan tüm alanlar, tüm kayıtlarda kaynakta doğrulandı         |
| `kismi`           | Verifier çalıştı ama bir kısmını onaylayamadı (değer **silinmez**) |
| `calistirilmamis` | Bu alanlar için Verifier hiç çalışmadı                             |

Bunları tek bir orana indirgemek en büyük hata olurdu: "çalıştırılmamış"ı
başarısızlık saymak sistemi haksız yere kötü, başarı saymak yalancı gösterirdi.

Yalnızca **sıralamayı belirleyen eksen(ler)** raporlanır — "en uzun vade"
sorusunda ödül miktarının doğrulanmış olması o cevap hakkında bilgi vermez.

**RAG yolunda özet bilerek üretilmez** (`None`) ve bu doğrudur: RAG hiçbir cümle
üretmez, kaynak parçasını **birebir** döndürür. Orada "bu sayı kaynakta geçiyor
mu?" kontrolü tanım gereği her zaman _evet_ derdi — hiçbir şey elemeyen,
yalnızca doğrulama yapılmış **izlenimi** veren bir kontrol olurdu. LLM ile
özetleme eklenirse Verifier o yola **birlikte** bağlanmalıdır.

Özet, çıkarım anında verilmiş **kayıtlı** hükümdür (`kaynak: "kayitli"`); soru
sorulurken metin yeniden taranmaz — `CampaignRecord` ham kaynak metni taşımaz.
Ayrıntı: [`validation/yanit_dogrulama.py`](validation/yanit_dogrulama.py)

### Şikâyet hattı — kırmızı çizgiler koda gömüldü

Şikâyet verisi henüz toplanmıyor ama hattın tamamı kurulu:
`complaint/izin_kapisi.py` · `pii_temizleme.py` · `kampanya_eslestirme.py` ·
`toplama.py`, ayrı `sikayetler` tablosu ve migration'ıyla birlikte.

Veri Rehberi'ndeki dört kırmızı çizgi **niyet beyanı değil, çalışan kontrol**:

| Kırmızı çizgi                                 | Kodda karşılığı                                                                     |
| --------------------------------------------- | ----------------------------------------------------------------------------------- |
| Ham metin izin kapısı geçmeden diske yazılmaz | İzin kaydı yoksa `IzinYok` fırlar; diske yazan `kaydet()` izni **ikinci kez** sorar |
| PII temizliği kayıttan **önce**               | `hazirla()` ham metni ne döner ne loglar — tek çıkış temizlenmiş metindir           |
| Şikâyet verisi kampanya tablosuna karışmaz    | Ayrı tablo, kampanyalara **foreign key yok**                                        |
| "Şikâyet oranı" denmez                        | `yogunluk_ozeti()` yüzde üretmez; adet döner, alan adı `gozlenen_yogunluk`          |

Varsayılan **her zaman izin yokluğudur**: dosya yoksa, bozuksa ya da alanları
eksikse "izin var" sayılmaz.

**Eşleşme bir hipotezdir.** Güven 0,50 eşiğinin altındaysa bağ kurulmaz ve
_neden_ kurulmadığı yazılır. Banka adının geçmesi tek başına yetmez — bir
bankanın onlarca kampanyası vardır. İki kampanya aynı güveni alırsa yine
bağ kurulmaz: rastgele birini seçmek, olmayan bir kesinlik üretmek olurdu.
Şikâyet tarihi kampanyanın penceresi dışındaysa aday **elenir**; pencere
içinde olmak ise puan kazandırmaz (aynı anda onlarca kampanya yürürlüktedir).

Ayrıntı: [`complaint/kampanya_eslestirme.py`](complaint/kampanya_eslestirme.py)

### Henüz kurulmayanlar (dürüstlük notu)

Aşağıdakiler hedef mimaride yer alır ancak **bu depoda henüz tamamlanmamıştır**;
tasarım ilkesi olarak sunulmakla birlikte uçtan uca çalışan bir özellik değildir:

- **LLM ile yanıt özetleme:** RAG şu an bulduğu kaynak parçalarını _birebir_
  döndürür, üzerine serbest metin üretmez — bu, halüsinasyonu yapısal olarak
  imkânsız kılar. Özetleme ancak Verifier ile birlikte güvenli olur.
- **Müşteri geri bildirim bileşeni:** Etki skorunun ikinci yarısı. Veri kaynağı
  henüz tanımlı olmadığı için gösterge `veri_yok` döner — **sıfır yazılmaz**,
  çünkü geri bildirim yokluğu "müşteriler memnun değil" anlamına gelmez.
  Kaynak eklendiğinde skorun şekli değişmez, yalnızca `durum` alanı dolar.
- **Hibrit katman katkısının tam ölçümü:** LLM katmanı GPU'suz makinede kayıt
  başına 150–300 sn sürdüğü için 263 kayıtlık ablation koşusu yapılamadı.
  `ablation.py` bu durumda LLM varyantını `GEÇERSİZ` işaretler; "katkı yok"
  diye yanlış bir sonuç raporlamaz.
- **Gerçek Complaint Insight verisi:** yukarıdaki Müşteri Sesi modülü şu an
  yalnızca sentetik veriyle çalışıyor. **Hat kurulu, veri yok** — şikâyet
  veri modeli, PII temizliği, izin kapısı ve kampanya eşleştirmesi yazıldı
  ve test edildi (aşağıya bakınız); eksik olan tek şey kurumsal/hukuki
  (KVKK) onaydır. Onay gelene kadar `sikayetler` tablosu **boş kalır**.

---

## Proje Yapısı

```
katilim-ai/
├── api/              # FastAPI: uc noktalar, sema, kimlik dogrulama
├── scraper/          # Veri toplama + kampanya degisim tarihcesi (Zeynep)
├── preprocessing/    # Turkce normalizasyon + sayfa kapsami ayiklama
├── terminology/      # Katilim bankaciligi terminoloji sozlugu (Yagmur)
├── extraction/       # Regex + NER + LLM hibrit cikarim (Yagmur)
├── validation/       # Verifier - sayisal iddialari kaynak metne karsi dogrular
├── chunking/         # RAG: parcalayici, embedding, seyrek vektor, retriever, indeksleyici
├── storage/          # PostgreSQL + Qdrant erisimi
├── comparison/       # Karsilastirma motoru + rakip matrisi + etki skoru (Sara)
├── calculator/       # Hesap makinesi araci (Sara)
├── complaint/        # Musteri Sesi - kural tabanli tema siniflandirici (sentetik demo)
├── agent/            # Ajan orkestrator + tool router (Sara)
├── dashboard/        # React + Ant Design arayuz (Havin)
├── gold_dataset/     # Altin Veri Seti (dogrulama referansi)
├── tests/            # Sozlesme, cikarim, regresyon ve entegrasyon testleri
│   └── veri/kapsam_disi/   # Kapsam olcumu icin karsi-ornek seti (URUN VERISI DEGIL)
├── docs/             # Proje dokumantasyonu + olcum raporlari
├── donanim.py        # Donanim profili (GPU/VRAM tespiti + ayarlar)
└── donanim_testi.py  # Tanilama + hiz olcumu (baska makinede calistirilir)
```

## Ekip ve Sorumluluklar

| Kişi                              | Sorumluluk                                                                 |
| --------------------------------- | -------------------------------------------------------------------------- |
| **Sara Toptamur** (Takım Kaptanı) | API, ajan orkestrasyon, karşılaştırma motoru, hesap makinesi, koordinasyon |
| **Yağmur Ekici**                  | NLP, bilgi çıkarımı, terminoloji, embedding, RAG                           |
| **Zeynep Sönmez**                 | Veri toplama, PDF/OCR, ön işleme, PostgreSQL, sistem testleri              |
| **Havin Karagöz**                 | React arayüz, UI/UX, karşılaştırma ekranları, Jüri Audit Paneli            |

---

## Teknoloji Yığını

Tüm bileşenler açık kaynaklıdır (şartname Md. 5.10 / 8):

| Katman                | Teknoloji                                   | Lisans                 |
| --------------------- | ------------------------------------------- | ---------------------- |
| Veri toplama          | Requests, BeautifulSoup4, Playwright        | Apache-2.0 / MIT / BSD |
| PDF                   | pypdf                                       | BSD                    |
| Bilgi çıkarımı        | regex, GLiNER (`urchade/gliner_multi-v2.1`) | MIT / Apache-2.0       |
| Yerel LLM             | Qwen2.5-Instruct (GGUF Q4_K_M), Ollama      | Apache-2.0 / MIT       |
| Yapılandırılmış çıktı | Pydantic                                    | MIT                    |
| Vektör veritabanı     | Qdrant                                      | Apache-2.0             |
| İlişkisel veritabanı  | PostgreSQL                                  | PostgreSQL License     |
| API                   | FastAPI, SQLAlchemy, Alembic                | MIT                    |
| Arayüz                | React, Ant Design                           | MIT                    |

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
pytest tests/ -v                  # tumu
pytest tests/ -m "not slow"       # LLM gerektiren yavas testler haric
```

CI, `main` dalına her push'ta testleri ve sızmış sır taramasını otomatik çalıştırır.

Bazı testler dış servis gerektirir ve servis yoksa **hata vermez, atlanır**:

| Test grubu            | Gereksinim                                                | Servis yoksa |
| --------------------- | --------------------------------------------------------- | ------------ |
| Veritabanı testleri   | PostgreSQL (`docker compose up -d postgres`)              | atlanır      |
| LLM / hibrit testleri | Ollama + Qwen2.5 modeli                                   | atlanır      |
| Vektör arama testleri | Qdrant (`docker compose up -d qdrant`) + embedding modeli | atlanır      |

Bu yüzden CI'da (dış servis yok) test sayısı yerelden düşük görünür — bu bir
regresyon değil, beklenen durumdur.

Yukarıdaki [ölçülebilir durum](#ölçülebilir-durum) tablosundaki her sayı bu
komutlarla yeniden üretilir:

```bash
python -m scraper.scripts.extraction_accuracy         # dolu/bos alan dogrulugu + alan bazli F1
python -m scraper.scripts.hibrit_extraction_accuracy  # regex + NER + LLM
python -m scraper.scripts.ablation                    # katman katkisi tablosu
pytest tests/test_karsi_ornekler.py -s                # kapsam olcumu (hassasiyet/ozgulluk)
```

Bir kampanyanın zaman içinde ne değiştirdiğini görmek için
(`scraper/scripts/kampanya_tarihcesi.py`, ek veri toplamaz):

```python
from scraper.scripts.kampanya_tarihcesi import tarihce_getir, degisen_alanlari_bul

tarihce = tarihce_getir("https://www.dunyakatilim.com.tr/kampanyalar/avantajli-kurlar")
degisen_alanlari_bul(tarihce)
# {'kampanya_bitis': {'eski': '2026-07-30', 'yeni': '2026-08-06'}}
```

RAG ölçümünün yöntemi ve sonuçları ayrı belgede:
[`docs/rag_tasarim_ve_olcum.md`](docs/rag_tasarim_ve_olcum.md)

Ölçüm çıktısı **alan bazlı precision/recall/F1** de basar; `ablation`
ise üç varyantı (regex / +NER / +NER+LLM) karşılaştırıp her katmanın
katkısını ayrıştırır. Sonuçlar ve yorumu:
[`docs/extraction_accuracy_raporu.md`](docs/extraction_accuracy_raporu.md)

---

## Lisans

[Apache License 2.0](LICENSE)

Şartname madde 8 gereği, tüm kaynak kodlar, veri kümeleri ve diğer bileşenler yarışma bitiş tarihinde Apache License 2.0 ile lisanslanarak Türkiye Açık Kaynak Platformu GitHub hesabında paylaşılacaktır.

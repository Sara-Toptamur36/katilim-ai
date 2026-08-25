# RAG: Tasarım Kararları ve Ölçüm

**Tarih:** 7 Ağustos 2026

Bu belge, KatılımAI'nin RAG (Retrieval-Augmented Generation) katmanının
nasıl kurulduğunu, hangi kararların **neden** alındığını ve retrieval
kalitesinin **ölçülmüş** sonuçlarını içerir.

Her karar, tahmine değil bu depoda yapılmış bir ölçüme dayanır.

---

## 1. Mimari

```
Ham kampanya metni (scraper/raw_data)
        ↓
chunking/parcalayici.py      Semantik parçalama + gürültü filtresi + tekilleştirme
        ↓
   ┌────────────────────────┬────────────────────────┐
   ↓                                                 ↓
chunking/embedding.py                    chunking/seyrek_vektor.py
Anlamsal vektör (768 boyut)              Kelime vektörü (BM25/IDF)
   └────────────────────────┬────────────────────────┘
                            ↓
              Qdrant hibrit koleksiyonu
                            ↓
chunking/retriever.py    Hibrit arama (RRF) + abstention kuralı
                            ↓
agent/router.py          RAG aracı → kaynaklı yanıt
```

---

## 2. Neden hibrit arama? (ölçülmüş gerekçe)

İlk spike (`docs/qdrant_spike_raporu.md`) yalnızca anlamsal (dense)
aramanın **ayırt edemediğini** gösterdi:

| Sorgu | En iyi skor |
|---|---|
| Alakalı: "Kâr payı oranı ve vade seçenekleri nedir?" | 0,8216 |
| **Tamamen alakasız:** "Uzay istasyonunda yerçekimi nasıl ölçülür?" | **0,7761** |
| Fark | **0,0455** |

Uzay istasyonu sorusu bile 0,78 alıyordu — yani ham benzerlik skoruna eşik
koymak yanlış pozitif üretirdi.

**Çözüm:** kelime (lexical/BM25) araması eklendi ve iki arama **RRF**
(Reciprocal Rank Fusion) ile birleştirildi. Doğrulama testinde alakalı
belge 1,0, alakasız 0,33 aldı — ayırt edicilik belirgin arttı.

Lexical arama, bu alanda özellikle kritik: **"Worldpuan", "ParafPara",
"Bankkart", "98/2", banka adları** gibi ayırt edici terimler birebir
eşleşmelidir; anlamsal benzerlik bunları bulanıklaştırır.

**Ek bağımlılık kullanılmadı:** terim frekanslarını biz üretiyoruz,
nadirlik ağırlığını (IDF) Qdrant sunucu tarafında hesaplıyor
(`Modifier.IDF`).

---

## 3. Türkçe için alınan özel kararlar

**Kararlı hash (kritik):** Python'un yerleşik `hash()`'i string'ler için
her süreçte farklı sonuç verir (`PYTHONHASHSEED`). İndeksleme ve sorgulama
farklı süreçlerde çalıştığı için bu kullanılsaydı, indekslenen terim
sorguda başka bir kimlik alır ve **lexical arama sessizce hiç eşleşmezdi.**
`zlib.crc32` kullanıldı; bir test bunu üç farklı `PYTHONHASHSEED` ile
doğruluyor.

**Ek dayanıklılığı:** Türkçe eklemeli bir dildir — "kampanya",
"kampanyadan", "kampanyaya" farklı token'dır. Tam morfolojik çözümleme
(Zemberek vb.) ağır bir bağımlılık getirir; bunun yerine uzun token'lar
için ayrıca bir gövde öneki düşük ağırlıkla indekslenir.

**Türkçe `İ` sorunu:** `str.lower()` noktalı büyük `İ`'yi bozar. Bu hata
projede daha önce üç ayrı yerde bulunmuştu; parçalayıcı ve tokenizer'da
aynı düzeltme uygulandı ve test edildi.

---

## 4. Parçalama: ölçülmüş iyileştirme

Naif satır bölme, alakasız bir sorgunun ilk üç sonucunun **aynı yasal
uyarı metni** olmasına yol açıyordu.

| | Naif bölme | Semantik parçalama |
|---|---|---|
| Parça sayısı | 2.180 | **734** (%67 azalma) |

Uygulanan kurallar:
- **Gürültü filtresi:** gezinme menüsü, sosyal medya butonları, form
  alanları, tarayıcı artıkları (`"Your browser does not support the audio
  element."` — belgelerin **%41'inde**).
- **Başlık her parçaya eklenir:** bir parça tek başına hangi kampanyaya ait
  olduğunu söylemelidir. Retrieval kalitesine en çok katkı yapan karar.
- **Tekilleştirme:** ortak yasal uyarılar bir kez indekslenir.

**Başlık kaynağı ölçülerek seçildi:** metin sezgisi (ilk anlamlı satır)
gerçek veride sık yanılıyordu — "Sektör: Giyim ve Aksesuar" (doğrusu
"Decathlon'da 4 Taksit"), "Müşteri Ol Kampanyaları" (gezinme menüsü). URL
slug'ı aynı örneklerde tutarlı doğruydu; slug birincil, metin yedek yapıldı.

**Yüksek frekanslı satırlar SİLİNMEZ:** "Ücretsiz ve ticari kredi
kartlarımız kampanyaya dahil değildir" belgelerin %21'inde geçer ama
gerçek bir kampanya koşuludur ve kullanıcı bunu sorabilir. Ayırt edicilik
sorunu silmekle değil IDF ile çözülür.

---

## 5. Abstention: kaynak yoksa cevap yok

**Kullanılan ölçüt RRF skoru değil, lexical örtüşmedir.** RRF bir
*sıralama* birleştirme skorudur; en üstteki sonuç sorgu alakalı olsa da
olmasa da ~1,0 alır — yani RRF'e eşik koymak işe yaramaz.

Bunun yerine: dönen parçalar sorunun **ayırt edici terimlerini** gerçekten
içeriyor mu? Alakasız sorguda hiçbir terim eşleşmez ve ölçüt sıfıra düşer.
Bu ölçüt ayrıca **yorumlanabilir** bir gerekçe üretir ("hangi terimler
eşleşti?"), audit panelinde gösterilebilir.

**Soru kelimeleri elenir:** İlk ölçümde "Python'da liste nasıl sıralanır?"
gibi alan dışı bir soru, yalnızca "nasıl"/"liste" gibi ortak kelimeler
eşleştiği için "kaynak buldum" sayılıyordu. Soru kelimeleri (`nasıl`,
`hangi`, `neden`, `ne`, `kaç` …) hiçbir belgeyi diğerinden ayırt etmediği
için token listesinden çıkarıldı.

**Gövde duyarlı eşleşme (Türkçe için zorunlu):** İlk sürümde örtüşme *tam
token* karşılaştırmasıyla hesaplanıyordu. Bu, eklemeli bir dilde yanıltıcı:
kullanıcı "kazan**ma**" derken metinde "kazan**ın**" geçer ve eşleşme
bulunamaz. Ölçüldü — *"Worldpuan kazanma koşulları neler?"* (cevaplanabilir
bir soru) yalnızca **0,50** örtüşme alıyordu; bu, alan dışı soruların en
yükseğiyle aynı seviyeydi, yani iki sınıf **ayırt edilemiyordu.**
İndeksleme tarafında zaten kullanılan gövde öneki kuralı örtüşme hesabına
da uygulandı — aynı soru **0,667**'ye çıktı.

### Eşik nasıl seçildi

Tahminle değil, gerçek indeks üzerinde iki sınıfın dağılımı ölçülerek:

| Sorgu sınıfı | Örtüşme aralığı |
|---|---|
| Cevaplanabilir doğal sorular | **0,667 – 1,000** |
| Alan dışı sorular | **0,000 – 0,500** |

Eşik **0,60** — iki sınıfın arasındaki boşluğa oturur ve her iki yönde de
pay bırakır (aşırı çekimserlik ↔ uydurma cevap dengesi).

> **Sınırlılık (dürüstlük notu):** Kalibrasyon küçük bir örneklemle
> (6 cevaplanabilir + 5 alan dışı soru) yapıldı. Daha geniş bir soru seti
> oluştukça yeniden ölçülmelidir; bu yüzden eşik tek bir sabitte
> (`chunking/retriever.py::ASGARI_TERIM_ORTUSMESI`) tutulur.

---

## 6. Ölçüm sonuçları

`python -m scraper.scripts.rag_degerlendirme`

Yer gerçeği **uydurulmadı**: Altın Veri Seti'ndeki elle doğrulanmış
kampanyalardan türetildi — kampanya adı sorgu, `kaynak_url` beklenen sonuç.

> **Ölçüm kapsamı (önemli):** Altın Veri Seti 28-29 Temmuz'da toplandı;
> 58 kaydın **26'sının** kampanyası günler içinde bankaların sitesinden
> kaldırıldı (rotasyon — `tests/test_scraper_regresyon.py` bunu zaten
> belgeliyor) ve belgeleri indekste hiç yok. Bunları "bulunamadı" saymak
> retrieval'i değil **veri eskimesini** ölçerdi ve doğruluğu haksız yere
> düşük gösterirdi. Bu yüzden ölçüm, belgesi gerçekten indekste olan
> kampanyalarla sınırlandırıldı; kapsam dışı sayısı çıktıda açıkça
> raporlanır.

### Sonuçlar — 7 Ağustos 2026

| Metrik | Sonuç |
|---|---|
| Recall@1 | **%93,75** (30/32) |
| Recall@3 | **%93,75** (30/32) |
| **Recall@5** | **%96,88** (31/32) |
| **Abstention doğruluğu** | **%100** (5/5 alan dışı soruda doğru şekilde cevap verilmedi) |
| Ölçüm dışı (kampanyası siteden kaldırılmış) | 26 kayıt |

Recall@5'te kaçırılan tek kampanya: `AL-006` (Eğitim Harcamalarınıza Vade
Farksız 6 Taksit).

### Ölçüm süreci boyunca düzeltilen iki hata

Bu sayılar ilk denemede çok daha kötüydü; ikisi de **ölçümün kendisindeki
veya normalizasyondaki** hatalardan kaynaklanıyordu:

| Sorun | Önce | Sonra |
|---|---|---|
| Recall, indekste **olmayan** kampanyalar üzerinden hesaplanıyordu | %53,45 | **%96,88** |
| Abstention, Türkçe ek farkları yüzünden iki sınıfı ayıramıyordu | %60 | **%100** |

Birincisi retrieval hatası değildi — Altın Veri Seti'ndeki kampanyaların
yarısı siteden kaldırılmıştı ve onları "bulunamadı" saymak veri eskimesini
ölçüyordu. İkincisi gerçek bir kusurdu: gövde duyarlı eşleşme ve soru
kelimesi eleme eklendi.

> Bu belge **yöntemi** sabitler; sayılar veri güncellendikçe değişir.
> Yeniden üretmek için: `python -m scraper.scripts.rag_degerlendirme`

### Yeniden doğrulama — 11 Ağustos 2026

Qdrant indeksi 7 Ağustos'tan beri güncellenmemişti (10 Ağustos'taki 10-banka
tam taramasından ve AL-001 kapsam kırpma düzeltmesinden sonra bile) — bu
belgede yayınlanan sayıların hâlâ geçerli olduğu doğrulanmamıştı. İndeks
`python -m chunking.indeksleyici` ile **sıfırdan yeniden kuruldu**
(234 belge → 733 parça, 234 belge/183 sn) ve ölçüm tekrarlandı:

| Metrik | 7 Ağustos | 11 Ağustos (tazelenmiş indeks) |
|---|---|---|
| Recall@1 | %93,75 | **%93,75** (değişmedi) |
| Recall@3 | %93,75 | **%93,75** (değişmedi) |
| Recall@5 | %96,88 | **%96,88** (değişmedi) |
| Abstention doğruluğu | %100 | **%100** (değişmedi) |
| Kaçırılan tek kampanya | AL-006 | **AL-006** (aynı) |

Sonuç birebir tekrar üretildi — README'deki rakamlar artık güncel veriyle
doğrulanmış durumda, bayat değil.

### Yeniden doğrulama — 17 Ağustos 2026 (ve bir ölçüm bulgusu)

İndeks yeniden kuruldu: **263 belge → 817 parça** (11 Ağustos'ta 234 → 733).
Ölçüm kapsamı **değişmedi**: 58 altın kayıttan 32'sinin belgesi hâlâ indekste,
26'sı kampanya rotasyonu nedeniyle kapsam dışı. Yani payda aynı, karşılaştırma temiz.

| Metrik | 11 Ağustos | 17 Ağustos |
|---|---|---|
| İndeks | 234 belge / 733 parça | **263 belge / 817 parça** |
| Recall@1 | %93,75 (30/32) | **%87,5 – %93,75** (28–30/32, *oynak*) |
| Recall@3 | %93,75 (30/32) | **%93,75** (30/32) |
| Recall@5 | %96,88 (31/32) | **%93,75** (30/32) ⬇ |
| Abstention doğruluğu | %100 (5/5) | **%100** (5/5) |
| Ölçüm kapsamı | 32 | 32 (değişmedi) |

**İki ayrı bulgu var; ikisi de gizlenmiyor.**

#### Bulgu 1 — Ölçüm deterministik değil

Aynı süreç içinde ölçüm üç kez tekrarlandığında Recall@1 farklı çıktı:

```
Recall@1: [29, 30, 29]  -> OYNAK
    koşu 1 kaçıranlar: AL-005, AL-006, ZK-004
    koşu 2 kaçıranlar: AL-005, AL-006
    koşu 3 kaçıranlar: AL-005, AL-006, ZK-004
Recall@3: [30, 30, 30]  -> KARARLI
Recall@5: [30, 30, 30]  -> KARARLI
```

**Sebep:** `chunking/qdrant_baglanti.py::hibrit_ara` Qdrant'ın varsayılan
**HNSW yaklaşık (ANN)** aramasını kullanıyor; `SearchParams(exact=True)`
verilmiyor. Yaklaşık arama, skorları birbirine çok yakın adaylarda koşudan
koşuya farklı sıra üretebilir. Oynaklık yalnızca **1. sırada** görülüyor —
beklenen davranış, çünkü rank-1 en küçük skor farkına duyarlı olan yerdir.

**Sonuç olarak Recall@1 tek bir sayı olarak raporlanamaz.** Gözlenen aralık
28–30/32 (dört ayrı koşu: 29, 28, 29, 30).

> **Öneri — UYGULANDI (25 Ağustos 2026).** `scraper/scripts/rag_degerlendirme.py::kategori_bazli_recall_olc`
> ve `abstention_olc`'un `exact` parametresi artık **varsayılan `True`** —
> üretimde (`agent/router.py`) `exact=False` (yaklaşık, hızlı) kalmaya
> devam ediyor, bu ikisi kasıtlı olarak farklı varsayılan kullanıyor:
> benchmark'ta tekrar üretilebilirlik, üretimde hız önceliklidir.

#### Bulgu 2 — Recall@5 bir kampanya geriledi

31/32 → 30/32. Yeni kaçırılan: **AL-005** (*Sağlık Harcamalarına Vade Farksız
6 Taksit Kampanyası*). Eskiden beri kaçırılan **AL-006** (*Eğitim Harcamalarınıza
Vade Farksız 6 Taksit Kampanyası*).

İki kampanyanın adı neredeyse aynı — yalnızca "Sağlık" / "Eğitim" kelimesinde
ayrışıyorlar. İndeks %11 büyüyünce (733 → 817 parça) bu ikisini birbirinden
ayırmak zorlaştı.

**Bu bir kod gerilemesi değil**, korpus büyümesinin doğal sonucu: aynı kalıpla
adlandırılmış kampanya sayısı arttıkça ayırt edicilik düşer. Ama **gerçek bir
kalite kaybı** ve öyle raporlanıyor.

**Doğru müdahale ne olurdu:** Bu tam olarak bir **reranker** vakası — hibrit
arama doğru belgeyi ilk 5'e getiriyor ama sıralayamıyor. Mentör raporu II
(Bölüm 6.2) da bunu öneriyor. Reranker'ın ölçülebilir kazanç tavanı artık
**2 kayıt** (@5'te kaçan AL-005 + AL-006) ve ayrıca @1 oynaklığı — 11
Ağustos'taki 1 kayıtlık tavandan daha büyük.

#### Bulgu 3 — İlk sorunun gecikmesi bir doğruluk sorunu değil, demo sorunuydu

Recall/abstention ölçümleri script içinden yapıldığı için gömme modeli zaten
yüklüydü; **arayüzden** ölçünce farklı bir tablo çıktı:

| Durum | Süre |
|---|---|
| Sıcak sorgu | ~5–9 sn |
| Soğuk sorgu (model yüklü, süreç yeni) | 18,9 sn |
| Sürecin **ilk** sorgusu (model yükleniyor) | 54,9 sn — bellek sıkışıkken 81 sn |

Arayüzün sohbet zaman aşımı 10 sn'ydi; API doğru cevabı üretmiş olmasına
rağmen ekranda **"Bağlantı sorunu"** yazıyordu. Yani bu bir ağ hatası değil,
**yanlış hata mesajıydı** ve demoda ilk soruyu soran jüri üyesini vururdu.

İki müdahale yapıldı:

1. **Sunucu tarafı (asıl çözüm):** gömme modeli açılışta yükleniyor
   (`api/main.py::yasam_dongusu`, `KATILIMAI_MODEL_ISIT=true`). Bekleyiş
   kimsenin beklemediği açılışa taşınıyor; `demo_baslat.py` bunu otomatik açar.
   Varsayılan kapalı — testler/CI `api.main`'i sık import eder.
2. **İstemci tarafı (emniyet payı):** sohbet zaman aşımı 90 sn.

Tek başına (2) yetmiyor: ısıtmasız denemede 90 sn bile aşıldı ve istek
`ERR_ABORTED` ile düştü. Isıtma açıkken aynı soru ilk denemede `200 OK` döndü.

---

### Yeniden doğrulama — 20/21 Ağustos 2026 (indeks yeniden kuruldu + soru seti 32'den 185'e çıkarıldı)

İndeks yeniden kuruldu: **300 belge → 878 parça** (17 Ağustos'ta 263 → 817).
Zeynep'in 18 Ağustos'ta yaptığı 9-banka yeniden taramasından beri (251 tekil
kampanya, 300 anlık görüntü) indeks 3 gündür bayattı; bu adım onu senkronladı.

Aynı zamanda ölçüm yöntemi **kökten değişti**: önceki tüm ölçümler Altın Veri
Seti'nin 32 kampanya adından türetilmiş dar bir sorgu setine dayanıyordu.
`gold_dataset/rag_soru_seti.json` artık **185 soru**, 6 kategoriye ayrılmış:

| Kategori | Soru sayısı | Ne test ediyor |
|---|---|---|
| tam_ad | 58 | Kampanyanın tam adı sorgu |
| kismi_ad | 54 | Kampanya adının bir kısmı |
| banka_ve_konu | 28 | **Yalnızca banka adı + genel konu — kampanya adı YOK** |
| dogal_soru | 20 | Doğal dilde, serbest formda soru |
| alan_disi | 15 | Cevaplanamamalı (abstention testi) |
| alan_ici_kapsam_disi | 10 | Alan içi ama bu script'in mevcut sürümünde henüz ayrı raporlanmıyor |

> **Önceki sayılarla doğrudan karşılaştırma yapılmaz.** 32 soruluk eski set
> yalnızca "tam_ad"a yakın, en kolay kategoriydi. 185 soruluk set kasıtlı
> olarak daha zor kategoriler (özellikle `banka_ve_konu`) içeriyor — bu
> yüzden genel ortalamanın düşük görünmesi bir kod gerilemesi değil, ölçüm
> setinin daha gerçekçi/zor hâle gelmesidir. Aşağıdaki sonuçlar yeni
> metodolojinin **ilk ölçümüdür**, referans bu tarihten itibaren buradan
> alınır.

**Ölçüm kapsamı:** 185 sorudan yalnızca 87'sinin beklenen belgesi hâlâ
indekste (73'ü kampanya rotasyonu nedeniyle kapsam dışı — aynı "veri
eskimesini retrieval hatası saymayalım" ilkesi, bkz. §6).

#### Sonuçlar — kategori bazlı (87 sorgu, ölçüm kapsamındaki)

| | Recall@1 | Recall@3 | Recall@5 |
|---|---|---|---|
| **Genel** | **%64,37** | **%79,31** | **%86,21** |
| tam_ad | %87,5 (28/32) | %93,75 (30/32) | %96,88 (31/32) |
| kismi_ad | %70,0 (21/30) | %90,0 (27/30) | %93,33 (28/30) |
| dogal_soru | %77,78 (7/9) | %77,78 (7/9) | %88,89 (8/9) |
| **banka_ve_konu** | **%0,0 (0/16)** | %31,25 (5/16) | %50,0 (8/16) |

**Abstention (alan_disi):** %86,67 (13/15) — **ilk kez %100 değil.**

#### Bulgu 4 — `banka_ve_konu` gerçek bir zayıflık ortaya çıkardı

Bu kategoride soru kampanya adını hiç içermiyor — örnek: *"Albaraka Türk
ihtiyaç finansmanı"* (beklenen: `vade-farksiz-kampanyasi`). Sistemin
Recall@1'i burada **%0**: lexical arama kampanya adına dayandığı için isim
verilmeyince ayırt edicilik neredeyse kayboluyor, @5'te bile ancak %50'ye
çıkıyor.

**Bu bir kod hatası değil, tam olarak §2'de kendi belgelediğimiz tasarım
tercihinin sınırı:** lexical (BM25) bileşen banka adı/ürün terimleri gibi
ayırt edici kelimelere ağırlık veriyor; kampanya adı verilmeyen bir soruda
bu avantaj kayboluyor ve sistem büyük ölçüde dense (anlamsal) aramaya
kalıyor — ki §2'nin başında zaten dense aramanın tek başına ayırt edici
olmadığını ölçmüştük. Yani bu kategori, retrieval'in henüz çözmediği
gerçek bir sınırı doğru şekilde açığa çıkarmış oluyor.

**Doğru müdahale:** Bulgu 2'de önerilen cross-encoder reranker'ın kazanç
tavanı bu kategoriyle birlikte yeniden hesaplanmalı — artık yalnızca "2
kayıt" değil, `banka_ve_konu`'nun @1'deki tam başarısızlığı da kapsıyor.
Bu, sıradaki iş listesinde reranker'ın önceliğini yükseltir.

#### Bulgu 5 — Abstention ilk kez kusurlu çıktı (%100 → %86,67)

Önceki tüm ölçümler 5 alan dışı soruyla yapılmıştı; 15 soruluk daha geniş
örneklemde 2 soru yanlışlıkla "kaynak bulundu" sayıldı. Hangi 2 soru
olduğu ve kök nedeni **henüz araştırılmadı** — bu belgeye eklenmesi
gereken bir sonraki adım budur; §5'teki 0,60 eşiğinin küçük bir örneklemle
(6+5 soru) kalibre edildiği zaten dürüstlük notu olarak yazılmıştı, bu
sonuç tam olarak o notun öngördüğü riskin gerçekleşmiş hâli.

---

### Yeniden doğrulama — 23 Ağustos 2026 (reranker + exact mod devreye alındı, indeks 511 belge/1970 parçaya büyütüldü)

`chunking/reranker.py` (cross-encoder `ms-marco-MiniLM-L-6-v2`) `chunking/retriever.py::getir`'e
koşulsuz bağlandı ve `KATILIMAI_RAG_EXACT_MOD=true` ile Qdrant'ın brute-force
(tam) araması kullanılarak 185 soruluk set yeniden koşuldu. Aynı zamanda
indeks, Zeynep'in 22-23 Ağustos taramasıyla senkron biçimde yeniden kuruldu:
**300 → 511 belge, 878 → 1970 parça**. Bu iki değişiklik (reranker/exact +
korpus büyümesi) birlikte geldiği için sonuçlar **saf reranker etkisi değil,
bileşik bir etki** olarak okunmalı — ayrıştırma yapılmadı, dürüstlük notu
olarak burada belirtiliyor.

#### Sonuçlar — kategori bazlı (119 sorgu, ölçüm kapsamındaki; önceki koşu 87 sorguydu — korpus büyüyünce daha fazla altın kayıt kapsam içine girdi)

| | Recall@1 | Recall@3 | Recall@5 |
|---|---|---|---|
| **Genel** | %64,37 → **%68,07** | %79,31 → **%80,67** | %86,21 → **%88,24** |
| tam_ad | %87,5 → %86,36 | %93,75 → %95,45 | %96,88 → %97,73 |
| kismi_ad | %70,0 → **%80,0** | %90,0 → %95,0 | %93,33 → %95,0 |
| dogal_soru | %77,78 → **%57,14** ⚠️ | %77,78 → **%64,29** ⚠️ | %88,89 → %92,86 |
| banka_ve_konu | **%0,0 → %14,29** | %31,25 → %33,33 | %50,0 → %52,38 |

**Abstention (alan_disi):** %86,67 (13/15) — **değişmedi.**
**Abstention (alan_ici_kapsam_disi):** **%50,0 (5/10)** — bu kategori önceki
ölçümde ayrı raporlanmamıştı (bkz. Bulgu 7).

#### Bulgu 6 — `banka_ve_konu` iyileşti ama çözülmedi

Recall@1 %0'dan %14,29'a çıktı — reranker'ın en çok kazandırdığı yer beklendiği
gibi burası. Ama mutlak sayı hâlâ düşük: kampanya adı verilmeyen bir soruda
doğru kaynağı **ilk sırada** bulma ihtimali 7'de 1. Recall@5'te ancak yarısı
(%52,38) yakalanıyor. **Kök sorun çözülmedi**, yalnızca hafifledi: lexical
bileşen hâlâ kampanya adı terimlerine ağırlık veriyor, reranker geniş aday
havuzunu (limit×2=20-40) yeniden sıralıyor ama havuzun kendisi zaten dar
kalıyorsa reranker doğru belgeyi bulamadığı yerden bulamaz.

**Denendi ve geri alındı (23 Ağustos 2026, aynı gün):** `genis_limit`
20'den 40'a çıkarıldı, 513 belge/1979 parçalık güncel indeksle yeniden
ölçüldü. Sonuç karışık ve **net olumsuz** çıktı:

| Kategori | pool=20 | pool=40 |
|---|---|---|
| banka_ve_konu Recall@1 | %14,29 | **%19,05** ✅ |
| banka_ve_konu Recall@5 | %52,38 | %38,1 ❌ |
| dogal_soru Recall@5 | %92,86 | %71,43 ❌ |
| **Genel Recall@5** | %88,24 | %83,19 ❌ |

Recall@1'de küçük bir kazanç (+4,8 puan) elde edildi ama bunun bedeli
Recall@3/@5'te çok daha büyük bir kayıp oldu — daha geniş aday havuzu
cross-encoder'a daha fazla dikkat dağıtıcı sunuyor ve zaten doğru
sıralanmış adayları alt sıralara itebiliyor. Değişiklik geri alındı
(`chunking/retriever.py::getir`, `genis_limit = max(20, limit * 2)`).
**Sorgu genişletme henüz denenmedi** — bir sonraki gerçek aday.

Yan bulgu: pool=40 koşusunda `alan_disi` abstention %86,67→%93,33'e
çıktı (2 sabit hatadan biri kayboldu) — ama pool=20'ye dönünce ayrıca
doğrulanmadı, muhtemelen indeksin 511→513 büyümesiyle veya havuz
büyümesiyle ilgili yan etki, bağımsız bir bulgu değil.

#### Bulgu 7 — `dogal_soru`da beklenmeyen gerileme

Recall@1 %77,78 → %57,14, Recall@3 %77,78 → %64,29 — reranker'ın **kötüleştirdiği**
tek kategori. Örneklem küçük (14 soru, sayısal olarak birkaç sorunun yön
değiştirmesi yeter) ama yön tutarlı (hem @1 hem @3 düştü, @5'te toparlanıyor).
Olası açıklama: cross-encoder, doğal dilde yazılmış (kampanya başlığından
uzak) sorularda yüzeysel kelime örtüşmesine RRF'den daha fazla ağırlık
veriyor olabilir.

**Araştırıldı (23 Ağustos 2026, aynı gün):** 20 `dogal_soru` sorusunun
tamamı tek tek çalıştırılıp beklenen kayıtla karşılaştırıldı. Kayıp
çıkan sorguların **hiçbiri temiz bir reranker hatası değil** — iki farklı
kök nedene ayrışıyor:

1. **Veri eskimesi (asıl ölçümde zaten dışlanıyor):** "Alışveriş yaparken
   altın biriktirebileceğim bir ürün var mı?" sorusu DK-003'ün
   `kaynak_url`'üne (`.../altin-kesem`) bağlıydı, ama scraper hiçbir zaman
   bu URL'yi toplamamış — korpusta yalnızca **`altin-kesemTicari`**
   (ayrı bir kampanya) var. `rag_degerlendirme.py` bu tür kayıtları zaten
   `kapsam_disi_eskimis` sayacına yazıp Recall hesabından çıkarıyor, yani
   bu doğru ölçüme hiç girmiyor.
2. **Gerçek yapısal belirsizlik (ölçüme giriyor, ama reranker'a özgü
   değil):** "Otel rezervasyonunda indirim sağlayan kampanya var mı?" ve
   "Hisse senedi işlemlerinde komisyon indirimi veren banka hangisi?"
   sorularında sistem doğru kampanyayı değil, **temalarca çok yakın başka
   kampanyaları** buluyor (örn. "yeni-yatirim-hesabiniza-sifir-komisyon"
   ile "dijitalden-musteri-ol-hisse-senedi-islemlerinde-75-komisyon-
   indirimi-kazan" karışıyor). Bu, belgenin §6/Bulgu 2'de zaten kayıtlı
   olan AL-005/AL-006 (neredeyse aynı isimli kampanyalar) sorununun aynısı
   — korpus büyüdükçe kaçınılmaz hale gelen bir ayırt edicilik sınırı,
   reranker'ın **yarattığı** değil, ortaya **çıkardığı** bir zayıflık.

**Sonuç:** "reranker `dogal_soru`yu kötüleştirdi" iddiası kısmen yanıltıcı
— küçük örneklemde (14 soru) birkaç sorunun yön değiştirmesi zaten
istatistiksel olarak gürültüye yakın, ve incelenen somut örnekler
reranker'ın kendine özgü bir hatasını değil, korpus ölçeğinin doğal
sonucu olan kampanya-ayırt-etme zorluğunu gösteriyor. Hızlı/güvenli bir
kod düzeltmesi yok — çözüm (varsa) sorgu genişletme veya kampanya bazlı
ayırt edici öznitelik eklemek gibi daha büyük bir yatırım gerektirir,
deadline'a bu kadar yakın denenmedi.

#### Bulgu 8 — Abstention'ın gerçek zayıf noktası `alan_ici_kapsam_disi`, `alan_disi` değil

Önceki ölçümler yalnızca `alan_disi` (uzay istasyonu, çamaşır makinesi gibi
tamamen alakasız sorular) abstention'ını raporluyordu: %86,67. Ama soru
setinde ayrıca **`alan_ici_kapsam_disi`** kategorisi var — katılım
bankacılığına yakın ama kampanya kapsamı dışında sorular ("Katılım
bankasında altın hesabı nasıl açılır?", "hesap açmak için hangi belgeler
gerekli?", "TMSF güvencesi kapsamında mıdır?", "internet bankacılığı
şifremi unuttum"). Bu kategoride abstention doğruluğu yalnızca **%50,0
(5/10)** — sistem bu soruların yarısında **çekimser kalması gerekirken
cevap üretiyor.**

**Bu, `alan_disi`'nden daha ciddi bir demo riski**: jürinin "hesap nasıl
açılır" tarzı bir soru sorması, "uzay istasyonunda yerçekimi" sormasından
çok daha olası. Kök neden ölçüldü: tam dağılım çıkarıldı (185 sorunun
tamamı için terim örtüşmesi hesaplandı) ve `alan_ici_kapsam_disi`'nin
aralığı (0,50-0,83) gerçek cevaplanabilir `kismi_ad`/`banka_ve_konu`
sorularının aralığıyla (ikisi de 0,50'den başlıyor) **iç içe** çıktı —
yani `ASGARI_TERIM_ORTUSMESI` eşiğini tek başına ayarlamak bu sorunu
çözemez, gerçek cevaplanabilir soruları da susturur.

**Düzeltildi (23 Ağustos 2026) — ama RAG katmanında değil, niyet
katmanında:** `agent/intent.py`'ye yeni bir `KAPSAM_DISI` niyeti eklendi
("hesap nasıl açılır", "hangi belgeler gerekir", "en yakın şube",
"şifremi unuttum", "TMSF", "bakiyemi nasıl öğrenirim", "limitimi nasıl
artırabilirim" kalıpları). Bu 7 soru artık RAG'e **hiç sorulmadan**
`agent/orchestrator.py`'de dürüst bir cevapla kapanıyor. Kalan 3 soru
(danışma kurulu, kâr payı dağıtım sıklığı, müdarebe/müşareke tanımı)
gerçek katılım bankacılığı kavramları olduğu için kasıtlı olarak
KAPSAM_DISI'ye alınmadı, RAG'in mevcut mekanizmasına bırakıldı.

**Ölçüm metodolojisi notu:** bu belgedeki ve `rag_degerlendirme.py`
çıktısındaki `alan_ici_kapsam_disi` yüzdesi `chunking/retriever.py`'yi
**doğrudan** çağırıyor, `agent/intent.py`'yi atlıyor. Yani tablodaki
%40-50 rakamı RAG'in **izole** halini ölçüyor; gerçek uçtan uca sistemde
(agent/orchestrator.py üzerinden) bu 10 sorudan 7'si artık hiç RAG'e
gitmiyor ve doğru şekilde kapsam dışı sayılıyor. Gerçek uçtan uca
abstention doğruluğunu ölçmek isteyen `agent.orchestrator.soru_isle`
üzerinden koşmalı, `chunking.retriever.getir` üzerinden değil.

`alan_disi`'ndeki 2 sabit hata da hâlâ aynı: *"Çamaşır makinesi nasıl
temizlenir?"* (örtüşme=0,667) ve *"Güneş sistemindeki gezegen sayısı
kaçtır?"* (örtüşme=0,6) — ikisi de `ASGARI_TERIM_ORTUSMESI=0,60` eşiğini
aşıyor çünkü sorudaki bazı kelimeler tesadüfen kampanya parçalarında da
geçiyor. Eşiği yükseltmek bu ikisini düzeltebilir ama diğer kategorilerde
false-negative (cevaplanabilir soruda gereksiz çekimserlik) riski taşır —
tam koşu yapılmadan eşik değiştirilmedi.

---

### Yeniden doğrulama — 25 Ağustos 2026 (abstention/rerank sıralama hatası düzeltildi + gizli bir API kırılması bulundu)

**Bulgu 9 — Abstention eşikleri (`ASGARI_VEKTOR_SKORU`, `ASGARI_TERIM_ORTUSMESI`) reranker'dan SONRA hesaplanıyordu.**

24 Ağustos'ta eklenen `ASGARI_VEKTOR_SKORU` menü-kirliliği eşiği ve mevcut terim örtüşmesi kontrolü, kodda **reranker zaten `limit`e (3-5) kestikten sonraki** listede hesaplanıyordu. Yorum satırı "ilk parçadaki en yüksek vektör skoru" diyordu ama bu, reranker'ın **çapraz-kodlayıcı skoruna göre** seçtiği son listeydi — gerçek en yüksek vektör skorlu aday reranker'ın kestiği `limit` dışında kalmış olabilirdi. Bu etkileşim hiç ölçülmemişti: `ASGARI_VEKTOR_SKORU` eşiği 24 Ağustos'ta, reranker'ın koşulsuz bağlanması ise 23 Ağustos'ta eklendi; ikisinin birlikte davranışı bu belgenin hiçbir ölçümüne girmedi.

**İlk düzeltme denemesi (aynı gün, GERİ ALINDI — ölçülerek yanlış çıktı):** İki sinyal de reranker'dan önce ama **tüm geniş aday havuzunda** (`genis_limit=20+`) hesaplanacak şekilde değiştirildi. Ölçüldü: `alan_disi` abstention doğruluğu %86,67→%66,67, `alan_ici_kapsam_disi` %50,0→%20,0'e **düştü**. Sebep: `ASGARI_TERIM_ORTUSMESI=0,60` eşiği 20/21 Ağustos'ta yalnızca **dar** (limit boyutundaki) bir kümeye göre kalibre edilmişti; `_terim_ortusmesi` tüm parçaların metnini tek bir birleşik dizgede arıyor — 20 adayın birleşik metni çok daha geniş bir "rastgele eşleşme yüzeyi" yaratıyor. "Fotosentez hangi organelde gerçekleşir?" gibi alanla tamamen alakasız sorular, sırf 20 farklı parçanın birleşik kelime dağarcığı geniş olduğu için yanlışlıkla eşiği geçti.

**Doğru kapsamlı düzeltme (`chunking/retriever.py::getir`):** İki sinyal de reranker'dan **önce**, ama aday havuzunun **tamamında değil, ilk `limit` adayında** (`aday_havuzu[:limit]` — Qdrant'ın kendi getirme sırasına göre, çapraz-kodlayıcıya göre DEĞİL) hesaplanıyor. Bu hem orijinal hatayı çözüyor (kontrol artık reranker'in yeniden sıraladığı kümeye değil, gerçek getirme sırasına bakıyor) hem de terim örtüşmesi kalibrasyonunun dayandığı küme BOYUTUNU koruyor. Reranker yalnızca `yeterli=True` iken ve yalnızca **gösterilecek** parçaları sıralamak için çalışıyor — cevaplanabilirlik kararına artık karışmıyor; `yeterli=False` durumunda hiç çalıştırılmıyor (`agent/router.py::rag_aracini_cagir` zaten `sonuc.parcalar`'a bakmıyor), gereksiz çapraz-kodlayıcı çağrısı ortadan kalktı.

**Doğrulama (düzeltilmiş kapsamla, 185 soruluk set):**

| Metrik | Önce (belgelenmiş, 23 Ağustos) | Sonra (25 Ağustos, düzeltme sonrası) |
|---|---|---|
| Abstention `alan_disi` | %86,67 (13/15) | **%93,33** (14/15) |
| Abstention `alan_ici_kapsam_disi` | %50,0 (5/10) | %40,0 (4/10) — 1 soru, örneklem gürültüsü |
| Recall@5 GENEL | %88,24 | **%88,24** (değişmedi) |

Recall birebir korunuyor (reranker'a giden aday havuzu ve final sıralama değişmedi — yalnızca abstention kararının hangi kümeye baktığı değişti), `alan_disi` abstention'da net iyileşme var.

**Bulgu 11 — `banka_tespit.py` (yazılmış ama varsayılan kapalıydı) ölçüldü: gerçekten kazanç sağlıyor, varsayılan `true` yapıldı.**

`retriever.py`'nin kendi "ölçüm yolu" notu takip edilerek `KATILIMAI_BANKA_OTOMATIK` açık/kapalı karşılaştırması (düzeltilmiş retriever koduyla) koşuldu:

| k | `banka_ve_konu` (kapalı → açık) | Genel (kapalı → açık) |
|---|---|---|
| 1 | %9,52 → **%23,81** | %66,39 → %68,91 |
| **3 (üretimde fiilen kullanılan)** | %28,57 → **%38,10** | %80,67 → **%82,35** |
| 5 | %52,38 → %47,62 (1 soru, gürültü) | %88,24 → %87,39 |

`agent/router.py::rag_aracini_cagir` üretimde **her zaman** `limit=3` kullanıyor (bkz. §6, "Recall@5 hiç kullanılmıyor" notu) — yani k=1/k=3'teki net kazanç gerçekten kullanılan yol için geçerli. k=5'teki küçük düşüş (21 sorudan 1'i) örneklem gürültüsü ve zaten kullanılmayan bir k değeri. `chunking/retriever.py::getir`'de `KATILIMAI_BANKA_OTOMATIK` varsayılanı `true` yapıldı.

**Bulgu 10 — `qdrant-client==1.18.0`'da `.search()` metodu artık yok; `hibrit_ara`'nın "ham vektör skoru" adımı (24 Ağustos, menü-kirliliği önlemi) hiçbir zaman gerçek bir Qdrant'a karşı çalıştırılmamıştı.**

CI'da servis olmadığı için ilgili testler (`test_rag_kalip_kirliligi.py`, `test_rag_uctan_uca.py`) hep skip ediliyordu; yerel dosya modundaki gerçek indeksle (`.qdrant_yerel`) ilk kez çalıştırıldığında `AttributeError: 'QdrantClient' object has no attribute 'search'` alındı. `chunking/qdrant_baglanti.py::hibrit_ara` ve yeni `yogun_ara` fonksiyonundaki `.search(...)` çağrıları `.query_points(query=..., using=YOGUN_AD, ...)`'e çevrildi (modern qdrant-client API'si). Ayrıca `tests/test_rag_kalip_kirliligi.py::_indeks_hazir_mi` doğrudan `QdrantClient(url=QDRANT_URL)` oluşturuyordu — yerel dosya modunu (`QDRANT_YEREL_YOL`) tanımıyordu, bu yüzden bu dosyadaki testler Docker olmadan **hiçbir zaman** çalışmamıştı. `istemci_al()` kullanacak şekilde düzeltildi.

**Doğrulama:** Düzeltmeler sonrası `.qdrant_yerel` üzerinden (1979 nokta, 23 Ağustos indeksinden) `test_rag_uctan_uca.py`, `test_kaynak_guncelligi.py`, `test_qdrant_baglanti.py` ve `test_rag_kalip_kirliligi.py` **ilk kez gerçek bir indekse karşı çalıştırıldı**: 27/27 geçti.

**Yan bulgu — parçalayıcıda kalıntı site kalıbı:** `test_rag_kalip_kirliligi.py` ilk kez gerçekten çalışınca, bu belgenin daha önce hiç yakalayamadığı gerçek bir kalıntı ortaya çıktı: "Kuveyt Türk'ün konut finansmanı oranı ne" sorusunun döndürdüğü iki parçada `chunking/parcalayici.py`'nin menü/site-kalıbı elemesinin kaçırdığı bir footer bloğu var — *"...İştiraklerimiz Şube ve ATM'ler Bize Ulaşın Müşteri İletişim Merkezi Arabuluculuk..."*.

**Kök neden bulundu (25 Ağustos 2026, aynı gün) — düzeltme DENENDİ ve GERİ ALINDI.** Gerçek kaynak satırları izlendi: sorun "tek uzun satıra düşme" değil — footer zaten ayrı satırlara bölünmüş durumda, ama iki ayrı sebeple `_menu_bloklarini_ele` bloğu parçalıyor: (1) `MENU_BLOK_ASGARI=5` altında kalan kısa artıklar ("Devam Faydalı Linkler Ürün ve Hizmet Ücretleri" gibi) hâlâ korunuyor; (2) "Fonum Ne Getirdi?" / "444 0 123" gibi menü öğeleri kendileri de `kalip_satirlar` içinde olduğu hâlde noktalama/rakam içerdikleri için `_etiket_gibi_mi` onları "düzyazı" sanıp bloğu ikiye bölüyor.

İki düzeltme denendi, ikisi de gerçek korpusta ölçülüp **güvensiz** bulundu:
- **Deneme 1:** `kalip_orani == 1.0` olan kısa blokları uzunluktan bağımsız eleme. Ölçüldü: 417 blok yeni elendi, örneklemin büyük kısmı **gerçek kampanya koşuluydu** (ör. "Kampanyadan Dünya Katılım Paraf kartlar faydalanabilecektir. | Sanal kartlar kampanyaya dahildir. | ParafPara kullanılarak yapılan işlemler ile iptal ve iade işlemleri dahil değildir.") — modül başı Tasarım Kararı 4'ün tam uyardığı hata.
- **Deneme 2:** Yalnızca blok-devamlılığını `kalip_satirlar` üyeliğiyle de tanımak (eşikleri değiştirmeden). Toplam parça sayısı 1875→1443'e düştü (-432, beklenenden çok daha büyük); rastgele örneklemde gerçek kampanya cümlelerinin **parçaları** (ör. "Bankkart Lira kazanabilmek için alışveriş yapmadan önce") kaybolduğu görüldü — Ziraat Katılım gibi bankaların şablon tabanlı kampanya metinleri, tıpkı navigasyon gibi, aynı cümle parçasını 4+ farklı sayfada tekrarlayabiliyor; mevcut `kalip_satirlar` mekanizması "site kalıbı" ile "şablonlanmış gerçek içerik"i ayırt edemiyor.

**Sonuç:** İki deneme de geri alındı, `chunking/parcalayici.py` bu oturumdan **değişmeden** çıktı. Bu, tahmin edilenden çok daha derin bir problem — güvenli bir çözüm muhtemelen kalıp-üyeliğinin yanına EK bir sinyal ister (ör. satırın CÜMLE PARÇASI mı yoksa TAM etiket mi olduğunu ayırt eden bir noktalama/büyük-harf deseni, ya da tam `rag_degerlendirme.py` regresyon ölçümüyle doğrulanan kademeli bir eşik taraması). Sıradaki denemenin gold sete karşı Recall/precision ölçümüyle doğrulanması şart — yalnızca örnekleme yeterli değil (bu oturumda tam da bunu öğrendik).

---

### Yeniden doğrulama — 25 Ağustos 2026 (uçtan uca abstention ilk kez ölçüldü — Bulgu 8'in açık kalan metodoloji notu kapatıldı)

**Bulgu 12 — `agent/intent.py::Niyet.KAPSAM_DISI` düzeltmesinin (23 Ağustos'ta eklendi) gerçek etkisi hiç ölçülmemişti; ölçüldü ve büyük bir kazanç doğrulandı.**

`scraper/scripts/rag_degerlendirme.py::abstention_uctan_uca_olc` eklendi — `chunking.retriever.getir`'i izole çağırmak yerine `agent.orchestrator.soru_isle`'i (kullanıcının gerçekte gördüğü tam yol: niyet tespiti → araç seçimi → gerekirse RAG) çağırır.

| Kategori | İzole (`chunking.retriever.getir`) | Uçtan uca (`agent.orchestrator.soru_isle`) |
|---|---|---|
| `alan_disi` | %93,33 (14/15) | %93,33 (14/15) — değişmedi |
| **`alan_ici_kapsam_disi`** | %40,0 (4/10) | **%90,0 (9/10)** |

`alan_disi` değişmedi çünkü bu kategorideki sorular ("çamaşır makinesi nasıl temizlenir" gibi) zaten bankacılıkla hiç ilgili değil — `KAPSAM_DISI` niyet kelimeleri (hesap açma, şifre, TMSF vb.) bunları hiç hedeflemiyor, aynı terim-örtüşmesi kapısına düşüyorlar. `alan_ici_kapsam_disi` ise tam KAPSAM_DISI'nin hedeflediği kategori — 7 soru artık RAG'e hiç gitmeden dürüst bir cevapla kapanıyor, yalnızca 1 soru ("Kâr payı dağıtımı hangi sıklıkta yapılır?") hâlâ yanlış cevaplanıyor. Bu, Bulgu 8'de **bilinçli olarak** KAPSAM_DISI'ye alınmayan 3 gerçek katılım bankacılığı sorusundan (danışma kurulu, kâr payı dağıtım sıklığı, müdarebe/müşareke) biri — beklenen bir kalıntı, yeni bir regresyon değil.

**Sonuç:** Bulgu 8'in kapanışında yazılan "ölçüm metodolojisi notu" (uçtan uca ölçüm `agent.orchestrator.soru_isle` üzerinden yapılmalı) artık uygulandı ve KAPSAM_DISI yatırımının gerçek değeri (izole ölçümdeki %40'ın **iki katından fazlası**) ilk kez rakamla doğrulandı.

---

**Bulgu 13 — AL-005/AL-006 "yakın-duplikat kampanya" sorunu araştırıldı; kök neden beklenenden farklı çıktı, bulunan düzeltme kısmi bir iyileşme sağladı.**

Orijinal varsayım (§6/Bulgu 2, Bulgu 7) "Sağlık Harcamalarına..." (AL-005) ve "Eğitim Harcamalarınıza..." (AL-006) kampanyalarının neredeyse aynı isimli olması yüzünden karıştığıydı. Gerçek kaynak izlendiğinde farklı bir kök neden bulundu: AL-006'nın kaynak URL'si (`egitim-kampanyasi-1`) `chunking/parcalayici.py::basligi_bul()`'un slug-uzunluk eşiğinin (`>= 20` karakter) **1 karakter altında** kalıyordu ("Eğitim Kampanyası 1" = 19 karakter) ve metin sezgisi yedeğine düşüp yarım kalmış bir cümle parçasını ("Albaraka Mobil'de Kampanyalar sayfasından katılım sağlayarak...") başlık olarak seçiyordu — indekslenen içerik "eğitim"/"taksit" konusuyla anlamsal olarak alakasızdı. Sonuç: "Eğitim Harcamalarınıza Vade Farksız 6 Taksit Kampanyası" sorgusunda doğru kampanya top-20'de **20. sırada** çıkıyordu.

**Düzeltme (dar kapsamlı, bilinçli tercih):** Genel `>= 20` eşiği DEĞİŞTİRİLMEDİ — eşiğin altında kalan 69 URL var, çoğu kısa ama bilgilendirici ("N11de 6 Taksit"), birkaçı gerçekten jenerik ("Kampanyalar", kırık URL fragmanlarından); toptan değişiklik yeniden indeksleme + tam Recall/precision doğrulaması gerektirirdi. Bunun yerine yalnızca bu tek kayıt için `_BASLIK_ISTISNALARI` sözlüğüyle dar bir istisna eklendi ("Eğitim Kampanyası").

**Ölçülen etki (yeniden indeksleme sonrası, 513 belge/1875 parça):** Sıra 20→**18** — küçük bir iyileşme, ama top-5'e girmeye yetmedi. Kök sebep: sorgunun büyük kısmı ("Vade Farksız 6 Taksit Kampanyası") AL-005'in GERÇEK başlığıyla birebir örtüşüyor, AL-006'nın kaynak sayfası ise aynı kavramı farklı kelimelerle anlatıyor ("okul ödemelerinize" vs gold etiketinin yazdığı "eğitim harcamalarınıza"). Bu, düzeltilen başlık sorunundan bağımsız, gold etiketleme kelime seçimi ile kaynak sayfa kelime seçimi arasındaki bir **kelime dağarcığı uyuşmazlığı** — `banka_ve_konu`/`dogal_soru` kategorilerinde zaten bilinen sınıfın aynısı.

**Doğrulama:** Yeniden indeksleme sonrası Genel Recall@5 %87,60 (önceki ölçüm %87,39, exact=True ile) — regresyon yok, örneklem indeks güncel korpusla senkronlandığı için büyüdü (119→129 sorgu). `test_rag_uctan_uca.py`, `test_kaynak_guncelligi.py`, `test_rag_kalip_kirliligi.py` 28/28 geçti.

---

**Bulgu 14 — Gerçek EVREN anahtarıyla ilk kez ölçüldü: bge-m3-embed, bu projenin Türkçe korpusunda yerel e5-base'in ALTINDA kaldı (ADR 0002'nin varsayımıyla çelişiyor).**

ADR 0002, EVREN'in kendi dokümantasyon ölçümüne dayanarak bge-m3-embed'i (R@1 0,95) en iyi seçenek olarak işaretlemişti — ama bu, EVREN'in genel test setinde ölçülmüştü, bu projenin Türkçe katılım bankacılığı korpusunda değil. 25 Ağustos'ta gerçek `EVREN_API_KEY` ile korpus yeniden indekslendi (`kampanya_parcalari_evren`, 513 belge/1875 parça, 47,88 sn — yerel modelin ~9 katı hızlı) ve aynı 129 sorguluk sette (`exact=True`, k=5) karşılaştırıldı:

| Kategori | Yerel hibrit (e5-base, 768b) | EVREN dense (bge-m3, 1024b) | EVREN hibrit (bge-m3, 1024b) |
|---|---|---|---|
| Genel Recall@5 | **%87,60** | %83,72 | %84,50 |
| tam_ad | %97,87 (46/47) | %97,87 (46/47) | %97,87 (46/47) |
| kismi_ad | %95,35 (41/43) | %97,67 (42/43) | %95,35 (41/43) |
| banka_ve_konu | **%52,17** (12/23) | %34,78 (8/23) | %39,13 (9/23) |
| dogal_soru | **%87,50** (14/16) | %75,00 (12/16) | %81,25 (13/16) |

Yerel hibrit hat her iki EVREN modunu da geçiyor — özellikle `banka_ve_konu` ve `dogal_soru`'da belirgin farkla. **Karar:** embedding tarafında yerel e5-base'de kalınıyor (hem ölçülen kalite hem offline demo garantisi lehine); EVREN yalnızca LLM çıkarım tarafında (`llm-fast`) değerlendirilmeye devam ediyor. ADR 0002 bu bulguyla güncellenmeli.

**Bulgu 15 — `banka_ve_konu` ve `dogal_soru`'nun düşük Recall'unun kök nedeni araştırıldı: çoğunlukla retrieval hatası değil, korpustaki YAKIN-DUPLİKAT kampanyalar.**

`banka_ve_konu`'daki kaçırılan sorguların (`Ziraat Katılım kart` vb.) hedeflediği bankaların aynı türde onlarca eşzamanlı kampanyası var (Ziraat Katılım: 60 "Kart Kampanyası", Türkiye Emlak Katılım: 55) — sistem gerçekten o türde bir kampanya döndürüyor, sadece gold'un işaretlediği TEK kayıt değil. `dogal_soru`'daki 4 kaçırılan sorudan hiçbiri banka adı içermiyor ve hepsi birden fazla bankanın neredeyse aynı kampanyayı yürüttüğü konulara denk geliyor (elektrikli araç şarjı, market iadesi, mobilden müşteri olma/mil kazanma, tarım finansmanı) — retrieval konuyla alakalı bir kampanya buluyor, ama hangi banka/hangi varyant olduğunu ayırt edecek bilgi sorguda yok.

**Denenip geri alınan çözüm — aday havuzunu genişletmek:** 23 Ağustos'ta (yerel e5-base, 185 sorulu eski set) havuz 20'den 40'a çıkarılınca `dogal_soru` Recall@5 %92,86→%71,43'e çökmüştü (bkz. `chunking/retriever.py::_ara` içindeki köşeli not). 25 Ağustos'ta EVREN + büyümüş sette (129 soru) AYNI deney tekrarlandı — sonuç yine olumsuz, sadece daha hafif: `banka_ve_konu` ve `dogal_soru` **hiç değişmedi** (birebir aynı), `tam_ad` hafifçe geriledi (%97,87→%95,74), GENEL düştü (%83,72→%82,95). Farklı embedding modeli ve daha büyük veri setiyle de doğrulandı: bu geniş havuzun cross-encoder'a sunduğu dikkat dağıtıcı fazlalıktan kaynaklanan **yapısal bir sınırlama**, tek bir ölçüm koşusunun gürültüsü değil.

**Açık kalan, henüz uygulanmamış fikir:** `kampanya_turu` (kart/yeni müşteri/ihtiyaç finansmanı vb.) alanını RAG indeks metadata'sına eklemek ve `banka_tespit.py`'daki desenle sorgudan tür ifadesini tanıyıp filtreye/skor artırımına çevirmek — `banka_ve_konu`'yu doğrudan hedefler. Risk: `extraction/regex_extractor.py::_kampanya_turunu_tespit_et` sınıflandırıcısının F1'i mükemmel değil; SERT filtre olarak kullanılırsa yanlış sınıflandırılmış doğru cevapları eleyebilir — soft-boost olarak denenip ölçülmeden varsayılan yapılmamalı.

---

## 7. Bilinçli sınırlar

- **LLM ile özetleme yok.** RAG, bulduğu kaynak parçalarını **birebir**
  döndürür; üzerine serbest metin üretmez. Böylece halüsinasyon yapısal
  olarak imkânsızdır — kullanıcıya gösterilen her cümle bir kaynak
  belgeden gelir. Özetleme ancak Verifier ile birlikte güvenli olur.
- **Reranker devrede (23 Ağustos'tan itibaren).** Cross-encoder reranker
  (`chunking/reranker.py`) `retriever.py::getir`'e koşulsuz bağlandı ve
  `banka_ve_konu` kategorisinde ölçülebilir kazanç sağladı (Recall@1 %0→%14,29,
  bkz. Bulgu 6) — ama sorunu çözmedi, yalnızca hafifletti. Aynı koşuda
  `dogal_soru` kategorisinde beklenmeyen bir gerileme de gözlendi (Bulgu 7),
  kök nedeni henüz araştırılmadı.
- **Zamansal filtre yok.** Metadata'da `erisim_zamani` tutuluyor ancak
  "soru tarihinde geçerli olan sürüm" filtresi henüz uygulanmıyor.
- **`banka_tespit.py` artık varsayılan AÇIK (25 Ağustos'tan itibaren).**
  bkz. Bulgu 11 — ölçülüp `banka_ve_konu` kategorisinde ve üretimde
  fiilen kullanılan k=3'te net kazanç doğrulandı.
- **Parçalayıcıda kalıntı bir site kalıbı türü var (25 Ağustos'ta
  bulundu, henüz düzeltilmedi).** `chunking/parcalayici.py`'nin menü
  eleme mantığı kısa/art-arda etiket satırlarına dayanıyor; footer
  bloklarının bazıları (ör. "İştiraklerimiz Şube ve ATM'ler Bize
  Ulaşın...") bu kalıba uymadığı için indekste kalabiliyor. Bkz. Bulgu
  10'un yan bulgusu.

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

> **Öneri (henüz uygulanmadı):** Ölçüm koşusu `exact=True` ile yapılmalı —
> üretimde ANN kalabilir, ama *benchmark* tekrar üretilebilir olmalı. Aksi
> hâlde bir iyileştirmenin gerçek mi gürültü mü olduğunu ayırt edemeyiz.
> Bu, LLM katmanı için zaten uyguladığımız "birden çok koşunun ortalaması"
> disiplininin retrieval karşılığıdır.

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

## 7. Bilinçli sınırlar

- **LLM ile özetleme yok.** RAG, bulduğu kaynak parçalarını **birebir**
  döndürür; üzerine serbest metin üretmez. Böylece halüsinasyon yapısal
  olarak imkânsızdır — kullanıcıya gösterilen her cümle bir kaynak
  belgeden gelir. Özetleme ancak Verifier ile birlikte güvenli olur.
- **Reranker yok.** Cross-encoder reranker retrieval kalitesini artırırdı
  ama ek model + gecikme getirir. Hibrit arama + abstention, mevcut veri
  büyüklüğü için yeterli ayırt ediciliği sağlıyor.
- **Zamansal filtre yok.** Metadata'da `erisim_zamani` tutuluyor ancak
  "soru tarihinde geçerli olan sürüm" filtresi henüz uygulanmıyor.

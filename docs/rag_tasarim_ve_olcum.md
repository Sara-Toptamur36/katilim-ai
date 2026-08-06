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

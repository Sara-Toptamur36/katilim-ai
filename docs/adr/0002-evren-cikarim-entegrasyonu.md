# ADR 0002 — EVREN çıkarım altyapısı entegrasyonu

Tarih: 24 Ağustos 2026
Durum: Kabul edildi
İlgili: `docs/PROJE_TANITIMI.md` (Mimari, `extraction/` ve `chunking/`), EVREN Katılımcı Dokümantasyonu (SSB EVREN, evren-teknofest.ssyz.org.tr, üretim tarihi 21.08.2026)

## Bağlam

TEKNOFEST 2026 Yapay Zekâ Dil Ajanları yarışması, katılımcı takımlara ortak kullanılan bir çıkarım altyapısı (EVREN) sağlıyor: on model alias'ı (metin/görüntü/video LLM'leri, gömme, yeniden sıralama), takım başına izole bir Qdrant örneği ve OpenAI uyumlu bir API. Proje şu ana kadar tamamen yerel çalışıyordu: çıkarım için Ollama (qwen2.5:7b), gömme için yerel `sentence-transformers` (`intfloat/multilingual-e5-base`, 768 boyut), arama için kendi barındırılan Qdrant.

Dokümantasyon, on model alias'ının her biri için gerçek ölçüm sonuçları veriyor (gecikme, doğruluk, getirme kalitesi) — "hangi model daha iyi" sorusunun cevabı senaryoya göre değişiyor ve bazı öneriler sezgiye aykırı (ör. yeniden sıralama getirme kalitesini düşürüyor).

## Karar

**Kullanılacak sistemler:**

1. **`llm-fast`** — `extraction/llm_extractor.py`'nin çıkarım motoru (Ollama'nın EVREN karşılığı).
   - Dokümantasyon Senaryo 2 (katılım bankacılığı finansal metin analizi) için doğrudan bunu öneriyor: "çıkarım işlemleri için, şema kısıtlı çıktı yapılandırmasıyla birlikte llm-fast önerilmektedir."
   - Ölçüm: JSON üretimi ve araç çağırmada `llm-large` ile fark YOK (5/5 görev, ikisi de 1,000). Projenin çıkarım görevi tam olarak bu kategori — yapılandırılmış JSON üretimi, kültürel/tarihsel bilgi değil.
   - `llm-fast` medyan gecikmesi 0,91 sn (16 eşzamanlı istekte 771,7 tok/s) — paylaşımlı, kotasız bir sistemde daha hafif tüketici olmak (§12 Kota politikası) hem takım hem diğer takımlar için avantaj.

2. **`bge-m3-embed`** — `chunking/embedding.py`'nin gömme modeli (yerel e5-base'in EVREN karşılığı).
   - Dokümantasyon Senaryo 2 için "terim ve madde bazlı getirme işlemleri için bge-m3-embed önerilmektedir" diyor.
   - Ölçüm (40 pasaj · 20 çeldirici · 20 sorgu): bu modelde R@1 = 0,95, sistemdeki EN YÜKSEK değer.
   - Projenin RAG'i **extractive** — LLM üretmiyor, doğrudan kaynak parçayı döndürüyor (`agent/router.py::rag_aracini_cagir`, "LLM KULLANILMIYOR" notu). Bu tasarımda ilk sonucun doğru olması (R@1) üçüncü sıradaki bir sonuçtan (R@3) daha kritik — alternatif `embed` (Qwen3, 2560 boyut) R@3'te iyi (1,00) ama R@1'de daha zayıf (0,90).

**Kullanılmayacak sistemler (gerekçeli):**

- **Hibrit (yoğun+seyrek) füzyon ve `rerank`** — dokümantasyonun kendi ölçümünde ikisi de saf yoğun getirmenin ALTINDA: hibrit 0,85, rerank 0,55 (saf yoğun 0,95'e karşı). Proje zaten `chunking/seyrek_vektor.py` + `reranker.py` ile hibrit bir hat kurmuş durumda — bu hat yerel e5-base vektörüyle geçerliliğini koruyor (ayrı ölçülmedi, EVREN'in bulgusu doğrudan aktarılamaz), ama EVREN'in `bge-m3-embed` vektörüyle bu adımlar varsayılan olarak devreye SOKULMUYOR. Takım kendi gold setiyle ayrıca ölçmek isterse `chunking/qdrant_baglanti.py::hibrit_ara` zaten mevcut.
- **`llm-large`** — çıkarım için gereksiz (yukarıda), video/kültürel-bilgi kullanım alanları projede yok.
- **`vlm`** — proje video işlemiyor.
- **`router` / `guard` model alias'ları** — `agent/router.py` zaten tamamen kural/bulanık-eşleştirme tabanlı, hiçbir LLM çağırmıyor (bu, dokümantasyonun "sınıflandırma/yönlendirme görevlerinde büyük model gereksiz" bulgusunu maliyetsiz şekilde zaten sağlıyor). İçerik güvenliği sınıflandırması kapsam dışı.
- **Akıl yürütme (thinking) modu** — hiç açılmıyor. `enable_thinking` parametresi `evren_istemci.py`'de hiç gönderilmiyor. Dokümantasyon SS3.2: açılması `llm-fast`'te 9 kat token karşılığı +0,04, `llm-large`'da 17 kat token karşılığı −0,32 puan getiriyor; ayrıca düşük `max_tokens` ile sessizce boş yanıt riski taşıyor (SS Tehlike kutusu).
- **EVREN'in Qdrant'ı** — projenin kendi Qdrant altyapısı (hibrit koleksiyon, Alembic migration'ları, yerel dosya modu jüri makinesi için) zaten olgun ve tam kontrollü. EVREN tarafında ölçülmüş bir performans avantajı yok; ek bir canlı bağımlılık eklemekten başka kazanç sağlamıyor. Adresler `.env.ornek`'te dokümante edildi ama varsayılan değil.
- **Aritmetik hesaplamalar modele bırakılmıyor** — zaten `calculator/calculator.py` ile koddan yapılıyordu (bu proje kararı EVREN entegrasyonundan ÖNCE alınmıştı). Dokümantasyon SS3.3 aynı sonucu ölçümle doğruluyor (TR-MMLU matematik: llm-fast %32,0, llm-large %36,0) — mevcut tasarım zaten doğruydu, değişiklik gerekmedi.

## Kurulum yaklaşımı: sessiz/opsiyonel geçiş

`EVREN_API_KEY` tanımlı DEĞİLSE hiçbir davranış değişmez — sistem yerel Ollama + yerel `sentence-transformers` ile çalışmaya devam eder. Bu, `docs/PROJE_TANITIMI.md` §8'de belirtilen "tamamen yerel çalışıyor, internet gerekmiyor" özelliğini korur ve `requirements.txt`'in üstündeki "tümü açık kaynak, ücretli/kapalı kaynak servis YOK" ilkesiyle çelişmez: `openai` istemci kütüphanesinin kendisi açık kaynak (Apache-2.0), EVREN ise yarışma tarafından resmî olarak sağlanan altyapı — üçüncü taraf ücretli bir servis değil.

`EVREN_API_KEY` tanımlıysa `extraction/llm_extractor.py` ve `chunking/embedding.py` OTOMATİK EVREN yoluna geçer — `donanim.py`'nin GPU/CPU profilini otomatik seçmesiyle aynı mantık: makul bir varsayılan var, ortam değişkeniyle geçersiz kılınabilir.

**Bilinçli olarak YAPILMAYAN bir şey:** EVREN aktifken bir çağrı başarısız olursa (ağ/anahtar hatası) sistem yerel modele SESSİZCE düşmüyor — hem `extraction/llm_extractor.py::llm_ile_sor` hem `chunking/embedding.py::_vektore_cevir` bu durumda `None`/hata döndürüyor. Gerekçe iki katmanlı:

1. **Gömme için zorunlu:** `bge-m3-embed` 1024, yerel `e5-base` 768 boyutlu vektör üretiyor. Aynı Qdrant koleksiyonuna karışık boyutta vektör yazmak indeksi bozar — bu "belge bulunamadı" gibi sessiz bir RAG başarısızlığına dönüşürdü (`docs/PROJE_TANITIMI.md` §5.6'nın tam uyardığı hata türü).
2. **Çıkarım için ölçüm bütünlüğü:** Bir batch çalıştırmasında bazı kayıtların EVREN'in `llm-fast`'i, bazılarının yerel `qwen2.5`'i tarafından işlenmesi, hangi modelin hangi sonucu ürettiğini belirsizleştirirdi — projenin kendi yeniden üretilebilirlik disiplinine (`gold_dataset/`, ablation raporları) aykırı.

## Sonuç

- Yeni `evren_istemci.py` modülü (repo kökü, `donanim.py` ile aynı seviyede) bağlantı/hazırlık/model-alias mantığını tek yerde topluyor.
- `extraction/llm_extractor.py`: `EVREN_API_KEY` varsa `llm-fast`'e şema kısıtlı JSON (`response_format=json_schema, strict=True`) ile gidiyor; yoksa mevcut Ollama yolu değişmeden çalışıyor.
- `chunking/embedding.py`: `EVREN_API_KEY` varsa `bge-m3-embed`'e gidiyor (`VEKTOR_BOYUTU` otomatik 1024 oluyor); yoksa mevcut yerel `e5-base` yolu değişmeden çalışıyor.
- `.env.ornek`: EVREN değişkenleri dokümante edildi, varsayılan boş (opsiyonel).
- `requirements.txt`: `openai==2.15.0` eklendi, yalnızca `EVREN_API_KEY` tanımlıysa devreye giriyor.
- Mevcut 299 testin hiçbiri etkilenmiyor — CI'da `EVREN_API_KEY` tanımlı olmadığından tüm testler eskisi gibi yerel Ollama/e5-base yoluna göre çalışmaya devam ediyor (bkz. `tests/test_evren_istemci.py`, yalnızca pasif-durum davranışını doğruluyor, ağ çağrısı yapmıyor).

## Güncelleme (24 Ağustos 2026, gerçek anahtar öncesi hazırlık) — hata analizi ve düzeltmeler

Gerçek `EVREN_API_KEY` ile bağlantı doğrulamasından önce yapılan bir hazırlık taramasında dört ek boşluk tespit edildi ve kapatıldı:

1. **`.env` hiçbir yerde process ortamına yüklenmiyordu** — depoda `python-dotenv` yoktu, `.env.ornek`'in "bu dosyayı `.env` olarak kopyalayıp düzenleyin" talimatı hiçbir kodla desteklenmiyordu. `EVREN_API_KEY` dâhil hiçbir `.env` değeri gerçekte etkili olmuyordu. Çözüm: `ortam_yukle.py` (yeni modül) + her giriş noktasının (`api/main.py`, `tests/conftest.py` [yeni], `donanim_testi.py`, `demo_baslat.py`, `cevrimdisi_hazirlik_kontrolu.py`) en başına `import ortam_yukle`.
2. **Qdrant koleksiyon boyut çakışması kodda otomatik ayrılmıyordu** — `chunking/qdrant_baglanti.py::VARSAYILAN_KOLEKSIYON` artık `QDRANT_KOLEKSIYON` elle verilmediği sürece EVREN aktifken otomatik `_evren` soneki alıyor (768 vs 1024 boyut karışmasını koddan engeller).
3. **Hibrit/dense ayrımı kodda hiç yoktu** — `chunking/retriever.py::getir()`'e `rag_modu` parametresi ve `RAG_MODE` ortam değişkeni eklendi (`chunking/qdrant_baglanti.py::yogun_ara`, yeni). Varsayılan: EVREN pasifken "hibrit" (mevcut, ölçülü davranış değişmedi), EVREN aktifken "dense" (EVREN'in kendi ölçümü, bu depoda henüz doğrulanmadı ama hibritin bu depoda da doğrulanmamış olmasından daha savunulabilir bir varsayılan).
4. **`ASGARI_VEKTOR_SKORU = 0.40` eşiği** yerel `e5-base`'e göre ölçülmüştü, `bge-m3-embed` için hâlâ doğrulanmadı — `ASGARI_VEKTOR_SKORU` ortam değişkeniyle ezilebilir hâle getirildi, koddaki uyarı bu eşiğin EVREN için henüz kalibre edilmediğini açıkça belirtiyor.

**Bilinçli olarak ERTELENEN madde — Sara'nın provider abstraction (interface + `providers/` benzeri bir katman) önerisi:** Şu anki tasarımda `evren_istemci.aktif_mi()` dallanması yalnızca **iki** net, dokümante edilmiş noktada yaşıyor (`extraction/llm_extractor.py::llm_ile_sor`, `chunking/embedding.py::_vektore_cevir`) — kodun her yerine dağılmış değil. Gerçek anahtarla ilk bağlantı doğrulanmadan (bkz. bu ADR'nin ana gövdesi, "önce doğrula sonra mimari kur" gerekçesi) bir `Protocol`/arayüz katmanı inşa etmek, henüz doğrulanmamış varsayımlar üzerine ikinci bir soyutlama katmanı koymak anlamına gelir. Gerçek EVREN davranışı doğrulandıktan ve `RAG_MODE=dense` ile `hibrit` karşılaştırmalı olarak ölçüldükten sonra yeniden değerlendirilecek.

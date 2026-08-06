# Qdrant + Embedding Spike Raporu

**Tarih:** 6 Ağustos 2026
**Amaç:** İlerleme Planı'nın Sprint 2 maddesi — *"en az 1 bankanın metniyle
ilk vektör kaydı denenir, donanım/RAM sorunları Sprint 3'ü beklemeden erken
yakalanır"*. Bu bir **risk azaltma adımıdır**, RAG'in kendisi değildir.

Çalıştırmak için:
```bash
docker compose up -d qdrant
python -m chunking.spike_qdrant
```

---

## Sonuç: teknik olarak çalışıyor ✅

Uçtan uca zincir doğrulandı: **gerçek banka metni → parçalama → embedding →
Qdrant'a yazma → Türkçe sorguyla arama**, kaynak bilgisi (provenance) korunarak.

| Adım | Süre | Not |
|---|---|---|
| Parçalama | ~0 sn | 8 kayıt → 104 parça |
| **Embedding** | **96,7 sn** | 104 parça (ilk model yüklemesi ~12 sn dahil) |
| Qdrant'a yazma | 4,6 sn | |
| Arama | **0,58 sn** | |

**Kullanılan model:** `intfloat/multilingual-e5-base` (768 boyut, ~1,1 GB).
Planlanan `bge-m3`'e (~2,3 GB) göre demo makinesinde belirgin şekilde hafif.
`EMBEDDING_MODELI` ortam değişkeniyle değiştirilebilir.

---

## Bulgu 1 — Embedding, LLM'in aksine darboğaz DEĞİL

Bu, spike'ın cevaplamak için yapıldığı asıl donanım sorusuydu:

| İşlem | Bu makinedeki süre |
|---|---|
| LLM çıkarımı (Ollama/Qwen2.5, tek çağrı) | **150–300+ sn** |
| Embedding (parça başına) | **~0,9 sn** |
| Vektör arama | **0,58 sn** |

**Sonuç:** RAG'in *arama* tarafı canlı demoda rahatlıkla çalışır (< 1 sn).
Pahalı olan tek şey **ilk indeksleme**, ki o da tek seferlik toplu iştir.

**Tam indeks tahmini:** 234 kayıt × ~13 parça ≈ 3.000 parça ≈ **45–50 dakika**
(tek seferlik). Demo öncesi bir kez çalıştırılıp Qdrant volume'ünde saklanmalı;
demo sırasında yeniden indekslemeye gerek yok.

---

## Bulgu 2 — Ham benzerlik skoru abstention için YETERSİZ ⚠️

Spike, iki sorgu tipini karşılaştırır: cevabı veride **olan** ve
**kesinlikle olmayan**.

| Sorgu | En iyi skor |
|---|---|
| "Kâr payı oranı ve vade seçenekleri nedir?" (alakalı) | **0,8216** |
| "Uzay istasyonunda yerçekimi nasıl ölçülür?" (tamamen alakasız) | **0,7761** |
| **Fark** | **0,0455** |

Uzay istasyonu sorusu bile **0,78** skor alıyor. e5 ailesi yüksek taban
benzerliği ürettiği için, "skor > 0,75 ise kaynak buldum" gibi sezgisel bir
eşik **yanlış pozitif üretir** — sistem alakasız bir kampanya metnini kaynak
gösterip cevap uydurabilir.

**Bu, projenin kendi şeffaflık ilkesiyle (rapor Bölüm 5.7/15) doğrudan
çelişen bir risktir** ve RAG bağlanmadan önce çözülmelidir. Seçenekler:

1. **Hibrit arama** (dense + BM25/lexical): "Worldpuan", "98/2", banka adı gibi
   birebir terimler lexical tarafta yakalanır, taban benzerliği sorunu azalır.
2. **Reranker** (cross-encoder): top-k sonucu yeniden sıralar, ayırt ediciliği
   belirgin artırır.
3. **Görece eşik**: mutlak skor yerine "en iyi sonuç, ikinciden ne kadar
   ayrışıyor?" ölçütü.

Spike bu uyarıyı otomatik verir: fark 0,05'in altına düşerse ekrana yazar.

---

## Bulgu 3 — Naif parçalama yinelenen ve değersiz parça üretiyor

Alakasız sorgunun ilk 3 sonucunun **üçü de aynı metindi**
("Harcama yapılan iş yerinin sektör bilgisinin doğruluğu..."). Ayrıca
sonuçlarda yasal uyarı/menü metinleri öne çıkıyor.

Bu beklenen bir sonuç — spike'taki parçalama **bilerek** en kaba haliyle
(satır bazlı) bırakıldı. Ama gerçek chunking tasarımının çözmesi gerekenleri
somutlaştırıyor:

- **Yinelenen parçalar** indeks alanını şişiriyor ve sonuç listesini dolduruyor
  → yazmadan önce tekilleştirme (hash) gerekli.
- **Boilerplate** (yasal uyarı, çerez metni, menü) her kampanyada tekrar ediyor
  ve gerçek içeriği bastırıyor → şablon metin filtresi gerekli.
- Kampanya koşulu / tablo satırı / SSS gibi **anlamlı sınırlar** korunmalı.

---

## Kapsam notu

Bu spike **altyapıyı** kurar (`chunking/qdrant_baglanti.py`,
`chunking/embedding.py`) ve riskleri ölçer. **Semantik chunking stratejisi,
metadata şeması ve retrieval kalitesi NLP tarafının (Yağmur) tasarım
kararıdır** — bu spike onun yerine karar vermez, hazır bir zemin ve ölçülmüş
üç bulgu bırakır.

## Sıradaki adım

1. Yinelenen/boilerplate parça filtresi (Bulgu 3) — ucuz, indeks kalitesini
   doğrudan artırır.
2. Hibrit arama veya reranker (Bulgu 2) — RAG "kaynaklı cevap" iddiasıyla
   sunulmadan önce **zorunlu**.
3. Tam indeksleme (~45–50 dk) demo öncesi bir kez çalıştırılır.

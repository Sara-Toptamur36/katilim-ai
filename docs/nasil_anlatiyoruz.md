# Sistemi nasıl anlatıyoruz — mimari iddiası

Bu belge **video, sunum ve Md. 6 dokümanı** yazılırken kullanılacak ortak
metindir. Amacı üslup birliği değil, **iddia dürüstlüğü**: dördümüz ayrı ayrı
yazacağız ve tek bir abartılı cümle, ölçülmüş her şeyin güvenilirliğini
birlikte götürür.

## 1. Neden bu belge var

En büyük kırmızı bayrak: **"Qwen'i fine-tune ettik" demek.**

Bu cümle söylendiği anda jürinin soracağı sorular bellidir:

- Eğitim verisi nerede, kaç örnek?
- Train/validation/test ayrımı nasıl yapıldı?
- Loss eğrisi, adapter ağırlıkları, hiperparametreler?
- Fine-tune edilmemiş baseline'a karşı ölçüm nerede?

**Bu depoda bunların hiçbirinin cevabı yok — çünkü fine-tuning yapılmadı.**
Yapılmadığı için de iddia edilmemeli. Cevaplanamayan bir soru, ölçülmüş
%98,28'lik makro F1'i de şüpheli hale getirir.

Fine-tuning'in **bilinçli olarak** kapsam dışı bırakılmasının gerekçesi ayrı
bir belgededir: [kapsam_ve_veri_ayrimi.md](kapsam_ve_veri_ayrimi.md).

## 2. Doğru anlatım (okunacak metin)

> KatılımAI, katılım bankalarının kampanya sayfalarından finansal bilgiyi
> çıkaran bir **hibrit çıkarım mimarisidir**. Üç katman sırayla çalışır:
> önce **regex** deterministik kalıpları yakalar, yakalayamadığı bağlamsal
> ifadeler için **GLiNER** zero-shot devreye girer, o da yetmezse
> **Qwen2.5-7B** yerelde (Ollama) sorulur. Katmanlar birbirinin üzerine
> yazmaz: her alan bir **aday** üretir, çözümleyici en yüksek güvenli adayı
> seçer ve 0,8 güven eşiğini geçen alanları kilitler.
>
> Yeniliğimiz modeli eğitmek değil, **hangi katmanın ne kadar katkı verdiğini
> — ve nerede zarar verdiğini — ölçmüş olmak**. Kullanılan üç model de açık
> kaynak ve **olduğu gibi**, sürümü sabitlenmiş biçimde çalışır.

Bu paragraf videoda da sunumda da olduğu gibi kullanılabilir.

## 3. Kullanılan modeller — hiçbirine dokunulmadı

| Katman | Model | Ne yaptık |
|---|---|---|
| Bağlamsal çıkarım | `urchade/gliner_multi-v2.1` | Zero-shot — **etiket adını söyleyip** sorduk, eğitmedik |
| Üretken çıkarım | `qwen2.5:7b-instruct-q4_K_M` (Ollama) | Yalnızca **istem (prompt)** yazdık, `temperature=0` |
| Gömme (RAG) | `intfloat/multilingual-e5-base` | Olduğu gibi kullanıldı |

Üçünde de **ağırlık güncellemesi yok**: adapter yok, LoRA yok, gradient
adımı yok, `training/` dizini yok. Sürümler `requirements.txt` içinde `==`
ile sabitlenmiştir.

## 4. Söylemeyeceğimiz / söyleyeceğimiz

| ❌ Söylemeyeceğiz | ✅ Söyleyeceğiz |
|---|---|
| "Qwen'i fine-tune ettik" | "Qwen2.5/Ollama destekli **hibrit çıkarım mimarisi**" |
| "Modeli kendi verimizle eğittik" | "Modeli **kendi istemimizle yönlendirdik**; ağırlıklara dokunulmadı" |
| "Kendi NER modelimizi çıkardık" | "GLiNER'ı **zero-shot** kullandık, etiket şemasını biz tanımladık" |
| "İnce ayar yaptık" | "Katman sırasını ve **güven eşiğini** ölçerek ayarladık" |

Son sütundaki ifadeler **doğrudur ve kanıtlanabilir** — aşağıya bakınız.

## 5. Her iddianın kanıtı nerede

İddia ederken kaynağı da göstereceğiz; jüri "nereden biliyorsunuz?" diye
sorduğunda tek tıkla açılacak yer:

| İddia | Kanıt |
|---|---|
| Üç katmanlı hibrit çıkarım | `extraction/hybrid_pipeline.py` |
| Katman katkısı ölçüldü | [extraction_accuracy_raporu.md](extraction_accuracy_raporu.md) |
| Makro F1 %98,28 | `python -m scraper.scripts.extraction_accuracy` |
| Güven eşiği 0,8 ile kilitleme | `extraction/hybrid_pipeline.py::KILITLEME_GUVEN_ESIGI` |
| Fine-tuning yok | [kapsam_ve_veri_ayrimi.md](kapsam_ve_veri_ayrimi.md) §4 |
| Modeller sürüm sabitli | `requirements.txt` (27 paketin tamamı `==`) |
| Kaynaksız cevap üretilmiyor | [rag_tasarim_ve_olcum.md](rag_tasarim_ve_olcum.md) §5 |

## 6. Bu kural nasıl korunuyor

`tests/test_iddia_durustlugu.py` deponun tüm `.md` ve `.py` dosyalarını tarar;
eğitim iddiası bulursa CI'da **kırmızı verir** ve dosya:satır gösterir. Test,
kelimenin geçmesini değil **olumlu iddia kalıplarını** arar — "fine-tuning
yapılmadı" gibi olumsuz cümleler serbesttir, çünkü onlar zaten doğruyu söyler.
Bekçinin gerçekten yakaladığı da ayrıca test edilir; yakalamayan bir bekçi
yeşil görünüp hiçbir şey korumaz.

**Neyi kapsamaz — elle kontrol gerekir:**

| Yüzey | Durum |
|---|---|
| Depodaki `.md` / `.py` | ✅ Otomatik |
| **Sunum (PPTX/PDF)** | ❌ İkili dosya, taranamaz |
| **Video anlatımı / altyazı** | ❌ Depoda değil |
| Depo dışı planlama belgeleri | ❌ Taranmıyor (17 Ağustos'ta elle kontrol edildi, temiz) |

Yani sunum ve video **kaydedilmeden önce** 4. bölümdeki tablo elle
karşılaştırılmalı. Bekçi bu adımın yerine geçmez, yalnızca yazılı depoda
sessiz bir kaymayı engeller.

# Extraction Accuracy Raporu (Sprint 3 Gün 4)

Rapor Bölüm 13'ün "Extraction Accuracy — Hedef ≥ %95" maddesinin **ilk gerçek
ölçümü**. `scraper/scripts/extraction_accuracy.py` ile üretildi:
Yağmur'un `extraction/regex_extractor.py` çıkarım motoru, doğrudan (Docker/DB
gerekmeden) Altın Veri Seti referans değerleriyle karşılaştırıldı.

Çalıştırmak için:
```bash
python -m scraper.scripts.extraction_accuracy         # yalnızca regex
python -m scraper.scripts.hibrit_extraction_accuracy  # regex + NER + LLM
```

---

## Ölçüm yöntemi değişikliği — 6 Ağustos 2026

Önceki ölçümler **tek bir doğruluk yüzdesi** raporluyordu ve bu yüzde,
yalnızca Altın Veri Seti'nde **dolu olan** alanlar üzerinden hesaplanıyordu.
Gold'da boş olan alanlar `continue` ile atlanıyordu — yani **motor kaynakta
hiç olmayan bir alana değer uydursa hiçbir ceza almıyordu.**

Bu, finansal bir uygulamada kritik bir kör noktadır: kullanıcının olmayan bir
kampanya koşuluna güvenerek karar vermesi, bir bilgiyi kaçırmaktan daha
tehlikelidir. Bu yüzden ölçüm **iki ayrı metriğe** ayrıldı:

| Metrik | Neyi ölçer | Hata türü |
|---|---|---|
| **Dolu alan doğruluğu** | Gold'da dolu olan alanı motor doğru buluyor mu? | Kaçırma / yanlış değer |
| **Boş alan doğruluğu** | Kaynakta olmayan alana motor değer uyduruyor mu? | **Yanlış pozitif (halüsinasyon)** |

### Kapsam kuralı (önemli)

Yanlış pozitif yalnızca, altın kayıtta `alan_belirtilmemis[alan] = true` ile
**açıkça "kaynakta belirtilmemiş"** diye işaretlenmiş alanlarda sayılır.
Gold'da boş olup bayraklanmamış alanlar ölçüm dışıdır — orada "kaynakta yok"
ile "etiketleyici bu sütunu doldurmadı" ayırt edilemez, ikisini karıştırmak
motoru haksız yere cezalandırırdı.

> **Veri kalitesi notu:** Bu bayrak şu an 7 alandan yalnızca 3'ünde tutarlı
> doldurulmuş (`kar_payi_orani`, `vade_ay`, `odul_miktari`).
> `odul_birimi` ve `finansman_tutari` boş bırakılmış ama bayraklanmamış;
> `taksit_sayisi` ve `erteleme_suresi_ay` sütunları ise Altın Veri Seti'nde
> hiç doldurulmamış (şemaya sonradan eklendiler). Bu alanlar için yanlış
> pozitif **ölçülemiyor** — Altın Veri Seti genişletilirken bu boşluğun
> kapatılması önerilir.

### Sonuç — 6 Ağustos 2026 (regex-only)

| Metrik | Sonuç |
|---|---|
| Dolu alan doğruluğu | **%84,38** (64 alanın 54'ü doğru) |
| Boş alan doğruluğu | **%91,78** (73 ölçülebilir alanın 67'si doğru) |
| **Yanlış pozitif** | **6** |
| Ölçüme dahil canlı kayıt | 36 |

### Tespit edilen 6 yanlış pozitif

| Kayıt | Alan | Uydurulan değer | Muhtemel neden |
|---|---|---|---|
| KT-006 | `kar_payi_orani_percent` | `0.0` | "vade farksız" → %0 kuralı, gold'da belirtilmemiş sayılan sayfada tetikleniyor |
| TF-001 | `kar_payi_orani_percent` | `0.0` | aynı kural |
| HF-005 | `kar_payi_orani_percent` | `0.1` | bağlamsız bir yüzde kâr payı sanılmış |
| TEK-001 | `kar_payi_orani_percent` | `10.0` | büyük olasılıkla indirim yüzdesi kâr payı sanılmış (`RATE_CONTEXT` hatası) |
| KT-006 | `odul_miktari` | `50000.0` | ödül bağlamı olmayan bir tutar ödül sanılmış |
| TOM-002 | `odul_miktari` | `2500.0` | aynı tür |

**Örüntü:** 6 yanlış pozitifin 4'ü `kar_payi_orani_percent` alanında ve
3'ü sıfır-oran (`0.0`) üretiyor. Bu, "vade farksız → kâr payı %0" kuralının
gerçekten kâr payından bahsetmeyen sayfalarda da tetiklendiğini gösteriyor.
Kural yanlış değil (gerçek sıfır-oran kampanyaları var), ancak bağlam
kontrolü gerektiriyor — bu, `kar_payi_orani` kritik bir finansal alan olduğu
için en yüksek öncelikli düzeltmedir.

---

---

## Alan bazlı P/R/F1 — 9 Ağustos 2026

Toplam iki metrik sistemin genel sağlığını gösterir ama **hangi alanın**
zayıf olduğunu söylemez. Şartnamenin en ağır kriteri (Model Başarısı, %30)
tam da bunu sorar. Ölçüm artık alan kırılımı da basıyor.

| Alan | Destek | TP | FP | FN | P% | R% | F1% |
|---|---|---|---|---|---|---|---|
| `odul_birimi` | 23 | 23 | 0 | 0 | 100,00 | 100,00 | **100,00** |
| `odul_miktari` | 23 | 22 | 2 | 1 | 91,67 | 95,65 | **93,62** |
| `finansman_tutari` | 6 | 4 | 1 | 2 | 80,00 | 66,67 | 72,73 |
| `kar_payi_orani_percent` | 5 | 5 | 4 | 0 | **55,56** | 100,00 | 71,43 |
| `vade_ay` | 7 | 1 | 0 | 6 | 100,00 | **14,29** | 25,00 |
| `taksit_sayisi` | — | — | — | — | — | — | ölçülemiyor |
| `erteleme_suresi_ay` | — | — | — | — | — | — | ölçülemiyor |

**Makro F1: %72,56** (5 ölçülebilir alan)

**Tanımlar:** TP = gold'da değer var, motor aynısını buldu · FN = kaçırdı ·
FP = kaynakta belirtilmemiş alana değer uydurdu. **Yanlış değer hem FP hem
FN sayılır** (bilinçli karar): gold 1,89 derken motor 10,0 bulduysa hem
doğru değeri kaçırmış hem yanlış bir değer iddia etmiştir. Yalnızca FN
saymak, finansal bir uygulamada daha tehlikeli olan "yanlış değer
gösterme" hatasını gizlerdi.

### Tablonun ilk çalıştırmada ortaya çıkardığı veri kalitesi hatası

`vade_ay` recall'ı **%14,29** görünüyor — ama bu bir çıkarım hatası
**değil**. Kaçırılan 6 kaydın tamamında gold'daki "vade" değeri aslında
bir **taksit sayısıdır**:

| Kayıt | Gold `vade_ay` | Kampanya başlığı |
|---|---|---|
| KT-006 | 5 | "Vade Farksız **5 Aya Varan Taksit**" |
| AL-001 | 6 | "Seçili sektörlerde vade farksız **6 taksit**" |
| AL-002 | 3 | "MTV Ödemelerinize Vade Farksız **3 Taksit**" |
| AL-005 | 6 | "Sağlık Harcamalarına Vade Farksız **6 Taksit**" |
| AL-006 | 6 | "Eğitim Harcamalarınıza Vade Farksız **6 Taksit**" |
| TOM-002 | 10 | "Özel Okul Ödemelerinde **10 Taksit**" |

**Sebep:** Altın Veri Seti 28 Temmuz'da etiketlenirken `taksit_sayisi`
sütunu **yoktu**; etiketleyicinin bu değerleri yazacak başka yeri olmadığı
için `vade_ay` sütununa girmiş. Motor bu kayıtlarda `vade_ay = None`
döndürerek **doğru** davranıyor — bu kampanyaların vadesi yok.

Bu, iki toplam metriğin haftalardır gizlediği bir hatadır ve alan
kırılımının neden gerekli olduğunun somut kanıtıdır. Düzeltme, sütunlar
etiketlendiğinde (bkz. `gold_dataset/etiketleme_yardimcisi.py`) bu altı
değerin `taksit_sayisi`'na taşınmasıdır; `vade_ay` recall'ı o zaman
gerçek değerine yükselecektir.

### Diğer okumalar

- `kar_payi_orani_percent` precision **%55,56** — 4 yanlış pozitifin
  kaynağı "vade farksız → %0" kuralının kâr payından hiç bahsetmeyen
  sayfalarda tetiklenmesi (aşağıdaki yanlış pozitif listesiyle tutarlı).
- `odul_birimi` **%100** — banka-özel birim tanıma (Bankkart Lira /
  ParafPara / Worldpuan) düzeltmesinden sonra hatasız.

---

## Geçmiş ölçüm — 1 Ağustos 2026

**%37.5 doğruluk (64 alanın 24'ü doğru), 36 canlı kayıt üzerinden ölçüldü.**

Hedeflenen %95'in oldukça altında. Ölçüm yalnızca hâlâ sitede canlı olan
kampanyalara uygulandı (rotasyona uğramış kayıtlar ölçüm dışı tutuldu — bkz.
`tests/test_scraper_regresyon.py`, bu veri kaybı çıkarım hatası değildir).

## Hatanın alan bazlı dağılımı

| Alan | Hata sayısı | Yorum |
|---|---|---|
| `odul_birimi` | 18 | **En büyük sorun.** Banka-özel sadakat birimleri (Bankkart Lira, ParafPara, Worldpuan) tanınmıyor, çoğunlukla varsayılan "TL" dönüyor veya hiç bulunamıyor |
| `odul_miktari` | 9 | Ödül ifadesi çoğu zaman hiç yakalanamıyor (`None` dönüyor) |
| `vade_ay` | 7 | Vade ifadesi çoğu zaman hiç yakalanamıyor |
| `kar_payi_orani_percent` | 4 | Hepsi "beklenen=0" durumları — Albaraka'nın "Vade Farksız" ifadesi, mevcut "kâr paysız" deseniyle eşleşmiyor (farklı ama eşdeğer bir sıfır-oran ifadesi) |
| `finansman_tutari` | 2 | Sayfada birden fazla tutar geçtiğinde yanlış olanı seçiyor (ör. AL-001: 40.000 TL bekleniyordu, 100.000 TL bulundu) |

## Somut örnekler (Yağmur için)

- **Ziraat Katılım (6 kayıt) + Emlak Katılım (4 kayıt):** `odul_birimi` hep
  "Bankkart Lira"/"ParafPara" yerine "TL" dönüyor — `RE_ODUL` deseni bu iki
  banka-özel birimi tanımıyor, `RE_ODUL_MIL`/`RE_ODUL_GRAM` gibi özel bir
  desen yok.
- **Albaraka (AL-002, AL-005, AL-006):** "Vade Farksız" kampanyaları kâr payı
  oranı %0 olması gerekirken `None` dönüyor — `RE_KAR_PAYSIZ` yalnızca "kâr
  paysız" / "0 kâr paylı" kalıplarını arıyor, "vade farksız" ifadesini
  kâr payı sıfırına bağlamıyor (bu iki ifade katılım bankacılığında eşdeğer
  anlam taşıyor olabilir — kavramsal bir karar Yağmur'a bırakılmalı).
- **AL-001:** Sayfada iki farklı tutar aralığı var (40.000 TL'lik bir alt
  kampanya + 100.000 TL'lik başka bir alt kampanya); `RE_TUTAR_UST_LIMIT`
  ilk eşleşmeyi alıyor ama bu her zaman doğru kampanyaya ait olmuyor.
- **TOM-002:** Beklenmeyen bir "kâr payı %10" değeri bulundu (gerçekte kampanya
  vade farksız/%0 olmalıydı) — düşük güvenli genel yüzde deseni (`RE_KAR_PAYI_GENEL`)
  muhtemelen alakasız bir "%10" ifadesini (10 taksit değil, başka bir yüzde)
  yanlışlıkla kâr payı sandı.

## Not

Bu rapor **yalnızca ölçüm ve tespittir** — `extraction/regex_extractor.py`
Yağmur'un alanı olduğu için buradan dokunulmadı (rehber Bölüm 13.3/proje
yapısı: "terminology/ extraction/ - Yağmur'un alanı, dokunma"). Yukarıdaki
bulgular doğrudan Yağmur ve Sara ile paylaşılmak üzere hazırlandı.

> 1 Ağustos'taki bulguların büyük kısmı düzeltilmiştir (%37,5 → %84,38);
> yukarıdaki "Geçmiş ölçüm" bölümü, iyileştirmenin izlenebilir kaydı olarak
> bilerek korunmuştur.

## Sıradaki adım

En yüksek öncelikli düzeltme, yanlış pozitiflerin yoğunlaştığı
`kar_payi_orani_percent` alanıdır (6 yanlış pozitifin 4'ü burada). "Vade
farksız → %0" kuralına bağlam kontrolü eklenmesi, hem yanlış pozitifi
azaltır hem de gerçek sıfır-oran kampanyalarını yakalamaya devam eder.

Ölçüm altyapısı artık her iki metriği de raporladığı için, bu düzeltmenin
etkisi **iki yönlü** görülebilir: dolu alan doğruluğu düşmeden boş alan
doğruluğunun artması beklenir. Yalnızca birinin iyileşip diğerinin bozulması,
kuralın fazla dar/geniş ayarlandığının işaretidir.

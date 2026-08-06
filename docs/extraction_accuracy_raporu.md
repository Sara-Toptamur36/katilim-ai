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

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

Aşağıdaki tablo, "Kaçırma analizi ve düzeltmeler" bölümündeki
düzeltmelerden **önceki** durumu gösterir — güncel değerler için o bölüme
bakınız.

| Alan | Destek | TP | FP | FN | P% | R% | F1% |
|---|---|---|---|---|---|---|---|
| `odul_birimi` | 23 | 23 | 1 | 0 | 95,83 | 100,00 | **97,87** |
| `odul_miktari` | 23 | 22 | 2 | 1 | 91,67 | 95,65 | **93,62** |
| `kar_payi_orani_percent` | 5 | 5 | 4 | 0 | **55,56** | 100,00 | 71,43 |
| `finansman_tutari` | 6 | 4 | 4 | 2 | **50,00** | 66,67 | 57,14 |
| `vade_ay` | 7 | 1 | 0 | 6 | 100,00 | **14,29** | 25,00 |
| `taksit_sayisi` | — | — | — | — | — | — | ölçülemiyor |
| `erteleme_suresi_ay` | — | — | — | — | — | — | ölçülemiyor |

**Makro F1: %69,01** (5 ölçülebilir alan)

> Bu sayılar, ölçüm kapsamı `finansman_tutari` ve `odul_birimi` için
> genişletildikten **sonrakidir** (boş alan kontrolü 73 → 116). Kapsam dar
> iken makro F1 %72,56 görünüyordu; düşüş motorun bozulmasından değil,
> daha önce **görünmeyen 4 yanlış pozitifin ölçülebilir hale gelmesinden**
> kaynaklanıyor.

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

## Kaçırma analizi ve düzeltmeler — 10 Ağustos 2026

Alan bazlı tablo 9 kaçırma gösteriyordu. Tek tek kaynak metne bakıldığında
**6'sı motorun hatası değildi.**

### Bulgu 1 — Altın Veri Seti'nde sistematik sütun hatası

`vade_ay` recall'ı %14,29'du. Kaçırılan 6 kaydın gold değeri aslında
**taksit sayısı**:

| Kayıt | Gold `vade_ay` | Kampanya başlığı | Sayfada gerçek vade ifadesi |
|---|---|---|---|
| KT-006 | 5 | "Vade Farksız **5 Aya Varan Taksit**" | yok |
| AL-001 | 6 | "vade farksız **6 taksit**" | yok |
| AL-002 | 3 | "MTV Ödemelerinize Vade Farksız **3 Taksit**" | yok |
| AL-005 | 6 | "Sağlık Harcamalarına Vade Farksız **6 Taksit**" | yok |
| AL-006 | 6 | "Eğitim Harcamalarınıza Vade Farksız **6 Taksit**" | yok |
| TOM-002 | 10 | "Özel Okul Ödemelerinde **10 Taksit**" | yok |

Sebep: `taksit_sayisi` sütunu 28 Temmuz'da **yoktu**. Gold'un kendi
`kampanya_avantaji` metni de altı kayıtta "taksit" diyor. Değerler
değiştirilmeden doğru sütuna taşındı; `vade_ay` boşaltıldı.

> **Not:** Taşıma sırasında `openpyxl`'in `ws.cell(r, c, None)` çağrısının
> hücreyi **temizlemediği** görüldü (imza `value=None` olduğu için "değer
> verilmedi" anlamına geliyor). İlk denemede aynı sayı iki sütunda birden
> kaldı. Doğrusu `ws.cell(r, c).value = None`.

### Bulgu 2 — "250 Bin TL" biçimi hiç tanınmıyordu

T.O.M. Katılım tutarları binlik ayıraç yerine kelimeyle yazıyor. Bu biçim
desende olmadığı için `finansman_tutari` bulunamıyordu.
`normalizer.tutara_cevir` artık bin/milyon/milyar çarpanını uyguluyor.

### Bulgu 3 — "X TL'ye kadar" tek başına finansman tutarı değil

`RE_TUTAR_UST_LIMIT`'te bağlam kontrolü yoktu (kâr payı deseninde vardı).
9 yanlış pozitifin 3'ü buradan geliyordu: kart limiti, harcama eşiği,
iade tavanı. Kâr payındaki `_ucret_baglaminda_mi` ile aynı yaklaşımla
olumsuz bağlam listesi eklendi.

Guard **yalnızca üst-limit desenine** uygulanır; aralık deseni
("X TL - Y TL arası") gerçek veride sadece finansman aralıklarında geçiyor
ve hiçbir yanlış pozitif oradan gelmedi.

**Bağlam penceresi cümleye kırpılır** — düz karakter penceresi cümle
sınırını aşıyor ve önceki cümledeki bir ödül ifadesi sonraki cümledeki
gerçek finansman tutarını eliyordu. Nokta yalnızca **ardından boşluk
gelirse** cümle sonu sayılır (Türkçe binlik ayıracı da noktadır);
satır sonu sınır değildir (scraper her HTML bloğu arasına `\n` koyuyor).

### Bulgu 4 — Ödül yüzdesi ve dar makas, kâr payı sanılıyordu

Genel yüzde fallback'inin dışlama listesinde ücret/masraf terimleri vardı
ama **ödül/kazanım** ve **dar makas** yoktu:

| Kayıt | Uydurulan | Gerçekte |
|---|---|---|
| TEK-001 | %10 | *"ödeme tutarının %10'u oranında… ödül kazanabilir"* |
| HF-005 | %0,1 | *"%0,1 **dar makas**tan yararlanabilir"* (döviz spreadi) |

`terminology/sozluk.json` dar makası **zaten** *"kâr payı oranı ile
KARIŞTIRILMAMALI"* diye işaretlemişti — kural sözlükte vardı ama regex'e
bağlanmamıştı.

### Bulgu 5 — Taksitlendirme tavanı ödül sanılıyordu

`RE_ODUL_TAVAN` ("en fazla / maksimum + tutar") bağlamsız çalışıyordu ve
KT-006'da *"Bu harcamaya ait uygulanacak **taksitlendirmede** maksimum
tutar 50.000 TL'dir"* cümlesini ödül olarak okudu.

Desen 4 gerçek kayıtta **doğru** çalışıyor (hepsinde "ödül" /
"kazanılabilecek" / "iade" aynı cümlede geçiyor), bu yüzden kaldırılmadı;
**aynı cümlede bir ödül kelimesi bulunması** şartı eklendi. Kelime kümesi
`llm_extractor._ODUL_ANAHTAR_KELIMELERI` ile aynı tutuldu — iki motor da
"ödül" kavramını aynı tanımlamalı.

### Sonuç

| | Önce | Sonra |
|---|---|---|
| Dolu alan doğruluğu | %85,94 | **%95,31** |
| Boş alan doğruluğu | %92,24 | **%98,36** |
| Kaçırma | 9 | **3** |
| Yanlış pozitif | 9 | **2** |
| **Makro F1** | **%69,01** | **%90,94** |
| `vade_ay` F1 | 25,00 | **100,00** |
| `odul_birimi` F1 | 97,87 | **100,00** |
| `odul_miktari` F1 | 93,62 | **95,65** |
| `kar_payi_orani` F1 | 71,43 | **83,33** |
| `finansman_tutari` F1 | 57,14 | **83,33** |
| `taksit_sayisi` | ölçülemiyor | **83,33** |

### Kalan 2 yanlış pozitifin ikisi de Altın Veri Seti kaynaklı

- **KT-006** `kar_payi_orani`: kampanya *"Vade Farksız 5 Aya Varan
  Taksit"*. AL-002, AL-005 ve TOM-002 **birebir aynı yapıda** ve gold'da
  üçü de `0`; KT-006 ise "belirtilmemiş". Gold tutarsızlığı — etiketleme
  kararı gerektirir.
- **TF-001** `kar_payi_orani`: sayfada *"Kâr paysız 2.500 TL'ye kadar"*
  ifadesi geçiyor, yani motor haklı. Ancak bu, kampanyanın kendisine değil
  sayfada listelenen **başka bir ürüne** ait — AL-001'le aynı **sayfa
  kapsamı kirlenmesi**.

### Kalan 3 kaçırma

- **AL-001** `finansman_tutari` (40.000 bekleniyor, 100.000 bulunuyor):
  desen sorunu **değil**. AL-001'in kazınan metni **AL-005'in kampanya
  metnini de içeriyor** ("1.000 TL-100.000 TL arası **sağlık**
  harcamalarınıza"). Albaraka'nın `.searchContent` seçicisi kardeş
  kampanya bloklarını da alıyor — bu bir **kapsam kirlenmesi** ve tüm
  Albaraka kayıtlarını etkiliyor olabilir. Scraper tarafında ele alınmalı.
- **AL-001** `taksit_sayisi` (6 bekleniyor, 4 bulunuyor): kampanya iki
  bölümlü ("4 taksitli" + "6 taksit"); gold'un kendi notu da bu
  ikiliği yazıyor. Gerçek belirsizlik — etiketleme kararı gerektirir.
- **DK-002** `odul_miktari` (0,1 bekleniyor, 1,0 bulunuyor): gold davet
  başına ödülü (0,1 gram), motor üst sınırı (1 gram) alıyor. KT-007'de
  gold **toplamı** seçmişti — etiketleme politikası netleştirilmeli.

---

## Ablation: katman katkısı — 9 Ağustos 2026

`python -m scraper.scripts.ablation`

"Hibrit %86" tek sayısı, katmanların **kendi** katkısını göstermez. Üst
katmanlar tek tek kapatılarak üç varyant aynı Altın Veri Seti'ne karşı
ölçülür.

Aşağıdaki tablo, ölçüm kapsamı genişletilmeden **önceki** durumu gösterir
(güncel sonuç için "Ölçüm kapsamı genişletilince ne oldu" bölümüne bakınız):

| Varyant | Dolu% | Boş% | Makro F1 | YP | Süre |
|---|---|---|---|---|---|
| regex | 85,94 | 93,15 | 72,56 | 5 | **0,8 sn** |
| regex + NER | 85,94 | 93,15 | 72,56 **(+0,00)** | 5 | **222 sn** |
| regex + NER + LLM | — | — | — | — | Ollama gerektirir |

### "+0,00" yanıltıcıdır — NER aslında 7 alan dolduruyor

Alan bazlı F1 hiçbir alanda değişmedi, ama bu **"NER hiçbir şey yapmadı"
demek değil.** Katman katkısı sayımı:

```
ner    7 alan doldurdu  ->  0 ölçüme girdi, 7 ÖLÇÜM DIŞI
```

NER'in doldurduğu 7 `finansman_tutari` değerinin tamamı, Altın Veri
Seti'nde o hücrenin **hiç etiketlenmediği** kayıtlara denk geliyor — yani
ne katkısı ne hatası ölçüme yansıyor.

### Ve bu 7 değer büyük olasılıkla YANLIŞ

Değerler kayıtların `odul_miktari` alanıyla **birebir örtüşüyor**:

| Kayıt | NER `finansman_tutari` | Gold `odul_miktari` | Kampanya |
|---|---|---|---|
| KT-007 | 750 | **750** | "…750 TL Kazan!" |
| AL-003 | 1.250 | **1.250** | "…1.250 TL Worldpuan!" |
| ZK-002 | 1.500 | **1.500** | "…1.500 TL Bankkart Lira!" |
| ZK-007 | 400 | **400** | "…400 TL Bankkart Lira!" |
| ZK-008 | 750 | **750** | "…750 TL Bankkart Lira!" |
| TEK-001 | 500 | **500** | "…500 TL'ye Varan Nakit İade" |

Bunlar kart kampanyaları — finansman ürünü değil, **ödül**. NER ödül
tutarını finansman tutarı sanıyor. Bu, `extraction/ner_extractor.py`'nin
kendi 1. bulgusunda zaten belgelenmiş hata:

> *"400 TL Bankkart Lira" → "finansman tutarı" sandı (0,52), "ödül
> miktarı" DEĞİL.*

Bu, ablation tablosunun tek başına yeterli olmadığının somut örneğidir:
F1 farkı 0 olan bir katman "zararsız" değil, "**ölçülemez**" olabilir.
Betik bu durumu artık otomatik uyarıyor.

### Ölçüm kapsamı genişletilince ne oldu (aynı gün)

`finansman_tutari` ve `odul_birimi` sütunlarının `alan_belirtilmemis`
bayrakları tamamlandıktan sonra ablation **aynı kodla** tekrar çalıştırıldı:

| | Kapsam dar | Kapsam geniş |
|---|---|---|
| NER katkısı | 7 doldurdu → **0 ölçüldü** | 7 doldurdu → **7 ölçüldü** |
| Makro F1 farkı | **+0,00** | **−3,81** |
| Yanlış pozitif (regex+NER) | 9 | **16** |
| `finansman_tutari` F1 | 57,14 | **38,10** |

Tahmin doğrulandı: NER'in 7 dolgusunun tamamı yanlış pozitif. **186
saniyelik maliyeti karşılığında ölçülebilir katkısı sıfır, zararı 7
yanlış pozitif.** Önceki "+0,00" bir ölçüm körlüğüydü.

**Karar önerisi:** NER katmanı mevcut haliyle hibrit boru hattından
çıkarılmalı ya da `finansman_tutari` etiketi devre dışı bırakılmalıdır
(GLiNER'in ödül/finansman ayrımını yapamadığı, `ner_extractor.py`
Bulgu 1'de zaten belgeli). Karar Yağmur'a aittir.

> **Ollama kapalıyken üçüncü varyant geçersizdir.** `llm_ile_cikar`
> erişemediğinde hata fırlatmaz, kademeli fallback gereği `None` döner —
> tablo "LLM katkı yapmadı" gibi görünür, oysa LLM hiç çalışmamıştır.
> Betik servisi kontrol edip satırı `GECERSIZ` işaretler.

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

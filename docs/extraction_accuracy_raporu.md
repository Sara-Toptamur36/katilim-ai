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

### Bulgu 6 — Sayfa kapsamı kirlenmesi

AL-001'in kazınan metni, kampanyanın kendi içeriği bittikten sonra
**başka kampanyaların tanıtım bloğunu** da içeriyordu:

```
Kredi kartına vade farksız taksit kampanyaları hakkında detaylı bilgi almak için:
Sağlık Kampanyası | Albaraka Türk
"… 1.000 TL- 100.000 TL arası sağlık harcamalarınıza …"     ← bu AL-005'in tutarı
Eğitim Kampanyası | Albaraka Türk
```

Motor bu bloktaki **100.000 TL**'yi AL-001'in finansman tutarı sanıyordu
(doğrusu 40.000 TL). `preprocessing/kapsam.py` bu bloğu kırpıyor ve
`statik_scraper` artık kaydetmeden önce uyguluyor; mevcut kayıtlar için
tek seferlik `scraper.scripts.kapsam_migrasyonu` çalıştırıldı.

> **Kapsam (dürüstlük notu):** 234 belgenin **yalnızca 1'inde** bu blok
> var — sistemik bir sorun değil. Kırpma da bilerek dar tutuldu: sadece
> *"…hakkında detaylı bilgi almak için:"* ifadesinden **sonra çapraz
> kampanya başlığı gelen** blok kesilir. Bu ifade kampanyanın kendi
> metninde geçerse (ör. telefon numarasına yönlendirme) metne dokunulmaz.
> Migrasyon 233 dosyaya hiç dokunmadı.

### Sonuç

| | Önce | Sonra |
|---|---|---|
| Dolu alan doğruluğu | %85,94 | **%96,88** |
| Boş alan doğruluğu | %92,24 | **%98,36** |
| Kaçırma | 9 | **2** |
| Yanlış pozitif | 9 | **2** |
| **Makro F1** | **%69,01** | **%93,72** |
| `vade_ay` F1 | 25,00 | **100,00** |
| `odul_birimi` F1 | 97,87 | **100,00** |
| `finansman_tutari` F1 | 57,14 | **100,00** |
| `odul_miktari` F1 | 93,62 | **95,65** |
| `kar_payi_orani` F1 | 71,43 | **83,33** |
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

**Karar (uygulandı — 11 Ağustos 2026, iki aşamalı):** Önce yalnızca NER'den
`finansman_tutari` çıkarıldı — NER'in diğer alanlardaki katkısı ölçülü
olarak zararlı bulunmadığı için korundu, yalnızca kanıtlanan zarar
noktasal olarak kapatıldı. Ardından **regex+NER+LLM** varyantı tekrar
ölçüldüğünde Makro F1 79,46'ya (**-13,19**) düştüğü görüldü; kök neden
analizinde LLM'in de **aynı** ödül/finansman karışıklığına düştüğü
kanıtlandı — 5 yanlış pozitiften 4'ünün değeri, o kaydın gerçek
`odul_miktari`'yla **birebir aynıydı** (AL-003: 1250=1250, ZK-006:
1000=1000, ZK-008: 750=750, TEK-005: 500=500 — hepsi "Yeni Müşteri"/"Kart
Kampanyası" türünde, gerçekte finansman ürünü bile değil). Bu,
`ner_extractor.py`'nin Bulgu 1'iyle birebir örtüşüyor — iki bağımsız
model de (GLiNER ve Qwen2.5) bu ayrımı yapamıyor, sistemik bir sınır.
Regex bu alanda zaten %100 F1 olduğu için (Sara'nın bağlam-kontrolü
düzeltmesi), `finansman_tutari` artık **hem NER'e hem LLM'e** hiç
sorulmuyor — `extraction/hybrid_pipeline.py`'nin "KAPSAM DIŞI ALANLAR"
listesine taşındı (`tahsis_ucreti` ile aynı kategori: regex zaten yeterli,
fallback yalnızca risk taşıyor).

**İkinci bulgu — vade_ay (aynı gün, ardışık ölçüm):** `finansman_tutari`
düzeltmesinden sonra Makro F1 79,46'ya çıktı ama hâlâ baz çizginin
(93,72) altındaydı; `vade_ay` F1'i 33,33'e düşmüştü. Kök neden: LLM'e
vade_ay sorulunca, "Vade Farksız 5 Aya Varan Taksit" gibi başlıklarda
taksit sayısını (5, 6, 3) vade_ay diye yazıyordu — Altın Veri Seti'nin
kendi bilinen kuralıyla çelişen tam olarak KT-006/AL-001/AL-002 ailesi.
`regex_extractor.py`'nin `RE_VADE` deseni bu bağlamı zaten bilerek
dışlıyordu (negatif lookahead ile); LLM'in aynı koruması yoktu. Çözüm:
`extraction/llm_extractor.py::_vade_aslinda_taksit_mi()` eklendi —
regex'in kendi kanıtlanmış taksit-tanıma deseninin (RE_TAKSIT_SAYISI)
sayıya ankorlanmış hali, iki motor arasında tutarlılık sağlıyor. Sonuç:
Makro F1 86,40'a çıktı, `vade_ay` F1'i 66,67'ye yükseldi.

**Kalan tek yanlış pozitif (AL-001) bir LLM hatası değil:** İncelendiğinde,
metinde gerçekten "Vade:\n6 aya kadar" diye yapılandırılmış bir alan
olduğu görüldü — ama bu, AL-001'in kendi içeriği değil, daha önce
belgelenmiş "sayfa kapsamı kirlenmesi" bulgusuyla (Albaraka'nın
`.searchContent` seçicisinin kardeş kampanya bloklarını da alması) aynı
kök nedenden, muhtemelen sızan bir kardeş kampanya alanı. Gold kaydının
kendi notu da ("sayfada vade ifadesi yok") bunu destekliyor. Bu, scraper/
veri tarafının bilinen bir sorunu — extraction katmanında düzeltilecek
bir şey yok, AL-001 zaten ekibin karar bekleyen kayıtları arasında.

**Üçüncü bulgu — dar makas (kullanıcının "sonuç eskiden yüksekti" sorusu
üzerine yapılan takip incelemesi):** `regex+NER` satırının Makro F1'i
(92,65) hâlâ regex-only'nin (93,72) altındaydı; tek fark `kar_payi_orani_
percent`'te (83,33→76,92). Regex-only'nin kendi yanlış pozitif listesiyle
karşılaştırıldığında, bu farkın kaynağı HF-005 kaydıydı — regex-only bu
kaydı hiç yanlış işaretlemiyordu, yalnızca NER eklenince ortaya çıkıyordu.
Gerçek metin: "...5.000 USD... hacmine kadar %0,1 dar makastan
yararlanabilir." GLiNER'in döndürdüğü varlık span'i yalnızca "%0,1" idi
(start/end konumlarıyla doğrulandı) — "makas" kelimesi span'in birkaç
karakter dışında kalıyordu, bu yüzden ham_deger üzerinde basit bir metin
kontrolü yetersizdi. `terminology/sozluk.json`'daki `dar_makas` kavramı
bunu zaten "kar_payi_orani ile karıştırılmamalı" diye işaretlemişti;
regex_extractor.py kendi bağlam-dışlama penceresiyle bunu doğru atlıyordu,
NER'in aynı koruması yoktu. Çözüm: `extraction/ner_extractor.py::
_dar_makas_baglaminda_mi()` eklendi — GLiNER'in start/end konumlarından
ham metindeki gerçek bağlam penceresine bakıyor (regex'in
`_ucret_baglaminda_mi`'siyle aynı ilke). **Sonuç: `regex+NER` artık
regex-only ile birebir eşit (Makro F1 93,72, 2 yanlış pozitif, +0,00)** —
NER katmanı ölçülebilir hiçbir net zarar üretmiyor. `regex+NER+LLM`
87,47'ye çıktı; kalan fark artık tamamen LLM'e ait ve büyük kısmı zaten
bilinen AL-001 kirlenmesinden geliyor.

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

---

## Güncelleme — 11 Ağustos 2026 (C2/C3/C4: kör alanlar + kalan 4 karar)

Sara'nın durum raporundaki C bloğunun geri kalanı ele alındı: `taksit_sayisi`/
`erteleme_suresi_ay` alanlarının neredeyse hiç ölçülememesi (C2/C3) ve
motorun tespit ettiği son 4 tutarsızlığın gold tarafında karara bağlanması
(C4).

### C2/C3 — kör alanlar dolduruldu

Altın Veri Seti'nin 58 gerçek kaydı tek tek tarandı: `kampanya_avantaji`
metninde **açıkça bir sayı olarak geçen ama alana işlenmemiş** 10 değer
bulundu (9 `taksit_sayisi`, 1 `erteleme_suresi_ay`) — hepsi kaydın
kendi metninden okundu, dışarıdan yeni bilgi eklenmedi:

| Kayıt | Alan | Değer | Kaynak ifade |
|---|---|---|---|
| KT-001 | taksit_sayisi | 6 | "6 taksite kadar avantajlı kâr payı oranı" |
| KT-004 | taksit_sayisi | 3 | "vade farksız 3 taksit" |
| VK-001 | taksit_sayisi | 3 | "vade farksız 3 taksit" |
| VK-002 | taksit_sayisi | 3 | "vade farksız 3 taksit" |
| VK-003 | taksit_sayisi | 5 | "vade farksız 5 taksit" |
| VK-006 | taksit_sayisi | 5 | "vade farksız 5 taksit" |
| ZK-003 | taksit_sayisi | 4 | "Bankkart kredi kartıyla 4 taksite bölünüyor" |
| DK-006 | taksit_sayisi | 9 | kademeli sistem, gold'un kendi kuralıyla ("en üst dilim alındı") tutarlı |
| DK-007 | taksit_sayisi | 3 | "3 aya varan taksit" (KT-006 emsaliyle aynı "N aya varan" kuralı) |
| TF-001 | erteleme_suresi_ay | 3 | ham metinde doğrulandı: "ilk taksit için 3 aya varan ödemesiz dönem hakkı tanınacaktır" |

Her satıra `notlar` alanında `[11 Ağu] ... eklendi` şeklinde tarihli bir not
düşüldü (KT-006'nın 9 Ağustos'taki `vade_ay->taksit_sayisi` notuyla aynı
konvansiyon). İki kayıt bilerek **dokunulmadan** bırakıldı:

- **KT-003**: "ödemesiz dönem" geçiyor ama süre sayı olarak verilmemiş,
  üstelik kaynak sayfa artık Kuveyt Türk sitesinde yok (bkz. C1) —
  doğrulanamaz.
- **ZK-004**: "2-4 taksitli işlemlerde +8 ek taksit" — kampanya taban
  taksidi mi (2-4) yoksa kendi sağladığı ek taksidi mi (8) temsil etmeli,
  gerçek bir belirsizlik; ekiple konuşulmadan doldurulmadı.

**Etki:** `taksit_sayisi` desteği 1'den 6'ya çıktı (regex-only F1
83,33 → **100,00**), `erteleme_suresi_ay` ilk kez ölçülebilir hale geldi
(destek 0 → 1, F1 100,00). Regex-only Makro F1: 93,72 → **94,62**.

### C4 — kalan 4 karar

Ölçümde kalan tüm hatalar tam olarak Sara'nın işaret ettiği 4 kayda
denk düştü. Yağmur'a durumla birlikte sunuldu, kararlar:

1. **KT-006 `kar_payi_orani`** — "Vade Farksız 5 Aya Varan Taksit" aynı
   yapıdaki AL-002/AL-005/TOM-002'de gold zaten `0`; KT-006 tek başına
   "belirtilmemiş" idi. **Karar: tutarlılık için `0` yapıldı**, `alan_belirtilmemis`
   listesinden çıkarıldı.
2. **AL-001 `taksit_sayisi`** — kampanya iki bölümlü (40.000 TL'lik Pratik
   Finansman Kart kısmı = 4 taksit, 100.000 TL'lik kredi kartı kısmı = 6
   taksit); `finansman_tutari` zaten ilk bölümü (40.000) esas alıyordu ama
   `taksit_sayisi` ikinci bölümün değerini (6) taşıyordu — alanlar arası
   tutarsızlık. **Karar: `4` yapıldı**, alanlar artık aynı alt kampanyaya
   (Pratik Finansman Kart) işaret ediyor.
3. **DK-002 `odul_miktari`** — ilk değerlendirmede DK-002'nin (davet başına
   0,1 gram) KT-007'nin (750 TL toplam) "politikasıyla çelişebileceği"
   düşünülmüştü. **11 Ağustos'ta yeniden incelendi:** KT-007'nin 750 TL'si
   aslında TEK bir yeni müşterinin İKİ farklı bileşeninin toplamı (500 TL
   harcama iadesi + 250 TL anket ödülü) — DK-002'deki gibi "birim ödül ×
   davet sayısı" çarpımı DEĞİL. Yani gerçek bir politika çelişkisi yoktu,
   ilk karşılaştırma yanlış eşleştirmeydi. **Karar: DK-002 (0,1 gram)
   olduğu gibi doğru, dokunulmadı.**
4. **TF-001 `kar_payi_orani`** — yanlış pozitif (`0.0`), sayfanın ortasında
   geçen tamamen farklı bir ürünün ("Yedek Hesap") "Kâr paysız 2.500 TL'ye
   kadar" ifadesinden geliyor; AL-001'deki sayfa-sonu kirlenmesinden farklı
   bir örüntü, şu an yalnızca bu 1 kayıtta görülüyor. **Karar: kod
   değiştirilmedi**, bilinen dar kapsamlı bir sınırlama olarak burada
   belgelendi (`preprocessing/kapsam.py` bilinçli olarak dar tutulmuş —
   tek örnek için yeni bir genel kural yazmak riskli).

**Sonuç:** KT-006 ve AL-001 düzeltmeleri sonrası regex-only Makro F1
94,62 → **98,28**e çıktı. C4'ün 4 kararı da artık kapalı: KT-006/AL-001
düzeltildi, DK-002 doğru olduğu teyit edildi (dokunulmadı), TF-001
bilinen sınırlama olarak belgelendi (dokunulmadı). Kalan tek hata (DK-002
— zaten doğru) ve kalan tek yanlış pozitif (TF-001 — bilinen sınırlama)
bilinçli olarak böyle bırakıldı, çözülmemiş değil.

### C1 — Altın Veri Seti tazelik durumu (yeniden ölçüldü)

Tüm bankalar canlı sitelerden yeniden tarandı (C5 ile birlikte, delta
kontrollü — yalnızca değişen/yeni sayfalar işlendi) ve `gold_eslesme.py`
ile 58 gerçek kayıt karşılaştırıldı:

- **36/58 hâlâ scraper önbelleğinde eşleşiyor** — Sara'nın 28 Temmuz
  rakamıyla birebir aynı; 11 gün sonra durum kötüleşmemiş.
- **22/58 artık hiçbir raw_data dosyasıyla eşleşmiyor** (%38 — Sara'nın
  tahmini %45'e yakın, biraz daha iyi çıktı).
- Banka bazında en kırılgan: **Vakıf Katılım (1/8 canlı)**, **Türkiye
  Finans (1/7 canlı)** — kampanyaları hızlı rotasyona giriyor.

**Önemli metodolojik not:** "raw_data'da eşleşiyor" ≠ "şu an sitede
canlı". Scraper eski dosyaları hiç silmiyor (bilinçli tasarım, delta
kontrolü için), bu yüzden bir kampanya siteden kalksa bile eski taraması
diskte kalmaya devam ediyor. Somut örnek: **T.O.M. Katılım** — raw_data'da
3 dosya var ve `gold_eslesme.py` üçünü de "canlı" sayıyor, ama sitenin
kendisi (`tombank.com.tr/kampanyalar.html`, doğrudan kontrol edildi,
11 Ağustos) artık yalnızca **1** kampanya (TOM-002, "Özel Okul
Ödemelerinde 10 Taksit") gösteriyor — diğer ikisi (Restoran %10 iade,
Market 1.000 TL iade) siteden kaldırılmış. Yani 36/58 rakamı gerçek
canlı-kapsamın üst sınırı, tam doğrulaması tek tek canlı kontrol
gerektirir (bu, ekibin ekran görüntülü manuel doğrulama sürecinin
konusu).

### C6 — T.O.M. Katılım örneklem yetersizliği: veri kısıtı, motor hatası değil

`scraper/config/bankalar.json` zaten belgeliyordu: T.O.M. Katılım'ın
kampanya sayfası tek bir HTML sayfasında (accordion panelleri) yayınlanıyor.
11 Ağustos'ta doğrudan kontrol edildi: sayfada artık yalnızca **1**
accordion paneli var (`accordion-item` sayısı canlı HTML'de 1). Yani
"hedef 5-8, mevcut 3" değerlendirmesi bile artık iyimser — banka o an
için yalnızca 1 kampanya yayınlıyor. Bu, scraper'ın eksikliği değil,
bankanın kendi sitesinin içerik kısıtı; ek tarama/kod değişikliğiyle
çözülemez. T.O.M. Katılım örneklemi, yalnızca banka zamanla yeni
kampanyalar yayınladıkça büyüyecek.

---

## Güncelleme — 17 Ağustos 2026 (diyakritiksiz yazım: sessiz alan kaybı)

`POST /cikar` ucundan uca denenirken bulundu: `regex_extractor.py`'nin
**kelime tabanlı** alanları, Türkçe diyakritik kullanılmadan yazılmış
metinde **sessizce boş dönüyordu**. Sayısal alanlar (rakam/sembol
eşleşmesi) etkilenmiyordu. Aynı cümlenin iki yazımı:

| alan | `...kar payi orani... 3 ay odemesiz donem` | `...kâr payı oranı... 3 ay ödemesiz dönem` |
|---|---|---|
| `erteleme_suresi_ay` | **None** | 3 |
| `hedef_kitle` | **None** | Yeni müşteri |
| `kampanya_turu` | **None** | Yeni Musteri Kampanyasi |
| `kampanya_avantaji` | eksik | tam |

### Önce ölçüldü: üretim verisi temiz, risk yapıştırma yolunda

`scraper/raw_data` altındaki **263 ham metnin tamamı** tarandı:

- **0/263 belgede** diyakritik yoğunluğu %1'in altında — yani korpusta
  kodlama kaynaklı ASCII'ye katlanmış (mojibake) tek bir belge **yok**.
- Anahtar kelimelerin ASCII varyantları için bulunan az sayıdaki eşleşme
  (`arac` 35, `katilim` 13, `ihtiyac` 4) tek tek incelendi: hepsi
  **doğru yazılmış kelimelerin alt dizgesi** (`aracılığıyla`,
  `ihtiyacınız`) ya da e-posta adresi. Gerçek diyakritiksiz yazım değil.

**Sonuç:** üretim verisinde şu an alan kaybetmiyoruz. Açık olan yüzey,
kullanıcıyı serbest metin **yapıştırmaya** davet eden yeni `POST /cikar`
ucu ve MetinAnalizi ekranı — Türkçe karakter kullanmadan yazan biri
alanların kaybolduğunu göremezdi. (Ayrıca taranan PDF/OCR metinlerinde
aksan kaybı bilinen bir sorundur, bkz. `ner_extractor.py` Bulgu 4.)

### Çarpma yarıçapı büyük

Aynı 263 belgenin her biri ASCII'ye katlanıp yeniden çıkarım yapıldı;
**87 belge (%33) en az bir alanını kaybediyor**:

| alan | kaybeden belge |
|---|---|
| `kampanya_bitis` | 60 |
| `hedef_kitle` | 15 |
| `kampanya_baslangic` | 13 |
| `erteleme_suresi_ay` | 4 |
| `kampanya_turu` | 4 |
| `odul_miktari` / `odul_birimi` | 1 |

Yani en büyük yüzey, ilk raporlanan dört alan **değil**, **tarih
alanları**: `RE_TARIH`'in ay adları (Şubat/Mayıs/Ağustos/Eylül/Kasım/
Aralık) diyakritikli yazılmıştı.

### Çözüm

Depoda bu desen zaten çözülmüştü (`agent/intent.py::turkce_ascii_katla`,
`terminology/genisletme.py::_turkce_kucult`, `TerminolojiSozlugu.jsx`);
aynısı çıkarım katmanına taşındı — `extraction/normalizer.py`'ye
`turkce_ascii_katla` / `turkce_ascii_kucult` eklendi.

`regex_extractor.py`'de **hem metin hem desen** aynı haritadan geçirilir
(`_katlanmis_derle`, `_katla_hepsi`), böylece desenler doğal Türkçe
yazımıyla okunabilir kalır ama eşleşme yazımdan bağımsız olur.

Katlama **uzunluk korur** (`str.translate` 1:1 — bu yüzden `str.lower()`
kullanılmaz, `'İ'.lower()` iki karakter üretip offset kaydırırdı). Bu
sayede eşleşme offset'leri ham metinde aynı yeri gösterir ve **kanıt izi
(`_izler`) ham metinden kesilir** — kullanıcıya kendi yazdığı metin
gösterilir (`"Dosya masrafı alınmaz"`, `"masrafi alinmaz"` değil).
Düz ASCII `I` harfine dokunulmaz (hem `I` hem `ı` olabilir).

### Regresyon: makro F1 değişmedi

Katlamanın yeni yanlış pozitif üretme riski vardı (ör. "kâr" ile "kar"
karışması). `python -m scraper.scripts.extraction_accuracy` öncesi/sonrası:

| | önce | sonra |
|---|---|---|
| Makro P | %97,34 | %97,34 |
| Makro R | %99,38 | %99,38 |
| **Makro F1** | **%98,28** | **%98,28** |

Alan bazlı P/R/F1 tablosunun tamamı ve bilinen iki hata (DK-002 ödül
miktarı, TF-001 yanlış pozitif) **birebir aynı** kaldı. "kâr" çakışması
gerçekleşmedi, çünkü `RE_KAR_PAYI_*` desenleri zaten `k[aâ]r` yazıp
ayrıca `pay`/`oran` bağlam kelimesini zorunlu kılıyordu.

## Güncelleme — 20 Ağustos 2026 (kâr payı oranı tabloları: TF-001 yeniden açıldı)

Teknik toplantıda gelen soru üzerine ("kâr payı oranı çoğu kampanya
sayfasında yok, bankaların kendi hesaplama araçlarında/tablolarında var —
buradan çekmek meşru mu?"): `scraper/scripts/tablo_isle.py` (HTML
`<table>` → yapılandırılmış JSON, Rehber Bölüm 18) **zaten yazılmıştı**
ama hiçbir extraction dosyası `tablolar` alanını okumuyordu — klasik
"yazıldı ama bağlanmadı" örüntüsü. 300 ham kayıt tarandı: **15 kayıtta**
dolu bir `tablolar` alanı var, bunlardan yalnızca **3 sayfada** (Albaraka
`dijital-musterilere-ozel-pratik-finansman-kart`, Türkiye Finans
`banka-calisanlarina-` ve `kamu-calisanlarina-ozel-ihtiyac-finansmani`)
gerçekten VADE+ORAN sütunlu bir "Kâr Payı Oranları" tablosu var — geri
kalan 12'si ödül/referans kademe tabloları (kâr payı oranıyla ilgisi yok).

**Neden tek sayıya indirgenmedi:** ölçüldü — Albaraka'nın tablosunda AYNI
vade diliminde FARKLI tutar dilimine göre farklı oran var (`%0` ve `%3,95`
ikisi de "1-6 ay vade"); Türkiye Finans'ın sayfasında AYNI sayfada
"sigortalı"/"sigortasız" için TAMAMEN AYRI iki oran seti var. Herhangi bir
otomatik "en düşük"/"ilk satır" seçimi UYDURMA bir karar olurdu (rapor
Bölüm 5.7/15). Bu yüzden `extraction/tablo_extractor.py::
oran_tablolarini_sec()` tabloyu OLDUĞU GİBİ (satır/sütun korunarak) yeni
bir `kar_payi_tablosu` sütununa taşır (bkz. `alembic/versions/
f5f4763fa380_...py`), `kar_payi_orani_percent`'e HİÇ dokunmaz. API'de
(`CampaignRecord.kar_payi_tablosu`) ve dashboard'da
(`KarPayiTablosuKarti.jsx`) kaynak tablosu şeffafça gösterilir.

### TF-001 yanlış pozitifi yeniden açıldı — artık 1 değil 2 örnek var

`kar_payi_tablosu`'nu doldurmak için tüm kayıtlar yeniden tarandığında,
17 Ağustos'ta "bilinen sınırlama, TEK örnek için genel kural riskli" diye
**bilinçli olarak düzeltilmeyen** TF-001 `kar_payi_orani_percent=0.0`
yanlış pozitifinin (bkz. yukarıdaki "C4" bölümü) aslında **2. bir
örneği** olduğu ölçüldü: Türkiye Finans'ın `kamu-calisanlarina-ozel-
ihtiyac-finansmani` sayfası da AYNI "Kâr paysız 2.500 TL'ye kadar Yedek
Hesap finansman desteğinden yararlanabilirsiniz." cümlesinden aynı
şekilde etkileniyordu (id=158/165). İkinci örnek, "tek kayıt için genel
kural riskli" gerekçesini geçersiz kıldı — artık dar kapsamlı, ölçülmüş
bir düzeltme yazıldı:

`extraction/regex_extractor.py::_ikincil_urun_baglaminda_mi` — "Yedek
Hesap" **özel adıyla** sınırlı bir bağlam guard'ı (`_ucret_baglaminda_mi`
ile aynı desen, bkz. `tests/test_baglam_guardlari.py::
test_ikincil_urundeki_kar_paysiz_ifadesi_ANA_orani_SIFIRLAMAZ`). Genel
"kar paysiz" kalıbı **daraltılmadı** — yalnızca bu bilinen ikincil ürün
adı yakınında geçtiğinde devre dışı kalır; doğrudan ana ürünü anlatan
"kar paysiz" ifadeleri (AL-002/AL-005/AL-006/VK-001/VK-002/VK-003/VK-006/
KT-006) etkilenmedi (regresyon: `tests/test_baglam_guardlari.py` ve
`tests/test_regex_extractor*.py` — 59/59 geçti).

### Regex-only fallback'in kendi sınırı — düzeltilmedi, belgelendi

Guard'dan sonra TF-001'in DÜZ METİN (regex-only, `extraction_accuracy.py`
ölçümü) tahmini `0.0` yerine `5.36` gibi BAŞKA bir hatalı sayıya
kayıyor — `get_text()`'in düzleştirdiği tablo hücrelerinden
(`RE_KAR_PAYI_GENEL`, güven 0.6 fallback) geliyor, tam olarak
`tablo_isle.py`'nin modül başlığında tarif ettiği "hangi sayının hangi
ürüne ait olduğunu kaybetme" sorunu. Bu, ölçülen tek regex-only Makro
F1'i (%98,28) **değiştirmiyor** — hâlâ `kar_payi_orani_percent` alanında
6 kayıttan 1 yanlış pozitif var, yalnızca hangi sayının üretildiği
değişti. Regex-only katman **BİLİNÇLİ OLARAK GPU/LLM'siz, basit bir
son çare fallback'tir** (rapor Bölüm 8) — bu katmanın kendisini
tablo-farkında hale getirmek yeni, dar kapsamlı olmayan bir genel kural
gerektirir; tek bir kayıt/örüntü için riskli (17 Ağustos'taki aynı
gerekçe). **Gerçek düzeltme üretim yolunda (DB'yi dolduran kod) zaten
var:**

`extraction/regex_ile_zenginlestir.py::zenginlestir()` — bir sayfada
`kar_payi_tablosu` bulunduysa VE hibrit boru hattının
`kar_payi_orani_percent` tahmini `KILITLEME_GUVEN_ESIGI`nin (0.8) altında
kaldıysa, alan **boş bırakılır** (DB'ye yazılmaz) — çünkü gerçek (vadeye/
sigortaya göre değişen) oranlar zaten `kar_payi_tablosu`'nda doğru
duruyor; düşük güvenli TEK sayı tahminine güvenmenin hiçbir faydası yok,
yalnızca zararı var. Regresyon kilidi: `tests/
test_regex_ile_zenginlestir.py::
test_tablolu_sayfada_dusuk_guvenli_kar_payi_tahmini_guvensiz`.

Üretim DB'sinde bu guard'dan ÖNCE zaten yanlış yazılmış olan 3 satır
(id=155/158/165 — bu ortamın kendi ID'leri, taşınabilir değil) elle
`None`'a sıfırlandı ve script yeniden çalıştırıldı; artık ya doğru bir
yüksek güvenli değer ya da dürüst `None` + dolu `kar_payi_tablosu`
taşıyorlar.

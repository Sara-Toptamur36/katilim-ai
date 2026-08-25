# Altın Veri Seti — Etiket İnceleme Listesi

*Bu dosya üretilmiştir; elle düzenlemeyin.*
*Yeniden üretmek için: `python -m gold_dataset.etiket_celiskisi_raporu`*

Bu liste **motorun hatalarını değil**, motor ile altın veri setinin
ÇELİŞTİĞİ yerleri gösterir. Her satırda motorun bulduğu değer ve o değeri
hangi metin parçasından çıkardığı (kanıt spanı) var — böylece kaynak
sayfayı açmadan karar verilebilir. Çelişkilerin bir kısmında **gold**
haklı, bir kısmında **motor**.

---

## 1. `vade farksız` — aynı kanıt, iki farklı etiket (EN ÖNCELİKLİ)

Tek başına en büyük metrik kaldıracı. Korpusta `vade farksız` geçen
kayıtların **1'inde** gold `kar_payi_orani = 0` diyor,
**49'ünde** ise `belirtilmemiş` diyor.

**`0` etiketlenmiş (1):** `AL-001`

**`belirtilmemiş` etiketlenmiş (49):** `KT-004`, `KT-006`, `AL-002`, `AL-005`, `AL-006`, `DK-001`, `DK-006`, `TOM-002`, `KT-008`, `AL-010`, `KT-009`, `KT-010`, `AL-012`, `KT-015`, `TOM-005`, `TOM-006`, `KT-018`, `TOM-007`, `DK-011`, `KT-019`, `KT-023`, `TEK-022`, `DK-016`, `TEK-023`, `KT-025`, `KT-027`, `DK-023`, `DK-025`, `KT-034`, `DK-029`, `KT-043`, `DK-036`, `KT-044`, `KT-045`, `TEK-044`, `TEK-045`, `TEK-048`, `KT-050`, `KT-053`, `TEK-052`, `KT-054`, `TEK-054`, `KT-057`, `TEK-056`, `KT-058`, `KT-059`, `TEK-058`, `TEK-061`, `TEK-062`

**Karar verilmesi gereken:** Katılım bankacılığında *vade farkı*,
geleneksel faizin karşılığıdır; *vade farksız* olması o işlem için oranın
sıfır olduğu anlamına gelir. Motor bu yorumu benimsiyor ve
`terminology/sozluk.json` içindeki `sifir_oran_ifadesi` kavramıyla
tutarlı davranıyor. İki seçenek de savunulabilir — ama **biri seçilip**
**tüm kayıtlara birden** uygulanmalı:

- **(A) `vade farksız` ⇒ `0`.** İkinci grup (49 kayıt) `0` yapılır.
  Beklenen etki: yanlış pozitif 91 → ~42, kâr payı oranı F1
  belirgin şekilde yükselir.
- **(B) `vade farksız` ⇒ `belirtilmemiş`.** Birinci grup (1 kayıt)
  boşaltılır ve `regex_extractor.py` içindeki `RE_VADE_FARKSIZ` kolu kaldırılır.

> **Ayrı bir sonucu var:** bir *kart* kampanyasının `kar_payi_orani = 0`
> taşıması, `comparison/compare_engine.py` içindeki `en_dusuk_kar_payi`
> sıralamasını (ASC) kazanmasına yol açıyor — konut finansmanının %1,87'si
> bir taksit kampanyasının 0'ına yeniliyor. Ödül birimleri için zaten var
> olan `odul_birimi_tekil_mi()` korumasının kâr payı ekseninde karşılığı yok.

---

## 2. Motorun değer bulduğu, gold'un `belirtilmemiş` dediği alanlar

**Kanıt spanına bakın:** ifade metinde gerçekten geçiyorsa gold eksik,
geçmiyorsa motor uyduruyor.

| Kayıt | Alan | Motorun bulduğu | Kanıt spanı | Güven |
|---|---|---|---|---|
| `DK-008` | `taksit_sayisi` | 6 | `6 Aya Varan Taksit` | 0.85 |
| `DK-009` | `taksit_sayisi` | 6 | `6 Aya Varan Taksit` | 0.85 |
| `DK-016` | `taksit_sayisi` | 6 | `6 Aya Varan Taksit` | 0.85 |
| `DK-023` | `taksit_sayisi` | 9 | `9 Aya Varan Taksit` | 0.85 |
| `DK-029` | `taksit_sayisi` | 12 | `12 Aya Varan Taksit` | 0.85 |
| `DK-034` | `taksit_sayisi` | 12 | `12 Aya Varan Taksit` | 0.85 |
| `HF-008` | `finansman_tutari` | 100.0 | `üst limiti 100 TL` | 0.75 |
| `HF-008` | `odul_birimi` | TL | `?` | 0 |
| `HF-008` | `odul_miktari` | 1.0 | `1 TL kazanırsınız` | 0.8 |
| `KT-001` | `vade_ay` | 3 | `3 ay vadeli` | 0.85 |
| `KT-017` | `taksit_sayisi` | 12 | `12 aya varan taksit` | 0.85 |
| `KT-018` | `erteleme_suresi_ay` | 2 | `2 ay ertelemeli` | 0.85 |
| `KT-018` | `finansman_tutari` | 100000.0 | `100.000 TL’ye Kadar` | 0.75 |
| `KT-018` | `kar_payi_orani` | 1.99 | `%1,99` | 0.9 |
| `KT-018` | `odul_birimi` | TL | `?` | 0 |
| `KT-018` | `odul_miktari` | 10000.0 | `10.000 TL’ye varan indirim` | 0.8 |
| `KT-018` | `vade_ay` | 48 | `48 aya varan vade` | 0.85 |
| `KT-019` | `odul_birimi` | Mil | `?` | 0 |
| `KT-019` | `odul_miktari` | 10000.0 | `10.000 Mil'e varan hediye` | 0.8 |
| `KT-019` | `taksit_sayisi` | 5 | `5 taksit` | 0.85 |
| `KT-023` | `finansman_tutari` | 250000.0 | `10.000 TL - 250.000 TL aras` | 0.85 |
| `KT-032` | `finansman_tutari` | 500000.0 | `300 TL - 500.000 TL aras` | 0.85 |
| `KT-036` | `kar_payi_orani` | 10.0 | `%10` | 0.6 |
| `KT-036` | `vade_ay` | 9 | `9 aya varan vade` | 0.85 |
| `KT-043` | `taksit_sayisi` | 3 | `3 aya varan taksit` | 0.85 |
| `KT-044` | `taksit_sayisi` | 5 | `5 Taksit` | 0.85 |
| `TEK-044` | `taksit_sayisi` | 5 | `5 aya varan taksit` | 0.85 |
| `TEK-052` | `taksit_sayisi` | 9 | `9 Taksit` | 0.85 |
| `TEK-056` | `taksit_sayisi` | 12 | `12 Aya Varan Taksit` | 0.85 |
| `TEK-058` | `taksit_sayisi` | 6 | `6 Aya Varan Taksit` | 0.85 |
| `TF-002` | `finansman_tutari` | 14999.0 | `10.000 TL – 14.999 TL aras` | 0.85 |
| `TF-013` | `kar_payi_orani` | 2.0 | `%2` | 0.6 |
| `TOM-001` | `finansman_tutari` | 3500.0 | `3.500 TL'ye kadar` | 0.75 |
| `TOM-007` | `taksit_sayisi` | 6 | `6 taksit` | 0.85 |
| `TOM-008` | `odul_birimi` | TL | `?` | 0 |
| `TOM-008` | `odul_miktari` | 300.0 | `300 TL iade` | 0.8 |
| `TOM-010` | `odul_birimi` | TL | `?` | 0 |
| `TOM-010` | `odul_miktari` | 250.0 | `250 TL iade` | 0.8 |
| `ZK-030` | `taksit_sayisi` | 6 | `6 taksit` | 0.85 |
| `ZK-033` | `taksit_sayisi` | 5 | `5 taksit` | 0.85 |
| `ZK-036` | `odul_birimi` | TL | `?` | 0 |
| `ZK-036` | `odul_miktari` | 1000.0 | `1.000 TL indirim` | 0.8 |

**Okuma kılavuzu (25 Ağustos 2026'da DÜZELTİLDİ):** ilk sezgi
"güven 0.85 üstü = gold eksik" idi - bu satırlar tek tek kaynakla
doğrulandığında YANLIŞ çıktı. Bu korpusta yüksek güven çoğunlukla
motorun BAĞLAM DIŞI bir sayıyı (üst sınır, eşik/tavan, başka bir
kampanyanın başlığı, site menüsü) doğru alanmış gibi bulduğu anlamına
geliyor. Önce kaydın KENDİ `notlar` alanına bakın - konu zaten
`BELİRSİZ <alan>: ...` diye açıklanmışsa gold kasıtlı ve doğrudur,
motora güvenmeyin. Kanıt spanı sayfanın gövdesinde değil bir menü
başlığında/başka kampanyada duruyorsa (ör. "Kuveyt Türk Kampüs'e
Gelenlere Toplamda 13.500 TL Hediye!" gibi bir link satırı), bu
scraper'ın içerik sınırlama hatasıdır - alanı DOLDURMAYIN.

---

Ölçümün kendisi: `python -m scraper.scripts.extraction_accuracy`

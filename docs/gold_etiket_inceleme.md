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
kayıtların **7'inde** gold `kar_payi_orani = 0` diyor,
**13'ünde** ise `belirtilmemiş` diyor.

**`0` etiketlenmiş (7):** `AL-001`, `AL-002`, `AL-005`, `AL-006`, `DK-001`, `DK-006`, `TOM-002`

**`belirtilmemiş` etiketlenmiş (13):** `KT-004`, `KT-006`, `KT-008`, `VK-009`, `AL-010`, `KT-009`, `VK-010`, `KT-010`, `AL-012`, `KT-015`, `TOM-004`, `TOM-005`, `TOM-006`

**Karar verilmesi gereken:** Katılım bankacılığında *vade farkı*,
geleneksel faizin karşılığıdır; *vade farksız* olması o işlem için oranın
sıfır olduğu anlamına gelir. Motor bu yorumu benimsiyor ve
`terminology/sozluk.json` içindeki `sifir_oran_ifadesi` kavramıyla
tutarlı davranıyor. İki seçenek de savunulabilir — ama **biri seçilip**
**tüm kayıtlara birden** uygulanmalı:

- **(A) `vade farksız` ⇒ `0`.** İkinci grup (13 kayıt) `0` yapılır.
  Beklenen etki: yanlış pozitif 34 → ~21, kâr payı oranı F1
  belirgin şekilde yükselir.
- **(B) `vade farksız` ⇒ `belirtilmemiş`.** Birinci grup (7 kayıt)
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
| `HF-008` | `odul_birimi` | TL | `?` | 0 |
| `HF-008` | `odul_miktari` | 1.0 | `1 TL kazanırsınız` | 0.8 |
| `KT-001` | `vade_ay` | 3 | `3 ay vadeli` | 0.85 |
| `KT-017` | `taksit_sayisi` | 12 | `12 aya varan taksit` | 0.85 |
| `TF-002` | `finansman_tutari` | 14999.0 | `10.000 TL – 14.999 TL aras` | 0.85 |
| `TF-004` | `kar_payi_orani` | 0.0 | `%0` | 0.9 |
| `TF-007` | `finansman_tutari` | 10000.0 | `10.000 TL’ye kadar` | 0.75 |
| `TOM-004` | `taksit_sayisi` | 12 | `12 Taksit` | 0.85 |
| `VK-009` | `taksit_sayisi` | 5 | `5 Taksit` | 0.85 |
| `VK-010` | `odul_birimi` | TL | `?` | 0 |
| `VK-010` | `odul_miktari` | 200.0 | `200 TL İndirim` | 0.8 |
| `VK-010` | `taksit_sayisi` | 5 | `5 Taksit` | 0.85 |
| `ZK-009` | `odul_birimi` | Bankkart Lira | `?` | 0 |
| `ZK-009` | `odul_miktari` | 2000.0 | `2000 TL Bankkart Lira` | 0.8 |
| `ZK-011` | `taksit_sayisi` | 4 | `4 Taksit` | 0.85 |
| `ZK-014` | `odul_birimi` | TL | `?` | 0 |
| `ZK-014` | `odul_miktari` | 3000.0 | `3.000 TL’ye Varan İndirim` | 0.8 |
| `ZK-015` | `odul_birimi` | Bankkart Lira | `?` | 0 |
| `ZK-015` | `odul_miktari` | 500.0 | `500 TL Bankkart Lira` | 0.8 |

**Okuma kılavuzu:** güven `0.85` üstünde metin ifadeyi *açıkça* içerir
(ör. `5 Taksit`, `6 Aya Varan Taksit`) — bunlarda büyük olasılıkla **gold**
**eksik**. Güven `0.6` olanlar düşük güvenli fallback'ten gelir ve
**motorun yanılma ihtimali yüksektir**.

---

Ölçümün kendisi: `python -m scraper.scripts.extraction_accuracy`

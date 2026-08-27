# EVREN FULL PIPELINE BENCHMARK RAPORU

**Tarih:** 2026-08-27 03:04:41
**Toplam Golden Kayıt:** 302
**Canlı Kayıt Sayısı:** 291

---

## 1. PIPELINE PERFORMANS TABLOSU

| Pipeline | TP | FP | FN | Precision | Recall | F1 |
|----------|----|----|----|-----------| -------|-----|
| Regex | 708 | 38 | 509 | 94.91% | 58.18% | 72.14% |
| Regex + NER | 711 | 49 | 506 | 93.55% | 58.42% | 71.92% |
| Regex + NER + EVREN | 760 | 58 | 457 | 92.91% | 62.45% | 74.69% |
| Final | 992 | 65 | 225 | 93.85% | 81.51% | 87.25% |

---

## 2. AŞAMA KATKILARI

| Aşama | Yeni Doğru Alan | Eklenen FP | Toplam TP | Çağrı Sayısı |
|-------|-----------------|-----------|-----------|--------------|
| Regex | 708 | 38 | 708 | - |
| NER | +3 | +11 | 711 | 54 |
| EVREN | +49 | +9 | 760 | 112 |

---

## 3. EVREN KATKI ANALİZİ

**Toplam EVREN Çağrısı:** 112
**Yeni Doğru Alan:** 49
**Yanlış Alan:** 9
**Recovery Örnekleri (Regex+NER bulamadı, EVREN buldu):** 38

### EVREN Recovery Örnekleri

Regex ve NER'in bulamadığı ancak EVREN'in bulduğu alanlar:

- [ZK-004] `hedef_kitle` = `Belirli segment` (GT: `Belirli segment`)
- [TOM-002] `hedef_kitle` = `Belirli segment` (GT: `Belirli segment`)
- [ZK-009] `hedef_kitle` = `Belirli segment` (GT: `Belirli segment`)
- [ZK-010] `hedef_kitle` = `Belirli segment` (GT: `Belirli segment`)
- [ZK-012] `hedef_kitle` = `Belirli segment` (GT: `Belirli segment`)
- [ZK-013] `hedef_kitle` = `Belirli segment` (GT: `Belirli segment`)
- [ZK-014] `hedef_kitle` = `Belirli segment` (GT: `Belirli segment`)
- [ZK-015] `hedef_kitle` = `Belirli segment` (GT: `Belirli segment`)
- [ZK-017] `hedef_kitle` = `Belirli segment` (GT: `Belirli segment`)
- [TOM-006] `hedef_kitle` = `Belirli segment` (GT: `Belirli segment`)

---

## 4. NER KATKI ANALİZİ

**Toplam NER Çağrısı:** 54
**Yeni Doğru Alan:** 3
**Yanlış Alan:** 11

---

## 5. PERFORMANS

**Toplam Süre:** 1164.8 saniye
**İlk Kayıt (Cold Start):** 54746.9 ms
**Ortalama Kayıt Başı:** 3865.8 ms

---

## 6. FALSE POSITIVE ANALİZİ

### Regex + NER + EVREN (58 FP)

**Kaynak: unknown** (33 FP)
- [TF-002] `finansman_tutari` = `14999.0`
- [TF-003] `odul_miktari` = `11000.0`
- [TOM-001] `finansman_tutari` = `3500.0`
- [HF-008] `odul_miktari` = `1.0`
- [HF-008] `finansman_tutari` = `100.0`

**Kaynak: regex** (25 FP)
- [TF-002] `kampanya_bitis` = `2026-12-31`
- [TEK-005] `kampanya_bitis` = `2026-08-31`
- [KT-017] `taksit_sayisi` = `12`
- [KT-018] `kar_payi_orani_percent` = `1.99`
- [KT-018] `hedef_kitle` = `Yeni müşteri`

---

## 7. FALSE NEGATIVE ANALİZİ (En Çok Kaçırılan Alanlar)

**Toplam FN:** 225

### `hedef_kitle` (117 FN)

- [KT-005] Beklenen: `Yeni müşteri`, Bulunan: `None`
- [KT-007] Beklenen: `Yeni müşteri`, Bulunan: `None`
- [AL-001] Beklenen: `Yeni müşteri`, Bulunan: `None`

### `kampanya_turu` (65 FN)

- [KT-001] Beklenen: `Finansman Kampanyasi`, Bulunan: `Yeni Musteri Kampanyasi`
- [KT-004] Beklenen: `Ihtiyac Finansmani Kampanyasi`, Bulunan: `Finansman Kampanyasi`
- [KT-007] Beklenen: `Yeni Musteri Kampanyasi`, Bulunan: `None`

### `kampanya_bitis` (9 FN)

- [VK-008] Beklenen: `2026-11-30`, Bulunan: `None`
- [VK-009] Beklenen: `2029-12-31`, Bulunan: `None`
- [VK-010] Beklenen: `2026-12-31`, Bulunan: `None`

### `taksit_sayisi` (8 FN)

- [AL-001] Beklenen: `6`, Bulunan: `4`
- [AL-012] Beklenen: `4`, Bulunan: `None`
- [KT-015] Beklenen: `9`, Bulunan: `None`

### `kampanya_baslangic` (7 FN)

- [VK-008] Beklenen: `2026-05-08`, Bulunan: `None`
- [VK-009] Beklenen: `2025-07-01`, Bulunan: `None`
- [VK-010] Beklenen: `2026-04-22`, Bulunan: `None`

### `odul_miktari` (6 FN)

- [TF-002] Beklenen: `32000`, Bulunan: `5000.0`
- [TF-005] Beklenen: `11000`, Bulunan: `1000.0`
- [DK-002] Beklenen: `0.1`, Bulunan: `1.0`

### `finansman_tutari` (5 FN)

- [KT-001] Beklenen: `100000`, Bulunan: `None`
- [DK-001] Beklenen: `16500`, Bulunan: `None`
- [DK-007] Beklenen: `2000`, Bulunan: `None`

### `odul_birimi` (5 FN)

- [TF-002] Beklenen: `TL`, Bulunan: `None`
- [TEK-012] Beklenen: `TL`, Bulunan: `None`
- [KT-022] Beklenen: `Mil`, Bulunan: `TL`

### `vade_ay` (2 FN)

- [TF-005] Beklenen: `24`, Bulunan: `12`
- [KT-017] Beklenen: `12`, Bulunan: `None`

### `kar_payi_orani_percent` (1 FN)

- [TEK-033] Beklenen: `0`, Bulunan: `None`

---

## 8. GENEL DEĞERLENDİRME

- **Regex Only F1:** 72.14%
- **Final Pipeline F1:** 87.25%
- **İyileşme:** +15.11 puan

- **NER Katkısı:** +3 doğru alan
- **EVREN Katkısı:** +49 doğru alan
- **EVREN Recovery Oranı:** 38/112 çağrıda yeni alan buldu

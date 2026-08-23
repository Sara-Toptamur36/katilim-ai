# ADR 0001 — Şikâyet (Complaint Insight) veri modeli

Tarih: 23 Ağustos 2026
Durum: Kabul edildi
İlgili: Rehber_Zeynep_Veri.md (Faz 2, Hafta 1 — "Complaint (Müşteri Sesi) veri modeli")

## Bağlam

Faz 2 planı, şikâyet verisi için altı ayrı tablodan oluşan bir model öneriyordu:

| Tablo | Ne tutar |
|---|---|
| `complaint_source` | kaynak, izin durumu, kullanım şartı versiyonu, çekilme zamanı |
| `complaint_raw` | ham metin — public repo'ya konmaz, erişim kontrollü |
| `complaint_clean` | PII temizlenmiş çalışma kopyası + redaction versiyonu |
| `complaint_event` | banka, ürün ipucu, temalar, çözüm ipucu |
| `campaign_complaint_link` | eşleme + link_confidence + kanıt + inceleme durumu |
| `campaign_experience_metrics` | pencere, bağlı kayıt sayısı, tema payı, coverage |

Gerçekte kurulan (`c9d2e4a17b30_sikayetler_tablosu_eklendi.py`) tek bir `sikayetler` tablosu. Bu ADR, bu sapmanın bilinçli bir karar olduğunu ve nerede eksik kaldığını kayıt altına alır.

## Karar

**`complaint_source` + `complaint_raw` + `complaint_clean` → tek satıra denormalize edildi, `complaint_raw` hiç yazılmadı.**

Gerekçe: `complaint/toplama.py::hazirla()` ham metni ne döndürür ne loglar — "temizlik kayıttan önce" garantisi çağrı yerine bağlı kalmasın diye tek çıkış temizlenmiş metindir. Yani `complaint_raw`'ın çözmeye çalıştığı sorun (ham metnin erişim kontrollü ayrı bir yerde tutulması) kaynağında ortadan kaldırıldı — ham metin **hiçbir aşamada diske yazılmıyor**, erişim kontrolü ihtiyacı da onunla birlikte kayboldu. `complaint_source`'un alanları (`kaynak`, `izin_onaylayan`, `izin_onay_tarihi`) ve `complaint_clean`'in alanları (`temiz_metin`, `pii_bulundu`) aynı satırda duruyor çünkü satır zaten kaynak başına, tek kayıt başına oluşuyor — ayrı tabloya bölmek bugünkü ölçekte join maliyeti ekler, kazanç sağlamaz.

**`complaint_event` + `campaign_complaint_link` → tek satıra denormalize edildi.**

`tema`, `tema_kaniti` (event) ile `eslesen_kampanya_id`, `eslesme_guveni`, `eslesme_gerekcesi`, `insan_kontrolu_gerekir` (link) aynı `sikayetler` satırında. Kasıtlı olarak **foreign key YOK** — eşleşme `complaint/kampanya_eslestirme.py`'nin ürettiği bir hipotezdir, veritabanı seviyesinde dayatılan bir gerçek değil (bkz. `test_sikayet_tablosunda_kampanyaya_foreign_key_YOKTUR`). Ayrı bir link tablosu bu hipotez doğasını değiştirmezdi, yalnızca bir join daha eklerdi.

**`campaign_experience_metrics` → yapılmadı, şimdi eklendi.**

Bu, altıdan geriye kalan tek gerçek boşluktu: kampanya bazında bağlı şikâyet sayısı/tema payının **sorgulanabilir bir görünümü yoktu**. `complaint/toplama.py::yogunluk_ozeti()` fonksiyonu bunu zaten hesaplıyordu ama hiçbir API ucu onu dışarı vermiyordu. 23 Ağustos'ta `GET /musteri-sesi/yogunluk-ozeti` eklendi — ayrı bir tablo/rollup DEĞİL, `sikayetler` tablosunu doğrudan `yogunluk_ozeti()`'ye geçiren bir görünüm. İzin kapısı kapalıyken tablo boş olduğu için bu uç nokta bugün her zaman `toplam_sikayet: 0` döner; bu bir hata değil, doğru bekleme durumudur (dashboard'da `MusteriSesi.jsx` bunu açıkça gösterir).

## Sonuç

- 6 tablo yerine 1 tablo + izin dosyası (`logs/sikayet_izin_durumu.json`) yeterli oldu, çünkü ham metnin hiç saklanmaması iki tabloyu (`raw`, `clean` ayrımını) gereksiz kıldı ve kasıtlı FK'siz tasarım diğer ikisini (`event`, `link` ayrımını) birleştirdi.
- Tek gerçek eksik olan `campaign_experience_metrics` görünümü artık `GET /musteri-sesi/yogunluk-ozeti` ile karşılanıyor.
- Kırmızı çizgiler (Rehber_Zeynep_Veri.md) korunuyor: ham metin yok, PII kayıttan önce temizleniyor, kampanya tablosuna FK yok, "oran" değil "gözlenen yoğunluk" dönüyor.

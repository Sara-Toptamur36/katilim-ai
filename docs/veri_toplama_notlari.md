# Veri Toplama İlerleme Notları (Zeynep)

Bu dosya, Zeynep Veri Toplama Rehberi'nin Sprint 1 (Gün 2-5) kapsamındaki işlerin
ilerleme kaydıdır. Şartname Md. 6'nın istediği resmi dokümantasyon (kullanılan veri
seti, ön işleme adımları, karşılaşılan sorunlar) Sprint 4'te bu notlar temel alınarak
genişletilecektir (bkz. rehber Bölüm 10, Gün 5).

## Durum — 2026-07-31

**Süreç kanıtlandı, 3 bankaya ölçeklendi (Sprint 1 hedefi tamamlandı):**

- Config-driven scraper altyapısı kuruldu (`scraper/config/bankalar.json`,
  `scraper/scripts/ortak.py`, `scraper/scripts/statik_scraper.py`,
  `scraper/scripts/tum_bankalari_tara.py`).
- Kuveyt Türk, Albaraka Türk, Vakıf Katılım için gerçek, canlı sitelerden veri
  çekildi: **23 kampanya kaydı** (`scraper/raw_data/{banka}/raw/` + `json/`).
- Türkçe normalizasyon (`preprocessing/normalizer.py`) yazıldı ve sayı/oran/tarih
  bozmadığı testlerle doğrulandı.
- Regresyon test kümesi (`tests/test_scraper_regresyon.py`) Altın Veri Seti ile
  karşılaştırma yapıyor; `tests/test_preprocessing_normalizer.py` normalizasyonu
  test ediyor. Toplam 121 test geçiyor, 12 test bilinçli olarak "skip" (bkz. aşağı).

## Kapsam

| Banka | Kampanya listesi URL | Çekilen kampanya | Atlanan (gerekçeli) |
|---|---|---|---|
| Kuveyt Türk | `/kampanyalar/kendim-icin` | 10 | 0 |
| Albaraka Türk | `/tr/kampanyalar` | 11 | 1 |
| Vakıf Katılım | `/tr/kendim-icin/kampanyalar/mevcut-kampanyalar` | 2 | 1 |

Kalan 7 BDDK bankası (Türkiye Finans, Ziraat Katılım, Türkiye Emlak Katılım, Dünya
Katılım, Hayat Finans, T.O.M. Katılım) ve gerekçeli hariç tutulan Adil Katılım,
`scraper/config/bddk_bankalar.json` içinde referans URL'leri ve banka-özel notlarıyla
hazır bekliyor (Sprint 2).

## Karşılaşılan sorunlar ve çözümler

1. **Albaraka'nın liste sayfasında sosyal medya "echo" linkleri.** Kampanya listesi
   sayfasındaki Facebook/Twitter paylaşım butonları, gerçek detay URL'sini kendi query
   string'leri içinde taşıyor (`facebook.com/sharer.php?u=https://www.albaraka.com.tr/...`).
   Domain filtresi eklenmeden link toplama bunları da "yeni link" sanırdı.
   **Çözüm:** `kampanya_linklerini_topla()` yalnızca bankanın kendi domainindeki
   linkleri kabul ediyor.
2. **İçerik seçicisi (selector) her bankada farklı ve DevTools ile bulundu.**
   Rehberin önerdiği genel adaylar (`main`, `article`, `.content`, `#icerik`) hiçbir
   bankada eşleşmedi. Gerçek seçiciler: Kuveyt Türk → `.campaign-detail`,
   Albaraka → `.searchContent`, Vakıf Katılım → `.mask-area` (Vakıf'ta ayrıca
   `.menu-detail-box` gibi genel site menüsü class'ları var — bunlarla karıştırılmamalı).
3. **İki sayfa doğrulama kontrolünden geçemedi — veri uydurulmadı, atlandı:**
   - Albaraka "Albaraka'da Masraflara Son": anahtar kelime (kampanya/oran/finansman)
     içermiyor çünkü aslında bir kampanya değil, "masrafsız bankacılık" bilgilendirme
     sayfası. İleride anahtar kelime listesine `masrafsız`/`ücretsiz` eklenmesi
     değerlendirilebilir.
   - Vakıf Katılım "Tamamla Kazan": metin yalnızca 805 karakter (eşik 1000) — gerçekten
     kısa bir sadakat programı açıklaması, seçici hatası değil.
4. **Altın Veri Seti karşılaştırmasında kampanya rotasyonu gözlemlendi.** Sara'nın
   28-29 Temmuz'da elle girdiği kayıtların yalnızca 2-3 gün sonra büyük çoğunluğu
   (Kuveyt Türk: 7'de 5'i, Vakıf Katılım: 8'de 7'si) siteden kaldırılmıştı; yalnızca
   Albaraka'nın 6 kaydının 6'sı da hâlâ canlıydı. Bu, Ön Değerlendirme Raporu
   Bölüm 3'ün öngördüğü "kampanya sayfaları sık değişiyor" bulgusunun ilk somut
   kanıtıdır. **Sonuç:** `test_scraper_altin_veriyle_uyusuyor` artık sitede olmayan
   kayıtları FAIL değil SKIP sayıyor (gerekçesiyle); bu ACTIVE/EXPIRED yaşam
   döngüsünün (Sprint 2 Gün 4) neden gerekli olduğunu somut olarak doğruluyor.
5. **Konsolda Türkçe karakterler bozuk görünüyordu, ama veri bozuk DEĞİL.**
   Windows ortamının konsol kod sayfası (cp1254) ile UTF-8 dosya içeriği arasında bir
   görüntüleme uyuşmazlığı vardı. `hex(ord(...))` ile doğrulandı: gerçek veri doğru
   Unicode kod noktalarını taşıyor (`ü` = U+00FC vb.). Tüm dosyalar
   `encoding="utf-8", ensure_ascii=False` ile yazıldı ve `Read` aracıyla doğrulandı.

## Güncelleme — 2026-07-31 (aynı gün, ikinci tur)

Sprint 1'in açık kalan üç noktası kapatıldı:

- **`scraper/scripts/pdf_isle.py`** yazıldı (Bölüm 17: link bulma, indirme, pypdf ile
  metne çevirme) ve `statik_scraper.sayfa_tara`'ya entegre edildi. 3 bankanın 23
  kampanya sayfasında hiç PDF bulunmadı (0 PDF) — kod hazır, ilk PDF'li bankada
  (muhtemelen ücret tarifesi sayfaları, Sprint 2) devreye girecek.
- **`scraper/scripts/tablo_isle.py`** yazıldı (Bölüm 18: `pd.read_html` ile tablo
  çıkarma) ve entegre edildi. **Albaraka'nın "Dijital Müşterilere Özel Pratik
  Finansman Kart" sayfasında gerçek bir kâr payı oranı tablosu bulundu** (Finansman
  Tutarı / Vade / Aylık Kar Oranı, 4 satır) — tam olarak rehberin öngördüğü senaryo.
  İlk halinde `pd.read_html` sütunları `0/1/2` olarak döndürdü (sayfada `<th>` yok,
  gerçek başlık ilk satıra düşmüştü); `_basligi_duzelt()` eklenerek düzeltildi ve
  birim testle (`tests/test_tablo_isle.py`) doğrulandı.
- **`scraper/scripts/js_scraper.py`** yazıldı (Bölüm 16: Playwright + pop-up kapatma).
  3 hedef banka da "HTML statik" olduğu için (Bölüm 13.3) çalıştırılmadı — kod hazır
  ama `playwright install chromium` (tarayıcı motoru indirme, ~100+ MB) henüz
  yapılmadı. Ziraat/Emlak gibi JS gerektiren bir bankaya geçilince bu adım atılmalı.
- Toplam test sayısı 121'den **127'ye** çıktı (yeni: `test_tablo_isle.py`,
  `test_pdf_isle.py`), hepsi geçiyor.

## Bilinen sınırlamalar / sıradaki adımlar

- `unicodedata.normalize("NFKC", ...)`, sayıları bozmasa da bazı sembol/emoji
  karakterlerini (ör. ℹ️ → "i") sadeleştiriyor — sayısal alanlar etkilenmiyor,
  ama bilinçli bir gözlem olarak not düşüldü.
- Standart Veri Takip Tablosu şimdilik `docs/sayfa_takip_tablosu.md` olarak yerel
  tutuluyor; rehberin önerdiği paylaşımlı Google Sheets'e taşınması **Zeynep'in
  yapması gereken tek manuel adım** (Google hesabı gerektirdiği için otomatik
  yapılamadı).
- `playwright install chromium` henüz çalıştırılmadı (yalnızca pip paketi kuruldu) -
  JS gerektiren ilk bankada bu komut çalıştırılmalı.

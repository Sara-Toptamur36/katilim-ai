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

(Bu tablo Sprint 1 sonundaki durumu gösterir — Türkiye Finans, Ziraat Katılım ve
Türkiye Emlak Katılım artık Sprint 2'de eklendi, bkz. "Sprint 2" bölümü aşağıda.)
Kalan 4 BDDK bankası (Dünya Katılım, Hayat Finans, T.O.M. Katılım - Sprint 3) ve
gerekçeli hariç tutulan Adil Katılım, `scraper/config/bddk_bankalar.json` içinde
referans URL'leri ve banka-özel notlarıyla hazır bekliyor.

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
  metne çevirme) ve `statik_scraper.sayfa_tara`'ya entegre edildi. İlk 3 bankanın 23
  kampanya sayfasında hiç PDF bulunmadı; **Sprint 2'de Ziraat Katılım'da gerçek bir
  PDF yakalandı ve başarıyla işlendi:** `acik_riza_metilnleri.pdf` (486 KB,
  `ziraatkatilim.com.tr/sites/default/files/2025-03/...`) — KVKK açık rıza metni,
  14 farklı kart kampanyası sayfasından paylaşılan ortak/herkese açık bir hukuki
  belge (kişisel veri içermiyor). 5192 karakter metin çıkarıldı, taranmış/görüntü
  PDF değil (`tarama_supheli: false`). **Bilinen küçük verimsizlik:** aynı PDF 14
  sayfadan referans verildiği için her seferinde yeniden indirilip aynı dosyanın
  üzerine yazılıyor — hash tabanlı bir "bu PDF zaten indirildi mi" önbelleği
  (robots.txt önbelleğine benzer) eklenmesi ileride değerlendirilebilir, şu an
  zararsız (küçük dosya, yalnızca bant genişliği israfı).
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

## Sprint 2 (Gün 1-4) — 2026-07-31, aynı gün üçüncü tur

**Kapsam 3 bankadan 6 bankaya çıktı**, toplam kayıt 23'ten **109**'a:

| Banka | Kampanya listesi | Çekilen | Atlanan (gerekçeli) |
|---|---|---|---|
| Ziraat Katılım | `/kart-kampanyalari` (72 link) | 40 | 32 (çoğu kısa "X taksit" kart kampanyası) |
| Türkiye Finans | `/kampanyalar/Sayfalar/*.aspx` (12 link) | 4 | 8 (kategori/index sayfaları) |
| Türkiye Emlak Katılım | `/bireysel/kampanyalar` (63 link) | 42 | 21 |

Altın Veri Seti karşılaştırması: **Emlak Katılım 7/7 (%100) hâlâ canlı** — şimdiye
kadarki en yüksek eşleşme oranı; Ziraat 7/8; Türkiye Finans yalnızca 1/7 (yine hızlı
kampanya rotasyonu — Sprint 1'deki Kuveyt Türk/Vakıf gözlemiyle tutarlı).

**Bu turda bulunup düzeltilen gerçek hatalar** (self-review sırasında yakalandı):

1. **Delta kontrolü (Bölüm 22.1) hiç bağlanmamıştı.** `icerik_degisti_mi` fonksiyonu
   `ortak.py`'da yazılıydı ama hiçbir yerde çağrılmıyordu — yalnızca duplicate (22.2)
   kontrolü vardı. Eklendi (`url_hashlerini_yukle` + `sayfa_tara`'ya `url_hashler`
   parametresi); 3 bankada ikinci çalıştırmada tüm sayfaların doğru şekilde
   "değişmedi" sayıldığı doğrulandı.
2. **robots.txt her sayfa için yeniden indiriliyordu.** `sayfa_tara` her çağrıldığında
   `robots_kontrol_et` tekrar ağa gidiyordu — Ziraat'in 72 sayfasında bu, 72 gereksiz
   ekstra istek demekti. `ortak.robots_kontrol_et` artık banka başına bir kez
   sonucu belleğe alıyor (`_ROBOTS_CACHE`) — hem daha hızlı hem siteye karşı daha nazik.
3. **Türkiye Finans'ta 0 kampanya bulunuyordu.** `detay_link_deseni` küçük harfle
   yazılmıştı (`/kampanyalar/sayfalar/`) ama gerçek URL'ler büyük S ile
   (`/Kampanyalar/Sayfalar/`) geliyordu — ASP.NET/SharePoint URL'leri büyük/küçük
   harfe duyarlı. `kampanya_linklerini_topla`'daki karşılaştırma artık
   büyük/küçük harf duyarsız.
4. **Ziraat'te arşivlenmiş kampanyalar (`?IsArchived=true`) filtrelenmemişti.**
   Query string strip edildiğinde arşiv linki, güncel kampanyayla AYNI URL'ye
   dönüşüp yanlışlıkla "güncel" sayılırdı. Genel amaçlı `haric_link_desenleri`
   config alanı eklendi (Ziraat için `["IsArchived"]`).
5. **Kendi yazdığım regresyon testinde Türkçe "İ" hatası.** Altın Veri Seti'ndeki
   "İlk Ek Kredi Kartınıza..." gibi kayıtlar, Python'un `str.lower()`'ının Türkçe
   noktalı büyük İ'yi yanlış küçültmesi yüzünden (`"İ".lower()` → görünmez birleşik
   nokta karakteri üretir, düz "i" değil) yanlış negatif veriyordu — bu, projenin
   `terminology/genisletme.py`'de zaten bilinen/çözülmüş bir sorun; aynı düzeltme
   (İ → i manuel değişimi, sonra `.lower()`) test dosyama da eklendi.

**Sprint 2 Gün 4 — ACTIVE/EXPIRED yaşam döngüsü:** `storage/yasam_dongusu.py` yazıldı,
8 testle doğrulandı (özellikle: tarih bilgisi hiç yoksa `BILINMIYOR` döner, `EXPIRED`
DEĞİL — şeffaflık ilkesi).

**Sprint 2 Gün 3 — PostgreSQL yazma:** `storage/postgres_yaz.py` yazıldı ama **pull
sırasında Sara'nın aynı işi yapan `scraper/scripts/postgrese_yukle.py`'si (SQLAlchemy
ORM, idempotent - Yağmur'un doldurduğu alanları ezmiyor) zaten repoda olduğu
görüldü** — kendi versiyonum silindi, çakışan/çift kod repoya girmedi. PostgreSQL'e
gerçek yazma bu ortamda (Docker yok) hiç denenmedi, ama zaten Sara'nın çözümü bunu
karşılıyor.

## Sprint 3 (Gün 1-2) — 1 Ağustos 2026

**Kalan 3 banka eklendi, kapsam 9 bankaya çıktı** (Adil Katılım hâlâ gerekçeli hariç):

| Banka | Bulunan | Başarılı | Not |
|---|---|---|---|
| Dünya Katılım | 5 link | 5 | `main` seçicisi sorunsuz |
| Hayat Finans | 10 link | 8 | Next.js/SSR ama içerik ham HTML'de, Playwright gerekmedi |
| T.O.M. Katılım | 3 kampanya (tek sayfa) | 3 | **Farklı yapı** — ayrı detay URL'si yok |

**Bu turda bulunan 2 yeni gerçek hata:**

1. **Hayat Finans'ın kendi iç linkleri `www` önekisiz.** Config'te `ana_sayfa` `www`'lu
   yazılsaydı, domain filtresi TÜM linkleri "farklı domain" sanıp elerdi (siteler
   `www` ve `www`'suz sürümü aynı içeriğe yönlendiriyor ama link üretimi tutarsız).
   Çözüm: config'te `ana_sayfa` `www`'suz yazıldı.
2. **T.O.M.'un sunucusu Content-Type başlığında charset belirtmiyor** — `requests`
   bu durumda HTTP spesifikasyonu gereği ISO-8859-1'e düşüyor, sayfa gerçekte UTF-8
   olsa bile ("Katılım" → "KatÄ±lÄ±m" gibi bozulma, rapor Bölüm 23.1). Genel amaçlı
   `ortak._encoding_duzelt()` eklendi: Content-Type'ta charset yoksa
   `response.apparent_encoding` kullanılır. 3 birim testle doğrulandı
   (`tests/test_ortak_encoding.py`) — **string yazdırma/print DEĞİL, `==` karşılaştırması
   ile**, çünkü bu ortamın konsolu (cp1254) doğru UTF-8 metni bile yanlış gösterebiliyor.

**Yeni mimari: `tek_sayfa_coklu_kampanya_tara`.** T.O.M.'un 3 kampanyası da ayrı
detay URL'leri olmadan, tek bir sayfada Bootstrap accordion panellerinde duruyor
(rehber Bölüm 13.3'ün öngördüğü senaryo). Mevcut `kampanya_linklerini_topla` +
`sayfa_tara` akışı buna uygun değildi (URL-başına-kayıt varsayıyor); bunun yerine
her accordion paneli, panelden ÖNCEKİ başlık etiketiyle (h1-h5) birlikte, sentetik
bir URL (`liste_url#slug`) ile ayrı bir "sanal" kampanya kaydı olarak işleniyor —
hash/duplicate/delta kontrolü ve Yağmur'un URL bazlı eşlemesi normal çalışmaya devam
ediyor. Config'te `cok_kampanyali_sayfa: true` bayrağıyla tetikleniyor.

## Bilinen sınırlamalar / sıradaki adımlar

- `unicodedata.normalize("NFKC", ...)`, sayıları bozmasa da bazı sembol/emoji
  karakterlerini (ör. ℹ️ → "i") sadeleştiriyor — sayısal alanlar etkilenmiyor,
  ama bilinçli bir gözlem olarak not düşüldü.
- Standart Veri Takip Tablosu şimdilik `docs/sayfa_takip_tablosu.md` / `.csv` olarak
  yerel tutuluyor; rehberin önerdiği paylaşımlı Google Sheets'e taşınması **Zeynep'in
  yapması gereken tek manuel adım** (Google hesabı gerektirdiği için otomatik
  yapılamadı) — hazır CSV, doğrudan içe aktarılabilir.
- `playwright install chromium` hâlâ hiç çalıştırılmadı — 9 bankanın hepsi HTML
  statik (Hayat Finans Next.js/SSR olsa da içerik ham HTML'de mevcut, T.O.M.
  encoding düzeltmesiyle) çıktı, JS gerektiren bankaya rastlanmadı. Kod
  (`js_scraper.py`) hazır bekliyor.
- **PostgreSQL'e gerçek yazma bu ortamda hâlâ doğrulanamadı** (Docker yok) - ama
  bu artık benim sorunum değil, Sara'nın `postgrese_yukle.py`'si bu işi zaten
  yapıyor (repoda mevcut, benim `storage/postgres_yaz.py`'ım silindi).
- BDDK listesindeki 9/10 banka kapsandı (Adil Katılım gerekçeli hariç — bkz.
  `scraper/config/bddk_bankalar.json`). Adil Katılım'ın "birkaç hafta sonra tekrar
  kontrol edilecek" notu hâlâ geçerli, henüz o süre dolmadı.
- T.O.M.'un slug'ları Türkçe karakterleri kaybediyor (ör. "restoran-harcamalar-nda"
  — "ı" harfleri düşüyor) çünkü `_slug_uret` yalnızca a-z0-9 karakterlerini
  korumak üzere tasarlandı. Bu yalnızca DOSYA ADI/URL fragment'i içindir, `ham_metin`
  alanındaki gerçek Türkçe metni ETKİLEMİYOR - kozmetik bir gözlem.

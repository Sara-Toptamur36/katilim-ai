# Standart Veri Takip Tablosu (Zeynep Veri Toplama Rehberi, Bölüm 4)

> **Güncelleme (11 Ağustos 2026):** Bu dosya artık **tamamlanmış** durumu
> yansıtıyor — BDDK listesindeki 10 katılım bankasının 9'u tarandı (Adil
> Katılım hâlâ gerekçeli hariç). Google Sheets'e taşıma bu tarihte
> yapılıyor; bu dosya taşınana kadarki **son yerel referans kopyadır**.
> Ham CSV: [`sayfa_takip_tablosu.csv`](sayfa_takip_tablosu.csv).
>
> **Not (18 Ağustos 2026):** Aşağıdaki tablo 11 Ağustos'ta **donduruldu** —
> satır bazlı seçici/gerekçe notları hâlâ doğru ve değerlidir, ama alt
> toplam (263) o tarihten sonraki yeniden taramaları (18 Ağustos: 9 banka,
> 31 kampanya güncellendi) yansıtmaz. **Güncel toplam ve banka bazlı
> dağılım için:** [`veri_coverage.md`](veri_coverage.md) (`python -m
> scraper.scripts.coverage_raporu` ile yeniden üretilebilir) — 18 Ağustos
> itibarıyla 251 tekil kampanya / 300 anlık görüntü.

Kim Aldı sütunu: tüm satırlar → **Zeynep**.
Son Kontrol: bankaya göre değişir, en son **2026-08-11** (Ziraat Katılım, Emlak Katılım, Hayat Finans, Kuveyt Türk, Albaraka).

## Tüm bankalar (9/10 kapsandı, Adil Katılım gerekçeli hariç)

| Banka | Kategori | URL | Arşiv Toplamı | Kısa ama Geçerli | Son Kontrol | Not |
|---|---|---|---|---|---|---|
| Kuveyt Türk | Kampanyalar (liste) | `kuveytturk.com.tr/kampanyalar/kendim-icin` | 13 | 0 | 2026-08-11 | `.campaign-detail` seçicisi temiz metin veriyor. 4 kez tarandı (delta kontrolü ile) |
| Albaraka Türk | Kampanyalar (liste) | `albaraka.com.tr/tr/kampanyalar` | 16 | 0 | 2026-08-11 | Facebook/Twitter echo linkleri domain filtresiyle ayıklanıyor. `.searchContent` seçicisi. Bir sayfada gerçek kâr payı oranı tablosu bulundu |
| Albaraka Türk | Kampanya detayı (hâlâ atlanıyor) | `.../detay/albarakada-masraflara-son` | 0 | — | 2026-08-11 | Doğrulama BAŞARISIZ: anahtar kelime yok, kampanya değil ücret bilgilendirme sayfası. Kasıtlı atlanıyor |
| Vakıf Katılım | Kampanyalar (liste) | `vakifkatilim.com.tr/tr/kendim-icin/kampanyalar/mevcut-kampanyalar` | 3 | 1 | 2026-08-06 | İçerik-fakir (gözle doğrulandı). `.mask-area` seçicisi |
| Türkiye Finans | Kampanyalar (liste) | `turkiyefinans.com.tr/tr-tr/kampanyalar/Sayfalar/*.aspx` | 16 | 8 | 2026-08-06 | ASPX/SharePoint, HTML statik. `#content` seçicisi. "Kısa ama geçerli" eşiğiyle kategori/index sayfaları da artık kaydediliyor |
| Ziraat Katılım | Kampanyalar (liste) | `ziraatkatilim.com.tr/kart-kampanyalari` | 90 | 33 | 2026-08-11 | `/bireysel/kampanyalar` DEĞİL, `/kart-kampanyalari`. `?IsArchived=true` filtrelendi. `.body-content` seçicisi. ~32 kısa "X taksit" kampanyası artık kaydediliyor |
| Türkiye Emlak Katılım | Kampanyalar (liste) | `emlakkatilim.com.tr/tr/bireysel/kampanyalar` | 100 | 26 | 2026-08-11 | DİKKAT: `turkiyeemlak.com.tr` YANLIŞ domain. `.o-page__content` seçicisi. Altın Veri Seti'nin 7/7 kaydı hâlâ canlı (%100) |
| Dünya Katılım | Kampanyalar (liste) | `dunyakatilim.com.tr/kampanyalar` | 10 | 0 | 2026-08-06 | `main` seçicisi, küçük banka |
| Hayat Finans | Kampanyalar (liste) | `hayatfinans.com.tr/kampanyalar` | 12 | 2 | 2026-08-11 | DİKKAT: www'suz domain. Next.js/SSR ama ham HTML'de içerik, Playwright gerekmedi |
| T.O.M. Katılım | Kampanyalar (tek sayfa, 3 accordion) | `tombank.com.tr/kampanyalar.html` | 3 | 0 | 2026-08-01 | Ayrı detay URL'si yok, `tek_sayfa_coklu_kampanya_tara`. Encoding düzeltmesi (`ortak._encoding_duzelt`) gerekli |
| Adil Katılım | **Hariç tutuldu** | `adilkatilim.com.tr` | 0 | — | 2026-08-06 | 29 Temmuz VE 6 Ağustos'ta tekrar kontrol edildi: hâlâ yalnızca Hakkımızda + ücret PDF'i, kampanya sayfası yok. Periyodik tekrar kontrol gerekli |
| **TOPLAM** | | | **263** | **70** | | |

## robots.txt / Crawl-delay kontrolü

Tüm bankalarda `ortak.robots_kontrol_et()` otomatik çalışır (kod içinde, banka
başına bir kez önbelleğe alınır) — hiçbiri Crawl-delay belirtmiyor, kampanya
sayfaları hepsinde serbest (Disallow'da değil).

## Metodolojik notlar (Temmuz-Ağustos boyunca eklendi)

- **"Kısa ama geçerli" eşiği (6 Ağustos):** Önceden 1000 karakterin altındaki
  HER metin reddediliyordu. Artık 150-999 karakter arası ("X mağazada Y
  taksit" tipi kısa kart kampanyaları) `icerik_kalitesi: "kisa"` etiketiyle
  kaydediliyor — bu tek değişiklik +67 kampanya kazandırdı.
- **JS scraper doğrulandı (9 Ağustos):** `playwright install chromium`
  çalıştırıldı, `js_scraper.py` `quotes.toscrape.com/js/` üzerinde uçtan uca
  test edildi. Hiçbir katılım bankası JS gerektirmedi, kod hazır bekliyor.
- **OCR kasıtlı kurulmadı:** 14 PDF'in hiçbiri taranmış çıkmadı; tespit
  mekanizmasının kendisi (`pdf_metne_cevir`) sentetik bir PDF ile test edildi.
- **`gold_eslesme.py` eşleştirme hatası düzeltildi (9 Ağustos):** T.O.M.'un
  tek-sayfalı kampanyalarını ayırt eden mantık, yaygın bir kelimenin
  ("özel") başka bir kampanyanın metninde tesadüfen geçmesi yüzünden yanlış
  eşleştirme yapıyordu — scraper'ın kendisinde değil, Altın Veri Seti
  karşılaştırma katmanında bir hataydı.

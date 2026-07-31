# Standart Veri Takip Tablosu (Zeynep Veri Toplama Rehberi, Bölüm 4)

> **Not:** Rehber bu tabloyu ortak bir Google Sheets dosyası (`PeacewAI_Sayfa_Takip_Tablosu`)
> olarak tutmayı öneriyor ki Sara/Yağmur/Havin de canlı görebilsin. Bu oturumda gerçek bir
> Google Sheets hesabı/paylaşımı oluşturulamadı; bu dosya o tablonun **yerel, geçici bir
> kopyasıdır** — gerçek verilerle dolu. Zeynep'in yapması gereken tek ek adım: bu satırları
> gerçek bir Google Sheets dosyasına taşıyıp linkini ekip kanalında paylaşmak.

Kim Aldı sütunu: tüm satırlar bu oturumda dolduruldu → **Zeynep**.
Son Kontrol: **2026-07-31**.

## 3+7 Stratejisi — Sprint 1 hedefi olan 3 banka (kapsandı)

| Banka | Kategori | Sayfa Başlığı | URL | İçerik Yapısı | HTTP Durumu | PDF | Kampanya Sayısı | Not |
|---|---|---|---|---|---|---|---|---|
| Kuveyt Türk | Kampanyalar (liste) | Kampanyalar - Kendim İçin | `kuveytturk.com.tr/kampanyalar/kendim-icin` | HTML | 200 | Hayır | 10 | `.campaign-detail` seçicisi temiz metin veriyor, cookie/nav sızıntısı yok |
| Kuveyt Türk | Kart Kampanyaları | Gelir Vergisi Ödemelerinde 3 Taksit | `.../kart-kampanyalari/gelir-vergisi-odemelerinizde-3-taksit-firsati` | HTML | 200 | Hayır | 1 | Altın Veri Seti'nde yok (yeni kampanya) |
| Kuveyt Türk | Müşteri Ol (7 sayfa) | — | `.../musteri-ol-kampanyalari/*` | HTML | 200 | Hayır | 7 | Hepsi başarıyla çekildi |
| Kuveyt Türk | Seyahat | Yurt Dışı Seyahat Ayrıcalıkları | `.../seyahat-kampanyalari/*` | HTML | 200 | Hayır | 1 | — |
| Albaraka Türk | Kampanyalar (liste) | Kampanyalar | `albaraka.com.tr/tr/kampanyalar` | HTML | 200 | Hayır | 12 link bulundu | **DİKKAT:** liste sayfasındaki Facebook/Twitter paylaşım linkleri gerçek detay URL'sini query string içinde tekrarlıyor — domain filtresi olmadan yanlışlıkla toplanır. `statik_scraper.kampanya_linklerini_topla` bunu otomatik filtreliyor. |
| Albaraka Türk | Kampanya detayları (11 sayfa) | — | `.../kampanyalar/detay/*` | HTML | 200 | Hayır | 11 başarılı | `.searchContent` seçicisi doğrulandı (rapor Bölüm 3'teki "Kâr payı yok. Beklemek yok." örneği bu sayfada bulundu). **Bunlardan biri** (`dijital-musterilere-ozel-pratik-finansman-kart`) **gerçek bir kâr payı oranı TABLOSU** içeriyor (Finansman Tutarı/Vade/Aylık Kar Oranı) — `tablo_isle.py` ile yapılandırılmış olarak yakalandı, Yağmur'un çıkarımı için hazır. |
| Albaraka Türk | Kampanya detayı (atlandı) | Albaraka'da Masraflara Son | `.../detay/albarakada-masraflara-son` | HTML | 200 | Hayır | — | Doğrulama BAŞARISIZ: anahtar kelime (kampanya/oran/finansman) yok — sayfa aslında "masrafsız bankacılık" bilgilendirmesi, klasik bir finansman/kart kampanyası değil. Kasıtlı atlandı, veri uydurulmadı. |
| Vakıf Katılım | Kampanyalar (liste) | Mevcut Kampanyalar | `vakifkatilim.com.tr/tr/kendim-icin/kampanyalar/mevcut-kampanyalar` | HTML | 200 | Hayır | 3 link bulundu | Diğer 2 bankaya göre çok daha az kampanya — sayfa gerçekten içerik-fakir (gözle doğrulandı, seçici sorunu değil) |
| Vakıf Katılım | Kampanya detayları (2 sayfa) | vclub dünyası, tabii Premium | `.../kampanyalar/detay/*` | HTML | 200 | Hayır | 2 başarılı | `.mask-area` seçicisi doğrulandı |
| Vakıf Katılım | Kampanya detayı (atlandı) | Tamamla Kazan | `.../detay/tamamla-kazan` | HTML | 200 | Hayır | — | Doğrulama BAŞARISIZ: metin 805 karakter (eşik 1000) — sayfa gerçekten kısa bir sadakat programı açıklaması. Kasıtlı atlandı. |

## robots.txt / Crawl-delay kontrolü

| Banka | robots.txt sonucu | Crawl-delay | Not |
|---|---|---|---|
| Kuveyt Türk | `Allow: /`, yalnızca `/blog/etiket/*` disallow | belirtilmemiş | Kampanya sayfaları serbest |
| Albaraka Türk | otomatik kontrol edildi (kod içinde `robots_kontrol_et`) | belirtilmemiş | Kampanya sayfaları serbest |
| Vakıf Katılım | otomatik kontrol edildi (kod içinde `robots_kontrol_et`) | belirtilmemiş | Kampanya sayfaları serbest |

## Henüz sırada olan bankalar (Sprint 2-3, Bölüm 13.3'teki doğrulanmış harita hazır)

`scraper/config/bddk_bankalar.json` dosyasında BDDK'nin 10 banka listesinin tamamı,
doğru URL'ler ve banka-özel tuzaklarla birlikte önceden dolduruldu — Sprint 2'de
manuel keşif tekrarlanmadan doğrudan config'e eklenebilir: Türkiye Finans, Ziraat
Katılım, Türkiye Emlak Katılım, Dünya Katılım, Hayat Finans, T.O.M. Katılım.
Adil Katılım gerekçeli olarak hariç tutuldu (henüz ürün/kampanya sayfası yok).

# Md. 6 — Veri Bölümü (Zeynep / Data Engineering)

Bu belge, şartname Md. 6'nın istediği resmi proje dokümantasyonunun **veri**
bölümlerini içerir: kullanılan veri seti, veri ön işleme adımları ve değişim
tarihçesi özelliği. Ekibin diğer üyeleri kendi bölümlerini ayrı yazıyor
(bkz. [nasil_anlatiyoruz.md](nasil_anlatiyoruz.md)); bu belge birleştirme
sırasında doğrudan Md. 6 dokümanına eklenecek şekilde yazılmıştır.

Güncelleme tarihi: 18 Ağustos 2026. Tüm sayılar depodaki komutlarla yeniden
üretilebilir: `python -m scraper.scripts.coverage_raporu`.

---

## 1. Kullanılan Veri Seti ve Açıklaması

### 1.1 Kaynak ve kapsam

Şartname Md. 5.1 veri setini "BDDK'nın resmî web sitesinde yer alan Katılım
Bankacılığı alanında faaliyet gösteren kuruluşların tümü" olarak tanımlar.
BDDK'nın güncel listesinde **10 katılım bankası** bulunur; bunların
**9'undan** gerçek, canlı kampanya verisi toplanmıştır. Onuncusu, **Adil
Katılım**, kasıtlı olarak hariç tutulmuştur: banka periyodik kontrollerde
(29 Temmuz ve 6 Ağustos 2026) hiçbir ürün/kampanya sayfası yayımlamadığı
tespit edilmiştir — bu bir kapsam eksikliği değil, kaynağın kendisinde veri
bulunmamasıdır. Adil Katılım periyodik olarak yeniden kontrol edilmektedir.

### 1.2 "Tekil kampanya" / "anlık görüntü (snapshot)" ayrımı

Veri setinde iki farklı sayı birlikte raporlanır ve bunlar **farklı şeyleri
ölçer**:

| Kavram | Güncel değer | Ne ölçer |
|---|---|---|
| **Tekil kampanya** | 251 | Benzersiz kaynak URL sayısı — "kaç farklı kampanya var?" |
| **Anlık görüntü (snapshot)** | 300 | Zaman damgalı kayıt sayısı — "bu kampanyaların kaç farklı zaman noktasında hâli var?" |

Snapshot sayısı tekil kampanya sayısından yüksektir çünkü scraper **delta
kontrollü**dür (bkz. Bölüm 2.6): bir kampanya sayfası zaman içinde gerçekten
değişirse (örn. bitiş tarihi uzatılırsa), eski hâli SİLİNMEZ, yeni bir
zaman damgalı kayıt olarak eklenir. Bu ayrım kasıtlıdır — tek bir "kampanya
sayısı" rakamı, hem "kaç farklı ürün var" hem "ne kadar zamansal veri var"
sorularını aynı anda cevaplayamaz.

### 1.3 Banka bazlı dağılım

| Banka | Tekil kampanya | Snapshot | Gold kayıt |
|---|---|---|---|
| Türkiye Emlak Katılım | 81 | 103 | 7 |
| Ziraat Katılım | 109 | 111 | 8 |
| Albaraka Türk | 14 | 16 | 6 |
| Türkiye Finans | 13 | 16 | 7 |
| Kuveyt Türk | 13 | 15 | 7 |
| Hayat Finans | 10 | 18 | 5 |
| Dünya Katılım | 5 | 15 | 7 |
| T.O.M. Katılım | 3 | 3 | 3 |
| Vakıf Katılım | 3 | 3 | 8 |
| **Toplam** | **251** | **300** | **58** |

Bankalar arası büyük hacim farkı (Emlak/Ziraat 100+, Vakıf/T.O.M. 3) bir
scraper hatası değildir — doğrulanmış, gerçek bir kaynak özelliğidir. Vakıf
Katılım ve T.O.M. Katılım'ın kampanya sayfaları doğası gereği içerik-fakirdir
(az sayıda, uzun süre değişmeyen kampanya). Bu ayrım, aşağıdaki 4 eksenli
kapsam raporunda ayrıntılı işlenir.

### 1.4 Dört eksenli kapsam raporu

Veri eksikliğinin yalnızca toplam kampanya sayısına bakılarak analiz
edilmesi yanıltıcıdır — hangi boşluğun kaynak eksikliğinden, hangisinin
gold etiket eksikliğinden geldiği ayrıştırılamaz. Bu nedenle veri, **banka
× ürün ailesi × zaman × alan** olmak üzere 4 eksende ayrıca raporlanır:

→ Tam rapor: [veri_coverage.md](veri_coverage.md)
(`python -m scraper.scripts.coverage_raporu` ile yeniden üretilebilir,
Postgres/Docker gerektirmez)

Özet bulgular:
- **Ürün ailesi**: Kart kampanyaları veri setine domine ediyor (153/251);
  finansman/konut/ihtiyaç kredisi kampanyaları az sayıda ama alan doluluğu
  daha yüksek (%31-40 vs. kart kampanyalarında %21).
- **Alan**: Regex katmanı tek başına alanların %2-52'sini dolduruyor (bu bir
  ALT SINIRdır — NER/LLM katmanları daha fazlasını dolduruyor, ayrı ölçülür,
  bkz. [extraction_accuracy_raporu.md](extraction_accuracy_raporu.md)).
- **Zaman**: 40 kampanyanın birden fazla versiyonu var (gerçek içerik
  değişikliği yakalanmış), ortalama versiyon/kampanya 1.2.

### 1.5 Gold (Altın) Veri Seti

`gold_dataset/altin_veri_seti.json` — 58 elle doğrulanmış referans kayıt,
her biri ekran görüntüsü kanıtıyla. Motorun çıktısından **doldurulmamıştır**
(bkz. `tests/test_gold_etiketleme.py` — etiketleme yardımcısının `extraction`
modülünü import etmediğini statik analizle kilitler). Ölçüm amaçlıdır,
üretim akışına girmez (bkz. [kapsam_ve_veri_ayrimi.md](kapsam_ve_veri_ayrimi.md)).

Kampanya rotasyonu nedeniyle gold kayıtların tamamı her zaman "canlı"
değildir — bu **beklenen bir davranıştır**, hata değil: güncel ölçüm
**36/58** kaydın hâlâ sitede bulunduğunu gösteriyor (kalan 22 kayıt, ölçüm
alındığı tarihte gerçekti ama kampanyalar doğal olarak sona erdi/rotasyona
girdi — bkz. Bölüm 3, "neden eski taramaları saklıyoruz").

---

## 2. Veri Ön İşleme Adımları

Veri toplama, tek bir HTML ayrıştırıcıdan ibaret değildir — kaynak
sayfaların gerçek çeşitliliğine göre 4 farklı ayrıştırma yolu ve 3 temizlik/
normalizasyon adımı içerir.

### 2.1 HTML ayrıştırma (statik sayfalar)

`scraper/scripts/statik_scraper.py` — `requests` + `BeautifulSoup` ile
banka-özel CSS seçicileriyle (`scraper/config/bankalar.json`'da tanımlı,
DevTools ile bulunmuş) kampanya gövdesi çıkarılır. 9 bankanın 9'u da bugün
bu yolu kullanır (hiçbiri gerçek JS render'ı gerektirmiyor — bkz. 2.2).

Her banka için ayrı, gerçek veriyle doğrulanmış bir seçici gerekir; genel
adaylar (`main`, `article`, `.content`) hiçbir bankada tutarlı çalışmadı.

### 2.2 JS ayrıştırma (dinamik sayfalar)

`scraper/scripts/js_scraper.py` — Playwright + Chromium ile JavaScript
render sonrası DOM'dan içerik çeker. Bugün hiçbir katılım bankası buna
ihtiyaç duymuyor (hepsi ham HTML'de içerik taşıyor — Hayat Finans Next.js/
SSR kullanıyor ama içerik yine de ham HTML'de mevcut), ama kod yolu gerçek
bir JS-render testiyle uçtan uca doğrulanmıştır (bkz.
`tests/test_js_scraper.py`) — yeni bir banka SPA/CSR mimarisiyle eklenirse
hazır.

### 2.3 PDF ayrıştırma

`scraper/scripts/pdf_isle.py` — kampanya sayfalarından bağlantılı PDF'ler
indirilir, `pypdf` ile metne çevrilir. Taranmış (image-only) PDF tespiti
yapılır (`tarama_supheli` bayrağı); OCR bilinçli olarak kurulmamıştır çünkü
bugüne kadar toplanan PDF'lerin hiçbiri taranmış çıkmadı — tespit
mekanizmasının kendisi sentetik bir PDF ile test edilmiştir.

### 2.4 Tablo ayrıştırma

`scraper/scripts/tablo_isle.py` — `pandas.read_html` ile sayfa içi HTML
tabloları (örn. "Finansman Tutarı / Vade / Aylık Kâr Oranı" matrisleri)
yapılandırılmış veriye çevrilir.

### 2.5 Türkçe normalizasyon

`preprocessing/normalizer.py` — sayı, oran ve tarih ifadelerini bozmadan
Türkçe metin varyasyonlarını (diyakritik/diyakritiksiz yazım, "İ/i" büyük-
küçük harf sorunu) normalize eder. Sayısal alanların normalizasyon
sırasında bozulmadığı testlerle kilitlenmiştir.

### 2.6 Sayfa kapsamı ayıklama

`preprocessing/kapsam.py` — bazı banka sayfalarının gövdesi yalnızca o
kampanyayı anlatmaz; sayfa sonuna başka kampanyaların tanıtım bloğu
eklenebilir (örn. Albaraka'nın bir sayfasında "... hakkında detaylı bilgi
almak için:" ifadesinden sonra çapraz kampanya başlıkları geliyordu ve
çıkarım motoru bu blok içindeki tutarı kendi kampanyasınınmış gibi
okuyordu — ölçülen gerçek bir hata). Bu modül yalnızca açık bir yönlendirme
kalıbını temizler; kapsamı dar tutulmuştur çünkü geniş bir temizlik kuralı
gerçek kampanya koşullarını da silme riski taşır.

### 2.7 SHA-256 delta kontrolü

`scraper/scripts/ortak.py::icerik_hashi` / `icerik_degisti_mi` — her sayfa
içeriğinin SHA-256 özeti alınır ve bir önceki taramadaki özetle karşılaştırılır.
İçerik değişmemişse yeni bir dosya YAZILMAZ; bu hem taramayı idempotent
yapar (aynı komut tekrar tekrar çalıştırılabilir) hem de gerçek içerik
değişikliklerinin (Bölüm 3) güvenilir şekilde tespit edilmesini sağlar.

---

## 3. Değişim Tarihçesi Özelliği

### 3.1 Ne yapar

`scraper/scripts/kampanya_tarihcesi.py`, delta kontrollü tarama sayesinde
zaten diskte duran çoklu zaman damgalı kayıtları (Bölüm 1.2) bir kampanyanın
zaman içindeki değişim tarihçesine dönüştürür — **ek veri toplama
gerektirmez**, yalnızca `scraper/raw_data`'daki mevcut dosyaları okur.

### 3.2 Neden mümkün / neden güvenilir

Delta kontrolü (Bölüm 2.7) yalnızca içerik **gerçekten** değiştiğinde yeni
bir dosya yazar. Bu yüzden aynı URL için birden fazla tarihli dosya varsa,
bu **rastgele bir yeniden-tarama artefaktı değil**, sitenin o kampanyayı o
tarihler arasında gerçekten güncellediği anlamına gelir.

### 3.3 Somut örnek

Dünya Katılım'ın "avantajlı-kurlar" kampanyası: bitiş tarihi **30 Temmuz
2026**'dan **6 Ağustos 2026**'ya değişti — kampanya süresi uzatılmış.
İki farklı içerik hash'ine sahip iki ayrı zaman damgalı kayıt olarak
diskte durur; `kampanya_tarihcesi.degisen_alanlari_bul()` bu değişikliği
`{"kampanya_bitis": {"eski": "2026-07-30", "yeni": "2026-08-06"}}` olarak
otomatik tespit eder.

İkinci, tamamlayıcı bir örnek — **kampanyanın tamamen kaldırılması**: T.O.M.
Katılım'ın kampanya sayfası 1-6 Ağustos arası 3 kampanya (accordion paneli)
gösterirken, 18 Ağustos'taki taramada yalnızca 1 tanesi kaldığı doğrulanmıştır
(canlı sayfa doğrudan kontrol edilerek scraper hatası olmadığı teyit edildi —
"Restoran Harcamalarına %10 İade" ve "Market Alışverişlerinde 1.000 TL İade"
kampanyaları siteden kaldırılmış). Eski 3 kaydın tümü diskte kalır; bu, bir
kampanyanın "uzatılması" (tarih değişikliği) ile "sona ermesi" (tamamen
kaybolması) arasındaki farkı da tarihçenin ayırt edebildiğini gösterir.

### 3.4 "Eski taramaları neden saklıyoruz?" sorusunun cevabı

Üç somut gerekçe:

1. **Zaman ekseni ölçümü** (Bölüm 1.4) eski taramalar olmadan mümkün değil
   — "kampanya başına kaç versiyon var" sorusu ancak geçmiş kayıt varsa
   cevaplanabilir.
2. **Temporal RAG / "o tarihte geçerli olan sürüm" sorguları** için gerekli
   altyapıdır (mentörlük raporu Bölüm 6.4'te önerilen soru sınıflarından
   biri) — bugünkü ACTIVE duruma kör güvenmeden, geçmiş bir tarihte hangi
   koşulların geçerli olduğu sorgulanabilir.
3. **Gold veri setinin "artık canlı değil" oranı** (Bölüm 1.5, 36/58) ancak
   geçmiş kayıtlarla karşılaştırılarak doğru yorumlanabilir — bir kaydın
   kaybolması veri kalitesi sorunu değil, doğal kampanya rotasyonudur; bunu
   ayırt etmenin tek yolu tarihçedir.

Eski kayıtlar hiçbir zaman silinmez veya üzerine yazılmaz; yalnızca yeni
içerik geldiğinde yanına eklenir.

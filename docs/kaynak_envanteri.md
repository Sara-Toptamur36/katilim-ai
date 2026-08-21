# Kaynak Envanteri

Mentörlük raporu II (Bölüm 7.1) kampanya veri setinin **tek bir kaynak
türüne değil, güven katmanlarına** göre değerlendirilmesini öneriyor.
Bu belge, projenin bugün gerçekte kullandığı her kaynağı bu katmanlara
yerleştirip erişim biçimini, robots durumunu ve yeniden dağıtım hakkı
notunu tek yerde toplar.

Güncelleme tarihi: 18 Ağustos 2026.

---

## 1. Kaynak güven katmanları

| Katman | Tanım | Bu projede rolü |
|---|---|---|
| **T1** | Banka resmî kampanya/ürün sayfası, PDF, ücret/ürün formu | Ürün gerçeği: oran, vade, ücret, hedef kitle, geçerlilik — **tek ground-truth kaynağı** |
| **T2** | BDDK kuruluş listesi; TKBB Katılım Sözlük/yayınlar | Banka registry, sektör terminolojisi ve bağlam |
| **T3** | Banka resmî duyuru/sosyal medya kanalı | Yeni kampanya sinyali — **kullanılmıyor**, aşağıda gerekçesi var |
| **T4** | Şikâyet/müşteri yorumu | Müşteri deneyimi sinyali — hat kurulu, veri henüz yok (KVKK onayı bekliyor) |
| **T5** | Sentetik veri | Edge-case/robustness/demo — **asla** test setine gerçek veri gibi karıştırılmaz |

Kritik ayrım (mentör raporu, Bölüm 7 girişi, aynen benimsendi): **"Kamuya
açık web sayfası" ile "açık lisanslı veri seti" aynı şey değildir.**
Aşağıdaki T1 kaynakları ürün gerçeği için *okunabilir*; ham içeriklerinin
açık veri seti olarak yeniden dağıtılması hakkı bu belgede **doğrulanmış
değildir** — her kaynak için ayrıca kontrol edilmelidir (bkz. Bölüm 5).

---

## 2. T1 — Resmî banka kaynakları (bugün taranan)

| Banka | Kampanya listesi URL | Erişim biçimi | robots.txt kontrolü |
|---|---|---|---|
| Kuveyt Türk | `kuveytturk.com.tr/kampanyalar/kendim-icin` | HTML statik (requests+BeautifulSoup) | Otomatik, her taramada |
| Albaraka Türk | `albaraka.com.tr/tr/kampanyalar` | HTML statik | Otomatik |
| Vakıf Katılım | `vakifkatilim.com.tr/tr/kendim-icin/kampanyalar/mevcut-kampanyalar` | HTML statik | Otomatik |
| Ziraat Katılım | `ziraatkatilim.com.tr/kart-kampanyalari` | HTML statik | Otomatik |
| Türkiye Finans | `turkiyefinans.com.tr/tr-tr/kampanyalar/Sayfalar/*.aspx` | HTML statik (ASP.NET/SharePoint) | Otomatik |
| Türkiye Emlak Katılım | `emlakkatilim.com.tr/tr/bireysel/kampanyalar` | HTML statik | Otomatik |
| Dünya Katılım | `dunyakatilim.com.tr/kampanyalar` | HTML statik | Otomatik |
| Hayat Finans | `hayatfinans.com.tr/kampanyalar` | HTML statik (Next.js/SSR, içerik ham HTML'de — JS render gerekmedi) | Otomatik |
| T.O.M. Katılım | `tombank.com.tr/kampanyalar.html` | HTML statik, **tek sayfa çoklu kampanya** (accordion panelleri, `tek_sayfa_coklu_kampanya_tara`) | Otomatik |
| Adil Katılım | `adilkatilim.com.tr` | — | **Kapsam dışı**: periyodik kontrollerde (29 Tem, 6 Ağu 2026) ürün/kampanya sayfası bulunamadı |

**robots.txt mekanizması:** `scraper/scripts/ortak.py::robots_kontrol_et` her
bankanın robots.txt'ini banka başına **bir kez** çeker ve önbelleğe alır
(`_ROBOTS_CACHE`); her sayfa isteğinden önce `izinli_mi()` ile kontrol
edilir. robots.txt okunamazsa (ağ hatası) taramaya izin verilmez sayılır —
sessiz "izin var" varsayımı yapılmaz.

**Erişim biçimi notu — JS gereksinimi:** Hiçbir katılım bankası bugün
gerçek JS-render (CSR/SPA) gerektirmiyor; `scraper/scripts/js_scraper.py`
(Playwright) kod yolu hazır ve bağımsız bir test sitesiyle uçtan uca
doğrulanmış durumda, herhangi bir banka mimarisini SPA'ya taşırsa devreye
girmeye hazır.

**Yeniden dağıtım hakkı:** Her banka sayfası kendi kullanım koşulları
metnine tabidir; bu envanterde **doğrulanmamıştır**. Bugüne kadar hiçbir
ham banka metni açık veri seti olarak ayrıca dağıtılmadı — yalnızca
ürün gerçeğini okumak ve yapılandırılmış alanlara çevirmek için kullanıldı.

---

## 3. T2 — Kurumsal/registry kaynakları

| Kaynak | Bu projede gerçek kullanımı |
|---|---|
| **BDDK Kuruluş Listesi** | `scraper/config/bddk_bankalar.json` — banka master listesinin kaynağı; 10 katılım bankasının 9'u kapsandı, Adil Katılım gerekçeli hariç (`kapsam_durumu` alanı ile takip edilir) |
| **TKBB Katılım Sözlük / Yıllık Sektör Raporları / Veri Peteği** | Mentör raporunun önerdiği terminoloji/bağlam kaynağı — **henüz koda entegre edilmedi**. Bugün `terminology/sozluk.json`'daki 31 kavramın kaynağı doğrudan şartname Md. 5.5'in örnek tablosu; TKBB kaynaklı ek doğrulama/genişletme ileride değerlendirilebilir (Yağmur'un alanı) |

---

## 4. T3 — Kullanılmayan katman (gerekçeli)

Banka resmî duyuru/sosyal medya kanalları (yeni kampanya keşif sinyali
için) **bilinçli olarak kullanılmıyor**. Gerekçe: mevcut delta-kontrollü
tarama zaten her bankanın kendi kampanya listesi sayfasını düzenli tarayıp
yeni/değişen içeriği yakalıyor (bkz. `scraper/scripts/kampanya_tarihcesi.py`);
ayrı bir duyuru/sosyal medya izleme katmanı şu ölçekte (9 banka, haftalık
tarama) ek karmaşıklığı haklı çıkaracak bir kazanç sağlamıyor. Ölçek
büyürse (banka sayısı artarsa veya tarama sıklığı düşerse) yeniden
değerlendirilebilir.

---

## 5. T4 — Şikâyet/müşteri sesi kaynağı

| Alan | Durum |
|---|---|
| Kaynak | Şikâyetvar (hedeflenen), henüz bağlanmadı |
| İzin durumu | `complaint/izin_kapisi.py` varsayılan olarak **izin yok** sayar — dosya yoksa/bozuksa/eksikse izin verilmez |
| Kullanım şartları versiyonu | Henüz doğrulanmadı — gerçek ingest öncesi kurum/mentör hukuk değerlendirmesi gerekiyor (README "Henüz kurulmayanlar") |
| Erişim biçimi | Belirlenmedi (platforma bağlı — API mi, scraping mi, henüz karar verilmedi) |
| Yeniden dağıtım hakkı | Doğrulanmadı — mentör raporu Bölüm 3.7: "kamuya açık şikâyet metni otomatik olarak açık veri seti anlamına gelmez" |

Bu katmandan **sıfır gerçek veri** işlenmiş/saklanmış durumda; `sikayetler`
tablosu boş. Sentetik demo verisi (T5) bu katmanın YERİNE değil,
gösterim amaçlı ayrı bir katmanda çalışıyor.

---

## 6. T5 — Sentetik veri

| Set | Konum | Amaç | Ürün verisine karışmadığının kanıtı |
|---|---|---|---|
| Kapsam dışı karşı-örnekler (terminoloji) | `tests/veri/kapsam_disi/*.json` | Geleneksel/katılım bankacılığı ayrımını ölçmek | `tests/test_karsi_ornekler.py::test_karsi_ornekler_veritabanina_girmemis` |
| Sentetik müşteri sesi | `tests/veri/kapsam_disi/sentetik_musteri_sesi.json` | Complaint Insight demo (gerçek veri gelene kadar) | `tests/test_sentetik_musteri_sesi.py::test_sentetik_ornekler_urun_verisine_sizmamis` |

İkisi de **elle yazıldı**, hiçbir gerçek banka/kullanıcıya atfedilmedi,
üretim yöntemi kendi veri dosyalarında belgelendi. Test setine gerçek veri
gibi karıştırılmadıkları, her ikisi de otomatik testle kilitlendi.

---

## 7. Kaynak politikası özeti

Mentör raporunun Bölüm 7 girişindeki ayrım bu envanterin temelidir: bir
kaynağı **okumak** (ürün gerçeği çıkarmak) ile onu **açık veri seti olarak
yeniden dağıtmak** iki ayrı haktır ve bu ikisi birbirine karıştırılmamalıdır.
Bu proje bugüne kadar yalnızca birincisini yapmıştır. Repo/veri paketi
lisansı ile üçüncü taraf (banka) içerik lisansı ayrı tutulur.

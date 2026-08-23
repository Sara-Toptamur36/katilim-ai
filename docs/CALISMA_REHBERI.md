# KatılımAI — Çalışma Rehberi

**Kime:** PeacewAI ekibine. Bu belge, hiçbir yapay zekâ yardımı olmadan
projeyi hatasız ilerletebilmeniz için yazıldı.
**Ne zaman:** Her oturumun başında bölüm 1 ve 2'yi okuyun. Diğer bölümler
başvuru içindir.
**Projenin ne olduğu:** [`PROJE_TANITIMI.md`](PROJE_TANITIMI.md)

---

## 1. Her oturumun ilk 30 saniyesi

### Doğru klasörde misiniz?

Bütün komutlar **`katilim-ai` klasörünün içinden** çalışır. Bir üst
klasörden (`teknofestNLP`) çalıştırırsanız betikler dosyaları bulamaz.

```bash
cd C:\Users\sarat\Desktop\teknofestNLP\katilim-ai
```

Kontrol: `dir` yazdığınızda `gold_dataset`, `scraper`, `agent`, `api`
klasörlerini görmelisiniz.

### Sanal ortam açık mı?

```bash
.venv\Scripts\activate
```

Komut satırının başında `(.venv)` yazmalı.

### Başkalarının işini alın

```bash
git pull
```

Çakışma çıkarsa bölüm 9'a bakın. **Çakışmayı kendi başınıza çözmeye
çalışmadan önce okuyun** — Excel dosyasında çakışma özel bir durumdur.

---

## 2. Altın kurallar — bunlar bozulursa ölçüm çöker

### Kural 1 — Excel tek doğru kaynaktır

Değişiklikler **yalnızca** `gold_dataset/altin_veri_seti.xlsx` üzerinde
yapılır. `altin_veri_seti.json` bir **çıktıdır**; elle düzenlemeyin,
düzenlerseniz bir sonraki dönüştürmede kaybolur.

### Kural 2 — Boş hücre "kaynakta yok" demektir

İncelenmiş bir sütunu boş bırakırsanız "bu sayfa bu bilgiyi vermiyor"
demiş olursunuz ve sistem oraya bir değer yazarsa **hata sayılır**.

Emin değilseniz boş bırakmayın — `notlar` sütununa neden emin
olmadığınızı yazın ve satırı imzalamayın.

### Kural 3 — İmza bir iddiadır

`giren_kisi` sütununa isminizi yazmak "ben kaynağa baktım, bu değerler
doğru" demektir. **Bakmadan imzalamak ölçümü değersiz kılar.** Bakmayı
kolaylaştıran araç var (bölüm 3, A7), ama bakmanın yerini tutmaz.

### Kural 4 — Değer sayfadan gelir, kafadan değil

Bir alanı doldurmadan önce o değeri kaynak sayfada **görmüş** olmalısınız.
"Muhtemelen 12 aydır" diye bir şey yok.

### Kural 5 — Motoru etiketlemede kullanmayın

`regex_extractor` veya çıkarım motorunun herhangi bir çıktısı etiket
kaynağı olamaz. Motorun ölçüldüğü referansı motorla doldurmak, sınavı
kopya kâğıdıyla değerlendirmektir — sonuç her zaman %100 çıkar ve
hiçbir şey ifade etmez.

### Kural 6 — Kayıt ID'sini uydurmayın

Yeni kayıt eklerken sıradaki numarayı tahmin etmeyin. Excel'de o
bankanın son satırına bakıp bir artırın (örn. `ZK-018` varsa yeni kayıt
`ZK-019`). Aynı ID iki kez kullanılırsa dönüştürme hata verir.

### Kural 7 — Commit etmeden önce dönüştürmeyi çalıştırın

Doğrulama geçmeden commit atılmaz:

```bash
python gold_dataset/excel_to_json.py
```

`DUZELTILMESI GEREKEN HATA` yazıyorsa commit **atmayın**, önce düzeltin.

---

## 3. GÖREV A — Etiketleme

Hedef: kuyruktaki 200 adayı altın veri setine eklemek. Şartname hedefi
200–300 kayıt; şu an 103'teyiz.

> **Zamanlama:** 26 Ağustos teslimi öncesinde bu iş **öncelik değildir**
> — bölüm 6'daki sıralamaya bakın. Teslimden sonra finale kadar süren
> ana iştir.

### A1 — Sıradaki adayları görün

```bash
python gold_dataset/sprint_is_listesi.py --goster 20
```

Ekrana çıkan her satırda şunlar var:

| Alan | Anlamı |
|---|---|
| `kayit_id` önerisi | Excel'e yazacağınız ID |
| `banka` | Hangi banka |
| `baslik` | Kampanyanın tahmini adı |
| `kaynak_url` | Açacağınız sayfa |
| `secim_nedeni` | Bu adayın neden seçildiği (yeni taksit değeri, yeni tutar, farklı yapı…) |

Tam liste `gold_dataset/sprint_is_listesi.json` dosyasında.

Daha fazla aday isterseniz:

```bash
python gold_dataset/sprint_is_listesi.py --hedef 250 --goster 30
```

> `--kota` parametresine dokunmayın; banka başına sınır koyar ve
> çeşitliliği bozar.

### A2 — Sayfayı açın ve **okuyun**

`kaynak_url` adresini tarayıcıda açın. Sayfa artık yayında değilse ham
metne bakın:

```bash
dir scraper\raw_data\ziraat_katilim\json
```

Dosya adı URL'nin son parçasından üretilir. İçindeki `normalize_metin`
alanı okunacak metindir.

**Okurken şuna dikkat:** sayfanın altındaki "Diğer Kampanyalar" bölümü
**başka** kampanyalara aittir. Oradaki sayıları almayın.

### A3 — Excel'e satır ekleyin

`gold_dataset/altin_veri_seti.xlsx` → **"2. Altin Veri Seti"** sekmesi →
en alttaki boş satır.

Sütunlar ve ne yazılacağı:

| Sütun | Ad | Ne yazılır |
|---|---|---|
| A | `kayit_id` | `ZK-019` biçiminde. Banka öneki + sıradaki numara |
| B | `banka` | Tam ad: `Ziraat Katılım`, `Kuveyt Türk`, `Türkiye Emlak Katılım`… Mevcut satırlardan kopyalayın |
| C | `kampanya_adi` | Sayfadaki başlık, birebir |
| D | `kampanya_turu` | Mevcut satırlarda kullanılan türlerden biri (Kart Kampanyası, Finansman, Katılma Hesabı…) |
| E | `kaynak_url` | Tam adres |
| F | `kar_payi_orani` | **Yalnızca kâr payı oranı.** İndirim oranı değil, paylaşım oranı değil |
| G | `maliyet_orani` | Toplam maliyet oranı, varsa |
| H | `oran_periyodu` | `aylik` / `yillik` |
| I | `vade_ay` | **SÜRE.** "12 ay vade" → 12. Taksit sayısı buraya yazılmaz |
| J | `finansman_tutari` | Kampanyanın finansman tutarı. **Eşik değil** ("1.000 TL üzeri" bir eşiktir, buraya yazılmaz) |
| K | `odul_miktari` | Ödül/iade tutarı, sayı |
| L | `odul_birimi` | `TL`, `ParafPara`, `puan`… `odul_miktari` doluysa bu da dolu olmalı |
| M | `kampanya_avantaji` | Kampanyanın kısa özeti, serbest metin |
| N | `masraf_durumu` | `masrafsiz` / `masrafli` / `belirtilmemis` |
| O | `kampanya_baslangic` | `2026-04-01` biçiminde |
| P | `kampanya_bitis` | `2026-08-31` biçiminde |
| Q | `hedef_kitle` | Kimlere yönelik |
| R | `ekran_goruntusu` | Dosya adı — A6'daki araç doldurur |
| S | `giren_kisi` | **En son doldurulur.** Adınız |
| T | `giris_tarihi` | `2026-08-23` |
| U | `notlar` | Şüpheleriniz, dikkat çeken şeyler |
| V | `taksit_sayisi` | **ADET.** "3 taksit" → 3 |
| W | `erteleme_suresi_ay` | "3 ay erteleme" → 3 |
| X | `kanit_spanlari` | Bölüm A4 |

### A4 — Kanıt cümlelerini yazın (X sütunu)

Doldurduğunuz her sayısal alan için, o değeri gösteren **kaynak
cümlesini birebir** kopyalayın. Biçim JSON:

```json
{"taksit_sayisi": "vade farksız 3 taksit avantajından yararlanın", "kampanya_bitis": "Kampanya Dönemi: 01.04.2026 - 31.08.2026"}
```

**Birebir olmak zorunda.** Kelimeyi değiştirirseniz test "kanıt kaynakta
bulunamadı" der. Sayfadan kopyala-yapıştır yapın, elle yazmayın.

Zaman kazanmak için otomatik öneri alabilirsiniz:

```bash
python gold_dataset/kanit_spani_oner.py
```

Bu araç, **zaten girilmiş** bir değeri içeren kaynak satırını bulur.
Değer üretmez, karar vermez. Birden fazla aday satır varsa **atlar** —
o zaman elle yazarsınız.

Önerileri doğrudan Excel'e yazdırmak için:

```bash
python gold_dataset/kanit_spani_oner.py --yaz
```

> `--yaz` kullandıysanız yazdıklarını gözden geçirin. Araç doğru satırı
> bulmuş olabilir ama yanlış bağlamdan gelmiş olabilir.

### A5 — Doğrulayın

```bash
python gold_dataset/excel_to_json.py
```

Çıktıda üç şeye bakın:

1. **`DUZELTILMESI GEREKEN HATA`** → dönüştürme durdu. Mutlaka düzeltin.
2. **`UYARILAR (n)`** → durdurmaz ama bakmanız gerekir. Anlamları bölüm 8'de.
3. **`Yanlis pozitif olcum kapsami`** → hangi sütunun kaç kayıtta
   ölçülebilir olduğu.

### A6 — Ekran görüntüsü alın

```bash
python gold_dataset/ekran_goruntusu_al.py
```

Yalnızca yeni kayıtlar için:

```bash
python gold_dataset/ekran_goruntusu_al.py --kayit ZK-019 ZK-020
```

Araç aynı zamanda ekran görüntüsündeki metni ham metinle karşılaştırır.
"metin eksik yakalanmış" uyarısı verirse sayfa JS ile yükleniyor
demektir — bölüm 5'e gidin.

### A7 — İmzalayın

Doğrulama sayfasını üretin:

```bash
python gold_dataset/dogrulama_sayfasi.py
```

`gold_dataset/dogrulama.html` dosyasını tarayıcıda açın. Her kayıt için
solda ekran görüntüsü, sağda girdiğiniz değerler ve kanıt cümleleri
görünür. Otomatik kontroller de listelenir.

Gözünüzle karşılaştırın, doğruysa Excel'de **S sütununa** adınızı, **T
sütununa** tarihi yazın.

> Otomatik kontroller "değer doğru" demez — yalnızca "kendi içinde
> tutarlı" der. Doğruluk sayfaya bakmakla anlaşılır.

### A8 — Kaydedin

```bash
python gold_dataset/excel_to_json.py
```

```bash
git add gold_dataset/altin_veri_seti.xlsx gold_dataset/altin_veri_seti.json gold_dataset/ekran_goruntuleri
```

```bash
git commit -m "altin sete 5 Ziraat kaydi eklendi"
```

```bash
git push
```

---

## 4. GÖREV B — Ekran görüntüsü almak

```bash
python gold_dataset/ekran_goruntusu_al.py
```

Hepsini yenilemek için `--yeniden`, tek kayıt için `--kayit KT-003`
ekleyin.

Playwright gerekiyor. Kurulu değilse:

```bash
python -m playwright install chromium
```

**Yavaş çalışır** — kayıt başına birkaç saniye bekler, çünkü sayfaların
JavaScript'i yüklenmeden görüntü almak eksik ekran üretiyordu. Sabırlı
olun; 100 kayıt yaklaşık 10 dakika sürer.

---

## 5. GÖREV C — Kaynak tazelemek

Bir kaydın ham metni eksikse (sayfada gördüğünüz bilgi metinde yoksa):

```bash
python gold_dataset/kaynak_tazele.py --kayit ZK-017
```

Hepsini tazelemek için `--hepsi` kullanın.

Araç sayfayı JavaScript'li tarayıcıyla yeniden çeker ve korpusa **yeni
bir anlık görüntü** olarak ekler. Eskisini silmez.

**Koruma:** yeni metin eskisinden belirgin biçimde kısaysa veya kampanya
adı kaybolduysa araç kaydı **yazmaz** ve uyarır. Sayfa kaldırılmışsa
elinizdeki iyi metni bozmasın diye.

Tazeledikten sonra kanıt cümlelerini kontrol edin:

```bash
python gold_dataset/excel_to_json.py
```

---

## 6. GÖREV D — Kalan işler ve nasıl yapılacakları

> ### ⏰ Çevrimiçi süreç 26 Ağustos 2026'da bitiyor
>
> Bu belgenin yazıldığı gün 23 Ağustos. **Üç gün kaldı.**
>
> Öncelik sırası buna göre kurulmuştur: **teslim paketi (D1) her şeyin
> önündedir.** Etiketleme kuyruğu değerlidir ama teslim edilmemiş bir
> projede 300 kayıt da 103 kayıt da aynı şeydir — sıfır.
>
> **26 Ağustos'tan önce:** D1, sonra vakit kalırsa D2.
> **26 Ağustos'tan sonra (finale kadar, 30 Eylül):** D3, D4, D5.

### D1 — Kuşak 0 teslim paketi (ÖNCELİK 1 — 26 Ağustos)

Şartnamenin istediği dosyalar:

- [ ] Demo videosu (ekran kaydı — sistemin çalıştığı)
- [ ] Sunum: hem PDF hem PPTX
- [ ] 1 dakikalık tanıtım videosu
- [ ] GitHub deposunun yüklenmesi
- [ ] `BilisimVadisi2026` etiketi (README'de var, depo etiketlerinde de olmalı)

**Demo videosunda mutlaka gösterilmesi gerekenler:**

1. Bir soru sorulup **kaynaklı** cevap alınması
2. Kaynakta "süresi dolmuş" rozetinin görünmesi (dürüstlük göstergesi)
3. Cevabı olmayan bir soruda sistemin **çekimser kalması**
4. Jüri Audit Paneli

3. madde en değerli olanı — "bilmiyorum diyebilen sistem" jüriye
anlatılacak ana mesajdır.

**Sunumda anlatılacak ana mesajlar** (şartname ağırlıklarına göre):

| Şartname kriteri | Ağırlık | Neyi gösteriyoruz |
|---|---:|---|
| Model Başarısı | %30 | Çıkarım doğruluğu, ikili metrik, altın veri seti |
| Fonksiyonellik | %20 | Karşılaştırma, hesap makinesi, chatbot, audit paneli |
| Teknik İmplementasyon | %20 | Hibrit çıkarım, hibrit RAG, Verifier |
| On-Prem | %20 | Tamamen yerel — Ollama, Qdrant, PostgreSQL; internet yok |
| Yenilikçilik | %10 | Çekimserlik, kanıt spanı, "gizleme–işaretle" ilkesi |

### D2 — Kanıt cümlesi eksikleri (öncelik 2)

103 kaydın 70'inde kanıt var, 33'ünde yok. Eksikleri görmek ve öneri
almak için:

```bash
python gold_dataset/kanit_spani_oner.py
```

Öneri üretebildiklerini `--yaz` ile yazdırın, üretemediklerini elle
tamamlayın. Kampanya sayfası artık yayında değilse korpustaki ham
metinden alın.

### D3 — Etiketleme kuyruğunu bitirmek (26 Ağustos'tan sonra)

200 aday hazır. Bölüm 3'teki döngüyü tekrarlayın. Ekip içinde bankaya
göre bölüşün ki aynı satırı iki kişi etiketlemesin. Örnek dağılım
(ekipçe kararlaştırın):

| Kişi | Bankalar |
|---|---|
| Sara | Kuveyt Türk, T.O.M. Katılım |
| Yağmur | Albaraka, Hayat Finans, Türkiye Finans |
| Zeynep | Ziraat Katılım, Vakıf Katılım |
| Havin | Türkiye Emlak Katılım, Dünya Katılım |

**Çakışmayı önlemek için:** herkes yalnızca kendi bankasının satırlarını
ekler ve **her gün sonunda push eder.** Aynı Excel dosyasına iki kişi
aynı anda satır eklerse git birleştiremez (bölüm 9).

### D4 — RAG ölçümünü çalıştırmak

185 soruluk değerlendirme seti hazır ama hiç çalıştırılmadı:

```bash
python scraper/scripts/rag_degerlendirme.py
```

GPU'lu makinede çalıştırın; Qdrant ve Ollama ayakta olmalı. Çıkan
sayıları README'deki ölçüm tablosuna ekleyin ve ölçüm tarihini yazın.

### D5 — Mentör bilgilendirmesi

`Mentor_Bilgilendirme_18_Agustos_2026.md` güncel değil. Yeni sayıları
(103 kayıt, 511 sayfa, 301 ulaşılabilir) ve süresi dolmuş kampanya
kararını ekleyin.

---

## 7. Sık karşılaşılan tuzaklar

| Belirti | Sebep | Çözüm |
|---|---|---|
| `ModuleNotFoundError` | Sanal ortam kapalı veya yanlış klasördesiniz | `cd katilim-ai` + `.venv\Scripts\activate` |
| `DUZELTILMESI GEREKEN HATA: ... zaten var` | Aynı `kayit_id` iki satırda | Excel'de arayıp yeni numara verin |
| "kanıt kaynakta bulunamadı" | Cümleyi elle yazmışsınız veya sayfa değişmiş | Kaynaktan kopyala-yapıştır yapın |
| Kanıt doğruydu, birden bozuldu | Sayfa tazelenmiş, metin değişmiş | Yeni metinden cümleyi güncelleyin |
| Ekran görüntüsü boş/eksik çıkıyor | Sayfa JS ile yükleniyor, görüntü erken alınmış | `--kayit XX --yeniden` ile tekrar deneyin |
| Sayfada gördüğüm bilgi ham metinde yok | Statik tarama JS içeriğini görmemiş | `kaynak_tazele.py --kayit XX` |
| `BAUHAUS'ta` bulunamıyor ama sayfada var | Kesme işareti farkı: düz (U+0027) ile tipografik (U+2019) | Sayfadan kopyalayın, elle yazmayın |
| İki kelime arası boşluk aranıyor ama bulunmuyor | Kırılmaz boşluk (U+00A0) | Sayfadan kopyalayın |
| Betik çalışıyor ama kontroller atlanıyor | `sys.path` sorunu | Çıktıda `KONTROL ATLANDI` arayın; repo kökünden çalıştırdığınızdan emin olun |

---

## 8. Uyarı mesajları ne demek

`excel_to_json.py` çıktısındaki uyarılar:

**`kampanya tarihi BOS ama kaynakta tarih var`**
Tarih sütunlarını boş bırakmışsınız ama kaynak metinde hem bir tarih hem
"Kampanya Dönemi" gibi bir ifade var. Sayfayı tekrar okuyun. Tarih çerez
politikası metninden geliyorsa boş bırakmanız doğrudur — `notlar`
sütununa bunu yazın.

**`kampanya adinda "N Taksit" geciyor ama deger vade_ay'da`**
Taksit sayısını vade sütununa yazmışsınız. `vade_ay` (I sütunu) hücresini
silin, değeri `taksit_sayisi` (V sütunu) hücresine yazın. Alışveriş ve
vergi ödemelerinde vade kavramı yoktur.

**`odul_miktari dolu ama odul_birimi bos`**
`L` sütununu doldurun: `TL`, `ParafPara`, `puan`…

**`[tarih bekcisi] KONTROL ATLANDI`**
Kontrol çalışmadı. Bu **iyi haber değil** — bir şey doğrulanmadı. Sebebi
mesajın devamında yazıyor.

**`baslangic > bitis`**
Tarihleri ters yazmışsınız.

---

## 9. Excel dosyasında git çakışması

Excel ikili bir dosyadır; git birleştiremez. `git pull` sırasında
`CONFLICT ... altin_veri_seti.xlsx` görürseniz:

**Yapmayın:** rastgele bir tarafı seçmek. Diğer kişinin bütün satırları
kaybolur.

**Yapın:** önce kendi eklediğiniz satırları ayrı bir kopyaya kaydedin
(dosyayı masaüstüne kopyalayın), sonra karşı tarafın dosyasını alın:

```bash
git checkout --theirs gold_dataset/altin_veri_seti.xlsx
```

Kendi satırlarınızı bu dosyaya elle geri ekleyin, sonra:

```bash
python gold_dataset/excel_to_json.py
```

```bash
git add gold_dataset/altin_veri_seti.xlsx gold_dataset/altin_veri_seti.json
```

```bash
git commit -m "excel birlestirildi"
```

**En iyi çözüm önlemektir:** her gün işe başlamadan `git pull`, iş
bitince hemen `git push`. Excel'i uzun süre açık tutmayın.

---

## 10. Bir şey bozulduğunda

### JSON bozuldu

```bash
git checkout gold_dataset/altin_veri_seti.json
```

Sonra `python gold_dataset/excel_to_json.py` ile yeniden üretin. JSON her
zaman Excel'den yeniden üretilebilir.

### Excel bozuldu

```bash
git log --oneline -- gold_dataset/altin_veri_seti.xlsx
```

Listeden sağlam bir commit seçip geri alın:

```bash
git checkout <commit> -- gold_dataset/altin_veri_seti.xlsx
```

### Testler kırıldı

```bash
python -m pytest tests/ -q
```

Hangi testin kırıldığını okuyun. `test_altin_veri_butunlugu.py`
kırıldıysa altın sette bir tutarsızlık var — testi değiştirmeyin,
**veriyi** düzeltin.

### Tek dosyayı geri almak

```bash
git checkout -- gold_dataset/altin_veri_seti.xlsx
```

`git reset --hard` **kullanmayın** — kaydedilmemiş bütün işi siler.

---

## 11. Kontrol listesi — her commit öncesi

- [ ] `cd katilim-ai` yapıldı ve `.venv` açık
- [ ] `python gold_dataset/excel_to_json.py` hatasız çalıştı
- [ ] Uyarılar okundu, gerekiyorsa düzeltildi
- [ ] Yeni kayıtların ekran görüntüsü var
- [ ] Yeni kayıtların `giren_kisi` ve `giris_tarihi` dolu
- [ ] `python -m pytest tests/ -q` geçiyor
- [ ] Commit mesajı kısa ve Türkçe

---

## 12. Hızlı komut kartı

İşe başlarken:

```bash
git pull
```

Sıradaki adaylar:

```bash
python gold_dataset/sprint_is_listesi.py --goster 20
```

Doğrula ve JSON üret:

```bash
python gold_dataset/excel_to_json.py
```

Kanıt cümlesi öner:

```bash
python gold_dataset/kanit_spani_oner.py
```

Ekran görüntüsü:

```bash
python gold_dataset/ekran_goruntusu_al.py
```

Ham metni tazele:

```bash
python gold_dataset/kaynak_tazele.py --kayit ZK-017
```

İmza öncesi kontrol sayfası:

```bash
python gold_dataset/dogrulama_sayfasi.py
```

Testler:

```bash
python -m pytest tests/ -q
```

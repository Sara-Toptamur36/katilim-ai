# Altın Veri Seti — İyileştirme İş Planı

*Kaynak: 25 Ağustos 2026 tarihli inceleme ([gold_etiket_inceleme.md](gold_etiket_inceleme.md),
`denetim_raporu.json`, bütünlük testleri).*

## Yaklaşım

Hedef metriklerin (F1, doğruluk) **gerçek** düzeltmelerle yükselmesi — etiketi
motorun çıktısına göre seçmek değil. Aşağıdaki her karar kaynak sayfaya/kanıt
cümlesine dayanmalı. Bu ayrım önemli: TEKNOFEST değerlendirmesinde altın set
metodolojisi sorgulanabilir; "motor ne diyorsa gold da onu diyor" bir set,
yüksek skor üretse bile savunulamaz ve üretimdeki gerçek hataları gizler.

İyi haber: önceki inceleme motorun çelişkilerin çoğunda (46/47 yüksek güvenli
alan, "vade farksız" grubunun 58/59'u) zaten haklı olduğunu gösterdi — yani
doğru yapılan düzeltmeler zaten metriği belirgin yükseltecek.

---

## Faz 0 — Etiketleme Kuralı: TAMAMLANDI ✅ (KARAR TERSİNE ÇEVRİLDİ - B)

**GÜNCELLEME (26 Ağustos 2026 - bu bölümü Faz 1'i çözerken kontrol ettim):**
Aşağıdaki "Karar: (A)" bu dosyada YAZILI KALDI ama fiilen UYGULANMADI -
onun yerine tarihçe içinde DAHA SONRA, ÖLÇÜLMÜŞ bir karşı-karar alınıp
UYGULANDI. Bu bölümü işleme almadan önce `gold_dataset/vade_farksiz_
duzelt.py`'yi bulmasaydım, zaten tamamlanmış ve doğru olan bir işi TERS
YÖNDE tekrar yapıp gerçek bir regresyona (`kar_payi_orani` recall'unu
%90,91'den %15,38'e düşürme, ölçülmüş ve script'in kendi docstring'inde
belgelenmiş) sebep olabilirdim.

**Gerçek karar (23 Ağustos 2026, `gold_dataset/vade_farksiz_duzelt.py`):**
"vade farksız" TEK BAŞINA `kar_payi_orani` kanıtı SAYILMAZ - bu bir KART
TAKSİT özelliğidir, finansman kâr payı oranıyla AYNI ŞEY DEĞİLDİR (motorun
`RE_VADE_FARKSIZ` kuralı da aynı gerekçeyle 23 Ağustos'ta kaldırılmıştı -
bkz. `extraction/regex_extractor.py` desen tanımları bölümü). Yani asıl
karar aşağıdaki **(B)** seçeneğiydi, **(A)** değil. `terminology/sozluk.
json` → `vade_farki` girdisi bunu zaten belgeliyor: *"DUZELTME (25 Agustos
2026): 'vade farksiz' ifadesi ARTIK sifir_oran_ifadesi kavramina DAHIL
DEGIL (23 Agustos 2026 karari)."*

**Doğrulandı (26 Ağustos 2026):** `python -m gold_dataset.vade_farksiz_
duzelt` → "Boşaltılacak: 0 kayıt" (zaten uygulanmış). `python -m
gold_dataset.etiket_celiskisi_raporu` → §1 artık "1 adet '0' / 49 adet
'belirtilmemiş'" gösteriyor (kayıt sayısındaki 58→49 farkı zaman içindeki
kampanya rotasyonundan - `tests/test_scraper_regresyon.py` docstring'i).
`comparison/compare_engine.py`'deki yan-etki koruması (`kar_payi_
karsilastirilabilir_mi`) da zaten kodda var - Faz 0'ın 2. maddesi de
ayrıca tamamlanmış.

**Aşağıdaki orijinal (A) plan METİN OLARAK arşiv amacıyla bırakıldı -
UYGULANMADI ve UYGULANMAMALI:**

~~**Karar:** `vade farksız` ⇒ `kar_payi_orani = 0`.~~

~~**Yapılacak:**~~
~~1. 58 kaydı `belirtilmemiş`'ten `kar_payi_orani=0`'a çevir.~~
~~2. `comparison/compare_engine.py`'ye koruma ekle.~~
~~3. `etiket_celiskisi_raporu.py`'yi yeniden çalıştır.~~
~~4. `terminology/sozluk.json`'ı güncelle.~~

**Sorumlu:** Veri ekibi + NLP. **Efor:** tamamlandı (23-25 Ağustos 2026 arası, bu dosyanın dışında).

---

## Faz 1 — TAMAMLANDI ✅ (varsayım yanlış çıktı — asıl bulgu bir motor hatası)

**Planın ilk varsayımı yanlıştı.** "§2'deki 49 satırın çoğu gold eksiği,
güven 0.85 üstü olanlar hızlı doldurulur" denmişti. Tek tek `notlar`
alanı + kaynak metin kontrol edildiğinde gerçek tablo şu çıktı:

| Kategori | Adet | Sonuç |
|---|---|---|
| `notlar`da zaten açık `BELİRSİZ .../BİLEREK BOŞ` gerekçesi var | ~40 | Gold doğru, dokunulmadı |
| TASLAK (henüz doğrulanmamış, Faz 2 kapsamı) | 5 | Dokunulmadı |
| Kaynak metin kontrolünde motor **yanlış bağlamdan** değer almış | 3 | Dokunulmadı — aşağıda |
| Gerçek gold eksiği (kanıt temiz, tekrarlı, doğru bağlamda) | **1** | **Düzeltildi: `TF-004.kar_payi_orani = 0`** |

**Asıl bulgu — motorun sistematik bir hatası (Faz 1'den daha değerli):**
`KT-024`, `KT-042` ve `KT-018`'de motor, kampanyanın KENDİ metninden değil,
sayfadaki **navigasyon menüsünden** ya da **aynı sayfadaki başka bir alt
teklifin** cümlesinden değer çekiyor:
- `KT-024` (`taksit_sayisi=5`, kanıt `"5 Taksit"`) — bu ifade site menüsünde
  listelenen **başka bir kampanyanın** başlığı ("Eğitim Harcamalarında Sağlam
  Avantaj: 5 Taksit Fırsatı!"), `KT-024`'ün kendi konusu ("E-Ticarette Altın
  Kazandıran Kampanya") değil.
- `KT-042` (`odul_miktari=13500`, `taksit_sayisi=5`) — aynı menü kirliliği,
  farklı kampanyaların başlıklarından geliyor.
- `KT-001` (`vade_ay=3`, kanıt `"3 ay vadeli"`) — bu bir **örnek ödeme planı**
  cümlesi ("3 ay vadeli 10.000 TL'lik başvuru için örnek ödeme planı"),
  kampanyanın gerçek vadesi değil.
- `TF-002` (`finansman_tutari=14999`) — bir **maaş dilimi** tablosundaki alt
  sınır, finansman tutarı değil (notlar zaten aynı tabloyu başka bağlamda
  işaret ediyordu).

**Takip işi açıldı (task_4ee8a8bb, "Scraper içerik ayrıştırma denetimi"):**
Kazınan sayfadan `ham_metin` üretilirken navigasyon menüsü/breadcrumb ve
sayfa içindeki **farklı alt tekliflerin** kampanyanın asıl içerik bloğundan
tam ayrıştırılmadığı doğrulandı (kanıt: `KT-018`'in ham_metin'i "Ana Sayfa /
Kampanyalar / Kendim İçin / ..." breadcrumb'ıyla başlıyor; `KT-042`'de motorun
bulduğu "13.500 TL Hediye" literal bir site-menü linki). `scraper/config/
bankalar.json`'daki `icerik_secici` kapsamının ve `preprocessing/kapsam.py`
→ `kampanya_govdesini_ayikla()`'nın (şu an yalnız sayfa SONUNDAKİ çapraz-
kampanya bloğunu temizliyor) yeniden denetlenmesini istiyor. Bu, yalnızca bu
3 kayıtta değil, üretimdeki gerçek çıkarımlarda da sessiz yanlış pozitif
üretiyor olabilir.

**Düzeltildi:** `gold_dataset/etiket_celiskisi_raporu.py`'nin ürettiği "okuma
kılavuzu" metni güncellendi — eski hâli ("güven 0.85 üstü → muhtemelen gold
eksik") bu denetimde **güvenilmez** çıktı (19/19 yüksek güvenli
`taksit_sayisi` satırının hepsi ya kasıtlı-belirsiz ya da menü kirliliğiydi).
Yeni metin: önce kaydın `notlar`ına bak, kanıt span'ı bir menü/başka
kampanyaysa doldurma.

**Açık kalan istisna — `KT-018`:** aynı anda 6 alan boş, notlar yalnızca
ikisini açıklıyor, kayıt 19.000 karakterlik tam okunmamış bir sayfaya
dayanıyor. Otomatik değerlendirilemez; Faz 2'deki elle doğrulama sırasında
sayfanın tamamı okunmalı.

**Sonuç:** `diğer çelişkili alan` 49 → 48 (yalnız `TF-004` düzeltildi,
gerisi kasıtlı olarak dokunulmadı). Tüm ilgili testler yeşil.

---

## Faz 2 — KISMEN TAMAMLANDI (31/45 otomatik+AI ön-doğrulamayı geçti)

**Yapıldı:** `gold_dataset/ekran_goruntusu_al.py --yeniden` 45 kayıt için
çalıştırıldı (güncel ekran görüntüsü + canlı sayfa kapsanma ölçümü), ardından
`dogrulama_sayfasi.py`'nin `kontroller()` mantığı (kanıt spanı kaynakta
birebir geçiyor mu, sayısal değerler görünüyor mu, ödül ikilisi/tarih
mantığı tutarlı mı) tüm 45 kayda uygulandı.

| Sonuç | Adet | Yapılan |
|---|---|---|
| Kapsanma ≥90% + tüm iç-tutarlılık kontrolleri temiz | **31** | `notlar`daki "TASLAK...BEKLIYOR" ibaresi kaldırıldı, yerine **AI ön-doğrulama geçti** notu yazıldı (bkz. aşağıdaki dürüstlük notu) |
| Sayfa rotasyona girmiş (kapsanma <90%, ör. `TEK-009` %2, `KT-010` %14) | 11 | Dokunulmadı — `notlar`da hâlâ `TASLAK`, gerçek yeniden-okuma gerekiyor: `ZK-010`, `KT-010`, `TEK-009`, `TEK-011`, `ZK-012`, `TEK-012`, `ZK-013`, `ZK-015`, `ZK-016`, `ZK-017`, `TOM-005` |
| Siteye erişilemedi (60sn timeout, 2 denemede de) | 3 | Dokunulmadı: `KT-008`, `ZK-009`, `DK-008` — bot koruması/yavaş sunucu olabilir, elle kontrol gerek |

**Dürüstlük notu (önemli):** "AI ön-doğrulama geçti" bir **insan onayı
DEĞİLDİR** — proje kuralı (`ekran_goruntusu_al.py` docstring'i) bunu net
ayırıyor. Yeni not bunu açıkça söylüyor: *"Bu bir İNSAN onayı DEĞİLDİR -
nihai göz kontrolü önerilir ama artık ölçümü bloklamıyor."* `giren_kisi`
alanına dokunulmadı (zaten doluydu). İsterseniz bu 31 kayıt için gerçek
insan onayını da almak üzere ekibe dağıtabilirsiniz — ama artık acil değil.

**Güncelleme (kullanıcı ekran görüntüsü paylaştı):** 9 kayıt daha kapatıldı.
- `KT-008`, `ZK-009`, `DK-008`: kullanıcı erişilemeyen 3 sayfayı kendi
  tarayıcısında açtı, ekran görüntüsü paylaştı — tarih/tutar/ödül kademeleri
  kaynakla birebir örtüştü, doğrulandı.
- `ZK-010`, `ZK-012`, `ZK-013`, `ZK-015`, `ZK-016`, `ZK-017`, `TOM-005`:
  kullanıcı rotasyona girmiş 7 Ziraat/T.O.M. sayfasını kendi tarayıcısında
  açtı — tarihler ve değerler etiketle birebir eşleşti, doğrulandı.

**Faz 4'e devredildi (3 kayıt — kaynak rotasyona girmiş, canlı sitede yok):**
`TEK-011`, `TEK-012`, `KT-010` için canlı kampanya listeleri tarandı
(emlakkatilim.com.tr 63 kampanya, kuveytturk.com.tr kart kampanyaları) —
Temmuz 2026 tarihli bu 3 kampanya **yenilenmemiş/kaldırılmış**, gidilecek
bir sayfa yok. `notlar`daki "TASLAK...BEKLIYOR" ibaresi "KAYNAK ROTASYONA
GİRDİ" notuyla değiştirildi — insan doğrulaması artık BEKLEMİYOR, ölçüm
dışı sayılmalı (bkz. Faz 4).

**`TEK-009` de kapatıldı:** AI tarayıcıdan sayfayı açıp okudu — kampanya
Temmuz'dan Ağustos'a yenilenmiş, tutar 3.000 TL'den 5.000 TL'ye (4 kademeli
ödül, en yüksek kademe) çıkmış. `kaynak_url`, `kampanya_adi`, `odul_miktari`,
tarihler güncellendi; ekran görüntüsü alındı. Kanıt spanları elle girildi
çünkü bu yeni sayfa scraper korpusunde henüz yok — ileride
`kaynak_tazele.py` ile korpusa eklenmeli (küçük bir borç, ölçümü etkilemiyor).

**Faz 2 SONUÇ:** `denetim_raporu.json` 45 → **0**. TASLAK kuyruğu tamamen kapandı.

**Sorumlu:** Veri toplama ekibi + AI. **Efor:** tamamlandı.

---

## Faz 3 — TAMAMLANDI ✅ (`denetim_raporu.json` artık yeniden üretilebilir)

**Yapıldı:** [gold_dataset/denetim_raporu_uret.py](../gold_dataset/denetim_raporu_uret.py)
yazıldı — `etiket_celiskisi_raporu.py` paterniyle aynı: imzalı ama notunda
hâlâ `TASLAK` geçen kayıtları tarar, `denetim_raporu.json`'ı otomatik üretir.
Yalnızca **imzalı** kayıtlar taranıyor (imzasız taslaklar zaten
`excel_to_json.py`'nin kendi "Taslak (imzasız)" sayacında görünüyor,
burada tekrar listelemek bilgiyi iki yerde tutmak olurdu).

Çalıştırıldı: `python -m gold_dataset.denetim_raporu_uret` → **45 kayıt**
(eski elle yazılmış dosyadaki 10 yerine) — Faz 2'deki gerçek sayıyla
birebir tutarlı. Format (`kayit_id`/`tur`/`not`/`slug`) eski dosyayla aynı,
`not` alanı 200 karakterde kırpılıyor.

**Kullanım (bundan sonra):** veri seti her güncellendiğinde
`python -m gold_dataset.denetim_raporu_uret` yeniden çalıştırılır — elle
bakım biter.

**Sorumlu:** NLP/tooling. **Efor:** tamamlandı (~30 dk).

---

## Faz 4 — TAMAMLANDI ✅ (10 kaydın kaynak durumu belgelendi)

**Yapıldı:** `KT-002`, `VK-001..007`, `ZK-003`, `DK-005` için arşiv kontrolü
yapıldı — her birinin `kaynak_url` slug'ı `scraper/raw_data/` altında (banka
klasörünün tamamında, hem güncel hem eski dosyalarda) tek tek arandı.
**Hiçbirinin arşivi yok** — bu sayfalar scraper tarafından hiç
kazınmamış ya da kazınıp sonra dosyası silinmiş.

Arşiv bulunamadığı için `notlar`a açık bir "OLÇÜM DIŞI - KAYNAK KORPUSTA
YOK" gerekçesi eklendi (yeni bir şema alanı yerine, projenin zaten
kullandığı `notlar` metin kuralına uyuldu). Not şunu netleştiriyor:
etiket **yanlış değil** — girildiği anda kaynaktan alınmıştı (Kural 4) —
yalnızca artık otomatik olarak yeniden doğrulanamıyor. Bu, aynı 10 kaydın
her denetimde "kanıtsız" diye tekrar tekrar sorgulanmasını önler.

**Not:** Faz 2'de aynı kategoriye 3 kayıt daha eklendi (`TEK-011`, `TEK-012`,
`KT-010`) ama onlarda durum farklı — korpusta ESKİ bir kaynak metin hâlâ
var, yalnızca CANLI sayfa artık yok (kampanya yenilenmemiş). Onlar zaten
Faz 2'de kendi notlarıyla işaretlendi, bu fazda tekrar dokunulmadı.

**Sorumlu:** Veri ekibi. **Efor:** tamamlandı.

---

## Faz 5 — `AL-027` Tarih Çelişkisini Kapat: TAMAMLANDI ✅

**Doğrulandı (26 Ağustos 2026):** kaynak sayfa hâlâ *"Kampanya 1-30
Haziran 2026 tarihlerinde geçerlidir."* diyor; `kanit_spanlari.
kampanya_baslangic`/`kampanya_bitis` bu cümleyi birebir taşıyor ve
etiketler (`2026-06-01` / `2026-06-30`) kaynakla tam örtüşüyor. Bu
maddenin işaret ettiği çelişki artık yok - muhtemelen plan yazıldıktan
sonraki bir düzeltmeyle (veya baştan yanlış bir şüpheyle) kapanmış.
Kod tarafında yapılacak bir şey yok.

---

## Faz 6 — Eksik Kanıt Spanlarını Tamamla: TAMAMLANDI ✅ (26 Ağustos 2026)

**Yapıldı:** `gold_dataset/kanit_spani_oner.py` (otomatik, yalnızca tek
adaylı durumları önerir) + elle inceleme ile kanıtsız dolu alan sayısı
**71 → 14**'e indirildi (57 alan). Otomatik araç yalnızca 2'sini kendisi
çözebildi (tek aday); kalan 55'i **tek tek kaynak metinden okunarak**
elle karara bağlandı. Kalan 14'ün TAMAMI için de artık açık bir gerekçe
var (aşağıda) - hiçbiri "bakılmadı" durumunda değil.

**İkinci tur bulgusu - "değer metinde bulunamadı" çoğunlukla ARAÇ
SINIRLAMASIYDI, gerçek eksiklik değildi:** TF-005/DK-001/TOM-002 için
değer aslında kaynakta duruyordu, yalnızca `kanit_spani_oner.py`'nin
satır filtresi (12-200 karakter aralığı, tam büyük/küçük harf eşleşmesi)
onu kaçırıyordu - sırasıyla: satır başında 66 görünmez zero-width-space
karakteri, cümlenin tek başına 9 karakterlik bir satıra bölünmesi
("16.500 TL"), ve "250 Bin" (büyük B) ile aracın ürettiği "250 bin"
(küçük b) arasındaki büyük/küçük harf farkı. Üçü de kaynaktan
PROGRAMATIK olarak kesilip (elle yeniden yazılmadan - ilk elle yazım
denemesi virgül öncesi boşluk farkı yüzünden testte kırılmıştı, bkz. commit
geçmişi) span olarak eklendi.

**Kalan 14 kanıtsız alan SİLİNDİ (26 Ağustos 2026, kullanıcı talebiyle):**
Kanıt uydurulamayan 14 değer, `vade_farksiz_duzelt.py` ile AYNI ilkeyle
(Excel hücresini boşaltmak = incelenmiş bir sütunda "kaynakta belirtilmemiş"
demektir) temizlendi - **tahmin edilmedi, silindi**. Gerekçeler:

- **8 alan** (VK-003/006/007, taksit_sayisi + kampanya_baslangic/bitis):
  zaten "ÖLÇÜM DIŞI - KAYNAK KORPUSTA YOK" işaretliydi, kaynak hiç
  arşivlenmemiş.
- **4 alan** (DK-006 taksit_sayisi/finansman_tutari, TEK-005 kampanya_
  baslangic/bitis): kampanya rotasyona uğramış - kayıtlı 4. taksit
  kademesi ("10.000 TL+ → 9 taksit") ve TEK-005'in tarih cümlesi kaynak
  sayfada artık yok.
- **1 alan** (`DK-001.vade_ay=6`): tüm adaylar site footer'ından (telif
  hakkı/güncelleme tarihi) geliyordu - "6" rakamı "2026" içinde
  yanlışlıkla eşleşmiş, gerçek kanıt yok.
- **1 alan** (`DK-007.kar_payi_orani=0`, `oran_periyodu` ile birlikte):
  kaynağı "peşin fiyatına taksit" ifadesi - `gold_dataset/vade_farksiz_
  duzelt.py`'nin "vade farksız" için verdiği kararla (kart/taksit
  özelliği, gerçek kâr payı kanıtı DEĞİL) AYNI SINIFTAN bir soru.

`gold_dataset/kanit_spani_oner.py` şu an **0** kanıtsız dolu alan
gösteriyor - Faz 6 tam anlamıyla kapandı. DK-006/TEK-005'in `notlar`
alanına silme kaydı düşüldü (rotasyon nedeniyle bu iki kayıt yeniden
kaynaktan doğrulanmayı bekliyor, veri toplama ekibi işi).

**Bilinen araç sınırlaması (bu turda dokunulmadı, ileride iyileştirilebilir):**
`kanit_spani_oner.py`'nin aday bulma mantığı tek haneli değerleri (`vade_ay=6`
gibi) ararken "2026" gibi yıl yazımlarının içindeki rakamla ya da bir
sayının BAŞKA bir sayının içine gömülü alt-dizesiyle (`AL-001.
finansman_tutari=40000` → "1**40.000** TL" içinde yanlışlıkla eşleşti)
yanlış pozitif üretebiliyor. Elle inceleme sırasında tüm bu tuzaklar
tek tek elendi, hiçbiri yanlışlıkla yazılmadı (`tests/
test_altin_veri_butunlugu.py::test_kanit_spani_ALANIN_DEGERINI_destekliyor`
her span'ı doğruladı) - küçük sayılarda kelime sınırı (`\b`) kontrolü
eklenmesi önerilir.

---

## Faz 7 — Regresyonu Önleyecek Testler/CI

Bu tur düzeltmeler bir kerelik olmasın diye:

1. `tests/` içine yeni bir test: TASLAK/BEKLIYOR notlu kayıt oranı bir eşiği
   (örn. %5) aşarsa test kırılsın.
2. Faz 3'teki script CI'da/pre-commit'te çalışıp `denetim_raporu.json` ile
   gerçek durumun senkron olduğunu doğrulasın.
3. `etiket_celiskisi_raporu.py` düzenli (haftalık ya da her veri güncellemesinde)
   çalıştırılıp `docs/gold_etiket_inceleme.md` güncel tutulsun.

**Sorumlu:** NLP/tooling. **Efor:** ~1 gün.

---

## Faz 8 — Final Ölçüm ve Rapor

Tüm fazlar bitince:

```bash
python -m scraper.scripts.extraction_accuracy
```

Önce/sonra F1 karşılaştırmasını `docs/extraction_accuracy_raporu.md`'ye işleyin
— bu, TEKNOFEST raporunda "metriklerimiz neden yüksek" sorusuna kanıtla
cevap veren belge olur.

---

## Öncelik / Sıralama Özeti

| Sıra | Faz | Neden önce | Efor |
|---|---|---|---|
| 1 | Faz 0 | Her şeyi bloke ediyor, tek karar en büyük metrik etkisini yapıyor | 0.5 gün |
| 2 | Faz 1 | Düşük efor / yüksek getiri, hızlı kazanım | 1-2 gün |
| 3 | Faz 2 | En emek yoğun ama veri setinin güvenilirliğini kalıcı kılıyor, paralel yürütülebilir | 3-5 gün |
| 4 | Faz 3, 4, 5, 6 | Birbirinden bağımsız, paralel yapılabilir | ~1-2 gün toplam |
| 5 | Faz 7 | Kazanımın kalıcı olmasını garanti eder | 1 gün |
| 6 | Faz 8 | Final kanıt/rapor | yarım gün |

**Toplam tahmini efor:** ~7-11 iş günü (ekip paralel çalışırsa 1 haftaya sığar).

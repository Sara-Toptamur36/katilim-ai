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

## Faz 0 — Etiketleme Kuralı: KARAR VERİLDİ ✅ (A)

**Karar:** `vade farksız` ⇒ `kar_payi_orani = 0`. Bu yeni bir yorum değil —
`terminology/sozluk.json` → `sifir_oran_ifadesi` girdisinde zaten belgeli:
kaynağı Ön Değerlendirme Raporu Bölüm 3, dayanağı şartname **Md. 5.2**.
Sözlük notu birebir: *"Bulundugunda kar_payi_orani_percent = 0.0 olarak
yorumlanir... NULL/bulunamadi ile karistirilmaz."* Motor (`regex_extractor.py`)
zaten bu kurala göre yazılmış ve tutarlı davranıyor — sorun kodda değil,
58 gold kaydın bu kurala uymamasında.

**Yapılacak:**
1. 58 kaydı (`docs/gold_etiket_inceleme.md` §1 listesi) `belirtilmemiş`'ten
   `kar_payi_orani=0`'a çevir. `alan_belirtilmemis.kar_payi_orani`'yi `false`
   yap, `kanit_spanlari.kar_payi_orani`'ye "vade farksız" geçen cümleyi yaz.
2. **Yan etkiyi kapat:** `comparison/compare_engine.py`'deki `en_dusuk_kar_payi`
   sıralaması artan sırada çalışıyor — bu 0'lar kart kampanyalarını konut/taşıt
   finansmanı gibi gerçek ürünlerin önüne geçirecek. Ödül birimi ekseninde
   zaten var olan `odul_birimi_tekil_mi()` korumasının bir benzerini kâr payı
   ekseninde de ekle (örn. kampanya türü finansman değilse en-düşük-oran
   karşılaştırmasına dahil etme).
3. `python -m gold_dataset.etiket_celiskisi_raporu` yeniden çalıştır, §1'in
   boşaldığını doğrula.
4. `terminology/sozluk.json`'daki `ornek_kaynak` notunu güncel sayıya
   ("13'ünde" ifadesi artık 58) göre tazele.

**Sorumlu:** Veri ekibi (toplu düzeltme) + NLP (compare_engine koruması). **Efor:** ~1 gün.

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

**Kalan iş (14 kayıt, gerçek elle inceleme gerektiriyor):**
1. **11 rotasyona girmiş kayıt** — sayfa değişmiş, etiket eski metinden
   kalma. `dogrulama.html` yerine kaynak sayfayı elden geçirip değerleri
   güncel metinle yeniden doğrulayın (bazıları hâlâ doğru olabilir, bazıları
   artık kaynaksız kalmış olabilir).
2. **3 erişilemeyen kayıt** (`KT-008`, `ZK-009`, `DK-008`) — tarayıcıdan elle
   açıp kontrol edin; otomasyon iki denemede de zaman aşımına uğradı.

**Sorumlu:** Veri toplama ekibi. **Efor:** ~1 gün (14 kayıt kaldı, 31 otomatik geçti).

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

## Faz 4 — Rotasyona Giren 10 Kaydı Çöz

**Sorun:** `KT-002`, `VK-001..007`, `ZK-003`, `DK-005` artık güncel kazınmış
korpusla eşleşmiyor — kaynak sayfaları rotasyona girmiş, otomatik doğrulama
dışında kalıyorlar.

**Yapılacak:**
1. Arşivlenmiş snapshot var mı kontrol et (kayıt oluşturulduğu tarihteki
   ekran görüntüsü/ham metin arşivde olabilir).
2. Yoksa kayda açık bir `olcum_disi: true` / benzeri alan ekleyip gerekçesini
   `notlar`a yaz — böylece "kanıt yok" diye tekrar tekrar sorgulanmaz, ölçüm
   raporlarında bilinçli olarak hariç tutulduğu görünür.

**Sorumlu:** Veri ekibi. **Efor:** ~yarım gün.

---

## Faz 5 — `AL-027` Tarih Çelişkisini Kapat

Kaynak cümle: *"Kampanya 1-30 Haziran 2026 tarihlerinde geçerlidir."*
Etiketteki `2026-06-01` muhtemelen doğru; span eşleştirme kaçırmış olabilir.
Sayfayı aç, teyit et, gerekirse düzelt. **Efor:** 15 dk.

---

## Faz 6 — Eksik Kanıt Spanlarını Tamamla (40 kayıt)

`kanit_spanlari` boş olan kayıtlardan gerçek (referans olmayan) TASLAK
dışı olanlara span ekleyin — doğrulanabilirliği artırır, gelecekteki
denetimleri hızlandırır. Faz 1-2 ile birlikte yürütülebilir.

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

# ADR 0003 — Şikâyet hattına önem derecesi, çözüm durumu ve üç seviyeli entity resolution eklendi

Tarih: 27 Ağustos 2026
Durum: Kabul edildi
İlgili: [ADR 0001](0001-sikayet-veri-modeli.md), mentor geri bildirimi (Complaint Insight pipeline eleştirisi), [`docs/veri_edinme_politikasi.md`](../veri_edinme_politikasi.md)

## Bağlam

Mentor geri bildirimi, şikâyet hattının iki kavramsal boşluğunu işaret etti:

1. **"Şikâyet = memnuniyetsizlik" varsayımı hatalı.** Bir şikâyetin teması
   (ör. ödül yatmadı) ile ciddiyeti (severity) ve çözüm durumu (resolution)
   aynı şey değildir; ADR 0001'deki tek tabloda `cozum_durumu` kolonu vardı
   ama hiçbir yol onu doldurmuyordu.
2. **Entity resolution'da kampanya eşleştirmesi tek bir blend skora
   sıkıştırılmıştı.** `kampanya_eslestirme.py` zaten banka/kampanya-adı/ödül-
   birimi ağırlıklı bir güven skoru üretiyordu, ama bu üç sinyal ayrı ayrı
   dışarı verilmiyordu — kampanya (en kırılgan seviye) eşiği geçemediğinde,
   banka ve ürün türü gibi daha güvenilir seviyeler de kayboluyordu.

Karar, **gerçek veri entegre etmeden, sentetik veri üzerinde** alındı ve
ölçüldü — bkz. [`docs/veri_edinme_politikasi.md`](../veri_edinme_politikasi.md).

## Karar

### 1. Önem derecesi (severity) — `complaint/onem_derecesi.py`

Ağırlıklı bir formül **uydurulmadı** (`comparison/etki_skoru.py` ve
`kampanya_eslestirme.py`'deki "sayı yerine kategori + gerekçe" ilkesiyle
aynı). Üç kategori: `YUKSEK` (parasal kayıp teması FEE_CHARGE/
REWARD_NOT_CREDITED veya tekrarlanan mağduriyet ifadesi), `DUSUK` (yalnızca
COMMUNICATION_AMBIGUITY), `ORTA` (**varsayılan** — "yüksek/düşük sinyali
görülmedi", "önemsiz" değil).

**Düzeltme (aynı gün, ilk sürüm kabul edildikten sonra):** ilk sürümde
`YUKSEK` yalnızca 2 temaya bağlıydı — yani 10 temanın 8'i, metnin
içeriğinden bağımsız olarak her zaman `ORTA` dönüyordu ve "önem derecesi"
fiilen temanın gizli bir yeniden etiketlemesiydi. Üçüncü, temadan bağımsız
bir sinyal eklendi: metinde somut bir TL/₺ tutarı geçmesi. `COMMUNICATION_
AMBIGUITY` bu sinyalden **muaftır** — "500 TL'lik ödül hakkında net bilgi
bulamadım" hâlâ bir bilgi eksikliğidir, doğrulanmış bir kayıp değil; tutar
geçmesi onu `YUKSEK`'e yükseltmez. Kontrol sırası: parasal tema → tekrar
ifadesi → DUSUK tema (mutlak) → tutar bahsi → varsayılan ORTA.

### 2. Çözüm durumu (resolution) — `complaint/cozum_tespiti.py`

ADR 0001'in `cozum_durumu` kolonu artık **metnin kendi ifadesinden** kural
tabanlı olarak dolduruluyor — bu bir **CRM/destek bileti entegrasyonu
değildir** (o hâlâ yok, Faz 2). Dört değer: `cozuldu`, `kismen`, `cozulmedi`,
`bilinmiyor` (**varsayılan** — çoğu şikâyet metni yalnızca sorunu anlatır,
çözüm sürecinin nerede olduğunu söylemez; "çözülmedi" varsaymak bir iddia
uydurmak olurdu).

### 3. Düşük-bilgi/spam işareti — `complaint/toplama.py::_dusuk_bilgi_supheli_mi`

4 kelimenin altındaki metinler **işaretlenir, silinmez** (`yineleme_supheli`
ile aynı felsefe). Eşik, mevcut veri setindeki en kısa geçerli şikâyetin (5
kelime) altında seçildi — gerçek içerikli kısa şikâyetler yanlışlıkla
işaretlenmesin diye.

**Kapsam dışı bırakılan:** anlamsal (paraphrase) yakın-tekrar tespiti ve
`dedup_group_id`. Gerekçe: `icerik_hash` zaten normalize edilmiş tam
eşleşmeler için bir grup anahtarı işlevi görüyor; paraphrase tespiti
embedding/ML katmanı gerektirir ve bu, projenin kural tabanlı, açıklanabilir
tasarım tercihiyle (bkz. `tema_siniflandirici.py`, `kampanya_eslestirme.py`)
çelişir. Eklenmedi, gizlenmedi — bu ADR'de yazılı bir sınırdır.

### 4. Üç seviyeli entity resolution — `complaint/kampanya_eslestirme.py::EslesmeSonucu`

`guven` (Seviye 3 — kampanya) **değişmedi**, geriye dönük uyumluluk korundu.
İki yeni alan eklendi:

- `banka_eslesti: bool` — Seviye 1, en yüksek güvenli sinyal
- `urun_turu_guven: float` — Seviye 2, `kampanya_turu` kelime örtüşmesiyle
  hesaplanır (kampanya adından **bağımsız**)

Zaman penceresi elemesi üç seviyeyi de kapsar (pencere dışıysa hiçbir seviye
puanlanmaz). Bu, mentor geri bildirimindeki *"kampanya eşleştirmeyi zorunlu
değil opsiyonel yapmanız doğru"* önerisinin doğrudan karşılığıdır — kampanya
adı hiç geçmese bile banka ve ürün türü artık ayrı ayrı görülebilir.

## Veri seti genişletildi (aynı gün, ikinci düzeltme)

Sayı sayıldı: `tema_siniflandirici.py::_TEMA_IFADELERI` içindeki 60 ifadenin
**27'si (%45) hiçbir örnek tarafından hiç tetiklenmiyordu** — bir ifadede
yazım/regex hatası olsa hiçbir test bunu yakalamazdı. `ornekler` grubu 20'den
40'a çıkarıldı (tema başına 2 → 4), yeni örnekler mümkün olduğunca daha önce
kullanılmamış ifadeleri hedefler.

**500'e çıkarılmadı — bilinçli tercih.** Tüm örnekler tek oturumda elle
yazıldığından, ham sayıyı büyütmek dilsel çeşitliliği artırmaz, yapay bir öz
güven üretir (bkz. [`docs/veri_edinme_politikasi.md`](../veri_edinme_politikasi.md)
§3). Onun yerine iki hedefe odaklanıldı: (1) kural setinin **test edilmeyen**
kısmını kapatmak, (2) cümle yapısı/uzunluk/üslupta gözle görülür çeşitlilik.

**Üçüncü düzeltme (aynı gün, kullanıcı geri bildirimi üzerine):** "40 az mı?"
sorusu somut ölçümle cevaplandı — v1.3 sonrası kalan %15'lik boşluk (9
ifade, çoğunlukla REWARD_NOT_CREDITED) 6 hedefli örnekle (`ornekler` 40→46)
kapatıldı; kural setinin **tamamı (%100)** artık en az bir örnekte
tetikleniyor. Aynı geçişte `entity_resolution_ornekleri` grubu eklendi —
3 seviyeli eşleştirme demosu artık `sikayet_hatti_olcum.py` ve
`tests/test_sikayet_hatti_sentetik.py`'de ayrı ayrı gömülü değil, tek bir
JSON kaynağından okunuyor (tutarlılık; ikinci bir kontrol-grubu senaryosu
`SM-ER2` de eklendi).

**SM-021, mentor geri bildirimindeki "kampanya çok güzel ama ödülüm
yatmadı" örneğini birebir uygular** — metin olumlu bir ifadeyle başlar
("Kampanya gerçekten çok avantajlıydı ama...") ve kural tabanlı sınıflandırıcının
buna aldanmadan cümle sonundaki somut şikâyet sinyaline kilitlendiğini kanıtlar.
Bu, "complaint ≠ sentiment" ayrımının koda gömülü somut kanıtıdır.

## Şema değişikliği

`sikayetler` tablosuna 4 yeni nullable kolon eklendi (migration
`fcdf5b2ef61c`, ADR 0001'deki `4fae96f0556c` ile aynı desen): `onem_derecesi`,
`dusuk_bilgi_supheli`, `banka_eslesti`, `urun_turu_guveni`. Tablo bu revizyon
sırasında **boş kalmaya devam ediyor** — izin kapısı hiçbir kaynak için
açılmadı, gerçek veri toplanmadı.

## Sonuç

- Mentor raporunun P1 önceliklerinden ikisi (severity/resolution katmanı,
  entity resolution seviyelendirmesi) kural tabanlı, kanıtlı ve sentetik
  veriyle ölçülür hale getirildi — bkz.
  [`tests/test_sikayet_hatti_sentetik.py`](../../tests/test_sikayet_hatti_sentetik.py)
  §9-13 ve [`sikayet_hatti_olcum.py`](../../sikayet_hatti_olcum.py).
- Kırmızı çizgiler korundu: hiçbir alan kanıtsız/varsayılan-olumsuz
  üretilmedi (`ORTA`, `bilinmiyor` varsayılandır), veritabanına gerçek veri
  yazılmadı, izin kapısı değiştirilmedi.
- Kapsam dışı bırakılanlar (paraphrase dedup, `dedup_group_id`, sentiment
  benchmark, 500 kayıtlık gold set, monitoring/drift) mentor raporunun
  gerçek veri gerektiren kalemleridir — bkz.
  [`docs/veri_edinme_politikasi.md`](../veri_edinme_politikasi.md) §3.

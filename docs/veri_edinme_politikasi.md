# Veri Edinme Politikası (Data Acquisition Policy)

**Amaç:** Şikâyet/müşteri sesi verisinin (Şikâyetvar veya benzeri bir platform)
hangi koşulda toplanacağını, toplanmazsa sistemin ne yapacağını ve bu kararın
kim tarafından, ne zaman verileceğini tek bir belgede sabitlemek.

Bu belge bir **niyet beyanı değildir** — [`complaint/izin_kapisi.py`](../complaint/izin_kapisi.py)
zaten bunu çalışan bir kontrole çevirmiştir. Bu belge o kontrolün **neden** o
şekilde tasarlandığını ve **hangi soruların hâlâ açık olduğunu** yazılı hale
getirir; mentor geri bildiriminde sorulan "hangi yöntemle, hangi tarih
aralığında, kaç kayıt, tekrarlar nasıl temizlenecek" sorularının resmi
cevabıdır.

---

## 1. Karar akışı

```
GERCEK VERI (ör. Sikayetvar)
        │
        ▼
complaint/izin_kapisi.py::izni_zorunlu_kil(kaynak)
        │
        ▼
   izin var mi? (kaynak bazli, kayitli, dogrulanmis)
   ┌────┴────┐
  EVET       HAYIR
   │          │
 ingest    IzinYok firlatilir
 (Faz 2)   → complaint/toplama.py::hazirla() CALISMAZ
            → sikayetler tablosuna HICBIR SEY yazilmaz
            → sistem SENTETIK veri setiyle devam eder
              (tests/veri/kapsam_disi/sentetik_musteri_sesi.json)
```

Bu, mentor geri bildirimindeki "REAL DATA → permission check → allowed? →
YES: ingest, NO: synthetic/mock" akışının birebir karşılığıdır — fark, bizim
akışımızda bu bir tasarım önerisi değil, [izin_kapisi.py](../complaint/izin_kapisi.py)'de
çalışan kod.

## 2. Faz 1 kararı: sentetik veri BİRİNCİL yoldur, yedek değil

Mentor akışında "synthetic/mock" dal, iznin reddedildiği durumda başvurulan
bir **yedek**tir. Bizim projemizde bu dal Faz 1'in **birincil ve tek** yoludur
— gerçek veriye bağımlı olmadan geliştirilen, test edilen ve ölçülen bir
sistem. Gerekçe:

- Kurumsal/hukuki (KVKK) onay süreci Faz 1 takviminde tamamlanamaz.
- Şartname Md. 5.1 veri setini katılım bankalarının resmî web siteleriyle
  tanımlar; şikâyet platformu şartnamenin zorunlu kapsamında değildir —
  projenin kendi eklentisidir, riski bilerek üstlenilir.
- Bir sistemi "gerçek veri gelene kadar çalışmaz" diye bırakmak yerine,
  boru hattının tamamını (PII, yineleme, tema, önem derecesi, çözüm durumu,
  entity resolution) sentetik veriyle **uçtan uca ölçülür** hale getirmek,
  gerçek veri geldiğinde geçiş riskini azaltır.

## 3. Sorulan sorulara cevap

| Soru | Cevap |
|---|---|
| Veriyi hangi yöntemle alacağız? | Henüz belirlenmedi — kurumsal onay öncesi bir yöntem seçmek erken taahhüt olurdu. Onay geldiğinde: [izin_kapisi.py](../complaint/izin_kapisi.py)'ye kaynak bazlı bir izin kaydı eklenir, `kaynak`/`onaylayan`/`kurum`/`onay_tarihi`/`kapsam` alanları zorunludur. |
| Erişim izni/koşulları uygun mu? | Bilinmiyor — mentor raporunun vurguladığı gibi, kamuya açık bir metnin yeniden kullanılabilir/eğitime uygun olduğu anlamına gelmediği kabul edilir. Bu soru kurumsal/hukuki sürecin parçasıdır, mühendislik kararıyla atlanamaz. |
| Hangi tarih aralığı? | Belirlenmedi — izin kaydındaki `kapsam` alanı bunu taşıyacak şekilde tasarlandı (bkz. `ZORUNLU_ALANLAR`). |
| Kaç kayıt yeterli? | Belirlenmedi. Sentetik tarafta hâlâ küçük bir ölçekte (42 örnek: 20 tema + 22 PII/dedup, artı 12 severity/resolution/spam örneği — v1.2) çalışılıyor; mentorun önerdiği ~500 kayıtlık gold set ölçeğine sentetik veriyle ulaşmak yapay çeşitlilik riski taşır (bkz. [kapsam_ve_veri_ayrimi.md §6](kapsam_ve_veri_ayrimi.md)). |
| Aynı şikâyetin tekrarları nasıl temizlenecek? | Kural tabanlı, normalize edilmiş içerik hash'i ile (`complaint/toplama.py::_dedup_anahtari`) — **silme değil işaretleme**. 5+2 çift ile ölçülüyor (v1.1). Anlamsal (paraphrase) yakın-tekrar tespiti kapsam dışı bırakıldı — bu, kural tabanlı sistemin bilinçli sınırıdır (embedding/ML katmanı gerektirir). |
| Sayfa/arama sonuçlarının örnekleme yanlılığı nasıl yönetilecek? | Ürün seviyesinde henüz yönetilmiyor (toplama yöntemi belirlenmediği için). API seviyesinde `MusteriSesiYogunlukYanit.orneklem_notu` alanı her yanıtta örneklem uyarısını taşır — bkz. §4. |
| Veri alınamazsa sistem ne yapacak? | Bu belgenin konusu tam olarak budur: sentetik veriyle çalışmaya devam eder, `GET /musteri-sesi/yogunluk-ozeti` dürüstçe `kapsam_durumu: "izin_yok"` döner, hiçbir sayı uydurulmaz. |

## 4. Örneklem yanlılığı — kalıcı uyarı

Gerçek veri toplanmaya başlasa bile, bir şikâyet platformuna yazan
kullanıcılar **tüm müşterileri temsil etmez** — sorun yaşayanların platforma
yazma ihtimali daha yüksektir. Bu yüzden:

- Sistem **asla** "Bankanın müşterilerinin %X'i memnun değil" gibi bir
  genelleme üretmeyecek.
- Sistem yalnızca "incelenen geri bildirimlerde negatif sinyal baskındır"
  gibi, örneklemi açıkça sınırlayan bir çerçeveleme kullanacaktır.
- Bu kural [`MusteriSesiYogunlukYanit.orneklem_notu`](../api/schemas.py)
  alanıyla API seviyesinde zorunlu kılınmıştır — dashboard bu alanı
  gizleyemez, her yanıtta gelir.

## 5. Bu belgenin sahibi ve güncellenme koşulu

Bu belge, kurumsal/hukuki onay süreci ilerledikçe güncellenmelidir. Onay
geldiğinde ilk yapılacak şey bu belgeye **gerçek bir izin kaydı örneği** ve
seçilen toplama yöntemini eklemektir — kod tarafında hiçbir değişiklik
gerekmez, çünkü [izin_kapisi.py](../complaint/izin_kapisi.py) zaten kaynak
bazlı izin kaydını bekleyecek şekilde tasarlanmıştır.

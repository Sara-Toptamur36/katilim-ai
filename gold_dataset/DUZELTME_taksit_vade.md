# Düzeltme: `taksit_sayisi` ile `vade_ay` karışıklığı (8 kayıt)

## Sorun

Aynı ifade altın sette iki farklı alana yazılmış:

| Kayıt | Kampanya adı | Değer nerede | Doğru mu |
|-------|--------------|--------------|----------|
| AL-002 | "MTV Ödemelerinize Vade Farksız 3 Taksit" | `taksit_sayisi=3` | ✅ |
| VK-001 | "MTV Ödemelerinde Vade Farksız 3 Taksit" | `vade_ay=3` | ❌ |

İkisi de olamaz.

## Neden acele düzeltilmeli

`vade_ay` **ölçülen** bir sütun. Taksit adedi oraya yazıldığında motor ne
üretirse üretsin kayıtların bir kısmı yanlış sayılır — yani ölçüm, motorun
hatasını değil **etiketleyicilerin anlaşmazlığını** ölçer. Bu hata türü en
pahalısıdır: sebep motorda aranır, saatler harcanır, orada yoktur.

## Ayrım

- **`taksit_sayisi` bir ADETTİR.** "3 taksit" = 3 ödeme.
- **`vade_ay` bir SÜREDİR.** "12 ay vade" = finansmanın 12 ayda kapanması.

Pratik ölçüt: **MTV, vergi, alışveriş, fatura ödemesinde "vade" diye bir
kavram yoktur.** Oralarda değer `taksit_sayisi`'dir. `vade_ay` yalnızca
gerçek bir finansman ürününde (ihtiyaç, konut, taşıt finansmanı) doldurulur.

## Düzeltilecek kayıtlar

Uyarıyı her an şu komutla görebilirsin:

```bash
python gold_dataset/excel_to_json.py
```

| Excel satırı | Kayıt | Şu an | Ekran görüntüsü |
|---|---|---|---|
| 10 | KT-004 | `vade_ay=3` | `ekran_goruntuleri/KT-004.png` |
| 20 | VK-001 | `vade_ay=3` | `ekran_goruntuleri/VK-001.png` |
| 21 | VK-002 | `vade_ay=3` | `ekran_goruntuleri/VK-002.png` |
| 22 | VK-003 | `vade_ay=5` | `ekran_goruntuleri/VK-003.png` |
| 25 | VK-006 | `vade_ay=5` | `ekran_goruntuleri/VK-006.png` |
| 37 | ZK-003 | `vade_ay=4` | `ekran_goruntuleri/ZK-003.png` |
| 55 | DK-006 | `vade_ay=9` | `ekran_goruntuleri/DK-006.png` |
| 56 | DK-007 | `vade_ay=3` | `ekran_goruntuleri/DK-007.png` |

Sekizinin de `giren_kisi` alanı Sara Toptamur ve **hepsinin ekran görüntüsü
var** — yani kaynağa bakmadan düzeltmek gerekmiyor.

## Adım adım (örnek: VK-001)

1. **Önce ekran görüntüsünü aç:** `gold_dataset/ekran_goruntuleri/VK-001.png`

   Sayfada şu yazıyor:
   > "31 Temmuz 2026 tarihine kadar motorlu taşıtlar verginizi bireysel Vakıf
   > Katılım Kredi Kartı'yla ödeyin, vade farksız 3 taksit avantajından
   > yararlanın!"

   Bu bir **vergi ödemesinin taksitlendirilmesi**. Finansman vadesi yok.
   Karar: değer `taksit_sayisi`'ne ait.

   > Bu adım atlanamaz. Kampanya adına bakıp karar vermek, ilk hatanın
   > yapılış şeklidir.

2. **`gold_dataset/altin_veri_seti.xlsx` dosyasını aç**, `2. Altin Veri Seti`
   sekmesine geç.

3. **Satır 20** (kayit_id = VK-001):
   - **I20** hücresini (`vade_ay`) **boşalt** — sil, 0 yazma. Boş hücre
     "kaynakta belirtilmemiş" demektir ve doğrusu budur.
   - **V20** hücresine (`taksit_sayisi`) **3** yaz.

4. **X20** hücresine (`kanit_spanlari`) kanıt cümlesini ekle. Biçim
   `alan: cümle`, her alan ayrı satırda (hücre içinde alt satır: `Alt+Enter`):

   ```
   taksit_sayisi: vade farksız 3 taksit avantajından yararlanın
   ```

   > Cümle sayfada **birebir** geçmeli. Özetleme, kendi cümleni yazma —
   > test bunu kontrol ediyor ve tutmazsa kırmızı verir. Kanıt spanı, bugün
   > verdiğin kararın gerekçesini dondurur; sayfa yarın değişirse gerekçe
   > kaybolmaz. (Bu 8 kaydın sıkıntısı tam olarak buydu: kaynak sayfaları
   > artık ham veride yok.)

5. **U20**'ye (`notlar`) mevcut notun sonuna ekle:

   ```
   ; 21 Agustos 2026: vade_ay=3 -> taksit_sayisi=3 duzeltildi, kaynak
   ekran goruntusuyle dogrulandi (vergi odemesi taksitlendirmesi, vade degil)
   ```

6. **Excel'i kaydet ve kapat.** (Açık kalırsa bir sonraki adım dosyayı
   okuyamaz.)

7. **Üret ve doğrula:**

   ```bash
   python gold_dataset/excel_to_json.py
   ```

   VK-001 uyarı listesinden çıkmış olmalı; uyarı sayısı 8'den 7'ye düşer.

   ```bash
   python -m gold_dataset.split_manifest_uret
   ```

   ```bash
   python -m pytest tests/test_altin_veri_butunlugu.py tests/test_taksit_vade_ayrimi.py -q
   ```

   Hepsi yeşilse düzeltme tamam.

## Dikkat

- **JSON'u elle düzenleme.** `altin_veri_seti.json` Excel'den üretilir;
  oraya yazdığın her şey bir sonraki `excel_to_json.py` çalıştırmasında silinir.
- **`vade_ay`'a 0 yazma.** 0 "vade sıfır" demektir; kastedilen "kaynakta yok".
  O da boş hücredir.
- **Kanıt spanı yalnızca DOLU alana verilir.** Boşalttığın `vade_ay` için
  span yazma — "kaynakta yok" iddiasının kanıtı cümle göstermek değil,
  gösterememektir.
- Emin olamadığın bir kayıt varsa **düzeltme, sor.** Yanlış yöne düzeltilmiş
  bir kayıt, uyarılı kayıttan kötüdür: uyarı görünür, yanlış düzeltme görünmez.

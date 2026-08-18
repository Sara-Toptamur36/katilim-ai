# Veri Kapsam Raporu (4 Eksenli)

Uretim tarihi: 2026-08-18

Mentorluk raporu II (Bolum 6.3): "veri eksikligi yalnizca toplam kampanya sayisina bakilarak analiz edilmemeli" - bu rapor banka, urun ailesi, zaman ve alan eksenlerinde ayri ayri kapsam gosterir. Yeni veri toplamaz; scraper/raw_data'daki mevcut veriyi regex ile ozetler (bkz. script docstring'i - Postgres/Docker'a bagimli DEGILDIR).

**Bilinen sinirlama:** ACTIVE/EXPIRED yasam dongusu durumu yalnizca Postgres'te hesaplanir; bu rapor DB okumadigi icin "aktif kampanya" sayisi icermiyor - yalnizca tekil kampanya ve snapshot sayilari.

## 1. Banka ekseni

| Banka | Tekil kampanya | Snapshot (raw_data) | Gold kayit |
|---|---|---|---|
| Albaraka Türk | 14 | 16 | 6 |
| Dünya Katılım | 5 | 10 | 7 |
| Hayat Finans | 10 | 12 | 5 |
| Kuveyt Türk | 13 | 13 | 7 |
| T.O.M. Katılım | 3 | 3 | 3 |
| Türkiye Emlak Katılım | 80 | 100 | 7 |
| Türkiye Finans | 13 | 16 | 7 |
| Vakıf Katılım | 3 | 3 | 8 |
| Ziraat Katılım | 89 | 90 | 8 |

## 2. Urun ailesi ekseni

En son gorulen versiyon uzerinden hesaplanir (ayni kampanyanin eski snapshot'lari tekrar sayilmaz).

| Urun ailesi (kampanya_turu) | Sayi | Alan doluluk % |
|---|---|---|
| Kart Kampanyasi | 133 | %21.4 |
| Belirtilmemis | 38 | %16.8 |
| Alisveris Puani Kampanyasi | 36 | %20.0 |
| Konut Finansmani Kampanyasi | 7 | %31.4 |
| Ihtiyac Finansmani Kampanyasi | 6 | %40.0 |
| Yatirim Urunu Kampanyasi | 4 | %0.0 |
| Yeni Musteri Kampanyasi | 3 | %40.0 |
| Finansman Kampanyasi | 2 | %20.0 |
| Tasit Finansmani Kampanyasi | 1 | %0.0 |

## 3. Zaman ekseni

- Ilk gorulme: 2026-07-31
- Son gorulme: 2026-08-11
- Kampanya basina ortalama versiyon sayisi: 1.14
- Coklu versiyonlu (gercekten degismis) kampanya sayisi: 33
- Bayatlik (son taramadan bu yana gecen gun): 7

## 4. Alan ekseni

Kar payi / vade / taksit / odul / masraf alanlarinin en son versiyonda ne siklikta dolu oldugu (regex katmaniyla - Yagmur'un NER/LLM katmani daha fazla doldurabilir, bu rapor bir ALT SINIR gosterir, kesin doluluk degil).

| Alan | Dolu | Toplam | Doluluk % |
|---|---|---|---|
| kar_payi_orani_percent | 37 | 230 | %16.1 |
| vade_ay | 5 | 230 | %2.2 |
| taksit_sayisi | 111 | 230 | %48.3 |
| odul_miktari | 83 | 230 | %36.1 |
| masraf_durumu | 5 | 230 | %2.2 |

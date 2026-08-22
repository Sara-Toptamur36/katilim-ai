# Veri Kapsam Raporu (4 Eksenli)

Uretim tarihi: 2026-08-22

Mentorluk raporu II (Bolum 6.3): "veri eksikligi yalnizca toplam kampanya sayisina bakilarak analiz edilmemeli" - bu rapor banka, urun ailesi, zaman ve alan eksenlerinde ayri ayri kapsam gosterir. Yeni veri toplamaz; scraper/raw_data'daki mevcut veriyi regex ile ozetler (bkz. script docstring'i - Postgres/Docker'a bagimli DEGILDIR).

**Bilinen sinirlama:** ACTIVE/EXPIRED yasam dongusu durumu yalnizca Postgres'te hesaplanir; bu rapor DB okumadigi icin "aktif kampanya" sayisi icermiyor - yalnizca tekil kampanya ve snapshot sayilari.

## 1. Banka ekseni

| Banka | Tekil kampanya | Snapshot (raw_data) | Gold kayit |
|---|---|---|---|
| Albaraka Türk | 37 | 39 | 8 |
| Dünya Katılım | 45 | 55 | 7 |
| Hayat Finans | 10 | 18 | 5 |
| Kuveyt Türk | 110 | 113 | 7 |
| T.O.M. Katılım | 13 | 13 | 3 |
| Türkiye Emlak Katılım | 84 | 107 | 7 |
| Türkiye Finans | 15 | 17 | 7 |
| Vakıf Katılım | 3 | 3 | 8 |
| Ziraat Katılım | 108 | 108 | 8 |

## 2. Urun ailesi ekseni

En son gorulen versiyon uzerinden hesaplanir (ayni kampanyanin eski snapshot'lari tekrar sayilmaz).

| Urun ailesi (kampanya_turu) | Sayi | Alan doluluk % |
|---|---|---|
| Kart Kampanyasi | 250 | %24.8 |
| Belirtilmemis | 61 | %14.1 |
| Konut Finansmani Kampanyasi | 53 | %24.9 |
| Alisveris Puani Kampanyasi | 37 | %20.0 |
| Finansman Kampanyasi | 9 | %15.6 |
| Ihtiyac Finansmani Kampanyasi | 6 | %50.0 |
| Yatirim Urunu Kampanyasi | 4 | %0.0 |
| Yeni Musteri Kampanyasi | 3 | %40.0 |
| Tasit Finansmani Kampanyasi | 2 | %0.0 |

## 3. Zaman ekseni

- Ilk gorulme: 2026-07-31
- Son gorulme: 2026-08-22
- Kampanya basina ortalama versiyon sayisi: 1.11
- Coklu versiyonlu (gercekten degismis) kampanya sayisi: 39
- Bayatlik (son taramadan bu yana gecen gun): 0

## 4. Alan ekseni

Kar payi / vade / taksit / odul / masraf alanlarinin en son versiyonda ne siklikta dolu oldugu (regex katmaniyla - Yagmur'un NER/LLM katmani daha fazla doldurabilir, bu rapor bir ALT SINIR gosterir, kesin doluluk degil).

| Alan | Dolu | Toplam | Doluluk % |
|---|---|---|---|
| kar_payi_orani_percent | 110 | 425 | %25.9 |
| vade_ay | 14 | 425 | %3.3 |
| taksit_sayisi | 231 | 425 | %54.4 |
| odul_miktari | 121 | 425 | %28.5 |
| masraf_durumu | 8 | 425 | %1.9 |

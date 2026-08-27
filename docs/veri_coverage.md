# Veri Kapsam Raporu (4 Eksenli)

Uretim tarihi: 2026-08-27

Mentorluk raporu II (Bolum 6.3): "veri eksikligi yalnizca toplam kampanya sayisina bakilarak analiz edilmemeli" - bu rapor banka, urun ailesi, zaman ve alan eksenlerinde ayri ayri kapsam gosterir. Yeni veri toplamaz; scraper/raw_data'daki mevcut veriyi regex ile ozetler (bkz. script docstring'i - Postgres/Docker'a bagimli DEGILDIR).

**Bilinen sinirlama:** ACTIVE/EXPIRED yasam dongusu durumu yalnizca Postgres'te hesaplanir; bu rapor DB okumadigi icin "aktif kampanya" sayisi icermiyor - yalnizca tekil kampanya ve snapshot sayilari.

## 1. Banka ekseni

| Banka | Tekil kampanya | Snapshot (raw_data) | Gold kayit |
|---|---|---|---|
| Albaraka Türk | 37 | 45 | 33 |
| Dünya Katılım | 45 | 57 | 37 |
| Hayat Finans | 13 | 30 | 9 |
| Kuveyt Türk | 110 | 123 | 63 |
| T.O.M. Katılım | 13 | 13 | 13 |
| Türkiye Emlak Katılım | 84 | 112 | 57 |
| Türkiye Finans | 15 | 18 | 14 |
| Vakıf Katılım | 100 | 106 | 10 |
| Ziraat Katılım | 108 | 119 | 62 |

## 2. Urun ailesi ekseni

En son gorulen versiyon uzerinden hesaplanir (ayni kampanyanin eski snapshot'lari tekrar sayilmaz).

| Urun ailesi (kampanya_turu) | Sayi | Alan doluluk % |
|---|---|---|
| Kart Kampanyasi | 392 | %15.5 |
| Belirtilmemis | 61 | %7.2 |
| Ticari Kampanya | 17 | %18.8 |
| Finansman Kampanyasi | 13 | %6.2 |
| Yeni Musteri Kampanyasi | 12 | %20.0 |
| Yatirim Urunu Kampanyasi | 8 | %5.0 |
| Ihtiyac Finansmani Kampanyasi | 7 | %45.7 |
| Tasit Finansmani Kampanyasi | 6 | %20.0 |
| Konut Finansmani Kampanyasi | 3 | %40.0 |
| POS Kampanyasi | 3 | %0.0 |
| Sigorta/BES Kampanyasi | 3 | %20.0 |

## 3. Zaman ekseni

- Ilk gorulme: 2026-07-31
- Son gorulme: 2026-08-26
- Kampanya basina ortalama versiyon sayisi: 1.19
- Coklu versiyonlu (gercekten degismis) kampanya sayisi: 74
- Bayatlik (son taramadan bu yana gecen gun): 1

## 4. Alan ekseni

Kar payi / vade / taksit / odul / masraf alanlarinin en son versiyonda ne siklikta dolu oldugu (regex katmaniyla - Yagmur'un NER/LLM katmani daha fazla doldurabilir, bu rapor bir ALT SINIR gosterir, kesin doluluk degil).

| Alan | Dolu | Toplam | Doluluk % |
|---|---|---|---|
| kar_payi_orani_percent | 12 | 525 | %2.3 |
| vade_ay | 13 | 525 | %2.5 |
| taksit_sayisi | 196 | 525 | %37.3 |
| odul_miktari | 158 | 525 | %30.1 |
| masraf_durumu | 11 | 525 | %2.1 |

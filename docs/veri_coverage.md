# Veri Kapsam Raporu (4 Eksenli)

Uretim tarihi: 2026-08-22

Mentorluk raporu II (Bolum 6.3): "veri eksikligi yalnizca toplam kampanya sayisina bakilarak analiz edilmemeli" - bu rapor banka, urun ailesi, zaman ve alan eksenlerinde ayri ayri kapsam gosterir. Yeni veri toplamaz; scraper/raw_data'daki mevcut veriyi regex ile ozetler (bkz. script docstring'i - Postgres/Docker'a bagimli DEGILDIR).

**Bilinen sinirlama:** ACTIVE/EXPIRED yasam dongusu durumu yalnizca Postgres'te hesaplanir; bu rapor DB okumadigi icin "aktif kampanya" sayisi icermiyor - yalnizca tekil kampanya ve snapshot sayilari.

## 1. Banka ekseni

| Banka | Tekil kampanya | Snapshot (raw_data) | Gold kayit |
|---|---|---|---|
| Albaraka Türk | 14 | 16 | 8 |
| Dünya Katılım | 5 | 15 | 7 |
| Hayat Finans | 10 | 18 | 5 |
| Kuveyt Türk | 13 | 15 | 7 |
| T.O.M. Katılım | 13 | 13 | 3 |
| Türkiye Emlak Katılım | 81 | 103 | 7 |
| Türkiye Finans | 25 | 28 | 7 |
| Vakıf Katılım | 3 | 3 | 8 |
| Ziraat Katılım | 109 | 111 | 8 |

## 2. Urun ailesi ekseni

En son gorulen versiyon uzerinden hesaplanir (ayni kampanyanin eski snapshot'lari tekrar sayilmaz).

| Urun ailesi (kampanya_turu) | Sayi | Alan doluluk % |
|---|---|---|
| Kart Kampanyasi | 172 | %22.3 |
| Belirtilmemis | 38 | %16.8 |
| Alisveris Puani Kampanyasi | 37 | %20.0 |
| Ihtiyac Finansmani Kampanyasi | 9 | %42.2 |
| Konut Finansmani Kampanyasi | 7 | %31.4 |
| Yatirim Urunu Kampanyasi | 4 | %0.0 |
| Yeni Musteri Kampanyasi | 3 | %40.0 |
| Finansman Kampanyasi | 2 | %20.0 |
| Tasit Finansmani Kampanyasi | 1 | %0.0 |

## 3. Zaman ekseni

- Ilk gorulme: 2026-07-31
- Son gorulme: 2026-08-22
- Kampanya basina ortalama versiyon sayisi: 1.18
- Coklu versiyonlu (gercekten degismis) kampanya sayisi: 40
- Bayatlik (son taramadan bu yana gecen gun): 0

## 4. Alan ekseni

Kar payi / vade / taksit / odul / masraf alanlarinin en son versiyonda ne siklikta dolu oldugu (regex katmaniyla - Yagmur'un NER/LLM katmani daha fazla doldurabilir, bu rapor bir ALT SINIR gosterir, kesin doluluk degil).

| Alan | Dolu | Toplam | Doluluk % |
|---|---|---|---|
| kar_payi_orani_percent | 50 | 273 | %18.3 |
| vade_ay | 7 | 273 | %2.6 |
| taksit_sayisi | 140 | 273 | %51.3 |
| odul_miktari | 92 | 273 | %33.7 |
| masraf_durumu | 10 | 273 | %3.7 |

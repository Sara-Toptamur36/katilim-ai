// GECICI: API'de henuz terminoloji sozlugunu donen bir endpoint yok
// (bkz. terminology/sozluk.json - Yagmur'un modulu, ama api/main.py'da
// bunu servis eden bir /terminoloji endpoint'i tanimli degil).
//
// Bu dosya, sozluk.json ile AYNI alan adlariyla (standart_terim,
// gelenek_karsilik, aciklama) birebir uyumlu mock veri saglar; boylece
// arayuz Sara gercek endpoint'i eklemeden once gelistirilebilir.
//
// Sara /terminoloji (veya benzeri) endpoint'ini eklediginde, TerminolojiSozlugu.jsx
// icindeki tek satirlik import degisir: bu dosya yerine api/client.js'deki
// gercek fonksiyon cagrilir - baska hicbir sey degismez.
export const MOCK_TERIMLER = [
  {
    standart_terim: "Kâr Payı Oranı",
    gelenek_karsilik: "Faiz Oranı",
    aciklama: "Katılım bankacılığında finansman/hesap üzerinden elde edilen kazanç oranı.",
  },
  {
    standart_terim: "Finansman Maliyeti",
    gelenek_karsilik: "Kredi Maliyeti (Faiz + Masraflar Toplamı)",
    aciklama: "Kâr payı oranı ile tahsis ücreti/masrafların toplamından oluşan gerçek maliyet.",
  },
  {
    standart_terim: "Katılım Fonu",
    gelenek_karsilik: "Vadeli Mevduat",
    aciklama: "Katılım bankalarında, mevduat yerine kâr/zarara ortak olunan hesap türü.",
  },
  {
    standart_terim: "Masrafsız Finansman",
    gelenek_karsilik: "Masrafsız Kredi",
    aciklama: "Dosya/ekspertiz gibi ek masraf alınmayan finansman kampanyası.",
  },
  {
    standart_terim: "Avantajlı Finansman",
    gelenek_karsilik: "İndirimli Kredi",
    aciklama: "Standart orana göre daha uygun koşullar sunan kampanya.",
  },
  {
    standart_terim: "Vade Süresi",
    gelenek_karsilik: "Kredi Vadesi",
    aciklama: "Finansmanın ay cinsinden geri ödeme süresi.",
  },
  {
    standart_terim: "Ödül Miktarı",
    gelenek_karsilik: "Kampanya Hediyesi",
    aciklama: "Mil, Gram, Puan gibi farklı birimlerde verilen kampanya ödülü.",
  },
  {
    standart_terim: "Niteliksel Sıfır Oran İfadesi",
    gelenek_karsilik: "Faizsiz Kredi",
    aciklama: "\"Kâr payı yok\", \"vade farksız\" gibi sayı içermeyen sıfır-oran ifadeleri.",
  },
];

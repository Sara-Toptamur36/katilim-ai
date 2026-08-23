// KatilimAI - ekranda gosterilen sayilarin TEK kaynagi.
//
// IKI FARKLI TARIH VAR, BILEREK AYRI TUTULUYOR:
//
//   VERI_TARIHI  -> kampanya hacmi, banka dagilimi, alan doluluk.
//                   PostgreSQL'den okundu, GUNCEL.
//   OLCUM_TARIHI -> makro F1, RAG Recall, cekimserlik, test sayisi.
//                   Belirli bir veri seti uzerinde OLCULDU.
//
// Ikisini tek tarihle gostermek YANILTICI olurdu: 23 Agustos'ta veri
// 251'den 447 kampanyaya cikti (Zeynep'in sitemap taramasi), ancak
// dogruluk olcumleri hala 251'lik set uzerinde yapilmis degerlerdir.
// "447 kampanyada %98,28 dogruluk" demek yanlis olur - o oran o sette
// olculmedi. Yeniden olcum yapilana kadar ayrim ekranda korunur.
export const VERI_TARIHI = "23 Ağustos 2026";
export const OLCUM_TARIHI = "18 Ağustos 2026";
export const OLCUM_VERI_SETI = "251 tekil kampanya / 817 parçalık indeks";

export const OLCUMLER = {
  // --- VERI: guncel, PostgreSQL'den (VERI_TARIHI) ---
  veri: {
    tekilKampanya: 447,
    anlikGoruntu: 496,
    kapsananBanka: 9,
    toplamBanka: 10,
    haricBanka: "Adil Katılım",
    haricSebep: "kampanya/ürün yayını bulunmadığı için hariç",
    goldKayit: 64,
    goldGercekBanka: 60,
    goldOrnekSenaryo: 4, // sartnamedeki A/B/C/D Bankasi ornegi
  },
  // --- OLCUM: 251'lik set uzerinde, 18 Agustos (OLCUM_TARIHI) ---
  cikarim: {
    doluAlanDogrulugu: 98.48,
    doluAlanDetay: "65/66 alan",
    bosAlanDogrulugu: 99.17,
    bosAlanDetay: "120/121 alan - 1 yanlış pozitif",
    makroF1: 98.28,
    makroF1Detay: "7 ölçülebilir alan, 5'i %100",
  },
  kapsam: {
    hassasiyet: "24/24",
    ozgulluk: "10/10",
  },
  rag: {
    // DIKKAT: bu 817/263, Recall degerlerinin OLCULDUGU indekstir.
    // Calisan sistemdeki guncel indeks SISTEM_DURUMU'nda (1907 parca) -
    // ikisi ayri, cunku Recall yeni indekste yeniden olculmedi.
    indekslenenParca: 817,
    belgeSayisi: 263,
    indeksTarihi: "17 Ağustos 2026",
    recall5: 93.75,
    recall3: 93.75,
    recall5Detay: "30/32 kampanya",
    recall1Alt: 87.5,
    recall1Ust: 93.75,
    recall1Not: "koşular arası oynuyor",
    abstention: 100,
    abstentionDetay: "5/5 alan dışı soruda cevap üretilmedi",
  },
  test: {
    gecen: 723,
    yavas: 44,
  },
  bilinenHatalar: [
    {
      kod: "DK-002",
      alan: "Ödül miktarı",
      aciklama: "Gold değeri doğrulandı, çıkarım motoru yanılıyor.",
    },
    {
      kod: "TF-001",
      alan: "Kâr payı oranı",
      aciklama: "20 Ağustos'ta düzeltildi: \"Kâr paysız ... Yedek Hesap\" yanlış pozitifi (2. bir örnekle doğrulanıp) dar kapsamlı bir guard ile giderildi; sayfadaki gerçek (vadeye göre değişen) oranlar artık kar_payi_tablosu alanında olduğu gibi gösteriliyor, tek sayıya indirgenmiyor. Regex-only fallback katmanında (GPU'suz demo yolu) hâlâ farklı bir düşük güvenli tahmin sorunu var — bilinen, kabul edilmiş bir sınırlama.",
    },
  ],
};

// PostgreSQL'den, VERI_TARIHI itibariyle. gold sutunu
// gold_dataset/altin_veri_seti.json'dan banka bazinda sayilmistir.
export const BANKA_DAGILIMI = [
  { banka: "Kuveyt Türk",           tekil: 121, snapshot: 123, gold: 7 },
  { banka: "Ziraat Katılım",        tekil: 109, snapshot: 111, gold: 8 },
  { banka: "Türkiye Emlak Katılım", tekil: 84,  snapshot: 106, gold: 7 },
  { banka: "Dünya Katılım",         tekil: 45,  snapshot: 55,  gold: 7 },
  { banka: "Albaraka Türk",         tekil: 37,  snapshot: 39,  gold: 8 },
  { banka: "Türkiye Finans",        tekil: 25,  snapshot: 28,  gold: 7 },
  { banka: "T.O.M. Katılım",        tekil: 13,  snapshot: 13,  gold: 3 },
  { banka: "Hayat Finans",          tekil: 10,  snapshot: 18,  gold: 5 },
  { banka: "Vakıf Katılım",         tekil: 3,   snapshot: 3,   gold: 8 },
];

// Doluluk: o urun ailesindeki kampanyalarda 5 izlenen alanin
// (kar payi, vade, taksit, odul, masraf) ne kadarinin dolu oldugu.
export const URUN_AILESI = [
  { ad: "Belirtilmemiş",                 sayi: 234, doluluk: 2.7 },
  { ad: "Kart Kampanyası",               sayi: 153, doluluk: 21.3 },
  { ad: "Alışveriş Puanı Kampanyası",    sayi: 37,  doluluk: 20.0 },
  { ad: "Konut Finansmanı Kampanyası",   sayi: 7,   doluluk: 28.6 },
  { ad: "İhtiyaç Finansmanı Kampanyası", sayi: 6,   doluluk: 36.7 },
  { ad: "Yatırım Ürünü Kampanyası",      sayi: 4,   doluluk: 0.0 },
  { ad: "Yeni Müşteri Kampanyası",       sayi: 3,   doluluk: 40.0 },
  { ad: "Finansman Kampanyası",          sayi: 2,   doluluk: 20.0 },
  { ad: "Taşıt Finansmanı Kampanyası",   sayi: 1,   doluluk: 0.0 },
];

export const ZAMAN_EKSENI = {
  ilkGorulme: "31 Temmuz 2026",
  sonGorulme: "22 Ağustos 2026",
  bayatlikGun: 1,
};

// Alan bazinda veri doluluk - PostgreSQL'den, tekil kampanya bazinda.
// NOT: Bu oranlar YALNIZCA regex katmaninin sonucudur. NER/LLM katmani
// daha fazlasini doldurur; bu bir ALT SINIR gostergesidir.
export const ALAN_DOLULUGU = [
  { alan: "Taksit sayısı",   dolu: 130, toplam: 447 },
  { alan: "Ödül miktarı",    dolu: 85,  toplam: 447 },
  { alan: "Kâr payı oranı",  dolu: 34,  toplam: 447 },
  { alan: "Vade",            dolu: 9,   toplam: 447 },
  { alan: "Masraf durumu",   dolu: 5,   toplam: 447 },
];

export const KAYNAK_TAKIP = [
  { banka: "Kuveyt Türk",           url: "kuveytturk.com.tr/kampanyalar/kendim-icin" },
  { banka: "Ziraat Katılım",        url: "ziraatkatilim.com.tr/kart-kampanyalari" },
  { banka: "Türkiye Emlak Katılım", url: "emlakkatilim.com.tr/tr/bireysel/kampanyalar" },
  { banka: "Dünya Katılım",         url: "dunyakatilim.com.tr/kampanyalar" },
  { banka: "Albaraka Türk",         url: "albaraka.com.tr/tr/kampanyalar" },
  { banka: "Türkiye Finans",        url: "turkiyefinans.com.tr/tr-tr/kampanyalar/Sayfalar" },
  { banka: "T.O.M. Katılım",        url: "tombank.com.tr/kampanyalar.html" },
  { banka: "Hayat Finans",          url: "hayatfinans.com.tr/kampanyalar" },
  { banka: "Vakıf Katılım",         url: "vakifkatilim.com.tr/tr/kendim-icin/kampanyalar/mevcut-kampanyalar" },
  { banka: "Adil Katılım",          url: "adilkatilim.com.tr", haric: true },
];

export const SISTEM_DURUMU = {
  qdrantParca: 1907,
  qdrantBelge: 498,
  indeksTarihi: "23 Ağustos 2026",
  sonTarama: "22 Ağustos 2026",
  bayatlikGun: 1,
};

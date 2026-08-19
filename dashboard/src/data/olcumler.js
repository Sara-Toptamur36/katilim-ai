export const OLCUM_TARIHI = "18 Ağustos 2026";

export const OLCUMLER = {
  veri: {
    tekilKampanya: 251,
    anlikGoruntu: 300,
    degisenKampanya: 40,
    alanDegisen: 25,
    kapsananBanka: 9,
    toplamBanka: 10,
    haricBanka: "Adil Katılım",
    haricSebep: "kampanya/ürün yayını bulunmadığı için hariç",
    goldKayit: 58,
  },
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
      aciklama: "Yanlış pozitif: sayfanın ortasında başka bir ürüne ait \"Kâr paysız 2.500 TL'ye kadar\" ifadesi %0 oran olarak alındı. Dar kapsamlı, bilinen sınırlama.",
    },
  ],
};

export const BANKA_DAGILIMI = [
  { banka: "Ziraat Katılım",        tekil: 109, snapshot: 111, gold: 8 },
  { banka: "Türkiye Emlak Katılım", tekil: 81,  snapshot: 103, gold: 7 },
  { banka: "Albaraka Türk",         tekil: 14,  snapshot: 16,  gold: 6 },
  { banka: "Kuveyt Türk",           tekil: 13,  snapshot: 15,  gold: 7 },
  { banka: "Türkiye Finans",        tekil: 13,  snapshot: 16,  gold: 7 },
  { banka: "Hayat Finans",          tekil: 10,  snapshot: 18,  gold: 5 },
  { banka: "Dünya Katılım",         tekil: 5,   snapshot: 15,  gold: 7 },
  { banka: "T.O.M. Katılım",        tekil: 3,   snapshot: 3,   gold: 3 },
  { banka: "Vakıf Katılım",         tekil: 3,   snapshot: 3,   gold: 8 },
];

export const URUN_AILESI = [
  { ad: "Kart Kampanyası",               sayi: 153, doluluk: 21.2 },
  { ad: "Belirtilmemiş",                 sayi: 38,  doluluk: 16.8 },
  { ad: "Alışveriş Puanı Kampanyası",    sayi: 37,  doluluk: 20.0 },
  { ad: "Konut Finansmanı Kampanyası",   sayi: 7,   doluluk: 31.4 },
  { ad: "İhtiyaç Finansmanı Kampanyası", sayi: 6,   doluluk: 40.0 },
  { ad: "Yatırım Ürünü Kampanyası",      sayi: 4,   doluluk: 0.0 },
  { ad: "Yeni Müşteri Kampanyası",       sayi: 3,   doluluk: 40.0 },
  { ad: "Finansman Kampanyası",          sayi: 2,   doluluk: 20.0 },
  { ad: "Taşıt Finansmanı Kampanyası",   sayi: 1,   doluluk: 0.0 },
];

export const ZAMAN_EKSENI = {
  ilkGorulme: "31 Temmuz 2026",
  sonGorulme: "18 Ağustos 2026",
  ortalamaVersiyon: 1.2,
  degisenKampanya: 40,
  bayatlikGun: 0,
};

// Alan bazında veri doluluğu - docs/veri_coverage.md 4. bölüm
// NOT: Bu oranlar YALNIZCA regex katmanının sonucudur. NER/LLM
// katmanı daha fazlasını doldurur; bu bir ALT SINIR göstergesidir.
export const ALAN_DOLULUGU = [
  { alan: "Taksit sayısı",   dolu: 130, toplam: 251 },
  { alan: "Ödül miktarı",    dolu: 85,  toplam: 251 },
  { alan: "Kâr payı oranı",  dolu: 37,  toplam: 251 },
  { alan: "Vade",            dolu: 5,   toplam: 251 },
  { alan: "Masraf durumu",   dolu: 5,   toplam: 251 },
];

export const KAYNAK_TAKIP = [
  { banka: "Ziraat Katılım",        url: "ziraatkatilim.com.tr/kart-kampanyalari" },
  { banka: "Türkiye Emlak Katılım", url: "emlakkatilim.com.tr/tr/bireysel/kampanyalar" },
  { banka: "Kuveyt Türk",           url: "kuveytturk.com.tr/kampanyalar/kendim-icin" },
  { banka: "Albaraka Türk",         url: "albaraka.com.tr/tr/kampanyalar" },
  { banka: "Hayat Finans",          url: "hayatfinans.com.tr/kampanyalar" },
  { banka: "Türkiye Finans",        url: "turkiyefinans.com.tr/tr-tr/kampanyalar/Sayfalar" },
  { banka: "Dünya Katılım",         url: "dunyakatilim.com.tr/kampanyalar" },
  { banka: "Vakıf Katılım",         url: "vakifkatilim.com.tr/tr/kendim-icin/kampanyalar/mevcut-kampanyalar" },
  { banka: "T.O.M. Katılım",        url: "tombank.com.tr/kampanyalar.html" },
  { banka: "Adil Katılım",          url: "adilkatilim.com.tr", haric: true },
];

export const SISTEM_DURUMU = {
  qdrantParca: 817,
  qdrantBelge: 263,
  indeksTarihi: "17 Ağustos 2026",
  sonTarama: "18 Ağustos 2026",
  bayatlikGun: 0,
};

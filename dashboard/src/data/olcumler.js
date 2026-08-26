// KatilimAI - ekranda gosterilen sayilarin TEK kaynagi.
//
// IKI FARKLI TARIH VAR, BILEREK AYRI TUTULUYOR:
//
//   VERI_TARIHI  -> kampanya hacmi, banka dagilimi, alan doluluk.
//                   PostgreSQL'den okundu, GUNCEL.
//   OLCUM_TARIHI -> makro F1, RAG Recall, cekimserlik, test sayisi.
//                   Belirli bir veri seti uzerinde OLCULDU.
//
// Ikisini tek tarihle gostermek YANILTICI olurdu.
//
// GUNCELLEME (26 Agustos 2026): cikarim.makroF1 onceki 98.28 degeri
// REGEX-ONLY ve kucuk/eski bir canli alt kumeden geliyordu (bkz.
// docs/extraction_accuracy_raporu.md, 20 Agustos guncellemesi). EVREN
// entegrasyonundaki sessiz bir hata duzeltildikten sonra (llm-fast
// dusunme zinciri max_tokens'i tuketip bos donuyordu - chat_template_
// kwargs enable_thinking=false ile giderildi), 291 canli kayit uzerinde
// HEM regex-only HEM hibrit (regex+LLM/EVREN) yeniden olculdu - bkz.
// cikarim_dogruluk_raporu.json. Asagidaki sayilar HIBRIT (calisan
// sistemin gercekte kullandigi) varyanttir; regex-only tek basina daha
// dusuktur (%80,66 F1). RAG olcumleri hala 25 Agustos'taki 1875 parcalik
// indekste - iki taraf farkli tarihte oldugu icin OLCUM_VERI_SETI ikisini
// ayri ayri belirtir.
export const VERI_TARIHI = "24 Ağustos 2026";
export const OLCUM_TARIHI = "26 Ağustos 2026";
export const OLCUM_VERI_SETI = "291 canlı kayıt (çıkarım) · 129 sorgu / 1875 parça (RAG)";

export const OLCUMLER = {
  // --- VERI: guncel, PostgreSQL'den (VERI_TARIHI) ---
  veri: {
    tekilKampanya: 447,
    anlikGoruntu: 496,
    kapsananBanka: 9,
    toplamBanka: 10,
    haricBanka: "Adil Katılım",
    haricSebep: "kampanya/ürün yayını bulunmadığı için hariç",
    // gold_dataset/altin_veri_seti.json'dan sayildi (24 Agustos 2026).
    // 64 iken bayat kalmisti - Sara'nin etiketleme sprinti 195 kayit
    // daha imzalayinca set 302'ye cikti ama ekran hala 64 gosteriyordu.
    // Sartname hedefi 200-300; bu sayi hedefin TUTTURULDUGUNU gosterir.
    goldKayit: 302,
    goldGercekBanka: 298,
    goldOrnekSenaryo: 4, // sartnamedeki A/B/C/D Bankasi ornegi
  },
  // --- OLCUM: cikarim 26 Agustos'ta hibrit pipeline ile 291 canli
  //     kayitta yeniden kosuldu; RAG olcumleri 25 Agustos'taki indekste ---
  cikarim: {
    doluAlanDogrulugu: 81.68,
    doluAlanDetay: "hibrit (regex+LLM/EVREN), 291 canlı kayıt",
    bosAlanDogrulugu: 96.88,
    bosAlanDetay: "hibrit (regex+LLM/EVREN), 291 canlı kayıt",
    makroF1: 82.50,
    makroF1Detay: "11 alan, hibrit (regex+LLM/EVREN) · regex-only tek başına %80,66",
  },
  kapsam: {
    hassasiyet: "24/24",
    ozgulluk: "10/10",
  },
  rag: {
    // DIKKAT: bu 817/263, Recall degerlerinin OLCULDUGU indekstir.
    // Calisan sistemdeki guncel indeks SISTEM_DURUMU'nda (1907 parca) -
    // ikisi ayri, cunku Recall yeni indekste yeniden olculmedi.
    indekslenenParca: 1875,
    belgeSayisi: 513,
    indeksTarihi: "25 Ağustos 2026",
    recall5: 87.6,
    recall3: 84.5,
    recall1: 72.09,
    recall5Detay: "129 sorgu",
    recall1Not: "koşular arası oynuyor (HNSW yaklaşık arama)",
    // Kategori kirilimi: sistemin nerede zorlandigi tek bir genel oranin
    // arkasinda kaybolmasin. banka_ve_konu en zor kategori - kullanici
    // kampanya adini vermeden "X bankasi kart" diye soruyor.
    recallKategori: [
      { ad: "Tam ad", oran: 97.87, detay: "46/47" },
      { ad: "Kısmi ad", oran: 95.35, detay: "41/43" },
      { ad: "Doğal soru", oran: 87.5, detay: "14/16" },
      { ad: "Banka + konu", oran: 52.17, detay: "12/23" },
    ],
    abstention: 86.67,
    abstentionDetay: "13/15 alan dışı soruda cevap üretilmedi",
    // Alan ICI ama kapsam disi sorular (ör. "hesap acmak icin hangi
    // belgeler gerekli") sistemin en zayif oldugu yer: kampanya
    // korpusunda cevabi yok ama terimler ortustugu icin esigi geciyor.
    abstentionKapsamDisi: 40,
    abstentionKapsamDisiDetay: "4/10 kapsam dışı soruda cevap üretilmedi",
  },
  // CI'nin kendi calisan sayisi (gh run view, GitHub Actions - "not slow"
  // takimi) DENETIM BULGUSU (26.08.2026): 2 test kirikti, "Sorgu Eslesme
  // Agirliklari" ozelligi eklenince test_kaynak_guncelligi.py'deki
  // SimpleNamespace sahte nesneleri terim_agirliklari alanini almamisti.
  // Duzeltildi (bkz. tests/test_kaynak_guncelligi.py); sayilar CI'nin
  // GERCEK son calismasindan (yerel .env/GERCEK_VERI_AKTIF etkisinden
  // ARINDIRILMIS, CI hicbir zaman yerel .env gormez).
  test: {
    gecen: 1278,
    yavas: 46,
  },
  bilinenHatalar: [
    {
      kod: "EX-AL",
      alan: "Kampanya avantajı (Albaraka)",
      aciklama: "Albaraka Mobil üzerinden kodla alınan indirim kampanyaları (13 kayıt) metinde hiç \"kart\" geçmiyor, mevcut desenler yakalayamıyor (26 Ağustos ölçümü).",
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
  ortalamaVersiyon: 1.1,
  degisenKampanya: 26,
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
  qdrantParca: 1875,
  qdrantBelge: 513,
  indeksTarihi: "25 Ağustos 2026",
  sonTarama: "22 Ağustos 2026",
  bayatlikGun: 1,
};

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
export const OLCUM_TARIHI = "27 Ağustos 2026";
export const OLCUM_VERI_SETI = "291 canlı kayıt (çıkarım) · 138 sorgu / 2304 parça (RAG)";

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
  //     kayitta yeniden kosuldu; RAG olcumleri 27 Agustos'ta yeni ozyinelemeli indekste ---
  cikarim: {
    doluAlanDogrulugu: 81.68,
    doluAlanDetay: "hibrit (regex+LLM/EVREN), 291 canlı kayıt",
    bosAlanDogrulugu: 96.88,
    bosAlanDetay: "hibrit (regex+LLM/EVREN), 291 canlı kayıt",
    makroF1: 82.50,
    makroF1Detay: "11 alan, hibrit (regex+LLM/EVREN) · regex-only tek başına %80,66",
    // DURUSTLUK NOTU (README, 26.08.2026 ablation bolumu): bu kosuda
    // GLiNER bu makinede yuklenirken coktugu icin (torch/Windows yerel
    // hatasi) NER katmani DEVRE DISIYDI. Yani "hibrit" burada gercekte
    // regex + LLM'dir. NER'in katkisi "yok" DEGIL, "olculmedi"dir -
    // ekranda da boyle yazilir, ucu birden calismis gibi gosterilmez.
    nerDurumu: "Bu ölçümde NER (GLiNER) devre dışıydı — raporlanan hibrit gerçekte regex + LLM'dir. NER'in katkısı ölçülmemiştir.",
    // Alan bazli F1 - cikarim_dogruluk_raporu.json'dan (hibrit varyant).
    // NEDEN EKRANDA: tek bir makro F1 sayisi sistemin nerede iyi, nerede
    // zayif oldugunu gizler. 23 Agustos'ta "bilinen zayif alan" diye
    // isaretlenen kampanya_turu (%35,63) ve hedef_kitle (R %19,67)
    // 26 Agustos'ta olculur bicimde duzeldi - once/sonra gorunur olmali.
    alanBazliF1: [
      { alan: "Kampanya başlangıç", f1: 97.67 },
      { alan: "Kampanya bitiş", f1: 95.69 },
      { alan: "Erteleme süresi", f1: 94.74 },
      { alan: "Ödül birimi", f1: 90.82 },
      { alan: "Ödül miktarı", f1: 90.36 },
      { alan: "Taksit sayısı", f1: 89.50 },
      { alan: "Kampanya türü", f1: 81.88, oncekiF1: 35.63 },
      { alan: "Kâr payı oranı", f1: 80.00 },
      { alan: "Finansman tutarı", f1: 72.73 },
      { alan: "Hedef kitle", f1: 56.95, oncekiF1: 19.67 },
      { alan: "Vade", f1: 57.14 },
    ],
  },
  kapsam: {
    hassasiyet: "24/24",
    ozgulluk: "10/10",
  },
  rag: {
    indekslenenParca: 2304,
    belgeSayisi: 623,
    indeksTarihi: "27 Ağustos 2026",
    recall5: 76.81,
    recall3: 73.19,
    recall1: 60.14,
    recall5Detay: "138 sorgu (Özyinelemeli parçalama - 900 karakter / 150 örtüşme)",
    recall1Not: "exact=True arama modu",
    recallKategori: [
      { ad: "Tam ad", oran: 96.00, detay: "48/50" },
      { ad: "Kısmi ad", oran: 86.96, detay: "40/46" },
      { ad: "Doğal soru", oran: 70.59, detay: "12/17" },
      { ad: "Banka + konu", oran: 24.00, detay: "6/25" },
    ],
    abstention: 93.33,
    abstentionDetay: "14/15 alan dışı soruda cevap üretilmedi",
    abstentionKapsamDisi: 100,
    abstentionKapsamDisiDetay: "10/10 kapsam dışı soruda uçtan uca niyet yönlendirmeli cevap üretilmedi",
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
  qdrantParca: 2304,
  qdrantBelge: 623,
  indeksTarihi: "27 Ağustos 2026",
  sonTarama: "22 Ağustos 2026",
  bayatlikGun: 1,
};

// KatilimAI - ekranda gosterilen sayilarin TEK kaynagi.
//
// IKI FARKLI TARIH VAR, BILEREK AYRI TUTULUYOR:
//
//   VERI_TARIHI  -> kampanya hacmi, banka dagilimi, alan doluluk.
//                   Ham tarama + PostgreSQL'den okundu.
//   OLCUM_TARIHI -> pipeline F1, RAG Recall, cekimserlik, test sayisi.
//                   Belirli bir veri seti uzerinde OLCULDU.
//
// Ikisini tek tarihle gostermek YANILTICI olurdu.
//
// GUNCELLEME (27 Agustos 2026): bu dosya README'deki "Olculebilir durum"
// tablosuyla ayni kosulardan beslenecek sekilde yeniden yazildi.
//
//   1) Cikarim artik DORT ASAMALI FULL PIPELINE benchmark'indan geliyor
//      (Regex -> Regex+NER -> Regex+NER+EVREN -> Final/Validation),
//      kaynak: EVREN_FULL_PIPELINE_RESULTS.json, 291 canli kayit.
//      Onceki 82,50 degeri NER'in COKTUGU (GLiNER/torch Windows hatasi)
//      bir kosudan geliyordu; o kosuda "hibrit" gercekte regex+LLM'di.
//      Bu kosuda NER CALISTI ve katkisi OLCULDU - net negatif ciktigi
//      icin de aynen raporlanir, gizlenmez.
//   2) RAG artik 25 Agustos'taki 1875 parcalik indekste degil, 27
//      Agustos'ta kurulan 2304 parcalik OZYINELEMELI indekste olculdu -
//      yani RAG oranlari ile CANLI indeks ilk kez AYNI indeks.
//   3) Hacim sayilari uc AYRI seyi olcer ve artik uCu de ayri tutulur
//      (yapilandirilmis kayit / tekil ham sayfa / anlik goruntu) -
//      onceden ikisi tek karta sikistirilmisti.
export const VERI_TARIHI = "26 Ağustos 2026";
export const OLCUM_TARIHI = "27 Ağustos 2026";
export const OLCUM_VERI_SETI =
  "291 canlı kayıt (çıkarım) · 138 sorgu / 2.304 parça (RAG)";

export const OLCUMLER = {
  // --- VERI: guncel (VERI_TARIHI) ---
  veri: {
    // UC FARKLI SAYI, UC FARKLI SEY. Tek bir "kampanya sayisi" vermek
    // yanlis olurdu - README'deki "ucu farkli seyi olcer" satirinin
    // ayrintisi ekranda TAM OLARAK burasidir:
    //   yapilandirilmisKayit -> PostgreSQL'de alanlari cikarilmis satir
    //                           (GERCEK_VERI_AKTIF=true). Bir ham sayfa
    //                           birden fazla kampanya tasiyabildigi icin
    //                           tekil sayfadan FAZLA olabilir.
    //   tekilKampanya        -> taranan TEKIL URL sayisi (ham veri).
    //   anlikGoruntu         -> ayni URL'nin farkli tarihlerdeki
    //                           kayitlari dahil, toplam JSON dosyasi.
    // tekil/anlik degerleri scraper/raw_data'dan sayilarak dogrulandi
    // (525 tekil URL / 623 dosya, 27.08.2026).
    yapilandirilmisKayit: 536,
    tekilKampanya: 525,
    anlikGoruntu: 623,
    kapsananBanka: 9,
    toplamBanka: 10,
    haricBanka: "Adil Katılım",
    haricSebep: "ürün/kampanya yayımlamadığı için hariç",
    // gold_dataset/altin_veri_seti.json'dan sayildi (27.08.2026):
    // 302 kayit = 298 gercek banka kaydi + 4 sartname ornegi (A/B/C/D
    // Bankasi). Sartname hedefi 200-300; hedef tutturuldu, taslak yok.
    goldKayit: 302,
    goldGercekBanka: 298,
    goldOrnekSenaryo: 4,
    // terminology/sozluk.json'dan sayildi - TerminolojiSozlugu.jsx ayni
    // dosyayi canli okur, bu yalnizca ozet kartlarinin kullandigi sayidir.
    terminolojiKavram: 31,
  },

  // --- OLCUM: EVREN full pipeline benchmark, 27 Agustos 2026,
  //     291 canli kayit. Kaynak: EVREN_FULL_PIPELINE_RESULTS.json ---
  cikarim: {
    doluAlanDogrulugu: 81.68,
    doluAlanDetay: "final pipeline, 291 canlı kayıt, 11 alan",
    bosAlanDogrulugu: 96.88,
    bosAlanDetay: "yanlış pozitif kontrolü, 291 canlı kayıt",

    // DIKKAT - BU SAYININ NE OLDUGU: 87,25 pipeline'in TOPLAM
    // TP/FP/FN'i uzerinden hesaplanir (mikro F1): TP 992, FP 65, FN 225
    // -> P %93,85, R %81,51. Alan bazli F1'lerin duz ortalamasi (makro)
    // ise %81,99'dur. Iki sayi FARKLI seyi olcer ve ikisi de yazilir -
    // asagidaki "alan bazli" listeyi toplayan bir juri uyesi 87,25'i
    // bulamayinca celiski gormemeli.
    makroF1: 87.25,
    makroF1Detay:
      "Regex→NER→EVREN→Validation · toplam TP/FP/FN üzerinden (P %93,85 / R %81,51)",
    precision: 93.85,
    recall: 81.51,
    alanOrtalamasiF1: 81.99,
    alanOrtalamasiNotu:
      "Aşağıdaki 11 alanın düz ortalaması %81,99; başlıktaki %87,25 ise toplam TP/FP/FN üzerinden hesaplanır. İkisi farklı şeyi ölçer, ikisi de raporlanır.",

    // DORT ASAMALI ABLATION - her katmanin katkisi AYRI olculdu.
    // Net negatif cikan katman (NER) da aynen yazilir.
    pipelineAsamalari: [
      { ad: "Regex", f1: 72.14, tp: 708, fp: 38, fn: 509, precision: 94.91, recall: 58.18 },
      { ad: "Regex + NER", f1: 71.92, tp: 711, fp: 49, fn: 506, precision: 93.55, recall: 58.42, delta: -0.22 },
      { ad: "Regex + NER + EVREN", f1: 74.69, tp: 760, fp: 58, fn: 457, precision: 92.91, recall: 62.45, delta: 2.77 },
      { ad: "Final (+ Validation)", f1: 87.25, tp: 992, fp: 65, fn: 225, precision: 93.85, recall: 81.51, delta: 12.56 },
    ],
    nerKatkisi: { cagri: 54, yeniDogruAlan: 3, yanlisAlan: 11, net: "negatif" },
    evrenKatkisi: { cagri: 112, kayitlaKurtardi: 38, yeniDogruAlan: 49, yanlisAlan: 9, net: "pozitif" },

    // DURUSTLUK NOTU: onceki surumde burada "NER bu olcumde devre disiydi,
    // katkisi OLCULMEDI" yaziyordu (GLiNER Windows'ta cokuyordu). 27
    // Agustos full pipeline kosusunda NER 54 kayitta CALISTI - artik
    // "olculmedi" degil, "olculdu ve net negatif cikti" denir.
    nerDurumu:
      "NER (GLiNER) bu ölçümde çalıştı: 54 kayıtta çağrıldı, +3 doğru / +11 yanlış alan getirdi — katkısı net negatif (F1 %72,14 → %71,92). Ölçüldüğü için raporlanır, pipeline'dan çıkarılması ayrı bir karardır.",

    // Alan bazli F1 - EVREN_FULL_PIPELINE_RESULTS.json "final" asamasinin
    // TP/FP/FN'lerinden hesaplandi. oncekiF1: 23 Agustos'ta "bilinen zayif
    // alan" diye isaretlenen deger - once/sonra gorunur kalmali.
    alanBazliF1: [
      { alan: "Kampanya başlangıç", f1: 97.67, tp: 147, fp: 0, fn: 7 },
      { alan: "Kampanya bitiş", f1: 96.94, tp: 222, fp: 5, fn: 9 },
      { alan: "Ödül birimi", f1: 91.75, tp: 89, fp: 11, fn: 5 },
      { alan: "Ödül miktarı", f1: 89.8, tp: 88, fp: 14, fn: 6 },
      { alan: "Taksit sayısı", f1: 89.09, tp: 98, fp: 16, fn: 8 },
      { alan: "Kampanya türü", f1: 87.43, tp: 226, fp: 0, fn: 65, oncekiF1: 35.63 },
      { alan: "Erteleme süresi", f1: 85.71, tp: 9, fp: 3, fn: 0 },
      { alan: "Kâr payı oranı", f1: 80.0, tp: 8, fp: 3, fn: 1 },
      { alan: "Finansman tutarı", f1: 74.42, tp: 16, fp: 6, fn: 5 },
      { alan: "Hedef kitle", f1: 59.03, tp: 85, fp: 1, fn: 117, oncekiF1: 19.67 },
      { alan: "Vade", f1: 50.0, tp: 4, fp: 6, fn: 2 },
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
    parcalamaYontemi: "Özyinelemeli parçalama (900 karakter / 150 örtüşme)",
    degerlendirmeSeti: 138,
    elenenSoru: 22,
    recall5: 81.88,
    recall3: 78.99,
    recall1: 68.12,
    recall5Detay: "138 sorgu · özyinelemeli indeks (900/150)",
    recall1Not: "exact=True arama modu",
    // KATEGORI KIRILIMI - DURUSTLUK NOTU: 27 Agustos kosusunda yalnizca
    // GENEL Recall@1/3/5 ve tam_ad kategorisi yeniden yayimlandi. Diger uc
    // kategori AYNI indekste ama ONCEKI kosunun (genel %76,81) degerleridir;
    // toplamlari yeni genel orana denk gelmez ve bu bilerek boyle yazilir -
    // olculmemis bir sayiyi "guncel" gibi gostermek yerine hangi kosudan
    // geldigi isaretlenir.
    recallKategori: [
      { ad: "Tam ad", oran: 96.0, detay: "48/50", guncel: true },
      { ad: "Kısmi ad", oran: 86.96, detay: "40/46", guncel: false },
      { ad: "Doğal soru", oran: 70.59, detay: "12/17", guncel: false },
      { ad: "Banka + konu", oran: 24.0, detay: "6/25", guncel: false },
    ],
    recallKategoriNotu:
      "Tam ad kategorisi 27 Ağustos koşusundan; diğer üç kategori aynı indeksteki önceki koşudan (genel %76,81) alınmıştır — 27 Ağustos'ta kategori kırılımı ayrıca yayımlanmadı.",
    abstention: 93.33,
    abstentionDetay: "alan dışı: 14/15 soruda cevap üretilmedi",
    // Cekimserligin GERCEK zayif noktasi alan_disi degil, alan_ici
    // kapsam_disi. Izole RAG olcumu %40; niyet yonlendirmesi devrede olan
    // UCTAN UCA olcumde %100. Ikisi ayri ayri yazilir, iyi olan tek basina
    // gosterilmez.
    abstentionAlanIciIzole: 40.0,
    abstentionAlanIciIzoleDetay: "alan içi kapsam dışı, izole RAG: 4/10",
    abstentionUctanUca: 100,
    abstentionUctanUcaDetay:
      "alan içi kapsam dışı, uçtan uca (niyet yönlendirmeli): 10/10",
  },

  // CI'nin kendi calisan sayisi (GitHub Actions, `-m "not slow"` takimi).
  // Yerel .env/GERCEK_VERI_AKTIF etkisinden ARINDIRILMIS - CI hicbir zaman
  // yerel .env gormez.
  //
  // "atlanan" ile "yavas" AYNI SEY DEGIL:
  //   atlanan       -> kosuda skip edilen test (harici servis/donanim yok).
  //   yavasDeselect -> @pytest.mark.slow ile CI'da DESELECT edilen, yani
  //                    hic toplanmayan test (Ollama/GLiNER/Qdrant ister).
  //   slowModul     -> SLOW_test_sprint_is_listesi.py, PYTEST_SLOW_TESTS
  //                    ortam degiskeniyle modul seviyesinde skip.
  test: {
    gecen: 1278,
    hata: 0,
    atlanan: 90,
    yavasDeselect: 46,
    slowModul: 34,
  },

  bilinenHatalar: [
    {
      kod: "EX-AL",
      alan: "Kampanya avantajı (Albaraka)",
      aciklama:
        "Albaraka Mobil üzerinden kodla alınan indirim kampanyaları (13 kayıt) metinde hiç \"kart\" geçmiyor, mevcut desenler yakalayamıyor (26 Ağustos ölçümü).",
    },
    {
      kod: "EX-VADE",
      alan: "Vade (vade_ay)",
      aciklama:
        "Final pipeline'da en zayıf alan: F1 %50,00 (TP 4 / FP 6 / FN 2). Yanlış pozitiflerin çoğu NER katmanından geliyor — regex tek başına 2 FP verirken NER sonrası 6'ya çıkıyor. Örneklem küçük (6 gerçek değer), oran gürültüye açık.",
    },
    {
      kod: "EX-HK",
      alan: "Hedef kitle",
      aciklama:
        "F1 %59,03 — 117 yanlış negatif. EVREN bu alanda en çok kurtarmayı yapan katman (recovery örneklerinin çoğu hedef_kitle) ama hâlâ vakaların yarısından fazlasında değer üretilemiyor.",
    },
  ],
};

// --- BANKA DAGILIMI ---
// DORT SUTUN, DORT AYRI SORU. Hangisinin ne oldugu ekranda da yazar:
//   kayit    -> PostgreSQL'de yapilandirilmis kayit (toplam 536). Canli
//               /kampanyalar acikken bu sutun canli sayimla DEGISTIRILIR;
//               statik degerler docs/JURI_DOKUMANTASYONU.md §3.9'dan.
//   tekil    -> scraper/raw_data'daki tekil URL (toplam 525).
//   snapshot -> toplam anlik goruntu dosyasi (toplam 623).
//   gold     -> altin veri setindeki kayit (toplam 298 + 4 sartname ornegi).
// tekil/snapshot/gold degerleri `python -m scraper.scripts.coverage_raporu`
// ile yeniden uretilir (bkz. docs/veri_coverage.md, 27.08.2026).
export const BANKA_DAGILIMI = [
  { banka: "Kuveyt Türk",           kayit: 110, tekil: 110, snapshot: 123, gold: 63 },
  { banka: "Ziraat Katılım",        kayit: 109, tekil: 108, snapshot: 119, gold: 62 },
  { banka: "Vakıf Katılım",         kayit: 100, tekil: 100, snapshot: 106, gold: 10 },
  { banka: "Türkiye Emlak Katılım", kayit: 84,  tekil: 84,  snapshot: 112, gold: 57 },
  { banka: "Dünya Katılım",         kayit: 45,  tekil: 45,  snapshot: 57,  gold: 37 },
  { banka: "Albaraka Türk",         kayit: 37,  tekil: 37,  snapshot: 45,  gold: 33 },
  { banka: "Türkiye Finans",        kayit: 25,  tekil: 15,  snapshot: 18,  gold: 14 },
  { banka: "T.O.M. Katılım",        kayit: 13,  tekil: 13,  snapshot: 13,  gold: 13 },
  { banka: "Hayat Finans",          kayit: 13,  tekil: 13,  snapshot: 30,  gold: 9 },
];

// --- KAPSAM RAPORU (URUN_AILESI / ALAN_DOLULUGU kaynagi) ---
// Bu iki dizi `python -m scraper.scripts.coverage_raporu` ciktisidir
// (docs/veri_coverage.md). Postgres/Docker GEREKTIRMEZ - dogrudan
// scraper/raw_data'yi regex katmaniyla ozetler, bu yuzden tabani
// yapilandirilmis kayit (536) degil TEKIL KAMPANYA (525) sayisidir.
// Kendi toplamini tasir ve ekranda kendi toplamiyla gosterilir - 536'ya
// tamamlanmis gibi sunulmaz. API canli veri modundayken (GERCEK_VERI_AKTIF
// =true) ikisi de /kampanyalar'dan yeniden hesaplanir; demo modunda ve API
// kapaliyken bu DOGRULANMIS anlik goruntu kullanilir (bkz. useCanliVeriOzet).
export const KAPSAM_RAPORU = {
  kayit: 525,
  tarih: "27 Ağustos 2026",
  komut: "python -m scraper.scripts.coverage_raporu",
};

// Doluluk: o urun ailesindeki kampanyalarda 5 izlenen alanin
// (kar payi, vade, taksit, odul, masraf) ne kadarinin dolu oldugu.
// Tur adlari kaynakta nasil duruyorsa oyle yazilir - canli yol ile yedek
// yolun ayni metni gostermesi icin.
export const URUN_AILESI = [
  { ad: "Kart Kampanyasi",               sayi: 392, doluluk: 15.5 },
  { ad: "Belirtilmemis",                 sayi: 61,  doluluk: 7.2 },
  { ad: "Ticari Kampanya",               sayi: 17,  doluluk: 18.8 },
  { ad: "Finansman Kampanyasi",          sayi: 13,  doluluk: 6.2 },
  { ad: "Yeni Musteri Kampanyasi",       sayi: 12,  doluluk: 20.0 },
  { ad: "Yatirim Urunu Kampanyasi",      sayi: 8,   doluluk: 5.0 },
  { ad: "Ihtiyac Finansmani Kampanyasi", sayi: 7,   doluluk: 45.7 },
  { ad: "Tasit Finansmani Kampanyasi",   sayi: 6,   doluluk: 20.0 },
  { ad: "Konut Finansmani Kampanyasi",   sayi: 3,   doluluk: 40.0 },
  { ad: "POS Kampanyasi",                sayi: 3,   doluluk: 0.0 },
  { ad: "Sigorta/BES Kampanyasi",        sayi: 3,   doluluk: 20.0 },
];

// Alan bazinda veri doluluk. Bu oranlar "cikarim ne kadar dogru" DEGIL,
// "bankalar bu alani kac kampanyada yayimlamis + REGEX katmani kac tanesini
// doldurabilmis" sorusunun cevabidir. NER/LLM katmani daha fazlasini
// doldurur - bu bir ALT SINIR gostergesidir.
export const ALAN_DOLULUGU = [
  { alan: "Taksit sayısı",   dolu: 196, toplam: 525 },
  { alan: "Ödül miktarı",    dolu: 158, toplam: 525 },
  { alan: "Vade",            dolu: 13,  toplam: 525 },
  { alan: "Kâr payı oranı",  dolu: 12,  toplam: 525 },
  { alan: "Masraf durumu",   dolu: 11,  toplam: 525 },
];

// docs/veri_coverage.md "3. Zaman ekseni" bolumunden (27.08.2026 uretimi).
// degisenKampanya = coklu versiyonlu, yani GERCEKTEN degismis kampanya
// sayisi; onceki surumde 26'da kalmisti.
export const ZAMAN_EKSENI = {
  ilkGorulme: "31 Temmuz 2026",
  sonGorulme: "26 Ağustos 2026",
  bayatlikGun: 1,
  ortalamaVersiyon: 1.19,
  degisenKampanya: 74,
};

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
  sonTarama: "26 Ağustos 2026",
  bayatlikGun: 1,
};

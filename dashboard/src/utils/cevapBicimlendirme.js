// Sohbet cevaplarini SUNUM icin bicimlendiren saf fonksiyonlar.
//
// ONEMLI SINIR: Bu dosya backend'in urettigi veriyi YENIDEN HESAPLAMAZ,
// yalnizca zaten kullaniciya gonderilmis metni (cevap / kaynak.metin)
// okunabilir hale getirir. Hicbir fonksiyon sayi UYDURMAZ - bir deger
// bulunamazsa null doner, cagiran taraf "Belirtilmemiş" gosterir.

import { ALAN_ADLARI } from "./alanEtiketleri";

// calculator/calculator.py::TaksitSonucu.ozet_metni() DETERMINISTIK bir
// sablondan uretilir (LLM degil, dogrudan sayilardan). Bu regex O sablonu
// eslestirir - baska bir yerden sayi UYDURMAZ, yalnizca cevap metninde
// ZATEN yazan degerleri ayiklar. Sablon degisirse eslesme basarisiz olur
// ve cagiran taraf ham metne duser (asagida hesaplamaVerisiCikar).
//
// Turkce harfler HEM aksanli (kâr, payı, aylık, ödeme) HEM aksansiz
// (kar, payi, aylik, odeme) haliyle eslesir - GERCEK backend uzerinde
// dogrulandi: sunucu bu cumleyi bazen diyakritiksiz uretiyor (calculator.py
// kaynagi aksanli olsa da, calisma ortaminin yerel ayarlarina gore cikti
// degisebiliyor). Bu tolerans olcum sonucu EKLENDI, tahmin degil.
const HESAPLAMA_SABLONU =
  /([\d.,]+)\s*TL tutar[ıi]nda finansman,\s*ayl[ıi]k %([\d.,]+) k[âa]r pay[ıi] oran[ıi] ve (\d+) ay vade ile:\s*ayl[ıi]k taksit ([\d.,]+) TL,\s*toplam geri [öo]deme ([\d.,]+) TL \(toplam k[âa]r pay[ıi] ([\d.,]+) TL\)/;

// Turkce sira sayilarindaki nokta ("100. yılına", "5. kata") cumle sonu
// DEGILDIR ama "[.!?](?=\s|$)" tek basina bunu ayirt edemez - rakamdan
// hemen sonraki nokta, ardindan kucuk harfle devam eden metinde bir sira
// sayi bicimidir. Olculdu (28.08.2026): "Cumhuriyetimizin 100. yılına
// özel..." cumlesi bu ayrim olmadan "Cumhuriyetimizin 100." olarak
// kirpiliyordu, anlamli bir kisa sonuc uretmiyordu.
function siraSayiNoktasiMi(metin, noktaIndex) {
  const oncesi = metin.slice(Math.max(0, noktaIndex - 3), noktaIndex);
  const sonrasi = metin.slice(noktaIndex + 1, noktaIndex + 3);
  return /\d$/.test(oncesi) && /^\s[a-zçğıöşü]/.test(sonrasi);
}

/**
 * Cevap metninden ilk cumleyi (kisa sonuc) cikarir.
 * Cumle sinirini gecemezse metnin tamamini (uzunsa kirpilmis) dondurur.
 */
export function kisaSonucCikar(cevap, maksUzunluk = 220) {
  if (!cevap) return "";
  const temiz = cevap.trim();

  // Ilk GERCEK cumle sonunu bul (". ", "! ", "? " veya satir sonu) - sira
  // sayi noktalari atlanir.
  const adaylar = /[.!?](?=\s|$)/g;
  let esleme = null;
  let m;
  while ((m = adaylar.exec(temiz))) {
    if (temiz[m.index] === "." && siraSayiNoktasiMi(temiz, m.index)) continue;
    esleme = m;
    break;
  }
  let ilkCumle = esleme ? temiz.slice(0, esleme.index + 1).trim() : temiz;

  if (ilkCumle.length > maksUzunluk) {
    ilkCumle = ilkCumle.slice(0, maksUzunluk).trim() + "…";
  }
  return ilkCumle;
}

/**
 * Kisa sonuc disinda kalan aciklama metni var mi? Varsa dondurur, yoksa null.
 */
export function kalanAciklamaCikar(cevap, kisaSonuc) {
  if (!cevap || !kisaSonuc) return null;
  const kalan = cevap.trim().slice(kisaSonuc.replace(/…$/, "").length).trim();
  return kalan.length > 0 ? kalan : null;
}

/**
 * Hesap makinesi cevabindan yapilandirilmis alanlari cikarir.
 * Eslesme basarisiz olursa null doner (cagiran taraf ham metni gosterir).
 */
export function hesaplamaVerisiCikar(cevap) {
  if (!cevap) return null;
  const m = cevap.match(HESAPLAMA_SABLONU);
  if (!m) return null;
  const [, anapara, oran, vade, aylikTaksit, toplamOdeme, toplamKarPayi] = m;
  return {
    anapara: `${anapara} TL`,
    oran: `%${oran}`,
    vade: `${vade} ay`,
    aylikTaksit: `${aylikTaksit} TL`,
    toplamOdeme: `${toplamOdeme} TL`,
    toplamKarPayi: `${toplamKarPayi} TL`,
  };
}

/**
 * Hesap makinesi cevabinin BASINDA (soru terminoloji yonlendirme cumlesi
 * gibi) hesaplama sablonundan once bir on-metin var mi? Varsa dondurur,
 * yoksa null. HesaplamaKarti sayilari zaten yapilandirilmis gosterdigi
 * icin bu on-metin, cevabin USTUNDEKI SONUÇ satirinda ayrica gosterilir -
 * boylece ayni cumle iki kez (bir kez duz metin, bir kez kart) basilmaz.
 */
export function hesaplamaOnekiCikar(cevap) {
  if (!cevap) return null;
  const m = cevap.match(HESAPLAMA_SABLONU);
  if (!m || m.index === 0) return null;
  const onek = cevap.slice(0, m.index).trim();
  return onek.length > 0 ? onek : null;
}

/**
 * Kaynak metnini GORSEL olarak temizler: fazla bosluk/satir sonlarini
 * sadelestirir, birebir tekrar eden satir/cumleleri kaldirir. Icerigi
 * DEGISTIRMEZ - yalnizca tekrarlari ve bicimlendirme gurultusunu siler.
 */
export function kaynakMetniTemizle(metin) {
  if (!metin) return "";

  const satirlar = metin
    .split(/\r?\n/)
    .map((s) => s.replace(/\s+/g, " ").trim())
    .filter(Boolean);

  const gorulen = new Set();
  const tekilSatirlar = satirlar.filter((s) => {
    const anahtar = s.toLowerCase();
    if (gorulen.has(anahtar)) return false;
    gorulen.add(anahtar);
    return true;
  });

  return tekilSatirlar.join(" ").replace(/\s+/g, " ").trim();
}

// "N ay" gecen her yer VADE DEGILDIR. GERCEK KAYNAKTA OLCULDU (27.08.2026,
// Kuveyt Turk "Evlilik Paketi" parcasi): metin "100.000 TL'ye Kadar %1,99
// Oranla 12 Aya Varan Taksit Firsati 2 ay ertelemeli ..." diyor. Naif bir
// "ilk eslesme kazanir" kurali buradan "2 ay"i (ODEME ERTELEMESI) cekip
// VADE diye gosteriyordu - gercek vade "12 aya varan". Yanlis bir sayi
// gostermek, hic gostermemekten KOTUDUR (ayni ilke: calculator.py::
// _girdileri_dogrula). Bu yuzden:
//   1) "ertele" baglamindaki adaylar ELENIR (vade degil, erteleme),
//   2) kalanlar arasindan vade sinyali (vade/taksit/varan) TASIYAN ilki
//      secilir; hicbiri tasimiyorsa ilk temiz aday kullanilir,
//   3) hicbir aday kalmazsa null doner -> "Belirtilmemiş".
// Turkce cekim ekleri de kapsanir ("12 Aya Varan" -> "ay\b" ile eslesmezdi).
const VADE_ADAYI = /\d{1,3}\s?ay(?:a|da|ı|i|lık|lik)?\b/gi;
const ERTELEME_BAGLAMI = /ertele/i;
const VADE_SINYALI = /(vade|taksit|varan)/i;

function vadeSec(metin) {
  const adaylar = [...metin.matchAll(VADE_ADAYI)];
  const temiz = adaylar.filter(
    (m) => !ERTELEME_BAGLAMI.test(metin.slice(m.index, m.index + m[0].length + 25))
  );
  if (temiz.length === 0) return null;
  const sinyalli = temiz.find((m) =>
    VADE_SINYALI.test(metin.slice(Math.max(0, m.index - 40), m.index + m[0].length + 40))
  );
  return (sinyalli ?? temiz[0])[0].trim();
}

/**
 * Bir kaynak metninde ORAN / VADE / TUTAR ile ilgili yuzeysel esleseni
 * bulur ve METINDE YAZDIGI GIBI (birebir) dondurur. Bu bir HESAPLAMA
 * DEGILDIR - kaynak metninden dogrudan alintidir, deger UYDURULMAZ.
 * Eslesme yoksa null doner ("Belirtilmemiş" gosterimi cagiran tarafta).
 */
export function finansalIpucuCikar(metin) {
  if (!metin) return { oran: null, vade: null, tutar: null };

  const oranEslesme = metin.match(/%\s?\d{1,3}(?:[.,]\d+)?/);
  const tutarEslesme = metin.match(/\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?\s?(?:TL|₺)\b/);

  return {
    oran: oranEslesme ? oranEslesme[0].trim() : null,
    vade: vadeSec(metin),
    tutar: tutarEslesme ? tutarEslesme[0].trim() : null,
  };
}

/**
 * Bir mesajin kaynaklarini (banka, kampanya_adi) ikilisine gore gruplar.
 * Ayni kampanyadan birden fazla parca (chunk) geldiyse tek karta birlestirir;
 * temsilci alanlar (guncellik, tarih, url, skorlar) EN YUKSEK benzerlik
 * skoruna sahip parcadan alinir.
 *
 * banka bilgisi olmayan kaynaklar gruplanamaz (kart/tablo icin anlamli
 * bir baslik uretilemez) - bunlar dondurulen listede YER ALMAZ, ama
 * cagiran taraf orijinal `kaynaklar` dizisini Kaynaklar bolumunde zaten
 * ayrica gosterir, yani hicbir kaynak kullanicidan gizlenmez.
 */
export function kampanyalariGrupla(kaynaklar) {
  if (!Array.isArray(kaynaklar) || kaynaklar.length === 0) return [];

  const gruplar = new Map();

  for (const k of kaynaklar) {
    if (!k?.banka) continue;
    const anahtar = `${k.banka}||${k.kampanya_adi ?? ""}`;
    if (!gruplar.has(anahtar)) {
      gruplar.set(anahtar, {
        banka: k.banka,
        kampanyaAdi: k.kampanya_adi ?? null,
        kaynaklar: [],
        enIyiKaynak: k,
      });
    }
    const grup = gruplar.get(anahtar);
    grup.kaynaklar.push(k);
    const mevcutSkor = grup.enIyiKaynak?.similarity_score ?? -1;
    const adaySkor = k?.similarity_score ?? -1;
    if (adaySkor > mevcutSkor) grup.enIyiKaynak = k;
  }

  return Array.from(gruplar.values());
}

// Dogrulama durumunun kullaniciya gosterilen etiketi ve rengi.
// audit.dogrulama backend'de zaten hesaplanmis, ARANMA/BENZERLIK
// skorundan (confidence) FARKLI bir eksen: "cevaptaki sayilar kaynakta
// dogrulandi mi?" sorusunun cevabidir (bkz. validation/yanit_dogrulama.py).
// dogrulama yoksa (arac bu kavrami uretmiyorsa, orn. sozluk) null doner.
const DOGRULAMA_DURUM_META = {
  dogrulandi: { etiket: "Doğrulandı", renk: "success" },
  kismi: { etiket: "Kısmi Doğrulama", renk: "warning" },
  calistirilmamis: { etiket: "Doğrulanamadı", renk: "default" },
};

export function dogrulamaDurumMeta(dogrulama) {
  if (!dogrulama?.durum) return null;
  return DOGRULAMA_DURUM_META[dogrulama.durum] ?? null;
}

/**
 * Dogrulama ozetindeki alanlardan, kaynakta DOGRULANAMAYAN (dogrulanamayan > 0)
 * olanlarin Turkce etiketlerini dondurur. Boş dizi = ya dogrulama yok ya da
 * tum alanlar sorunsuz - iki durum da cagiran tarafta ayirt edilir
 * (dogrulama objesinin kendisi null/dolu kontrolüyle).
 */
export function dogrulanamayanAlanEtiketleri(dogrulama) {
  if (!dogrulama?.alanlar?.length) return [];
  return dogrulama.alanlar
    .filter((a) => (a.dogrulanamayan ?? 0) > 0)
    .map((a) => ALAN_ADLARI[a.alan] ?? a.alan);
}

/**
 * audit.latency_ms -> "4,2 sn" bicimi. Milisaniye backend'den GERCEK
 * olcum degeridir (bkz. AuditBilgisi.latency_ms); burada yalnizca birim
 * donusumu yapilir, yeni bir sure HESAPLANMAZ.
 */
export function sureMetni(latencyMs) {
  if (latencyMs == null) return null;
  return `${(latencyMs / 1000).toFixed(1).replace(".", ",")} sn`;
}

/**
 * Bir kampanyanin "one cikan avantaji" - kaynak parcasinin ILK CUMLESI.
 * Yeni bir ozet UYETMEZ; kisaSonucCikar ile AYNI mekanizmayi kaynak
 * metnine uygular. Kaynak yoksa/bossa null doner.
 */
export function oneCikanAvantajCikar(birlesikMetin) {
  if (!birlesikMetin) return null;
  const cumle = kisaSonucCikar(birlesikMetin, 140);
  return cumle || null;
}

// Benzerlik skoruna gore kategorik "eslesme kalitesi" rozeti. Ayni esik
// degerleri (0.6 / 0.8) EvidenceCard.jsx'teki renklendirmeyle AYNIDIR -
// tek bir yerde tanimlanmadigi icin burada tekrarlanir ama deger olarak
// kasitli tutarlidir (iki bilesen ayni skoru FARKLI kategorilere
// bolerse jüri gozunde celiskili gorunurdu).
export function esleseKaliteMeta(similarityScore) {
  if (similarityScore == null) return null;
  if (similarityScore >= 0.8) return { etiket: "Tam Eşleşme", renk: "success" };
  if (similarityScore >= 0.6) return { etiket: "Kısmi Eşleşme", renk: "warning" };
  return { etiket: "Zayıf Eşleşme", renk: "error" };
}

/**
 * Bir kampanya karti/tablo satiri icin gosterilecek TEK durum rozetini
 * secer. Guncellik (aktif/suresi_dolmus) biliniyorsa ONCELIKLIDIR - bu
 * dogrudan kaynaktan gelen bir gercektir. Guncellik bilinmiyorsa (backend
 * "bilinmiyor" dondurdugunde) yerine arama benzerligine dayali eslesme
 * kalitesi gosterilir; boylece rozet hicbir zaman bos kalmaz ama iki
 * FARKLI kavram (tazelik / eslesme) tek etikette KARISTIRILMAZ - hangisinin
 * gosterildigi `tur` alaniyla ayirt edilir.
 */
export function kampanyaRozetiMeta(guncellik, similarityScore) {
  if (guncellik === "aktif") return { etiket: "Güncel", renk: "success", tur: "guncellik" };
  if (guncellik === "suresi_dolmus") return { etiket: "Süresi dolmuş", renk: "error", tur: "guncellik" };
  const kalite = esleseKaliteMeta(similarityScore);
  return kalite ? { ...kalite, tur: "eslesme" } : null;
}

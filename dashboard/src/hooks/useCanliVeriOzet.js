import { useEffect, useState } from "react";
import { tazelikGetir, kampanyalariGetir } from "../api/client";
import {
  OLCUMLER,
  BANKA_DAGILIMI,
  URUN_AILESI,
  ALAN_DOLULUGU,
  KAPSAM_RAPORU,
  SISTEM_DURUMU,
  VERI_TARIHI,
} from "../data/olcumler";

function tarihMetni(isoMetin) {
  if (!isoMetin) return null;
  return new Date(isoMetin).toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

// Genel Bakış ve Jüri Audit Paneli AYNI canlı veri hesaplamalarını kullanır
// (tekil kampanya sayısı, banka/ürün ailesi dağılımı, alan doluluğu). Önceden
// bu mantık yalnızca Dashboard.jsx içindeydi; Model Metrikleri/Veri Kaynakları
// panelleri Audit'e taşınınca aynı hesaplamanın iki yerde kopyalanmaması için
// tek bir hook'a çıkarıldı - iki sayfa da CANLI veriden aynı anda, aynı
// şekilde sapıyor/güncelleniyor.
export function useCanliVeriOzet() {
  const [tazelik, setTazelik] = useState(null);
  const [kampanyalar, setKampanyalar] = useState(null);

  useEffect(() => {
    tazelikGetir()
      .then(setTazelik)
      .catch(() => setTazelik(null));

    kampanyalariGetir()
      .then(setKampanyalar)
      .catch(() => setKampanyalar(null));
  }, []);

  // DENETIM BULGUSU (27.08.2026): GERCEK_VERI_AKTIF tanimli degilken
  // (varsayilan false) /kampanyalar PostgreSQL'i HIC OKUMAZ, api/mock_data.py
  // icindeki 4 ornek kaydi (A/B/C/D Bankasi) dondurur. Bu hook o listeyi
  // "canli veri" sayip banka dagilimini, urun ailesini ve alan dolulugunu
  // 4 SAHTE kayittan hesapliyordu - ekranda "Kuveyt Turk 110" yerine
  // "A Bankasi 1" gorunuyordu ve juriye gercek kapsam gibi sunuluyordu.
  //
  // Artik demo modu ACIKCA disarida birakilir: mock liste dagilim
  // hesaplarina HIC girmez, olcumler.js'teki DOGRULANMIS anlik goruntu
  // kullanilir. tekil/anlik sayilari ise demo modda bile gercektir -
  // /sistem/tazelik onlari scraper/raw_data'dan dogrudan sayar, mock'tan
  // degil (bkz. api/main.py::_ham_veri_tazeligi).
  const demoModu = tazelik?.demo_mode === true;
  const canliListe = demoModu ? null : kampanyalar;

  // DENETIM BULGUSU (27.08.2026): "Kampanya Turu Dagilimi" karti 471
  // kampanya diyordu, taranan korpus ise 525 tekil sayfa. Sebep: yerel
  // PostgreSQL 25 Agustos'ta yuklenmis, 26 Agustos taramasinin 89 sayfasi
  // henuz islenmemis. Canli sayim TEKNIK OLARAK dogru ama korpusu EKSIK
  // temsil ediyor - ekranda "veri bu kadar" gibi okunuyordu.
  //
  // KURAL: canli kayit sayisi, /sistem/tazelik'in ham veriden saydigi tekil
  // sayfa sayisinin ALTINDAYSA veritabani geride demektir; o durumda
  // dagilimlar icin coverage_raporu ciktisi (docs/veri_coverage.md, ayni
  // ham korpustan uretilir ve tek komutla tazelenir) kullanilir.
  // Veritabani yuklendiginde (juri ortaminda 536 >= 525) kosul kendiliginden
  // duser ve canli sayima geri donulur - elle bir bayrak cevirmek gerekmez.
  const hamTekilSayfa = tazelik?.tekil_kampanya ?? null;
  const veritabaniGeride =
    canliListe != null && hamTekilSayfa != null && canliListe.length < hamTekilSayfa;
  const gercekKampanyalar = veritabaniGeride ? null : canliListe;

  const tekilKampanya = tazelik?.tekil_kampanya ?? OLCUMLER.veri.tekilKampanya;
  const anlikGoruntu = tazelik?.anlik_goruntu ?? OLCUMLER.veri.anlikGoruntu;
  // PostgreSQL'de yapilandirilmis kayit sayisi: canli listenin uzunlugu,
  // demo modda README'de yayimlanan olcum.
  const yapilandirilmisKayit =
    gercekKampanyalar?.length ?? OLCUMLER.veri.yapilandirilmisKayit;
  // Kapsam raporunun (URUN_AILESI / ALAN_DOLULUGU) hangi tabandan geldigi -
  // canli modda /kampanyalar, aksi halde coverage_raporu ciktisi.
  const kapsamRaporuKaynagi = gercekKampanyalar ? null : KAPSAM_RAPORU;
  // Dagilimlarin neden canli sayimdan gelmedigi - ekranda aynen yazilir.
  const yedekSebebi = gercekKampanyalar
    ? null
    : demoModu
      ? "demo modu — /kampanyalar örnek veri döndürüyor"
      : veritabaniGeride
        ? `veritabanı ${canliListe.length} kayıtta, taranan ${hamTekilSayfa} sayfanın gerisinde`
        : "API kapalı";
  const ragParca = tazelik?.rag_parca_sayisi ?? SISTEM_DURUMU.qdrantParca;
  const ragBelge = tazelik?.rag_belge_sayisi ?? SISTEM_DURUMU.qdrantBelge;
  const hacimCanli = tazelik != null;
  // DENETIM BULGUSU (26.08.2026): Dashboard "Veri: {tarih}" etiketi
  // VERI_TARIHI sabitini (24 Agustos) gosteriyordu ama hemen yanindaki
  // sayilar (tekilKampanya vb.) CANLI /sistem/tazelik'ten geliyor - API
  // baglantiliyken tarama gercekte daha yeni oldugunda etiket bayat
  // kaliyordu. tazelik.son_tarama VARSA o kullanilir, yoksa (API kapali)
  // statik VERI_TARIHI'ne duser.
  const sonTarama = tarihMetni(tazelik?.son_tarama) ?? VERI_TARIHI;

  // Izlenen bes alan, olcumler.js'teki "doluluk" tanimiyla AYNI olmali.
  const IZLENEN_ALANLAR = [
    "kar_payi_orani_percent",
    "vade_ay",
    "taksit_sayisi",
    "odul_miktari",
    "masraf_durumu",
  ];
  const urunAilesi = gercekKampanyalar
    ? Object.entries(
        gercekKampanyalar.reduce((grup, k) => {
          const ad = k.kampanya_turu || "Belirtilmemiş";
          (grup[ad] ??= []).push(k);
          return grup;
        }, {})
      )
        .map(([ad, uyeler]) => {
          const dolu = uyeler.reduce(
            (t, k) => t + IZLENEN_ALANLAR.filter((a) => k[a] != null).length,
            0
          );
          return {
            ad,
            sayi: uyeler.length,
            doluluk:
              Math.round((1000 * dolu) / (uyeler.length * IZLENEN_ALANLAR.length)) / 10,
          };
        })
        .sort((a, b) => b.sayi - a.sayi)
    : URUN_AILESI;

  const alanDolulugu = gercekKampanyalar
    ? [
        { alan: "Taksit sayısı", anahtar: "taksit_sayisi" },
        { alan: "Ödül miktarı", anahtar: "odul_miktari" },
        { alan: "Kâr payı oranı", anahtar: "kar_payi_orani_percent" },
        { alan: "Vade", anahtar: "vade_ay" },
        { alan: "Masraf durumu", anahtar: "masraf_durumu" },
      ]
        .map(({ alan, anahtar }) => ({
          alan,
          dolu: gercekKampanyalar.filter((k) => k[anahtar] != null).length,
          toplam: gercekKampanyalar.length,
        }))
        .sort((a, b) => b.dolu - a.dolu)
    : ALAN_DOLULUGU;

  const dagilimCanli = gercekKampanyalar != null;
  const urunAilesiToplam = urunAilesi.reduce((t, u) => t + u.sayi, 0);
  const alanDolulukToplam = alanDolulugu[0]?.toplam ?? urunAilesiToplam;

  // --- CANLI BANKA DAGILIMI ---
  // DENETIM BULGUSU (26.08.2026): "Banka Bazinda Dagilim" karti sabit
  // BANKA_DAGILIMI'nden (24 Agustos anlik goruntusu) okuyordu - o tarihte
  // Vakif Katilim 3 kampanyaydi, /kampanyalar'daki GUNCEL sayi 100. Sabit
  // veriyle "Vakif Katilim yalnizca 3 kampanya toplayabildi, veri kapsami
  // bosluguydu" denmesi artik YANLIS bilgi vermek olurdu - gercekte o
  // bankadan cok daha fazla kampanya toplanmis, sadece ekran eski
  // anlik goruntuyu gosteriyordu. tekil canli /kampanyalar'dan sayilir;
  // snapshot/gold icin canli bir uc nokta olmadigindan (backend banka
  // kirilimi sunmuyor) statik BANKA_DAGILIMI'nden isimle eslenerek alinir -
  // bu ikisi zaten sik degismeyen degerlerdir.
  // "kayit" sutunu = PostgreSQL'de yapilandirilmis kayit sayisi. Canli
  // /kampanyalar acikken bu sutun canli sayimla degistirilir; tekil/
  // snapshot/gold icin backend banka kirilimi sunmadigindan statik
  // BANKA_DAGILIMI'nden isimle eslenir (bunlar sik degismeyen degerler).
  const bankaDagilimi = gercekKampanyalar
    ? Object.entries(
        gercekKampanyalar.reduce((grup, k) => {
          const ad = k.banka || "Belirtilmemiş";
          grup[ad] = (grup[ad] ?? 0) + 1;
          return grup;
        }, {})
      )
        .map(([banka, kayit]) => {
          const statik = BANKA_DAGILIMI.find((b) => b.banka === banka);
          return {
            banka,
            kayit,
            tekil: statik?.tekil ?? null,
            snapshot: statik?.snapshot ?? null,
            gold: statik?.gold ?? null,
          };
        })
        .sort((a, b) => b.kayit - a.kayit)
    : BANKA_DAGILIMI;

  const bankaDagilimiToplami = bankaDagilimi.reduce((t, b) => t + b.kayit, 0);
  const enBuyukBankaTekil = bankaDagilimi[0]?.kayit ?? 1;

  const baskinBankalar = bankaDagilimi.slice(0, 2).map((b) => b.banka);
  const baskinYuzde = Math.round(
    (100 * bankaDagilimi.slice(0, 2).reduce((t, b) => t + b.kayit, 0)) / bankaDagilimiToplami
  );
  const zayifBankalar = [...bankaDagilimi]
    .sort((a, b) => a.kayit - b.kayit)
    .slice(0, 3)
    .map((b) => `${b.banka} ${b.kayit}`)
    .join(", ");

  return {
    tazelik,
    kampanyalar,
    demoModu,
    tekilKampanya,
    anlikGoruntu,
    yapilandirilmisKayit,
    kapsamRaporuKaynagi,
    yedekSebebi,
    veritabaniGeride,
    sonTarama,
    ragParca,
    ragBelge,
    hacimCanli,
    urunAilesi,
    alanDolulugu,
    dagilimCanli,
    urunAilesiToplam,
    alanDolulukToplam,
    bankaDagilimi,
    bankaDagilimiToplami,
    enBuyukBankaTekil,
    baskinBankalar,
    baskinYuzde,
    zayifBankalar,
  };
}

import { useEffect, useState } from "react";
import { tazelikGetir, kampanyalariGetir } from "../api/client";
import { OLCUMLER, BANKA_DAGILIMI, URUN_AILESI, ALAN_DOLULUGU, SISTEM_DURUMU } from "../data/olcumler";

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

  const tekilKampanya = tazelik?.tekil_kampanya ?? OLCUMLER.veri.tekilKampanya;
  const anlikGoruntu = tazelik?.anlik_goruntu ?? OLCUMLER.veri.anlikGoruntu;
  const ragParca = tazelik?.rag_parca_sayisi ?? SISTEM_DURUMU.qdrantParca;
  const ragBelge = tazelik?.rag_belge_sayisi ?? SISTEM_DURUMU.qdrantBelge;
  const hacimCanli = tazelik != null;

  // Izlenen bes alan, olcumler.js'teki "doluluk" tanimiyla AYNI olmali.
  const IZLENEN_ALANLAR = [
    "kar_payi_orani_percent",
    "vade_ay",
    "taksit_sayisi",
    "odul_miktari",
    "masraf_durumu",
  ];
  const urunAilesi = kampanyalar
    ? Object.entries(
        kampanyalar.reduce((grup, k) => {
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

  const alanDolulugu = kampanyalar
    ? [
        { alan: "Taksit sayısı", anahtar: "taksit_sayisi" },
        { alan: "Ödül miktarı", anahtar: "odul_miktari" },
        { alan: "Kâr payı oranı", anahtar: "kar_payi_orani_percent" },
        { alan: "Vade", anahtar: "vade_ay" },
        { alan: "Masraf durumu", anahtar: "masraf_durumu" },
      ]
        .map(({ alan, anahtar }) => ({
          alan,
          dolu: kampanyalar.filter((k) => k[anahtar] != null).length,
          toplam: kampanyalar.length,
        }))
        .sort((a, b) => b.dolu - a.dolu)
    : ALAN_DOLULUGU;

  const dagilimCanli = kampanyalar != null;
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
  const bankaDagilimi = kampanyalar
    ? Object.entries(
        kampanyalar.reduce((grup, k) => {
          const ad = k.banka || "Belirtilmemiş";
          grup[ad] = (grup[ad] ?? 0) + 1;
          return grup;
        }, {})
      )
        .map(([banka, tekil]) => {
          const statik = BANKA_DAGILIMI.find((b) => b.banka === banka);
          return { banka, tekil, snapshot: statik?.snapshot ?? null, gold: statik?.gold ?? null };
        })
        .sort((a, b) => b.tekil - a.tekil)
    : BANKA_DAGILIMI;

  const bankaDagilimiToplami = bankaDagilimi.reduce((t, b) => t + b.tekil, 0);
  const enBuyukBankaTekil = bankaDagilimi[0]?.tekil ?? 1;

  const baskinBankalar = bankaDagilimi.slice(0, 2).map((b) => b.banka);
  const baskinYuzde = Math.round(
    (100 * bankaDagilimi.slice(0, 2).reduce((t, b) => t + b.tekil, 0)) / bankaDagilimiToplami
  );
  const zayifBankalar = [...bankaDagilimi]
    .sort((a, b) => a.tekil - b.tekil)
    .slice(0, 3)
    .map((b) => `${b.banka} ${b.tekil}`)
    .join(", ");

  return {
    tazelik,
    kampanyalar,
    tekilKampanya,
    anlikGoruntu,
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

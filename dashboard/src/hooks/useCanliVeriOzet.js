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
  };
}

// Baskin bankalar VERIDEN hesaplanir, isim olarak GOMULMEZ - BANKA_DAGILIMI
// degistikce siralama degisir. Statik veriye bagli oldugu icin modul
// seviyesinde bir kere hesaplanir, hook'a gerek yoktur.
export const BASKIN_BANKALAR = [...BANKA_DAGILIMI]
  .sort((a, b) => b.tekil - a.tekil)
  .slice(0, 2)
  .map((b) => b.banka);

export const BASKIN_YUZDE = Math.round(
  (100 * [...BANKA_DAGILIMI].sort((a, b) => b.tekil - a.tekil).slice(0, 2)
    .reduce((t, b) => t + b.tekil, 0)) /
    BANKA_DAGILIMI.reduce((t, b) => t + b.tekil, 0),
);

export const ZAYIF_BANKALAR = [...BANKA_DAGILIMI]
  .sort((a, b) => a.tekil - b.tekil)
  .slice(0, 3)
  .map((b) => `${b.banka} ${b.tekil}`)
  .join(", ");

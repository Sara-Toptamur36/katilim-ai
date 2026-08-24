import { useEffect, useMemo, useState } from "react";
import { Alert, Card, Select, Space, Tag, Typography } from "antd";
import { kampanyalariGetir } from "../api/client";
import KarsilastirmaPaneli from "../components/KarsilastirmaPaneli";
import RakipMatrisi from "../components/RakipMatrisi";
import TerminolojiSozlugu from "../components/TerminolojiSozlugu";

const { Title, Text } = Typography;

// Karşılaştırma kriteri ile kampanya nesnesindeki veri alanı eşleştirmesi
const KRITER_ALAN_HARITASI = {
  en_dusuk_kar_payi: "kar_payi_orani_percent",
  en_yuksek_odul: "odul_miktari",
  en_uzun_vade: "vade_ay",
  en_dusuk_masraf: "tahsis_ucreti",
  en_yuksek_tutar: "finansman_tutari",
};

export default function Karsilastirma() {
  const [kampanyalar, setKampanyalar] = useState([]);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(null);
  const [secilenIdler, setSecilenIdler] = useState([]);

  // Kriter state'i KarsilastirmaPaneli ile Select seçicisini bağlamak için buraya taşındı
  const [kriter, setKriter] = useState("en_dusuk_kar_payi");

  // Karşılaştırma verilerini bir kez çek
  useEffect(() => {
    setYukleniyor(true);
    setHata(null);
    kampanyalariGetir()
      .then((veri) => setKampanyalar(veri))
      .catch((e) => setHata(e.message))
      .finally(() => setYukleniyor(false));
  }, []);

  const seciliAlan = KRITER_ALAN_HARITASI[kriter] || "kar_payi_orani_percent";

  // Seçili kritere göre verisi olanlar üste, boş olanlar alta gelecek şekilde sırala
  const siraliKampanyalar = useMemo(() => {
    if (!kampanyalar) return [];
    return [...kampanyalar].sort((a, b) => {
      const aDolu = a[seciliAlan] != null;
      const bDolu = b[seciliAlan] != null;
      if (aDolu === bDolu) return 0;
      return aDolu ? -1 : 1; // Dolu verisi olanlar üstte
    });
  }, [kampanyalar, seciliAlan]);

  // RakipMatrisi'nin tür süzgeci için: veride gerçekten bulunan türler.
  // Sabit liste yazmak yerine veriden türetilir - şemaya yeni bir tür
  // eklendiğinde süzgeç kendiliğinden öğrenir, kimse güncellemeyi unutamaz.
  const kampanyaTurleri = useMemo(() => {
    const bulunan = new Set(
      (kampanyalar ?? []).map((k) => k.kampanya_turu).filter(Boolean)
    );
    bulunan.delete("Belirlenemedi"); // süzgeç olarak anlamsız
    return [...bulunan].sort();
  }, [kampanyalar]);

  // Seçili kriterde verisi olan kampanya sayısını hesapla
  const veriOlanKampanyaSayisi = useMemo(() => {
    if (!kampanyalar) return 0;
    return kampanyalar.filter((k) => k[seciliAlan] != null).length;
  }, [kampanyalar, seciliAlan]);

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
      <Title level={3} style={{ marginBottom: 20 }}>
        Karşılaştırma
      </Title>

      {hata && (
        <Alert
          type="error"
          message="Veri alınamadı"
          description={hata}
          style={{ marginBottom: 16 }}
          showIcon
        />
      )}

      {/* Bölüm 1: Kampanya Karşılaştır */}
      <Card title="Kampanya Karşılaştır" className="karsilastirma-karti">
        <div style={{ marginBottom: 16 }}>
          <Text type="secondary" style={{ display: "block", marginBottom: 8 }}>
            Karşılaştırmak istediğiniz kampanyaları seçin:
          </Text>
          <Select
            mode="multiple"
            placeholder="Karşılaştırmak için en az 2 kampanya seçin"
            style={{ width: "100%", marginBottom: 16 }}
            value={secilenIdler}
            onChange={setSecilenIdler}
            loading={yukleniyor}
            filterOption={(input, option) =>
              (option?.searchtext || "")
                .toLowerCase()
                .includes(input.toLowerCase())
            }
            options={siraliKampanyalar.map((k) => {
              const doluMu = k[seciliAlan] != null;
              return {
                value: k.id,
                label: `${k.banka} — ${k.kampanya_adi}`,
                searchtext: `${k.banka} ${k.kampanya_adi}`,
                doluMu: doluMu,
                raw: k,
              };
            })}
            optionRender={(option) => {
              const k = option.data.raw;
              const doluMu = option.data.doluMu;
              return (
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    width: "100%",
                    gap: 8,
                    opacity: doluMu ? 1 : 0.45,
                  }}
                >
                  <span style={{ fontWeight: doluMu ? 500 : 400 }}>
                    {k.banka} — {k.kampanya_adi}
                  </span>
                  <Space size={4} wrap style={{ marginLeft: "auto", flexShrink: 0 }}>
                    {k.kar_payi_orani_percent != null && (
                      <Tag color="blue" style={{ margin: 0, fontSize: 10, padding: "0 4px" }}>
                        kâr payı
                      </Tag>
                    )}
                    {k.odul_miktari != null && (
                      <Tag color="gold" style={{ margin: 0, fontSize: 10, padding: "0 4px" }}>
                        ödül
                      </Tag>
                    )}
                    {k.vade_ay != null && (
                      <Tag color="cyan" style={{ margin: 0, fontSize: 10, padding: "0 4px" }}>
                        vade
                      </Tag>
                    )}
                    {k.tahsis_ucreti != null && (
                      <Tag color="orange" style={{ margin: 0, fontSize: 10, padding: "0 4px" }}>
                        masraf
                      </Tag>
                    )}
                    {k.finansman_tutari != null && (
                      <Tag color="green" style={{ margin: 0, fontSize: 10, padding: "0 4px" }}>
                        tutar
                      </Tag>
                    )}
                  </Space>
                </div>
              );
            }}
          />
        </div>
        <KarsilastirmaPaneli
          secilenIdler={secilenIdler}
          kriter={kriter}
          onKriterDegis={setKriter}
          veriOlanSayisi={veriOlanKampanyaSayisi}
        />
      </Card>

      {/* Bölüm 2: Rakip Analizi — Şartname Md. 5.7
          Buraya bir süre "durum hesaplandığında görünecek" yer tutucusu
          konmuştu: veritabanındaki kayıtların TAMAMI durum=BILINMIYOR
          olduğu için matris boş dönüyordu. Sebep backend'deydi
          (storage/yasam_dongusu.durum_hesapla üretim kodunda hiç
          çağrılmıyordu) ve 24.08.2026'da giderildi; durum artık okuma
          anında tarihlerden hesaplanıyor. Bileşen o günden beri hazır
          bekliyordu, geri bağlandı. */}
      <Card title="Rakip Analizi" className="karsilastirma-karti">
        <RakipMatrisi turler={kampanyaTurleri} />
      </Card>

      {/* Bölüm 3: Terminoloji Sözlüğü */}
      <Card title="Terminoloji Sözlüğü" className="karsilastirma-karti">
        <TerminolojiSozlugu />
      </Card>
    </div>
  );
}


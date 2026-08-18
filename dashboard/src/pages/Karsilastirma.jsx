import { useEffect, useState } from "react";
import { Alert, Divider, Select, Typography } from "antd";
import { kampanyalariGetir } from "../api/client";
import KarsilastirmaPaneli from "../components/KarsilastirmaPaneli";
import RakipMatrisi from "../components/RakipMatrisi";
import TerminolojiSozlugu from "../components/TerminolojiSozlugu";

const { Title } = Typography;

export default function Karsilastirma() {
  const [kampanyalar, setKampanyalar] = useState([]);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(null);
  const [secilenIdler, setSecilenIdler] = useState([]);

  // Karşılaştırma ve rakip matrisi için kampanya verilerini çek
  useEffect(() => {
    setYukleniyor(true);
    setHata(null);
    kampanyalariGetir()
      .then((veri) => setKampanyalar(veri))
      .catch((e) => setHata(e.message))
      .finally(() => setYukleniyor(false));
  }, []);

  const turler = [...new Set(kampanyalar.map((k) => k.kampanya_turu))];

  return (
    <div>
      <Title level={3}>Karşılaştırma</Title>

      {hata && (
        <Alert
          type="error"
          title="Veri alınamadı"
          description={hata}
          style={{ marginBottom: 16 }}
          showIcon
        />
      )}

      <Title level={4}>Kampanya Karşılaştır</Title>
      <div style={{ marginBottom: 12 }}>
        <Select
          mode="multiple"
          placeholder="Karşılaştırmak için en az 2 kampanya seçin"
          style={{ width: "100%", maxWidth: 600, marginBottom: 12 }}
          value={secilenIdler}
          onChange={setSecilenIdler}
          loading={yukleniyor}
          options={kampanyalar.map((k) => ({
            value: k.id,
            label: `${k.banka} — ${k.kampanya_adi}`,
          }))}
        />
      </div>
      <KarsilastirmaPaneli secilenIdler={secilenIdler} />

      <Divider />
      <Title level={4}>Rakip Analizi</Title>
      <RakipMatrisi turler={turler} />

      <Divider />
      <Title level={4}>Terminoloji Sözlüğü</Title>
      <TerminolojiSozlugu />
    </div>
  );
}

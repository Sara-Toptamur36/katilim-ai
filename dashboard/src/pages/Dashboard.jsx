import { useEffect, useState } from "react";
import { Alert, Spin, Typography } from "antd";
import { kampanyalariGetir } from "../api/client";
import TazelikSeridi from "../components/TazelikSeridi";
import IstatistikKartlari from "../components/IstatistikKartlari";

const { Title } = Typography;

export default function Dashboard() {
  const [kampanyalar, setKampanyalar] = useState([]);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(null);

  // İstatistik kartları için tüm kampanyaları çek
  useEffect(() => {
    setYukleniyor(true);
    setHata(null);
    kampanyalariGetir()
      .then((veri) => setKampanyalar(veri))
      .catch((e) => setHata(e.message))
      .finally(() => setYukleniyor(false));
  }, []);

  return (
    <div>
      <Title level={3}>Genel Bakış</Title>

      <TazelikSeridi />

      {hata && (
        <Alert
          type="error"
          title="Veri alınamadı"
          description={hata}
          style={{ marginBottom: 16 }}
          showIcon
        />
      )}

      {yukleniyor ? (
        <Spin description="İstatistikler yükleniyor..." />
      ) : (
        <IstatistikKartlari kampanyalar={kampanyalar} />
      )}
    </div>
  );
}

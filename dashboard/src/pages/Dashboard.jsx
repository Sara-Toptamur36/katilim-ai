import { useEffect, useState } from "react";
import { Alert } from "antd";
import { kampanyalariGetir } from "../api/client";
import KampanyaTablosu from "../components/KampanyaTablosu";
import FiltrePaneli from "../components/FiltrePaneli";

export default function Dashboard() {
  const [kampanyalar, setKampanyalar] = useState([]);
  const [tumKampanyalar, setTumKampanyalar] = useState([]); // filtre secenekleri icin
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(null);
  const [filtreler, setFiltreler] = useState({});

  // Filtre secenekleri icin bir kez, hic filtresiz veri cekilir
  useEffect(() => {
    kampanyalariGetir()
      .then((veri) => setTumKampanyalar(veri))
      .catch(() => {});
  }, []);

  // Filtreler degistikce, sunucu tarafinda filtrelenmis veri cekilir
  useEffect(() => {
    setYukleniyor(true);
    setHata(null);
    kampanyalariGetir(filtreler)
      .then((veri) => setKampanyalar(veri))
      .catch((e) => setHata(e.message))
      .finally(() => setYukleniyor(false));
  }, [filtreler]);

  const bankalar = [...new Set(tumKampanyalar.map((k) => k.banka))];
  const turler = [...new Set(tumKampanyalar.map((k) => k.kampanya_turu))];

  return (
    <div>
      <h2>Kampanya Karsilastirma Panosu</h2>
      <FiltrePaneli
        bankalar={bankalar}
        turler={turler}
        filtreler={filtreler}
        onDegistir={setFiltreler}
      />
      {hata && (
        <Alert
          type="error"
          message="Veri alinamadi"
          description={hata}
          style={{ marginBottom: 16 }}
          showIcon
        />
      )}
      <KampanyaTablosu kampanyalar={kampanyalar} yukleniyor={yukleniyor} />
    </div>
  );
}

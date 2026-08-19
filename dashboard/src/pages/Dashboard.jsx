import { useEffect, useState } from "react";
import { Alert, Divider, Typography } from "antd";
import { kampanyalariGetir } from "../api/client";
import KampanyaTablosu from "../components/KampanyaTablosu";
import FiltrePaneli from "../components/FiltrePaneli";
import IstatistikKartlari from "../components/IstatistikKartlari";
import EtkiSkoruKarti from "../components/EtkiSkoruKarti";
import KampanyaTarihcesiKarti from "../components/KampanyaTarihcesiKarti";
import KarsilastirmaPaneli from "../components/KarsilastirmaPaneli";
import RakipMatrisi from "../components/RakipMatrisi";
import TazelikSeridi from "../components/TazelikSeridi";
import TerminolojiSozlugu from "../components/TerminolojiSozlugu";

const { Title } = Typography;

export default function Dashboard() {
  const [kampanyalar, setKampanyalar] = useState([]);
  const [tumKampanyalar, setTumKampanyalar] = useState([]); // filtre secenekleri icin
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(null);
  const [filtreler, setFiltreler] = useState({});
  const [secilenIdler, setSecilenIdler] = useState([]);

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

  const rowSelection = {
    selectedRowKeys: secilenIdler,
    onChange: setSecilenIdler,
  };

  return (
    <div>
      <Title level={3}>Kampanya Karsilastirma Panosu</Title>

      <TazelikSeridi />

      <IstatistikKartlari kampanyalar={kampanyalar} />

      <FiltrePaneli
        bankalar={bankalar}
        turler={turler}
        filtreler={filtreler}
        onDegistir={setFiltreler}
      />

      {hata && (
        <Alert
          type="error"
          title="Veri alinamadi"
          description={hata}
          style={{ marginBottom: 16 }}
          showIcon
        />
      )}

      <KampanyaTablosu
        kampanyalar={kampanyalar}
        yukleniyor={yukleniyor}
        rowSelection={rowSelection}
      />

      {/* Tek kampanya secildiginde "bu iyi bir kampanya mi?" sorusu;
          iki ve uzeri secildiginde karsilastirma paneli devreye girer. */}
      {secilenIdler.length === 1 && (
        <>
          <Divider />
          <Title level={4}>Etki Skoru</Title>
          <EtkiSkoruKarti kampanyaId={secilenIdler[0]} />

          <Divider />
          <Title level={4}>Değişim Tarihçesi</Title>
          <KampanyaTarihcesiKarti kampanyaId={secilenIdler[0]} />
        </>
      )}

      <Divider />
      <Title level={4}>Kampanya Karsilastir</Title>
      <KarsilastirmaPaneli secilenIdler={secilenIdler} />

      <Divider />
      <Title level={4}>Rakip Analizi</Title>
      <RakipMatrisi turler={turler} />

      <Divider />
      <Title level={4}>Terminoloji Sozlugu</Title>
      <TerminolojiSozlugu />
    </div>
  );
}

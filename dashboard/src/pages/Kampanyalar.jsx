import { useEffect, useState } from "react";
import { Alert, Divider, Typography } from "antd";
import { kampanyalariGetir } from "../api/client";
import FiltrePaneli from "../components/FiltrePaneli";
import KampanyaTablosu from "../components/KampanyaTablosu";
import EtkiSkoruKarti from "../components/EtkiSkoruKarti";
import KampanyaTarihcesiKarti from "../components/KampanyaTarihcesiKarti";
import KarPayiTablosuKarti from "../components/KarPayiTablosuKarti";

const { Title } = Typography;

export default function Kampanyalar() {
  const [kampanyalar, setKampanyalar] = useState([]);
  const [tumKampanyalar, setTumKampanyalar] = useState([]); // Filtre seçenekleri için tüm veriler
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(null);
  const [filtreler, setFiltreler] = useState({});
  const [secilenIdler, setSecilenIdler] = useState([]);

  // Filtre seçenekleri için bir kez, filtresiz veri çekilir
  useEffect(() => {
    kampanyalariGetir()
      .then((veri) => setTumKampanyalar(veri))
      .catch(() => {});
  }, []);

  // Filtreler değiştikçe sunucu tarafından filtrelenmiş veri çekilir
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
  const secilenKampanya = kampanyalar.find((k) => k.id === secilenIdler[0]);

  const rowSelection = {
    selectedRowKeys: secilenIdler,
    onChange: setSecilenIdler,
  };

  return (
    <div>
      <Title level={3}>Kampanyalar</Title>

      <FiltrePaneli
        bankalar={bankalar}
        turler={turler}
        filtreler={filtreler}
        onDegistir={setFiltreler}
      />

      {hata && (
        <Alert
          type="error"
          title="Veri alınamadı"
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

      {/* Tek kampanya seçildiğinde etki skoru, değişim tarihçesi ve kâr payı tablosu */}
      {secilenIdler.length === 1 && (
        <>
          <Divider />
          <Title level={4}>Etki Skoru</Title>
          <EtkiSkoruKarti kampanyaId={secilenIdler[0]} />

          <Divider />
          <Title level={4}>Değişim Tarihçesi</Title>
          <KampanyaTarihcesiKarti kampanyaId={secilenIdler[0]} />

          {secilenKampanya?.kar_payi_tablosu && (
            <>
              <Divider />
              <KarPayiTablosuKarti tablolar={secilenKampanya.kar_payi_tablosu} />
            </>
          )}
        </>
      )}
    </div>
  );
}

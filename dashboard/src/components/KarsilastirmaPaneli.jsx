import { useState } from "react";
import { Select, Button, Space, Table, Alert, Tag } from "antd";
import { karsilastir } from "../api/client";

// api/comparison/compare_engine.py'daki KRITERLER sozlugu ile BIREBIR ayni
// olmali - sunucu, bu listenin disindaki bir kriteri 422 ile reddeder.
const KRITERLER = [
  { value: "en_dusuk_kar_payi", label: "En dusuk kar payi orani" },
  { value: "en_yuksek_odul", label: "En yuksek odul miktari" },
  { value: "en_uzun_vade", label: "En uzun vade secenegi" },
  { value: "en_dusuk_masraf", label: "En dusuk masraf/tahsis ucreti" },
  { value: "en_yuksek_tutar", label: "En yuksek finansman tutari" },
];

const sonucKolonlari = [
  { title: "#", dataIndex: "sira", key: "sira", width: 50 },
  { title: "Banka", dataIndex: "banka", key: "banka" },
  { title: "Kampanya", dataIndex: "kampanya_adi", key: "kampanya_adi" },
  {
    title: "Kriter Degeri",
    dataIndex: "kriter_degeri",
    key: "kriter_degeri",
    render: (deger) => (deger != null ? deger : "Belirtilmemis"),
  },
  {
    title: "Eksik Alanlar",
    dataIndex: "eksik_alanlar",
    key: "eksik_alanlar",
    render: (alanlar) =>
      alanlar && alanlar.length > 0 ? (
        alanlar.map((a) => (
          <Tag key={a} color="orange">
            {a}
          </Tag>
        ))
      ) : (
        <Tag color="green">Eksik yok</Tag>
      ),
  },
];

export default function KarsilastirmaPaneli({ secilenIdler }) {
  const [kriter, setKriter] = useState("en_dusuk_kar_payi");
  const [sonuc, setSonuc] = useState(null);
  const [yukleniyor, setYukleniyor] = useState(false);
  const [hata, setHata] = useState(null);

  const karsilastirmayiCalistir = async () => {
    setYukleniyor(true);
    setHata(null);
    try {
      const veri = await karsilastir(secilenIdler, kriter);
      setSonuc(veri);
    } catch (e) {
      setHata(e.response?.data?.detail || e.message);
      setSonuc(null);
    } finally {
      setYukleniyor(false);
    }
  };

  return (
    <div style={{ marginBottom: 24 }}>
      <Space wrap style={{ marginBottom: 12 }}>
        <Select
          style={{ width: 260 }}
          value={kriter}
          onChange={setKriter}
          options={KRITERLER}
        />
        <Button
          type="primary"
          onClick={karsilastirmayiCalistir}
          disabled={secilenIdler.length < 2}
          loading={yukleniyor}
        >
          Karsilastir ({secilenIdler.length} secili)
        </Button>
      </Space>

      {secilenIdler.length < 2 && (
        <p style={{ color: "#888" }}>
          Karsilastirmak icin tablodan en az 2 kampanya secin.
        </p>
      )}

      {hata && (
        <Alert type="error" title="Karsilastirma basarisiz" description={hata} showIcon />
      )}

      {sonuc && (
        <>
          {sonuc.audit?.sebep && (
            <Alert
              type="info"
              title={sonuc.audit.sebep}
              style={{ marginBottom: 12 }}
              showIcon
            />
          )}
          <Table
            columns={sonucKolonlari}
            dataSource={sonuc.sonuclar}
            rowKey="id"
            pagination={false}
            size="small"
            scroll={{ x: "max-content" }}
          />
        </>
      )}
    </div>
  );
}

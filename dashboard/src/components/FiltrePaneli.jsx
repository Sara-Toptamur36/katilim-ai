import { Select, Space } from "antd";

export default function FiltrePaneli({ bankalar, turler, filtreler, onDegistir }) {
  return (
    <Space style={{ marginBottom: 16 }}>
      <Select
        placeholder="Banka secin"
        style={{ width: 200 }}
        allowClear
        value={filtreler.banka}
        onChange={(deger) => onDegistir({ ...filtreler, banka: deger })}
        options={bankalar.map((b) => ({ value: b, label: b }))}
      />
      <Select
        placeholder="Kampanya turu"
        style={{ width: 240 }}
        allowClear
        value={filtreler.kampanya_turu}
        onChange={(deger) => onDegistir({ ...filtreler, kampanya_turu: deger })}
        options={turler.map((t) => ({ value: t, label: t }))}
      />
    </Space>
  );
}

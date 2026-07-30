import { Table, Tag } from "antd";

// Eksik veri GIZLENMEZ - "Belirtilmemis" yazilir (rapor Bolum 5.7/15, seffaflik ilkesi).
// Siralamada null degerler en sona gider (NULLS LAST mantigi, ?? 999 ile).
const kolonlar = [
  { title: "Banka", dataIndex: "banka", key: "banka" },
  { title: "Kampanya", dataIndex: "kampanya_adi", key: "kampanya_adi" },
  { title: "Tur", dataIndex: "kampanya_turu", key: "kampanya_turu" },
  {
    title: "Kar Payi Orani",
    dataIndex: "kar_payi_orani_percent",
    key: "kar_payi",
    render: (deger) => (deger != null ? `%${deger}` : "Belirtilmemis"),
    sorter: (a, b) =>
      (a.kar_payi_orani_percent ?? 999) - (b.kar_payi_orani_percent ?? 999),
  },
  {
    title: "Vade (ay)",
    dataIndex: "vade_ay",
    key: "vade",
    render: (deger) => (deger != null ? deger : "Belirtilmemis"),
    sorter: (a, b) => (a.vade_ay ?? 999) - (b.vade_ay ?? 999),
  },
  {
    title: "Odul",
    key: "odul",
    render: (_, kayit) =>
      kayit.odul_miktari != null
        ? `${kayit.odul_miktari} ${kayit.odul_birimi ?? ""}`
        : "Belirtilmemis",
  },
  {
    title: "Durum",
    dataIndex: "durum",
    key: "durum",
    render: (durum) => (
      <Tag color={durum === "ACTIVE" ? "green" : "default"}>
        {durum === "ACTIVE" ? "Aktif" : durum === "EXPIRED" ? "Suresi Dolmus" : "Bilinmiyor"}
      </Tag>
    ),
  },
];

export default function KampanyaTablosu({ kampanyalar, yukleniyor, rowSelection }) {
  return (
    <Table
      columns={kolonlar}
      dataSource={kampanyalar}
      rowKey="id"
      loading={yukleniyor}
      rowSelection={rowSelection}
      scroll={{ x: "max-content" }}
    />
  );
}

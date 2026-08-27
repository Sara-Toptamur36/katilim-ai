import { useState } from "react";
import { Table, Tag, Button } from "antd";
import { CheckCircleOutlined, WarningOutlined } from "@ant-design/icons";
import { finansalIpucuCikar } from "../../utils/cevapBicimlendirme";
import EvidenceCard from "../EvidenceCard";

function guncellikEtiketi(guncellik) {
  if (guncellik === "suresi_dolmus")
    return (
      <Tag color="red">
        <WarningOutlined /> Süresi dolmuş
      </Tag>
    );
  if (guncellik === "aktif")
    return (
      <Tag color="green">
        <CheckCircleOutlined /> Güncel
      </Tag>
    );
  return <Tag color="default">Belirtilmemiş</Tag>;
}

// Birden fazla kampanya doner geldiginde uzun metin yerine kullanilan
// karsilastirma tablosu. Oran/Vade/Tutar sutunlari kaynak metninden
// BIREBIR alinti (finansalIpucuCikar) - kaynakta yoksa "Belirtilmemiş"
// gosterilir, hicbir sayi hesaplanmaz/uydurulmaz.
export default function KarsilastirmaTablosu({ kampanyalar }) {
  const [genisletilenAnahtar, setGenisletilenAnahtar] = useState(null);

  const veri = kampanyalar.map((k, i) => {
    const birlesikMetin = k.kaynaklar.map((x) => x.metin).filter(Boolean).join(" ");
    const ipucu = finansalIpucuCikar(birlesikMetin);
    return {
      key: i,
      banka: k.banka,
      kampanya: k.kampanyaAdi ?? "Belirtilmemiş",
      oran: ipucu.oran ?? "Belirtilmemiş",
      vade: ipucu.vade ?? "Belirtilmemiş",
      tutar: ipucu.tutar ?? "Belirtilmemiş",
      guncellik: k.enIyiKaynak?.guncellik,
      kaynaklar: k.kaynaklar,
    };
  });

  // SUTUN GENISLIKLERI + scroll.x ZORUNLU (olculdu 27.08.2026, 784 px
  // genislikte gercek veriyle): genislik verilmeden antd sutunlari mevcut
  // dar alana SIKISTIRIYOR ve uzun kampanya adlari harf harf alt alta
  // sariliyordu ("K u v e y t T ü r k") - tablo okunamaz hale geliyordu.
  // scroll={{x:true}} tek basina yetmiyor: tasma olmadigi icin yatay kaydirma
  // hic devreye girmiyordu. Toplam genislik scroll.x ile SABITLENIR, dar
  // ekranda tablo kendi icinde yatay kayar (govde kaymaz).
  const sutunlar = [
    { title: "Banka", dataIndex: "banka", key: "banka", width: 130, ellipsis: true },
    { title: "Kampanya", dataIndex: "kampanya", key: "kampanya", width: 200, ellipsis: true },
    { title: "Oran", dataIndex: "oran", key: "oran", width: 90 },
    { title: "Vade", dataIndex: "vade", key: "vade", width: 90 },
    { title: "Tutar", dataIndex: "tutar", key: "tutar", width: 110 },
    {
      title: "Durum",
      dataIndex: "guncellik",
      key: "guncellik",
      width: 130,
      render: (v) => guncellikEtiketi(v),
    },
    {
      title: "",
      key: "kaynak",
      width: 110,
      render: (_, kayit) => (
        <Button
          type="link"
          size="small"
          onClick={() =>
            setGenisletilenAnahtar((a) => (a === kayit.key ? null : kayit.key))
          }
        >
          Kaynağı Gör
        </Button>
      ),
    },
  ];

  return (
    <Table
      className="karsilastirma-tablosu"
      size="small"
      dataSource={veri}
      columns={sutunlar}
      pagination={false}
      style={{ marginTop: 8, maxWidth: 860 }}
      scroll={{ x: 860 }}
      expandable={{
        expandedRowKeys: genisletilenAnahtar === null ? [] : [genisletilenAnahtar],
        showExpandColumn: false,
        expandedRowRender: (kayit) => (
          <div>
            {kayit.kaynaklar.map((k, i) => (
              <EvidenceCard key={i} kaynak={k} boyut="kucuk" />
            ))}
          </div>
        ),
      }}
    />
  );
}

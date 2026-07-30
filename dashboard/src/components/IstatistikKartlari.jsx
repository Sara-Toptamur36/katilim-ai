import { Card, Statistic, Row, Col } from "antd";

export default function IstatistikKartlari({ kampanyalar }) {
  const karPayiOlanlar = kampanyalar.filter((k) => k.kar_payi_orani_percent != null);
  const enDusukKarPayi =
    karPayiOlanlar.length > 0
      ? Math.min(...karPayiOlanlar.map((k) => k.kar_payi_orani_percent))
      : null;

  return (
    <Row gutter={16} style={{ marginBottom: 16 }}>
      <Col span={8}>
        <Card>
          <Statistic title="Toplam Kampanya" value={kampanyalar.length} />
        </Card>
      </Col>
      <Col span={8}>
        <Card>
          <Statistic
            title="Aktif Banka Sayisi"
            value={new Set(kampanyalar.map((k) => k.banka)).size}
          />
        </Card>
      </Col>
      <Col span={8}>
        <Card>
          <Statistic
            title="En Dusuk Kar Payi"
            value={enDusukKarPayi != null ? enDusukKarPayi : "Belirtilmemis"}
            suffix={enDusukKarPayi != null ? "%" : ""}
          />
        </Card>
      </Col>
    </Row>
  );
}

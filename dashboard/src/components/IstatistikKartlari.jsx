import { Card, Statistic, Row, Col, Tooltip } from "antd";

// DUZELTILEN YANLIS ETIKET (24.08.2026): kart basligi "Aktif Banka Sayisi"
// diyordu ama hesap TUM bankalari sayiyordu - durum alani o tarihte
// veritabaninda hep BILINMIYOR oldugu icin "aktif" diye bir ayrim zaten
// yapilamiyordu. Yasam dongusu hesabi duzeltilince (bkz.
// api/kampanya_repository._durum_coz) ayrim gercekten mumkun oldu:
// baslik durustlestirildi ve AYRI bir "Aktif Kampanya" karti eklendi.
export default function IstatistikKartlari({ kampanyalar }) {
  const karPayiOlanlar = kampanyalar.filter((k) => k.kar_payi_orani_percent != null);
  const enDusukKarPayi =
    karPayiOlanlar.length > 0
      ? Math.min(...karPayiOlanlar.map((k) => k.kar_payi_orani_percent))
      : null;
  const aktifSayisi = kampanyalar.filter((k) => k.durum === "ACTIVE").length;

  return (
    <Row gutter={16} style={{ marginBottom: 16 }}>
      <Col span={6}>
        <Card>
          <Statistic title="Toplam Kampanya" value={kampanyalar.length} />
        </Card>
      </Col>
      <Col span={6}>
        <Tooltip title="Bitiş tarihi bugünden ileride olan kampanyalar. Tarihi belirtilmemiş kayıtlar 'bilinmiyor' sayılır, aktif sayılmaz.">
          <Card>
            <Statistic title="Aktif Kampanya" value={aktifSayisi} />
          </Card>
        </Tooltip>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title="Banka Sayısı"
            value={new Set(kampanyalar.map((k) => k.banka)).size}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title="En Düşük Kâr Payı"
            value={enDusukKarPayi != null ? enDusukKarPayi : "Belirtilmemiş"}
            suffix={enDusukKarPayi != null ? "%" : ""}
          />
        </Card>
      </Col>
    </Row>
  );
}

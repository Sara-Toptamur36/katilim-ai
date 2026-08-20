import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Input,
  Progress,
  Row,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import { musteriSesiOrneklerGetir, musteriSesiSiniflandir } from "../api/client";

// FAZ 1 T8 - mentorun 3.7'deki "en dusuk riskli yol" onerisi: gercek
// Sikayetvar/musteri verisi ancak kurumsal/hukuki (KVKK) izin surecinden
// sonra Faz 2'de ingest edilecek. Bu ekran o zamana kadar KURAL TABANLI
// bir Complaint Insight demosu - sentetik veri uzerinde.
//
// DURUSTLUK ILKESI (rapor Bolum 5.7/15 ile ayni): bu ekran GERCEK musteri
// verisi gosteriyormus gibi YAPILMAZ. "Sentetik demo verisi" uyarisi her
// zaman gorunur kalir, gizlenmez.

const ORNEK_METIN = "Kampanyaya katıldım ama vaat edilen ödül tutarı hesabıma hâlâ geçmedi.";

const kolonlar = [
  { title: "ID", dataIndex: "id", key: "id", width: 90 },
  { title: "Metin", dataIndex: "metin", key: "metin" },
  {
    title: "Tema",
    dataIndex: "tema",
    key: "tema",
    render: (tema) =>
      tema ? <Tag color="geekblue">{tema}</Tag> : <Typography.Text type="secondary">—</Typography.Text>,
  },
  {
    title: "Güven",
    dataIndex: "guven",
    key: "guven",
    width: 100,
    render: (guven) => (guven > 0 ? `%${Math.round(guven * 100)}` : "—"),
  },
  {
    title: "Eşleşen ifadeler",
    dataIndex: "eslesen_ifadeler",
    key: "eslesen_ifadeler",
    render: (ifadeler) => (
      <Space size={4} wrap>
        {ifadeler.map((i) => (
          <Tag key={i}>{i}</Tag>
        ))}
      </Space>
    ),
  },
];

export default function MusteriSesi() {
  const [metin, setMetin] = useState("");
  const [sonuc, setSonuc] = useState(null);
  const [yukleniyor, setYukleniyor] = useState(false);
  const [hata, setHata] = useState(null);

  const [ornekVeri, setOrnekVeri] = useState(null);
  const [ornekYukleniyor, setOrnekYukleniyor] = useState(true);
  const [ornekHata, setOrnekHata] = useState(null);

  useEffect(() => {
    musteriSesiOrneklerGetir()
      .then(setOrnekVeri)
      .catch((e) => setOrnekHata(e.message))
      .finally(() => setOrnekYukleniyor(false));
  }, []);

  const siniflandir = async () => {
    setYukleniyor(true);
    setHata(null);
    setSonuc(null);
    try {
      setSonuc(await musteriSesiSiniflandir(metin));
    } catch (e) {
      setHata(e.response?.data?.detail?.[0]?.msg ?? e.message);
    } finally {
      setYukleniyor(false);
    }
  };

  return (
    <div>
      <Typography.Title level={3}>Müşteri Sesi (Complaint Insight)</Typography.Title>

      <Alert
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
        title="Bu ekrandaki veri SENTETİKTİR — gerçek müşteri şikâyeti değildir"
        description={
          ornekVeri?.aciklama ??
          "Örnekler elle yazıldı, hiçbir gerçek bankaya atfedilmiyor. Gerçek müşteri verisi ancak kurumsal/hukuki (KVKK) izin sürecinden sonra kullanılacak (bkz. proje Faz 2 planı)."
        }
      />

      <Typography.Paragraph type="secondary">
        Kural tabanlı bir sınıflandırıcı, serbest metni 10 temalı bir taksonomiye göre
        eşleştirir. Hiçbir ifade eşleşmezse tema <strong>uydurulmaz</strong> — boş döner.
      </Typography.Paragraph>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={10}>
          <Card size="small" title="Kendi metninizi deneyin">
            <Input.TextArea
              value={metin}
              onChange={(e) => setMetin(e.target.value)}
              rows={4}
              placeholder="Örn: Kampanyaya katıldım ama ödülüm hesabıma geçmedi…"
            />
            <Space style={{ marginTop: 12 }} wrap>
              <Button
                type="primary"
                onClick={siniflandir}
                loading={yukleniyor}
                disabled={metin.trim().length < 1}
              >
                Sınıflandır
              </Button>
              <Button onClick={() => setMetin(ORNEK_METIN)}>Örnek metin</Button>
            </Space>
          </Card>
        </Col>

        <Col xs={24} lg={14}>
          {hata && <Alert type="error" title="Sınıflandırılamadı" description={hata} showIcon />}
          {sonuc && (
            <Card size="small" title="Sonuç">
              {sonuc.tema ? (
                <Space direction="vertical" style={{ width: "100%" }}>
                  <Tag color="geekblue" style={{ fontSize: 14, padding: "4px 10px" }}>
                    {sonuc.tema}
                  </Tag>
                  <Progress percent={Math.round(sonuc.guven * 100)} size="small" style={{ maxWidth: 240 }} />
                  <Space size={4} wrap>
                    {sonuc.eslesen_ifadeler.map((i) => (
                      <Tag key={i}>{i}</Tag>
                    ))}
                  </Space>
                </Space>
              ) : (
                <Alert
                  type="info"
                  title="Hiçbir tema eşleşmedi"
                  description="Bu bir hata değil — sistem, bilinen 10 temadan hiçbiriyle ilgisi olmayan metne zorla bir etiket yapıştırmaz."
                  showIcon
                />
              )}
            </Card>
          )}
        </Col>
      </Row>

      <Typography.Title level={4}>Sentetik örnek seti</Typography.Title>
      {ornekHata && <Alert type="error" title="Örnekler alınamadı" description={ornekHata} showIcon />}
      {ornekVeri && (
        <Table
          columns={kolonlar}
          dataSource={ornekVeri.ornekler}
          rowKey="id"
          loading={ornekYukleniyor}
          pagination={false}
          size="small"
          scroll={{ x: "max-content" }}
        />
      )}
    </div>
  );
}

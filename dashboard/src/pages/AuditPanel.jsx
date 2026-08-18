import { Descriptions, Tag, Table, Card, Row, Col, Statistic, Typography, Empty } from "antd";
import { useAudit } from "../context/AuditContext";
import KopyalaButonu from "../components/KopyalaButonu";

const { Title } = Typography;

const gecmisKolonlari = [
  { title: "Zaman", dataIndex: "zaman", key: "zaman", render: (z) => new Date(z).toLocaleTimeString("tr-TR") },
  { title: "Soru", dataIndex: "soru", key: "soru", ellipsis: true },
  { title: "Niyet", dataIndex: "intent", key: "intent" },
  { title: "Araç", dataIndex: "cagrilan_arac", key: "cagrilan_arac" },
  { title: "Gecikme (ms)", dataIndex: "latency_ms", key: "latency_ms" },
  {
    title: "Cache",
    dataIndex: "cache_hit",
    key: "cache_hit",
    render: (v) => <Tag color={v ? "green" : "default"}>{v ? "HIT" : "MISS"}</Tag>,
  },
];

const retrieverKolonlari = [
  { title: "Chunk ID", dataIndex: "chunk_id", key: "chunk_id" },
  {
    title: "Benzerlik",
    dataIndex: "similarity_score",
    key: "similarity_score",
    render: (v) => (v != null ? v.toFixed(3) : "Belirtilmemiş"),
  },
  {
    title: "Rerank Skoru",
    dataIndex: "rerank_score",
    key: "rerank_score",
    render: (v) => (v != null ? v.toFixed(3) : "Belirtilmemiş"),
  },
  { title: "Metin (kısa)", dataIndex: "metin_ozeti", key: "metin_ozeti", ellipsis: true },
];

export default function AuditPanel() {
  const { sonAudit, auditGecmisi } = useAudit();

  if (!sonAudit) {
    return (
      <div>
        <Title level={3}>Jüri Audit Paneli</Title>
        <Empty description="Henüz sorgu yok. Önce Chatbot ekranından bir soru sorun." />
      </div>
    );
  }

  return (
    <div>
      <Title level={3}>Jüri Audit Paneli</Title>

      <Descriptions title="Son Sorgu Denetim Bilgisi" bordered column={2} style={{ marginBottom: 24 }}>
        <Descriptions.Item label="Algılanan Niyet">
          {sonAudit.intent ?? "Belirtilmemiş"}{" "}
          {sonAudit.intent_confidence != null && (
            <Tag color="blue">{(sonAudit.intent_confidence * 100).toFixed(0)}%</Tag>
          )}
        </Descriptions.Item>
        <Descriptions.Item label="Çağrılan Araç">
          <Tag color="purple">{sonAudit.cagrilan_arac ?? "Belirtilmemiş"}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Yanıt Süresi">
          {sonAudit.latency_ms != null ? `${sonAudit.latency_ms} ms` : "Belirtilmemiş"}
        </Descriptions.Item>
        <Descriptions.Item label="Cache">
          <Tag color={sonAudit.cache_hit ? "green" : "default"}>
            {sonAudit.cache_hit ? "HIT" : "MISS"}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Model">{sonAudit.model ?? "Belirtilmemiş"}</Descriptions.Item>
        <Descriptions.Item label="Temperature">
          {sonAudit.temperature ?? "Belirtilmemiş"}
        </Descriptions.Item>
        {sonAudit.regex_basari_orani != null && (
          <Descriptions.Item label="Regex/Model Başarı Oranı" span={2}>
            {(sonAudit.regex_basari_orani * 100).toFixed(1)}%
          </Descriptions.Item>
        )}
        {sonAudit.sebep && (
          <Descriptions.Item label="Sebep / Açıklama" span={2}>
            {sonAudit.sebep}
          </Descriptions.Item>
        )}
      </Descriptions>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card size="small">
            <Statistic
              title="Extraction Confidence"
              value={sonAudit.extraction_confidence != null ? sonAudit.extraction_confidence * 100 : 0}
              suffix="%"
              precision={1}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small">
            <Statistic
              title="Response Confidence"
              value={sonAudit.response_confidence != null ? sonAudit.response_confidence * 100 : 0}
              suffix="%"
              precision={1}
            />
          </Card>
        </Col>
      </Row>

      {sonAudit.sql_sorgusu && (
        <Card
          title="Çalıştırılan SQL Sorgusu"
          size="small"
          extra={<KopyalaButonu metin={sonAudit.sql_sorgusu} />}
          style={{ marginBottom: 24 }}
        >
          <pre style={{ background: "#f5f5f5", padding: 12, overflow: "auto" }}>
            {sonAudit.sql_sorgusu}
          </pre>
        </Card>
      )}

      <Card
        title="Ham Audit JSON"
        size="small"
        extra={<KopyalaButonu metin={JSON.stringify(sonAudit, null, 2)} />}
        style={{ marginBottom: 24 }}
      >
        <pre style={{ background: "#f5f5f5", padding: 12, maxHeight: 300, overflow: "auto" }}>
          {JSON.stringify(sonAudit, null, 2)}
        </pre>
      </Card>

      {sonAudit.retriever_sonuclari && sonAudit.retriever_sonuclari.length > 0 && (
        <Table
          title={() => "Retriever Sonuçları"}
          size="small"
          dataSource={sonAudit.retriever_sonuclari}
          rowKey="chunk_id"
          columns={retrieverKolonlari}
          pagination={false}
          style={{ marginBottom: 24 }}
        />
      )}

      <Table
        title={() => "Sorgu Geçmişi (son 20)"}
        size="small"
        dataSource={auditGecmisi}
        rowKey="zaman"
        columns={gecmisKolonlari}
        pagination={false}
        scroll={{ x: "max-content" }}
      />
    </div>
  );
}

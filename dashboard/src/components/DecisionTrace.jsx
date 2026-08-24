import { useState } from "react";
import {
  Modal,
  Steps,
  Tag,
  Typography,
  Descriptions,
  Table,
  Alert,
  Divider,
  Button,
  Tooltip,
} from "antd";
import {
  AuditOutlined,
  LinkOutlined,
  BulbOutlined,
  CalculatorOutlined,
  SearchOutlined,
  WarningOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";

/**
 * DecisionTrace — "Bu cevabı nereden çıkardın?" modal zinciri.
 *
 * Kullanım:
 *   <DecisionTrace audit={yanit.audit} soru="kullanıcı sorusu" />
 *
 * audit objesi (backend AuditBilgisi):
 *   trace_id, intent, intent_confidence, cagrilan_arac,
 *   extraction_confidence, retriever_sonuclari, sql_sorgusu,
 *   response_confidence, dogrulama, terminoloji_tutarli,
 *   latency_ms, model, demo_snapshot
 *
 * 5 adım: Soru → Niyet → Araç → Hesaplama/Retrieval → Doğrulama
 */

// Araç adını okunabilir metne çevir
const ARAC_ETIKET = {
  rag:         { label: "RAG — Vektör Arama",       ikon: <SearchOutlined />,    renk: "blue"   },
  sql:         { label: "SQL — Veritabanı",          ikon: <LinkOutlined />,      renk: "cyan"   },
  calculator:  { label: "Hesap Makinesi (Python)",   ikon: <CalculatorOutlined />, renk: "orange" },
  sozluk:      { label: "Terminoloji Sözlüğü",       ikon: <BulbOutlined />,      renk: "purple" },
  extraction:  { label: "Çıkarım Motoru",             ikon: <AuditOutlined />,     renk: "geekblue" },
  fallback:    { label: "Güvenli Başarısızlık",       ikon: <WarningOutlined />,   renk: "red"    },
};

function aracMeta(arac) {
  return ARAC_ETIKET[arac] ?? { label: arac ?? "Bilinmiyor", ikon: <BulbOutlined />, renk: "default" };
}

function traceIdKisa(id) {
  if (!id) return null;
  return id.slice(0, 8) + "…";
}

// 5 adımlık karar zinciri
function adimlarUret(audit, soru) {
  return [
    {
      title: "Kullanıcı Sorusu",
      description: soru ? `"${soru.slice(0, 80)}${soru.length > 80 ? "…" : ""}"` : "—",
      icon: <SearchOutlined />,
      status: "finish",
    },
    {
      title: "Niyet Tespiti",
      description: audit?.intent
        ? `${audit.intent} (güven: ${audit.intent_confidence != null ? `%${Math.round(audit.intent_confidence * 100)}` : "—"})`
        : "—",
      icon: <BulbOutlined />,
      status: audit?.intent ? "finish" : "wait",
    },
    {
      title: "Araç Seçimi",
      description: aracMeta(audit?.cagrilan_arac).label,
      icon: aracMeta(audit?.cagrilan_arac).ikon,
      status: audit?.cagrilan_arac ? "finish" : "wait",
    },
    {
      title: "Hesaplama / Retrieval",
      description: audit?.cagrilan_arac === "calculator"
        ? "Deterministik Python — LLM hesaplamıyor"
        : audit?.retriever_sonuclari?.length > 0
          ? `${audit.retriever_sonuclari.length} parça bulundu`
          : audit?.sql_sorgusu
            ? "SQL sorgusu çalıştırıldı"
            : "—",
      icon: <CalculatorOutlined />,
      status: "finish",
    },
    {
      title: "Doğrulama",
      description: audit?.dogrulama?.durum
        ? `${audit.dogrulama.durum} (${audit.dogrulama.kaynak_sayisi ?? 0} kaynak)`
        : "—",
      icon: <CheckCircleOutlined />,
      status: audit?.dogrulama ? "finish" : "wait",
    },
  ];
}

// Retriever sonuçları tablosu
const RETRIEVER_SUTUNLAR = [
  { title: "Chunk ID", dataIndex: "chunk_id", key: "chunk_id", ellipsis: true, width: 180, render: (v) => <Typography.Text code style={{ fontSize: 10 }}>{v?.slice(0, 20)}…</Typography.Text> },
  { title: "Benzerlik", dataIndex: "similarity_score", key: "sim", width: 90, render: (v) => v != null ? `%${(v * 100).toFixed(1)}` : "—" },
  { title: "Rerank", dataIndex: "rerank_score", key: "rerank", width: 80, render: (v) => v != null ? v.toFixed(3) : "—" },
  { title: "Özet", dataIndex: "metin_ozeti", key: "ozet", ellipsis: true },
];

// Doğrulama durum ikonu
function dogrulamaDurum(durum) {
  const MAP = {
    dogrulandi: { renk: "green",  ikon: <CheckCircleOutlined />, etiket: "Doğrulandı" },
    kismi:      { renk: "orange", ikon: <WarningOutlined />,     etiket: "Kısmen Doğrulandı" },
    belirsiz:   { renk: "default",ikon: null,                     etiket: "Belirsiz" },
  };
  const m = MAP[durum] ?? MAP.belirsiz;
  return <Tag color={m.renk}>{m.ikon} {m.etiket}</Tag>;
}

export default function DecisionTrace({ audit, soru }) {
  const [acik, setAcik] = useState(false);

  if (!audit) return null;

  const meta = aracMeta(audit.cagrilan_arac);
  const adimlar = adimlarUret(audit, soru);

  return (
    <>
      <Tooltip title="Bu cevabı nereden çıkardı? — Karar zinciri">
        <Button
          size="small"
          type="text"
          icon={<AuditOutlined />}
          onClick={() => setAcik(true)}
          style={{ fontSize: 11, color: "#8c8c8c" }}
        >
          Karar zinciri
        </Button>
      </Tooltip>

      <Modal
        open={acik}
        onCancel={() => setAcik(false)}
        footer={null}
        width={720}
        title={
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <AuditOutlined />
            <span>Karar Zinciri</span>
            {audit.trace_id && (
              <Tooltip title={`Tam trace_id: ${audit.trace_id}`}>
                <Tag
                  color="default"
                  style={{ fontFamily: "monospace", fontSize: 10, cursor: "help" }}
                >
                  #{traceIdKisa(audit.trace_id)}
                </Tag>
              </Tooltip>
            )}
            {audit.demo_snapshot && (
              <Tag color="gold">DEMO SNAPSHOT</Tag>
            )}
          </div>
        }
      >
        {/* 5 adım zinciri */}
        <Steps
          direction="vertical"
          size="small"
          items={adimlar}
          style={{ marginBottom: 20 }}
        />

        <Divider style={{ margin: "12px 0" }} />

        {/* Niyet + araç detayı */}
        <Descriptions size="small" bordered column={2} style={{ marginBottom: 16 }}>
          <Descriptions.Item label="Tespit edilen niyet">
            <Tag color="blue">{audit.intent ?? "—"}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Niyet güveni">
            {audit.intent_confidence != null
              ? `%${Math.round(audit.intent_confidence * 100)}`
              : "—"}
          </Descriptions.Item>
          <Descriptions.Item label="Seçilen araç">
            <Tag color={meta.renk}>
              {meta.ikon} {meta.label}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Model">
            <Typography.Text code style={{ fontSize: 11 }}>
              {audit.model ?? "—"}
            </Typography.Text>
          </Descriptions.Item>
          <Descriptions.Item label="Yanıt güveni">
            {audit.response_confidence != null
              ? `%${Math.round(audit.response_confidence * 100)}`
              : "—"}
          </Descriptions.Item>
          <Descriptions.Item label="Gecikme">
            {audit.latency_ms != null ? `${audit.latency_ms} ms` : "—"}
          </Descriptions.Item>
          <Descriptions.Item label="Çıkarım güveni">
            {audit.extraction_confidence != null
              ? `%${Math.round(audit.extraction_confidence * 100)}`
              : "—"}
          </Descriptions.Item>
          <Descriptions.Item label="Regex başarı">
            {audit.regex_basari_orani != null
              ? `%${Math.round(audit.regex_basari_orani * 100)}`
              : "—"}
          </Descriptions.Item>
        </Descriptions>

        {/* SQL (karşılaştırma/hesap yolunda) */}
        {audit.sql_sorgusu && (
          <>
            <Typography.Text strong style={{ display: "block", marginBottom: 6 }}>
              Çalıştırılan SQL
            </Typography.Text>
            <pre
              style={{
                background: "#0d0d0d",
                color: "#c5e6a5",
                padding: "10px 14px",
                borderRadius: 6,
                fontSize: 11,
                overflow: "auto",
                maxHeight: 160,
                marginBottom: 16,
              }}
            >
              {audit.sql_sorgusu}
            </pre>
          </>
        )}

        {/* Retriever sonuçları (RAG yolunda) */}
        {audit.retriever_sonuclari?.length > 0 && (
          <>
            <Typography.Text strong style={{ display: "block", marginBottom: 6 }}>
              Retriever Sonuçları ({audit.retriever_sonuclari.length} parça)
            </Typography.Text>
            <Table
              dataSource={audit.retriever_sonuclari}
              columns={RETRIEVER_SUTUNLAR}
              size="small"
              rowKey={(_, i) => i}
              pagination={false}
              style={{ marginBottom: 16 }}
              scroll={{ x: true }}
            />
          </>
        )}

        {/* Doğrulama bloğu */}
        {audit.dogrulama && (
          <>
            <Typography.Text strong style={{ display: "block", marginBottom: 8 }}>
              Doğrulama Sonucu
            </Typography.Text>
            <Descriptions size="small" bordered column={2}>
              <Descriptions.Item label="Durum">
                {dogrulamaDurum(audit.dogrulama.durum)}
              </Descriptions.Item>
              <Descriptions.Item label="Kaynak sayısı">
                {audit.dogrulama.kaynak_sayisi ?? "—"}
              </Descriptions.Item>
              {audit.dogrulama.eslesen_alanlar?.length > 0 && (
                <Descriptions.Item label="Eşleşen alanlar" span={2}>
                  {audit.dogrulama.eslesen_alanlar.map((a, i) => (
                    <Tag key={i} color="green">{a}</Tag>
                  ))}
                </Descriptions.Item>
              )}
              {audit.dogrulama.eslesmeyen_alanlar?.length > 0 && (
                <Descriptions.Item label="Eşleşmeyen alanlar" span={2}>
                  {audit.dogrulama.eslesmeyen_alanlar.map((a, i) => (
                    <Tag key={i} color="red">{a}</Tag>
                  ))}
                </Descriptions.Item>
              )}
            </Descriptions>
          </>
        )}

        {/* Açıklama notu */}
        <Alert
          type="info"
          showIcon
          style={{ marginTop: 16 }}
          message="Epistemik şeffaflık"
          description="Bu panel, yapay zeka yanıtının kaynaklanma zincirini gösterir. Güven skorları 'doğruluk oranı' değil, 'eşleşme/benzerlik skoru'dur."
        />
      </Modal>
    </>
  );
}

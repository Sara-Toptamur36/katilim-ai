import { Descriptions, Tag, Table, Card, Row, Col, Statistic, Typography, Empty } from "antd";
import { CheckOutlined, ExclamationOutlined } from "@ant-design/icons";
import { useAudit } from "../context/AuditContext";
import KopyalaButonu from "../components/KopyalaButonu";

const { Title } = Typography;

// Alan adları haritası
const ALAN_ADLARI = {
  kar_payi_orani_percent: "Kâr payı oranı",
  vade_ay: "Vade",
  taksit_sayisi: "Taksit sayısı",
  odul_miktari: "Ödül miktarı",
  finansman_tutari: "Finansman tutarı",
  masraf_durumu: "Masraf durumu",
  tahsis_ucreti: "Tahsis ücreti",
  erteleme_suresi_ay: "Erteleme süresi",
};

// Yığılmış çubuk alt bileşeni (kayit_sayisi genişliğinde)
function YigilmisCubuk({ dogrulanan = 0, dogrulanamayan = 0, calistirilmamis = 0, kayitSayisi = 0 }) {
  if (!kayitSayisi || kayitSayisi <= 0) return null;

  const pctDogrulanan = (dogrulanan / kayitSayisi) * 100;
  const pctDogrulanamayan = (dogrulanamayan / kayitSayisi) * 100;
  const pctCalistirilmamis = (calistirilmamis / kayitSayisi) * 100;

  return (
    <div
      style={{
        display: "flex",
        width: "100%",
        height: 6,
        borderRadius: 3,
        overflow: "hidden",
        backgroundColor: "var(--kenarlik, #e4ddcb)",
        marginTop: 6,
      }}
    >
      {pctDogrulanan > 0 && (
        <div
          title={`Doğrulandı: ${dogrulanan}`}
          style={{ width: `${pctDogrulanan}%`, backgroundColor: "#169276", height: "100%" }}
        />
      )}
      {pctDogrulanamayan > 0 && (
        <div
          title={`Doğrulanamadı: ${dogrulanamayan}`}
          style={{ width: `${pctDogrulanamayan}%`, backgroundColor: "#d4a34b", height: "100%" }}
        />
      )}
      {pctCalistirilmamis > 0 && (
        <div
          title={`Çalıştırılmadı: ${calistirilmamis}`}
          style={{ width: `${pctCalistirilmamis}%`, backgroundColor: "#b9bdb6", height: "100%" }}
        />
      )}
    </div>
  );
}

// Alan tablosu kolon tanımları
const dogrulamaKolonlari = [
  {
    title: "Alan",
    dataIndex: "alan",
    key: "alan",
    render: (alan, record) => {
      const turkce = ALAN_ADLARI[alan] || alan;
      return (
        <div>
          <div style={{ fontWeight: 500, color: "var(--yazi-koyu, #192b27)" }}>{turkce}</div>
          <YigilmisCubuk
            dogrulanan={record.dogrulanan}
            dogrulanamayan={record.dogrulanamayan}
            calistirilmamis={record.calistirilmamis}
            kayitSayisi={record.kayit_sayisi}
          />
        </div>
      );
    },
  },
  {
    title: "Doğrulandı",
    dataIndex: "dogrulanan",
    key: "dogrulanan",
    align: "right",
    render: (val) => <span style={{ color: "#169276", fontWeight: 600 }}>{val ?? 0}</span>,
  },
  {
    title: "Doğrulanamadı",
    dataIndex: "dogrulanamayan",
    key: "dogrulanamayan",
    align: "right",
    render: (val) => <span style={{ color: "#d4a34b", fontWeight: 600 }}>{val ?? 0}</span>,
  },
  {
    title: "Çalıştırılmadı",
    dataIndex: "calistirilmamis",
    key: "calistirilmamis",
    align: "right",
    render: (val) => <span style={{ color: "#7b8c86" }}>{val ?? 0}</span>,
  },
  {
    title: "Kayıt",
    dataIndex: "kayit_sayisi",
    key: "kayit_sayisi",
    align: "right",
    render: (val) => <span>{val ?? 0}</span>,
  },
];

// Kaynakta Doğrulama Ana Bölüm Bileşeni
function KaynaktaDogrulamaBolumu({ sonAudit }) {
  const dogrulama = sonAudit?.dogrulama;
  const dogrulananAlanlar = sonAudit?.dogrulanan_alanlar;

  const hasDogrulama =
    dogrulama &&
    Array.isArray(dogrulama.alanlar) &&
    dogrulama.alanlar.length > 0;

  const hasDogrulananAlanlar =
    dogrulananAlanlar &&
    typeof dogrulananAlanlar === "object" &&
    Object.keys(dogrulananAlanlar).length > 0;

  // 1) Başlık Rozeti
  let headerBadge = null;
  if (dogrulama?.durum === "dogrulandi") {
    headerBadge = (
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 4,
          padding: "3px 10px",
          borderRadius: 6,
          backgroundColor: "#ddf2ec",
          color: "#0c765f",
          fontSize: 12,
          fontWeight: 500,
        }}
      >
        <CheckOutlined />
        <span>Tüm alanlar doğrulandı</span>
      </span>
    );
  } else if (dogrulama?.durum === "kismi") {
    headerBadge = (
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 4,
          padding: "3px 10px",
          borderRadius: 6,
          backgroundColor: "#f8edcf",
          color: "#8c6219",
          fontSize: 12,
          fontWeight: 500,
        }}
      >
        <ExclamationOutlined />
        <span>Bir kısmı doğrulanamadı</span>
      </span>
    );
  } else if (dogrulama?.durum === "calistirilmamis") {
    headerBadge = (
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 4,
          padding: "3px 10px",
          borderRadius: 6,
          backgroundColor: "#eeeae0",
          color: "#7b8c86",
          fontSize: 12,
          fontWeight: 500,
        }}
      >
        <span>Verifier çalışmadı</span>
      </span>
    );
  }

  return (
    <Card size="small" style={{ marginBottom: 24 }}>
      {/* 1) BAŞLIK SATIRI */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
        <div style={{ fontSize: 16, fontWeight: 600, color: "var(--yazi-koyu, #192b27)" }}>
          Kaynakta Doğrulama
        </div>
        {headerBadge}
      </div>

      {/* 1) BAŞLIĞIN ALTINDAKİ 11px NOT */}
      <div style={{ fontSize: 11, color: "var(--yazi-soluk, #7b8c86)", marginBottom: 16 }}>
        Bu hüküm çıkarım anında verildi; soru sorulurken kaynak metin yeniden taranmadı. Canlı bir yeniden doğrulama değildir.
      </div>

      {/* 2) ALAN TABLOSU (audit.dogrulama VARSA) */}
      {hasDogrulama && (
        <Table
          size="small"
          dataSource={dogrulama.alanlar}
          rowKey="alan"
          columns={dogrulamaKolonlari}
          pagination={false}
          style={{ marginBottom: 12 }}
        />
      )}

      {/* 3) TEK KAYIT DURUMU (audit.dogrulama YOKSA ama audit.dogrulanan_alanlar VARSA) */}
      {!hasDogrulama && hasDogrulananAlanlar && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 12 }}>
          {Object.entries(dogrulananAlanlar).map(([key, val]) => {
            const isTrue = Boolean(val === true || val === "true" || val === "dogrulandi");
            const alanAdi = ALAN_ADLARI[key] || key;
            return (
              <div key={key} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
                {isTrue ? (
                  <>
                    <CheckOutlined style={{ color: "#169276", fontWeight: "bold" }} />
                    <span style={{ fontWeight: 500, color: "var(--yazi-koyu, #192b27)" }}>{alanAdi}</span>
                  </>
                ) : (
                  <>
                    <ExclamationOutlined style={{ color: "#d4a34b", fontWeight: "bold" }} />
                    <span style={{ fontWeight: 500, color: "var(--yazi-koyu, #192b27)" }}>{alanAdi}</span>
                    <span style={{ fontSize: 11, color: "var(--yazi-soluk, #7b8c86)" }}>kaynakta teyit edilemedi</span>
                  </>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* 4) İKİSİ DE YOKSA */}
      {!hasDogrulama && !hasDogrulananAlanlar && (
        <div style={{ color: "var(--yazi-soluk, #7b8c86)", fontSize: 13, padding: "8px 0", marginBottom: 12 }}>
          Bu yanıt için doğrulama bilgisi yok — çağrılan araç sayısal alan kullanmamış olabilir.
        </div>
      )}

      {/* 5) EN ALTTA AÇIKLAMA */}
      <div style={{ fontSize: 11, color: "var(--yazi-soluk, #7b8c86)", marginTop: 12, lineHeight: "1.4" }}>
        Doğrulanamayan değerler silinmez — Verifier'in bilinen sınırları vardır ve bir değeri kaynakta bulamaması onu yanlış yapmaz.
        <br />
        Çalıştırılmadı, o alan için doğrulama hiç yapılmadığı anlamına gelir.
      </div>
    </Card>
  );
}

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

      <KaynaktaDogrulamaBolumu sonAudit={sonAudit} />

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


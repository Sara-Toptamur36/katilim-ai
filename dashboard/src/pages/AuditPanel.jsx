import { useMemo } from "react";
import { Link } from "react-router-dom";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  List,
  Row,
  Space,
  Statistic,
  Steps,
  Table,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import {
  CalculatorOutlined,
  CheckOutlined,
  ClockCircleOutlined,
  ExclamationOutlined,
  InfoCircleOutlined,
  RobotOutlined,
  SwapOutlined,
} from "@ant-design/icons";
import { useAudit } from "../context/AuditContext";
import KopyalaButonu from "../components/KopyalaButonu";
import ModelVeriPanelleri from "../components/ModelVeriPanelleri";

const { Title, Text, Paragraph } = Typography;

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
function YigilmisCubuk({
  dogrulanan = 0,
  dogrulanamayan = 0,
  calistirilmamis = 0,
  kayitSayisi = 0,
}) {
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

// Kaynakta Doğrulama Ana Bölüm Bileşeni (KORUNDU)
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
          backgroundColor: "var(--uyari-zemin)",
          color: "var(--uyari-yazi)",
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
          backgroundColor: "var(--kart-ustu)",
          color: "var(--yazi-soluk)",
          fontSize: 12,
          fontWeight: 500,
        }}
      >
        <span>Verifier çalışmadı</span>
      </span>
    );
  }

  return (
    <Card size="small" className="audit-karti">
      {/* 1) BAŞLIK SATIRI */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
        <div style={{ fontSize: 16, fontWeight: 600, color: "var(--yazi-koyu, #192b27)" }}>
          Kaynakta Doğrulama (Fact-Checking)
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
  {
    title: "Zaman",
    dataIndex: "zaman",
    key: "zaman",
    render: (z) => (z ? new Date(z).toLocaleTimeString("tr-TR") : "—"),
  },
  { title: "Soru / İşlem", dataIndex: "soru", key: "soru", ellipsis: true },
  { title: "Niyet", dataIndex: "intent", key: "intent", render: (v) => v ?? "—" },
  { title: "Araç", dataIndex: "cagrilan_arac", key: "cagrilan_arac", render: (v) => v ?? "—" },
  { title: "Gecikme (ms)", dataIndex: "latency_ms", key: "latency_ms", render: (v) => v ?? "—" },
  {
    title: "Durum / Cache",
    dataIndex: "cache_hit",
    key: "cache_hit",
    render: (v, rec) => {
      if (rec.basarisiz) {
        return <Tag color="error">Başarısız</Tag>;
      }
      return <Tag color={v ? "green" : "default"}>{v ? "HIT" : "MISS"}</Tag>;
    },
  },
];

export default function AuditPanel() {
  const { sonAudit, auditGecmisi } = useAudit();

  // SORUN 5: Reranker skoru kontrolü - veride rerank_score alanı gerçekten varsa ayrı kolon ekle
  const varMiRerankSkoru = useMemo(() => {
    if (!sonAudit?.retriever_sonuclari) return false;
    return sonAudit.retriever_sonuclari.some((r) => r.rerank_score != null);
  }, [sonAudit]);

  const retrieverKolonlari = useMemo(() => {
    const kolonlar = [
      { title: "Chunk ID", dataIndex: "chunk_id", key: "chunk_id", render: (v) => v ?? "Belirtilmemiş" },
      {
        title: () => (
          <Tooltip title="Vektör arama benzerliği (0-1) — accuracy değil">
            <span>Vektör Benzerliği ⓘ</span>
          </Tooltip>
        ),
        dataIndex: "similarity_score",
        key: "similarity_score",
        render: (v) => (v != null ? v.toFixed(3) : "Belirtilmemiş"),
      },
    ];

    if (varMiRerankSkoru) {
      kolonlar.push({
        title: "Rerank Skoru",
        dataIndex: "rerank_score",
        key: "rerank_score",
        render: (v) => (v != null ? v.toFixed(3) : "Belirtilmemiş"),
      });
    }

    kolonlar.push({
      title: "Metin (kısa)",
      dataIndex: "metin_ozeti",
      key: "metin_ozeti",
      ellipsis: true,
      render: (v) => v ?? "Belirtilmemiş",
    });

    return kolonlar;
  }, [varMiRerankSkoru]);

  // SORUN 2: Boş Ekran Tanıtım Kılavuzu (Sahte veri üretilmez)
  if (!sonAudit) {
    return (
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <Title level={3} style={{ marginBottom: 4 }}>
          Jüri Audit Paneli
        </Title>
        <ModelVeriPanelleri />

        <Card className="audit-karti">
          <Space direction="vertical" size={16} style={{ width: "100%" }}>
            <div>
              <Title level={4} style={{ margin: 0 }}>
                Henüz denetlenecek sorgu yok
              </Title>
              <Paragraph
                type="secondary"
                style={{ marginTop: 8, fontSize: 14, lineHeight: 1.6 }}
              >
                Bu panel, sistemin bir soruya veya işleme nasıl cevap verdiğini adım
                adım gösterir. Bir işlem yapıldığında burada şunlar görünür:
              </Paragraph>
            </div>

            <div
              style={{
                background: "var(--zemin-yumusak)",
                padding: "16px 20px",
                borderRadius: 10,
                border: "1px solid var(--kenarlik)",
              }}
            >
              <List
                size="small"
                dataSource={[
                  "🎯 Algılanan Niyet (Intent) ve niyet güven skoru",
                  "🛠️ Çağrılan Araç (Tool) ve parametreleri",
                  "🔍 Çalıştırılan SQL Sorgusu ve veritabanı sonuçları",
                  "📊 Retriever Benzerlik Skorları ve vektör arama chunk'ları",
                  "🛡️ Güven Skorları (çıkarım ve yanıt güvenilirlikleri)",
                  "⏱️ Yanıt Süresi & Cache Durumu (milisaniye cinsinden gecikme)",
                  "✅ Kaynakta Doğrulama (Fact-Checking/Verifier) sonuçları",
                ]}
                renderItem={(item) => (
                  <List.Item
                    style={{ border: "none", padding: "4px 0", fontSize: 13 }}
                  >
                    {item}
                  </List.Item>
                )}
              />
            </div>

            <Space wrap size="middle" style={{ marginTop: 8 }}>
              <Link to="/chatbot">
                <Button type="primary" icon={<RobotOutlined />}>
                  AI Asistan'a git
                </Button>
              </Link>
              <Link to="/hesapla">
                <Button icon={<CalculatorOutlined />}>
                  Hesap Makinesi'ne git
                </Button>
              </Link>
              <Link to="/karsilastirma">
                <Button icon={<SwapOutlined />}>
                  Karşılaştırma'ya git
                </Button>
              </Link>
            </Space>
          </Space>
        </Card>
      </div>
    );
  }

  // SORUN 3: Düzen Şeridi & 2-Sütunlu Yapı
  return (
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
      <Title level={3} style={{ marginBottom: 4 }}>
        Jüri Audit Paneli
      </Title>
      <ModelVeriPanelleri />

      {/* ÜST ŞERİT: Soru metni + trace zamanı + çağrılan araç + yanıt süresi */}
      <div className="audit-ust-serit">
        <div style={{ flex: 1, minWidth: 260 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Sorgu / İşlem Detayı
          </Text>
          <div style={{ fontSize: 16, fontWeight: 600, color: "var(--yazi-koyu)" }}>
            {sonAudit.soru || sonAudit.sebep || "Denetim Kaydı"}
          </div>
          {sonAudit.zaman && (
            <Text type="secondary" style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 4, marginTop: 2 }}>
              <ClockCircleOutlined /> İzleme Zamanı: {new Date(sonAudit.zaman).toLocaleTimeString("tr-TR")}
            </Text>
          )}
        </div>

        <Space size="large" wrap align="center">
          {sonAudit.basarisiz && (
            <div>
              <Text type="secondary" style={{ fontSize: 11, display: "block" }}>
                Durum
              </Text>
              <Tag color="error" style={{ fontSize: 13, padding: "2px 8px", marginTop: 2 }}>
                Başarısız
              </Tag>
            </div>
          )}
          <div>
            <Text type="secondary" style={{ fontSize: 11, display: "block" }}>
              Çağrılan Araç
            </Text>
            <Tag color="purple" style={{ fontSize: 13, padding: "2px 8px", marginTop: 2 }}>
              {sonAudit.cagrilan_arac ?? "—"}
            </Tag>
          </div>

          <Statistic
            title={<Text type="secondary" style={{ fontSize: 11 }}>Toplam Yanıt Süresi</Text>}
            value={sonAudit.latency_ms ?? "—"}
            suffix={sonAudit.latency_ms != null ? "ms" : ""}
            valueStyle={{ color: "var(--marka-600)", fontWeight: 700, fontSize: 24 }}
          />
        </Space>
      </div>

      {sonAudit.hata && (
        <Alert
          type="error"
          message="İşlem Başarısız Oldu"
          description={sonAudit.hata}
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 2-SÜTUNLU DÜZEN: Solda Karar Zinciri (Steps), Sağda Skorlar & Parametreler */}
      <Row gutter={[20, 20]} style={{ marginBottom: 20 }}>
        {/* SOL SÜTUN: Karar Zinciri (antd Steps dikey) */}
        <Col xs={24} lg={10}>
          <Card title="Karar Zinciri Pipeline" className="audit-karti" style={{ height: "100%" }}>
            <Steps
              direction="vertical"
              size="small"
              current={4}
              items={[
                {
                  title: `Niyet: ${sonAudit.intent ?? "Belirtilmemiş"}`,
                  description: (
                    <Tooltip title="Niyet güven skoru — doğruluk oranı değil">
                      <span>
                        Niyet Güven Skoru ⓘ:{" "}
                        {sonAudit.intent_confidence != null
                          ? `${(sonAudit.intent_confidence * 100).toFixed(0)}%`
                          : "Belirtilmemiş"}
                      </span>
                    </Tooltip>
                  ),
                },
                {
                  title: `Araç: ${sonAudit.cagrilan_arac ?? "Belirtilmemiş"}`,
                  description: "Çalıştırılan handler motoru",
                },
                {
                  title: "Veri Erişimi (Retrieval)",
                  description: sonAudit.sql_sorgusu
                    ? "SQL Veritabanı Sorgusu Çalıştırıldı"
                    : `${sonAudit.retriever_sonuclari?.length ?? 0} Vektör Chunk'ı Bulundu`,
                },
                {
                  title: "Kaynakta Doğrulama",
                  description: `Durum: ${sonAudit.dogrulama?.durum ?? "Yapılmadı / N/A"}`,
                },
                {
                  title: "Yanıt Üretimi",
                  description: `Cache: ${sonAudit.cache_hit ? "HIT" : "MISS"} | Model: ${
                    sonAudit.model ?? "Standart"
                  }`,
                },
              ]}
            />
          </Card>
        </Col>

        {/* SAĞ SÜTUN: Bileşen Skorları + Model Parametreleri (SORUN 4 Tooltipler) */}
        <Col xs={24} lg={14}>
          <Card title="Bileşen Skorları & Model Parametreleri" className="audit-karti" style={{ height: "100%" }}>
            <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
              <Col span={12}>
                <div className="audit-istatistik-kutu">
                  <Statistic
                    title={
                      <Tooltip title="Çıkarım güven skoru — doğruluk oranı değil">
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          Çıkarım Güven Skoru ⓘ
                        </Text>
                      </Tooltip>
                    }
                    value={
                      sonAudit.extraction_confidence != null
                        ? (sonAudit.extraction_confidence * 100).toFixed(1)
                        : "—"
                    }
                    suffix={sonAudit.extraction_confidence != null ? "%" : ""}
                    valueStyle={{ fontSize: 20 }}
                  />
                </div>
              </Col>
              <Col span={12}>
                <div className="audit-istatistik-kutu">
                  <Statistic
                    title={
                      <Tooltip title="Yanıt güven skoru — doğruluk oranı değil">
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          Yanıt Güven Skoru ⓘ
                        </Text>
                      </Tooltip>
                    }
                    value={
                      sonAudit.response_confidence != null
                        ? (sonAudit.response_confidence * 100).toFixed(1)
                        : "—"
                    }
                    suffix={sonAudit.response_confidence != null ? "%" : ""}
                    valueStyle={{ fontSize: 20 }}
                  />
                </div>
              </Col>
            </Row>

            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="Niyet">
                {sonAudit.intent ?? "Belirtilmemiş"}
              </Descriptions.Item>
              <Descriptions.Item
                label={
                  <Tooltip title="Niyet güven skoru — doğruluk oranı değil">
                    <span>Niyet Güven Skoru ⓘ</span>
                  </Tooltip>
                }
              >
                {sonAudit.intent_confidence != null ? (
                  <Tag color="blue">{(sonAudit.intent_confidence * 100).toFixed(0)}%</Tag>
                ) : (
                  "Belirtilmemiş"
                )}
              </Descriptions.Item>
              <Descriptions.Item label="Model">{sonAudit.model ?? "Belirtilmemiş"}</Descriptions.Item>
              <Descriptions.Item label="Temperature">
                {sonAudit.temperature ?? "Belirtilmemiş"}
              </Descriptions.Item>
              <Descriptions.Item label="Cache Durumu">
                <Tag color={sonAudit.cache_hit ? "green" : "default"}>
                  {sonAudit.cache_hit ? "HIT" : "MISS"}
                </Tag>
              </Descriptions.Item>
              {sonAudit.regex_basari_orani != null && (
                <Descriptions.Item label="Regex/Model Başarı">
                  {(sonAudit.regex_basari_orani * 100).toFixed(1)}%
                </Descriptions.Item>
              )}
              {sonAudit.sebep && (
                <Descriptions.Item label="Açıklama / Sebep" span={2}>
                  {sonAudit.sebep}
                </Descriptions.Item>
              )}
            </Descriptions>
          </Card>
        </Col>
      </Row>

      {/* ALT TAM GENİŞLİK 1: Çalıştırılan SQL (KopyalaButonu ile) */}
      {sonAudit.sql_sorgusu && (
        <Card
          title="Çalıştırılan SQL Sorgusu"
          size="small"
          className="audit-karti"
          extra={<KopyalaButonu metin={sonAudit.sql_sorgusu} />}
        >
          <pre
            style={{
              background: "var(--zemin-yumusak)",
              color: "var(--yazi-koyu)",
              padding: 12,
              borderRadius: 8,
              overflow: "auto",
              margin: 0,
              fontSize: 13,
            }}
          >
            {sonAudit.sql_sorgusu}
          </pre>
        </Card>
      )}

      {/* ALT TAM GENİŞLİK 2: Kaynakta Doğrulama Bölümü (Korundu) */}
      <KaynaktaDogrulamaBolumu sonAudit={sonAudit} />

      {/* ALT TAM GENİŞLİK 3: Retriever Sonuçları Tablosu */}
      {sonAudit.retriever_sonuclari && sonAudit.retriever_sonuclari.length > 0 && (
        <Card title="Retriever Sonuçları" className="audit-karti">
          <Table
            size="small"
            dataSource={sonAudit.retriever_sonuclari}
            rowKey="chunk_id"
            columns={retrieverKolonlari}
            pagination={false}
          />
        </Card>
      )}

      {/* EN ALT: Sorgu Geçmişi Tablosu (Korundu) */}
      <Card title="Sorgu Geçmişi (Son 20 İşlem)" className="audit-karti">
        <Table
          size="small"
          dataSource={auditGecmisi}
          rowKey={(rec, idx) => rec.zaman || idx}
          columns={gecmisKolonlari}
          pagination={false}
          scroll={{ x: "max-content" }}
        />
      </Card>
    </div>
  );
}



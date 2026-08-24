import { useEffect, useState } from "react";
import {
  Alert,
  Card,
  Descriptions,
  Empty,
  InputNumber,
  Progress,
  Skeleton,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
  Button,
} from "antd";
import {
  AuditOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  MinusCircleOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import { extractionAuditGetir, kampanyalariGetir } from "../api/client";

/**
 * ExtractionAudit — Jüri "hangi katman ne değer verdi?" sorusunun ekranı.
 *
 * Bir kampanya seçilince GET /audit/extraction/{id} çağrılır.
 * Her alan için: mevcut değer, çıkarım katmanı, güven, gold reference,
 * doğrulandı mı?
 *
 * ROL KISITI: Bu sayfa yalnızca banka_calisani / denetleyici / yonetici
 * rolüne gösterilmeli (menü kısıtı App.jsx'te yapılıyor).
 */

const KATMAN_RENK = {
  regex:   { renk: "blue",    etiket: "🔵 Regex"   },
  gliner:  { renk: "purple",  etiket: "🟣 GLiNER"  },
  qwen:    { renk: "orange",  etiket: "🟠 Qwen"    },
  hibrit:  { renk: "green",   etiket: "🟢 Hibrit"  },
  sozluk:  { renk: "cyan",    etiket: "🩵 Sözlük"  },
};

function katmanTag(katman) {
  const m = KATMAN_RENK[katman?.toLowerCase()] ?? { renk: "default", etiket: katman ?? "—" };
  return <Tag color={m.renk}>{m.etiket}</Tag>;
}

function DogrulamaIkon({ dogrulandi }) {
  if (dogrulandi === true)
    return <CheckCircleOutlined style={{ color: "#52c41a" }} title="Doğrulandı" />;
  if (dogrulandi === false)
    return <CloseCircleOutlined style={{ color: "#ff4d4f" }} title="Doğrulanamadı" />;
  return <MinusCircleOutlined style={{ color: "#8c8c8c" }} title="Doğrulama yapılmadı" />;
}

// Alan tablosu sütunları
const ALANLAR_SUTUNLAR = [
  {
    title: "Alan",
    key: "label",
    width: 180,
    render: (_, r) => (
      <span>
        <strong>{r.label}</strong>
        {r.birim && <Typography.Text type="secondary" style={{ fontSize: 11 }}> ({r.birim})</Typography.Text>}
      </span>
    ),
  },
  {
    title: "Mevcut Değer",
    key: "mevcut_deger",
    width: 130,
    render: (_, r) => {
      if (r.belirtilmemis)
        return (
          <Tooltip title="Kaynak metinde belirtilmemiş — gizlenmez, işaretlenir">
            <Tag color="default">Belirtilmemiş</Tag>
          </Tooltip>
        );
      if (r.mevcut_deger == null) return <Tag color="default">—</Tag>;
      return (
        <Tag color="geekblue">
          {r.mevcut_deger}
          {r.birim ? ` ${r.birim}` : ""}
        </Tag>
      );
    },
  },
  {
    title: "Çıkarım Katmanı",
    key: "katman",
    width: 130,
    render: (_, r) => {
      const katman = r.katmanlar?.[0]?.katman;
      return katmanTag(katman);
    },
  },
  {
    title: "Güven",
    key: "confidence",
    width: 110,
    render: (_, r) => {
      const conf = r.katmanlar?.[0]?.confidence;
      if (conf == null) return <Typography.Text type="secondary">—</Typography.Text>;
      const yuzde = Math.round(conf * 100);
      return (
        <Tooltip title="Çıkarım güven skoru — doğruluk değil, eşleşme skoru">
          <Progress
            percent={yuzde}
            size="small"
            status={yuzde >= 80 ? "success" : yuzde >= 50 ? "normal" : "exception"}
            style={{ width: 80 }}
            format={(p) => `%${p}`}
          />
        </Tooltip>
      );
    },
  },
  {
    title: "Gold Ref.",
    key: "gold",
    width: 110,
    render: (_, r) => {
      if (!r.gold_reference) return <Typography.Text type="secondary">—</Typography.Text>;
      return (
        <Tooltip title={`Gold değer: ${r.gold_reference.deger ?? "—"}`}>
          <Tag color={r.gold_reference.dogrulandi ? "green" : "red"}>
            {r.gold_reference.deger ?? "—"}
          </Tag>
        </Tooltip>
      );
    },
  },
  {
    title: "Doğ.",
    key: "dogrulandi",
    width: 60,
    align: "center",
    render: (_, r) => <DogrulamaIkon dogrulandi={r.dogrulandi} />,
  },
  {
    title: "Evidence",
    key: "evidence",
    ellipsis: true,
    render: (_, r) => {
      const ev = r.katmanlar?.[0]?.evidence;
      if (!ev) return <Typography.Text type="secondary">Ham metin bu görünümde yok</Typography.Text>;
      return (
        <Typography.Text italic style={{ fontSize: 11 }}>"{ev}"</Typography.Text>
      );
    },
  },
];

export default function ExtractionAudit() {
  const [kampanyaId, setKampanyaId] = useState(null);
  const [veri, setVeri] = useState(null);
  const [yukleniyor, setYukleniyor] = useState(false);
  const [hata, setHata] = useState(null);

  const getir = (id) => {
    if (!id) return;
    setYukleniyor(true);
    setHata(null);
    setVeri(null);
    extractionAuditGetir(id)
      .then(setVeri)
      .catch((e) => setHata(e?.response?.data?.detail ?? e.message))
      .finally(() => setYukleniyor(false));
  };

  return (
    <div style={{ padding: "0 4px" }}>
      {/* Başlık */}
      <div style={{ marginBottom: 20 }}>
        <Typography.Title level={4} style={{ marginBottom: 4 }}>
          <AuditOutlined style={{ marginRight: 8 }} />
          Çıkarım Denetimi (Extraction Audit)
        </Typography.Title>
        <Typography.Text type="secondary">
          Bir kampanya için Regex → GLiNER → Qwen → Resolver katman izlerini gösterir.
          Hangi model hangi değeri çıkardı? Doğrulama sonucu ne?
        </Typography.Text>
      </div>

      {/* Rol uyarısı */}
      <Alert
        type="info"
        showIcon
        message="Bu ekran yalnızca yetkili roller için — banka çalışanı, denetleyici, yönetici."
        style={{ marginBottom: 16 }}
      />

      {/* Kampanya ID girişi */}
      <Space style={{ marginBottom: 20 }}>
        <InputNumber
          placeholder="Kampanya ID girin (ör. 1)"
          min={1}
          value={kampanyaId}
          onChange={setKampanyaId}
          style={{ width: 200 }}
          onPressEnter={() => getir(kampanyaId)}
        />
        <Button
          type="primary"
          icon={<SearchOutlined />}
          onClick={() => getir(kampanyaId)}
          disabled={!kampanyaId || yukleniyor}
          loading={yukleniyor}
        >
          Getir
        </Button>
      </Space>

      {/* Hata */}
      {hata && (
        <Alert
          type="error"
          message="Hata"
          description={hata}
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Yükleniyor */}
      {yukleniyor && <Skeleton active paragraph={{ rows: 6 }} />}

      {/* Kampanya özeti */}
      {veri && !yukleniyor && (
        <>
          <Card
            size="small"
            style={{ marginBottom: 16 }}
            title={
              <span>
                <AuditOutlined style={{ marginRight: 8 }} />
                {veri.banka} — {veri.kampanya_adi}
                {veri.genel_guven != null && (
                  <Tag color="blue" style={{ marginLeft: 8 }}>
                    Genel güven: %{Math.round(veri.genel_guven * 100)}
                  </Tag>
                )}
              </span>
            }
          >
            <Descriptions size="small" column={2}>
              <Descriptions.Item label="Kampanya ID">
                {veri.kampanya_id}
              </Descriptions.Item>
              <Descriptions.Item label="Çıkarım yöntemi">
                {katmanTag(veri.cikarim_yontemi)}
              </Descriptions.Item>
              <Descriptions.Item label="Kaynak URL" span={2}>
                {veri.kaynak_url ? (
                  <Typography.Link href={veri.kaynak_url} target="_blank" rel="noopener noreferrer">
                    {veri.kaynak_url}
                  </Typography.Link>
                ) : (
                  <Typography.Text type="secondary">—</Typography.Text>
                )}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          {/* Alan tablosu */}
          <Alert
            type="info"
            showIcon
            message="Ham metin bu görünümde mevcut değil"
            description={
              <>
                Bu görünüm DB'deki mevcut çıkarım sonuçlarını gösterir. Ham kaynak metinden
                canlı çıkarım için <strong>POST /cikar</strong> endpoint'ini kullanın (hibrit=false).
                Evidence sütunu ham metin taranmadığında boş kalır — sistem uydurmaz.
              </>
            }
            style={{ marginBottom: 12 }}
          />

          <Table
            dataSource={veri.alanlar}
            columns={ALANLAR_SUTUNLAR}
            rowKey="alan"
            size="small"
            pagination={false}
            scroll={{ x: "max-content" }}
          />

          {/* Açıklama */}
          <div style={{ marginTop: 16, padding: "8px 12px", background: "#f5f5f5", borderRadius: 6 }}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              <strong>Simge açıklaması:</strong>{" "}
              <CheckCircleOutlined style={{ color: "#52c41a" }} /> Doğrulandı &nbsp;·&nbsp;
              <CloseCircleOutlined style={{ color: "#ff4d4f" }} /> Doğrulanamadı &nbsp;·&nbsp;
              <MinusCircleOutlined style={{ color: "#8c8c8c" }} /> Doğrulama yapılmadı (alan yok/eski kayıt)
              &nbsp;·&nbsp; <strong>Gold Ref.</strong>: gold_dataset/gold_records.json referansı (yoksa —)
            </Typography.Text>
          </div>
        </>
      )}

      {/* Boş durum */}
      {!veri && !yukleniyor && !hata && (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="Yukarıya bir kampanya ID girerek çıkarım izlerini görüntüleyin."
        />
      )}
    </div>
  );
}

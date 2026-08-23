import { useEffect, useRef, useState } from "react";
import {
  Button,
  Card,
  Collapse,
  Input,
  Space,
  Spin,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import {
  ClearOutlined,
  InfoCircleOutlined,
  RobotOutlined,
  SendOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { chatGonder } from "../api/client";
import ChatMesaji from "../components/ChatMesaji";
import { useAudit } from "../context/AuditContext";

const { Title, Text } = Typography;

/* Kalici sohbet gecmisi — sessionStorage yerine localStorage:
   sayfa yenilendiginde ya da baska sekmeden donuldugunde gecmis kaybolmaz.
   Backend'in yanit uretemediginde (fallback) mesajlar kayit disi birakilmaz;
   kullanici gecmisini gormek isteyebilir. */
const DEPO_ANAHTARI = "katilimai-chat-gecmisi";

function gecmisiYukle() {
  try {
    const ham = localStorage.getItem(DEPO_ANAHTARI);
    return ham ? JSON.parse(ham) : [];
  } catch {
    return [];
  }
}

const ORNEK_SORULAR = [
  "Kuveyt Türk ile Türkiye Finans kâr payı oranını karşılaştır",
  "Kâr payı oranı ne demek?",
  "Ziraat Katılım kart kampanyalarında taksit var mı?",
  "500.000 TL için Kuveyt Türk ile Ziraat Katılım toplam maliyetini karşılaştır",
];

const ARAC_RENKLERI = {
  rag: "blue",
  sql: "purple",
  calculator: "green",
  dictionary: "orange",
  fallback: "default",
};

export default function Chatbot() {
  const [mesajlar, setMesajlar] = useState(gecmisiYukle);
  const [girdi, setGirdi] = useState("");
  const [bekleniyor, setBekleniyor] = useState(false);
  const [auditAcik, setAuditAcik] = useState(false);
  const { auditEkle } = useAudit();
  const mesajListesiRef = useRef(null);
  const girdiBileseniRef = useRef(null);

  /* Yeni mesaj geldiginde otomatik asagi kaydir */
  useEffect(() => {
    if (mesajListesiRef.current) {
      mesajListesiRef.current.scrollTop = mesajListesiRef.current.scrollHeight;
    }
  }, [mesajlar, bekleniyor]);

  /* localStorage'a yaz */
  useEffect(() => {
    try {
      localStorage.setItem(DEPO_ANAHTARI, JSON.stringify(mesajlar));
    } catch {
      /* Depolama dolu - sessizce gec */
    }
  }, [mesajlar]);

  const sohbetiTemizle = () => {
    setMesajlar([]);
    localStorage.removeItem(DEPO_ANAHTARI);
    girdiBileseniRef.current?.focus();
  };

  const gonder = async (metin) => {
    const soru = (metin ?? girdi).trim();
    if (!soru || bekleniyor) return;

    setMesajlar((o) => [...o, { rol: "kullanici", metin: soru }]);
    setGirdi("");
    setBekleniyor(true);

    try {
      const yanit = await chatGonder(soru);
      setMesajlar((o) => [
        ...o,
        {
          rol: "bot",
          metin: yanit.cevap,
          kaynaklar: yanit.kaynaklar,
          confidence: yanit.confidence,
          fallback: yanit.fallback,
          terminolojiTutarli: yanit.audit?.terminoloji_tutarli ?? null,
          terminolojiSorunlari: yanit.audit?.terminoloji_sorunlari ?? [],
          cagrilanArac: yanit.audit?.cagrilan_arac,
          /* Audit detay toggle icin ham audit blogunu sakla */
          auditHam: yanit.audit,
        },
      ]);
      auditEkle(yanit.audit, soru);
    } catch {
      setMesajlar((o) => [
        ...o,
        {
          rol: "bot",
          metin: "Uzgunüm, su anda yanit veremiyorum. Lutfen tekrar deneyin.",
          hata: true,
        },
      ]);
    } finally {
      setBekleniyor(false);
      girdiBileseniRef.current?.focus();
    }
  };

  const klavyeBasildi = (e) => {
    /* Shift+Enter -> yeni satir; sadece Enter -> gonder */
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      gonder();
    }
  };

  const bos = mesajlar.length === 0;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 140px)",
        minHeight: 460,
        gap: 0,
      }}
    >
      {/* Baslik + kontroller */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          paddingBottom: 12,
          flexShrink: 0,
        }}
      >
        <Title level={3} style={{ margin: 0 }}>
          <RobotOutlined style={{ marginRight: 8, color: "#1677ff" }} />
          AI Asistan
        </Title>
        <Space>
          <Tooltip title="Audit detaylarini goster / gizle">
            <Button
              icon={<InfoCircleOutlined />}
              onClick={() => setAuditAcik((a) => !a)}
              type={auditAcik ? "primary" : "default"}
              size="small"
            >
              Audit
            </Button>
          </Tooltip>
          <Tooltip title="Sohbet gecmisini temizle">
            <Button
              icon={<ClearOutlined />}
              onClick={sohbetiTemizle}
              size="small"
              disabled={bos}
              danger
            >
              Temizle
            </Button>
          </Tooltip>
        </Space>
      </div>

      {/* Mesaj listesi */}
      <Card
        ref={mesajListesiRef}
        styles={{ body: { padding: 16, height: "100%", overflowY: "auto" } }}
        style={{ flex: 1, minHeight: 0, overflowY: "auto" }}
      >
        {bos ? (
          /* Bos durum - ornek sorular */
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              gap: 20,
              opacity: 0.85,
            }}
          >
            <RobotOutlined style={{ fontSize: 48, color: "#1677ff" }} />
            <Title level={4} style={{ margin: 0 }}>
              Merhaba! Kampanyalar hakkinda sorularinizi yanitliyorum.
            </Title>
            <Text type="secondary" style={{ textAlign: "center", maxWidth: 480 }}>
              Kar payi oranlarini karsilastirir, taksit hesabi yapabilir,
              terminoloji sozlugune danisabilir veya kampanya hakkinda serbest
              soru sorabilirsiniz.
            </Text>
            <Space wrap style={{ justifyContent: "center" }}>
              {ORNEK_SORULAR.map((s, i) => (
                <Button
                  key={i}
                  size="small"
                  onClick={() => gonder(s)}
                  disabled={bekleniyor}
                  style={{ maxWidth: 320, whiteSpace: "normal", height: "auto", padding: "4px 8px" }}
                >
                  {s}
                </Button>
              ))}
            </Space>
          </div>
        ) : (
          <>
            {mesajlar.map((m, i) => (
              <div key={i} style={{ marginBottom: 16 }}>
                {/* Mesaj baloncugu */}
                <div
                  style={{
                    display: "flex",
                    flexDirection: m.rol === "kullanici" ? "row-reverse" : "row",
                    alignItems: "flex-start",
                    gap: 8,
                  }}
                >
                  <div
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: "50%",
                      background: m.rol === "kullanici" ? "#1677ff" : "#52c41a",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                  >
                    {m.rol === "kullanici" ? (
                      <UserOutlined style={{ color: "#fff", fontSize: 14 }} />
                    ) : (
                      <RobotOutlined style={{ color: "#fff", fontSize: 14 }} />
                    )}
                  </div>
                  <div
                    style={{
                      maxWidth: "80%",
                      background: m.rol === "kullanici" ? "#1677ff" : "rgba(0,0,0,0.04)",
                      borderRadius: 12,
                      padding: "8px 14px",
                    }}
                  >
                    <Text
                      style={{
                        color: m.rol === "kullanici" ? "#fff" : "inherit",
                        whiteSpace: "pre-wrap",
                      }}
                    >
                      {m.metin}
                    </Text>
                    {m.streaming && <span style={{ opacity: 0.6 }}>▍</span>}
                  </div>
                </div>

                {/* Arac etiketi */}
                {m.cagrilanArac && (
                  <div style={{ marginLeft: 40, marginTop: 4 }}>
                    <Tag color={ARAC_RENKLERI[m.cagrilanArac] ?? "default"}>
                      {m.cagrilanArac}
                    </Tag>
                  </div>
                )}

                {/* ChatMesaji: kaynak, terminoloji, fallback bilgileri */}
                {m.rol === "bot" && (
                  <div style={{ marginLeft: 40, marginTop: 4 }}>
                    <ChatMesaji mesaj={{ ...m, metin: "" }} />
                  </div>
                )}

                {/* Audit detay blogu (toggle ile) */}
                {auditAcik && m.auditHam && (
                  <div style={{ marginLeft: 40, marginTop: 4 }}>
                    <Collapse
                      size="small"
                      items={[
                        {
                          key: "audit",
                          label: (
                            <Space>
                              <InfoCircleOutlined />
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                Audit — niyet: {m.auditHam.intent} | gecikme:{" "}
                                {m.auditHam.latency_ms} ms
                              </Text>
                            </Space>
                          ),
                          children: (
                            <div style={{ fontSize: 13, background: "#fafafa", padding: "8px 12px", borderRadius: 6, border: "1px dashed #d9d9d9" }}>
                              <Text type="secondary">
                                📊 Bu sorguya ait detaylı <strong>Model Adayları</strong>, <strong>RAG Benzerlik Skorları</strong> ve <strong>Çıkarım Çatışmaları (Conflict Resolution)</strong> gibi bilgileri sol menüdeki <strong>Jüri Audit Paneli</strong> sekmesinden inceleyebilirsiniz.
                              </Text>
                            </div>
                          ),
                        },
                      ]}
                    />
                  </div>
                )}
              </div>
            ))}

            {bekleniyor && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  marginLeft: 40,
                }}
              >
                <Spin size="small" />
                <Text type="secondary">Yanit hazirlaniyor…</Text>
              </div>
            )}
          </>
        )}
      </Card>

      {/* Girdi alani */}
      <div
        style={{
          paddingTop: 12,
          flexShrink: 0,
          display: "flex",
          gap: 8,
        }}
      >
        <Input.TextArea
          ref={girdiBileseniRef}
          value={girdi}
          onChange={(e) => setGirdi(e.target.value)}
          onKeyDown={klavyeBasildi}
          placeholder="Örn: Kuveyt Türk kar payi orani ne? (Enter gonder, Shift+Enter yeni satir)"
          disabled={bekleniyor}
          autoSize={{ minRows: 1, maxRows: 4 }}
          style={{ flex: 1 }}
        />
        <Tooltip title="Gonder (Enter)">
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={() => gonder()}
            loading={bekleniyor}
            disabled={!girdi.trim()}
            style={{ height: "auto", alignSelf: "flex-end" }}
          >
            Gonder
          </Button>
        </Tooltip>
      </div>
    </div>
  );
}

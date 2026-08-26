import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Alert,
  Card,
  Col,
  Descriptions,
  Empty,
  Progress,
  Row,
  Select,
  Skeleton,
  Space,
  Statistic,
  Table,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import {
  AuditOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  MinusCircleOutlined,
  SafetyOutlined,
} from "@ant-design/icons";
import { extractionAuditGetir, kampanyalariGetir } from "../api/client";
import { OLCUMLER, OLCUM_TARIHI } from "../data/olcumler";

/**
 * ExtractionAudit — Jüri "hangi katman ne değer verdi?" sorusunun ekranı.
 *
 * Bir kampanya seçilince GET /audit/extraction/{id} çağrılır.
 * Her alan için: mevcut değer, çıkarım katmanı, güven, gold reference,
 * doğrulandı mı?
 *
 * DENETIM BULGUSU (26.08.2026): eskiden menude yalnizca banka_calisani/
 * denetleyici/yonetici rolune gosteriliyordu; jüri kendi (musteri) hesabiyla
 * bu sayfayi goremiyordu. Sartname Md. 6 geregi jurinin canli cikarim
 * denetimini arayuzden yapabilmesi icin App.jsx::GUVEN_MENUSU'ndeki rol
 * kisiti kaldirildi - tum giris yapmis kullanicilara acik.
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

// Kampanyanın veritabanındaki 5 temel finansal alandan kaç tanesinin dolu olduğunu sayar
function doluAlanSayisiHesapla(k) {
  let sayi = 0;
  if (k.kar_payi_orani_percent != null) sayi++;
  if (k.vade_ay != null) sayi++;
  if (k.taksit_sayisi != null) sayi++;
  if (k.finansman_tutari != null) sayi++;
  if (k.odul_miktari != null) sayi++;
  return sayi;
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
  const [kampanyalar, setKampanyalar] = useState([]);
  const [listeYukleniyor, setListeYukleniyor] = useState(true);
  const [secilenId, setSecilenId] = useState(null);
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

  // Kampanyaları API'den çekip veri zenginliğine göre sıralama ve ilk zengin kampanyayı yükleme
  useEffect(() => {
    setListeYukleniyor(true);
    kampanyalariGetir()
      .then((liste) => {
        const sirali = [...liste].sort((a, b) => {
          const aDolu = doluAlanSayisiHesapla(a);
          const bDolu = doluAlanSayisiHesapla(b);
          return bDolu - aDolu;
        });
        setKampanyalar(sirali);

        // İlk açılışta en çok alanı dolu olan kampanyayı otomatik seç ve detayını yükle
        if (sirali.length > 0) {
          const ilkId = sirali[0].id;
          setSecilenId(ilkId);
          getir(ilkId);
        }
      })
      .catch((e) => {
        setHata("Kampanya listesi yüklenemedi: " + (e?.message || "Bağlantı hatası"));
      })
      .finally(() => {
        setListeYukleniyor(false);
      });
  }, []);

  const kampanyaDegisti = (id) => {
    setSecilenId(id);
    getir(id);
  };

  // Antd Select seçeneklerinin hazırlanması
  const secenekler = useMemo(() => {
    return kampanyalar.map((k) => {
      const doluSayisi = doluAlanSayisiHesapla(k);
      return {
        value: k.id,
        searchValue: `${k.banka} ${k.kampanya_adi} ${k.id}`,
        label: (
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {k.banka} — {k.kampanya_adi}
            </span>
            <Tag
              color={doluSayisi > 0 ? "blue" : "default"}
              style={{ marginLeft: 8, fontSize: 10, flexShrink: 0 }}
            >
              {doluSayisi > 0 ? `${doluSayisi} alan dolu` : "alan yok"}
            </Tag>
          </div>
        ),
      };
    });
  }, [kampanyalar]);

  // Çıkarılmış dolu finansal alan var mı kontrolü
  const doluAlanMevcutMu = useMemo(() => {
    if (!veri || !Array.isArray(veri.alanlar)) return false;
    return veri.alanlar.some((a) => !a.belirtilmemis && a.mevcut_deger != null);
  }, [veri]);

  return (
    <div style={{ padding: "0 4px" }}>
      {/* Başlık ve Yumuşatılmış Rol Rozeti */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: 4 }}>
          <Typography.Title level={4} style={{ margin: 0 }}>
            <AuditOutlined style={{ marginRight: 8 }} />
            Çıkarım Denetimi (Extraction Audit)
          </Typography.Title>
          <Tag color="blue" icon={<SafetyOutlined />}>
            Denetim Ekranı — Jüri Erişimine Açık
          </Tag>
        </div>
        <Typography.Text type="secondary">
          Bir kampanya için Regex → GLiNER → Qwen → Resolver katman izlerini gösterir.
          Hangi model hangi değeri çıkardı? Doğrulama sonucu ne?
        </Typography.Text>
      </div>

      {/* Toplu ölçüm özeti - bu sayfadaki kayıt bazlı kanıtın TOPLAM sayısı.
          Aynı sayılar Jüri Audit Paneli'ndeki Model Metrikleri panelinde de
          var; buradaki fark, o panelin aggregate sayı verirken bu sayfanın
          o sayının ARKASINDAKİ kayıt/alan bazlı kanıtı göstermesi - ikisi
          artık aynı sayfa ailesinde, birbirine referans veriyor. */}
      <Card size="small" style={{ marginBottom: 20, background: "var(--zemin-yumusak)" }}>
        <Row gutter={24} align="middle">
          <Col xs={24} sm={8}>
            <Statistic
              title="Dolu Alan Doğruluğu"
              value={OLCUMLER.cikarim.doluAlanDogrulugu}
              suffix="%"
              valueStyle={{ fontSize: 20 }}
            />
          </Col>
          <Col xs={24} sm={8}>
            <Statistic
              title="Boş Alan Doğruluğu"
              value={OLCUMLER.cikarim.bosAlanDogrulugu}
              suffix="%"
              valueStyle={{ fontSize: 20 }}
            />
          </Col>
          <Col xs={24} sm={8}>
            <Statistic
              title="Makro F1"
              value={OLCUMLER.cikarim.makroF1}
              suffix="%"
              valueStyle={{ fontSize: 20 }}
            />
          </Col>
        </Row>
        <Typography.Text type="secondary" style={{ fontSize: 11, display: "block", marginTop: 10 }}>
          Toplam ölçüm ({OLCUM_TARIHI} tarihli, {OLCUMLER.cikarim.makroF1Detay}) — alan bazlı kırılım, tam
          metodoloji ve RAG/Scope Guard ölçümleri için{" "}
          <Link to="/audit">Jüri Audit Paneli → Model Metrikleri</Link>.
        </Typography.Text>
        {/* Asagidaki zincir (Regex -> GLiNER -> Qwen -> Resolver) sistemin
            TASARIMIDIR; olculen kosuda NER devre disiydi. Ikisi karistirilmasin
            diye olcum serigi burada acikca belirtilir. */}
        <Typography.Text type="secondary" style={{ fontSize: 11, display: "block", marginTop: 6 }}>
          {OLCUMLER.cikarim.nerDurumu}
        </Typography.Text>
      </Card>

      {/* Kampanya Seçici Dropdown */}
      <div style={{ marginBottom: 20 }}>
        <Space direction="vertical" style={{ width: "100%", maxWidth: 650 }}>
          <Typography.Text type="secondary" style={{ fontSize: 12, fontWeight: 500 }}>
            Kampanya Seçimi (Veri zenginliğine göre sıralanmıştır)
          </Typography.Text>
          <Select
            showSearch
            style={{ width: "100%" }}
            placeholder="Kampanya seçin…"
            value={secilenId}
            onChange={kampanyaDegisti}
            loading={listeYukleniyor}
            optionFilterProp="searchValue"
            options={secenekler}
          />
        </Space>
      </div>

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

      {/* Yükleniyor durumu */}
      {(yukleniyor || listeYukleniyor) && !veri && (
        <Skeleton active paragraph={{ rows: 6 }} />
      )}

      {/* Kampanya özeti ve alan tablosu */}
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

          {/* Çıkarılabilir alan yoksa açıklayıcı uyarı; varsa tablo */}
          {!doluAlanMevcutMu ? (
            <Alert
              type="warning"
              showIcon
              message="Çıkarılabilir Finansal Alan Bulunamadı"
              description="Bu kampanyada çıkarılabilir finansal alan bulunamadı — kaynak metin bu bilgileri içermiyor. Sistem olmayan veriyi uydurmaz."
              style={{ marginBottom: 16 }}
            />
          ) : (
            <>
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
            </>
          )}

          {/* Açıklama Dipnotu (Koyu tema uyumlu var(--kart-ustu) kullanır) */}
          <div style={{ marginTop: 16, padding: "8px 12px", background: "var(--kart-ustu)", borderRadius: 6 }}>
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

      {/* Tamamen veri yoksa boş durum */}
      {!veri && !yukleniyor && !listeYukleniyor && !hata && (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="Lütfen yukarıdaki menüden bir kampanya seçin."
        />
      )}
    </div>
  );
}

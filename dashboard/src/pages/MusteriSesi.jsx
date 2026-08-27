import { useEffect, useState } from "react";
import { Alert, Card, Col, Row, Space, Statistic, Table, Tag, Typography } from "antd";
import { musteriSesiOrnekleriGetir, musteriSesiYogunlukGetir } from "../api/client";

const { Title, Text, Paragraph } = Typography;

/**
 * MusteriSesi — Complaint Insight (şikâyet hattı) demo ve durum ekranı.
 *
 * NEDEN VAR: ADR 0001 ve VeriKaynagiRozeti.jsx'in kendi yorumu bu sayfaya
 * atıf yapıyordu ("MusteriSesi'nde SENTETİK/Gerçek veri metni görünür")
 * ama sayfa depoda hiç yoktu - backend (GET /musteri-sesi/ornekler, GET
 * /musteri-sesi/yogunluk-ozeti) hazırdı, UI eksikti. Bu doküman/kod
 * tutarsızlığını kapatır (27 Ağustos 2026).
 *
 * İKİ AYRI VERİ KAYNAĞI, HİÇ KARIŞTIRILMAZ:
 *   1. Örnekler (GET /musteri-sesi/ornekler) — SENTETİK, elle yazılmış,
 *      hiçbir gerçek bankaya atfedilmeyen demo veri. `sentetik: true`
 *      backend'den gelir, burada yeniden hesaplanmaz.
 *   2. Yoğunluk özeti (GET /musteri-sesi/yogunluk-ozeti) — GERÇEK
 *      `sikayetler` tablosunu okur. İzin kapısı (complaint/izin_kapisi.py)
 *      hiçbir kaynak için açılmadığından bu her zaman `toplam_sikayet: 0`
 *      ve `kapsam_durumu: "izin_yok"` döner - bu bir hata DEĞİL, doğru
 *      boş durumdur ve sayfa bunu OLDUĞU GİBİ gösterir.
 */

const ONEM_RENK = { YUKSEK: "red", ORTA: "gold", DUSUK: "default" };
const COZUM_RENK = {
  cozuldu: "green",
  kismen: "gold",
  cozulmedi: "red",
  bilinmiyor: "default",
};
const KAPSAM_DURUMU_METIN = {
  izin_yok: {
    renk: "default",
    baslik: "İzin yok",
    aciklama:
      "Hiçbir kaynak için geçerli bir izin kaydı yok - veri toplanması henüz başlamadı (bkz. complaint/izin_kapisi.py).",
  },
  izin_var_veri_yok: {
    renk: "gold",
    baslik: "İzin var, veri yok",
    aciklama: "En az bir kaynak için izin var ama henüz hiç şikâyet işlenmedi.",
  },
  veri_var: {
    renk: "green",
    baslik: "Veri var",
    aciklama: "En az bir şikâyet işlenmiş/kaydedilmiştir.",
  },
};

export default function MusteriSesi() {
  const [ornekVeri, setOrnekVeri] = useState(null);
  const [yogunlukVeri, setYogunlukVeri] = useState(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(null);

  useEffect(() => {
    setYukleniyor(true);
    setHata(null);
    Promise.all([musteriSesiOrnekleriGetir(), musteriSesiYogunlukGetir()])
      .then(([ornekler, yogunluk]) => {
        setOrnekVeri(ornekler);
        setYogunlukVeri(yogunluk);
      })
      .catch((e) => setHata(e.message))
      .finally(() => setYukleniyor(false));
  }, []);

  const sutunlar = [
    { title: "ID", dataIndex: "id", width: 70 },
    { title: "Metin (PII maskeli)", dataIndex: "metin" },
    {
      title: "Tema",
      dataIndex: "tema",
      width: 190,
      render: (v) => (v ? <Tag>{v}</Tag> : <Text type="secondary">—</Text>),
    },
    {
      title: "Önem",
      dataIndex: "onem_derecesi",
      width: 90,
      render: (v) => <Tag color={ONEM_RENK[v] ?? "default"}>{v}</Tag>,
    },
    {
      title: "Çözüm durumu",
      dataIndex: "cozum_durumu",
      width: 120,
      render: (v) => <Tag color={COZUM_RENK[v] ?? "default"}>{v}</Tag>,
    },
    {
      title: "İşaretler",
      key: "isaretler",
      width: 140,
      render: (_, r) => (
        <Space size={4}>
          {r.yineleme_supheli && <Tag color="purple">yineleme?</Tag>}
          {r.dusuk_bilgi_supheli && <Tag color="default">düşük bilgi?</Tag>}
        </Space>
      ),
    },
  ];

  const kapsam = yogunlukVeri
    ? KAPSAM_DURUMU_METIN[yogunlukVeri.kapsam_durumu] ?? KAPSAM_DURUMU_METIN.izin_yok
    : null;

  return (
    <div>
      <Space align="center" style={{ marginBottom: 4 }}>
        <Title level={3} style={{ margin: 0 }}>
          Müşteri Sesi (Complaint Insight)
        </Title>
        <Tag color="purple" style={{ fontWeight: 600 }}>
          🟡 SENTETİK VERİ
        </Tag>
      </Space>
      <Paragraph type="secondary" style={{ maxWidth: 760 }}>
        Kampanya metinlerinden değil, müşterilerin şikâyet ifadelerinden
        anlam çıkaran ayrı bir hat. Aşağıdaki örnekler elle yazılmış,
        hiçbir gerçek bankaya atfedilmeyen sentetik veridir - gerçek bir
        şikâyet platformu verisi kurumsal/hukuki (KVKK) onay sürecinden
        sonra bağlanacaktır (bkz.{" "}
        <Text code>docs/veri_edinme_politikasi.md</Text>).
      </Paragraph>

      {hata && (
        <Alert
          type="error"
          showIcon
          message="Veri alınamadı"
          description={hata}
          style={{ marginBottom: 16 }}
        />
      )}

      {kapsam && (
        <Alert
          type={yogunlukVeri.kapsam_durumu === "veri_var" ? "success" : "info"}
          showIcon
          message={`Gerçek veri durumu: ${kapsam.baslik}`}
          description={
            <>
              <div>{kapsam.aciklama}</div>
              <div style={{ marginTop: 4 }}>
                <Text strong>Gözlenen yoğunluk (adet, oran DEĞİL):</Text>{" "}
                {yogunlukVeri.toplam_sikayet}. {yogunlukVeri.aciklama}
              </div>
              <div style={{ marginTop: 4 }}>
                <Text type="secondary">{yogunlukVeri.orneklem_notu}</Text>
              </div>
            </>
          }
          style={{ marginBottom: 16 }}
        />
      )}

      {ornekVeri && (
        <Space size="large" style={{ marginBottom: 16 }} wrap>
          <Statistic title="Sentetik örnek sayısı" value={ornekVeri.ornekler.length} />
          <Statistic title="Tema sayısı" value={ornekVeri.temalar.length} />
          <Statistic
            title="Yüksek önem işaretli"
            value={ornekVeri.ornekler.filter((o) => o.onem_derecesi === "YUKSEK").length}
          />
        </Space>
      )}

      <Card title="Sentetik örnekler ve sınıflandırma çıktısı" size="small" style={{ marginBottom: 16 }}>
        <Paragraph type="secondary" style={{ marginTop: -4 }}>
          {ornekVeri?.aciklama}
        </Paragraph>
        <Table
          rowKey="id"
          size="small"
          loading={yukleniyor}
          dataSource={ornekVeri?.ornekler ?? []}
          columns={sutunlar}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <UcSeviyeliEslesmeKarti />
    </div>
  );
}

/**
 * UcSeviyeliEslesmeKarti — Kampanya eşleştirmesinin üç bağımsız güven
 * seviyesini (banka / ürün türü / kampanya) sabit, açıklanabilir bir
 * örnekle gösterir (bkz. complaint/kampanya_eslestirme.py::EslesmeSonucu,
 * ADR 0003).
 *
 * NEDEN STATİK: /musteri-sesi/ornekler uç noktası kampanya listesi
 * göndermez (bu örnekler tek başına metinlerdir, belirli bir kampanyaya
 * bağlı değildir) - canlı hesaplama için ayrı bir "kampanya eşleştir"
 * uç noktası gerekir, bu kartın amacı o değil. Buradaki sayılar
 * `sikayet_hatti_olcum_raporu.json`'daki AYNI örnekle üretilmiştir
 * (bkz. sikayet_hatti_olcum.py::_entity_resolution_ozeti) - tutarlılık
 * için elle senkronize tutulur.
 */
function UcSeviyeliEslesmeKarti() {
  return (
    <Card
      title="Üç seviyeli kampanya eşleştirmesi (entity resolution)"
      size="small"
      extra={<Tag color="default">sabit örnek</Tag>}
    >
      <Paragraph type="secondary" style={{ marginTop: -4 }}>
        Müşteriler çoğu zaman spesifik kampanya adını yazmaz - banka ve
        ürün türünü belirtir. Kampanya (Seviye 3) eşiği geçemese bile
        banka ve ürün türü sinyalleri <Text strong>bağımsız</Text> olarak
        saklanır, kaybolmaz.
      </Paragraph>
      <Text code style={{ display: "block", marginBottom: 12 }}>
        "A Bankası konut finansmanı başvurumda sorun yaşadım, kâr payı
        oranı yanlış hesaplandı."
      </Text>
      <Row gutter={16}>
        <Col span={8}>
          <Card size="small" style={{ background: "#f6ffed" }}>
            <Text strong>Seviye 1 — Banka</Text>
            <div style={{ marginTop: 8 }}>
              <Tag color="green">Eşleşti: A Bankası</Tag>
            </div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              Çok yüksek güven
            </Text>
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" style={{ background: "#fffbe6" }}>
            <Text strong>Seviye 2 — Ürün türü</Text>
            <div style={{ marginTop: 8 }}>
              <Tag color="gold">Konut Finansmanı — güven 1.0</Tag>
            </div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              Orta/yüksek güven
            </Text>
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" style={{ background: "#fff1f0" }}>
            <Text strong>Seviye 3 — Kampanya</Text>
            <div style={{ marginTop: 8 }}>
              <Tag color="red">Eşleşmedi (güven 0.45 &lt; eşik 0.50)</Tag>
            </div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              Çoğu zaman düşük güven — spesifik kampanya adı hiç geçmiyor
            </Text>
          </Card>
        </Col>
      </Row>
    </Card>
  );
}

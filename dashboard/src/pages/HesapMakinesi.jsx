import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Divider,
  Input,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import { CalculatorOutlined } from "@ant-design/icons";
import { hesapla, kampanyalariGetir } from "../api/client";
import { useAudit } from "../context/AuditContext";

const { Title, Text, Paragraph } = Typography;

// Sartname Md. 5.7 taksit/maliyet hesabi. Bu yetenek bugune kadar YALNIZCA
// sohbet uzerinden erisilebiliyordu ("500.000 TL icin 12 ay vadeyle taksit
// ne olur") - API ucu ve client.js::hesapla hazirdi ama hicbir ekran
// cagirmiyordu. Juri ekranlarda gezerken hesap makinesini goremiyordu.

// Aylik oran ust siniri sema ile AYNI (api/schemas.py::HesapIstek: ge=0, le=20).
// Arayuz burada gevsek davranirsa kullanici 422 hatasi goruyor - sinir
// istemcide de uygulanir ki hata mesaji yerine engellenmis girdi olsun.
const AZAMI_AYLIK_ORAN = 20;
const AZAMI_ANAPARA = 100_000_000;
const AZAMI_VADE_AY = 480;

const ELLE_GIRIS = "__elle__";

function tl(deger) {
  if (deger == null) return "—";
  return deger.toLocaleString("tr-TR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

// Kampanyanin hesaba girebilmesi icin HEM oran HEM vade gerekir; amortisman
// ikisi olmadan yapilamaz. Eksik olanlar GIZLENMEZ, isaretlenir (rapor
// Bolum 5.7/15 - eksik veri gizlenmez ilkesi).
function hesaplanabilir(kampanya) {
  return kampanya.kar_payi_orani_percent != null && kampanya.vade_ay != null;
}

const PLAN_KOLONLARI = [
  { title: "Ay", dataIndex: "ay", key: "ay", width: 70 },
  { title: "Taksit", dataIndex: "taksit", key: "taksit", render: tl },
  {
    title: "Kâr payı kısmı",
    dataIndex: "kar_payi_kismi",
    key: "kar_payi_kismi",
    render: tl,
  },
  {
    title: "Anapara kısmı",
    dataIndex: "anapara_kismi",
    key: "anapara_kismi",
    render: tl,
  },
  {
    title: "Kalan bakiye",
    dataIndex: "kalan_bakiye",
    key: "kalan_bakiye",
    render: tl,
  },
];

export default function HesapMakinesi() {
  const { auditEkle } = useAudit();

  const [kampanyalar, setKampanyalar] = useState([]);
  const [kampanyaYukleniyor, setKampanyaYukleniyor] = useState(true);
  const [secilenKampanya, setSecilenKampanya] = useState(ELLE_GIRIS);

  const [anapara, setAnapara] = useState("");
  const [oran, setOran] = useState("");
  const [vade, setVade] = useState("");
  const [planIstiyor, setPlanIstiyor] = useState(false);

  const [sonuc, setSonuc] = useState(null);
  const [hata, setHata] = useState(null);
  const [hesaplaniyor, setHesaplaniyor] = useState(false);

  useEffect(() => {
    kampanyalariGetir()
      .then(setKampanyalar)
      .catch(() => setKampanyalar([]))
      .finally(() => setKampanyaYukleniyor(false));
  }, []);

  // Kampanya secilince oran/vade KAYITTAN dolar - kullanicidan yalnizca
  // anapara istenir. Elle giris de mumkun kalir (kampanyasiz senaryo).
  const kampanyaSecildi = (deger) => {
    setSecilenKampanya(deger);
    setSonuc(null);
    setHata(null);
    if (deger === ELLE_GIRIS) return;
    const k = kampanyalar.find((x) => x.id === deger);
    if (!k) return;
    // Turkce yazimla doldurulur ("1,89") - kullaniciya gosterilen bicim ile
    // yazacagi bicim ayni olmali, yoksa alan makineden gelmis gibi durur.
    setOran(k.kar_payi_orani_percent?.toLocaleString("tr-TR") ?? "");
    setVade(String(k.vade_ay ?? ""));
  };

  const secenekler = useMemo(
    () => [
      { value: ELLE_GIRIS, label: "Elle giriş (kampanyadan bağımsız)" },
      ...kampanyalar.map((k) => ({
        value: k.id,
        // Hesaplanamayan kampanya listeden CIKARILMAZ - sebebi yazilir.
        label: hesaplanabilir(k)
          ? `${k.banka} — ${k.kampanya_adi}`
          : `${k.banka} — ${k.kampanya_adi}  (oran/vade eksik)`,
        disabled: !hesaplanabilir(k),
      })),
    ],
    [kampanyalar]
  );

  // Noktanin Turkce'de IKI anlami var: binlik ayraci ("500.000") ve -
  // makineden gelen degerlerde - ondalik ayraci ("1.89"). Kor bir
  // `replace(/\./g,"")` ikincisini 189 yapar; bu, calculator.py'de
  // duzeltilen "1234 TL -> 234" hatasinin arayuz karsiligidir.
  //
  // Kural: virgul VARSA ondalik ayraci odur, noktalar binliktir. Virgul
  // yoksa nokta ancak "3'er basamakli gruplar" desenine uyuyorsa binlik
  // sayilir; aksi halde ondalik kabul edilir.
  const sayi = (metin) => {
    let t = String(metin).trim();
    if (t === "") return null;
    if (t.includes(",")) {
      t = t.replace(/\./g, "").replace(",", ".");
    } else if (/^\d{1,3}(\.\d{3})+$/.test(t)) {
      t = t.replace(/\./g, "");
    }
    const d = Number(t);
    return Number.isFinite(d) ? d : null;
  };

  const girdiHatasi = () => {
    const a = sayi(anapara);
    const o = sayi(oran);
    const v = sayi(vade);
    if (a == null || o == null || v == null) return "Üç alanı da doldurun.";
    if (a <= 0 || a > AZAMI_ANAPARA) return `Anapara 0 ile ${tl(AZAMI_ANAPARA)} TL arasında olmalı.`;
    if (o < 0 || o > AZAMI_AYLIK_ORAN)
      return `Aylık kâr payı oranı 0 ile %${AZAMI_AYLIK_ORAN} arasında olmalı. Yıllık oran girmiş olabilir misiniz?`;
    if (!Number.isInteger(v) || v <= 0 || v > AZAMI_VADE_AY)
      return `Vade 1 ile ${AZAMI_VADE_AY} ay arasında tam sayı olmalı.`;
    return null;
  };

  const hesapla_ = async () => {
    const sorun = girdiHatasi();
    if (sorun) {
      setHata(sorun);
      setSonuc(null);
      return;
    }
    setHesaplaniyor(true);
    setHata(null);
    try {
      const yanit = await hesapla({
        anapara: sayi(anapara),
        aylik_oran_percent: sayi(oran),
        vade_ay: sayi(vade),
        odeme_plani_istiyor: planIstiyor,
      });
      setSonuc(yanit);
      // Juri Audit Paneli bu hesabi da gorsun - sohbet yaniti gibi
      // izlenebilir olmali (bkz. context/AuditContext.jsx).
      auditEkle(yanit.audit, `Hesaplama: ${tl(sayi(anapara))} TL / %${oran} / ${vade} ay`);
    } catch (e) {
      setHata(e.response?.data?.detail ?? e.message);
      setSonuc(null);
    } finally {
      setHesaplaniyor(false);
    }
  };

  return (
    <div>
      <Title level={3}>Hesap Makinesi</Title>
      <Paragraph type="secondary" style={{ maxWidth: 720 }}>
        Taksit ve toplam maliyet hesabı. Bir kampanya seçerseniz kâr payı oranı
        ve vade <strong>kaydın kendisinden</strong> gelir; sizden yalnızca
        anapara istenir.
      </Paragraph>

      <Card size="small" style={{ maxWidth: 720, marginBottom: 16 }}>
        <Space orientation="vertical" style={{ width: "100%" }} size={12}>
          <div>
            <Text type="secondary">Kampanya</Text>
            <Select
              style={{ width: "100%", marginTop: 4 }}
              value={secilenKampanya}
              onChange={kampanyaSecildi}
              loading={kampanyaYukleniyor}
              options={secenekler}
              showSearch
              optionFilterProp="label"
            />
          </div>

          <Row gutter={12}>
            <Col xs={24} sm={8}>
              <Text type="secondary">Anapara (TL)</Text>
              <Input
                style={{ marginTop: 4 }}
                value={anapara}
                onChange={(e) => setAnapara(e.target.value)}
                placeholder="500.000"
                inputMode="decimal"
              />
            </Col>
            <Col xs={24} sm={8}>
              <Tooltip title="AYLIK orandır — yıllık oran girmeyin. Kampanya kayıtlarındaki kar_payi_orani_percent ile aynı birim.">
                <Text type="secondary">Aylık kâr payı oranı (%) ⓘ</Text>
              </Tooltip>
              <Input
                style={{ marginTop: 4 }}
                value={oran}
                onChange={(e) => setOran(e.target.value)}
                placeholder="1,89"
                inputMode="decimal"
              />
            </Col>
            <Col xs={24} sm={8}>
              <Text type="secondary">Vade (ay)</Text>
              <Input
                style={{ marginTop: 4 }}
                value={vade}
                onChange={(e) => setVade(e.target.value)}
                placeholder="12"
                inputMode="numeric"
              />
            </Col>
          </Row>

          <Space wrap>
            <Button
              type="primary"
              icon={<CalculatorOutlined />}
              onClick={hesapla_}
              loading={hesaplaniyor}
            >
              Hesapla
            </Button>
            <Button
              onClick={() => {
                setPlanIstiyor(!planIstiyor);
                setSonuc(null);
              }}
            >
              {planIstiyor ? "Ödeme planı: açık" : "Ödeme planı: kapalı"}
            </Button>
          </Space>
        </Space>
      </Card>

      {hata && (
        <Alert
          type="error"
          title="Hesaplama yapılamadı"
          description={hata}
          showIcon
          style={{ maxWidth: 720, marginBottom: 16 }}
        />
      )}

      {sonuc && (
        <>
          <Card size="small" style={{ maxWidth: 720, marginBottom: 16 }}>
            <Row gutter={16}>
              <Col xs={24} sm={8}>
                <Statistic title="Aylık taksit" value={tl(sonuc.aylik_taksit)} suffix="TL" />
              </Col>
              <Col xs={24} sm={8}>
                <Statistic title="Toplam ödeme" value={tl(sonuc.toplam_odeme)} suffix="TL" />
              </Col>
              <Col xs={24} sm={8}>
                <Statistic title="Toplam kâr payı" value={tl(sonuc.toplam_kar_payi)} suffix="TL" />
              </Col>
            </Row>

            <Divider style={{ margin: "12px 0" }} />

            <Paragraph style={{ marginBottom: 8 }}>{sonuc.ozet}</Paragraph>

            {/* Hesap LLM'e BIRAKILMAZ (rapor Bolum 8) - bu rozet o iddianin
                ekrandaki karsiligidir; API'nin kendi dondurdugu degerdir,
                arayuzde sabitlenmis bir metin degil. */}
            <Tooltip title="Taksit hesabı saf Python fonksiyonuyla yapılır; dil modeli kullanılmaz. Bu değer API'nin kendi yanıtından gelir.">
              <Tag color="green">yöntem: {sonuc.yontem}</Tag>
            </Tooltip>
          </Card>

          {sonuc.odeme_plani?.length > 0 && (
            <Card size="small" title="Ödeme planı" style={{ maxWidth: 900 }}>
              <Table
                columns={PLAN_KOLONLARI}
                dataSource={sonuc.odeme_plani}
                rowKey="ay"
                size="small"
                pagination={{ pageSize: 12, showSizeChanger: false }}
                scroll={{ x: "max-content" }}
              />
            </Card>
          )}
        </>
      )}
    </div>
  );
}

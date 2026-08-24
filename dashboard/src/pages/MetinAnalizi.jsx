import { useState } from "react";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  Input,
  List,
  Progress,
  Row,
  Space,
  Statistic,
  Table,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ExperimentOutlined,
  FileSearchOutlined,
  InfoCircleOutlined,
  MinusOutlined,
} from "@ant-design/icons";
import { metinCikar } from "../api/client";
import { useAudit } from "../context/AuditContext";

const { Title, Text, Paragraph } = Typography;

// Sartname Md. 6: demo videosunda "metin girdisi verilmesi, modelin urettigi
// yapilandirilmis cikti" gosterilmesi ZORUNLU. Bu ekran o yolu acar.
//
// TASARIM ILKESI: Deger tek basina gosterilmez. Her alanin yaninda hangi
// katmanin doldurdugu, metindeki kaniti ve dogrulanip dogrulanmadigi gider.
// Bulunamayan alan da GIZLENMEZ - adiyla listelenir, cunku "bos" demek
// "sifir" degil "kaynakta belirtilmemis" demektir.

const ORNEK_METIN = `Kuveyt Türk'ten konut finansmanında kaçırılmayacak fırsat!

Aylık %1,89 kâr payı oranı ve 120 aya varan vade seçeneğiyle hayalinizdeki eve
bir adım daha yaklaşın. Dosya masrafı alınmaz, tahsis ücreti yoktur.

Kampanya 31.12.2026 tarihine kadar geçerlidir. Yeni müşterilerimize özeldir.`;

const ALAN_ADLARI = {
  kar_payi_orani_percent: "Kâr payı oranı (%)",
  kar_payi_orani_decimal: "Kâr payı oranı (ondalık)",
  vade_ay: "Vade (ay)",
  taksit_sayisi: "Taksit sayısı",
  erteleme_suresi_ay: "Ödemesiz dönem (ay)",
  finansman_tutari: "Finansman tutarı",
  odul_miktari: "Ödül miktarı",
  odul_birimi: "Ödül birimi",
  masraf_durumu: "Masraf durumu",
  tahsis_ucreti: "Tahsis ücreti",
  kampanya_avantaji: "Kampanya avantajı",
  kampanya_baslangic: "Başlangıç tarihi",
  kampanya_bitis: "Bitiş tarihi",
  kampanya_turu: "Kampanya türü",
  hedef_kitle: "Hedef kitle",
};

const alanAdi = (anahtar) => ALAN_ADLARI[anahtar] ?? anahtar;

// Üç katmanlı hibrit mimarisi için belirgin renk ve tooltip tanımları (SORUN 3)
const KATMAN_ROZETLERI = {
  regex: {
    color: "green",
    etiket: "regex",
    aciklama: "Deterministik, hızlı kural tabanlı katman",
  },
  gliner: {
    color: "blue",
    etiket: "GLiNER",
    aciklama: "Sıfır atışlı (zero-shot) NER çıkarım katmanı",
  },
  ner: {
    color: "blue",
    etiket: "GLiNER",
    aciklama: "Sıfır atışlı (zero-shot) NER çıkarım katmanı",
  },
  llm: {
    color: "purple",
    etiket: "LLM",
    aciklama: "Büyük dil modeli (LLM) anlamsal çıkarım katmanı",
  },
};

// Verifier durumunun görsel rozet ve tooltip ile sunumu (SORUN 4)
function DogrulamaIsareti({ dogrulandi }) {
  if (dogrulandi === true) {
    return (
      <Tooltip title="Verifier, çıkarılan değeri kaynak metne geri sorar ve bağlamıyla doğrular.">
        <Tag color="green" style={{ margin: 0 }}>
          <CheckCircleOutlined /> doğrulandı
        </Tag>
      </Tooltip>
    );
  }
  if (dogrulandi === false) {
    return (
      <Tooltip title="Verifier bu değeri kaynak metinde birebir doğrulayamadı. Değer SİLİNMEZ — bilinen sınırları var (ör. 'vade farksız' gibi rakam içermeyen ifadeler); amaç görünürlüktür.">
        <Tag color="orange" style={{ margin: 0 }}>
          <ExclamationCircleOutlined /> doğrulanamadı
        </Tag>
      </Tooltip>
    );
  }
  return (
    <Tooltip title="Sayısal olmayan alan — Verifier, çıkarılan değeri kaynak metne geri sorar.">
      <Tag color="default" style={{ margin: 0 }}>
        <MinusOutlined /> çalıştırılmadı
      </Tag>
    </Tooltip>
  );
}

const kolonlar = [
  {
    title: "Alan",
    dataIndex: "alan",
    key: "alan",
    width: 170,
    render: (alan) => <strong>{alanAdi(alan)}</strong>,
  },
  {
    title: "Değer",
    key: "deger",
    width: 140,
    render: (_, satir) => String(satir.deger),
  },
  {
    title: "Katman",
    dataIndex: "katman",
    key: "katman",
    width: 100,
    render: (katman) => {
      const k = KATMAN_ROZETLERI[String(katman).toLowerCase()] || {
        color: "default",
        etiket: katman,
        aciklama: "Çıkarım katmanı",
      };
      return (
        <Tooltip title={k.aciklama}>
          <Tag color={k.color} style={{ fontWeight: 600, margin: 0 }}>
            {k.etiket}
          </Tag>
        </Tooltip>
      );
    },
  },
  {
    title: "Metindeki Kanıt",
    key: "kanit",
    width: 260,
    render: (_, satir) =>
      satir.kanit_turu === "siniflandirma" ? (
        <Tooltip title="Bu alan metinden alıntılanmaz, anahtar kelimelerle SINIFLANDIRILIR. Aşağıdaki ifade bir etikettir; metinde aynen aramayın.">
          <Tag color="cyan" style={{ margin: 0 }}>
            sınıflandırma: {satir.kaynak_span}
          </Tag>
        </Tooltip>
      ) : (
        <Tooltip title={satir.kaynak_span}>
          <span className="analiz-kanit-metin">“{satir.kaynak_span}”</span>
        </Tooltip>
      ),
  },
  {
    title: () => (
      <Tooltip title="Çıkarım güven skoru — doğruluk oranı değil">
        <span>Güven Skoru ⓘ</span>
      </Tooltip>
    ),
    dataIndex: "guven",
    key: "guven",
    width: 110,
    align: "right",
    render: (guven) => (
      <Tooltip title="Çıkarım güven skoru — doğruluk oranı değil">
        <span>{guven == null ? "—" : guven.toFixed(2)}</span>
      </Tooltip>
    ),
  },
  {
    title: "Verifier",
    key: "dogrulandi",
    width: 130,
    render: (_, satir) => <DogrulamaIsareti dogrulandi={satir.dogrulandi} />,
  },
];

export default function MetinAnalizi() {
  const { auditEkle } = useAudit();
  const [metin, setMetin] = useState("");
  const [hibrit, setHibrit] = useState(false);
  const [sonuc, setSonuc] = useState(null);
  const [yukleniyor, setYukleniyor] = useState(false);
  const [hata, setHata] = useState(null);

  const analizEt = async () => {
    setYukleniyor(true);
    setHata(null);
    setSonuc(null);
    try {
      const yanit = await metinCikar(metin, hibrit);
      setSonuc(yanit);
      // Juri Audit Paneli bu cikarimi da gorsun.
      //
      // DENETIM BULGUSU (Havin'in 24.08.2026 raporu, Md. 6): /hesapla ve
      // /karsilastir audit dondururken /cikar dondurmuyordu. Backend tarafi
      // duzeltildi (api/main.py, CikarimYanit.audit) ama arayuz o blogu
      // AuditContext'e hic aktarmiyordu - yani Metin Analizi ekranindan
      // yapilan cikarimlar hala denetim panelinde gorunmuyordu. Sistemin
      // "nasil karar verdi?" sorusu en cok sorulan islemi, denetlenemeyen
      // tek islem olarak kaliyordu.
      auditEkle(yanit.audit, `Metin analizi: ${metin.slice(0, 60)}`);
    } catch (e) {
      setHata(e.response?.data?.detail?.[0]?.msg ?? e.message);
    } finally {
      setYukleniyor(false);
    }
  };

  const satirlar =
    sonuc?.izler.map((iz) => ({
      ...iz,
      key: iz.alan,
      deger: sonuc.alanlar[iz.alan],
    })) ?? [];

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
      <Title level={3} style={{ marginBottom: 4 }}>
        Metin Analizi
      </Title>
      <Paragraph type="secondary" style={{ marginBottom: 20 }}>
        Bir kampanya metnini yapıştırın; sistem hangi finansal alanı{" "}
        <strong>hangi katmandan</strong>, <strong>metnin neresinden</strong> çıkardığını
        kanıtıyla göstersin. Bulunamayan alanlar gizlenmez — adıyla listelenir.
      </Paragraph>

      {/* Düzen: Sol lg={10} (Form), Sağ lg={14} (Sonuç veya Rehber) */}
      <Row gutter={[20, 20]}>
        {/* Sol Kolon: Metin Girişi & Parametreler */}
        <Col xs={24} lg={10}>
          <Card
            size="small"
            title={
              <Space>
                <FileSearchOutlined style={{ color: "var(--marka-500)" }} />
                <span>Kampanya Metni Girdisi</span>
              </Space>
            }
            className="analiz-karti"
          >
            <Input.TextArea
              value={metin}
              onChange={(e) => setMetin(e.target.value)}
              rows={10}
              placeholder="Kampanya metnini buraya yapıştırın (en az 20 karakter)…"
              style={{ fontSize: 13, lineHeight: 1.5 }}
            />

            {/* Hibrit Analiz Seçeneği Formun İçine Alındı */}
            <div
              style={{
                marginTop: 12,
                marginBottom: 14,
                padding: "10px 12px",
                borderRadius: 8,
                background: "var(--zemin-yumusak)",
                border: "1px solid var(--kenarlik)",
              }}
            >
              <Tooltip title="NER + LLM katmanlarını da çalıştırır. GPU'suz makinede daha uzun sürebilir.">
                <Checkbox
                  checked={hibrit}
                  onChange={(e) => setHibrit(e.target.checked)}
                >
                  <span style={{ fontWeight: 500 }}>Hibrit analiz (NER + LLM)</span>{" "}
                  <Tag color="orange" style={{ marginLeft: 4 }}>
                    yavaş
                  </Tag>
                </Checkbox>
              </Tooltip>
              <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 4 }}>
                NER + LLM katmanlarını çalıştırır (daha detaylı fakat daha yavaştır).
              </div>
            </div>

            <Space wrap size="middle">
              <Button
                type="primary"
                icon={<ExperimentOutlined />}
                onClick={analizEt}
                loading={yukleniyor}
                disabled={metin.trim().length < 20}
              >
                Analiz Et
              </Button>
              <Button onClick={() => setMetin(ORNEK_METIN)}>Örnek metin</Button>
              <Button
                onClick={() => {
                  setMetin("");
                  setSonuc(null);
                  setHata(null);
                }}
              >
                Temizle
              </Button>
            </Space>
          </Card>
        </Col>

        {/* Sağ Kolon: Çıkarım Sonuçları veya Öğretici Rehber */}
        <Col xs={24} lg={14}>
          <div className={sonuc ? "analiz-sag-kolon" : ""}>
            {hata && (
              <Alert
                type="error"
                title="Analiz yapılamadı"
                description={hata}
                showIcon
                style={{ marginBottom: 16 }}
              />
            )}

            {/* SORUN 1: Boş Durum Öğretici Tanıtım Kartı (Sahte veri üretilmez) */}
            {!sonuc && !hata && (
              <Card
                size="small"
                title={
                  <Space>
                    <InfoCircleOutlined style={{ color: "var(--marka-500)" }} />
                    <span>Çıkarım Motoru Ne Gösterecek?</span>
                  </Space>
                }
                className="analiz-karti"
              >
                <Space direction="vertical" size={14} style={{ width: "100%" }}>
                  <Paragraph
                    style={{ fontSize: 13, color: "var(--yazi-normal)", margin: 0 }}
                  >
                    Metin analizi çalıştırıldığında, üç katmanlı yapay zekâ motorumuz
                    metni tarayarak şu bilgileri üretecektir:
                  </Paragraph>

                  <div
                    style={{
                      background: "var(--zemin-yumusak)",
                      padding: "12px 16px",
                      borderRadius: 8,
                      border: "1px solid var(--kenarlik)",
                    }}
                  >
                    <List
                      size="small"
                      dataSource={[
                        "📌 Alan: Metinden çıkarılan finansal alan (ör. kâr payı oranı, vade, tahsis ücreti)",
                        "🔢 Değer: Normalize edilmiş sayısal veya metinsel sonuç",
                        "🏷️ Katman: Değeri hangi katmanın bulduğu (regex / GLiNER / LLM)",
                        "💬 Kanıt: Değerin metinde birebir geçtiği tırnak içindeki cümle",
                        "✅ Verifier: Değerin kaynakta doğrulanıp doğrulanmadığı (bağlam kontrolü)",
                      ]}
                      renderItem={(item) => (
                        <List.Item
                          style={{
                            border: "none",
                            padding: "3px 0",
                            fontSize: 12,
                          }}
                        >
                          {item}
                        </List.Item>
                      )}
                    />
                  </div>

                  <Alert
                    type="info"
                    showIcon
                    message="Temel İlke: Bulunamayan alanlar gizlenmez — adıyla listelenir."
                    description="Sistem kaynakta olmayan bir değeri uydurmaz; bulunamayan alanlar 'bilinmiyor' olarak açıkça bildirilir."
                  />
                </Space>
              </Card>
            )}

            {/* Sonuç Alanları ve İstatistik Kartları */}
            {sonuc && (
              <Space direction="vertical" size={16} style={{ width: "100%" }}>
                {/* SORUN 2: Dört Ayrı İstatistik Kartı Şeridi */}
                <Row gutter={[12, 12]}>
                  <Col span={6}>
                    <div className="analiz-istatistik-kutu">
                      <Tooltip title="Çıkarım güven skoru — doğruluk oranı değil">
                        <Text type="secondary" style={{ fontSize: 11, display: "block" }}>
                          Genel Güven ⓘ
                        </Text>
                      </Tooltip>
                      <Progress
                        percent={Math.round(sonuc.genel_guven * 100)}
                        size="small"
                        style={{ marginTop: 4 }}
                      />
                    </div>
                  </Col>
                  <Col span={6}>
                    <div className="analiz-istatistik-kutu">
                      <Text type="secondary" style={{ fontSize: 11, display: "block" }}>
                        Bulunan Alan
                      </Text>
                      <Statistic
                        value={sonuc.izler.length}
                        valueStyle={{ fontSize: 20, fontWeight: 700 }}
                      />
                    </div>
                  </Col>
                  <Col span={6}>
                    <div className="analiz-istatistik-kutu">
                      <Text type="secondary" style={{ fontSize: 11, display: "block" }}>
                        İşlem Süresi
                      </Text>
                      <Statistic
                        value={sonuc.sure_ms}
                        suffix="ms"
                        valueStyle={{ fontSize: 20, fontWeight: 700 }}
                      />
                    </div>
                  </Col>
                  <Col span={6}>
                    <div className="analiz-istatistik-kutu vurgulu">
                      <Text type="secondary" style={{ fontSize: 11, display: "block" }}>
                        Çıkarım Yöntemi
                      </Text>
                      <Tag
                        color={sonuc.hibrit_kullanildi ? "orange" : "green"}
                        style={{ marginTop: 4, fontWeight: 600 }}
                      >
                        {sonuc.hibrit_kullanildi ? "hibrit (NER+LLM)" : "deterministik (regex)"}
                      </Tag>
                    </div>
                  </Col>
                </Row>

                {sonuc.not && (
                  <Alert
                    type="info"
                    title="Hibrit katmanlar çalışmadı"
                    description={sonuc.not}
                    showIcon
                  />
                )}

                {satirlar.length === 0 ? (
                  <Alert
                    type="warning"
                    title="Bu metinden hiçbir alan çıkarılamadı"
                    description="Metin bir kampanya metni olmayabilir ya da bilinen kalıpların dışında yazılmış olabilir. Sistem tahmin üretmek yerine boş dönmeyi tercih eder."
                    showIcon
                  />
                ) : (
                  <Card size="small" title="Çıkarılan Finansal Alanlar" className="analiz-karti">
                    <Table
                      columns={kolonlar}
                      dataSource={satirlar}
                      pagination={false}
                      size="small"
                      scroll={{ x: "max-content" }}
                    />
                  </Card>
                )}

                {sonuc.turetilmis_alanlar.length > 0 && (
                  <Card
                    size="small"
                    title={
                      <Tooltip title="Bu alanlar metinden çıkarılmadı; diğer alanlardan hesaplandı/derlendi. Kanıt izleri yoktur.">
                        <span>Türetilmiş Alanlar (Hesaplanan)</span>
                      </Tooltip>
                    }
                    className="analiz-karti"
                  >
                    {sonuc.turetilmis_alanlar.map((alan) => (
                      <div key={alan} style={{ marginBottom: 4 }}>
                        <Tag color="cyan">türetildi</Tag> {alanAdi(alan)}:{" "}
                        <strong>{String(sonuc.alanlar[alan])}</strong>
                      </div>
                    ))}
                  </Card>
                )}

                {sonuc.catismalar.length > 0 && (
                  <Card size="small" title="Katman Çatışmaları" className="analiz-karti">
                    <Paragraph type="secondary" style={{ fontSize: 12 }}>
                      Aynı alan için birden fazla katman farklı değer önerdi. Seçilen değer aşağıda:
                    </Paragraph>
                    <pre style={{ margin: 0, fontSize: 12, overflowX: "auto" }}>
                      {JSON.stringify(sonuc.catismalar, null, 2)}
                    </pre>
                  </Card>
                )}

                {/* SORUN 7: Kaynakta Bulunamayan Alanlar (Gizlenmez, adıyla listelenir) */}
                {sonuc.bos_alanlar.length > 0 && (
                  <Card
                    size="small"
                    title={
                      <Tooltip title="Bu alanlar SIFIR değil, BİLİNMİYOR. Kaynakta belirtilmemiş olduğu için boş bırakıldı — tahmin üretilmedi.">
                        <span>Kaynakta Bulunamayan Alanlar ({sonuc.bos_alanlar.length})</span>
                      </Tooltip>
                    }
                    className="analiz-karti"
                  >
                    <Space wrap size={6} style={{ marginBottom: 8 }}>
                      {sonuc.bos_alanlar.map((alan) => (
                        <Tag key={alan} style={{ fontSize: 12 }}>
                          {alanAdi(alan)}
                        </Tag>
                      ))}
                    </Space>
                    <Paragraph
                      type="secondary"
                      style={{ fontSize: 12, marginTop: 4, marginBottom: 0 }}
                    >
                      Bu alanlar <strong>sıfır değil, kaynakta belirtilmemiştir</strong>. Sistem
                      olmayan veriyi tahmin ile uydurmaz.
                    </Paragraph>
                  </Card>
                )}
              </Space>
            )}
          </div>
        </Col>
      </Row>
    </div>
  );
}


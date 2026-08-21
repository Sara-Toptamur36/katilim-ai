import { useState } from "react";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  Empty,
  Input,
  Progress,
  Row,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import { metinCikar } from "../api/client";

// Sartname Md. 6: demo videosunda "metin girdisi verilmesi, modelin urettigi
// yapilandirilmis cikti" gosterilmesi ZORUNLU. Bu ekran o yolu acar.
//
// TASARIM ILKESI: Deger tek basina gosterilmez. Her alanin yaninda hangi
// katmanin doldurdugu, metindeki kaniti ve dogrulanip dogrulanmadigi gider.
// Bulunamayan alan da GIZLENMEZ - adiyla listelenir, cunku "bos" demek
// "sifir" degil "kaynakta belirtilmemis" demektir.

// Ornek metinde Turkce karakterler BILEREK dogru yazildi: kelime tabanli
// alanlarin (hedef_kitle, kampanya_turu, erteleme_suresi_ay) cikarimi su an
// diyakritige duyarli - diyakritiksiz yazimda sessizce bos donuyorlar.
// Duzeltme ayri bir is olarak takipte; ornek metin o hataya dusmemeli.
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

const KATMAN_RENKLERI = { regex: "blue", ner: "purple", llm: "orange" };

function DogrulamaIsareti({ dogrulandi }) {
  if (dogrulandi === true) {
    return (
      <Tooltip title="Değer kaynak metinde bağlamıyla birlikte doğrulandı">
        <Tag color="green">doğrulandı</Tag>
      </Tooltip>
    );
  }
  if (dogrulandi === false) {
    return (
      <Tooltip title="Verifier bu değeri kaynakta doğrulayamadı. Değer SİLİNMEZ — bilinen sınırları var (ör. 'vade farksız' gibi rakam içermeyen ifadeler); amaç görünürlüktür.">
        <Tag color="orange">doğrulanamadı</Tag>
      </Tooltip>
    );
  }
  return (
    <Tooltip title="Sayısal olmayan alan — Verifier çalıştırılmadı">
      <Typography.Text type="secondary">—</Typography.Text>
    </Tooltip>
  );
}

const kolonlar = [
  {
    title: "Alan",
    dataIndex: "alan",
    key: "alan",
    render: (alan) => <strong>{alanAdi(alan)}</strong>,
  },
  {
    title: "Değer",
    key: "deger",
    render: (_, satir) => String(satir.deger),
  },
  {
    title: "Katman",
    dataIndex: "katman",
    key: "katman",
    render: (katman) => <Tag color={KATMAN_RENKLERI[katman]}>{katman}</Tag>,
  },
  {
    title: "Metindeki kanıt",
    key: "kanit",
    render: (_, satir) =>
      satir.kanit_turu === "siniflandirma" ? (
        <Tooltip title="Bu alan metinden alıntılanmaz, anahtar kelimelerle SINIFLANDIRILIR. Aşağıdaki ifade bir etikettir; metinde aynen aramayın.">
          <Tag>sınıflandırma: {satir.kaynak_span}</Tag>
        </Tooltip>
      ) : (
        <Typography.Text code>{satir.kaynak_span}</Typography.Text>
      ),
  },
  {
    title: "Güven",
    dataIndex: "guven",
    key: "guven",
    render: (guven) => (guven == null ? "—" : guven.toFixed(2)),
  },
  {
    title: "Verifier",
    key: "dogrulandi",
    render: (_, satir) => <DogrulamaIsareti dogrulandi={satir.dogrulandi} />,
  },
];

export default function MetinAnalizi() {
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
      setSonuc(await metinCikar(metin, hibrit));
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
    <div>
      <Typography.Title level={3}>Metin Analizi</Typography.Title>
      <Typography.Paragraph type="secondary">
        Bir kampanya metnini yapıştırın; sistem hangi finansal alanı{" "}
        <strong>hangi katmandan</strong>, <strong>metnin neresinden</strong> çıkardığını
        kanıtıyla göstersin. Bulunamayan alanlar gizlenmez — adıyla listelenir.
      </Typography.Paragraph>

      <Row gutter={16}>
        <Col xs={24} lg={10}>
          <Card size="small" title="Kampanya metni">
            <Input.TextArea
              value={metin}
              onChange={(e) => setMetin(e.target.value)}
              rows={12}
              placeholder="Kampanya metnini buraya yapıştırın (en az 20 karakter)…"
            />
            <Space style={{ marginTop: 12 }} wrap>
              <Button type="primary" onClick={analizEt} loading={yukleniyor} disabled={metin.trim().length < 20}>
                Analiz Et
              </Button>
              <Button onClick={() => setMetin(ORNEK_METIN)}>Örnek metin</Button>
              <Button onClick={() => { setMetin(""); setSonuc(null); setHata(null); }}>
                Temizle
              </Button>
            </Space>

            <div style={{ marginTop: 12 }}>
              <Tooltip title="NER + LLM katmanlarını da çalıştırır. GPU'suz makinede kayıt başına 150-300 saniye sürebilir — canlı demoda kullanmayın.">
                <Checkbox checked={hibrit} onChange={(e) => setHibrit(e.target.checked)}>
                  Hibrit analiz (NER + LLM) <Tag color="orange">yavaş</Tag>
                </Checkbox>
              </Tooltip>
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={14}>
          {hata && (
            <Alert type="error" title="Analiz yapılamadı" description={hata} showIcon />
          )}

          {!sonuc && !hata && (
            <Card size="small">
              <Empty description="Soldaki alana bir kampanya metni yapıştırıp Analiz Et'e basın" />
            </Card>
          )}

          {sonuc && (
            <Space orientation="vertical" size={12} style={{ width: "100%" }}>
              <Card size="small">
                <Space size="large" wrap>
                  <span>
                    <Typography.Text type="secondary">Genel güven</Typography.Text>
                    <Progress
                      percent={Math.round(sonuc.genel_guven * 100)}
                      size="small"
                      style={{ width: 180 }}
                    />
                  </span>
                  <span>
                    <Typography.Text type="secondary">Bulunan alan</Typography.Text>
                    <div><strong>{sonuc.izler.length}</strong></div>
                  </span>
                  <span>
                    <Typography.Text type="secondary">Süre</Typography.Text>
                    <div><strong>{sonuc.sure_ms} ms</strong></div>
                  </span>
                  <span>
                    <Typography.Text type="secondary">Yöntem</Typography.Text>
                    <div>
                      <Tag color={sonuc.hibrit_kullanildi ? "orange" : "blue"}>
                        {sonuc.hibrit_kullanildi ? "hibrit" : "deterministik (regex)"}
                      </Tag>
                    </div>
                  </span>
                </Space>
              </Card>

              {sonuc.not && (
                <Alert type="info" title="Hibrit katmanlar çalışmadı" description={sonuc.not} showIcon />
              )}

              {satirlar.length === 0 ? (
                <Alert
                  type="warning"
                  title="Bu metinden hiçbir alan çıkarılamadı"
                  description="Metin bir kampanya metni olmayabilir ya da bilinen kalıpların dışında yazılmış olabilir. Sistem tahmin üretmek yerine boş dönmeyi tercih eder."
                  showIcon
                />
              ) : (
                <Card size="small" title="Çıkarılan alanlar">
                  <Table columns={kolonlar} dataSource={satirlar} pagination={false} size="small" />
                </Card>
              )}

              {sonuc.turetilmis_alanlar.length > 0 && (
                <Card
                  size="small"
                  title={
                    <Tooltip title="Bu alanlar metinden çıkarılmadı; diğer alanlardan hesaplandı/derlendi. Kanıt izleri yoktur.">
                      <span>Türetilmiş alanlar (metinden çıkarılmadı)</span>
                    </Tooltip>
                  }
                >
                  {sonuc.turetilmis_alanlar.map((alan) => (
                    <div key={alan}>
                      <Tag color="cyan">türetildi</Tag> {alanAdi(alan)}:{" "}
                      <strong>{String(sonuc.alanlar[alan])}</strong>
                    </div>
                  ))}
                </Card>
              )}

              {sonuc.catismalar.length > 0 && (
                <Card size="small" title="Katman çatışmaları">
                  <Typography.Paragraph type="secondary">
                    Aynı alan için birden fazla katman farklı değer önerdi. Hangisinin neden
                    seçildiği aşağıda:
                  </Typography.Paragraph>
                  <pre style={{ margin: 0, fontSize: 12, overflowX: "auto" }}>
                    {JSON.stringify(sonuc.catismalar, null, 2)}
                  </pre>
                </Card>
              )}

              {sonuc.bos_alanlar.length > 0 && (
                <Card
                  size="small"
                  title={
                    <Tooltip title="Bu alanlar SIFIR değil, BİLİNMİYOR. Kaynakta belirtilmemiş olduğu için boş bırakıldı — tahmin üretilmedi.">
                      <span>Kaynakta belirtilmemiş alanlar ({sonuc.bos_alanlar.length})</span>
                    </Tooltip>
                  }
                >
                  <Space wrap size={4}>
                    {sonuc.bos_alanlar.map((alan) => (
                      <Tag key={alan}>{alanAdi(alan)}</Tag>
                    ))}
                  </Space>
                  <Typography.Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
                    Bu alanlar <strong>sıfır değil, bilinmiyor</strong>. Sistem kaynakta olmayan
                    bir değeri üretmez.
                  </Typography.Paragraph>
                </Card>
              )}
            </Space>
          )}
        </Col>
      </Row>
    </div>
  );
}

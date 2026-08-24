import { useState } from "react";
import { Select, Button, Space, Table, Alert, Tag, Typography } from "antd";
import { karsilastir } from "../api/client";
import { useAudit } from "../context/AuditContext";

// api/comparison/compare_engine.py'daki KRITERLER sozlugu ile BIREBIR ayni
// olmali - sunucu, bu listenin disindaki bir kriteri 422 ile reddeder.
const KRITERLER = [
  { value: "en_dusuk_kar_payi", label: "En düşük kâr payı oranı" },
  { value: "en_yuksek_odul", label: "En yüksek ödül miktarı" },
  { value: "en_uzun_vade", label: "En uzun vade seçeneği" },
  { value: "en_dusuk_masraf", label: "En düşük masraf/tahsis ücreti" },
  { value: "en_yuksek_tutar", label: "En yüksek finansman tutarı" },
];

const KRITER_ETIKETLERI = {
  en_dusuk_kar_payi: "En düşük kâr payı oranı",
  en_yuksek_odul: "En yüksek ödül miktarı",
  en_uzun_vade: "En uzun vade seçeneği",
  en_dusuk_masraf: "En düşük masraf/tahsis ücreti",
  en_yuksek_tutar: "En yüksek finansman tutarı",
};

const sonucKolonlari = [
  { title: "#", dataIndex: "sira", key: "sira", width: 50 },
  { title: "Banka", dataIndex: "banka", key: "banka" },
  { title: "Kampanya", dataIndex: "kampanya_adi", key: "kampanya_adi" },
  {
    title: "Kriter Değeri",
    dataIndex: "kriter_degeri",
    key: "kriter_degeri",
    render: (deger) => (deger != null ? deger : "Belirtilmemiş"),
  },
  {
    title: "Eksik Alanlar",
    dataIndex: "eksik_alanlar",
    key: "eksik_alanlar",
    render: (alanlar) =>
      alanlar && alanlar.length > 0 ? (
        alanlar.map((a) => (
          <Tag key={a} color="orange">
            {a}
          </Tag>
        ))
      ) : (
        <Tag color="green">Eksik yok</Tag>
      ),
  },
];

// Kriter state'i ana bileşene (Karsilastirma.jsx) taşındı. Böylece kampanya seçicisi
// seçili kritere göre dolu verisi olan kampanyaları üst sıraya alabilir.
export default function KarsilastirmaPaneli({
  secilenIdler,
  kriter = "en_dusuk_kar_payi",
  onKriterDegis,
  veriOlanSayisi = 0,
}) {
  const { auditEkle } = useAudit();
  const [sonuc, setSonuc] = useState(null);
  const [yukleniyor, setYukleniyor] = useState(false);
  const [hata, setHata] = useState(null);

  const karsilastirmayiCalistir = async () => {
    setYukleniyor(true);
    setHata(null);
    try {
      const veri = await karsilastir(secilenIdler, kriter);
      setSonuc(veri);

      // POST /karsilastir yanıtında gelen audit verisi Jüri Audit Paneline iletilir
      if (veri?.audit) {
        const kriterAdi = KRITER_ETIKETLERI[kriter] || kriter;
        auditEkle(veri.audit, `Karşılaştırma: ${kriterAdi}`);
      }
    } catch (e) {
      setHata(e.response?.data?.detail || e.message);
      setSonuc(null);
    } finally {
      setYukleniyor(false);
    }
  };


  return (
    <div style={{ marginBottom: 12 }}>
      <Space wrap style={{ marginBottom: 12 }} align="center">
        <Select
          style={{ width: 260 }}
          value={kriter}
          onChange={onKriterDegis}
          options={KRITERLER}
        />
        <Typography.Text type="secondary" style={{ fontSize: 13 }}>
          Bu kriterde veri olan {veriOlanSayisi} kampanya var
        </Typography.Text>
        <Button
          type="primary"
          onClick={karsilastirmayiCalistir}
          disabled={secilenIdler.length < 2}
          loading={yukleniyor}
        >
          Karşılaştır ({secilenIdler.length} seçili)
        </Button>
      </Space>

      {secilenIdler.length < 2 && (
        <p style={{ color: "var(--yazi-soluk)", marginBottom: 12 }}>
          Karşılaştırmak için yukarıdaki listeden en az 2 kampanya seçin.
        </p>
      )}

      {hata && (
        <Alert
          type="error"
          message="Karşılaştırma başarısız"
          description={hata}
          showIcon
          style={{ marginBottom: 12 }}
        />
      )}

      {sonuc && (
        <>
          {sonuc.audit?.sebep && (
            <Alert
              type="info"
              message={sonuc.audit.sebep}
              style={{ marginBottom: 12 }}
              showIcon
            />
          )}
          <Table
            columns={sonucKolonlari}
            dataSource={sonuc.sonuclar}
            rowKey="id"
            pagination={false}
            size="small"
            scroll={{ x: "max-content" }}
          />
        </>
      )}
    </div>
  );
}


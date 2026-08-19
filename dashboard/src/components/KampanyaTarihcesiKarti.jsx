import { useEffect, useState } from "react";
import { Alert, Card, Skeleton, Table, Tag, Timeline, Typography } from "antd";
import { kampanyaTarihcesiGetir } from "../api/client";

// Kampanyanin ZAMAN icindeki degisimi - statik karsilastirmanin
// tamamlayicisi. Ek veri toplamaz, scraper'in delta kontrollu tarama
// sayesinde zaten diskte duran coklu tarihli kayitlari okur (bkz.
// scraper/scripts/kampanya_tarihcesi.py). "Bu kampanya sessizce
// guncellendi mi?" sorusunun cevabidir.

const ALAN_ADLARI = {
  kar_payi_orani_percent: "Kâr payı oranı",
  vade_ay: "Vade",
  finansman_tutari: "Finansman tutarı",
  taksit_sayisi: "Taksit sayısı",
  erteleme_suresi_ay: "Erteleme süresi",
  odul_miktari: "Ödül miktarı",
  odul_birimi: "Ödül birimi",
  kampanya_baslangic: "Başlangıç tarihi",
  kampanya_bitis: "Bitiş tarihi",
};

const kolonlar = [
  {
    title: "Alan",
    dataIndex: "alan",
    key: "alan",
    render: (alan) => ALAN_ADLARI[alan] ?? alan,
  },
  {
    title: "Önce",
    dataIndex: "eski",
    key: "eski",
    render: (deger) => deger ?? <Typography.Text type="secondary">Belirtilmemiş</Typography.Text>,
  },
  {
    title: "Sonra",
    dataIndex: "yeni",
    key: "yeni",
    render: (deger) =>
      deger == null ? (
        <Typography.Text type="secondary">Belirtilmemiş</Typography.Text>
      ) : (
        <Tag color="blue">{deger}</Tag>
      ),
  },
];

export default function KampanyaTarihcesiKarti({ kampanyaId }) {
  const [veri, setVeri] = useState(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(null);

  useEffect(() => {
    if (kampanyaId == null) return;
    setYukleniyor(true);
    setHata(null);
    kampanyaTarihcesiGetir(kampanyaId)
      .then(setVeri)
      .catch((e) => setHata(e.message))
      .finally(() => setYukleniyor(false));
  }, [kampanyaId]);

  if (kampanyaId == null) return null;
  if (hata) {
    return <Alert type="error" title="Tarihçe alınamadı" description={hata} showIcon />;
  }
  if (yukleniyor || !veri) return <Skeleton active paragraph={{ rows: 2 }} />;

  const { tarihce, degisen_alanlar: degisenAlanlar } = veri;

  // Coklu-taramali olmak zaten ISTISNADIR (bkz. kampanya_tarihcesi.py
  // docstring'i) - tek/sifir kayitli olmak hata degil, en yaygin durumdur.
  if (tarihce.length === 0) {
    return (
      <Alert
        type="info"
        title="Tarama kaydı bulunamadı"
        description="Bu kampanyanın kaynak sayfası için henüz bir tarama kaydı yok."
        showIcon
      />
    );
  }

  const degisenSatirlar = Object.entries(degisenAlanlar ?? {}).map(([alan, d]) => ({
    key: alan,
    alan,
    ...d,
  }));

  return (
    <Card size="small" title={`Değişim Tarihçesi — ${tarihce.length} tarama`}>
      {degisenSatirlar.length > 0 ? (
        <Table columns={kolonlar} dataSource={degisenSatirlar} pagination={false} size="small" />
      ) : (
        <Alert
          type="info"
          title={
            tarihce.length === 1
              ? "Bu kampanya tek bir tarihte tarandı"
              : "İçerik tarandı ama takip edilen alanlarda gerçek bir değişiklik yok"
          }
          description="Kozmetik bir metin düzeltmesi olabilir; finansal alanlar aynı kaldı."
          showIcon
          style={{ marginBottom: tarihce.length > 1 ? 12 : 0 }}
        />
      )}

      {tarihce.length > 1 && (
        <Timeline
          style={{ marginTop: 16 }}
          items={tarihce.map((t) => ({ children: t.tarih }))}
        />
      )}
    </Card>
  );
}

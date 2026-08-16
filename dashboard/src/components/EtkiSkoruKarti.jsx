import { useEffect, useState } from "react";
import { Alert, Card, Progress, Skeleton, Table, Tag, Tooltip, Typography } from "antd";
import { etkiSkoruGetir } from "../api/client";

// "Bu kampanya IYI bir kampanya mi?" - piyasaya gore nerede duruyor.
//
// TASARIM: Skor ASLA tek basina gosterilmez, eksen kirilimi hep yanindadir.
// Tek bir sayiya bakip karar vermek, sayinin nereden geldigini gizlemek olur
// (bkz. comparison/etki_skoru.py modul basligi).

const EKSEN_ADLARI = {
  en_dusuk_kar_payi: "Kâr payı",
  en_yuksek_odul: "Ödül",
  en_uzun_vade: "Vade",
  en_dusuk_masraf: "Masraf",
};

// Eksen neden ölçülemedi? Kullanıcıya "yok" demek yetmez, sebebi lazım.
const EKSEN_DURUM_METINLERI = {
  deger_yok: "Kaynakta belirtilmemiş",
  birim_karisik: "Farklı birimler karşılaştırılamaz",
  yetersiz_eksen_kume: "Karşılaştırılacak başka değer yok",
};

function yuzdelikRengi(yuzdelik) {
  if (yuzdelik >= 0.75) return "green";
  if (yuzdelik >= 0.4) return "blue";
  return "orange";
}

// "Üst %X dilim" DEMIYORUZ: en iyi kayıt için "üst %0 dilim" gibi anlamsız
// bir metin üretirdi.
//
// Sayıya iyelik eki de EKLEMIYORUZ ("%75'inden" mi "%75'sinden" mi?) —
// Türkçede ek, sayının okunuşundaki son sese göre değişir ve her sayı için
// doğru eki üretmek ayrı bir iş. Onun yerine ek gerektirmeyen "%X kadarından"
// kalıbı kullanılıyor; uç değerlerde ise sayı hiç yazılmıyor.
function yuzdelikMetni(yuzdelik, olculebilirKayit) {
  const rakip = olculebilirKayit - 1; // kendisi hariç
  if (yuzdelik >= 1) return `Diğer ${rakip} kampanyanın hepsinden iyi`;
  if (yuzdelik <= 0) return `Diğer ${rakip} kampanyanın hepsinden geride`;
  return `Diğer ${rakip} kampanyanın %${Math.round(yuzdelik * 100)} kadarından iyi`;
}

const kolonlar = [
  {
    title: "Eksen",
    dataIndex: "eksen",
    key: "eksen",
    render: (eksen, satir) => (
      <Tooltip title={satir.aciklama}>{EKSEN_ADLARI[eksen] ?? eksen}</Tooltip>
    ),
  },
  {
    title: "Bu kampanya",
    key: "deger",
    render: (_, satir) =>
      satir.deger == null ? (
        <Typography.Text type="secondary">Belirtilmemiş</Typography.Text>
      ) : (
        `${satir.deger}${satir.birim ? ` ${satir.birim}` : ""}`
      ),
  },
  {
    title: "Piyasadaki yeri",
    key: "yuzdelik",
    render: (_, satir) => {
      if (satir.yuzdelik == null) {
        const sebep = EKSEN_DURUM_METINLERI[satir.durum] ?? satir.durum;
        return <Tag>{sebep}</Tag>;
      }
      return (
        <Tag color={yuzdelikRengi(satir.yuzdelik)}>
          {yuzdelikMetni(satir.yuzdelik, satir.olculebilir_kayit)}
        </Tag>
      );
    },
  },
];

export default function EtkiSkoruKarti({ kampanyaId }) {
  const [veri, setVeri] = useState(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(null);

  useEffect(() => {
    if (kampanyaId == null) return;
    setYukleniyor(true);
    setHata(null);
    etkiSkoruGetir(kampanyaId)
      .then(setVeri)
      .catch((e) => setHata(e.message))
      .finally(() => setYukleniyor(false));
  }, [kampanyaId]);

  if (kampanyaId == null) return null;
  if (hata) {
    return <Alert type="error" title="Etki skoru alınamadı" description={hata} showIcon />;
  }
  if (yukleniyor || !veri) return <Skeleton active paragraph={{ rows: 3 }} />;

  const { finansal, musteri_geri_bildirim: geriBildirim } = veri;
  const olculdu = finansal.durum === "olculdu";

  return (
    <Card size="small" title={`Etki Skoru — ${veri.banka}`}>
      {olculdu ? (
        <>
          <Typography.Text strong>Finansal gösterge</Typography.Text>
          <Progress
            percent={Math.round(finansal.skor * 100)}
            status={finansal.skor >= 0.6 ? "success" : "normal"}
            style={{ maxWidth: 320 }}
          />
          <Typography.Paragraph type="secondary">
            {finansal.kampanya_turu} türünde {finansal.karsilastirma_kumesi} aktif
            kampanya içinde, {finansal.kullanilan_eksen} eksen ölçülerek hesaplandı.
          </Typography.Paragraph>
        </>
      ) : (
        <Alert
          type="info"
          title="Finansal gösterge hesaplanamadı"
          description={finansal.sebep}
          showIcon
          style={{ marginBottom: 12 }}
        />
      )}

      <Table
        columns={kolonlar}
        dataSource={finansal.eksen_kirilimi}
        rowKey="eksen"
        pagination={false}
        size="small"
      />

      {/* Sifir YAZILMAZ: geri bildirim yoklugu "memnun degil" demek degildir. */}
      <Alert
        type="info"
        title="Müşteri geri bildirimi"
        description={geriBildirim.sebep ?? "Yeterli geri bildirim bulunamadı."}
        showIcon
        style={{ marginTop: 12 }}
      />
    </Card>
  );
}

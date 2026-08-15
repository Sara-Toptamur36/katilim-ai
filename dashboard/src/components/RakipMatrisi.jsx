import { useEffect, useState } from "react";
import { Alert, Select, Skeleton, Space, Table, Tag, Tooltip, Typography } from "antd";
import { rakipAnaliziGetir } from "../api/client";

// Sartname Md. 5.7 - "farkli katilim bankalarina ait urunlerin
// karsilastirilabilir hale getirilmesi". KarsilastirmaPaneli TEK kritere
// gore secilmis kampanyalari siralar; bu tablo TUM kriterleri TUM
// kampanyalar icin yan yana koyar.
//
// Her kampanya KENDI satirinda kalir (bankalar tek satira sikistirilmaz) -
// gerekcesi comparison/compare_engine.py::rakip_matrisi docstring'inde.

const EKSEN_BASLIKLARI = {
  en_dusuk_kar_payi: "Kâr Payı",
  en_yuksek_odul: "Ödül",
  en_uzun_vade: "Vade",
  en_dusuk_masraf: "Masraf",
  en_yuksek_tutar: "Tutar",
};

const EKSEN_BIRIMLERI = {
  en_dusuk_kar_payi: (d) => `%${d}`,
  en_uzun_vade: (d) => `${d} ay`,
  en_dusuk_masraf: (d) => `${d} TL`,
  en_yuksek_tutar: (d) => `${d} TL`,
};

function hucreMetni(kriter, hucre) {
  if (hucre?.deger == null) return null;
  // Odulun birimi hucreyle birlikte gelir - "5000" tek basina TL mi
  // Worldpuan mi belli degil.
  if (kriter === "en_yuksek_odul") {
    return `${hucre.deger} ${hucre.birim ?? ""}`.trim();
  }
  return (EKSEN_BIRIMLERI[kriter] ?? String)(hucre.deger);
}

function EksenBasligi({ eksen }) {
  const baslik = EKSEN_BASLIKLARI[eksen.kriter] ?? eksen.kriter;

  if (eksen.durum === "veri_yok") {
    return (
      <Tooltip title="Hiçbir kampanyada bu alan belirtilmemiş">
        <span>
          {baslik} <Tag>veri yok</Tag>
        </span>
      </Tooltip>
    );
  }

  if (eksen.durum === "birim_karisik") {
    return (
      <Tooltip
        title={`Farklı birimler var (${eksen.birimler?.join(", ")}). Farklı birimler arasında "en yüksek" karşılaştırması yapılamaz, bu yüzden lider seçilmedi.`}
      >
        <span>
          {baslik} <Tag color="orange">birim karışık</Tag>
        </span>
      </Tooltip>
    );
  }

  return (
    <Tooltip title={`${eksen.aciklama} — ${eksen.olculebilir_kayit} kampanyada ölçülebildi`}>
      <span>{baslik}</span>
    </Tooltip>
  );
}

function eksenKolonu(eksen) {
  return {
    title: <EksenBasligi eksen={eksen} />,
    key: eksen.kriter,
    render: (_, satir) => {
      const hucre = satir.degerler[eksen.kriter];
      const metin = hucreMetni(eksen.kriter, hucre);

      // Eksik veri GIZLENMEZ (rapor Bolum 5.7/15).
      if (metin === null) {
        return <Typography.Text type="secondary">Belirtilmemiş</Typography.Text>;
      }
      if (hucre.lider) {
        return (
          <Tag color="green">
            {metin} <span aria-label="lider">★</span>
          </Tag>
        );
      }
      return metin;
    },
  };
}

export default function RakipMatrisi({ turler = [] }) {
  const [tur, setTur] = useState(null);
  const [veri, setVeri] = useState(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(null);

  useEffect(() => {
    setYukleniyor(true);
    setHata(null);
    rakipAnaliziGetir(tur)
      .then(setVeri)
      .catch((e) => setHata(e.message))
      .finally(() => setYukleniyor(false));
  }, [tur]);

  const suzgec = (
    <Select
      value={tur}
      onChange={setTur}
      allowClear
      placeholder="Tüm kampanya türleri"
      style={{ minWidth: 260, marginBottom: 12 }}
      options={turler.map((t) => ({ value: t, label: t }))}
    />
  );

  if (hata) {
    return (
      <>
        {suzgec}
        <Alert type="error" title="Rakip analizi alınamadı" description={hata} showIcon />
      </>
    );
  }

  if (yukleniyor || !veri) {
    return (
      <>
        {suzgec}
        <Skeleton active paragraph={{ rows: 4 }} />
      </>
    );
  }

  const kolonlar = [
    {
      title: "Banka",
      dataIndex: "banka",
      key: "banka",
      render: (banka, satir) => (
        <Typography.Link href={satir.kaynak_url} target="_blank" rel="noopener noreferrer">
          {banka}
        </Typography.Link>
      ),
    },
    { title: "Kampanya", dataIndex: "kampanya_adi", key: "kampanya_adi" },
    ...veri.eksenler.map(eksenKolonu),
    {
      title: <Tooltip title="Kaç eksende önde olduğu">Öne çıktığı</Tooltip>,
      dataIndex: "lider_eksen_sayisi",
      key: "lider_eksen_sayisi",
      render: (sayi) => (sayi > 0 ? <Tag color="blue">{sayi} eksen</Tag> : "—"),
    },
  ];

  return (
    <>
      {suzgec}

      <Typography.Paragraph type="secondary">
        {veri.kayit_sayisi} aktif kampanya · {veri.banka_sayisi} banka. Yeşil hücre o
        eksendeki lideri gösterir; eşitlikte birden fazla lider işaretlenir. Bir bankanın
        aynı türde birden çok kampanyası varsa her biri kendi satırındadır — farklı
        kampanyaların en iyi değerleri tek satırda birleştirilmez.
      </Typography.Paragraph>

      <Table
        columns={kolonlar}
        dataSource={veri.satirlar}
        rowKey={(satir) => satir.id ?? `${satir.banka}-${satir.kampanya_adi}`}
        pagination={{ pageSize: 10, hideOnSinglePage: true }}
        scroll={{ x: "max-content" }}
        size="small"
      />

      <Space size={4} wrap>
        <Typography.Text type="secondary">Eksen durumları:</Typography.Text>
        <Tag>veri yok</Tag>
        <Typography.Text type="secondary">hiçbir kampanyada belirtilmemiş ·</Typography.Text>
        <Tag color="orange">birim karışık</Tag>
        <Typography.Text type="secondary">
          farklı birimler karşılaştırılamaz, lider seçilmedi
        </Typography.Text>
      </Space>
    </>
  );
}

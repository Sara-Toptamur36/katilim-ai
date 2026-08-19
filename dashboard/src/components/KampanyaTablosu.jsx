import { Table, Tag, Tooltip, Typography } from "antd";

// Verifier (validation/verifier.py) her sayisal alanin kaynak metinde
// (deger + baglam) gercekten gectigini kontrol eder ve sonucu
// `dogrulanan_alanlar` sutununda saklar. Uc durum BILEREK ayri:
//
//   alan sozlukte YOK  -> Verifier bu alan icin hic calismadi
//   true               -> kaynakta dogrulandi
//   false              -> dogrulanamadi; deger SILINMEZ (Verifier'in
//                         bilinen siniri var: "vade farksiz" gibi rakam
//                         icermeyen ifadeler dogrulanamiyor). Amac
//                         gorunurluk, veri budama degil.
function DogrulamaOzeti({ dogrulananAlanlar }) {
  const girdiler = Object.entries(dogrulananAlanlar ?? {});

  if (girdiler.length === 0) {
    return (
      <Tooltip title="Bu kayıtta Verifier hiçbir alan için çalıştırılmadı (alanlar zaten doluydu ya da sayısal değil)">
        <span>—</span>
      </Tooltip>
    );
  }

  const dogrulanan = girdiler.filter(([, d]) => d === true);
  const basarisiz = girdiler.filter(([, d]) => d === false);
  const hepsi = basarisiz.length === 0;

  const ipucu = (
    <>
      {dogrulanan.length > 0 && <div>✓ {dogrulanan.map(([a]) => a).join(", ")}</div>}
      {basarisiz.length > 0 && (
        <div style={{ marginTop: 4 }}>
          ⚠ {basarisiz.map(([a]) => a).join(", ")} — kaynakta doğrulanamadı, değer
          silinmedi
        </div>
      )}
    </>
  );

  return (
    <Tooltip title={ipucu}>
      <Tag color={hepsi ? "green" : "orange"}>
        {dogrulanan.length}/{girdiler.length}
      </Tag>
    </Tooltip>
  );
}

// Eksik veri GIZLENMEZ - "Belirtilmemis" yazilir (rapor Bolum 5.7/15, seffaflik ilkesi).
// Siralamada null degerler en sona gider (NULLS LAST mantigi, ?? 999 ile).
const kolonlar = [
  { title: "Banka", dataIndex: "banka", key: "banka" },
  { title: "Kampanya", dataIndex: "kampanya_adi", key: "kampanya_adi" },
  { title: "Tür", dataIndex: "kampanya_turu", key: "kampanya_turu" },
  {
    title: "Kâr Payı Oranı",
    dataIndex: "kar_payi_orani_percent",
    key: "kar_payi",
    render: (deger) => (deger != null ? `%${deger}` : "Belirtilmemiş"),
    sorter: (a, b) =>
      (a.kar_payi_orani_percent ?? 999) - (b.kar_payi_orani_percent ?? 999),
  },
  {
    title: "Vade (ay)",
    dataIndex: "vade_ay",
    key: "vade",
    render: (deger) => (deger != null ? deger : "Belirtilmemiş"),
    sorter: (a, b) => (a.vade_ay ?? 999) - (b.vade_ay ?? 999),
  },
  {
    title: "Ödül",
    key: "odul",
    render: (_, kayit) =>
      kayit.odul_miktari != null
        ? `${kayit.odul_miktari} ${kayit.odul_birimi ?? ""}`
        : "Belirtilmemiş",
  },
  {
    title: (
      <Tooltip title="Sayısal değerlerin kaynak metinde doğrulanma oranı (Verifier)">
        Doğrulama
      </Tooltip>
    ),
    key: "dogrulama",
    render: (_, kayit) => (
      <DogrulamaOzeti dogrulananAlanlar={kayit.dogrulanan_alanlar} />
    ),
  },
  {
    title: (
      <Tooltip title="Kaynak sayfanın son tarandığı tarih. İçeriğin gerçekten değişip değişmediği için bkz. Değişim Tarihçesi (tek kampanya seçince).">
        Son Tarandı
      </Tooltip>
    ),
    dataIndex: "belge_tarihi",
    key: "belge_tarihi",
    render: (deger) => deger ?? <Typography.Text type="secondary">Belirtilmemiş</Typography.Text>,
    sorter: (a, b) => (a.belge_tarihi ?? "").localeCompare(b.belge_tarihi ?? ""),
  },
  {
    title: "Durum",
    dataIndex: "durum",
    key: "durum",
    render: (durum) => (
      <Tag color={durum === "ACTIVE" ? "green" : "default"}>
        {durum === "ACTIVE" ? "Aktif" : durum === "EXPIRED" ? "Süresi Dolmuş" : "Bilinmiyor"}
      </Tag>
    ),
  },
];

export default function KampanyaTablosu({ kampanyalar, yukleniyor, rowSelection }) {
  return (
    <Table
      columns={kolonlar}
      dataSource={kampanyalar}
      rowKey="id"
      loading={yukleniyor}
      rowSelection={rowSelection}
      scroll={{ x: "max-content" }}
    />
  );
}

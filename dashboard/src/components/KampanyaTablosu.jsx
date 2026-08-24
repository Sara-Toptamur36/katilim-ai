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

// EKSIK DEGERIN IKI AYRI SEBEBI VAR ve bunlari ayirmak seffaflik ilkesinin
// ta kendisidir - "eksik veri gizlenmez, ISARETLENIR":
//
//   alan_belirtilmemis[alan] === true -> kaynak sayfaya BAKILDI, deger orada yok
//   alan sozlukte hic yok            -> cikarim bu alani hic denemedi
//
// Ikisi de bos hucre uretir ama ayni sey DEGILDIR: birincisi bankanin
// bilgiyi yayimlamadigini soyler (olculebilir bir bulgu), ikincisi bizim
// hentiz bakmadigimizi. Arayuz ikisini de duz "Belirtilmemis" yazarak
// birbirine karistiriyordu; `alan_belirtilmemis` sutunu backend'de
// uretilip API'den donuyor ama hicbir yerde OKUNMUYORDU.
//
// Ayni uc-durum ayrimi Verifier icin (DogrulamaOzeti) zaten yapiliyordu.
function EksikDeger({ kayit, alan }) {
  const bakildi = kayit?.alan_belirtilmemis?.[alan] === true;
  return (
    <Tooltip
      title={
        bakildi
          ? "Kaynak sayfa tarandı, bu bilgi sayfada yayımlanmamış"
          : "Bu alan için çıkarım çalıştırılmadı — kaynakta olmadığı anlamına gelmez"
      }
    >
      <Typography.Text type="secondary" style={{ borderBottom: "1px dotted", cursor: "help" }}>
        {bakildi ? "Kaynakta yok" : "Belirtilmemiş"}
      </Typography.Text>
    </Tooltip>
  );
}

const kolonlar = [
  { title: "Banka", dataIndex: "banka", key: "banka" },
  { title: "Kampanya", dataIndex: "kampanya_adi", key: "kampanya_adi" },
  { title: "Tür", dataIndex: "kampanya_turu", key: "kampanya_turu" },
  {
    title: "Kâr Payı Oranı",
    dataIndex: "kar_payi_orani_percent",
    key: "kar_payi",
    render: (deger, kayit) =>
      deger != null ? `%${deger}` : <EksikDeger kayit={kayit} alan="kar_payi_orani_percent" />,
    sorter: (a, b) =>
      (a.kar_payi_orani_percent ?? 999) - (b.kar_payi_orani_percent ?? 999),
  },
  {
    title: "Vade (ay)",
    dataIndex: "vade_ay",
    key: "vade",
    render: (deger, kayit) =>
      deger != null ? deger : <EksikDeger kayit={kayit} alan="vade_ay" />,
    sorter: (a, b) => (a.vade_ay ?? 999) - (b.vade_ay ?? 999),
  },
  {
    title: "Ödül",
    key: "odul",
    render: (_, kayit) =>
      kayit.odul_miktari != null ? (
        `${kayit.odul_miktari} ${kayit.odul_birimi ?? ""}`
      ) : (
        <EksikDeger kayit={kayit} alan="odul_miktari" />
      ),
  },
  {
    // NAKIT IADE / INDIRIM - 24.08.2026'da baglandi.
    // Bu iki deger cikarim motorunda ZATEN uretiliyordu (RE_NAKIT_IADE /
    // RE_INDIRIM_ORANI) ama veritabaninda sutunlari yoktu, her calistirmada
    // atiliyordu. Olculdu: 60 kayit etkileniyordu - "Enterprise Arac
    // Kiralamalarinda %35 Indirim" gibi kampanyalarin ANA avantaji
    // arayuzde hicbir yerde gorunmuyordu.
    //
    // Kendi sutunlarinda durmalari ayrica bir KESINLIK korumasidir: motor
    // bu yuzdeleri kar payi oraniyla karistirmasin diye ayiriyor; gidecek
    // yer olmayinca ayirmanin yarisi bosa gidiyordu.
    title: (
      <Tooltip title="Nakit iade veya indirim oranı — kâr payı oranı DEĞİLDİR, ayrı bir avantaj türüdür">
        İade / İndirim
      </Tooltip>
    ),
    key: "iade_indirim",
    render: (_, kayit) => {
      const parcalar = [];
      if (kayit.nakit_iade_orani != null) {
        parcalar.push(
          <Tag color="green" key="iade">
            %{kayit.nakit_iade_orani} nakit iade
          </Tag>
        );
      }
      if (kayit.indirim_orani_percent != null) {
        parcalar.push(
          <Tag color="blue" key="indirim">
            %{kayit.indirim_orani_percent} indirim
          </Tag>
        );
      }
      return parcalar.length ? <>{parcalar}</> : <EksikDeger kayit={kayit} alan="nakit_iade_orani" />;
    },
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

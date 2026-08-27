import { useState } from "react";
import { Table, Tag, Button, Tooltip } from "antd";
import {
  finansalIpucuCikar,
  oneCikanAvantajCikar,
  kampanyaRozetiMeta,
} from "../../utils/cevapBicimlendirme";
import EvidenceCard from "../EvidenceCard";

function DurumHucresi({ meta }) {
  if (!meta) return <Tag color="default">Belirtilmemiş</Tag>;
  const antdRenk = { success: "green", warning: "orange", error: "red" }[meta.renk] ?? "default";
  return <Tag color={antdRenk}>{meta.etiket}</Tag>;
}

// Birden fazla kampanya doner geldiginde uzun metin yerine kullanilan
// karsilastirma tablosu. Oran/Vade/Tutar/Avantaj sutunlari kaynak
// metninden BIREBIR alinti (finansalIpucuCikar / oneCikanAvantajCikar) -
// kaynakta yoksa "Belirtilmemiş" gosterilir, hicbir deger hesaplanmaz/
// uydurulmaz. Durum sutunu KampanyaKarti ile AYNI kurali izler: guncellik
// biliniyorsa o, bilinmiyorsa arama benzerligine dayali eslesme kalitesi
// gosterilir (bkz. cevapBicimlendirme.js::kampanyaRozetiMeta).
export default function KarsilastirmaTablosu({ kampanyalar }) {
  const [genisletilenAnahtar, setGenisletilenAnahtar] = useState(null);

  const veri = kampanyalar.map((k, i) => {
    const birlesikMetin = k.kaynaklar.map((x) => x.metin).filter(Boolean).join(" ");
    const ipucu = finansalIpucuCikar(birlesikMetin);
    return {
      key: i,
      banka: k.banka,
      kampanya: k.kampanyaAdi ?? "Belirtilmemiş",
      oran: ipucu.oran ?? "Belirtilmemiş",
      vade: ipucu.vade ?? "Belirtilmemiş",
      tutar: ipucu.tutar ?? "Belirtilmemiş",
      avantaj: oneCikanAvantajCikar(birlesikMetin),
      rozet: kampanyaRozetiMeta(k.enIyiKaynak?.guncellik, k.enIyiKaynak?.similarity_score),
      kaynaklar: k.kaynaklar,
    };
  });

  // SUTUN GENISLIKLERI + scroll.x ZORUNLU (olculdu 27.08.2026, 784 px
  // genislikte gercek veriyle): genislik verilmeden antd sutunlari mevcut
  // dar alana SIKISTIRIYOR ve uzun kampanya adlari harf harf alt alta
  // sariliyordu ("K u v e y t T ü r k") - tablo okunamaz hale geliyordu.
  // scroll={{x:true}} tek basina yetmiyor: tasma olmadigi icin yatay kaydirma
  // hic devreye girmiyordu. Toplam genislik scroll.x ile SABITLENIR, dar
  // ekranda tablo kendi icinde yatay kayar (govde kaymaz).
  const sutunlar = [
    { title: "Banka", dataIndex: "banka", key: "banka", width: 120, ellipsis: true },
    { title: "Kampanya", dataIndex: "kampanya", key: "kampanya", width: 170, ellipsis: true },
    { title: "Vade", dataIndex: "vade", key: "vade", width: 80 },
    { title: "Tutar", dataIndex: "tutar", key: "tutar", width: 100 },
    { title: "Oran", dataIndex: "oran", key: "oran", width: 80 },
    {
      title: "Avantaj",
      dataIndex: "avantaj",
      key: "avantaj",
      width: 200,
      ellipsis: { showTitle: false },
      render: (v) =>
        v ? (
          <Tooltip title={v}>
            <span>{v}</span>
          </Tooltip>
        ) : (
          "Belirtilmemiş"
        ),
    },
    {
      title: "Durum",
      dataIndex: "rozet",
      key: "rozet",
      width: 120,
      render: (v) => <DurumHucresi meta={v} />,
    },
    {
      title: "",
      key: "kaynak",
      width: 110,
      render: (_, kayit) => (
        <Button
          type="link"
          size="small"
          onClick={() =>
            setGenisletilenAnahtar((a) => (a === kayit.key ? null : kayit.key))
          }
        >
          Kaynağı Gör
        </Button>
      ),
    },
  ];

  return (
    <>
      <Table
        className="karsilastirma-tablosu"
        size="small"
        dataSource={veri}
        columns={sutunlar}
        pagination={false}
        style={{ marginTop: 8, maxWidth: 900 }}
        scroll={{ x: 900 }}
        expandable={{
          expandedRowKeys: genisletilenAnahtar === null ? [] : [genisletilenAnahtar],
          showExpandColumn: false,
          expandedRowRender: (kayit) => (
            <div>
              {kayit.kaynaklar.map((k, i) => (
                <EvidenceCard key={i} kaynak={k} boyut="kucuk" />
              ))}
            </div>
          ),
        }}
      />
      <div className="karsilastirma-tablosu-not">
        Tablodaki bilgiler kaynaklardan alınmıştır. Eksik alanlar "Belirtilmemiş" olarak işaretlenir.
      </div>
    </>
  );
}

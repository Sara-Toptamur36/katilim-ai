import { useState } from "react";
import { Card, Tag, Button } from "antd";
import {
  BankOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  DownOutlined,
  UpOutlined,
} from "@ant-design/icons";
import { finansalIpucuCikar } from "../../utils/cevapBicimlendirme";
import EvidenceCard from "../EvidenceCard";

function GuncellikRozeti({ guncellik, kampanyaBitis }) {
  if (guncellik === "suresi_dolmus")
    return (
      <Tag color="red">
        <WarningOutlined /> Süresi dolmuş{kampanyaBitis ? ` — ${kampanyaBitis}` : ""}
      </Tag>
    );
  if (guncellik === "aktif")
    return (
      <Tag color="green">
        <CheckCircleOutlined /> Güncel{kampanyaBitis ? ` — ${kampanyaBitis} tarihine kadar` : ""}
      </Tag>
    );
  return <Tag color="default">Geçerlilik durumu belirtilmemiş</Tag>;
}

function BilgiSatiri({ etiket, deger }) {
  return (
    <div className="kampanya-karti-satir">
      <span className="kampanya-karti-etiket">{etiket}</span>
      <span className="kampanya-karti-deger">{deger ?? "Belirtilmemiş"}</span>
    </div>
  );
}

// Tek bir kampanyayi (bir veya birden fazla kaynak parcasindan gruplanmis)
// yapilandirilmis bir kart olarak gosterir. Oran/Vade/Tutar alanlari kaynak
// metninden BIREBIR alinti olarak cikarilir (finansalIpucuCikar); kaynakta
// yoksa "Belirtilmemiş" gosterilir, ASLA uydurulmaz.
export default function KampanyaKarti({ kampanya }) {
  const [kaynakAcik, setKaynakAcik] = useState(false);
  const { banka, kampanyaAdi, enIyiKaynak, kaynaklar } = kampanya;

  const birlesikMetin = kaynaklar.map((k) => k.metin).filter(Boolean).join(" ");
  const ipucu = finansalIpucuCikar(birlesikMetin);

  return (
    <Card
      size="small"
      className="kampanya-karti"
      title={
        <span>
          <BankOutlined style={{ marginRight: 6 }} />
          {banka}
          {kampanyaAdi ? ` — ${kampanyaAdi}` : ""}
        </span>
      }
      style={{ marginTop: 8, maxWidth: 480 }}
    >
      <div style={{ marginBottom: 8 }}>
        <GuncellikRozeti
          guncellik={enIyiKaynak?.guncellik}
          kampanyaBitis={enIyiKaynak?.kampanya_bitis}
        />
      </div>

      <div className="kampanya-karti-satirlar">
        <BilgiSatiri etiket="Oran" deger={ipucu.oran} />
        <BilgiSatiri etiket="Vade" deger={ipucu.vade} />
        <BilgiSatiri etiket="Finansman tutarı" deger={ipucu.tutar} />
        <BilgiSatiri
          etiket="Güncellik tarihi"
          deger={enIyiKaynak?.belge_tarihi}
        />
      </div>

      <Button
        type="link"
        size="small"
        onClick={() => setKaynakAcik((a) => !a)}
        icon={kaynakAcik ? <UpOutlined /> : <DownOutlined />}
        style={{ paddingLeft: 0, marginTop: 4 }}
      >
        Kaynağı Gör
      </Button>

      {kaynakAcik && (
        <div style={{ marginTop: 4 }}>
          {kaynaklar.map((k, i) => (
            <EvidenceCard key={i} kaynak={k} boyut="kucuk" />
          ))}
        </div>
      )}
    </Card>
  );
}

import { useState } from "react";
import { Card, Tag, Button } from "antd";
import { BankOutlined, DownOutlined, UpOutlined } from "@ant-design/icons";
import {
  finansalIpucuCikar,
  oneCikanAvantajCikar,
  kampanyaRozetiMeta,
} from "../../utils/cevapBicimlendirme";
import EvidenceCard from "../EvidenceCard";

function DurumRozeti({ meta }) {
  if (!meta) return <Tag color="default">Belirtilmemiş</Tag>;
  const antdRenk = { success: "green", warning: "orange", error: "red" }[meta.renk] ?? "default";
  return <Tag color={antdRenk}>{meta.etiket}</Tag>;
}

function IlgiliBilgiSatiri({ etiket, deger }) {
  return (
    <li className="kampanya-karti-ilgili-satir">
      <span className="kampanya-karti-etiket">{etiket}:</span>{" "}
      <span className="kampanya-karti-deger">{deger ?? "Belirtilmemiş"}</span>
    </li>
  );
}

// Kampanya karti - jüri gosteriminde tek bakista taranabilmesi icin YATAY
// dort bolume ayrilir: kimlik+durum / one cikan avantaj / ilgili bilgiler /
// kaynak tarihi+detay. Hicbir alan burada HESAPLANMAZ - hepsi ya kaynak
// metninden birebir alinti (finansalIpucuCikar, oneCikanAvantajCikar) ya
// da backend'in zaten urettigi alanlardir (guncellik, similarity_score,
// belge_tarihi). Eksikse "Belirtilmemiş" gosterilir, ASLA uydurulmaz.
export default function KampanyaKarti({ kampanya }) {
  const [kaynakAcik, setKaynakAcik] = useState(false);
  const { banka, kampanyaAdi, enIyiKaynak, kaynaklar } = kampanya;

  const birlesikMetin = kaynaklar.map((k) => k.metin).filter(Boolean).join(" ");
  const ipucu = finansalIpucuCikar(birlesikMetin);
  const avantaj = oneCikanAvantajCikar(birlesikMetin);
  const rozet = kampanyaRozetiMeta(enIyiKaynak?.guncellik, enIyiKaynak?.similarity_score);

  return (
    <Card size="small" className="kampanya-karti-yatay" style={{ marginTop: 8 }}>
      <div className="kampanya-karti-satir-govde">
        {/* 1 — Kimlik + durum */}
        <div className="kampanya-karti-bolum kampanya-karti-kimlik">
          <div className="kampanya-karti-banka">
            <BankOutlined style={{ marginRight: 6 }} />
            {banka}
          </div>
          <DurumRozeti meta={rozet} />
          {kampanyaAdi && <div className="kampanya-karti-adi">{kampanyaAdi}</div>}
        </div>

        {/* 2 — Öne çıkan avantaj */}
        <div className="kampanya-karti-bolum">
          <div className="kampanya-karti-alan-baslik">Öne Çıkan Avantaj</div>
          <div className="kampanya-karti-avantaj-metni">
            {avantaj ?? "Kaynak metninde belirgin bir avantaj cümlesi bulunamadı."}
          </div>
        </div>

        {/* 3 — İlgili bilgiler */}
        <div className="kampanya-karti-bolum">
          <div className="kampanya-karti-alan-baslik">İlgili Bilgiler</div>
          <ul className="kampanya-karti-ilgili-liste">
            <IlgiliBilgiSatiri etiket="Vade" deger={ipucu.vade} />
            <IlgiliBilgiSatiri etiket="Tutar" deger={ipucu.tutar} />
            <IlgiliBilgiSatiri etiket="Oran" deger={ipucu.oran} />
          </ul>
        </div>

        {/* 4 — Kaynak tarihi + detay */}
        <div className="kampanya-karti-bolum kampanya-karti-tarih-bolum">
          <div className="kampanya-karti-alan-baslik">Kaynak Tarihi</div>
          <div className="kampanya-karti-tarih">{enIyiKaynak?.belge_tarihi ?? "Belirtilmemiş"}</div>
          <Button
            size="small"
            onClick={() => setKaynakAcik((a) => !a)}
            icon={kaynakAcik ? <UpOutlined /> : <DownOutlined />}
            style={{ marginTop: 6 }}
          >
            Detayları Gör
          </Button>
        </div>
      </div>

      {kaynakAcik && (
        <div style={{ marginTop: 10 }}>
          {kaynaklar.map((k, i) => (
            <EvidenceCard key={i} kaynak={k} boyut="kucuk" />
          ))}
        </div>
      )}
    </Card>
  );
}

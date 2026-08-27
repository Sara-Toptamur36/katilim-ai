import { useState } from "react";
import { Typography } from "antd";
import { kaynakMetniTemizle } from "../../utils/cevapBicimlendirme";

const KIRPMA_UZUNLUGU = 220;

// Kaynak metnini (RAG'in birebir dondurdugu alinti) GORSEL olarak
// temizleyip varsayilan olarak kirpar. Icerik degistirilmez - yalnizca
// gurultu (tekrar satirlar/fazla bosluk) silinir ve uzun metin
// "Devamını göster" ile actirilir.
export default function KaynakMetniGoster({ metin, boyut = "normal" }) {
  const [acik, setAcik] = useState(false);
  if (!metin) return null;

  const temiz = kaynakMetniTemizle(metin);
  const uzunMu = temiz.length > KIRPMA_UZUNLUGU;
  const gosterilen = !uzunMu || acik ? temiz : temiz.slice(0, KIRPMA_UZUNLUGU).trim() + "…";

  return (
    <blockquote
      style={{
        margin: 0,
        padding: "8px 12px",
        borderLeft: "3px solid #1677ff",
        background: "var(--kart-ustu)",
        borderRadius: "0 6px 6px 0",
        fontSize: boyut === "kucuk" ? 11 : 12,
        lineHeight: 1.6,
      }}
    >
      <Typography.Text type="secondary" italic>
        "{gosterilen}"
      </Typography.Text>
      {uzunMu && (
        <div style={{ marginTop: 4 }}>
          <Typography.Link
            onClick={() => setAcik((a) => !a)}
            style={{ fontSize: 11 }}
          >
            {acik ? "Daha az göster" : "Devamını göster"}
          </Typography.Link>
        </div>
      )}
    </blockquote>
  );
}

import { CommentOutlined } from "@ant-design/icons";

/**
 * DeneyimSinyaliBadge — Müşteri Sesi verilerini finansal veriden
 * görsel olarak ayıran badge.
 *
 * RAPOR GEREKSİNİMİ: "müşteri sesi verisinin kehribar (amber) tonunda
 * ve 'deneyim sinyali' etiketiyle, görsel dili tamamen farklı bir
 * şekilde sunulması planlanmıştır."
 *
 * KULLANIM:
 *   <DeneyimSinyaliBadge />
 *   <DeneyimSinyaliBadge sentetik />
 */
export default function DeneyimSinyaliBadge({ sentetik = false }) {
  return (
    <span className="deneyim-sinyali-badge">
      <CommentOutlined className="deneyim-sinyali-ikon" />
      📢 {sentetik ? "Deneyim Sinyali (SENTETİK)" : "Deneyim Sinyali"}
    </span>
  );
}

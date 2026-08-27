import { Card, Typography } from "antd";
import { CalculatorOutlined } from "@ant-design/icons";
import { hesaplamaVerisiCikar } from "../../utils/cevapBicimlendirme";

const SATIRLAR = [
  { anahtar: "anapara", etiket: "Finansman" },
  { anahtar: "vade", etiket: "Vade" },
  { anahtar: "oran", etiket: "Aylık kâr payı oranı" },
  { anahtar: "aylikTaksit", etiket: "Aylık ödeme" },
  { anahtar: "toplamOdeme", etiket: "Toplam ödeme" },
  { anahtar: "toplamKarPayi", etiket: "Toplam kâr payı" },
];

// HESAPLAMA SONUCU karti - LLM'in degil, calculator/calculator.py'deki
// deterministik Python fonksiyonunun urettigi sayilari gosterir. Sayilar
// YENIDEN HESAPLANMAZ; cevap metninde ZATEN yazan degerler ayiklanip
// yapilandirilmis satirlar halinde sunulur (bkz. hesaplamaVerisiCikar).
export default function HesaplamaKarti({ cevapMetni }) {
  const veri = hesaplamaVerisiCikar(cevapMetni);

  return (
    <Card
      size="small"
      className="hesaplama-karti"
      title={
        <span>
          <CalculatorOutlined style={{ marginRight: 6 }} />
          Hesaplama Sonucu
        </span>
      }
      style={{ marginTop: 8, maxWidth: 420 }}
    >
      {veri ? (
        <div className="hesaplama-karti-satirlar">
          {SATIRLAR.map(({ anahtar, etiket }) => (
            <div className="hesaplama-karti-satir" key={anahtar}>
              <span className="hesaplama-karti-etiket">{etiket}</span>
              <span className="hesaplama-karti-deger">{veri[anahtar]}</span>
            </div>
          ))}
        </div>
      ) : (
        <Typography.Paragraph style={{ margin: 0 }}>{cevapMetni}</Typography.Paragraph>
      )}
      <Typography.Text type="secondary" style={{ fontSize: 11, display: "block", marginTop: 10 }}>
        Bu değer deterministik hesaplama motoru tarafından hesaplanmıştır.
      </Typography.Text>
    </Card>
  );
}

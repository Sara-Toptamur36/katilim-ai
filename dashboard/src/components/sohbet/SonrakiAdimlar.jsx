import { Link } from "react-router-dom";
import { RightOutlined } from "@ant-design/icons";

// Sonraki adim onerileri - UYDURULMUS bir "AI onerisi" DEGIL, uygulamada
// zaten var olan gercek sayfalara (App.jsx route tanimlari) yonlendiren
// sabit kisayollardir. Hicbir veri UYETMEZ, yalniz navigasyon saglar.
const ADIMLAR = [
  { etiket: "Kampanyaları detaylı inceleyin", href: "/kampanyalar" },
  { etiket: "Finansman karşılaştırması yapın", href: "/karsilastirma" },
  { etiket: "Finansman hesaplayın", href: "/hesapla" },
];

export default function SonrakiAdimlar() {
  return (
    <div className="sonraki-adimlar-blok">
      <div className="sohbet-alt-baslik">Sonraki Adımlar</div>
      <ul className="sonraki-adimlar-liste">
        {ADIMLAR.map((a) => (
          <li key={a.href}>
            <Link to={a.href}>
              {a.etiket} <RightOutlined style={{ fontSize: 10 }} />
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

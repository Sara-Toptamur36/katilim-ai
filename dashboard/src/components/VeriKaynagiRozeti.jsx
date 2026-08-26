import { useEffect, useState } from "react";
import { Tag, Tooltip } from "antd";
import { tazelikGetir } from "../api/client";

// NEDEN GEREKLI: demo/canlı veri ayrımı önceden dağınıktı - yalnızca
// Dashboard'da (TazelikSeridi'nin demo_mode banner'ı) ve MusteriSesi'nde
// (SENTETİK/Gerçek veri metni) görünüyordu. Jüri Chatbot'ta ya da
// Karşılaştırma'dayken hangi veri modunda olduğunu hiç göremiyordu.
// Bu bileşen ÜstBar'a (her sayfada render edilir, bkz. App.jsx) eklenerek
// TEK, her zaman görünen bir rozet sağlar.
//
// AYRI BİR VERİ KAYNAĞI EKLEMEZ: TazelikSeridi'nin de okuduğu AYNI
// GET /sistem/tazelik uç noktasını kullanır - iki yerde ayrı "demo mu
// değil mi" hesabı oluşmasın diye (bkz. api/schemas.py::TazelikYanit.demo_mode).
export default function VeriKaynagiRozeti() {
  const [veri, setVeri] = useState(null);

  useEffect(() => {
    tazelikGetir()
      .then(setVeri)
      .catch(() => setVeri(null)); // sessizce gizlenir - ÜstBar'daki "Bağlantı yok" göstergesi zaten bunu bildiriyor
  }, []);

  if (!veri) return null;

  const tarih = veri.son_tarama
    ? new Date(veri.son_tarama).toLocaleDateString("tr-TR", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : null;

  if (veri.demo_mode) {
    return (
      <Tooltip title="Yerel doğrulanmış veri (PostgreSQL/Qdrant/Ollama) — gerçek canlı banka verisi değildir.">
        <Tag color="purple" style={{ margin: 0, fontWeight: 600 }}>
          🟣 DEMO SNAPSHOT{tarih ? ` — ${tarih}` : ""}
        </Tag>
      </Tooltip>
    );
  }

  return (
    <Tooltip title="Sistem gerçek/canlı veri modunda çalışıyor (GERCEK_VERI_AKTIF=true).">
      <Tag color="green" style={{ margin: 0, fontWeight: 600 }}>
        🟢 CANLI VERİ
      </Tag>
    </Tooltip>
  );
}

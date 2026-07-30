import { useEffect, useState } from "react";
import { Input, Spin, Typography } from "antd";
import { chatGonder, tokenAl } from "../api/client";
import ChatMesaji from "../components/ChatMesaji";
import { useAudit } from "../context/AuditContext";

const { Title } = Typography;

export default function Chatbot() {
  const [mesajlar, setMesajlar] = useState(() => {
    const kayitli = sessionStorage.getItem("chat_gecmisi");
    return kayitli ? JSON.parse(kayitli) : [];
  });
  const [girdi, setGirdi] = useState("");
  const [bekleniyor, setBekleniyor] = useState(false);
  const { auditEkle } = useAudit();

  useEffect(() => {
    sessionStorage.setItem("chat_gecmisi", JSON.stringify(mesajlar));
  }, [mesajlar]);

  // Aktif yol: Sara'nin /chat endpoint'i su an tek seferde (non-streaming)
  // yanit donuyor. Bu fonksiyon bunun icin yazildi.
  const gonder = async () => {
    if (!girdi.trim()) return;

    const soru = girdi;
    setMesajlar((onceki) => [...onceki, { rol: "kullanici", metin: soru }]);
    setGirdi("");
    setBekleniyor(true);

    try {
      const yanit = await chatGonder(soru);
      setMesajlar((onceki) => [
        ...onceki,
        {
          rol: "bot",
          metin: yanit.cevap,
          kaynaklar: yanit.kaynaklar,
          confidence: yanit.confidence,
          fallback: yanit.fallback,
        },
      ]);
      auditEkle(yanit.audit, soru);
    } catch {
      setMesajlar((onceki) => [
        ...onceki,
        {
          rol: "bot",
          metin: "Uzgunum, su anda yanit veremiyorum. Lutfen tekrar deneyin.",
          hata: true,
        },
      ]);
    } finally {
      setBekleniyor(false);
    }
  };

  // HAZIR AMA HENUZ KULLANILMIYOR: Sara /chat/stream (SSE) endpoint'ini
  // eklediginde onSearch={gonderStreaming} olarak degistirilecek. Rehber
  // Sprint 3 Gun 2 fallback plani geregi, iki fonksiyon ayri tutuluyor -
  // Sara'nin SSE'si hazir olmadan arayuz calisir durumda kalir.
  const gonderStreaming = async () => {
    if (!girdi.trim()) return;

    const soru = girdi;
    setMesajlar((onceki) => [...onceki, { rol: "kullanici", metin: soru }]);
    setGirdi("");
    setMesajlar((onceki) => [...onceki, { rol: "bot", metin: "", streaming: true }]);

    try {
      const yanit = await fetch("http://localhost:8000/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${tokenAl()}`,
        },
        body: JSON.stringify({ soru }),
      });

      const reader = yanit.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const parca = decoder.decode(value, { stream: true });

        setMesajlar((onceki) => {
          const kopya = [...onceki];
          const son = { ...kopya[kopya.length - 1] };
          son.metin += parca;
          kopya[kopya.length - 1] = son;
          return kopya;
        });
      }

      setMesajlar((onceki) => {
        const kopya = [...onceki];
        kopya[kopya.length - 1] = { ...kopya[kopya.length - 1], streaming: false };
        return kopya;
      });
    } catch {
      setMesajlar((onceki) => [
        ...onceki,
        {
          rol: "bot",
          metin: "Baglanti sirasinda bir sorun olustu. Lutfen tekrar deneyin.",
          hata: true,
        },
      ]);
    }
  };

  return (
    <div>
      <Title level={3}>Chatbot</Title>
      <div>
        {mesajlar.map((m, i) => (
          <ChatMesaji key={i} mesaj={m} />
        ))}
      </div>
      {bekleniyor && <Spin description="Yanit hazirlaniyor..." />}
      <Input.Search
        value={girdi}
        onChange={(e) => setGirdi(e.target.value)}
        onSearch={gonder}
        enterButton="Gonder"
        placeholder="Orn: A Bankasi'nin konut finansmani orani ne?"
        disabled={bekleniyor}
      />
    </div>
  );
}

import { Card, Typography, Tag, Progress, Alert } from "antd";

export default function ChatMesaji({ mesaj }) {
  const kullaniciMi = mesaj.rol === "kullanici";

  return (
    <div style={{ marginBottom: 16 }}>
      <div>
        <strong>{kullaniciMi ? "Siz:" : "KatilimAI:"}</strong>{" "}
        {mesaj.metin}
        {mesaj.streaming && <span>▍</span>}
      </div>

      {mesaj.fallback && (
        <Alert
          type="info"
          title="Bu soruyu tam olarak anlayamadim"
          description="Kampanya karsilastirmasi, kar payi oranlari veya vade sureleri hakkinda soru sorabilirsiniz."
          showIcon
          style={{ marginTop: 8, maxWidth: 480 }}
        />
      )}

      {mesaj.hata && (
        <Alert
          type="error"
          title="Baglanti sorunu"
          description={mesaj.metin}
          showIcon
          style={{ marginTop: 8, maxWidth: 480 }}
        />
      )}

      {!kullaniciMi && mesaj.confidence != null && !mesaj.streaming && !mesaj.hata && (
        <div style={{ marginTop: 4 }}>
          <span>Yanit guven skoru: </span>
          <Progress
            percent={Math.round(mesaj.confidence * 100)}
            size="small"
            status={
              mesaj.confidence > 0.8
                ? "success"
                : mesaj.confidence > 0.5
                  ? "normal"
                  : "exception"
            }
            style={{ width: 200 }}
          />
        </div>
      )}

      {mesaj.kaynaklar && mesaj.kaynaklar.length > 0 && (
        <Card size="small" title="Kaynaklar" style={{ marginTop: 8, maxWidth: 480 }}>
          {mesaj.kaynaklar.map((k, i) => (
            <div key={i}>
              <Typography.Link href={k.kaynak_url} target="_blank" rel="noopener noreferrer">
                {k.banka} — {k.kampanya_adi}
              </Typography.Link>
              {k.similarity_score != null && (
                <Tag style={{ marginLeft: 8 }}>
                  Benzerlik: {k.similarity_score.toFixed(2)}
                </Tag>
              )}
              {k.belge_tarihi && <Tag>Belge tarihi: {k.belge_tarihi}</Tag>}
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}

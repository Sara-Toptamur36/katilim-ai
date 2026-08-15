import { Card, Typography, Tag, Progress, Alert } from "antd";

// Md. 5.5 - Terminoloji Kontrolu kartinin metinleri. Uc durum BILEREK
// ayri: `null`, "sorun yok" DEMEK DEGILDIR - RAG ve Sozluk araclarinda
// gelenek terim MESRU sekilde gecebilir, o yuzden orada kontrol bir hata
// degil BILGI NOTU uretir. Bunu "temiz" gibi gostermek olcumu yanlis
// anlatirdi (bkz. agent/orchestrator.py modul docstring'i).
const TERMINOLOJI_DURUMLARI = {
  temiz: {
    tip: "success",
    baslik: "Terminoloji denetlendi — geleneksel bankacılık terimi kullanılmadı",
  },
  sizinti: {
    tip: "warning",
    baslik: "Terminoloji uyarısı — yanıtta geleneksel bankacılık terimi geçiyor",
  },
  bilgi: {
    tip: "info",
    baslik: "Terminoloji bilgi notu — bu yanıtta geleneksel terim beklenen bir durum",
  },
};

// Bilgi notunun GEREKCESI araca gore degisir - ikisini ayni cumleyle
// aciklamak yanlis olur (orchestrator ikisini ayni kumede tutar ama
// SEBEPLERI farklidir, bkz. o dosyanin docstring'i):
//   rag        -> kaynak metin birebir aktarilir, bankanin ifadesi
//                 duzeltilmez (seffaflik ilkesi)
//   dictionary -> sozlugun ISI zaten gelenek karsiligi ogretmektir
const BILGI_NOTU_GEREKCELERI = {
  rag: "Bu yanıt kaynak metni birebir aktarır; bankanın kendi ifadesi değiştirilmez. Katılım bankacılığı karşılığı aşağıda bilgi olarak verilir.",
  dictionary:
    "Bu yanıt sözlükten gelir; geleneksel karşılığı öğretmek sözlüğün görevidir. Aşağıdaki eşleştirme cevabın kendisidir, bir hata değildir.",
};

function terminolojiDurumu(mesaj) {
  const sorunVar = mesaj.terminolojiSorunlari?.length > 0;

  // Fallback yanitta ("bu soruyu anlayamadim") ONAY kartini gostermeyiz -
  // ortada denetlenecek gercek bir cevap yoktur, "terminoloji temiz"
  // demek yaniltici bir guven verirdi. Sorun BULUNDUYSA yine gosterilir:
  // uyariyi gizlemek seffaflik ilkesine aykiri olurdu.
  if (mesaj.fallback && !sorunVar) return null;

  if (mesaj.terminolojiTutarli === true) return "temiz";
  if (mesaj.terminolojiTutarli === false) return "sizinti";
  return sorunVar ? "bilgi" : null;
}

export default function ChatMesaji({ mesaj }) {
  const kullaniciMi = mesaj.rol === "kullanici";
  const durum = kullaniciMi ? null : terminolojiDurumu(mesaj);

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

      {durum && !mesaj.streaming && !mesaj.hata && (
        <Alert
          type={TERMINOLOJI_DURUMLARI[durum].tip}
          title={TERMINOLOJI_DURUMLARI[durum].baslik}
          description={
            mesaj.terminolojiSorunlari?.length > 0 ? (
              <>
                {durum === "bilgi" && BILGI_NOTU_GEREKCELERI[mesaj.cagrilanArac] && (
                  <div style={{ marginBottom: 4 }}>
                    {BILGI_NOTU_GEREKCELERI[mesaj.cagrilanArac]}
                  </div>
                )}
                {mesaj.terminolojiSorunlari.map((s, i) => (
                  <div key={i}>
                    <Tag>{s.gelenek_terim}</Tag> → <strong>{s.onerilen}</strong>
                  </div>
                ))}
              </>
            ) : (
              "Yanıtta faiz, mevduat veya kredi gibi geleneksel bankacılık terimi bulunmadı."
            )
          }
          showIcon
          style={{ marginTop: 8, maxWidth: 480 }}
        />
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

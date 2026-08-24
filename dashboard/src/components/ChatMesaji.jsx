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
        <strong>{kullaniciMi ? "Siz:" : "KatılımAI:"}</strong>{" "}
        {mesaj.metin}
        {mesaj.streaming && <span>▍</span>}
      </div>

      {mesaj.fallback && (
        <Alert
          type="warning"
          message="Güvenli Başarısızlık: Cevap Üretilemedi"
          description="Sistem, kaynak yetersizliği veya düşük güven skoru nedeniyle cevap üretmedi. Halüsinasyon riskini önlemek için bu bir güvenlik önlemidir. Lütfen sorunuzu farklı kelimelerle ifade edin veya kampanya koşullarını sorun."
          showIcon
          style={{ marginTop: 8, maxWidth: 480 }}
        />
      )}

      {mesaj.hata && (
        <Alert
          type="error"
          title="Bağlantı sorunu"
          description={mesaj.metin}
          showIcon
          style={{ marginTop: 8, maxWidth: 480 }}
        />
      )}

      {!kullaniciMi && mesaj.confidence != null && !mesaj.streaming && !mesaj.hata && (
        <div style={{ marginTop: 4 }}>
          <span>Yanıt güven skoru: </span>
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
        <Card size="small" title="Kaynaklar" style={{ marginTop: 8, maxWidth: 640 }} headStyle={{ backgroundColor: "var(--kart-ustu)" }}>
          {mesaj.kaynaklar.map((k, i) => (
            <div key={i} style={{ marginBottom: i < mesaj.kaynaklar.length - 1 ? 16 : 0, paddingBottom: i < mesaj.kaynaklar.length - 1 ? 12 : 0, borderBottom: i < mesaj.kaynaklar.length - 1 ? "1px solid var(--kenarlik)" : "none" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 }}>
                <Typography.Link href={k.kaynak_url} target="_blank" rel="noopener noreferrer" style={{ fontWeight: 600 }}>
                  🔗 {k.banka} — {k.kampanya_adi}
                </Typography.Link>
                {k.similarity_score != null && (
                  <Tag color="blue" style={{ margin: 0 }}>
                    Skor: {k.similarity_score.toFixed(2)}
                  </Tag>
                )}
              </div>
              <div style={{ marginBottom: 8 }}>
                {/* KAYNAK GIZLENMEZ, ISARETLENIR.
                    Retriever'da bir tarih filtresi vardi ama calismiyordu
                    (hicbir cagiran gecmiyordu ve baktigi valid_at alanlari
                    indekste hic yoktu). Filtre yerine isaret secildi: yanlis
                    cikarilmis tek bir tarih, GECERLI bir kampanyayi sessizce
                    gorunmez yapabilirdi - juride fark edilmesi en zor hata.
                    Burada kullanici hem kaynagi hem uyariyi birlikte gorur. */}
                {k.guncellik === "suresi_dolmus" && (
                  <Tag color="red" style={{ fontWeight: 600 }}>
                    ⚠ Süresi dolmuş{k.kampanya_bitis ? ` — ${k.kampanya_bitis}` : ""}
                  </Tag>
                )}
                {k.guncellik === "aktif" && k.kampanya_bitis && (
                  <Tag color="green">Geçerli — {k.kampanya_bitis} tarihine kadar</Tag>
                )}
                {k.guncellik === "bilinmiyor" && (
                  <Tag color="default">Geçerlilik tarihi bilinmiyor</Tag>
                )}
                {k.chunk_id && <Tag color="default">Chunk ID: {k.chunk_id}</Tag>}
                {k.belge_tarihi && <Tag color="cyan">Tarih: {k.belge_tarihi}</Tag>}
                {k.erisim_zamani && <Tag color="geekblue">Erişim: {new Date(k.erisim_zamani).toLocaleDateString("tr-TR")}</Tag>}
              </div>

              {/* "Her cumle bir kaynak belgeden gelir" iddiasinin GORSEL KANITI. */}
              {k.metin && (
                <blockquote
                  style={{
                    margin: 0,
                    padding: "8px 12px",
                    borderLeft: "4px solid #1677ff",
                    background: "var(--kart-ustu)",
                    borderRadius: "0 4px 4px 0",
                    fontSize: 13,
                  }}
                >
                  <Typography.Text type="secondary" italic>{k.metin}</Typography.Text>
                </blockquote>
              )}
            </div>
          ))}
          <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px dashed var(--kenarlik)" }}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              ℹ️ Alıntılar kaynak sayfadan <strong>birebir</strong> alınmıştır; sistem bu metnin üzerine cümle üretmez.
            </Typography.Text>
          </div>
        </Card>
      )}
    </div>
  );
}

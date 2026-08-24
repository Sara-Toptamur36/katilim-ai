import { Card, Typography, Tag, Progress, Alert } from "antd";

// Yanit guven skoru bu esigin altindaysa cevabin ustunde acik bir uyari
// gosterilir. Cevap GIZLENMEZ, kaynaklar da gizlenmez - yanina isaret
// konur (README ilke 1: "filtrelemek yerine isaretlemek").
//
// Esik neden 0,5: asagidaki Progress zaten 0,5 altini "exception" (kirmizi)
// olarak boyuyordu, ama kirmizi bir cubuk tek basina ne demek oldugunu
// soylemiyordu. Olculdu: menu metninden gelen alakasiz kaynaklarda skor
// 0,08-0,17 araliginda kaliyor, gercek kampanya eslesmelerinde 0,57 ve
// uzerine cikiyor - esik bu iki kumeyi ayiriyor.
const DUSUK_GUVEN_ESIGI = 0.5;
import EvidenceCard from "./EvidenceCard";
import DecisionTrace from "./DecisionTrace";


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

      {!kullaniciMi &&
        mesaj.confidence != null &&
        !mesaj.streaming &&
        !mesaj.hata &&
        mesaj.confidence < DUSUK_GUVEN_ESIGI && (
          <Alert
            type="warning"
            title="Bu yanıtın kaynak eşleşmesi zayıf"
            description="Bulunan kaynaklar soruyla düşük oranda örtüşüyor; yanıt bir kampanya metni yerine sayfa menüsünden gelmiş olabilir. Aşağıdaki kaynaklara bakmadan bu yanıta dayanmayın."
            showIcon
            style={{ marginTop: 8, maxWidth: 520 }}
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
            <EvidenceCard key={i} kaynak={k} />
          ))}
          <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px dashed var(--kenarlik)" }}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              ℹ️ Alıntılar kaynak sayfadan <strong>birebir</strong> alınmıştır; sistem bu metnin üzerine cümle üretmez.
            </Typography.Text>
          </div>
        </Card>
      )}

      {/* Karar zinciri (Audit) butonu — sadece bot yanıtlarında */}
      {!kullaniciMi && mesaj.auditHam && !mesaj.streaming && !mesaj.hata && (
        <div style={{ marginTop: 6 }}>
          <DecisionTrace audit={mesaj.auditHam} soru={mesaj.soruMetni} />
        </div>
      )}
    </div>
  );
}

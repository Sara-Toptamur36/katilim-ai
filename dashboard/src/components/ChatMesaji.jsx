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
import SonucBaslik from "./sohbet/SonucBaslik";
import HesaplamaKarti from "./sohbet/HesaplamaKarti";
import KampanyaKarti from "./sohbet/KampanyaKarti";
import KarsilastirmaTablosu from "./sohbet/KarsilastirmaTablosu";
import SonrakiAdimlar from "./sohbet/SonrakiAdimlar";
import {
  kisaSonucCikar,
  kalanAciklamaCikar,
  hesaplamaOnekiCikar,
  kampanyalariGrupla,
  dogrulamaDurumMeta,
  dogrulanamayanAlanEtiketleri,
  sureMetni,
} from "../utils/cevapBicimlendirme";


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

// Bu mesaj icin "SONUÇ" ustbaslığı ile yapilandirilmis govde (kampanya
// kartlari / karsilastirma tablosu / hesaplama karti) gosterilsin mi?
// Kullanici mesajlarinda, hata/cekimserlik/streaming durumunda HAYIR -
// oralarda ham metin zaten dogru gosterimdir.
function yapilandirilmisGovdeUygunMu(mesaj, kullaniciMi) {
  return !kullaniciMi && !mesaj.streaming && !mesaj.hata && !mesaj.fallback;
}

// RAG araci basarili oldugunda cevap metni, kaynak parcalarinin BIREBIR
// numaralanmis kopyasidir ("Kaynaklarda bulduklarim:\n1. ...\n2. ...",
// bkz. agent/router.py::rag_aracini_cagir). Bu metni SONUÇ satirinda
// oldugu gibi basmak, asagidaki kampanya kartlarinda/Kaynaklar bolumunde
// GOSTERILECEK olan ayni metni tekrar etmek anlamina gelirdi - bu yuzden
// RAG yolunda SONUÇ icin sabit, kisa bir baslik kullanilir; asil icerik
// yapilandirilmis kartlarda ve Kaynaklar bolumunde gosterilir.
// dogrulama.durum RAG/kampanya aramasinda VAR OLAN bir veridir (verifier
// zaten calisiyor, bkz. validation/yanit_dogrulama.py) ama daha once SONUÇ
// satirina hic yansimiyordu - kullanici "Bulunan seçenekler:" gibi sabit,
// bilgisiz bir baslikla karsilasiyordu. Burada kaynaktaki SAYILARI degil,
// yalnizca yapisal gercekleri (kac kayit, dogrulama durumu) cumleye doker.
function ragSonucBasligi(kampanyaSayisi, dogrulamaDurumu) {
  if (kampanyaSayisi === 0) return "Kaynaklarda bulunan bilgiler:";
  const adet = kampanyaSayisi >= 2 ? `${kampanyaSayisi} kampanya` : "1 kampanya";
  if (dogrulamaDurumu === "kismi") {
    return `Sorgunuzla birebir eşleşen, doğrulanmış bir teklif bulunamadı. İlgili ${adet} listelendi.`;
  }
  if (dogrulamaDurumu === "dogrulandi") {
    return `Sorgunuzla eşleşen, kaynakta doğrulanmış ${adet} bulundu:`;
  }
  return `Sorgunuzla ilgili ${adet} bulundu:`;
}

function GovdeIcerigi({ mesaj, kampanyalar }) {
  const arac = mesaj.cagrilanArac;
  const dogrulama = mesaj.auditHam?.dogrulama ?? null;

  let kisaSonuc = null;
  let kalanAciklama = null;

  if (arac === "rag") {
    kisaSonuc = ragSonucBasligi(kampanyalar.length, dogrulama?.durum);
  } else if (arac === "calculator") {
    // Hesaplama karti sayilari zaten yapilandirilmis gosterir; ustte
    // yalnizca kart URETMEDEN once gelen bir on-metin varsa (ornek:
    // terminoloji yonlendirme cumlesi) gosterilir - ayni cumle iki kez
    // basilmasin diye asil hesaplama cumlesi burada TEKRARLANMAZ.
    kisaSonuc = hesaplamaOnekiCikar(mesaj.metin);
  } else {
    kisaSonuc = kisaSonucCikar(mesaj.metin);
    kalanAciklama = kalanAciklamaCikar(mesaj.metin, kisaSonuc);
  }

  const dogrulanamayanlar = dogrulanamayanAlanEtiketleri(dogrulama);

  // Kucuk sonuc kumelerinde (<=3) hem tek tek kart hem karsilastirma
  // tablosu birlikte gosterilir - kart detayi, tablo taranabilirligi
  // saglar. Daha kalabalik sonuclarda yalnizca tablo gosterilir, aksi
  // halde kart yigini kaydirma yorgunlugu yaratir.
  const kartGoster = arac !== "calculator" && kampanyalar.length >= 1 && kampanyalar.length <= 3;
  const tabloGoster = arac !== "calculator" && kampanyalar.length >= 2;

  return (
    <>
      <div className="sohbet-asistan-etiket">KatılımAI</div>
      <SonucBaslik
        kisaSonuc={kisaSonuc}
        aciklama={kalanAciklama}
        durumRozetesi={dogrulamaDurumMeta(dogrulama)}
        sure={sureMetni(mesaj.auditHam?.latency_ms)}
      />

      {/* Sabit, veri UYETMEYEN bir kullanim ipucu - yalnizca incelenecek
          kampanya oldugunda gosterilir. Hicbir sayi/iddia icermez. */}
      {(kartGoster || tabloGoster) && (
        <div className="sonuc-ipucu-not">
          💡 Daha net bir karşılaştırma için kampanyaları inceleyebilir veya finansman hesabı yapabilirsiniz.
        </div>
      )}

      {arac === "calculator" && <HesaplamaKarti cevapMetni={mesaj.metin} />}

      {kartGoster && (
        <>
          {kampanyalar.length > 1 && (
            <div className="sohbet-alt-baslik">Önerilen Kampanyalar</div>
          )}
          {kampanyalar.map((k, i) => (
            <KampanyaKarti key={i} kampanya={k} />
          ))}
        </>
      )}

      {/* ADIM 4 - belirsizlik uyarisi: cevapta gecen sayilarin HANGILERI
          kaynakta dogrulanamadi acikca soylenir; hicbir alan "dogru gibi"
          gosterilmez. Veri audit.dogrulama.alanlar'dan gelir, uydurulmaz. */}
      {dogrulanamayanlar.length > 0 && (
        <div className="sonuc-dogrulanamayan-not">
          Not: {dogrulanamayanlar.join(", ")} bilgisi kaynaklarda doğrulanamamıştır.
        </div>
      )}

      {tabloGoster && (
        <>
          <div className="sohbet-alt-baslik">Karşılaştırma Tablosu</div>
          <KarsilastirmaTablosu kampanyalar={kampanyalar} />
        </>
      )}

      {(kartGoster || tabloGoster) && <SonrakiAdimlar />}
    </>
  );
}

export default function ChatMesaji({ mesaj }) {
  const kullaniciMi = mesaj.rol === "kullanici";
  const durum = kullaniciMi ? null : terminolojiDurumu(mesaj);
  const yapilandirilmisGoster = yapilandirilmisGovdeUygunMu(mesaj, kullaniciMi);
  const kampanyalar = yapilandirilmisGoster ? kampanyalariGrupla(mesaj.kaynaklar) : [];

  return (
    <div style={{ marginBottom: 16 }}>
      {yapilandirilmisGoster ? (
        <GovdeIcerigi mesaj={mesaj} kampanyalar={kampanyalar} />
      ) : (
        <div>
          <strong>{kullaniciMi ? "Siz:" : "KatılımAI:"}</strong>{" "}
          {mesaj.metin}
          {mesaj.streaming && <span>▍</span>}
        </div>
      )}

      {/* CEKIMSERLIK (abstention) - projenin juriye anlatilan ana mesaji:
          "bilmiyorum diyebilen sistem". Bu yuzden kucuk bir uyari degil,
          belirgin bir kart olarak gosterilir.

          PROP NOTU: antd v6'da Alert basligi `title` ile verilir, `message`
          ile DEGIL. Burasi `message` kullaniyordu, bu yuzden baslik hic
          ekrana basilmiyordu - kullanici yalnizca aciklama metnini
          goruyordu ve bunun bilincli bir karar oldugu anlasilmiyordu. */}
      {mesaj.fallback && (
        <Alert
          type="warning"
          title="Güvenli Başarısızlık — Yanıt Üretilmedi"
          description={
            <>
              <strong>Bu bir hata değil, bilinçli bir güvenlik kararıdır.</strong>
              <br />
              Soruyu yanıtlayacak yeterli kaynak bulunamadı. Sistem, uydurma
              bilgi vermektense cevap vermemeyi tercih etti.
              <br />
              <span style={{ fontSize: 12, opacity: 0.8 }}>
                Soruyu farklı kelimelerle sorabilir ya da mevcut kampanya
                koşullarını sorabilirsiniz.
              </span>
            </>
          }
          showIcon
          style={{ marginTop: 8, maxWidth: 520 }}
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
        !mesaj.fallback &&
        mesaj.confidence < DUSUK_GUVEN_ESIGI && (
          <Alert
            type="warning"
            title="Bu yanıtın kaynak eşleşmesi zayıf"
            description="Bulunan kaynaklar soruyla düşük oranda örtüşüyor; yanıt bir kampanya metni yerine sayfa menüsünden gelmiş olabilir. Aşağıdaki kaynaklara bakmadan bu yanıta dayanmayın."
            showIcon
            style={{ marginTop: 8, maxWidth: 520 }}
          />
        )}

      {/* Cekimserlikte guven cubugu GOSTERILMEZ: fallback yanitta confidence
          her zaman 0 doner ve "%0 guven" kirmizi bir cubuk, sistemin basarisiz
          oldugu izlenimi verir. Oysa cevap uretmemek burada dogru davranistir.
          Yukaridaki "Guvenli Basarisizlik" karti zaten durumu anlatiyor. */}
      {!kullaniciMi &&
        mesaj.confidence != null &&
        !mesaj.streaming &&
        !mesaj.hata &&
        !mesaj.fallback && (
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

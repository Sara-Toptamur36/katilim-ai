import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Alert } from "antd";
import {
  RobotOutlined,
  SwapOutlined,
  AuditOutlined,
} from "@ant-design/icons";
import client from "../api/client";
import {
  OLCUMLER,
  OLCUM_TARIHI,
  VERI_TARIHI,
  SISTEM_DURUMU,
  KAYNAK_TAKIP,
} from "../data/olcumler";
import TazelikSeridi from "../components/TazelikSeridi";
import { useCanliVeriOzet } from "../hooks/useCanliVeriOzet";

export default function Dashboard() {
  const [apiBagli, setApiBagli] = useState(false);
  const [kontrolEdildi, setKontrolEdildi] = useState(false);

  // API sağlık kontrolü
  useEffect(() => {
    client
      .get("/")
      .then(() => setApiBagli(true))
      .catch(() => setApiBagli(false))
      .finally(() => setKontrolEdildi(true));
  }, []);

  // Canlı hacim/dağılım verisi - Jüri Audit Paneli'yle PAYLAŞILAN hook.
  // Bkz. hooks/useCanliVeriOzet.js: iki sayfa da aynı /sistem/tazelik ve
  // /kampanyalar çağrısından türetilen sayıları gösterir, kopya hesaplama
  // yok.
  const {
    tekilKampanya,
    anlikGoruntu,
    ragParca,
    ragBelge,
    urunAilesi,
    alanDolulugu,
    urunAilesiToplam,
    alanDolulukToplam,
    bankaDagilimi,
    enBuyukBankaTekil,
    baskinBankalar,
    baskinYuzde,
    zayifBankalar,
  } = useCanliVeriOzet();

  return (
    <div
      style={{
        maxWidth: 1560,
        margin: "0 auto",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      {/* Sayfaya ve Drawer'lara özel stiller */}
      <style>{`
        .hero-buton {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          height: 40px;
          padding: 0 20px;
          border-radius: 8px;
          background: #169276;
          border: none;
          color: #ffffff;
          font-weight: 600;
          font-size: 13.5px;
          text-decoration: none;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
          transition: all 150ms ease;
          box-sizing: border-box;
          cursor: pointer;
        }
        .hero-buton:hover {
          background: #0c765f !important;
          color: #ffffff !important;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.26) !important;
        }
        .hero-buton:active {
          background: #0c6653 !important;
        }

        /* AI Asistanı Aç butonu — altın vurgu */
        .hero-buton-altin {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          height: 40px;
          padding: 0 20px;
          border-radius: 8px;
          background: #d4a34b;
          border: none;
          color: #1a1408;
          font-weight: 650;
          font-size: 13.5px;
          text-decoration: none;
          box-shadow: 0 2px 10px rgba(212,163,75,0.32);
          transition: all 150ms ease;
          box-sizing: border-box;
          cursor: pointer;
        }
        .hero-buton-altin:hover {
          background: #c08f38 !important;
          color: #1a1408 !important;
          box-shadow: 0 4px 14px rgba(212,163,75,0.40) !important;
        }
        .hero-buton-altin:active {
          background: #b38432 !important;
        }

        /* 1400px altında hero paneli sağ kutuları tek sıra 4'lü */
        @media (max-width: 1400px) {
          .hero-kapsayici {
            grid-template-columns: 1fr !important;
            gap: 20px !important;
          }
          .hero-sag-grid {
            grid-template-columns: repeat(4, 1fr) !important;
            gap: 10px !important;
          }
          .hero-sag-kutu {
            padding: 12px !important;
          }
          .hero-sag-deger {
            font-size: 17px !important;
          }
        }

        /* 900px altında hero paneli sağ kutuları 2x2 */
        @media (max-width: 900px) {
          .hero-sag-grid {
            grid-template-columns: repeat(2, 1fr) !important;
          }
        }

        /* Sayı kutuları responsive düzeni */
        @media (max-width: 1000px) {
          .sayi-kutulari-grid {
            grid-template-columns: repeat(2, 1fr) !important;
          }
        }
        @media (max-width: 640px) {
          .sayi-kutulari-grid {
            grid-template-columns: 1fr !important;
          }
          .hero-sag-grid {
            grid-template-columns: 1fr !important;
          }
          .olcum-tarih-metni {
            width: 100%;
            text-align: right;
            margin-top: 4px;
          }
        }

        /* İki sütunlu grafik ızgarası */
        .grafik-izgarasi {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
        }
        @media (max-width: 1200px) {
          .grafik-izgarasi {
            grid-template-columns: 1fr !important;
          }
        }

        /* Halka grafik lejant satırı */
        .halka-lejant-satir {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 12.5px;
          line-height: 1.3;
          padding: 4px 0;
        }
        .halka-lejant-kare {
          width: 10px;
          height: 10px;
          border-radius: 2px;
          flex-shrink: 0;
        }
        .halka-lejant-ad {
          flex: 1;
          color: var(--yazi-normal);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .halka-lejant-sayi {
          font-weight: 650;
          color: var(--yazi-koyu);
          min-width: 28px;
          text-align: right;
        }
        .halka-lejant-yuzde {
          color: var(--yazi-soluk);
          font-size: 11.5px;
          min-width: 42px;
          text-align: right;
        }

        /* Yatay çubuk grafik satırı */
        .cubuk-satir {
          display: grid;
          grid-template-columns: 150px 1fr 36px;
          align-items: center;
          gap: 10px;
        }
        .cubuk-banka-adi {
          font-size: 12.5px;
          color: var(--yazi-koyu);
          font-weight: 500;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .cubuk-arka {
          width: 100%;
          height: 10px;
          background: var(--kenarlik);
          border-radius: 5px;
          overflow: hidden;
        }
        .cubuk-dolu {
          height: 100%;
          background: var(--marka-500);
          border-radius: 5px;
          transition: width 0.5s ease;
        }
        .cubuk-deger {
          font-size: 12.5px;
          font-weight: 650;
          color: var(--yazi-koyu);
          text-align: right;
        }

        /* Taranan Kaynaklar kartı stilleri */
        .kaynak-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px 20px;
        }
        @media (max-width: 900px) {
          .kaynak-grid {
            grid-template-columns: 1fr !important;
          }
        }
        .kaynak-url-link {
          font-size: 11px;
          color: var(--yazi-soluk);
          text-decoration: none;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          display: block;
          transition: color 150ms ease;
        }
        .kaynak-url-link:hover {
          text-decoration: underline;
          color: var(--marka-500) !important;
        }
      `}</style>

      {/* ========================================================
          1) TANITIM PANELİ (HERO)
          ======================================================== */}
      <div
        className="hero-kapsayici"
        style={{
          background: "linear-gradient(135deg, #0b4037 0%, #082f29 100%)",
          borderRadius: 16,
          padding: 24,
          color: "#ffffff",
          display: "grid",
          gridTemplateColumns: "1.2fr 1fr",
          gap: 24,
          alignItems: "center",
          boxShadow: "0 4px 18px rgba(8, 47, 41, 0.35)",
        }}
      >
        {/* Sol Taraf: Başlık, Açıklama ve Butonlar */}
        <div style={{ display: "flex", flexDirection: "column" }}>
          <span
            style={{
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.12em",
              color: "#7bcbb6",
              textTransform: "uppercase",
              marginBottom: 6,
            }}
          >
            ANA KONTROL MERKEZİ
          </span>

          <h1
            style={{
              fontSize: 24,
              fontWeight: 650,
              color: "#ffffff",
              lineHeight: 1.25,
              margin: "0 0 4px 0",
              letterSpacing: "-0.01em",
            }}
          >
            Katılım bankacılığı verisini güvenilir, karşılaştırılabilir ve
            denetlenebilir kararlara dönüştürün.
          </h1>

          <p
            style={{
              fontSize: 13.5,
              lineHeight: 1.55,
              color: "rgba(255, 255, 255, 0.72)",
              maxWidth: 720,
              margin: "10px 0 18px 0",
            }}
          >
            Katılım bankacılığı verisini ve toplanan kampanya kapsamını tek
            ekrandan izleyin. Eksik veri görünür kalır; model kalite ölçümleri,
            veri kaynağı detayları ve her yanıtın audit izi Jüri Audit
            Paneli'nde takip edilir.
          </p>

          {/* 3 Dolu Yeşil Buton */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
            <Link to="/chatbot" className="hero-buton-altin">
              <RobotOutlined /> AI Asistanı Aç
            </Link>

            <Link to="/karsilastirma" className="hero-buton">
              <SwapOutlined /> Karşılaştırma Başlat
            </Link>

            <Link to="/audit" className="hero-buton">
              <AuditOutlined /> Audit İzini İncele
            </Link>
          </div>
        </div>

        {/* Sağ Taraf: 4 Küçük Bilgi Kutusu */}
        <div
          className="hero-sag-grid"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, 1fr)",
            gap: 12,
          }}
        >
          {/* Kutu 1: Sistem Durumu */}
          <div
            className="hero-sag-kutu"
            style={{
              background: "rgba(255, 255, 255, 0.07)",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: 12,
              padding: 14,
              display: "flex",
              flexDirection: "column",
            }}
          >
            <span
              style={{
                fontSize: 10,
                letterSpacing: "0.1em",
                color: "rgba(255, 255, 255, 0.55)",
                textTransform: "uppercase",
                marginBottom: 3,
              }}
            >
              SİSTEM DURUMU
            </span>
            <span
              className="hero-sag-deger"
              style={{
                fontSize: 19,
                fontWeight: 600,
                color: apiBagli ? "#7bcbb6" : "#f0a0a0",
              }}
            >
              {apiBagli ? "Sağlıklı" : "Bağlantı yok"}
            </span>
          </div>

          {/* Kutu 2: Veri Modu */}
          <div
            className="hero-sag-kutu"
            style={{
              background: "rgba(255, 255, 255, 0.07)",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: 12,
              padding: 14,
              display: "flex",
              flexDirection: "column",
            }}
          >
            <span
              style={{
                fontSize: 10,
                letterSpacing: "0.1em",
                color: "rgba(255, 255, 255, 0.55)",
                textTransform: "uppercase",
                marginBottom: 3,
              }}
            >
              VERİ MODU
            </span>
            <span
              className="hero-sag-deger"
              style={{
                fontSize: 19,
                fontWeight: 600,
                color: apiBagli ? "#ffffff" : "rgba(255, 255, 255, 0.4)",
              }}
            >
              {apiBagli ? "PostgreSQL" : "—"}
            </span>
            {!apiBagli && (
              <span
                style={{
                  fontSize: 11,
                  color: "rgba(255, 255, 255, 0.5)",
                  marginTop: 1,
                }}
              >
                API kapalı
              </span>
            )}
          </div>

          {/* Kutu 3: RAG İndeksi */}
          <div
            className="hero-sag-kutu"
            style={{
              background: "rgba(255, 255, 255, 0.07)",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: 12,
              padding: 14,
              display: "flex",
              flexDirection: "column",
            }}
            title={`Bu, Recall@5'in ölçüldüğü indekstir (${OLCUMLER.rag.indeksTarihi} tarihli, ${OLCUMLER.rag.indekslenenParca} parça) — Sistem Sağlığı kartındaki "Canlı RAG İndeksi" ile bilerek farklıdır, çünkü Recall o indekste henüz yeniden ölçülmedi.`}
          >
            <span
              style={{
                fontSize: 10,
                letterSpacing: "0.1em",
                color: "rgba(255, 255, 255, 0.55)",
                textTransform: "uppercase",
                marginBottom: 3,
              }}
            >
              {/* ETIKET AYRIMI: burasi Recall@5'in OLCULDUGU indekstir.
                  Asagidaki Sistem Sagligi karti CALISAN (canli) indeksi
                  gosterir - ikisi bilerek ayri, Recall yeni indekste
                  yeniden olculmedi. DENETIM BULGUSU (26.08.2026): eskiden
                  bu ayrim yalnizca kod yorumunda vardi, ekranda gorunmuyordu
                  - juri "ÖLÇÜM İNDEKSİ" ile "Canlı RAG İndeksi" farkli sayi
                  gosterince hangisinin yanlis oldugunu soruyordu. Simdi
                  "(Recall)" etiketi + title tooltip + alt metin bunu acikca
                  soyluyor. */}
              ÖLÇÜM İNDEKSİ (Recall)
            </span>
            <span
              className="hero-sag-deger"
              style={{ fontSize: 19, fontWeight: 600, color: "#ffffff" }}
            >
              {OLCUMLER.rag.indekslenenParca} parça
            </span>
            <span
              style={{
                fontSize: 11,
                color: "rgba(255, 255, 255, 0.5)",
                marginTop: 1,
              }}
            >
              {OLCUMLER.rag.indeksTarihi} ölçümü · canlı indeks {ragParca} parça
            </span>
          </div>

          {/* Kutu 4: Gold Veri Seti */}
          <div
            className="hero-sag-kutu"
            style={{
              background: "rgba(255, 255, 255, 0.07)",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: 12,
              padding: 14,
              display: "flex",
              flexDirection: "column",
            }}
          >
            <span
              style={{
                fontSize: 10,
                letterSpacing: "0.1em",
                color: "rgba(255, 255, 255, 0.55)",
                textTransform: "uppercase",
                marginBottom: 3,
              }}
            >
              GOLD VERİ SETİ
            </span>
            <span
              className="hero-sag-deger"
              style={{ fontSize: 19, fontWeight: 600, color: "#ffffff" }}
            >
              {OLCUMLER.veri.goldKayit} kayıt
            </span>
            <span
              style={{
                fontSize: 11,
                color: "rgba(255, 255, 255, 0.5)",
                marginTop: 1,
              }}
            >
              elle doğrulanmış
            </span>
          </div>
        </div>
      </div>

      {/* ========================================================
          2) ETİKET SATIRI (PILL ROW) + SAĞA YASLI ÖLÇÜM TARİHİ
          ======================================================== */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        {/* Sol taraftaki hap etiketler */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 8,
          }}
        >
          {/* 1. Veri modu etiketi */}
          <div
            style={{
              height: 28,
              borderRadius: 14,
              padding: "0 12px",
              fontSize: 12,
              fontWeight: 600,
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              background: "var(--kart)",
              border: "1px solid var(--kenarlik)",
              color: "var(--yazi-koyu)",
            }}
          >
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: "50%",
                background: apiBagli ? "#3fb296" : "#c94f4f",
              }}
            />
            {apiBagli ? "Canlı veri" : "Bağlantı yok"}
          </div>

          {/* 2. API Sözleşmesi Uyumlu */}
          <div
            style={{
              height: 28,
              borderRadius: 14,
              padding: "0 12px",
              fontSize: 12,
              fontWeight: 600,
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              background: "var(--kart)",
              border: "1px solid var(--kenarlik)",
              color: "var(--yazi-koyu)",
            }}
          >
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: "50%",
                background: "#3fb296",
              }}
            />
            API sözleşmesi uyumlu
          </div>
        </div>

        {/* Sağ tarafta ölçüm tarihi — Sağa Yaslı */}
        <div
          className="olcum-tarih-metni"
          style={{
            fontSize: 12,
            color: "var(--yazi-soluk)",
            marginLeft: "auto",
            whiteSpace: "nowrap",
          }}
        >
          <span>Veri: {VERI_TARIHI}</span>
          <span style={{ margin: "0 6px", opacity: 0.5 }}>·</span>
          <span>Ölçüm: {OLCUM_TARIHI}</span>
        </div>
      </div>

      {/* ========================================================
          3) SAKİN HATA / BİLGİLENDİRME UYARISI
          ======================================================== */}
      {kontrolEdildi && !apiBagli && (
        <Alert
          type="info"
          title="API bağlantısı yok - veriler gösterilemiyor"
          description="Yerel sunucu çalışmıyor. Ölçüm değerleri 18 Ağustos 2026 tarihli kayıtlardan gösteriliyor."
          showIcon
          closable
        />
      )}

      {/* ========================================================
          4) SAYI KUTULARI (4 ADET METRİK KARTI)
          ======================================================== */}
      <div
        className="sayi-kutulari-grid"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 16,
        }}
      >
        {/* Kutu 1: Veri — üst yeşil çizgi */}
        <div
          style={{
            background: "var(--kart)",
            border: "1px solid var(--kenarlik)",
            borderTop: "3px solid #0c765f",
            borderRadius: 12,
            padding: 20,
            display: "flex",
            flexDirection: "column",
            position: "relative",
          }}
        >
          <span
            style={{
              position: "absolute",
              top: 16,
              right: 16,
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: "0.08em",
              color: "#0c765f",
              textTransform: "uppercase",
            }}
          >
            VERİ
          </span>
          <span
            style={{
              fontSize: 32,
              fontWeight: 650,
              color: "var(--yazi-koyu)",
              lineHeight: 1.2,
              marginTop: 4,
            }}
          >
            {tekilKampanya}
          </span>
          <span
            style={{
              fontSize: 13,
              color: "var(--yazi-normal)",
              marginTop: 6,
              fontWeight: 500,
            }}
          >
            Taranan kampanya sayfası
          </span>
          {/* DENETIM BULGUSU (26.08.2026): bu sayi (tekilKampanya, /sistem/
              tazelik'ten - scraper/raw_data'daki TUM benzersiz URL, scraper
              hicbir eski dosyayi SILMIYOR) ile asagidaki "Kampanya Turu
              Dagilimi" grafiginin toplami (urunAilesiToplam, /kampanyalar'dan -
              yalnizca yapilandirilmis kayda donusturulup Postgres'e YAZILMIS
              olanlar) farkli sorulara cevap veriyor. Aradaki fark, henuz
              islenmemis veya ayiklama sirasinda elenmis ham sayfalardir -
              hata degil. Etiketsiz oldugunda ayni ekranda iki celisen sayi
              gibi gorunuyordu - simdi ikisi de acikca adlandiriliyor. */}
          <span
            style={{
              fontSize: 11,
              color: "var(--yazi-soluk)",
              marginTop: 4,
            }}
            title="Taranan kampanya sayfası: scraper/raw_data'daki tüm benzersiz URL (eski taramalar silinmez). Aşağıdaki grafikteki sayı ise yalnızca yapılandırılmış kayda dönüştürülüp veritabanına yazılmış olanlardır."
          >
            {urunAilesiToplam} kaydı veritabanında işlenmiş · {anlikGoruntu} anlık görüntü
          </span>
        </div>

        {/* Kutu 2: Kapsam — üst yeşil çizgi */}
        <div
          style={{
            background: "var(--kart)",
            border: "1px solid var(--kenarlik)",
            borderTop: "3px solid #0c765f",
            borderRadius: 12,
            padding: 20,
            display: "flex",
            flexDirection: "column",
            position: "relative",
          }}
        >
          <span
            style={{
              position: "absolute",
              top: 16,
              right: 16,
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: "0.08em",
              color: "#0c765f",
              textTransform: "uppercase",
            }}
          >
            KAPSAM
          </span>
          <span
            style={{
              fontSize: 32,
              fontWeight: 650,
              color: "var(--yazi-koyu)",
              lineHeight: 1.2,
              marginTop: 4,
            }}
          >
            {OLCUMLER.veri.kapsananBanka} / {OLCUMLER.veri.toplamBanka}
          </span>
          <span
            style={{
              fontSize: 13,
              color: "var(--yazi-normal)",
              marginTop: 6,
              fontWeight: 500,
            }}
          >
            Kapsanan katılım bankası
          </span>
          <span
            style={{
              fontSize: 11,
              color: "var(--yazi-soluk)",
              marginTop: 4,
            }}
          >
            {OLCUMLER.veri.haricBanka} kampanya yayını yapmıyor
          </span>
        </div>

        {/* Kutu 3: Çıkarım Ölçümü — üst altın çizgi */}
        <div
          style={{
            background: "var(--kart)",
            border: "1px solid var(--kenarlik)",
            borderTop: "3px solid #d4a34b",
            borderRadius: 12,
            padding: 20,
            display: "flex",
            flexDirection: "column",
            position: "relative",
          }}
        >
          <span
            style={{
              position: "absolute",
              top: 16,
              right: 16,
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: "0.08em",
              color: "#b8873a",
              textTransform: "uppercase",
            }}
          >
            ÖLÇÜM
          </span>
          <span
            style={{
              fontSize: 32,
              fontWeight: 650,
              color: "var(--yazi-koyu)",
              lineHeight: 1.2,
              marginTop: 4,
            }}
          >
            %{OLCUMLER.cikarim.makroF1.toString().replace(".", ",")}
          </span>
          <span
            style={{
              fontSize: 13,
              color: "var(--yazi-normal)",
              marginTop: 6,
              fontWeight: 500,
            }}
          >
            Alan bazlı makro F1
          </span>
          <span
            style={{
              fontSize: 11,
              color: "var(--yazi-soluk)",
              marginTop: 4,
            }}
          >
            {OLCUMLER.cikarim.makroF1Detay}
          </span>
        </div>

        {/* Kutu 4: RAG Ölçümü — üst altın çizgi */}
        <div
          style={{
            background: "var(--kart)",
            border: "1px solid var(--kenarlik)",
            borderTop: "3px solid #d4a34b",
            borderRadius: 12,
            padding: 20,
            display: "flex",
            flexDirection: "column",
            position: "relative",
          }}
        >
          <span
            style={{
              position: "absolute",
              top: 16,
              right: 16,
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: "0.08em",
              color: "#b8873a",
              textTransform: "uppercase",
            }}
          >
            ÖLÇÜM
          </span>
          <span
            style={{
              fontSize: 32,
              fontWeight: 650,
              color: "var(--yazi-koyu)",
              lineHeight: 1.2,
              marginTop: 4,
            }}
          >
            %{OLCUMLER.rag.recall5.toString().replace(".", ",")}
          </span>
          <span
            style={{
              fontSize: 13,
              color: "var(--yazi-normal)",
              marginTop: 6,
              fontWeight: 500,
            }}
          >
            RAG Recall@5
          </span>
          <span
            style={{
              fontSize: 11,
              color: "var(--yazi-soluk)",
              marginTop: 4,
            }}
          >
            {OLCUMLER.rag.recall5Detay} · indeks{" "}
            {OLCUMLER.rag.indeksTarihi.replace(" 2026", "")}
          </span>
        </div>
      </div>

      {/* ========================================================
          5) İKİ SÜTUNLU GRAFİK IZGARASI
          ======================================================== */}
      {(() => {
        /* -- Halka grafik verileri -- */
        /* Sıcak renk paleti: koyu yeşil, gri (eksik veri), altın, turuncu, açık yeşil, bej */
        const halkaRenkler = ["#0c6653", "#b9bdb6", "#d4a34b", "#d97736", "#3fb296", "#d8c48c"];
        const ilkBes = urunAilesi.slice(0, 5);
        const kalanlar = urunAilesi.slice(5);
        const digerToplam = kalanlar.reduce((t, u) => t + u.sayi, 0);
        const halkaDilimler = [
          ...ilkBes.map((u, i) => ({ ad: u.ad, sayi: u.sayi, renk: halkaRenkler[i] })),
          { ad: "Diğer", sayi: digerToplam, renk: halkaRenkler[5] },
        ];
        const toplam = urunAilesiToplam;
        const yaricap = 74;
        const kalinlik = 26;
        const merkez = 100;

        /* stroke-dasharray/offset hesaplama (SVG çember) */
        const cevre = 2 * Math.PI * yaricap;
        let toplamOffset = 0;
        const svgDilimler = halkaDilimler.map((d) => {
          const oran = d.sayi / toplam;
          const uzunluk = cevre * oran;
          const bosluk = cevre - uzunluk;
          const offset = -toplamOffset;
          toplamOffset += uzunluk;
          return { ...d, dasharray: `${uzunluk} ${bosluk}`, dashoffset: offset };
        });

        /* -- Çubuk grafik verileri -- */
        const enBuyuk = enBuyukBankaTekil;

        return (
          <div className="grafik-izgarasi">
            {/* SOL KART — Kampanya Türü Dağılımı (Halka Grafik) */}
            <div
              style={{
                background: "var(--kart)",
                border: "1px solid var(--kenarlik)",
                borderRadius: 14,
                padding: 20,
                boxShadow: "var(--golge-kart)",
              }}
            >
              {/* Başlık bloğu */}
              <div style={{ marginBottom: 18 }}>
                <div
                  style={{
                    fontSize: 15,
                    fontWeight: 650,
                    color: "var(--yazi-koyu)",
                  }}
                >
                  Kampanya Türü Dağılımı
                </div>
                <div
                  style={{
                    fontSize: 12,
                    color: "var(--yazi-soluk)",
                    marginTop: 2,
                  }}
                >
                  {urunAilesiToplam} kampanyanın ürün ailesine göre dağılımı
                </div>
              </div>

              {/* İçerik: Halka + Lejant yan yana */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 24,
                  flexWrap: "wrap",
                }}
              >
                {/* SVG Halka Grafik */}
                <div style={{ position: "relative", flexShrink: 0 }}>
                  <svg
                    viewBox="0 0 200 200"
                    width={160}
                    height={160}
                    style={{ transform: "rotate(-90deg)" }}
                  >
                    {svgDilimler.map((d, i) => (
                      <circle
                        key={i}
                        cx={merkez}
                        cy={merkez}
                        r={yaricap}
                        fill="none"
                        stroke={d.renk}
                        strokeWidth={kalinlik}
                        strokeDasharray={d.dasharray}
                        strokeDashoffset={d.dashoffset}
                        strokeLinecap="butt"
                      />
                    ))}
                  </svg>
                  {/* Ortadaki sayı */}
                  <div
                    style={{
                      position: "absolute",
                      top: "50%",
                      left: "50%",
                      transform: "translate(-50%, -50%)",
                      textAlign: "center",
                    }}
                  >
                    <div
                      style={{
                        fontSize: 28,
                        fontWeight: 700,
                        color: "var(--yazi-koyu)",
                        lineHeight: 1,
                      }}
                    >
                      {urunAilesiToplam}
                    </div>
                    <div
                      style={{
                        fontSize: 11,
                        color: "var(--yazi-soluk)",
                        marginTop: 2,
                      }}
                    >
                      kampanya
                    </div>
                  </div>
                </div>

                {/* Lejant listesi */}
                <div style={{ flex: 1, minWidth: 180 }}>
                  {halkaDilimler.map((d) => {
                    const yuzde = ((d.sayi / toplam) * 100).toFixed(1).replace(".", ",");
                    return (
                      <div className="halka-lejant-satir" key={d.ad}>
                        <span
                          className="halka-lejant-kare"
                          style={{ background: d.renk }}
                        />
                        <span className="halka-lejant-ad">{d.ad}</span>
                        <span className="halka-lejant-sayi">{d.sayi}</span>
                        <span className="halka-lejant-yuzde">%{yuzde}</span>
                      </div>
                    );
                  })}
                  {/* Gri dilim açıklama notu */}
                  <div
                    style={{
                      fontSize: 11,
                      color: "var(--yazi-soluk)",
                      marginTop: 6,
                      lineHeight: 1.4,
                    }}
                  >
                    Gri dilim, ürün ailesi kaynakta belirtilmemiş kampanyaları gösterir.
                  </div>
                </div>
              </div>
            </div>

            {/* SAĞ KART — Banka Bazında Dağılım (Yatay Çubuk) */}
            <div
              style={{
                background: "var(--kart)",
                border: "1px solid var(--kenarlik)",
                borderRadius: 14,
                padding: 20,
                boxShadow: "var(--golge-kart)",
              }}
            >
              {/* Başlık bloğu */}
              <div style={{ marginBottom: 18 }}>
                <div
                  style={{
                    fontSize: 15,
                    fontWeight: 650,
                    color: "var(--yazi-koyu)",
                  }}
                >
                  Banka Bazında Dağılım
                </div>
                <div
                  style={{
                    fontSize: 12,
                    color: "var(--yazi-soluk)",
                    marginTop: 2,
                  }}
                >
                  Tekil kampanya sayısı
                </div>
              </div>

              {/* Çubuk grafik satırları */}
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {bankaDagilimi.map((b) => {
                  const yuzde = (b.tekil / enBuyuk) * 100;
                  /* Baskın iki banka altın, diğerleri yeşil */
                  const baskinMi = baskinBankalar.includes(b.banka);
                  return (
                    <div className="cubuk-satir" key={b.banka}>
                      <span className="cubuk-banka-adi">{b.banka}</span>
                      <div className="cubuk-arka">
                        <div
                          className="cubuk-dolu"
                          style={{
                            width: `${yuzde}%`,
                            background: baskinMi ? "#d4a34b" : undefined,
                          }}
                        />
                      </div>
                      <span className="cubuk-deger">{b.tekil}</span>
                    </div>
                  );
                })}
              </div>

              {/* Amber uyarı notu */}
              <div
                style={{
                  marginTop: 16,
                  background: "rgba(194, 142, 40, 0.10)",
                  border: "1px solid rgba(194, 142, 40, 0.35)",
                  borderRadius: 8,
                  padding: "8px 12px",
                  fontSize: 11.5,
                  color: "#c28e28",
                  lineHeight: 1.45,
                }}
              >
                Altın renkli iki banka ({baskinBankalar.join(" ve ")}) toplam kampanyaların %{baskinYuzde}'sini oluşturuyor. Diğer uçta {zayifBankalar} kampanya var — bu bir tarama eksikliği değil, bu bankaların o an sitesinde yayında olan kampanya sayısı bu kadardır.
              </div>
            </div>

            {/* SOL KART 2 — Alan Bazında Veri Doluluğu */}
            <div
              style={{
                background: "var(--kart)",
                border: "1px solid var(--kenarlik)",
                borderRadius: 14,
                padding: 20,
                boxShadow: "var(--golge-kart)",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
              }}
            >
              <div>
                {/* Başlık bloğu */}
                <div style={{ marginBottom: 18 }}>
                  <div
                    style={{
                      fontSize: 15,
                      fontWeight: 650,
                      color: "var(--yazi-koyu)",
                    }}
                  >
                    Alan Bazında Veri Doluluğu
                  </div>
                  <div
                    style={{
                      fontSize: 12,
                      color: "var(--yazi-soluk)",
                      marginTop: 2,
                    }}
                  >
                    {/* "kampanya" tek basina belirsizdi: bu sayi
                        veritabanina YUKLENMIS kayit sayisi (/kampanyalar),
                        TazelikSeridi'ndeki "tekil kampanya" ise TARANAN
                        ham sayfa sayisi (scraper/raw_data) - ikisi farkli
                        seyler olcuyor, ikisi de canli ve dogru, sadece
                        etiketsiz aynı kelimeyle celisiyor gorunuyorlardi
                        (denetim bulgusu, 25.08.2026). */}
                    veritabanındaki {alanDolulukToplam} kampanyada hangi alan ne sıklıkta dolu
                  </div>
                </div>

                {/* Doluluk satırları */}
                <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  {alanDolulugu.map((item) => {
                    const yuzdeSayi = (item.dolu / item.toplam) * 100;
                    const yuzdeMetin = yuzdeSayi.toFixed(1).replace(".", ",");
                    let cubukRengi = "#d97736"; // < 15 turuncu
                    if (yuzdeSayi >= 40) {
                      cubukRengi = "#169276"; // >= 40 yeşil
                    } else if (yuzdeSayi >= 15) {
                      cubukRengi = "#d4a34b"; // 15 - 40 altın
                    }

                    return (
                      <div key={item.alan} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                          <span style={{ fontSize: 13, fontWeight: 500, color: "var(--yazi-koyu)" }}>
                            {item.alan}
                          </span>
                          <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
                            <span style={{ fontSize: 13, fontWeight: 650, color: "var(--yazi-koyu)" }}>
                              {item.dolu} / {item.toplam}
                            </span>
                            <span style={{ fontSize: 12, color: "var(--yazi-soluk)" }}>
                              %{yuzdeMetin}
                            </span>
                          </div>
                        </div>
                        <div
                          style={{
                            width: "100%",
                            height: 8,
                            background: "var(--kenarlik)",
                            borderRadius: 4,
                            overflow: "hidden",
                          }}
                        >
                          <div
                            style={{
                              width: `${yuzdeSayi}%`,
                              height: "100%",
                              background: cubukRengi,
                              borderRadius: 4,
                              transition: "width 0.5s ease",
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* En altta açıklama notları */}
              <div
                style={{
                  marginTop: 16,
                  paddingTop: 10,
                  borderTop: "1px solid var(--kenarlik)",
                  fontSize: 11,
                  color: "var(--yazi-soluk)",
                  lineHeight: 1.4,
                  display: "flex",
                  flexDirection: "column",
                  gap: 8,
                }}
              >
                <div>
                  Bu oranlar yalnızca regex katmanının sonucudur. NER ve LLM katmanları daha fazlasını doldurur — bu bir alt sınır göstergesidir, kesin doluluk değildir.
                </div>
                <div>
                  Doluluk oranı ile çıkarım doğruluğu farklı şeylerdir: doluluk, bankaların o alanı kaç kampanyada yayımladığını gösterir; %98,28 makro F1 ise yayımlanan alanları ne kadar doğru okuduğumuzu ölçer.
                </div>
              </div>
            </div>

            {/* SAĞ KART 2 — Sistem Sağlığı ve Veri Tazeliği */}
            <div
              style={{
                background: "var(--kart)",
                border: "1px solid var(--kenarlik)",
                borderRadius: 14,
                padding: 20,
                boxShadow: "var(--golge-kart)",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
              }}
            >
              <div>
                {/* Başlık bloğu */}
                <div style={{ marginBottom: 18 }}>
                  <div
                    style={{
                      fontSize: 15,
                      fontWeight: 650,
                      color: "var(--yazi-koyu)",
                    }}
                  >
                    Sistem Sağlığı ve Veri Tazeliği
                  </div>
                  <div
                    style={{
                      fontSize: 12,
                      color: "var(--yazi-soluk)",
                      marginTop: 2,
                    }}
                  >
                    Arka plandaki teknik durum
                  </div>
                </div>

                {/* Mini Kart Grid - DENETIM BULGUSU (25.08.2026): burada 4
                    kart (2x2) vardi, "SON TARAMA" karti SISTEM_DURUMU'ndaki
                    SABIT tarihi gosteriyordu ve hemen altindaki
                    TazelikSeridi'nin CANLI "Son tarama" etiketiyle
                    celisiyordu (ayni bilgi, iki farkli kaynak, ayni ekranda).
                    Kart kaldirildi - TazelikSeridi zaten ayni bilgiyi canli
                    gosteriyor. */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr 1fr",
                    gap: 10,
                  }}
                >
                  {/* Mini Kart 1: RAG İNDEKSİ */}
                  <div
                    style={{
                      background: "var(--zemin-yumusak)",
                      border: "1px solid var(--kenarlik)",
                      borderRadius: 10,
                      padding: 12,
                    }}
                  >
                    <div
                      style={{
                        fontSize: 10,
                        fontWeight: 700,
                        letterSpacing: "0.08em",
                        color: "var(--yazi-soluk)",
                        textTransform: "uppercase",
                      }}
                    >
                      {/* Hero'daki "OLCUM INDEKSI" ile karistirilmasin:
                          burasi calisan sistemin guncel indeksi. */}
                      CANLI RAG İNDEKSİ
                    </div>
                    <div
                      style={{
                        fontSize: 17,
                        fontWeight: 650,
                        color: "var(--yazi-koyu)",
                        marginTop: 4,
                        lineHeight: 1.2,
                      }}
                    >
                      {ragParca} parça
                    </div>
                    <div
                      style={{
                        fontSize: 11,
                        color: "var(--yazi-soluk)",
                        marginTop: 4,
                      }}
                    >
                      {/* Tarih SISTEM_DURUMU'ndan degil - asagidaki
                          TazelikSeridi'nin canli "RAG indeksi" etiketiyle
                          celisen ikinci bir sabit tarih olmasin diye
                          kaldirildi (bkz. yukaridaki denetim notu). */}
                      {ragBelge} belgeden
                    </div>
                  </div>

                  {/* Mini Kart 2: API DURUMU */}
                  <div
                    style={{
                      background: "var(--zemin-yumusak)",
                      border: "1px solid var(--kenarlik)",
                      borderRadius: 10,
                      padding: 12,
                    }}
                  >
                    <div
                      style={{
                        fontSize: 10,
                        fontWeight: 700,
                        letterSpacing: "0.08em",
                        color: "var(--yazi-soluk)",
                        textTransform: "uppercase",
                      }}
                    >
                      API DURUMU
                    </div>
                    <div
                      style={{
                        fontSize: 17,
                        fontWeight: 650,
                        color: apiBagli ? "#0c765f" : "#c94f4f",
                        marginTop: 4,
                        lineHeight: 1.2,
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                      }}
                    >
                      <span
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          background: apiBagli ? "#3fb296" : "#c94f4f",
                          display: "inline-block",
                        }}
                      />
                      {apiBagli ? "Çalışıyor" : "Bağlantı yok"}
                    </div>
                    <div
                      style={{
                        fontSize: 11,
                        color: "var(--yazi-soluk)",
                        marginTop: 4,
                      }}
                    >
                      {apiBagli ? "canlı bağlantı aktif" : "API sunucusu kapalı"}
                    </div>
                  </div>

                  {/* Mini Kart 3: GOLD VERİ SETİ */}
                  <div
                    style={{
                      background: "var(--zemin-yumusak)",
                      border: "1px solid var(--kenarlik)",
                      borderRadius: 10,
                      padding: 12,
                    }}
                  >
                    <div
                      style={{
                        fontSize: 10,
                        fontWeight: 700,
                        letterSpacing: "0.08em",
                        color: "var(--yazi-soluk)",
                        textTransform: "uppercase",
                      }}
                    >
                      GOLD VERİ SETİ
                    </div>
                    <div
                      style={{
                        fontSize: 17,
                        fontWeight: 650,
                        color: "var(--yazi-koyu)",
                        marginTop: 4,
                        lineHeight: 1.2,
                      }}
                    >
                      {OLCUMLER.veri.goldKayit} kayıt
                    </div>
                    <div
                      style={{
                        fontSize: 11,
                        color: "var(--yazi-soluk)",
                        marginTop: 4,
                      }}
                    >
                      elle doğrulanmış
                    </div>
                  </div>
                </div>
              </div>

              {/* 2x2 grid'in ALTINDA TazelikSeridi veya API Kapalı Bilgisi */}
              <div style={{ marginTop: 14 }}>
                {apiBagli ? (
                  <TazelikSeridi />
                ) : (
                  <div
                    style={{
                      paddingTop: 10,
                      borderTop: "1px solid var(--kenarlik)",
                      fontSize: 12,
                      color: "var(--yazi-normal)",
                      lineHeight: 1.4,
                    }}
                  >
                    Veri tazeliği API bağlantısı kurulduğunda burada gösterilecektir.
                  </div>
                )}
              </div>
            </div>

            {/* TAM GENİŞLİK KART — Taranan Kaynaklar */}
            <div
              style={{
                gridColumn: "1 / -1",
                background: "var(--kart)",
                border: "1px solid var(--kenarlik)",
                borderRadius: 14,
                padding: 20,
                boxShadow: "var(--golge-kart)",
              }}
            >
              {/* Başlık bloğu */}
              <div style={{ marginBottom: 18 }}>
                <div
                  style={{
                    fontSize: 15,
                    fontWeight: 650,
                    color: "var(--yazi-koyu)",
                  }}
                >
                  Taranan Kaynaklar
                </div>
                <div
                  style={{
                    fontSize: 12,
                    color: "var(--yazi-soluk)",
                    marginTop: 2,
                  }}
                >
                  BDDK listesindeki 10 katılım bankasının resmî kampanya sayfaları · son tarama {SISTEM_DURUMU.sonTarama}
                </div>
              </div>

              {/* 2 Sütunlu Liste (5 + 5) */}
              <div className="kaynak-grid">
                {KAYNAK_TAKIP.map((item) => {
                  return (
                    <div
                      key={item.banka}
                      style={{
                        paddingBottom: 10,
                        borderBottom: "1px solid var(--kenarlik)",
                        display: "flex",
                        flexDirection: "column",
                        gap: 2,
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <span style={{ fontSize: 13, fontWeight: 600, color: "var(--yazi-koyu)" }}>
                          {item.banka}
                        </span>
                        {item.haric && (
                          <span
                            style={{
                              fontSize: 10,
                              fontWeight: 600,
                              background: "var(--kart-ustu)",
                              color: "var(--yazi-soluk)",
                              padding: "1px 5px",
                              borderRadius: 5,
                            }}
                          >
                            kapsam dışı
                          </span>
                        )}
                      </div>

                      {item.haric ? (
                        <div>
                          <span
                            style={{
                              fontSize: 11,
                              color: "var(--yazi-soluk)",
                              whiteSpace: "nowrap",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              display: "block",
                            }}
                          >
                            {item.url}
                          </span>
                          <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 1 }}>
                            kampanya/ürün yayımlamıyor
                          </div>
                        </div>
                      ) : (
                        <a
                          href={`https://${item.url}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="kaynak-url-link"
                          title={`https://${item.url}`}
                        >
                          {item.url}
                        </a>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* En altta not */}
              <div
                style={{
                  marginTop: 16,
                  paddingTop: 10,
                  borderTop: "1px solid var(--kenarlik)",
                  fontSize: 11,
                  color: "var(--yazi-soluk)",
                  lineHeight: 1.4,
                }}
              >
                Her kampanya kaydı, alındığı sayfanın URL'si ve tarih damgasıyla birlikte saklanır. Bir yanıtın dayandığı kaynak Jüri Audit Paneli'nden izlenebilir.
              </div>
            </div>
          </div>
        );
      })()}
    </div>
  );
}

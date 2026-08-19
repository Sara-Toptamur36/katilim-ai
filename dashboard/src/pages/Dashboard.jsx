import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Alert, Drawer, Modal } from "antd";
import {
  RobotOutlined,
  SwapOutlined,
  AuditOutlined,
} from "@ant-design/icons";
import client from "../api/client";
import {
  OLCUMLER,
  OLCUM_TARIHI,
  BANKA_DAGILIMI,
  URUN_AILESI,
  ZAMAN_EKSENI,
  ALAN_DOLULUGU,
  SISTEM_DURUMU,
  KAYNAK_TAKIP,
} from "../data/olcumler";
import TazelikSeridi from "../components/TazelikSeridi";

export default function Dashboard() {
  const [apiBagli, setApiBagli] = useState(false);
  const [kontrolEdildi, setKontrolEdildi] = useState(false);
  const [metrikPaneliAcik, setMetrikPaneliAcik] = useState(false);
  const [veriPaneliAcik, setVeriPaneliAcik] = useState(false);

  // Paneller arası geçiş kontrolü (biri açılırken diğeri kapanır)
  const modelPaneliniAc = () => {
    setVeriPaneliAcik(false);
    setMetrikPaneliAcik(true);
  };

  const veriPaneliniAc = () => {
    setMetrikPaneliAcik(false);
    setVeriPaneliAcik(true);
  };

  // API sağlık kontrolü
  useEffect(() => {
    client
      .get("/")
      .then(() => setApiBagli(true))
      .catch(() => setApiBagli(false))
      .finally(() => setKontrolEdildi(true));
  }, []);

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

        /* Model Metrikleri Modal — perde ve konum */
        .metrik-modal .ant-modal-mask {
          background: rgba(12, 30, 26, 0.55) !important;
          backdrop-filter: blur(6px);
        }
        .metrik-modal .ant-modal {
          padding-bottom: 0 !important;
        }
        .metrik-modal .ant-modal-content {
          border-radius: 18px !important;
          padding: 24px !important;
        }
        .metrik-modal .ant-modal-header {
          margin-bottom: 0 !important;
          padding-bottom: 16px !important;
          border-bottom: 1px solid var(--kenarlik) !important;
        }
        .metrik-modal .ant-modal-body {
          max-height: 85vh;
          overflow-y: auto;
          padding-top: 20px !important;
        }

        /* Bento ızgara */
        .bento-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
        }
        @media (max-width: 900px) {
          .bento-grid { grid-template-columns: repeat(2, 1fr) !important; }
        }
        @media (max-width: 640px) {
          .bento-grid { grid-template-columns: 1fr !important; }
        }

        /* Modal 1100px altında daralt */
        @media (max-width: 1100px) {
          .metrik-modal .ant-modal {
            width: 94% !important;
            max-width: 94vw !important;
          }
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

        /* Drawer responsive kuralları (Veri Kaynakları Drawer'ı için) */
        @media (max-width: 1024px) {
          .metrik-drawer .ant-drawer-content-wrapper {
            width: 90% !important;
            max-width: 90vw !important;
          }
        }
        @media (max-width: 768px) {
          .metrik-drawer .ant-drawer-content-wrapper {
            width: 100% !important;
            max-width: 100vw !important;
          }
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
            Veri toplama hattını, çıkarım kalitesini, RAG performansını ve ajan
            kararlarını tek ekrandan izleyin. Eksik veri görünür kalır; her yanıt
            kaynağı ve audit iziyle birlikte takip edilir.
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
              RAG İNDEKSİ
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
              {OLCUMLER.rag.indeksTarihi}
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

          {/* 3. Model Metrikleri (Tıklanabilir - Drawer Açar) */}
          <div
            onClick={modelPaneliniAc}
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
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#d8c48c")}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--kenarlik)")}
            title="Model metrikleri detay panelini aç"
          >
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: "50%",
                background: "#d8c48c",
              }}
            />
            Model Metrikleri
          </div>

          {/* 4. Veri Kaynakları (Tıklanabilir - Drawer Açar) */}
          <div
            onClick={veriPaneliniAc}
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
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#d8c48c")}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--kenarlik)")}
            title="Veri kaynakları kapsam panelini aç"
          >
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: "50%",
                background: "#d8c48c",
              }}
            />
            Veri Kaynakları
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
          Ölçüm: {OLCUM_TARIHI}
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
            {OLCUMLER.veri.tekilKampanya}
          </span>
          <span
            style={{
              fontSize: 13,
              color: "var(--yazi-normal)",
              marginTop: 6,
              fontWeight: 500,
            }}
          >
            Toplanan kampanya
          </span>
          <span
            style={{
              fontSize: 11,
              color: "var(--yazi-soluk)",
              marginTop: 4,
            }}
          >
            {OLCUMLER.veri.anlikGoruntu} tarihli anlık görüntü
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
        const ilkBes = URUN_AILESI.slice(0, 5);
        const kalanlar = URUN_AILESI.slice(5);
        const digerToplam = kalanlar.reduce((t, u) => t + u.sayi, 0);
        const halkaDilimler = [
          ...ilkBes.map((u, i) => ({ ad: u.ad, sayi: u.sayi, renk: halkaRenkler[i] })),
          { ad: "Diğer", sayi: digerToplam, renk: halkaRenkler[5] },
        ];
        const toplam = 251;
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
        const enBuyuk = 109;

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
                  251 kampanyanın ürün ailesine göre dağılımı
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
                      251
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
                {BANKA_DAGILIMI.map((b) => {
                  const yuzde = (b.tekil / enBuyuk) * 100;
                  /* Baskın iki banka altın, diğerleri yeşil */
                  const baskinMi = b.banka === "Ziraat Katılım" || b.banka === "Türkiye Emlak Katılım";
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
                Altın renkli iki banka, Ziraat Katılım ve Türkiye Emlak Katılım toplam kampanyaların %76'sını oluşturuyor — dağılım dengesizdir.
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
                    251 kampanyada hangi alan ne sıklıkta dolu
                  </div>
                </div>

                {/* Doluluk satırları */}
                <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  {ALAN_DOLULUGU.map((item) => {
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

                {/* 2x2 Mini Kart Grid */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
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
                      RAG İNDEKSİ
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
                      {SISTEM_DURUMU.qdrantParca} parça
                    </div>
                    <div
                      style={{
                        fontSize: 11,
                        color: "var(--yazi-soluk)",
                        marginTop: 4,
                      }}
                    >
                      {SISTEM_DURUMU.qdrantBelge} belgeden · {SISTEM_DURUMU.indeksTarihi}
                    </div>
                  </div>

                  {/* Mini Kart 2: SON TARAMA */}
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
                      SON TARAMA
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
                      {SISTEM_DURUMU.sonTarama}
                    </div>
                    <div
                      style={{
                        fontSize: 11,
                        color: "#0c765f",
                        fontWeight: 600,
                        marginTop: 4,
                      }}
                    >
                      bayatlık {SISTEM_DURUMU.bayatlikGun} gün
                    </div>
                  </div>

                  {/* Mini Kart 3: API DURUMU */}
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

                  {/* Mini Kart 4: GOLD VERİ SETİ */}
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
                              background: "#eeeae0",
                              color: "#7b8c86",
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

      {/* ========================================================
          7) MODEL METRİKLERİ DETAY PANELİ (MODAL — BENTO DÜZEN)
          ======================================================== */}
      <Modal
        open={metrikPaneliAcik}
        onCancel={() => setMetrikPaneliAcik(false)}
        footer={null}
        width={1000}
        centered
        className="metrik-modal"
        title={
          <div>
            <div style={{ fontSize: 20, fontWeight: 650, color: "var(--yazi-koyu)" }}>
              Model Metrikleri
            </div>
            <div style={{ fontSize: 12, color: "var(--yazi-soluk)", fontWeight: 400, marginTop: 2 }}>
              Son ölçüm: {OLCUM_TARIHI}
            </div>
          </div>
        }
      >
        {/* --- BENTO GRID --- */}
        <div className="bento-grid">

          {/* ===== SATIR 1 — ÜÇ BÜYÜK SKOR KARTI ===== */}

          {/* Kart A: Dolu Alan */}
          {(() => {
            const bentoKartStil = {
              background: "var(--kart)",
              border: "1px solid var(--kenarlik)",
              borderRadius: 14,
              padding: 16,
              boxShadow: "0 1px 3px rgba(60,50,30,0.05)",
            };
            const bentoBaslikStil = {
              fontSize: 11,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--yazi-soluk)",
              marginBottom: 12,
              fontWeight: 700,
            };
            /* Doluluk çubuğu yardımcısı */
            const DolulukCubugu = ({ yuzde, renk }) => (
              <div style={{ height: 5, borderRadius: 3, background: "var(--kenarlik)", marginTop: 8, overflow: "hidden" }}>
                <div style={{ width: `${yuzde}%`, height: "100%", borderRadius: 3, background: renk }} />
              </div>
            );

            return (
              <>
                {/* Kart A: Dolu Alan */}
                <div style={bentoKartStil}>
                  <div style={bentoBaslikStil}>DOLU ALAN</div>
                  <div style={{ fontSize: 34, fontWeight: 700, color: "#b8873a", lineHeight: 1 }}>
                    %{OLCUMLER.cikarim.doluAlanDogrulugu.toString().replace(".", ",")}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--yazi-normal)", marginTop: 4 }}>Doğruluk</div>
                  <DolulukCubugu yuzde={OLCUMLER.cikarim.doluAlanDogrulugu} renk="#d4a34b" />
                  <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 6 }}>{OLCUMLER.cikarim.doluAlanDetay}</div>
                </div>

                {/* Kart B: Boş Alan — yeşil tonlar */}
                <div style={bentoKartStil}>
                  <div style={bentoBaslikStil}>BOŞ ALAN</div>
                  <div style={{ fontSize: 34, fontWeight: 700, color: "#0c765f", lineHeight: 1 }}>
                    %{OLCUMLER.cikarim.bosAlanDogrulugu.toString().replace(".", ",")}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--yazi-normal)", marginTop: 4 }}>Yanlış pozitif kontrolü</div>
                  <DolulukCubugu yuzde={OLCUMLER.cikarim.bosAlanDogrulugu} renk="#169276" />
                  <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 6 }}>{OLCUMLER.cikarim.bosAlanDetay}</div>
                </div>

                {/* Kart C: Makro F1 — altın vurgu (ana metrik) */}
                <div style={bentoKartStil}>
                  <div style={bentoBaslikStil}>MAKRO F1</div>
                  <div style={{ fontSize: 34, fontWeight: 700, color: "#b8873a", lineHeight: 1 }}>
                    %{OLCUMLER.cikarim.makroF1.toString().replace(".", ",")}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--yazi-normal)", marginTop: 4 }}>Alan bazlı</div>
                  <DolulukCubugu yuzde={OLCUMLER.cikarim.makroF1} renk="#d4a34b" />
                  <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 6 }}>{OLCUMLER.cikarim.makroF1Detay}</div>
                </div>

                {/* ===== SATIR 2 — RAG (2 sütun) + KAPSAM (1 sütun) ===== */}

                {/* RAG Performansı — 2 sütun genişliğinde */}
                <div style={{ ...bentoKartStil, gridColumn: "span 2" }}>
                  <div style={bentoBaslikStil}>RAG PERFORMANSI</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

                    {/* Recall@1 — ARALIK ÇUBUĞU */}
                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
                        <span style={{ fontSize: 13, color: "var(--yazi-normal)" }}>Recall@1</span>
                        <span style={{ fontSize: 13, fontWeight: 600, color: "#0c765f" }}>
                          %{OLCUMLER.rag.recall1Alt.toString().replace(".", ",")} – %{OLCUMLER.rag.recall1Ust.toString().replace(".", ",")}
                          <span style={{ fontSize: 11, color: "var(--yazi-soluk)", fontWeight: 400, marginLeft: 6 }}>
                            {OLCUMLER.rag.recall1Not}
                          </span>
                        </span>
                      </div>
                      {/* Aralık çubuğu: 0→alt açık zümrüt (#7bcbb6), alt→üst koyu zümrüt (#169276), üst→100 boş */}
                      <div style={{ height: 5, borderRadius: 3, background: "var(--kenarlik)", position: "relative", overflow: "hidden" }}>
                        <div style={{ position: "absolute", left: 0, top: 0, width: `${OLCUMLER.rag.recall1Alt}%`, height: "100%", background: "#7bcbb6", borderRadius: "3px 0 0 3px" }} />
                        <div style={{ position: "absolute", left: `${OLCUMLER.rag.recall1Alt}%`, top: 0, width: `${OLCUMLER.rag.recall1Ust - OLCUMLER.rag.recall1Alt}%`, height: "100%", background: "#169276" }} />
                      </div>
                    </div>

                    {/* Recall@3 — düz çubuk */}
                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
                        <span style={{ fontSize: 13, color: "var(--yazi-normal)" }}>Recall@3</span>
                        <span style={{ fontSize: 13, fontWeight: 600, color: "#0c765f" }}>
                          %{OLCUMLER.rag.recall3.toString().replace(".", ",")}
                          <span style={{ fontSize: 11, color: "var(--yazi-soluk)", fontWeight: 400, marginLeft: 6 }}>{OLCUMLER.rag.recall5Detay}</span>
                        </span>
                      </div>
                      <DolulukCubugu yuzde={OLCUMLER.rag.recall3} renk="#169276" />
                    </div>

                    {/* Recall@5 — düz çubuk */}
                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
                        <span style={{ fontSize: 13, color: "var(--yazi-normal)" }}>Recall@5</span>
                        <span style={{ fontSize: 13, fontWeight: 600, color: "#0c765f" }}>
                          %{OLCUMLER.rag.recall5.toString().replace(".", ",")}
                          <span style={{ fontSize: 11, color: "var(--yazi-soluk)", fontWeight: 400, marginLeft: 6 }}>{OLCUMLER.rag.recall5Detay}</span>
                        </span>
                      </div>
                      <DolulukCubugu yuzde={OLCUMLER.rag.recall5} renk="#169276" />
                    </div>

                    {/* Çekimserlik — düz çubuk, koyu yeşil */}
                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
                        <span style={{ fontSize: 13, color: "var(--yazi-normal)" }}>Çekimserlik</span>
                        <span style={{ fontSize: 13, fontWeight: 600, color: "#0c765f" }}>
                          %{OLCUMLER.rag.abstention}
                          <span style={{ fontSize: 11, color: "var(--yazi-soluk)", fontWeight: 400, marginLeft: 6 }}>{OLCUMLER.rag.abstentionDetay}</span>
                        </span>
                      </div>
                      <DolulukCubugu yuzde={OLCUMLER.rag.abstention} renk="#0c765f" />
                    </div>
                  </div>

                  {/* İndeks bilgisi */}
                  <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 14, paddingTop: 10, borderTop: "1px solid var(--kenarlik)" }}>
                    İndeks: {OLCUMLER.rag.indekslenenParca} parça / {OLCUMLER.rag.belgeSayisi} belge · {OLCUMLER.rag.indeksTarihi}
                  </div>
                </div>

                {/* Kapsam Ölçümü — 1 sütun */}
                <div style={bentoKartStil}>
                  <div style={bentoBaslikStil}>KAPSAM ÖLÇÜMÜ</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    {/* Hassasiyet */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: 13, color: "var(--yazi-normal)" }}>Hassasiyet</span>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontSize: 14, fontWeight: 650, color: "var(--yazi-koyu)" }}>{OLCUMLER.kapsam.hassasiyet}</span>
                        <span style={{ fontSize: 10, fontWeight: 700, background: "rgba(12,118,95,0.12)", color: "#0c765f", padding: "2px 6px", borderRadius: 6 }}>%100</span>
                      </div>
                    </div>
                    {/* Özgüllük */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: 13, color: "var(--yazi-normal)" }}>Özgüllük</span>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontSize: 14, fontWeight: 650, color: "var(--yazi-koyu)" }}>{OLCUMLER.kapsam.ozgulluk}</span>
                        <span style={{ fontSize: 10, fontWeight: 700, background: "rgba(12,118,95,0.12)", color: "#0c765f", padding: "2px 6px", borderRadius: 6 }}>%100</span>
                      </div>
                    </div>
                  </div>
                  <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 14 }}>Scope Guard</div>
                </div>

                {/* ===== SATIR 3 — TEST (1 sütun) + BİLİNEN HATALAR (2 sütun) ===== */}

                {/* Otomatik Test — 1 sütun */}
                <div style={bentoKartStil}>
                  <div style={bentoBaslikStil}>OTOMATİK TEST</div>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
                    <span style={{ fontSize: 28, fontWeight: 700, color: "#0c765f", lineHeight: 1 }}>{OLCUMLER.test.gecen}</span>
                    <span style={{ fontSize: 12, color: "var(--yazi-normal)" }}>geçen test</span>
                    <span style={{ fontSize: 10, fontWeight: 600, background: "var(--kenarlik)", color: "var(--yazi-soluk)", padding: "2px 7px", borderRadius: 6, marginLeft: "auto" }}>+{OLCUMLER.test.yavas} yavaş</span>
                  </div>
                  <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 14 }}>CI her push'ta çalışır.</div>
                </div>

                {/* Bilinen Hatalar — 2 sütun genişliğinde */}
                <div style={{ ...bentoKartStil, gridColumn: "span 2" }}>
                  <div style={bentoBaslikStil}>BİLİNEN HATALAR</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
                    {OLCUMLER.bilinenHatalar.map((hata, idx) => (
                      <div key={hata.kod}>
                        {idx > 0 && <div style={{ borderTop: "1px solid var(--kenarlik)", margin: "10px 0" }} />}
                        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <span style={{ fontSize: 11, fontWeight: 700, background: "#fbe4e4", color: "#c94f4f", padding: "2px 7px", borderRadius: 6, flexShrink: 0 }}>{hata.kod}</span>
                            <span style={{ fontWeight: 650, fontSize: 13, color: "var(--yazi-koyu)" }}>{hata.alan}</span>
                          </div>
                          <div style={{ fontSize: 12, color: "var(--yazi-normal)", lineHeight: 1.45, paddingLeft: 2 }}>{hata.aciklama}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 12, paddingTop: 8, borderTop: "1px solid var(--kenarlik)" }}>
                    Hatalar gizlenmez, kayıt altındadır.
                  </div>
                </div>

                {/* Renk anlamı açıklama notu */}
                <div style={{ gridColumn: "1 / -1", fontSize: 11, color: "var(--yazi-soluk)", marginBottom: -4 }}>
                  Altın renkli değerler çıkarım doğruluğunu, yeşil renkli değerler güvenilirlik ölçümlerini (yanlış pozitif kontrolü, kaynak bulma, çekimserlik) gösterir.
                </div>

                {/* ===== SATIR 4 — TAM GENİŞLİK AMBER UYARI ===== */}
                <div
                  style={{
                    gridColumn: "1 / -1",
                    background: "#f8edcf",
                    border: "1px solid #e7c978",
                    borderRadius: 12,
                    padding: 14,
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 10,
                    fontSize: 12.5,
                    color: "#8c6219",
                    lineHeight: 1.5,
                  }}
                >
                  {/* Uyarı ikonu */}
                  <span style={{ fontSize: 16, flexShrink: 0, marginTop: 1 }}>⚠</span>
                  <span>Bu değerler canlı telemetri değildir. {OLCUM_TARIHI} tarihinde yapılmış ölçümlerdir. Veri veya indeks değiştiğinde yeniden ölçülmesi gerekir.</span>
                </div>
              </>
            );
          })()}
        </div>
      </Modal>

      {/* ========================================================
          8) VERİ KAYNAKLARI DETAY PANELİ (MODAL — BENTO DÜZEN)
          ======================================================== */}
      <Modal
        open={veriPaneliAcik}
        onCancel={() => setVeriPaneliAcik(false)}
        footer={null}
        width={1000}
        centered
        className="metrik-modal"
        title={
          <div>
            <div style={{ fontSize: 20, fontWeight: 650, color: "var(--yazi-koyu)" }}>
              Veri Kaynakları
            </div>
            <div style={{ fontSize: 12, color: "var(--yazi-soluk)", fontWeight: 400, marginTop: 2 }}>
              Kapsam raporu: {OLCUM_TARIHI}
            </div>
          </div>
        }
      >
        {/* --- BENTO GRID --- */}
        <div className="bento-grid">
          {(() => {
            const bentoKartStil = {
              background: "var(--kart)",
              border: "1px solid var(--kenarlik)",
              borderRadius: 14,
              padding: 16,
              boxShadow: "0 1px 3px rgba(60,50,30,0.05)",
            };
            const bentoBaslikStil = {
              fontSize: 11,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--yazi-soluk)",
              marginBottom: 12,
              fontWeight: 700,
            };
            const DolulukCubugu = ({ yuzde, renk }) => (
              <div style={{ height: 5, borderRadius: 3, background: "var(--kenarlik)", marginTop: 8, overflow: "hidden" }}>
                <div style={{ width: `${yuzde}%`, height: "100%", borderRadius: 3, background: renk }} />
              </div>
            );

            return (
              <>
                {/* ===== SATIR 1 — ÜÇ SKOR KARTI ===== */}

                {/* Kart A: TEKİL KAMPANYA */}
                <div style={bentoKartStil}>
                  <div style={bentoBaslikStil}>TEKİL KAMPANYA</div>
                  <div style={{ fontSize: 34, fontWeight: 700, color: "#0c5144", lineHeight: 1 }}>
                    {OLCUMLER.veri.tekilKampanya}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--yazi-normal)", marginTop: 4 }}>Toplanan</div>
                  <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 14 }}>
                    {OLCUMLER.veri.anlikGoruntu} tarihli anlık görüntü
                  </div>
                </div>

                {/* Kart B: BANKA KAPSAMI */}
                <div style={bentoKartStil}>
                  <div style={bentoBaslikStil}>BANKA KAPSAMI</div>
                  <div style={{ fontSize: 34, fontWeight: 700, color: "#169276", lineHeight: 1 }}>
                    {OLCUMLER.veri.kapsananBanka} / {OLCUMLER.veri.toplamBanka}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--yazi-normal)", marginTop: 4 }}>Kapsanan katılım bankası</div>
                  <DolulukCubugu yuzde={(OLCUMLER.veri.kapsananBanka / OLCUMLER.veri.toplamBanka) * 100} renk="#169276" />
                  <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 6 }}>
                    {OLCUMLER.veri.haricBanka} hariç
                  </div>
                </div>

                {/* Kart C: GOLD VERİ SETİ */}
                <div style={bentoKartStil}>
                  <div style={bentoBaslikStil}>GOLD VERİ SETİ</div>
                  <div style={{ fontSize: 34, fontWeight: 700, color: "#b8873a", lineHeight: 1 }}>
                    {OLCUMLER.veri.goldKayit}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--yazi-normal)", marginTop: 4 }}>Elle doğrulanmış kayıt</div>
                  <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 14 }}>
                    referans veri seti
                  </div>
                </div>

                {/* ===== SATIR 2 — BANKA DAĞILIMI (2 sutun) + ZAMAN EKSENİ (1 sutun) ===== */}

                {/* Banka Dağılımı Kartı (2 sütun) */}
                <div style={{ ...bentoKartStil, gridColumn: "span 2" }}>
                  <div style={bentoBaslikStil}>BANKA BAZINDA DAĞILIM</div>
                  
                  {/* Banka listesi */}
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {BANKA_DAGILIMI.map((b) => {
                      const maxTekil = 109;
                      const yuzde = (b.tekil / maxTekil) * 100;
                      const baskinMi = b.banka === "Ziraat Katılım" || b.banka === "Türkiye Emlak Katılım";
                      const cubukRengi = baskinMi ? "#d4a34b" : "#169276";

                      return (
                        <div key={b.banka} style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                              <span style={{ fontSize: 13, fontWeight: 500, color: "var(--yazi-koyu)" }}>
                                {b.banka}
                              </span>
                              {baskinMi && (
                                <span style={{ fontSize: 10, fontWeight: 600, background: "#f8edcf", color: "#8c6219", padding: "1px 5px", borderRadius: 5 }}>
                                  baskın
                                </span>
                              )}
                            </div>
                            <div style={{ fontSize: 11, color: "var(--yazi-soluk)", display: "flex", alignItems: "center", gap: 4 }}>
                              <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>{b.tekil}</span>
                              <span>|</span>
                              <span>{b.snapshot}</span>
                              <span>|</span>
                              <span>{b.gold}</span>
                            </div>
                          </div>
                          <div style={{ width: "100%", height: 5, background: "var(--kenarlik)", borderRadius: 3, overflow: "hidden" }}>
                            <div style={{ width: `${yuzde}%`, height: "100%", background: cubukRengi, borderRadius: 3 }} />
                          </div>
                        </div>
                      );
                    })}

                    {/* Toplam Satırı */}
                    <div style={{ borderTop: "2px solid var(--kenarlik)", paddingTop: 8, marginTop: 4, display: "flex", justifyContent: "space-between", alignItems: "center", fontWeight: 700 }}>
                      <span style={{ fontSize: 13, color: "var(--yazi-koyu)" }}>Toplam</span>
                      <div style={{ fontSize: 11, color: "var(--yazi-koyu)", display: "flex", alignItems: "center", gap: 4 }}>
                        <span>{BANKA_DAGILIMI.reduce((s, b) => s + b.tekil, 0)}</span>
                        <span>|</span>
                        <span>{BANKA_DAGILIMI.reduce((s, b) => s + b.snapshot, 0)}</span>
                        <span>|</span>
                        <span>{BANKA_DAGILIMI.reduce((s, b) => s + b.gold, 0)}</span>
                      </div>
                    </div>
                  </div>

                  {/* Amber Kutusu */}
                  <div
                    style={{
                      background: "#f8edcf",
                      border: "1px solid #e7c978",
                      borderRadius: 8,
                      padding: "10px 12px",
                      fontSize: 11.5,
                      color: "#8c6219",
                      lineHeight: 1.45,
                      marginTop: 12,
                    }}
                  >
                    Altın renkli iki banka toplam kampanyaların %76'sını oluşturuyor — dağılım dengesizdir. Bu bir veri kapsamı boşluğudur, gizlenmemektedir.
                  </div>
                </div>

                {/* Zaman Ekseni Kartı (1 sütun) */}
                <div style={bentoKartStil}>
                  <div style={bentoBaslikStil}>ZAMAN EKSENİ</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 13 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ color: "var(--yazi-normal)" }}>İlk görülme</span>
                      <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>{ZAMAN_EKSENI.ilkGorulme}</span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ color: "var(--yazi-normal)" }}>Son görülme</span>
                      <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>{ZAMAN_EKSENI.sonGorulme}</span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ color: "var(--yazi-normal)" }}>Bayatlık</span>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <span style={{ fontWeight: 600, color: "#0c765f" }}>{ZAMAN_EKSENI.bayatlikGun} gün</span>
                        <span style={{ fontSize: 10, fontWeight: 600, background: "rgba(12,118,95,0.12)", color: "#0c765f", padding: "1px 5px", borderRadius: 5 }}>güncel</span>
                      </div>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ color: "var(--yazi-normal)" }}>Değişen kampanya</span>
                      <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>{ZAMAN_EKSENI.degisenKampanya} / {OLCUMLER.veri.tekilKampanya}</span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ color: "var(--yazi-normal)" }}>Ortalama versiyon</span>
                      <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>{ZAMAN_EKSENI.ortalamaVersiyon.toString().replace(".", ",")}</span>
                    </div>
                  </div>
                </div>

                {/* ===== SATIR 3 — ÜRÜN AİLESİ (2 sutun) + KAPSAM DIŞI (1 sutun) ===== */}

                {/* Ürün Ailesi Kartı (2 sütun) */}
                <div style={{ ...bentoKartStil, gridColumn: "span 2" }}>
                  <div style={bentoBaslikStil}>ÜRÜN AİLESİ DAĞILIMI</div>
                  
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {URUN_AILESI.map((u) => {
                      const dusukMu = u.doluluk < 25;
                      const yaziRengi = dusukMu ? "#b8873a" : "#0c765f";
                      const cubukRengi = dusukMu ? "#d4a34b" : "#169276";
                      const kaynaktaYokMu = u.ad === "Belirtilmemiş";

                      return (
                        <div key={u.ad} style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                              <span style={{ fontSize: 13, fontWeight: 500, color: "var(--yazi-koyu)" }}>{u.ad}</span>
                              {kaynaktaYokMu && (
                                <span style={{ fontSize: 10, fontWeight: 600, background: "#eeeae0", color: "#7b8c86", padding: "1px 5px", borderRadius: 5 }}>
                                  kaynakta yok
                                </span>
                              )}
                            </div>
                            <div style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 12 }}>
                              <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>{u.sayi}</span>
                              <span style={{ fontWeight: 600, color: yaziRengi, minWidth: 46, textAlign: "right" }}>
                                %{u.doluluk.toString().replace(".", ",")}
                              </span>
                            </div>
                          </div>
                          <div style={{ width: "100%", height: 5, background: "var(--kenarlik)", borderRadius: 3, overflow: "hidden" }}>
                            <div style={{ width: `${u.doluluk}%`, height: "100%", background: cubukRengi, borderRadius: 3 }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 12, paddingTop: 8, borderTop: "1px solid var(--kenarlik)" }}>
                    Alan doluluk, o üründeki kampanyaların yapılandırılmış alanlarının ne kadarının dolu olduğunu gösterir. Düşük oran veri eksikliğidir, hata değildir.
                  </div>
                </div>

                {/* Kapsam Dışı Banka Kartı (1 sütun) */}
                <div style={{ ...bentoKartStil, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                      <span style={bentoBaslikStil}>KAPSAM DIŞI BANKA</span>
                      <span style={{ fontSize: 10, fontWeight: 600, background: "var(--kenarlik)", color: "var(--yazi-soluk)", padding: "1px 6px", borderRadius: 5 }}>1 banka</span>
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: "var(--yazi-koyu)", marginBottom: 6 }}>
                      {OLCUMLER.veri.haricBanka}
                    </div>
                    <div style={{ fontSize: 12, color: "var(--yazi-normal)", lineHeight: 1.5 }}>
                      BDDK listesinde yer alıyor ancak ürün/kampanya yayımlamadığı için hariç tutuldu.
                    </div>
                  </div>
                  <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 14 }}>
                    Periyodik olarak yeniden kontrol ediliyor.
                  </div>
                </div>

                {/* ===== SATIR 4 — TAM GENİŞLİK BİLGİ KUTUSU ===== */}
                <div
                  style={{
                    gridColumn: "1 / -1",
                    background: "var(--zemin-yumusak)",
                    border: "1px solid var(--kenarlik)",
                    borderRadius: 12,
                    padding: 14,
                    fontSize: 12.5,
                    color: "var(--yazi-normal)",
                    lineHeight: 1.5,
                  }}
                >
                  Bilinen sınırlama: Aktif/Süresi dolmuş yaşam döngüsü durumu yalnızca PostgreSQL'de hesaplanır. Bu rapor veritabanı okumadığı için aktif kampanya sayısı içermez.
                </div>
              </>
            );
          })()}
        </div>
      </Modal>
    </div>
  );
}

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Alert, Drawer } from "antd";
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

        /* Drawer responsive kuralları */
        @media (max-width: 1024px) {
          .metrik-drawer .ant-drawer-content-wrapper {
            width: 90% !important;
            max-width: 90vw !important;
          }
          .metrik-ikili-grid {
            grid-template-columns: 1fr !important;
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
            <Link to="/chatbot" className="hero-buton">
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
        {/* Kutu 1: Veri */}
        <div
          style={{
            background: "var(--kart)",
            border: "1px solid var(--kenarlik)",
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
              color: "var(--yazi-soluk)",
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

        {/* Kutu 2: Kapsam */}
        <div
          style={{
            background: "var(--kart)",
            border: "1px solid var(--kenarlik)",
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
              color: "var(--yazi-soluk)",
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

        {/* Kutu 3: Çıkarım Ölçümü */}
        <div
          style={{
            background: "var(--kart)",
            border: "1px solid var(--kenarlik)",
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
              color: "var(--yazi-soluk)",
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

        {/* Kutu 4: RAG Ölçümü */}
        <div
          style={{
            background: "var(--kart)",
            border: "1px solid var(--kenarlik)",
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
              color: "var(--yazi-soluk)",
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
          5) MEVCUT İÇERİK: TAZELİK ŞERİDİ (Sadece API bağlıyken)
          ======================================================== */}
      {apiBagli && <TazelikSeridi />}

      {/* ========================================================
          6) MODEL METRİKLERİ DETAY PANELİ (DRAWER - 660px)
          ======================================================== */}
      <Drawer
        title={
          <div>
            <div style={{ fontSize: 18, fontWeight: 700, color: "var(--yazi-koyu)" }}>
              Model Metrikleri
            </div>
            <div style={{ fontSize: 12, color: "var(--yazi-soluk)", fontWeight: 400, marginTop: 2 }}>
              Son ölçüm: {OLCUM_TARIHI}
            </div>
          </div>
        }
        placement="right"
        width={660}
        onClose={() => setMetrikPaneliAcik(false)}
        open={metrikPaneliAcik}
        className="metrik-drawer"
        styles={{ body: { padding: "16px 20px" } }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {/* BÖLÜM 1 - Çıkarım Doğruluğu */}
          <div
            style={{
              background: "var(--kart)",
              border: "1px solid var(--kenarlik)",
              borderRadius: 10,
              padding: "12px 16px",
            }}
          >
            <div
              style={{
                fontSize: 12.5,
                fontWeight: 700,
                color: "var(--marka-600)",
                marginBottom: 10,
                letterSpacing: "0.05em",
              }}
            >
              ÇIKARIM DOĞRULUĞU
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 13.5 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--yazi-normal)" }}>Dolu alan doğruluğu</span>
                <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>
                  %{OLCUMLER.cikarim.doluAlanDogrulugu.toString().replace(".", ",")}{" "}
                  <span style={{ fontSize: 12, color: "var(--yazi-soluk)", fontWeight: 400 }}>
                    ({OLCUMLER.cikarim.doluAlanDetay})
                  </span>
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--yazi-normal)" }}>Boş alan doğruluğu</span>
                <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>
                  %{OLCUMLER.cikarim.bosAlanDogrulugu.toString().replace(".", ",")}{" "}
                  <span style={{ fontSize: 12, color: "var(--yazi-soluk)", fontWeight: 400 }}>
                    ({OLCUMLER.cikarim.bosAlanDetay})
                  </span>
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--yazi-normal)" }}>Alan bazlı makro F1</span>
                <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>
                  %{OLCUMLER.cikarim.makroF1.toString().replace(".", ",")}{" "}
                  <span style={{ fontSize: 12, color: "var(--yazi-soluk)", fontWeight: 400 }}>
                    ({OLCUMLER.cikarim.makroF1Detay})
                  </span>
                </span>
              </div>
            </div>
            <div
              style={{
                fontSize: 11.5,
                color: "var(--yazi-soluk)",
                marginTop: 10,
                lineHeight: 1.4,
                borderTop: "1px dashed var(--kenarlik)",
                paddingTop: 6,
              }}
            >
              Dolu ve boş alan ayrı ölçülür: bir alanı kaçırmak ile olmayan bir değeri uydurmak farklı hatalardır.
            </div>
          </div>

          {/* BÖLÜM 2 - RAG Performansı */}
          <div
            style={{
              background: "var(--kart)",
              border: "1px solid var(--kenarlik)",
              borderRadius: 10,
              padding: "12px 16px",
            }}
          >
            <div
              style={{
                fontSize: 12.5,
                fontWeight: 700,
                color: "var(--marka-600)",
                marginBottom: 10,
                letterSpacing: "0.05em",
              }}
            >
              RAG PERFORMANSI
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 13.5 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--yazi-normal)" }}>Recall@1</span>
                <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>
                  %{OLCUMLER.rag.recall1Alt.toString().replace(".", ",")} - %{OLCUMLER.rag.recall1Ust.toString().replace(".", ",")}{" "}
                  <span style={{ fontSize: 12, color: "var(--yazi-soluk)", fontWeight: 400 }}>
                    (28-30/32, {OLCUMLER.rag.recall1Not})
                  </span>
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--yazi-normal)" }}>Recall@3</span>
                <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>
                  %{OLCUMLER.rag.recall3.toString().replace(".", ",")}{" "}
                  <span style={{ fontSize: 12, color: "var(--yazi-soluk)", fontWeight: 400 }}>
                    ({OLCUMLER.rag.recall5Detay})
                  </span>
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--yazi-normal)" }}>Recall@5</span>
                <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>
                  %{OLCUMLER.rag.recall5.toString().replace(".", ",")}{" "}
                  <span style={{ fontSize: 12, color: "var(--yazi-soluk)", fontWeight: 400 }}>
                    ({OLCUMLER.rag.recall5Detay})
                  </span>
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--yazi-normal)" }}>Çekimserlik doğruluğu</span>
                <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>
                  %{OLCUMLER.rag.abstention}{" "}
                  <span style={{ fontSize: 12, color: "var(--yazi-soluk)", fontWeight: 400 }}>
                    ({OLCUMLER.rag.abstentionDetay})
                  </span>
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--yazi-normal)" }}>İndeks</span>
                <span style={{ fontWeight: 600, color: "var(--yazi-koyu)", fontSize: 12.5 }}>
                  {OLCUMLER.rag.indekslenenParca} parça / {OLCUMLER.rag.belgeSayisi} belge - {OLCUMLER.rag.indeksTarihi}
                </span>
              </div>
            </div>
            <div
              style={{
                fontSize: 11.5,
                color: "var(--yazi-soluk)",
                marginTop: 10,
                lineHeight: 1.4,
                borderTop: "1px dashed var(--kenarlik)",
                paddingTop: 6,
              }}
            >
              Recall@1 tek bir sayı olarak verilemiyor; aynı süreçte üç kez ölçüldüğünde 28-30/32 arasında değişiyor. Recall@3 ve @5 kararlı.
            </div>
          </div>

          {/* BÖLÜM 3 & 4 - Kapsam Ölçümü ve Otomatik Test (YAN YANA GRID) */}
          <div
            className="metrik-ikili-grid"
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 12,
            }}
          >
            {/* BÖLÜM 3 - Kapsam Ölçümü (Scope Guard) */}
            <div
              style={{
                background: "var(--kart)",
                border: "1px solid var(--kenarlik)",
                borderRadius: 10,
                padding: "12px 16px",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: 12.5,
                    fontWeight: 700,
                    color: "var(--marka-600)",
                    marginBottom: 10,
                    letterSpacing: "0.05em",
                  }}
                >
                  KAPSAM ÖLÇÜMÜ
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 13.5 }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--yazi-normal)" }}>Hassasiyet</span>
                    <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>
                      {OLCUMLER.kapsam.hassasiyet}
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--yazi-normal)" }}>Özgüllük</span>
                    <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>
                      {OLCUMLER.kapsam.ozgulluk}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* BÖLÜM 4 - Otomatik Test */}
            <div
              style={{
                background: "var(--kart)",
                border: "1px solid var(--kenarlik)",
                borderRadius: 10,
                padding: "12px 16px",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: 12.5,
                    fontWeight: 700,
                    color: "var(--marka-600)",
                    marginBottom: 10,
                    letterSpacing: "0.05em",
                  }}
                >
                  OTOMATİK TEST
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 13.5 }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--yazi-normal)" }}>Geçen test</span>
                    <span style={{ fontWeight: 600, color: "#3fb296" }}>
                      {OLCUMLER.test.gecen}
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--yazi-normal)" }}>Yavaş test</span>
                    <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>
                      {OLCUMLER.test.yavas}
                    </span>
                  </div>
                </div>
              </div>
              <div
                style={{
                  fontSize: 11.5,
                  color: "var(--yazi-soluk)",
                  marginTop: 8,
                  lineHeight: 1.3,
                }}
              >
                CI her push'ta çalışır.
              </div>
            </div>
          </div>

          {/* BÖLÜM 5 - Bilinen Hatalar */}
          <div
            style={{
              background: "var(--kart)",
              border: "1px solid var(--kenarlik)",
              borderRadius: 10,
              padding: "12px 16px",
            }}
          >
            <div
              style={{
                fontSize: 12.5,
                fontWeight: 700,
                color: "var(--marka-600)",
                marginBottom: 10,
                letterSpacing: "0.05em",
              }}
            >
              BİLİNEN HATALAR
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {OLCUMLER.bilinenHatalar.map((hata) => (
                <div
                  key={hata.kod}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 3,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 700,
                        background: "rgba(201, 79, 79, 0.12)",
                        color: "#c94f4f",
                        padding: "2px 6px",
                        borderRadius: 4,
                        flexShrink: 0,
                      }}
                    >
                      {hata.kod}
                    </span>
                    <span
                      style={{
                        fontWeight: 600,
                        fontSize: 13,
                        color: "var(--yazi-koyu)",
                      }}
                    >
                      {hata.alan}
                    </span>
                  </div>
                  <div
                    style={{
                      fontSize: 12.5,
                      color: "var(--yazi-normal)",
                      lineHeight: 1.45,
                      paddingLeft: 2,
                    }}
                  >
                    {hata.aciklama}
                  </div>
                </div>
              ))}
            </div>
            <div
              style={{
                fontSize: 11.5,
                color: "var(--yazi-soluk)",
                marginTop: 10,
                lineHeight: 1.4,
                borderTop: "1px dashed var(--kenarlik)",
                paddingTop: 6,
              }}
            >
              Hatalar gizlenmez, kayıt altındadır.
            </div>
          </div>

          {/* En Altta Amber Uyarı Kutusu */}
          <div
            style={{
              background: "rgba(194, 142, 40, 0.10)",
              border: "1px solid rgba(194, 142, 40, 0.35)",
              borderRadius: 10,
              padding: "10px 14px",
              fontSize: 12,
              color: "#d8c48c",
              lineHeight: 1.45,
            }}
          >
            Bu değerler canlı telemetri değildir. 18 Ağustos 2026 tarihinde yapılmış ölçümlerdir. Veri veya indeks değiştiğinde yeniden ölçülmesi gerekir.
          </div>
        </div>
      </Drawer>

      {/* ========================================================
          7) VERİ KAYNAKLARI DETAY PANELİ (DRAWER - 660px)
          ======================================================== */}
      <Drawer
        title={
          <div>
            <div style={{ fontSize: 18, fontWeight: 700, color: "var(--yazi-koyu)" }}>
              Veri Kaynakları
            </div>
            <div style={{ fontSize: 12, color: "var(--yazi-soluk)", fontWeight: 400, marginTop: 2 }}>
              Kapsam raporu: {OLCUM_TARIHI}
            </div>
          </div>
        }
        placement="right"
        width={660}
        onClose={() => setVeriPaneliAcik(false)}
        open={veriPaneliAcik}
        className="metrik-drawer"
        styles={{ body: { padding: "16px 20px" } }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {/* BÖLÜM 1 - Banka Bazında Dağılım */}
          <div
            style={{
              background: "var(--kart)",
              border: "1px solid var(--kenarlik)",
              borderRadius: 10,
              padding: "12px 16px",
            }}
          >
            <div
              style={{
                fontSize: 12.5,
                fontWeight: 700,
                color: "var(--marka-600)",
                marginBottom: 10,
                letterSpacing: "0.05em",
              }}
            >
              BANKA BAZINDA DAĞILIM
            </div>

            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr
                  style={{
                    borderBottom: "1px solid var(--kenarlik)",
                    color: "var(--yazi-soluk)",
                    fontSize: 12,
                  }}
                >
                  <th style={{ textAlign: "left", padding: "6px 8px" }}>Banka</th>
                  <th style={{ textAlign: "right", padding: "6px 8px", minWidth: 120 }}>
                    Tekil kampanya
                  </th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>Anlık görüntü</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>Gold kayıt</th>
                </tr>
              </thead>
              <tbody>
                {BANKA_DAGILIMI.map((b) => {
                  const maxTekil = 109;
                  const yuzde = (b.tekil / maxTekil) * 100;
                  return (
                    <tr
                      key={b.banka}
                      style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.04)" }}
                    >
                      <td
                        style={{
                          padding: "6px 8px",
                          color: "var(--yazi-koyu)",
                          fontWeight: 500,
                        }}
                      >
                        {b.banka}
                      </td>
                      <td style={{ padding: "6px 8px", textAlign: "right" }}>
                        <div style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>
                          {b.tekil}
                        </div>
                        <div
                          style={{
                            width: "100%",
                            height: 4,
                            background: "var(--kenarlik)",
                            borderRadius: 2,
                            marginTop: 3,
                          }}
                        >
                          <div
                            style={{
                              width: `${yuzde}%`,
                              height: "100%",
                              background: "var(--marka-500)",
                              borderRadius: 2,
                            }}
                          />
                        </div>
                      </td>
                      <td
                        style={{
                          padding: "6px 8px",
                          textAlign: "right",
                          color: "var(--yazi-normal)",
                        }}
                      >
                        {b.snapshot}
                      </td>
                      <td
                        style={{
                          padding: "6px 8px",
                          textAlign: "right",
                          color: "var(--yazi-normal)",
                        }}
                      >
                        {b.gold}
                      </td>
                    </tr>
                  );
                })}

                {/* Toplam Satırı */}
                <tr
                  style={{
                    borderTop: "2px solid var(--kenarlik)",
                    fontWeight: 700,
                    color: "var(--yazi-koyu)",
                  }}
                >
                  <td style={{ padding: "8px 8px" }}>Toplam</td>
                  <td style={{ padding: "8px 8px", textAlign: "right" }}>
                    {BANKA_DAGILIMI.reduce((s, b) => s + b.tekil, 0)}
                  </td>
                  <td style={{ padding: "8px 8px", textAlign: "right" }}>
                    {BANKA_DAGILIMI.reduce((s, b) => s + b.snapshot, 0)}
                  </td>
                  <td style={{ padding: "8px 8px", textAlign: "right" }}>
                    {BANKA_DAGILIMI.reduce((s, b) => s + b.gold, 0)}
                  </td>
                </tr>
              </tbody>
            </table>

            {/* Amber Uyarı Kutusu */}
            <div
              style={{
                background: "rgba(194, 142, 40, 0.10)",
                border: "1px solid rgba(194, 142, 40, 0.35)",
                borderRadius: 8,
                padding: "10px 12px",
                fontSize: 12,
                color: "#d8c48c",
                lineHeight: 1.45,
                marginTop: 12,
              }}
            >
              Dağılım dengesiz: Ziraat Katılım ve Türkiye Emlak Katılım toplam kampanyaların %76'sını oluşturuyor. Bu bir veri kapsamı boşluğudur, gizlenmemektedir.
            </div>
          </div>

          {/* BÖLÜM 2 - Kapsam Dışı Banka */}
          <div
            style={{
              background: "var(--kart)",
              border: "1px solid var(--kenarlik)",
              borderRadius: 10,
              padding: "12px 16px",
            }}
          >
            <div
              style={{
                fontSize: 12.5,
                fontWeight: 700,
                color: "var(--marka-600)",
                marginBottom: 8,
                letterSpacing: "0.05em",
              }}
            >
              KAPSAM DIŞI BANKA
            </div>
            <div
              style={{
                fontSize: 13,
                color: "var(--yazi-normal)",
                lineHeight: 1.5,
              }}
            >
              <strong>{OLCUMLER.veri.haricBanka}</strong> — BDDK listesinde yer alıyor ancak ürün/kampanya yayımlamadığı için hariç tutuldu. Periyodik olarak yeniden kontrol ediliyor.
            </div>
          </div>

          {/* BÖLÜM 3 - Ürün Ailesi Dağılımı */}
          <div
            style={{
              background: "var(--kart)",
              border: "1px solid var(--kenarlik)",
              borderRadius: 10,
              padding: "12px 16px",
            }}
          >
            <div
              style={{
                fontSize: 12.5,
                fontWeight: 700,
                color: "var(--marka-600)",
                marginBottom: 10,
                letterSpacing: "0.05em",
              }}
            >
              ÜRÜN AİLESİ DAĞILIMI
            </div>

            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr
                  style={{
                    borderBottom: "1px solid var(--kenarlik)",
                    color: "var(--yazi-soluk)",
                    fontSize: 12,
                  }}
                >
                  <th style={{ textAlign: "left", padding: "6px 8px" }}>Ürün ailesi</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>Kampanya sayısı</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>Alan doluluk</th>
                </tr>
              </thead>
              <tbody>
                {URUN_AILESI.map((u) => {
                  const dusukMu = u.doluluk < 25;
                  return (
                    <tr
                      key={u.ad}
                      style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.04)" }}
                    >
                      <td style={{ padding: "6px 8px", color: "var(--yazi-koyu)" }}>
                        {u.ad}
                      </td>
                      <td
                        style={{
                          padding: "6px 8px",
                          textAlign: "right",
                          fontWeight: 600,
                          color: "var(--yazi-koyu)",
                        }}
                      >
                        {u.sayi}
                      </td>
                      <td
                        style={{
                          padding: "6px 8px",
                          textAlign: "right",
                          fontWeight: 600,
                          color: dusukMu ? "#c28e28" : "var(--yazi-koyu)",
                        }}
                      >
                        %{u.doluluk.toString().replace(".", ",")}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            <div
              style={{
                fontSize: 11.5,
                color: "var(--yazi-soluk)",
                marginTop: 10,
                lineHeight: 1.4,
                borderTop: "1px dashed var(--kenarlik)",
                paddingTop: 6,
              }}
            >
              Alan doluluk, o üründeki kampanyaların yapılandırılmış alanlarının ne kadarının dolu olduğunu gösterir. Düşük oran veri eksikliğidir, hata değildir.
            </div>
          </div>

          {/* BÖLÜM 4 - Zaman Ekseni */}
          <div
            style={{
              background: "var(--kart)",
              border: "1px solid var(--kenarlik)",
              borderRadius: 10,
              padding: "12px 16px",
            }}
          >
            <div
              style={{
                fontSize: 12.5,
                fontWeight: 700,
                color: "var(--marka-600)",
                marginBottom: 10,
                letterSpacing: "0.05em",
              }}
            >
              ZAMAN EKSENİ
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 13.5 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--yazi-normal)" }}>İlk görülme</span>
                <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>
                  {ZAMAN_EKSENI.ilkGorulme}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--yazi-normal)" }}>Son görülme</span>
                <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>
                  {ZAMAN_EKSENI.sonGorulme}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--yazi-normal)" }}>Bayatlık</span>
                <span style={{ fontWeight: 600, color: "#3fb296" }}>
                  {ZAMAN_EKSENI.bayatlikGun} gün
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--yazi-normal)" }}>Değişen kampanya</span>
                <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>
                  {ZAMAN_EKSENI.degisenKampanya} / {OLCUMLER.veri.tekilKampanya}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--yazi-normal)" }}>
                  Kampanya başına ortalama versiyon
                </span>
                <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>
                  {ZAMAN_EKSENI.ortalamaVersiyon.toString().replace(".", ",")}
                </span>
              </div>
            </div>
          </div>

          {/* En Altta Gri Bilgi Kutusu */}
          <div
            style={{
              background: "rgba(255, 255, 255, 0.04)",
              border: "1px solid var(--kenarlik)",
              borderRadius: 10,
              padding: "10px 14px",
              fontSize: 12,
              color: "var(--yazi-soluk)",
              lineHeight: 1.45,
            }}
          >
            Bilinen sınırlama: Aktif/Süresi dolmuş yaşam döngüsü durumu yalnızca PostgreSQL'de hesaplanır. Bu rapor veritabanı okumadığı için aktif kampanya sayısı içermez.
          </div>
        </div>
      </Drawer>
    </div>
  );
}

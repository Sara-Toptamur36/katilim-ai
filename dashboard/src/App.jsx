import { useState, useEffect, useCallback } from "react";
import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import { Layout, ConfigProvider, Drawer, theme as antTema } from "antd";
import {
  DashboardOutlined,
  RobotOutlined,
  FileSearchOutlined,
  AuditOutlined,
  MoonOutlined,
  SunOutlined,
  MenuOutlined,
} from "@ant-design/icons";

/* Sayfa bileşenleri */
import Dashboard from "./pages/Dashboard";
import MetinAnalizi from "./pages/MetinAnalizi";
import Chatbot from "./pages/Chatbot";
import AuditPanel from "./pages/AuditPanel";

/* Bağlam sağlayıcıları */
import { AuditProvider } from "./context/AuditContext";

const { Sider, Header, Content } = Layout;

/* localStorage anahtarı */
const TEMA_ANAHTAR = "katilimai-tema";

/* -------------------------------------------------------
   Menü öğeleri tanımı
   ------------------------------------------------------- */
const KONTROL_MENUSU = [
  { yol: "/", etiket: "Genel Bakış", ikon: <DashboardOutlined /> },
  { yol: "/chatbot", etiket: "AI Asistan", ikon: <RobotOutlined /> },
  { yol: "/analiz", etiket: "Metin Analizi", ikon: <FileSearchOutlined /> },
];

const GUVEN_MENUSU = [
  { yol: "/audit", etiket: "Jüri Audit Paneli", ikon: <AuditOutlined /> },
];

/* Yola göre aktif sayfa adını döndürür */
const SAYFA_ADLARI = {
  "/": "Genel Bakış",
  "/chatbot": "AI Asistan",
  "/analiz": "Metin Analizi",
  "/audit": "Jüri Audit Paneli",
};

/* -------------------------------------------------------
   Menü İçeriği — hem Sider hem Drawer'da kullanılır
   ------------------------------------------------------- */
function MenuIcerigi({ tiklaCalistir }) {
  const { pathname } = useLocation();

  /* Tek bir menü öğesini oluşturur */
  const menuOgesiOlustur = (oge) => {
    const aktifMi = pathname === oge.yol;
    return (
      <Link
        key={oge.yol}
        to={oge.yol}
        className={`menu-ogesi ${aktifMi ? "aktif" : ""}`}
        onClick={tiklaCalistir}
      >
        <span className="menu-ogesi-ikon">{oge.ikon}</span>
        <span>{oge.etiket}</span>
      </Link>
    );
  };

  return (
    <>
      {/* Marka bloğu */}
      <div className="marka-blogu">
        <div className="marka-ust">
          <div className="marka-logo">NN</div>
          <div className="marka-yazi">
            <span className="marka-baslik">KatılımAI</span>
            <span className="marka-alt-baslik">Intelligence Platform</span>
          </div>
        </div>
      </div>

      {/* Çalışma alanı kartı */}
      <div className="calisma-alani-karti">
        <div className="calisma-alani-baslik">Bilişim Vadisi 2026</div>
        <div className="calisma-alani-aciklama">Mentörlük çalışma alanı</div>
      </div>

      {/* Kontrol merkezi menüsü */}
      <div className="menu-bolum-baslik">Kontrol Merkezi</div>
      {KONTROL_MENUSU.map(menuOgesiOlustur)}

      {/* Güven ve izleme menüsü */}
      <div className="menu-bolum-baslik">Güven ve İzleme</div>
      {GUVEN_MENUSU.map(menuOgesiOlustur)}
    </>
  );
}

/* -------------------------------------------------------
   Sol Kenar Çubuğu — sadece masaüstünde görünür
   ------------------------------------------------------- */
function SolMenu() {
  return (
    <Sider width={272} className="kenar-cubugu masaustu-sider">
      <MenuIcerigi />
    </Sider>
  );
}

/* -------------------------------------------------------
   Üst Bar bileşeni
   ------------------------------------------------------- */
function UstBar({ koyuMu, temaToggle, cekmeceyiAc }) {
  const { pathname } = useLocation();
  const sayfaAdi = SAYFA_ADLARI[pathname] || "Sayfa";

  return (
    <Header className="ust-bar">
      {/* Sol taraf: hamburger (mobilde) + yol göstergesi */}
      <div className="ust-bar-sol">
        {/* Hamburger düğmesi — sadece mobilde görünür */}
        <button
          className="hamburger-dugme"
          onClick={cekmeceyiAc}
          aria-label="Menüyü aç"
        >
          <MenuOutlined />
        </button>

        <div className="yol-gostergesi">
          <span className="yol-marka">KatılımAI</span>
          <span className="yol-ayirici">/</span>
          <span className="yol-aktif">{sayfaAdi}</span>
        </div>
      </div>

      {/* Sağ taraf: tema düğmesi + profil */}
      <div className="ust-bar-sag">
        {/* Koyu tema düğmesi */}
        <button
          className="tema-dugme"
          onClick={temaToggle}
          aria-label={koyuMu ? "Açık temaya geç" : "Koyu temaya geç"}
          title={koyuMu ? "Açık temaya geç" : "Koyu temaya geç"}
        >
          {koyuMu ? <SunOutlined /> : <MoonOutlined />}
        </button>

        {/* Kullanıcı profili */}
        <div className="profil-blogu">
          <div className="profil-bilgi">
            <span className="profil-isim">PeacewAI Takımı</span>
            <span className="profil-rol">Proje yöneticisi</span>
          </div>
          <div className="profil-avatar">PT</div>
        </div>
      </div>
    </Header>
  );
}

/* -------------------------------------------------------
   Ana Uygulama bileşeni
   ------------------------------------------------------- */
function App() {
  /* ---------- Koyu tema durumu ---------- */
  const [koyuMu, setKoyuMu] = useState(() => {
    /* Sayfa yüklenirken localStorage'dan oku */
    try {
      return localStorage.getItem(TEMA_ANAHTAR) === "koyu";
    } catch {
      return false;
    }
  });

  /* html etiketine data-tema niteliğini yansıt */
  useEffect(() => {
    const html = document.documentElement;
    if (koyuMu) {
      html.setAttribute("data-tema", "koyu");
    } else {
      html.removeAttribute("data-tema");
    }
  }, [koyuMu]);

  /* Tema değiştirme fonksiyonu */
  const temaToggle = useCallback(() => {
    setKoyuMu((onceki) => {
      const yeni = !onceki;
      try {
        localStorage.setItem(TEMA_ANAHTAR, yeni ? "koyu" : "acik");
      } catch {
        /* localStorage erişim hatası — sessizce geç */
      }
      return yeni;
    });
  }, []);

  /* ---------- Mobil çekmece durumu ---------- */
  const [cekmeceAcik, setCekmeceAcik] = useState(false);

  const cekmeceyiAc = useCallback(() => setCekmeceAcik(true), []);
  const cekmeceyiKapat = useCallback(() => setCekmeceAcik(false), []);

  return (
    <ConfigProvider
      theme={{
        /* Koyu tema aktifken darkAlgorithm kullan */
        algorithm: koyuMu ? antTema.darkAlgorithm : antTema.defaultAlgorithm,
        token: {
          colorPrimary: "#169276",
          borderRadius: 8,
          fontFamily:
            '"Inter", "Segoe UI", Roboto, -apple-system, BlinkMacSystemFont, sans-serif',
        },
      }}
    >
      <BrowserRouter>
        <AuditProvider>
          <Layout style={{ minHeight: "100vh" }}>
            {/* Sol dikey menü — masaüstünde görünür */}
            <SolMenu />

            {/* Mobil çekmece menüsü */}
            <Drawer
              placement="left"
              onClose={cekmeceyiKapat}
              open={cekmeceAcik}
              width={272}
              styles={{
                body: { padding: 0, background: "var(--kenar-cubugu)" },
                header: { display: "none" },
              }}
              className="mobil-cekmece"
            >
              <MenuIcerigi tiklaCalistir={cekmeceyiKapat} />
            </Drawer>

            {/* Sağ taraf: üst bar + içerik */}
            <Layout>
              <UstBar
                koyuMu={koyuMu}
                temaToggle={temaToggle}
                cekmeceyiAc={cekmeceyiAc}
              />
              <Content className="icerik-alani">
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/analiz" element={<MetinAnalizi />} />
                  <Route path="/chatbot" element={<Chatbot />} />
                  <Route path="/audit" element={<AuditPanel />} />
                </Routes>
              </Content>
            </Layout>
          </Layout>
        </AuditProvider>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;

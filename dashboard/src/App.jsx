import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import { Layout, ConfigProvider } from "antd";
import {
  DashboardOutlined,
  RobotOutlined,
  FileSearchOutlined,
  AuditOutlined,
} from "@ant-design/icons";

/* Sayfa bileşenleri */
import Dashboard from "./pages/Dashboard";
import MetinAnalizi from "./pages/MetinAnalizi";
import Chatbot from "./pages/Chatbot";
import AuditPanel from "./pages/AuditPanel";

/* Bağlam sağlayıcıları */
import { AuditProvider } from "./context/AuditContext";

const { Sider, Header, Content } = Layout;

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
   Sol Kenar Çubuğu bileşeni
   ------------------------------------------------------- */
function SolMenu() {
  const { pathname } = useLocation();

  /* Tek bir menü öğesini oluşturur */
  const menuOgesiOlustur = (oge) => {
    const aktifMi = pathname === oge.yol;
    return (
      <Link
        key={oge.yol}
        to={oge.yol}
        className={`menu-ogesi ${aktifMi ? "aktif" : ""}`}
      >
        <span className="menu-ogesi-ikon">{oge.ikon}</span>
        <span>{oge.etiket}</span>
      </Link>
    );
  };

  return (
    <Sider width={272} className="kenar-cubugu">
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
    </Sider>
  );
}

/* -------------------------------------------------------
   Üst Bar bileşeni
   ------------------------------------------------------- */
function UstBar() {
  const { pathname } = useLocation();
  const sayfaAdi = SAYFA_ADLARI[pathname] || "Sayfa";

  return (
    <Header className="ust-bar">
      {/* Yol göstergesi */}
      <div className="yol-gostergesi">
        <span className="yol-marka">KatılımAI</span>
        <span className="yol-ayirici">/</span>
        <span className="yol-aktif">{sayfaAdi}</span>
      </div>

      {/* Kullanıcı profili */}
      <div className="profil-blogu">
        <div className="profil-bilgi">
          <span className="profil-isim">PeacewAI Takımı</span>
          <span className="profil-rol">Proje yöneticisi</span>
        </div>
        <div className="profil-avatar">PT</div>
      </div>
    </Header>
  );
}

/* -------------------------------------------------------
   Ana Uygulama bileşeni
   ------------------------------------------------------- */
function App() {
  return (
    <ConfigProvider
      theme={{
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
            {/* Sol dikey menü */}
            <SolMenu />

            {/* Sağ taraf: üst bar + içerik */}
            <Layout>
              <UstBar />
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

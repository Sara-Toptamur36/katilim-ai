import { useState, useEffect, useCallback } from "react";
import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import { Layout, ConfigProvider, Drawer, theme as antTema } from "antd";
import {
  DashboardOutlined,
  RobotOutlined,
  TagsOutlined,
  SwapOutlined,
  FileSearchOutlined,
  AuditOutlined,
  MoonOutlined,
  SunOutlined,
  MenuOutlined,
  MessageOutlined,
  CalculatorOutlined,
  LoginOutlined,
} from "@ant-design/icons";

/* Sayfa bileşenleri */
import Dashboard from "./pages/Dashboard";
import Kampanyalar from "./pages/Kampanyalar";
import Karsilastirma from "./pages/Karsilastirma";
import MetinAnalizi from "./pages/MetinAnalizi";
import MusteriSesi from "./pages/MusteriSesi";
import HesapMakinesi from "./pages/HesapMakinesi";
import Giris from "./pages/Giris";
import Chatbot from "./pages/Chatbot";
import AuditPanel from "./pages/AuditPanel";

/* Bağlam sağlayıcıları */
import { AuditProvider } from "./context/AuditContext";

/* API istemcisi — veri modu kontrolü için */
import client, { rolAl } from "./api/client";

const { Sider, Header, Content } = Layout;

/* localStorage anahtarı */
const TEMA_ANAHTAR = "katilimai-tema";

/* -------------------------------------------------------
   Menü öğeleri tanımı
   ------------------------------------------------------- */
const KONTROL_MENUSU = [
  { yol: "/", etiket: "Genel Bakış", ikon: <DashboardOutlined /> },
  { yol: "/chatbot", etiket: "AI Asistan", ikon: <RobotOutlined /> },
  { yol: "/kampanyalar", etiket: "Kampanyalar", ikon: <TagsOutlined /> },
  { yol: "/karsilastirma", etiket: "Karşılaştırma", ikon: <SwapOutlined /> },
  { yol: "/hesapla", etiket: "Hesap Makinesi", ikon: <CalculatorOutlined /> },
];

const GUVEN_MENUSU = [
  // `roller`: yalnizca API'de GERCEKTEN bir kisit varsa yazilir. Metin
  // Analizi, POST /cikar ucuna dayanir ve o uc rol_gerekli(["banka_calisani",
  // "denetleyici", "yonetici"]) ile korunur - menu bu kisiti YANSITIR,
  // kendi basina politika UYDURMAZ. Digerlerinde API kisiti olmadigi icin
  // burada da yoktur.
  {
    yol: "/analiz",
    etiket: "Metin Analizi",
    ikon: <FileSearchOutlined />,
    roller: ["banka_calisani", "denetleyici", "yonetici"],
  },
  { yol: "/musteri-sesi", etiket: "Müşteri Sesi", ikon: <MessageOutlined /> },
  { yol: "/audit", etiket: "Jüri Audit Paneli", ikon: <AuditOutlined /> },
  { yol: "/giris", etiket: "Giriş / Kayıt", ikon: <LoginOutlined /> },
];

/* Rol BILINMIYORSA hicbir sey gizlenmez.
   "rol yok" ile "yetkisiz" AYNI SEY DEGILDIR: sistem varsayilan olarak mock
   kimlik dogrulamayla calisir (rol_gerekli o modda hicbir kisit uygulamaz),
   dolayisiyla giris yapilmamis olmasi demoyu kilitlememelidir. Menu ancak
   GERCEK bir rol biliniyorsa suzer. */
function menuyuRoleGoreSuz(ogeler, rol) {
  if (!rol) return ogeler;
  return ogeler.filter((o) => !o.roller || o.roller.includes(rol));
}

/* Yola göre aktif sayfa adını döndürür */
const SAYFA_ADLARI = {
  "/": "Genel Bakış",
  "/chatbot": "AI Asistan",
  "/kampanyalar": "Kampanyalar",
  "/karsilastirma": "Karşılaştırma",
  "/hesapla": "Hesap Makinesi",
  "/analiz": "Metin Analizi",
  "/musteri-sesi": "Müşteri Sesi",
  "/audit": "Jüri Audit Paneli",
  "/giris": "Giriş / Kayıt",
};

/* -------------------------------------------------------
   Menü İçeriği — hem Sider hem Drawer'da kullanılır
   ------------------------------------------------------- */
function MenuIcerigi({ tiklaCalistir }) {
  const { pathname } = useLocation();

  // Rol her yol degisiminde yeniden OKUNUR: Giris ekraninda giris/cikis
  // yapilinca menu ayni oturumda guncellensin diye. localStorage degisimi
  // React'e kendiliginden haber vermez, o yuzden yol degisimi tetikleyici
  // olarak kullanilir (kullanici zaten Giris ekranindan bir yere gider).
  const [rol, setRol] = useState(() => rolAl());
  useEffect(() => {
    setRol(rolAl());
  }, [pathname]);

  /* ---------- Veri modu göstergesi ---------- */
  /* "kontrol"      = sayfa açılışında API'ye bağlanıyor
     "canli"        = API yanıt verdi
     "baglanti_yok" = API'ye ulaşılamadı */
  const [veriModu, setVeriModu] = useState("kontrol");
  const [sonKontrol, setSonKontrol] = useState("");

  const formatSaat = () => {
    const simdi = new Date();
    const saat = String(simdi.getHours()).padStart(2, "0");
    const dakika = String(simdi.getMinutes()).padStart(2, "0");
    return `${saat}:${dakika}`;
  };

  const kontrolEt = () => {
    setVeriModu("kontrol");
    client
      .get("/")
      .then(() => {
        setVeriModu("canli");
        setSonKontrol(formatSaat());
      })
      .catch(() => {
        setVeriModu("baglanti_yok");
        setSonKontrol(formatSaat());
      });
  };

  useEffect(() => {
    kontrolEt();
  }, []);

  const VERI_MODU_METINLERI = {
    kontrol: "Kontrol ediliyor",
    canli: "Canlı veri",
    baglanti_yok: "Bağlantı yok",
  };

  const NOKTA_RENKLERI = {
    kontrol: "rgba(255, 255, 255, 0.4)",
    canli: "#3fb296",
    baglanti_yok: "#c94f4f",
  };

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

      {/* Veri modu durum kutusu */}
      <div
        onClick={kontrolEt}
        style={{
          margin: "16px 16px 8px",
          padding: "10px 14px",
          borderRadius: 10,
          background: "rgba(255, 255, 255, 0.06)",
          border: "1px solid rgba(255, 255, 255, 0.08)",
          cursor: "pointer",
          display: "flex",
          flexDirection: "column",
          gap: 3,
          transition: "background 0.2s ease",
          boxSizing: "border-box",
        }}
        title="Yeniden kontrol etmek için tıklayın"
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: NOKTA_RENKLERI[veriModu],
              boxShadow:
                veriModu === "canli"
                  ? "0 0 6px rgba(63, 178, 150, 0.6)"
                  : veriModu === "baglanti_yok"
                  ? "0 0 6px rgba(201, 79, 79, 0.6)"
                  : "none",
              flexShrink: 0,
            }}
          />
          <span
            style={{
              fontSize: 13,
              color: "#ffffff",
              fontWeight: 600,
              lineHeight: 1.2,
            }}
          >
            {VERI_MODU_METINLERI[veriModu]}
          </span>
        </div>
        {sonKontrol && (
          <span
            style={{
              fontSize: 11,
              color: "rgba(255, 255, 255, 0.45)",
              paddingLeft: 16,
              lineHeight: 1.2,
            }}
          >
            son kontrol {sonKontrol}
          </span>
        )}
      </div>

      {/* Kontrol merkezi menüsü */}
      <div className="menu-bolum-baslik">Kontrol Merkezi</div>
      {menuyuRoleGoreSuz(KONTROL_MENUSU, rol).map(menuOgesiOlustur)}

      {/* Güven ve izleme menüsü */}
      <div className="menu-bolum-baslik">Güven ve İzleme</div>
      {menuyuRoleGoreSuz(GUVEN_MENUSU, rol).map(menuOgesiOlustur)}
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
            '-apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
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
              size={272}
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
                  <Route path="/kampanyalar" element={<Kampanyalar />} />
                  <Route path="/karsilastirma" element={<Karsilastirma />} />
                  <Route path="/hesapla" element={<HesapMakinesi />} />
                  <Route path="/analiz" element={<MetinAnalizi />} />
                  <Route path="/musteri-sesi" element={<MusteriSesi />} />
                  <Route path="/chatbot" element={<Chatbot />} />
                  <Route path="/audit" element={<AuditPanel />} />
                  <Route path="/giris" element={<Giris />} />
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

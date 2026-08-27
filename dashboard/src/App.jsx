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
  CalculatorOutlined,
  SettingOutlined,
  LogoutOutlined,
  CommentOutlined,
} from "@ant-design/icons";

/* Sayfa bileşenleri */
import Dashboard from "./pages/Dashboard";
import Kampanyalar from "./pages/Kampanyalar";
import Karsilastirma from "./pages/Karsilastirma";
import MetinAnalizi from "./pages/MetinAnalizi";
import HesapMakinesi from "./pages/HesapMakinesi";
import Giris from "./pages/Giris";
import Chatbot from "./pages/Chatbot";
import AuditPanel from "./pages/AuditPanel";
import ExtractionAudit from "./pages/ExtractionAudit";
import MusteriSesi from "./pages/MusteriSesi";

/* Bileşenler */
import VeriKaynagiRozeti from "./components/VeriKaynagiRozeti";

/* Bağlam sağlayıcıları */
import { AuditProvider } from "./context/AuditContext";

/* API istemcisi — veri modu kontrolü için */
import client, {
  rolAl,
  rolSil,
  tokenSil,
  kullaniciAdiAl,
  kullaniciAdiSil,
  oturumBaslangiciSil,
} from "./api/client";

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
  // Metin Analizi ve Cikarim Denetimi eskiden yalnizca banka_calisani/
  // denetleyici/yonetici rolune `roller` filtresiyle gosteriliyordu. API
  // tarafindaki rol_gerekli(["banka_calisani","denetleyici","yonetici"])
  // kisiti SADECE JWT_AKTIF=true iken calisir (varsayilan mock/demo modda
  // hicbir etkisi yok, bkz. api/main.py::cikar), yani bu iki sayfa fiilen
  // her zaman erisilebilirdi - sadece menude GIZLIYORDU. Sartname Md. 6
  // jurinin serbest metin -> yapilandirilmis cikti akisini CANLI gormesini
  // gerektirdigi icin (bkz. api/main.py::cikar), bu iki sayfa DENETIM
  // BULGUSU (26.08.2026) sonrasi tum giris yapmis rollere acildi - jüri
  // kendi (musteri) hesabiyla giris yapip buradan kontrol edebilsin diye.
  {
    yol: "/analiz",
    etiket: "Metin Analizi",
    ikon: <FileSearchOutlined />,
  },
  { yol: "/audit", etiket: "Jüri Audit Paneli", ikon: <AuditOutlined /> },
  {
    yol: "/extraction-audit",
    etiket: "Çıkarım Denetimi",
    ikon: <FileSearchOutlined />,
  },
  { yol: "/musteri-sesi", etiket: "Müşteri Sesi", ikon: <CommentOutlined /> },
  // Bu menu ogesi yalnizca GIRIS YAPILMISKEN gorunur (SolMenu, App()'in
  // "girisli" dalinda render edilir - bkz. asagidaki if(!girisli) erken
  // donusu). Yani buraya tiklandiginda Giris.jsx HER ZAMAN Ayarlar
  // gorunumunu gosterir (mevcutRol dolu), Giris/Kayit sekmelerini degil -
  // etiket bunu yansitmali (DENETIM BULGUSU 26.08.2026: eskiden "Giriş /
  // Kayıt" yaziyordu, kullanici menude hic gormeyecegi bir sayfa adi
  // goruyordu).
  { yol: "/giris", etiket: "Ayarlar", ikon: <SettingOutlined /> },
];

/* Uygulama artik girisin ARKASINDA oldugu icin (bkz. App()::girisli) rol
   buraya her zaman DOLU gelir - "musteri" (self-servis kayit) veya elle
   acilmis bir hesabin rolu. rol=null durumu yalnizca teorik bir guvenlik
   agi olarak kalir; o durumda da hicbir sey gizlenmiyoruz. */
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
  "/audit": "Jüri Audit Paneli",
  "/extraction-audit": "Çıkarım Denetimi",
  "/giris": "Ayarlar",
};

/* -------------------------------------------------------
   Menü İçeriği — hem Sider hem Drawer'da kullanılır
   ------------------------------------------------------- */
function MenuIcerigi({ tiklaCalistir = () => {} }) {
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
          {/* BASE_URL kullaniliyor: production build /katilim-ai/ on ekiyle
              aliniyor (deploy-pages.yml). Duz "/logo.png" yazilirsa yerelde
              calisir ama GitHub Pages'te logo kirik cikar - fark edilmesi
              zor bir hata olurdu. */}
          <img
            className="marka-logo"
            src={`${import.meta.env.BASE_URL}logo.png`}
            alt="KatılımAI"
          />
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
function UstBar({ koyuMu, temaToggle, cekmeceyiAc, kullaniciAdi, rol, onCikis }) {
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

      {/* Sağ taraf: veri modu rozeti + tema düğmesi + profil */}
      <div className="ust-bar-sag">
        {/* Canlı/yerel veri rozeti - her sayfada görünür (bkz. madde 14,
            önceden yalnızca Dashboard'da görünen dağınık göstergelerin
            merkezileştirilmiş hali) */}
        <VeriKaynagiRozeti />

        {/* Koyu tema düğmesi */}
        <button
          className="tema-dugme"
          onClick={temaToggle}
          aria-label={koyuMu ? "Açık temaya geç" : "Koyu temaya geç"}
          title={koyuMu ? "Açık temaya geç" : "Koyu temaya geç"}
        >
          {koyuMu ? <SunOutlined /> : <MoonOutlined />}
        </button>

        {/* Kullanıcı profili + çıkış */}
        <div className="profil-blogu">
          <div className="profil-bilgi">
            <span className="profil-isim">{kullaniciAdi || "Kullanıcı"}</span>
            <span className="profil-rol">{rol || "—"}</span>
          </div>
          <img
            className="profil-avatar"
            src={`${import.meta.env.BASE_URL}logo-64.png`}
            alt=""
          />
        </div>

        <button
          className="tema-dugme"
          onClick={onCikis}
          aria-label="Çıkış yap"
          title="Çıkış yap"
        >
          <LogoutOutlined />
        </button>
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

  /* ---------- Oturum kapısı ----------
     Uygulama artik Giris/Kayit ekraninin ARKASINDA: rol yoksa (hic kayit
     olunmamis/giris yapilmamissa) hicbir sayfa/menu render edilmez, yalnizca
     Giris ekrani gosterilir. Cikis yapinca ayni sekilde uygulamadan cikilir
     (bkz. Giris.jsx::cikis -> onCikisYapildi). */
  const [girisli, setGirisli] = useState(() => !!rolAl());
  const [kullaniciAdi, setKullaniciAdi] = useState(() => kullaniciAdiAl());
  const [rol, setRol] = useState(() => rolAl());

  const girisBasarili = useCallback(() => {
    setGirisli(true);
    setKullaniciAdi(kullaniciAdiAl());
    setRol(rolAl());
  }, []);

  // Ust bardaki dogrudan cikis dugmesi Giris.jsx'in KENDI cikis() akisindan
  // GECMIYOR - bu yuzden localStorage temizligi burada da yapilir. Giris.jsx
  // zaten kendi cikis()'inda ayni temizligi yapip bu callback'i cagirdigi
  // icin cift temizlemenin zarari yok (tekrar cagirmak no-op'tur).
  const cikisYapildi = useCallback(() => {
    tokenSil();
    rolSil();
    kullaniciAdiSil();
    oturumBaslangiciSil();
    setGirisli(false);
    setKullaniciAdi(null);
  }, []);

  if (!girisli) {
    return (
      <ConfigProvider
        theme={{
          algorithm: koyuMu ? antTema.darkAlgorithm : antTema.defaultAlgorithm,
          token: {
            colorPrimary: "#169276",
            borderRadius: 8,
            fontFamily:
              '-apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
          },
        }}
      >
        <Giris onGirisBasarili={girisBasarili} koyuMu={koyuMu} temaToggle={temaToggle} />
      </ConfigProvider>
    );
  }

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
                kullaniciAdi={kullaniciAdi}
                rol={rol}
                onCikis={cikisYapildi}
              />
              <Content className="icerik-alani">
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/kampanyalar" element={<Kampanyalar />} />
                  <Route path="/karsilastirma" element={<Karsilastirma />} />
                  <Route path="/hesapla" element={<HesapMakinesi />} />
                  <Route path="/analiz" element={<MetinAnalizi />} />
                  <Route path="/chatbot" element={<Chatbot />} />
                  <Route path="/audit" element={<AuditPanel />} />
                  <Route path="/extraction-audit" element={<ExtractionAudit />} />
                  <Route path="/musteri-sesi" element={<MusteriSesi />} />
                  <Route
                    path="/giris"
                    element={
                      <Giris
                        onGirisBasarili={girisBasarili}
                        onCikisYapildi={cikisYapildi}
                        koyuMu={koyuMu}
                        temaToggle={temaToggle}
                      />
                    }
                  />
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

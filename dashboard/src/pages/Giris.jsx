import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Input,
  Space,
  Tabs,
  Typography,
} from "antd";
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  LockOutlined,
  LoginOutlined,
  UserAddOutlined,
  UserOutlined,
} from "@ant-design/icons";
import {
  girisYap,
  kayitOl,
  rolAl,
  rolKaydet,
  rolSil,
  tokenKaydet,
  tokenSil,
  kullaniciAdiKaydet,
  kullaniciAdiAl,
  kullaniciAdiSil,
  oturumBaslangiciKaydet,
  oturumBaslangiciSil,
  sistemBilgisi,
} from "../api/client";
import Ayarlar from "./Ayarlar";

const { Title, Text, Paragraph } = Typography;

// Yagmur rol tabanli erisimi kurdu (POST /kayit, POST /token, rol_gerekli).
// Uygulama artik giris ekrani ARKASINDA (bkz. App.jsx): POST /token yalnizca
// JWT_AKTIF=true iken calisiyor (varsayilan calisma modu mock) - bu ekran
// mock modda GIRIS YAP sekmesini de calisir tutmak icin yerel kabul yapiyor
// (asagida bkz. girisMockKabul). Sunucu zaten mock modda HERHANGI bir
// Bearer token'i kabul ediyor (api/auth.py::token_dogrula) - bu, o gercekligi
// giris ekranina tasimaktan ibarettir, yeni bir guvenlik acigi ACMAZ.
const ASGARI_SIFRE = 8; // api/schemas.py::KayitIstek ile AYNI

export default function Giris({ onGirisBasarili, onCikisYapildi, koyuMu, temaToggle }) {
  const [kullaniciAdi, setKullaniciAdi] = useState("");
  const [sifre, setSifre] = useState("");
  const [mesaj, setMesaj] = useState(null); // {tip, baslik, metin}
  const [calisiyor, setCalisiyor] = useState(false);
  const [mevcutRol, setMevcutRol] = useState(rolAl());
  const [mevcutKullaniciAdi, setMevcutKullaniciAdi] = useState(kullaniciAdiAl());
  const [aktifSekme, setAktifSekme] = useState("giris");

  // MOCK MOD TESPITI - neden gerekli:
  // Varsayilan yapilandirmada (JWT_AKTIF ayarli degil) POST /token
  // bilerek 400 doner: "mock modda /token gerekmez". Onceki surumde
  // "Giris yap" dugmesi aktif duruyordu, kullanici basiyor ve teknik
  // bir hata mesaji goruyordu - calismayan bir dugme sunmak yerine
  // durumu onceden soyluyoruz. Bilgi GET / uzerinden geliyor
  // (api/main.py::kok -> jwt_dogrulama).
  const [jwtModu, setJwtModu] = useState(null); // "mock" | "gercek" | null

  useEffect(() => {
    sistemBilgisi()
      .then((b) => setJwtModu(b?.jwt_dogrulama ?? null))
      .catch(() => setJwtModu(null)); // API kapaliysa varsayim yapmiyoruz
  }, []);

  const mockMod = jwtModu === "mock";

  const hataMetni = (e) =>
    // API'nin KENDI mesajini gosteriyoruz. Ozellikle /token mock modda
    // "mock modda /token gerekmez" diye aciklayici bir 400 doner; bunu
    // genel bir "giris basarisiz" ile degistirmek kullaniciyi yanlis
    // yone iterdi (bkz. api/client.js::girisYap).
    e.response?.data?.detail ?? e.message;

  const giris = async () => {
    setCalisiyor(true);
    setMesaj(null);
    try {
      let rol;
      if (mockMod) {
        // Sunucu POST /token'i mock modda kasitli olarak reddediyor
        // (api/main.py::token_al). Sunucu zaten bu modda herhangi bir
        // Bearer token'i sorgusuz kabul ettigi icin (api/auth.py), burada
        // ayni gercekligi yerel olarak uyguluyoruz: kimlik dogrulanmadan
        // oturum acilir, kendi kendine kayit olan kullanicilarla AYNI
        // "musteri" rolu atanir.
        rol = "musteri";
        tokenKaydet(`mock-token-${kullaniciAdi}`);
        rolKaydet(rol);
      } else {
        const yanit = await girisYap(kullaniciAdi, sifre);
        rol = yanit.rol;
      }
      kullaniciAdiKaydet(kullaniciAdi);
      oturumBaslangiciKaydet();
      setMevcutRol(rol);
      setMevcutKullaniciAdi(kullaniciAdi);
      setMesaj({
        tip: "success",
        baslik: "Giriş yapıldı",
        metin: `Rolünüz: ${rol}.`,
      });
      onGirisBasarili?.();
    } catch (e) {
      setMesaj({ tip: "error", baslik: "Giriş yapılamadı", metin: hataMetni(e) });
    } finally {
      setCalisiyor(false);
    }
  };

  const kayit = async () => {
    if (sifre.length < ASGARI_SIFRE) {
      setMesaj({
        tip: "error",
        baslik: "Şifre çok kısa",
        metin: `Şifre en az ${ASGARI_SIFRE} karakter olmalı.`,
      });
      return;
    }
    setCalisiyor(true);
    setMesaj(null);
    try {
      const yanit = await kayitOl(kullaniciAdi, sifre);
      // Kayit uc noktasi token dondurmez (bkz. api/schemas.py::KayitYanit) -
      // JWT_AKTIF=true iken kullanici ayrica giris yapmali; mock modda ise
      // token zaten sorgulanmadigi icin kayit sonrasi dogrudan oturum acilir.
      rolKaydet(yanit.rol);
      kullaniciAdiKaydet(yanit.kullanici_adi);
      tokenKaydet(`mock-token-${yanit.kullanici_adi}`);
      oturumBaslangiciKaydet();
      setMevcutRol(yanit.rol);
      setMevcutKullaniciAdi(yanit.kullanici_adi);
      setMesaj({
        tip: "success",
        baslik: "Kayıt oluşturuldu",
        metin: `${yanit.kullanici_adi} — rol: ${yanit.rol}.`,
      });
      onGirisBasarili?.();
    } catch (e) {
      setMesaj({ tip: "error", baslik: "Kayıt yapılamadı", metin: hataMetni(e) });
    } finally {
      setCalisiyor(false);
    }
  };

  const cikis = () => {
    tokenSil();
    rolSil();
    kullaniciAdiSil();
    oturumBaslangiciSil();
    setMevcutRol(null);
    setMevcutKullaniciAdi(null);
    setMesaj(null);
    onCikisYapildi?.();
  };

  // Şifre uzunluğunun anlık görsel doğrulaması (min 8 karakter)
  const sifreGecerli = sifre.length >= ASGARI_SIFRE;

  const sekmeOgeleri = [
    {
      key: "giris",
      label: (
        <span>
          <LoginOutlined /> Giriş Yap
        </span>
      ),
      children: (
        <Space direction="vertical" style={{ width: "100%" }} size={14}>
          <div>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Kullanıcı adı
            </Text>
            <Input
              prefix={<UserOutlined style={{ color: "var(--yazi-soluk)" }} />}
              style={{ marginTop: 4 }}
              value={kullaniciAdi}
              onChange={(e) => setKullaniciAdi(e.target.value)}
              autoComplete="username"
              placeholder="Kullanıcı adınızı girin"
            />
          </div>

          <div>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Şifre
            </Text>
            <Input.Password
              prefix={<LockOutlined style={{ color: "var(--yazi-soluk)" }} />}
              style={{ marginTop: 4 }}
              value={sifre}
              onChange={(e) => setSifre(e.target.value)}
              autoComplete="current-password"
              onPressEnter={giris}
              placeholder="Şifrenizi girin"
            />
            {/* Şifre alanında en az 8 karakter kuralı anlık görselleştirilir */}
            <div
              className={`giris-sifre-durum ${
                sifreGecerli ? "gecerli" : "gecersiz"
              }`}
            >
              {sifreGecerli ? (
                <>
                  <CheckCircleOutlined /> Şifre uzunluğu yeterli ({sifre.length}/{ASGARI_SIFRE} karakter)
                </>
              ) : (
                <>
                  <ExclamationCircleOutlined /> En az {ASGARI_SIFRE} karakter olmalı ({sifre.length}/{ASGARI_SIFRE})
                </>
              )}
            </div>
          </div>

          <Button
            type="primary"
            block
            size="large"
            icon={<LoginOutlined />}
            onClick={giris}
            loading={calisiyor}
            disabled={!kullaniciAdi || !sifre}
            style={{ marginTop: 6 }}
          >
            Giriş yap
          </Button>
        </Space>
      ),
    },
    {
      key: "kayit",
      label: (
        <span>
          <UserAddOutlined /> Kayıt Ol
        </span>
      ),
      children: (
        <Space direction="vertical" style={{ width: "100%" }} size={14}>
          <div>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Kullanıcı adı
            </Text>
            <Input
              prefix={<UserOutlined style={{ color: "var(--yazi-soluk)" }} />}
              style={{ marginTop: 4 }}
              value={kullaniciAdi}
              onChange={(e) => setKullaniciAdi(e.target.value)}
              autoComplete="username"
              placeholder="Yeni kullanıcı adı belirleyin"
            />
          </div>

          <div>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Şifre (en az {ASGARI_SIFRE} karakter)
            </Text>
            <Input.Password
              prefix={<LockOutlined style={{ color: "var(--yazi-soluk)" }} />}
              style={{ marginTop: 4 }}
              value={sifre}
              onChange={(e) => setSifre(e.target.value)}
              autoComplete="new-password"
              onPressEnter={kayit}
              placeholder="Şifrenizi belirleyin"
            />
            {/* Şifre alanında en az 8 karakter kuralı anlık görselleştirilir */}
            <div
              className={`giris-sifre-durum ${
                sifreGecerli ? "gecerli" : "gecersiz"
              }`}
            >
              {sifreGecerli ? (
                <>
                  <CheckCircleOutlined /> Şifre uzunluğu yeterli ({sifre.length}/{ASGARI_SIFRE} karakter)
                </>
              ) : (
                <>
                  <ExclamationCircleOutlined /> En az {ASGARI_SIFRE} karakter olmalı ({sifre.length}/{ASGARI_SIFRE})
                </>
              )}
            </div>
          </div>

          {/* Rol SECTIREN bir alan BILEREK yok: sunucu her zaman "musteri"
              atar (api/schemas.py::KayitIstek). Buraya bir rol secici
              koymak, herkesin kendini yonetici yapabilmesi demek olurdu. */}

          <Button
            type="primary"
            block
            size="large"
            icon={<UserAddOutlined />}
            onClick={kayit}
            loading={calisiyor}
            disabled={!kullaniciAdi || !sifre}
            style={{ marginTop: 6 }}
          >
            Kayıt ol
          </Button>
        </Space>
      ),
    },
  ];

  // Oturum acikken bu ekran artik Giris/Kayit sekmelerini degil, Ayarlar
  // sayfasini gosterir (bkz. kullanici talebi: "girisi ciktan sonraki
  // giris cikis sayfasi Ayarlar'a donusmeli"). Sekmeler yalnizca oturum
  // YOKKEN (App.jsx'teki kapi ekrani) gorunur.
  if (mevcutRol) {
    return (
      <Ayarlar
        kullaniciAdi={mevcutKullaniciAdi}
        rol={mevcutRol}
        onCikis={cikis}
        koyuMu={koyuMu}
        temaToggle={temaToggle}
      />
    );
  }

  return (
    <div className="giris-kapsayici">
      <div className="giris-karti">
        {/* Başlık ve Logo Amblemi */}
        <div className="giris-baslik-blogu">
          <img
            className="giris-logo-amblem"
            src={`${import.meta.env.BASE_URL}logo.png`}
            alt="KatılımAI"
          />
          <Title level={3} style={{ margin: 0, letterSpacing: "-0.5px" }}>
            KatılımAI Portal
          </Title>
          <Paragraph type="secondary" style={{ fontSize: 13, marginTop: 4, marginBottom: 0 }}>
            Katılım bankacılığı yapay zekâ analiz platformu
          </Paragraph>
        </div>

        {/* Giriş Yap / Kayıt Ol Sekmeleri */}
        <Tabs
          activeKey={aktifSekme}
          onChange={setAktifSekme}
          centered
          items={sekmeOgeleri}
        />

        {/* Hata / Başarı bildirim mesajı kartın İÇİNDE, formun hemen altında */}
        {mesaj && (
          <Alert
            type={mesaj.tip}
            message={mesaj.baslik}
            description={mesaj.metin}
            showIcon
            style={{ marginTop: 16 }}
          />
        )}
      </div>
    </div>
  );
}


import { useState } from "react";
import {
  Alert,
  Button,
  Collapse,
  Input,
  Space,
  Tabs,
  Tag,
  Typography,
} from "antd";
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  LockOutlined,
  LoginOutlined,
  LogoutOutlined,
  UserAddOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { girisYap, kayitOl, rolAl, rolSil, tokenSil } from "../api/client";

const { Title, Text, Paragraph } = Typography;

// Yagmur rol tabanli erisimi kurdu (POST /kayit, POST /token, rol_gerekli)
// ama arayuz hicbirini cagirmiyordu - client.js sabit "mock-token-havin"
// kullaniyordu. TokenYanit semasindaki `rol` alani kendi aciklamasinda
// "arayuzun menuyu role gore cizebilmesi icin" diyor; bu ekran o alani
// nihayet isteyen taraftir.

const ASGARI_SIFRE = 8; // api/schemas.py::KayitIstek ile AYNI

export default function Giris() {
  const [kullaniciAdi, setKullaniciAdi] = useState("");
  const [sifre, setSifre] = useState("");
  const [mesaj, setMesaj] = useState(null); // {tip, baslik, metin}
  const [calisiyor, setCalisiyor] = useState(false);
  const [mevcutRol, setMevcutRol] = useState(rolAl());
  const [aktifSekme, setAktifSekme] = useState("giris");

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
      const yanit = await girisYap(kullaniciAdi, sifre);
      setMevcutRol(yanit.rol);
      setMesaj({
        tip: "success",
        baslik: "Giriş yapıldı",
        metin: `Rolünüz: ${yanit.rol}. Menü bu role göre çizilecek.`,
      });
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
      setMesaj({
        tip: "success",
        baslik: "Kayıt oluşturuldu",
        metin: `${yanit.kullanici_adi} — rol: ${yanit.rol}. Şimdi giriş yapabilirsiniz.`,
      });
    } catch (e) {
      setMesaj({ tip: "error", baslik: "Kayıt yapılamadı", metin: hataMetni(e) });
    } finally {
      setCalisiyor(false);
    }
  };

  const cikis = () => {
    tokenSil();
    rolSil();
    setMevcutRol(null);
    setMesaj({
      tip: "info",
      baslik: "Çıkış yapıldı",
      metin: "Menü yeniden tüm ekranları gösteriyor (rol bilinmiyor).",
    });
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
          {/* Rol Bilgisi Etiketi: Kayıt olan herkes müşteri rolü alır */}
          <div style={{ marginBottom: 4 }}>
            <Tag color="cyan" style={{ fontSize: 12, padding: "4px 8px", width: "100%", textAlign: "center" }}>
              👤 Kayıt olan tüm kullanıcılar varsayılan olarak "müşteri" rolü alır
            </Tag>
          </div>

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

  return (
    <div className="giris-kapsayici">
      <div className="giris-karti">
        {/* Başlık ve Logo Amblemi */}
        <div className="giris-baslik-blogu">
          <div className="giris-logo-amblem">K</div>
          <Title level={3} style={{ margin: 0, letterSpacing: "-0.5px" }}>
            KatılımAI Portal
          </Title>
          <Paragraph type="secondary" style={{ fontSize: 13, marginTop: 4, marginBottom: 0 }}>
            Katılım bankacılığı yapay zekâ analiz platformu
          </Paragraph>
        </div>

        {/* Oturum Açık ise Mevcut Rolü Belirgin Göster */}
        {mevcutRol && (
          <Alert
            type="info"
            showIcon
            message={
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  width: "100%",
                }}
              >
                <span>
                  Oturum Açık — Rol:{" "}
                  <Tag color="blue" style={{ fontWeight: 600, marginLeft: 4 }}>
                    {mevcutRol}
                  </Tag>
                </span>
                <Button
                  size="small"
                  type="text"
                  danger
                  onClick={cikis}
                  icon={<LogoutOutlined />}
                >
                  Çıkış
                </Button>
              </div>
            }
            style={{ marginBottom: 16 }}
          />
        )}

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

        {/* Demo Modu Uyarısı: Tek cümle + Katlanır Ayrıntı Bölümü */}
        <Alert
          type="warning"
          showIcon
          icon={<InfoCircleOutlined />}
          style={{ marginTop: 20 }}
          message="Demo modunda giriş yapmadan tüm ekranlara erişebilirsiniz."
          description={
            <Collapse
              ghost
              size="small"
              items={[
                {
                  key: "detay",
                  label: (
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      Teknik Ayrıntıyı Göster
                    </Text>
                  ),
                  children: (
                    <Text type="secondary" style={{ fontSize: 12, display: "block", lineHeight: 1.5 }}>
                      Sistem varsayılan olarak mock kimlik doğrulama ile çalışır: her istek
                      kabul edilir ve tüm ekranlar açık kalır. Gerçek yetkilendirme yalnızca
                      sunucu <code>JWT_AKTIF=true</code> ile başlatıldığında devreye girer.
                    </Text>
                  ),
                },
              ]}
            />
          }
        />
      </div>
    </div>
  );
}


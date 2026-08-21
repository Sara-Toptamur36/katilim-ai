import { useState } from "react";
import { Alert, Button, Card, Input, Space, Tag, Typography } from "antd";
import { LoginOutlined, UserAddOutlined } from "@ant-design/icons";
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

  return (
    <div>
      <Title level={3}>Giriş / Kayıt</Title>

      <Paragraph type="secondary" style={{ maxWidth: 640 }}>
        Kayıt olan herkes <strong>müşteri</strong> rolü alır. Banka çalışanı,
        denetleyici ve yönetici hesapları serbest kayıtla açılmaz — bunlar elle
        tanımlanır.
      </Paragraph>

      <Card size="small" style={{ maxWidth: 480 }}>
        <Space orientation="vertical" style={{ width: "100%" }} size={12}>
          {mevcutRol && (
            <Alert
              type="info"
              showIcon
              title={
                <span>
                  Oturum açık — rol: <Tag color="blue">{mevcutRol}</Tag>
                </span>
              }
              description="Menü bu role göre çiziliyor."
            />
          )}

          <div>
            <Text type="secondary">Kullanıcı adı</Text>
            <Input
              style={{ marginTop: 4 }}
              value={kullaniciAdi}
              onChange={(e) => setKullaniciAdi(e.target.value)}
              autoComplete="username"
            />
          </div>

          <div>
            <Text type="secondary">Şifre (en az {ASGARI_SIFRE} karakter)</Text>
            <Input.Password
              style={{ marginTop: 4 }}
              value={sifre}
              onChange={(e) => setSifre(e.target.value)}
              autoComplete="current-password"
              onPressEnter={giris}
            />
          </div>

          {/* Rol SECTIREN bir alan BILEREK yok: sunucu her zaman "musteri"
              atar (api/schemas.py::KayitIstek). Buraya bir rol secici
              koymak, herkesin kendini yonetici yapabilmesi demek olurdu. */}

          <Space wrap>
            <Button
              type="primary"
              icon={<LoginOutlined />}
              onClick={giris}
              loading={calisiyor}
              disabled={!kullaniciAdi || !sifre}
            >
              Giriş yap
            </Button>
            <Button
              icon={<UserAddOutlined />}
              onClick={kayit}
              loading={calisiyor}
              disabled={!kullaniciAdi || !sifre}
            >
              Kayıt ol
            </Button>
            {mevcutRol && <Button onClick={cikis}>Çıkış</Button>}
          </Space>

          {mesaj && (
            <Alert
              type={mesaj.tip}
              title={mesaj.baslik}
              description={mesaj.metin}
              showIcon
            />
          )}
        </Space>
      </Card>

      <Alert
        type="warning"
        showIcon
        style={{ maxWidth: 640, marginTop: 16 }}
        title="Demo modunda giriş gerekmez"
        description={
          <>
            Sistem varsayılan olarak <strong>mock kimlik doğrulama</strong> ile
            çalışır: her istek kabul edilir ve menüde hiçbir ekran gizlenmez.
            Gerçek yetkilendirme yalnızca sunucu <code>JWT_AKTIF=true</code> ile
            başlatıldığında devreye girer; bu ekran o modda anlam kazanır.
            Mock modda <code>Giriş yap</code> düğmesi, sunucunun açıklayıcı
            uyarısını olduğu gibi gösterir.
          </>
        }
      />
    </div>
  );
}

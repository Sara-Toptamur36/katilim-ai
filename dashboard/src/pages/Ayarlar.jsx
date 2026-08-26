import { useState } from "react";
import { Alert, Button, Card, Drawer, Input, Switch, Tag, Typography } from "antd";
import {
  BulbOutlined,
  CheckCircleFilled,
  LockOutlined,
  LogoutOutlined,
  SafetyOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { sifreDegistir, oturumBaslangiciAl } from "../api/client";

const { Title, Text, Paragraph } = Typography;

const ASGARI_SIFRE = 8; // api/schemas.py::SifreDegistirIstek ile AYNI

// Sifre gucu, backend'in ZORUNLU kildigi tek kural (min 8 karakter) disinda
// bir KISIT DEGIL - sadece kullaniciyi daha guclu bir sifreye tesvik eden
// gorsel bir gostergedir. Backend bunlari dogrulamiyor, o yuzden burada da
// "Kaydet" dugmesini bunlara BAGLI KILMIYORUZ (yalnizca min 8 + eslesme
// kontrol edilir) - aksi halde arayuz sunucunun uygulamadigi bir kurali
// varmis gibi gosterirdi.
const SIFRE_KURALLARI = [
  { anahtar: "uzunluk", etiket: `En az ${ASGARI_SIFRE} karakter uzunluğunda`, test: (s) => s.length >= ASGARI_SIFRE },
  { anahtar: "buyuk", etiket: "En az 1 büyük harf (A-Z)", test: (s) => /[A-Z]/.test(s) },
  { anahtar: "kucuk", etiket: "En az 1 küçük harf (a-z)", test: (s) => /[a-z]/.test(s) },
  { anahtar: "rakam", etiket: "En az 1 rakam (0-9)", test: (s) => /[0-9]/.test(s) },
  { anahtar: "ozel", etiket: "En az 1 özel karakter (!@#$%^&*)", test: (s) => /[!@#$%^&*]/.test(s) },
];

const GUC_ETIKETLERI = ["Zayıf", "Orta", "İyi", "Güçlü", "Çok Güçlü"];

function SifreDegistirPaneli({ acik, kapat, kullaniciAdi }) {
  const [mevcutSifre, setMevcutSifre] = useState("");
  const [yeniSifre, setYeniSifre] = useState("");
  const [tekrarSifre, setTekrarSifre] = useState("");
  const [calisiyor, setCalisiyor] = useState(false);
  const [mesaj, setMesaj] = useState(null);

  const kapatVeTemizle = () => {
    setMevcutSifre("");
    setYeniSifre("");
    setTekrarSifre("");
    setMesaj(null);
    kapat();
  };

  const karsilananKurallar = SIFRE_KURALLARI.filter((k) => k.test(yeniSifre));
  const guc = yeniSifre.length === 0 ? -1 : karsilananKurallar.length - 1;

  const kaydet = async () => {
    setMesaj(null);
    if (yeniSifre.length < ASGARI_SIFRE) {
      setMesaj({ tip: "error", metin: `Yeni şifre en az ${ASGARI_SIFRE} karakter olmalı.` });
      return;
    }
    if (yeniSifre !== tekrarSifre) {
      setMesaj({ tip: "error", metin: "Yeni şifreler birbiriyle eşleşmiyor." });
      return;
    }
    setCalisiyor(true);
    try {
      await sifreDegistir(kullaniciAdi, mevcutSifre, yeniSifre);
      setMesaj({ tip: "success", metin: "Şifreniz değiştirildi." });
      setMevcutSifre("");
      setYeniSifre("");
      setTekrarSifre("");
    } catch (e) {
      setMesaj({ tip: "error", metin: e.response?.data?.detail ?? e.message });
    } finally {
      setCalisiyor(false);
    }
  };

  return (
    <Drawer
      placement="left"
      open={acik}
      onClose={kapatVeTemizle}
      width={420}
      title={
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <SafetyOutlined style={{ fontSize: 18, color: "var(--marka-500)" }} />
          <span>Şifre Değiştir</span>
        </div>
      }
    >
      <Paragraph type="secondary" style={{ fontSize: 13 }}>
        Hesap güvenliğinizi artırmak için şifrenizi düzenli olarak değiştirmenizi öneririz.
      </Paragraph>

      <div style={{ display: "flex", flexDirection: "column", gap: 16, marginTop: 8 }}>
        <div>
          <Text type="secondary" style={{ fontSize: 13 }}>
            Mevcut Şifre
          </Text>
          <Input.Password
            prefix={<LockOutlined style={{ color: "var(--yazi-soluk)" }} />}
            style={{ marginTop: 4 }}
            value={mevcutSifre}
            onChange={(e) => setMevcutSifre(e.target.value)}
            autoComplete="current-password"
            placeholder="Mevcut şifrenizi girin"
          />
        </div>

        <div>
          <Text type="secondary" style={{ fontSize: 13 }}>
            Yeni Şifre
          </Text>
          <Input.Password
            prefix={<LockOutlined style={{ color: "var(--yazi-soluk)" }} />}
            style={{ marginTop: 4 }}
            value={yeniSifre}
            onChange={(e) => setYeniSifre(e.target.value)}
            autoComplete="new-password"
            placeholder={`Yeni şifre (min. ${ASGARI_SIFRE} karakter)`}
          />
        </div>

        <div>
          <Text type="secondary" style={{ fontSize: 13 }}>
            Yeni Şifre Tekrar
          </Text>
          <Input.Password
            prefix={<LockOutlined style={{ color: "var(--yazi-soluk)" }} />}
            style={{ marginTop: 4 }}
            value={tekrarSifre}
            onChange={(e) => setTekrarSifre(e.target.value)}
            autoComplete="new-password"
            onPressEnter={kaydet}
            placeholder="Yeni şifreyi tekrar girin"
          />
        </div>

        <div>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Şifre Gücü
          </Text>
          <div style={{ display: "flex", gap: 4, marginTop: 6 }}>
            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                style={{
                  height: 5,
                  flex: 1,
                  borderRadius: 3,
                  background: i <= guc ? "var(--marka-500)" : "var(--kenarlik)",
                }}
              />
            ))}
          </div>
          <Text type="secondary" style={{ fontSize: 11, display: "block", marginTop: 4 }}>
            {guc < 0 ? "Henüz değerlendirilmedi" : GUC_ETIKETLERI[guc]}
          </Text>
        </div>

        <div>
          <Text type="secondary" style={{ fontSize: 12, fontWeight: 600 }}>
            Şifre gereksinimleri
          </Text>
          <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
            {SIFRE_KURALLARI.map((k) => {
              const karsilandi = k.test(yeniSifre);
              return (
                <div key={k.anahtar} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
                  <CheckCircleFilled
                    style={{ color: karsilandi ? "#169276" : "var(--kenarlik)", fontSize: 15 }}
                  />
                  <Text type={karsilandi ? undefined : "secondary"}>{k.etiket}</Text>
                </div>
              );
            })}
          </div>
        </div>

        {mesaj && <Alert type={mesaj.tip} showIcon message={mesaj.metin} />}

        <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
          <Button block onClick={kapatVeTemizle}>
            İptal
          </Button>
          <Button
            type="primary"
            block
            icon={<LockOutlined />}
            loading={calisiyor}
            disabled={!mevcutSifre || !yeniSifre || !tekrarSifre}
            onClick={kaydet}
          >
            Kaydet
          </Button>
        </div>
      </div>
    </Drawer>
  );
}

export default function Ayarlar({ kullaniciAdi, rol, onCikis, koyuMu, temaToggle }) {
  const [panelAcik, setPanelAcik] = useState(false);

  const baslangic = oturumBaslangiciAl();
  const baslangicMetni = baslangic
    ? new Date(baslangic).toLocaleString("tr-TR", {
        day: "numeric",
        month: "long",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "—";

  const kartStil = { marginBottom: 16 };

  return (
    <div style={{ maxWidth: 640, margin: "0 auto" }}>
      <Title level={3} style={{ marginBottom: 4 }}>
        Ayarlar
      </Title>
      <Paragraph type="secondary" style={{ marginBottom: 24 }}>
        Uygulama tercihleri ve hesap ayarlarınızı buradan yönetebilirsiniz.
      </Paragraph>

      <Card
        style={kartStil}
        title={
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <UserOutlined style={{ color: "var(--marka-500)" }} />
            <span>Oturum Bilgileri</span>
          </div>
        }
      >
        <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 16, marginBottom: 16 }}>
          <div>
            <Text type="secondary" style={{ fontSize: 12, display: "block" }}>
              Kullanıcı
            </Text>
            <Text strong>{kullaniciAdi}</Text>{" "}
            <Tag color="blue" style={{ marginLeft: 4 }}>
              {rol}
            </Tag>
          </div>
          <div>
            <Text type="secondary" style={{ fontSize: 12, display: "block" }}>
              Oturum Başlangıcı
            </Text>
            <Text>{baslangicMetni}</Text>
          </div>
        </div>
        <Button danger block icon={<LogoutOutlined />} onClick={onCikis}>
          Çıkış Yap
        </Button>
      </Card>

      <Card
        style={kartStil}
        title={
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <BulbOutlined style={{ color: "var(--marka-500)" }} />
            <span>Görünüm Tercihleri</span>
          </div>
        }
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <Text strong>Karanlık Mod</Text>
            <Text type="secondary" style={{ fontSize: 12, display: "block" }}>
              Koyu tema kullanımını etkinleştirir
            </Text>
          </div>
          <Switch checked={koyuMu} onChange={temaToggle} />
        </div>
      </Card>

      <Card
        style={kartStil}
        title={
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <SafetyOutlined style={{ color: "var(--marka-500)" }} />
            <span>Güvenlik</span>
          </div>
        }
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <Text strong>Şifre Değiştir</Text>
            <Text type="secondary" style={{ fontSize: 12, display: "block" }}>
              Hesap şifrenizi güvenli bir şekilde güncelleyin
            </Text>
          </div>
          <Button icon={<LockOutlined />} onClick={() => setPanelAcik(true)}>
            Değiştir
          </Button>
        </div>
      </Card>

      <SifreDegistirPaneli
        acik={panelAcik}
        kapat={() => setPanelAcik(false)}
        kullaniciAdi={kullaniciAdi}
      />
    </div>
  );
}

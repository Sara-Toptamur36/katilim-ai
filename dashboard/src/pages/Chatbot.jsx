import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import { Input, Popconfirm, Button } from "antd";
import {
  SendOutlined,
  PlusOutlined,
  DeleteOutlined,
  UserOutlined,
  SwapOutlined,
  CalculatorOutlined,
  BookOutlined,
  FilterOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  InfoCircleOutlined,
  ClearOutlined,
} from "@ant-design/icons";
import { chatGonder, tokenAl, API_TABANI } from "../api/client";
import ChatMesaji from "../components/ChatMesaji";
import { useAudit } from "../context/AuditContext";

// LocalStorage anahtarları
const SOHBET_ANAHTAR = "katilimai_sohbetler";
const GECMIS_ACIK_ANAHTAR = "katilimai_gecmis_acik";
const MAKS_SOHBET = 30;

// Benzersiz kimlik üretici
function kimlikUret() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

// Zaman etiketini biçimlendiren yardımcı fonksiyon
function zamanEtiketi(zamanDamgasi) {
  if (!zamanDamgasi) return "";
  const simdi = new Date();
  const hedef = new Date(zamanDamgasi);
  const farkMs = simdi - hedef;
  const farkGun = Math.floor(farkMs / (1000 * 60 * 60 * 24));

  if (farkGun === 0) {
    return hedef.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
  }
  if (farkGun === 1) return "dün";
  if (farkGun < 7) return `${farkGun} gün önce`;
  return hedef.toLocaleDateString("tr-TR", { day: "numeric", month: "short" });
}

// Örnek sorular
const ORNEK_SORULAR = [
  {
    ikon: <SwapOutlined />,
    baslik: "Kampanya karşılaştır",
    soru: "Kuveyt Türk ve Albaraka Türk kampanyalarını karşılaştır",
  },
  {
    ikon: <CalculatorOutlined />,
    baslik: "Taksit hesapla",
    soru: "100.000 TL, 36 ay vade, %2 kâr payı ile aylık taksit ne kadar?",
  },
  {
    ikon: <BookOutlined />,
    baslik: "Terim öğren",
    soru: "Kâr payı oranı ne demek?",
  },
  {
    ikon: <FilterOutlined />,
    baslik: "En avantajlıyı bul",
    soru: "En düşük kâr paylı kampanya hangisi?",
  },
];

// localStorage'dan sohbetleri oku
function sohbetleriOku() {
  try {
    const ham = localStorage.getItem(SOHBET_ANAHTAR);
    if (!ham) return [];
    const veri = JSON.parse(ham);
    return Array.isArray(veri) ? veri : [];
  } catch {
    return [];
  }
}

// localStorage'a sohbetleri yaz
function sohbetleriYaz(sohbetler) {
  try {
    localStorage.setItem(SOHBET_ANAHTAR, JSON.stringify(sohbetler));
  } catch {
    /* localStorage dolu olabilir */
  }
}

// Geçmiş paneli varsayılan açık/kapalı durumunu oku
function gecmisVarsayilan() {
  try {
    const kayitli = localStorage.getItem(GECMIS_ACIK_ANAHTAR);
    if (kayitli !== null) return kayitli === "true";
  } catch {
    /* localStorage okunamazsa pencere genişliğine göre davran */
  }
  return window.innerWidth >= 1200;
}

// === Bekleme animasyonu (üç nokta) alt bileşeni ===
function BeklemeBalonu({ bekleniyor }) {
  const [saniye, setSaniye] = useState(0);

  useEffect(() => {
    if (!bekleniyor) {
      setSaniye(0);
      return;
    }
    const zamanlayici = setInterval(() => setSaniye((o) => o + 1), 1000);
    return () => clearInterval(zamanlayici);
  }, [bekleniyor]);

  if (!bekleniyor) return null;

  return (
    <div className="sohbet-mesaj-satiri asistan">
      {/* Asistan avatarı */}
      <img
        className="sohbet-avatar asistan-avatar"
        src={`${import.meta.env.BASE_URL}logo-64.png`}
        alt=""
      />
      <div className="sohbet-balon asistan-balon">
        {/* Üç nokta animasyonu */}
        <div className="bekleme-noktalar">
          <span className="bekleme-nokta" />
          <span className="bekleme-nokta" />
          <span className="bekleme-nokta" />
        </div>
        <div className="bekleme-sayac">
          yanıt bekleniyor… {saniye} sn
        </div>
        {saniye >= 10 && (
          <div className="bekleme-isinma-notu">
            İlk soru, dil modeli belleğe yüklenirken daha uzun sürebilir. Sonraki sorular hızlanacak.
          </div>
        )}
      </div>
    </div>
  );
}

export default function Chatbot() {
  // Tüm sohbetler ve aktif sohbet kimliği
  const [sohbetler, setSohbetler] = useState(sohbetleriOku);
  const [aktifId, setAktifId] = useState(() => {
    const mevcut = sohbetleriOku();
    return mevcut.length > 0 ? mevcut[0].id : null;
  });

  // Geçmiş paneli açık/kapalı
  const [gecmisAcik, setGecmisAcik] = useState(gecmisVarsayilan);

  // Girdi ve bekleniyor durumu
  const [girdi, setGirdi] = useState("");
  const [bekleniyor, setBekleniyor] = useState(false);
  // Sara'nin ekledigi Audit gorunumu: acikken her asistan yanitinin
  // altinda o sorguya ait niyet ve gecikme ozeti gorunur. Ayrintili
  // inceleme Juri Audit Paneli'nde - burada yalnizca hizli bakis.
  const [auditAcik, setAuditAcik] = useState(false);

  // Audit bağlamı
  const { auditEkle } = useAudit();

  // Mesaj listesinin altına kaydırma referansı
  const mesajSonuRef = useRef(null);
  const girdiFocusRef = useRef(null);

  // Aktif sohbetin mesajları (türetilmiş değer)
  const aktifSohbet = useMemo(
    () => sohbetler.find((s) => s.id === aktifId) || null,
    [sohbetler, aktifId]
  );
  const mesajlar = aktifSohbet?.mesajlar || [];

  // Sohbet değişimlerini localStorage'a yaz
  useEffect(() => {
    sohbetleriYaz(sohbetler);
  }, [sohbetler]);

  // Geçmiş açık/kapalı durumunu localStorage'a yaz
  useEffect(() => {
    try {
      localStorage.setItem(GECMIS_ACIK_ANAHTAR, String(gecmisAcik));
    } catch { /* yoksay */ }
  }, [gecmisAcik]);

  // Yeni mesaj eklenince alta kaydır
  useEffect(() => {
    mesajSonuRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mesajlar.length, bekleniyor]);

  // === Sohbet yönetim fonksiyonları ===

  // Yeni sohbet oluştur
  const yeniSohbet = useCallback(() => {
    const yeni = { id: kimlikUret(), baslik: "Yeni sohbet", mesajlar: [], zaman: Date.now() };
    setSohbetler((onceki) => {
      const guncellenmis = [yeni, ...onceki].slice(0, MAKS_SOHBET);
      return guncellenmis;
    });
    setAktifId(yeni.id);
    setGirdi("");
    setBekleniyor(false);
  }, []);

  // Sohbet seç
  const sohbetSec = useCallback((id) => {
    setAktifId(id);
    setBekleniyor(false);
    setGirdi("");
  }, []);

  // Sohbet sil
  const sohbetSil = useCallback((id) => {
    setSohbetler((onceki) => {
      const kalan = onceki.filter((s) => s.id !== id);
      // Aktif sohbet silindiyse ilkine geç veya null
      if (id === aktifId) {
        setAktifId(kalan.length > 0 ? kalan[0].id : null);
      }
      return kalan;
    });
  }, [aktifId]);

  // Aktif sohbetin mesajlarını güncelle (yardımcı)
  const mesajGuncelle = useCallback((guncelleyici) => {
    setSohbetler((onceki) =>
      onceki.map((s) => {
        if (s.id !== aktifId) return s;
        const yeniMesajlar = typeof guncelleyici === "function"
          ? guncelleyici(s.mesajlar)
          : guncelleyici;
        // Başlığı ilk kullanıcı mesajından al
        let baslik = s.baslik;
        if (baslik === "Yeni sohbet") {
          const ilkKullanici = yeniMesajlar.find((m) => m.rol === "kullanici");
          if (ilkKullanici) baslik = ilkKullanici.metin.slice(0, 40);
        }
        return { ...s, mesajlar: yeniMesajlar, baslik, zaman: Date.now() };
      })
    );
  }, [aktifId]);

  // === Mesaj gönderme fonksiyonu ===
  // Aktif yol: Sara'nin /chat endpoint'i su an tek seferde (non-streaming)
  // yanit donuyor. Bu fonksiyon bunun icin yazildi.
  // Aktif sohbetin mesajlarini siler ama sohbet kaydini korur.
  // 'Yeni Sohbet'ten farki: gecmis listesinde yeni satir acmaz.
  const aktifSohbetiTemizle = useCallback(() => {
    setSohbetler((onceki) =>
      onceki.map((s) =>
        s.id === aktifId ? { ...s, mesajlar: [], zaman: Date.now() } : s
      )
    );
  }, [aktifId]);

  // TUM gecmisi siler. "Temizle" dugmesinden farki: o yalnizca AKTIF
  // sohbetin mesajlarini bosaltir, gecmis listesi oldugu gibi kalir.
  // Demo/sunum oncesi eski sohbetlerin ekranda gorunmesi istenmiyordu -
  // tek tek silmek yerine tek dugme.
  const tumGecmisiSil = useCallback(() => {
    setSohbetler([]);
    setAktifId(null);
    setGirdi("");
    setBekleniyor(false);
  }, []);

  const gonder = useCallback(async (metin) => {
    const soru = (metin || girdi).trim();
    if (!soru) return;

    // Aktif sohbet yoksa yenisini oluştur
    let hedefId = aktifId;
    if (!hedefId) {
      const yeni = { id: kimlikUret(), baslik: soru.slice(0, 40), mesajlar: [], zaman: Date.now() };
      setSohbetler((onceki) => [yeni, ...onceki].slice(0, MAKS_SOHBET));
      hedefId = yeni.id;
      setAktifId(yeni.id);
    }

    // Kullanıcı mesajını ekle
    const kullaniciMesaji = { rol: "kullanici", metin: soru };
    setSohbetler((onceki) =>
      onceki.map((s) => {
        if (s.id !== hedefId) return s;
        const yeniMesajlar = [...s.mesajlar, kullaniciMesaji];
        let baslik = s.baslik;
        if (baslik === "Yeni sohbet") baslik = soru.slice(0, 40);
        return { ...s, mesajlar: yeniMesajlar, baslik, zaman: Date.now() };
      })
    );

    setGirdi("");
    setBekleniyor(true);

    try {
      const yanit = await chatGonder(soru);
      const botMesaji = {
        rol: "bot",
        metin: yanit.cevap,
        kaynaklar: yanit.kaynaklar,
        confidence: yanit.confidence,
        fallback: yanit.fallback,
        // Md. 5.5 - Terminoloji Kontrolu. Bu iki alan backend'de zaten
        // uretiliyordu ama yalnizca audit blogunda kaliyor, kullaniciya
        // hic gosterilmiyordu. Uc durumlu okunur (bkz. ChatMesaji.jsx):
        // true = denetlendi/temiz, false = gelenek terim sizmis,
        // null = bu arac icin uygulanmaz (RAG/Sozluk).
        terminolojiTutarli: yanit.audit?.terminoloji_tutarli ?? null,
        terminolojiSorunlari: yanit.audit?.terminoloji_sorunlari ?? [],
        cagrilanArac: yanit.audit?.cagrilan_arac,
        // Audit gorunumu acildiginda gosterilecek ham blok.
        auditHam: yanit.audit ?? null,
        soruMetni: soru,  // DecisionTrace modalı için soru bağlamı
      };
      setSohbetler((onceki) =>
        onceki.map((s) => {
          if (s.id !== hedefId) return s;
          return { ...s, mesajlar: [...s.mesajlar, botMesaji], zaman: Date.now() };
        })
      );
      auditEkle(yanit.audit, soru);
    } catch (hata) {
      // Sorun 3: 90 saniyelik zaman aşımı (timeout) hatasında kullanıcıya özel mesaj verilir
      const zamanAsimi = hata?.code === "ECONNABORTED" || hata?.message?.includes("timeout");
      const botMetin = zamanAsimi
        ? "Yanıt 90 saniyede gelmedi - model hâlâ yükleniyor olabilir, tekrar deneyin."
        : "Üzgünüm, şu anda yanıt veremiyorum. Lütfen tekrar deneyin.";

      const hataMesaji = {
        rol: "bot",
        metin: botMetin,
        hata: true,
      };
      setSohbetler((onceki) =>
        onceki.map((s) => {
          if (s.id !== hedefId) return s;
          return { ...s, mesajlar: [...s.mesajlar, hataMesaji], zaman: Date.now() };
        })
      );

      // Sorun 2: Hata alan sorular da audit kaydına eklenir. Uydurma değer üretilmez.
      const hataMetni = zamanAsimi
        ? "Yanıt 90 saniyede gelmedi - model hâlâ yükleniyor olabilir, tekrar deneyin."
        : (hata?.response?.data?.detail || hata?.message || "Üzgünüm, şu anda yanıt veremiyorum. Lütfen tekrar deneyin.");

      auditEkle(
        {
          cagrilan_arac: null,
          hata: hataMetni,
          basarisiz: true,
        },
        soru
      );
    } finally {
      setBekleniyor(false);
    }
  }, [girdi, aktifId, auditEkle]);

  // === SSE Streaming gönderme (/chat/stream) ===
  // Backend: main.py::chat_stream — kelime kelime SSE + bittiğinde audit/kaynaklar.
  // SSE formatı: "data: {...}\n\n" satırları
  //   { token: "kelime " }         — her kelimede
  //   { done: true, audit: {}, kaynaklar: [], fallback: bool }  — sonda
  const gonderStreaming = useCallback(async (metin) => {
    const soru = (metin || girdi).trim();
    if (!soru) return;

    let hedefId = aktifId;
    if (!hedefId) {
      const yeni = { id: kimlikUret(), baslik: soru.slice(0, 40), mesajlar: [], zaman: Date.now() };
      setSohbetler((onceki) => [yeni, ...onceki].slice(0, MAKS_SOHBET));
      hedefId = yeni.id;
      setAktifId(yeni.id);
    }

    const kullaniciMesaji = { rol: "kullanici", metin: soru };
    setSohbetler((onceki) =>
      onceki.map((s) => {
        if (s.id !== hedefId) return s;
        const yeniMesajlar = [...s.mesajlar, kullaniciMesaji];
        let baslik = s.baslik;
        if (baslik === "Yeni sohbet") baslik = soru.slice(0, 40);
        return { ...s, mesajlar: yeniMesajlar, baslik, zaman: Date.now() };
      })
    );

    setGirdi("");
    setBekleniyor(true);

    // Bot placeholer — streaming:true ile
    const streamId = kimlikUret();
    setSohbetler((onceki) =>
      onceki.map((s) => {
        if (s.id !== hedefId) return s;
        return {
          ...s,
          mesajlar: [
            ...s.mesajlar,
            { rol: "bot", metin: "", streaming: true, _streamId: streamId, soruMetni: soru },
          ],
          zaman: Date.now(),
        };
      })
    );

    try {
      const yanit = await fetch(`${API_TABANI}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${tokenAl()}`,
        },
        body: JSON.stringify({ soru }),
      });

      if (!yanit.ok) throw new Error(`HTTP ${yanit.status}`);

      const reader = yanit.body.getReader();
      const decoder = new TextDecoder();
      let tampon = "";

      const botMesajGuncelle = (guncelleyici) =>
        setSohbetler((onceki) =>
          onceki.map((s) => {
            if (s.id !== hedefId) return s;
            return {
              ...s,
              mesajlar: s.mesajlar.map((m) =>
                m._streamId === streamId ? guncelleyici(m) : m
              ),
            };
          })
        );

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        tampon += decoder.decode(value, { stream: true });

        // SSE satırlarını ayır
        const satirlar = tampon.split("\n");
        tampon = satirlar.pop() ?? ""; // tamamlanmamış satırı tampon'a geri al

        for (const satir of satirlar) {
          if (!satir.startsWith("data: ")) continue;
          try {
            const olay = JSON.parse(satir.slice(6));

            if (olay.token !== undefined) {
              // Her token gönderimde metni ekle
              botMesajGuncelle((m) => ({ ...m, metin: m.metin + olay.token }));
            } else if (olay.done) {
              // Tamamlandı — audit + kaynaklar set et, streaming kapat
              botMesajGuncelle((m) => ({
                ...m,
                streaming: false,
                kaynaklar: olay.kaynaklar ?? [],
                fallback: olay.fallback ?? false,
                confidence: olay.audit?.response_confidence ?? null,
                terminolojiTutarli: olay.audit?.terminoloji_tutarli ?? null,
                terminolojiSorunlari: olay.audit?.terminoloji_sorunlari ?? [],
                cagrilanArac: olay.audit?.cagrilan_arac,
                auditHam: olay.audit ?? null,
              }));
              auditEkle(olay.audit, soru);
            }
          } catch { /* geçersiz JSON satırını yoksay */ }
        }
      }

      // Stream kapalıysa ama done olayı gelmediyse streaming kapat
      botMesajGuncelle((m) => m.streaming ? { ...m, streaming: false } : m);

    } catch {
      setSohbetler((onceki) =>
        onceki.map((s) => {
          if (s.id !== hedefId) return s;
          return {
            ...s,
            mesajlar: s.mesajlar.map((m) =>
              m._streamId === streamId
                ? { rol: "bot", metin: "Bağlantı sırasında bir sorun oluştu. Lütfen tekrar deneyin.", hata: true }
                : m
            ),
          };
        })
      );
    } finally {
      setBekleniyor(false);
    }
  }, [girdi, aktifId, auditEkle]);

  // Enter = gönder, Shift+Enter = alt satır
  // Streaming aktif: /chat/stream SSE kullanılıyor.
  const tusYakala = useCallback((e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      gonderStreaming();
    }
  }, [gonderStreaming]);

  // Örnek soru tıklandığında
  const ornekSoruGonder = useCallback((soru) => {
    gonderStreaming(soru);
  }, [gonderStreaming]);

  return (
    <div className="sohbet-sayfa">
      {/* === SOL: Sohbet geçmişi paneli === */}
      <aside className={`sohbet-gecmis-panel ${gecmisAcik ? "acik" : "kapali"}`}>
        <div className="sohbet-gecmis-icerik">
          {/* Yeni Sohbet düğmesi */}
          <button className="yeni-sohbet-dugme" onClick={yeniSohbet}>
            <PlusOutlined />
            <span>Yeni Sohbet</span>
          </button>

          {/* Tum gecmisi sil - yalnizca silinecek sohbet varken gorunur */}
          {sohbetler.length > 0 && (
            <Popconfirm
              title="Tüm sohbet geçmişi silinsin mi?"
              description={`${sohbetler.length} sohbet kalıcı olarak silinecek.`}
              okText="Hepsini sil"
              cancelText="Vazgeç"
              okButtonProps={{ danger: true }}
              onConfirm={tumGecmisiSil}
            >
              <button className="gecmisi-sil-dugme" type="button">
                <DeleteOutlined />
                <span>Geçmişi sil ({sohbetler.length})</span>
              </button>
            </Popconfirm>
          )}

          {/* Sohbet listesi */}
          {sohbetler.length === 0 ? (
            <div className="sohbet-gecmis-bos">Henüz sohbet yok</div>
          ) : (
            <div className="sohbet-gecmis-liste">
              {sohbetler.map((s) => (
                <div
                  key={s.id}
                  className={`sohbet-gecmis-satir ${s.id === aktifId ? "aktif" : ""}`}
                  onClick={() => sohbetSec(s.id)}
                >
                  <div className="sohbet-gecmis-satir-icerik">
                    <div className="sohbet-gecmis-baslik">{s.baslik}</div>
                    <div className="sohbet-gecmis-zaman">{zamanEtiketi(s.zaman)}</div>
                  </div>
                  <Popconfirm
                    title="Silinsin mi?"
                    onConfirm={(e) => {
                      e?.stopPropagation();
                      sohbetSil(s.id);
                    }}
                    onCancel={(e) => e?.stopPropagation()}
                    okText="Sil"
                    cancelText="Vazgeç"
                  >
                    <button
                      className="sohbet-sil-dugme"
                      onClick={(e) => e.stopPropagation()}
                      aria-label="Sohbeti sil"
                    >
                      <DeleteOutlined />
                    </button>
                  </Popconfirm>
                </div>
              ))}
            </div>
          )}
        </div>
      </aside>

      {/* === SAĞ: Ana sohbet alanı === */}
      <div className="sohbet-ana-alan">
        {/* Geçmiş açma/kapama düğmesi */}
        <div className="sohbet-ust-bar">
          <button
            className="gecmis-toggle-dugme"
            onClick={() => setGecmisAcik((o) => !o)}
            aria-label={gecmisAcik ? "Geçmişi kapat" : "Geçmişi aç"}
            title={gecmisAcik ? "Geçmişi kapat" : "Geçmişi aç"}
          >
            {gecmisAcik ? <MenuFoldOutlined /> : <MenuUnfoldOutlined />}
          </button>

          {/* Sara'nin Audit gorunumu + sohbet temizleme */}
          <div className="sohbet-ust-bar-sag">
            <Button
              size="small"
              icon={<InfoCircleOutlined />}
              onClick={() => setAuditAcik((a) => !a)}
              type={auditAcik ? "primary" : "default"}
              title="Audit detaylarını göster / gizle"
            >
              Audit
            </Button>
            <Popconfirm
              title="Bu sohbetin mesajları silinsin mi?"
              okText="Sil"
              cancelText="Vazgeç"
              onConfirm={aktifSohbetiTemizle}
            >
              <Button
                size="small"
                danger
                icon={<ClearOutlined />}
                disabled={mesajlar.length === 0}
                title="Sohbet mesajlarını temizle"
              >
                Temizle
              </Button>
            </Popconfirm>
          </div>
        </div>

        {/* Mesaj akışı veya boş ekran */}
        <div className="sohbet-mesaj-alani">
          {mesajlar.length === 0 && !bekleniyor ? (
            /* === BOŞ EKRAN === */
            <div className="sohbet-bos-ekran">
              <img
                className="sohbet-bos-amblem"
                src={`${import.meta.env.BASE_URL}logo.png`}
                alt=""
              />
              <h2 className="sohbet-bos-baslik">Size nasıl yardımcı olabilirim?</h2>
              <p className="sohbet-bos-aciklama">
                Katılım bankası kampanyaları, karşılaştırma ve finansman hesaplaması hakkında soru sorun.
              </p>
              <div className="sohbet-ornek-grid">
                {ORNEK_SORULAR.map((ornek, i) => (
                  <button
                    key={i}
                    className="sohbet-ornek-kart"
                    onClick={() => ornekSoruGonder(ornek.soru)}
                  >
                    <span className="sohbet-ornek-ikon">{ornek.ikon}</span>
                    <span className="sohbet-ornek-baslik">{ornek.baslik}</span>
                    <span className="sohbet-ornek-soru">{ornek.soru}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* === MESAJ AKIŞI === */
            <div className="sohbet-mesaj-listesi">
              {mesajlar.map((m, i) => {
                const kullaniciMi = m.rol === "kullanici";
                return (
                  <div
                    key={i}
                    className={`sohbet-mesaj-satiri ${kullaniciMi ? "kullanici" : "asistan"}`}
                  >
                    {/* Avatar */}
                    {!kullaniciMi && (
                      <img
        className="sohbet-avatar asistan-avatar"
        src={`${import.meta.env.BASE_URL}logo-64.png`}
        alt=""
      />
                    )}
                    <div className={`sohbet-balon ${kullaniciMi ? "kullanici-balon" : "asistan-balon"}`}>
                      <ChatMesaji mesaj={m} />

                      {/* Audit gorunumu acikken hizli ozet. Ayrintili
                          inceleme Juri Audit Paneli'nde yapilir. */}
                      {auditAcik && !kullaniciMi && m.auditHam && (
                        <div className="sohbet-audit-ozet">
                          <div className="sohbet-audit-satir">
                            <InfoCircleOutlined />
                            <span>
                              niyet: <strong>{m.auditHam.intent ?? "—"}</strong>
                              {m.auditHam.intent_confidence != null && (
                                <> (güven {m.auditHam.intent_confidence})</>
                              )}
                              {" · "}araç: <strong>{m.auditHam.cagrilan_arac ?? "—"}</strong>
                              {m.auditHam.latency_ms != null && (
                                <> · {m.auditHam.latency_ms} ms</>
                              )}
                            </span>
                          </div>
                          <div className="sohbet-audit-not">
                            Model adayları, RAG benzerlik skorları ve çıkarım
                            çatışmaları için sol menüdeki{" "}
                            <strong>Jüri Audit Paneli</strong>'ne bakın.
                          </div>
                        </div>
                      )}
                    </div>
                    {kullaniciMi && (
                      <div className="sohbet-avatar kullanici-avatar">
                        <UserOutlined />
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Bekleme balonu */}
              <BeklemeBalonu bekleniyor={bekleniyor} />

              {/* Kaydırma hedefi */}
              <div ref={mesajSonuRef} />
            </div>
          )}
        </div>

        {/* === ALTTAKİ YAZMA ALANI === */}
        <div className="sohbet-yazma-alani">
          <div className="sohbet-yazma-kutu">
            <Input.TextArea
              ref={girdiFocusRef}
              value={girdi}
              onChange={(e) => setGirdi(e.target.value)}
              onKeyDown={tusYakala}
              placeholder="Örn: A Bankası'nın konut finansmanı oranı ne?"
              disabled={bekleniyor}
              autoSize={{ minRows: 1, maxRows: 4 }}
              className="sohbet-textarea"
            />
            <Button
              type="primary"
              shape="circle"
              icon={<SendOutlined />}
              onClick={() => gonderStreaming()}
              disabled={bekleniyor || !girdi.trim()}
              className="sohbet-gonder-dugme"
            />
          </div>
          <div className="sohbet-yazma-not">
            Yanıtlar kaynak gösterir; kaynak bulunamazsa sistem cevap üretmez.
          </div>
        </div>
      </div>
    </div>
  );
}

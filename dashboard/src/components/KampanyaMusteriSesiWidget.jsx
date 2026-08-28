import { useEffect, useState } from "react";
import { Alert, Skeleton, Space, Statistic, Tag, Typography } from "antd";
import { CommentOutlined, WarningOutlined } from "@ant-design/icons";
import { kampanyaMusteriSesiOzetiGetir } from "../api/client";

const { Text } = Typography;

/**
 * KampanyaMusteriSesiWidget — Kampanya detay sayfasında o kampanyaya
 * bağlanan şikayetlerin özet görünümü.
 *
 * RAPOR GEREKSİNİMİ: Kehribar border ile ayrılmış bölüm, tema dağılımı,
 * önem dağılımı, çözüm oranı ve son birkaç şikayet.
 */
export default function KampanyaMusteriSesiWidget({ kampanyaId }) {
  const [veri, setVeri] = useState(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(null);

  useEffect(() => {
    if (!kampanyaId) return;
    
    setYukleniyor(true);
    setHata(null);
    kampanyaMusteriSesiOzetiGetir(kampanyaId)
      .then(setVeri)
      .catch((e) => setHata(e.message))
      .finally(() => setYukleniyor(false));
  }, [kampanyaId]);

  if (!kampanyaId) return null;

  if (hata) {
    return (
      <Alert
        type="warning"
        className="musteri-sesi-alert"
        showIcon
        message="Müşteri Sesi verileri alınamadı"
        description={hata}
        style={{ marginTop: 16 }}
      />
    );
  }

  if (yukleniyor || !veri) {
    return <Skeleton active paragraph={{ rows: 3 }} style={{ marginTop: 16 }} />;
  }

  // Veri yoksa gösterme
  if (veri.toplam_sikayet === 0) {
    return (
      <div
        style={{
          marginTop: 16,
          padding: 16,
          background: "var(--musteri-sesi-amber-50)",
          border: "2px solid var(--musteri-sesi-amber-300)",
          borderRadius: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <CommentOutlined style={{ color: "var(--musteri-sesi-amber-600)", fontSize: 18 }} />
          <Text style={{ color: "var(--musteri-sesi-amber-900)", fontSize: 13 }}>
            Bu kampanya için henüz şikayet verisi bulunmamaktadır.
          </Text>
        </div>
      </div>
    );
  }

  // DUZELTME: backend (api/schemas.py::KampanyaMusteriSesiOzeti) `cozum_orani`
  // ile (çözüldü+kısmen)/(toplam-bilinmiyor) ORANINI ZATEN HESAPLAR - burada
  // TEKRAR hesaplamak hem gereksiz hem YANLIS (payda farkli tanimlaniyordu,
  // "cozulmedi" eski kodda paydaya HIC GIRMIYORDU). Null olabilir - "yeterli
  // veri yok" ile "%0 cozuldu" AYNI SEY DEGILDIR.
  const cozumOraniYuzde =
    veri.cozum_orani != null ? Math.round(veri.cozum_orani * 100) : null;
  // `temalar` bir dict'tir ({"REWARD_NOT_CREDITED": 5, ...}) - `tema_dagilimi`
  // adinda bir alan YOK, dizi de degil. Buyukten kucuge sirali listeye cevrilir.
  const temaListesi = Object.entries(veri.temalar || {})
    .sort((a, b) => b[1] - a[1])
    .map(([tema, sayi]) => ({ tema, sayi }));

  return (
    <div
      style={{
        marginTop: 16,
        padding: 20,
        background: "var(--musteri-sesi-amber-50)",
        border: "2px solid var(--musteri-sesi-amber-300)",
        borderRadius: 12,
      }}
    >
      {/* Başlık */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 16,
        }}
      >
        <CommentOutlined
          style={{
            color: "var(--musteri-sesi-amber-600)",
            fontSize: 20,
          }}
        />
        <span
          style={{
            fontSize: 16,
            fontWeight: 700,
            color: "var(--musteri-sesi-amber-900)",
          }}
        >
          Müşteri Sesi (Deneyim Sinyali)
        </span>
        <Tag
          style={{
            background: "var(--musteri-sesi-amber-200)",
            border: "1px solid var(--musteri-sesi-amber-400)",
            color: "var(--musteri-sesi-amber-900)",
            fontSize: 10,
            fontWeight: 600,
            marginLeft: "auto",
          }}
        >
          SENTETİK
        </Tag>
      </div>

      {/* İstatistikler */}
      <Space size="large" style={{ marginBottom: 16 }} wrap>
        <Statistic
          title="Toplam Şikayet"
          value={veri.toplam_sikayet}
          valueStyle={{ fontSize: 22, fontWeight: 650 }}
        />
        <Statistic
          title="Yüksek Önem"
          value={veri.onem_dagilimi.YUKSEK || 0}
          valueStyle={{ fontSize: 22, fontWeight: 650, color: "#f57c00" }}
          prefix={<WarningOutlined />}
        />
        <Statistic
          title="Çözüm Oranı"
          value={cozumOraniYuzde != null ? cozumOraniYuzde : "—"}
          suffix={cozumOraniYuzde != null ? "%" : ""}
          valueStyle={{
            fontSize: 22,
            fontWeight: 650,
            color:
              cozumOraniYuzde == null
                ? "var(--yazi-soluk)"
                : cozumOraniYuzde > 50
                ? "#52c41a"
                : "#faad14",
          }}
        />
      </Space>

      {/* Tema Dağılımı */}
      {temaListesi.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Text
            strong
            style={{
              fontSize: 13,
              color: "var(--musteri-sesi-amber-900)",
              display: "block",
              marginBottom: 8,
            }}
          >
            Tema Dağılımı:
          </Text>
          <Space size={6} wrap>
            {temaListesi.map((tema, idx) => (
              <Tag key={idx} className="sikayet-tema-tag" style={{ fontSize: 12 }}>
                {tema.tema} ({tema.sayi})
              </Tag>
            ))}
          </Space>
        </div>
      )}

      {/* Son Şikayetler */}
      {veri.ornek_metinler && veri.ornek_metinler.length > 0 && (
        <div>
          <Text
            strong
            style={{
              fontSize: 13,
              color: "var(--musteri-sesi-amber-900)",
              display: "block",
              marginBottom: 8,
            }}
          >
            Son Şikayetler:
          </Text>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {veri.ornek_metinler.slice(0, 3).map((sikayet, idx) => (
              <div
                key={idx}
                style={{
                  padding: 10,
                  background: "var(--musteri-sesi-amber-100)",
                  border: "1px solid var(--musteri-sesi-amber-400)",
                  borderRadius: 8,
                  fontSize: 12,
                  lineHeight: 1.5,
                }}
              >
                <div style={{ color: "var(--musteri-sesi-amber-900)" }}>
                  {sikayet.metin_ozet}
                </div>
                <Space size={4} style={{ marginTop: 6 }}>
                  {sikayet.tema && (
                    <Tag
                      style={{
                        fontSize: 10,
                        background: "var(--musteri-sesi-amber-200)",
                        border: "1px solid var(--musteri-sesi-amber-500)",
                        color: "var(--musteri-sesi-amber-900)",
                      }}
                    >
                      {sikayet.tema}
                    </Tag>
                  )}
                  {sikayet.onem_derecesi && (
                    <Tag
                      color={
                        sikayet.onem_derecesi === "YUKSEK"
                          ? "red"
                          : sikayet.onem_derecesi === "ORTA"
                          ? "gold"
                          : "default"
                      }
                      style={{ fontSize: 10 }}
                    >
                      {sikayet.onem_derecesi}
                    </Tag>
                  )}
                </Space>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Örneklem Notu */}
      <div
        style={{
          marginTop: 12,
          padding: 10,
          background: "var(--musteri-sesi-amber-100)",
          border: "1px dashed var(--musteri-sesi-amber-500)",
          borderRadius: 6,
          fontSize: 11,
          color: "var(--musteri-sesi-amber-900)",
          lineHeight: 1.5,
        }}
      >
        ℹ️ Bu veriler sentetiktir ve "şikayet yoğunluğu" olarak sunulmaktadır (oran değil).
      </div>
    </div>
  );
}

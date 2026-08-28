import { useEffect, useState } from "react";
import { Alert, Skeleton, Space, Statistic, Tag } from "antd";
import { CommentOutlined, WarningOutlined } from "@ant-design/icons";
import { musteriSesiIstatistiklerGetir } from "../api/client";
import { TEMA_ADLARI } from "../utils/temaAdlari";

/**
 * MusteriSesiWidget — Dashboard ana sayfada müşteri sesi (complaint insight)
 * verilerinin özet görünümü.
 *
 * RAPOR GEREKSİNİMİ: Kehribar (amber) görsel dil ile finansal verilerden
 * ayrılmalı, "deneyim sinyali" olarak sunulmalı.
 */
export default function MusteriSesiWidget() {
  const [veri, setVeri] = useState(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(null);

  useEffect(() => {
    setYukleniyor(true);
    setHata(null);
    musteriSesiIstatistiklerGetir()
      .then(setVeri)
      .catch((e) => setHata(e.message))
      .finally(() => setYukleniyor(false));
  }, []);

  if (hata) {
    return (
      <Alert
        type="warning"
        className="musteri-sesi-alert"
        showIcon
        message="Müşteri Sesi verileri alınamadı"
        description={hata}
      />
    );
  }

  if (yukleniyor || !veri) {
    return <Skeleton active paragraph={{ rows: 3 }} />;
  }

  // DUZELTME: backend (api/schemas.py::MusteriSesiIstatistikler) `en_cok_tema`
  // ve dogrudan `cozum_orani` (0-1 float | null) doner - `top_temalar` ve
  // `cozum_dagilimi` alanlari YOKTUR, bu widget onlari varsayip cokuyordu
  // (Dashboard ana sayfasi, HER girisli kullaniciya).
  const topTemalar = (veri.en_cok_tema || []).slice(0, 3);
  // cozum_orani NULL olabilir - "yeterli veri yok" ile "%0 cozuldu" AYNI
  // SEY DEGILDIR (bkz. complaint/toplama.py::yogunluk_ozeti ayni ilke).
  const cozumOraniYuzde =
    veri.cozum_orani != null ? Math.round(veri.cozum_orani * 100) : null;

  return (
    <div className="musteri-sesi-widget">
      {/* Başlık ve Badge */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 16,
        }}
      >
        <CommentOutlined className="musteri-sesi-widget-ikon" />
        <span className="musteri-sesi-widget-baslik">
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
          SENTETİK VERİ
        </Tag>
      </div>

      {/* İstatistikler */}
      <Space size="large" style={{ marginBottom: 16 }} wrap>
        <Statistic
          title="Toplam Şikayet"
          value={veri.toplam_sikayet}
          valueStyle={{ fontSize: 24, fontWeight: 650 }}
        />
        <Statistic
          title="Yüksek Önem"
          value={veri.yuksek_oncelikli || 0}
          valueStyle={{ fontSize: 24, fontWeight: 650, color: "#f57c00" }}
          prefix={<WarningOutlined />}
        />
        <Statistic
          title="Çözüm Oranı"
          value={cozumOraniYuzde != null ? cozumOraniYuzde : "—"}
          suffix={cozumOraniYuzde != null ? "%" : ""}
          valueStyle={{
            fontSize: 24,
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

      {/* Top 3 Tema */}
      {topTemalar.length > 0 && (
        <div>
          <div
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "var(--musteri-sesi-amber-900)",
              marginBottom: 8,
            }}
          >
            En Sık Görülen Temalar:
          </div>
          <Space size={6} wrap>
            {topTemalar.map((tema, idx) => (
              <Tag
                key={idx}
                className="sikayet-tema-tag"
                style={{ fontSize: 12 }}
              >
                {TEMA_ADLARI[tema.tema] || tema.tema} ({tema.adet})
              </Tag>
            ))}
          </Space>
        </div>
      )}

      {/* Örneklem Notu */}
      <div
        style={{
          marginTop: 12,
          padding: 8,
          background: "var(--musteri-sesi-amber-100)",
          border: "1px dashed var(--musteri-sesi-amber-400)",
          borderRadius: 6,
          fontSize: 11,
          color: "var(--musteri-sesi-amber-900)",
          lineHeight: 1.5,
        }}
      >
        ℹ️ <strong>Örneklem notu:</strong> Bu veriler sentetiktir ve tüm
        müşterileri temsil etmez. "Şikayet yoğunluğu" olarak sunulmaktadır
        (oran değil, mutlak sayı).
      </div>
    </div>
  );
}

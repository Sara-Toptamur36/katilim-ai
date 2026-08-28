import { useEffect, useState } from "react";
import { Alert, Descriptions, Modal, Space, Tag } from "antd";
import { CloseOutlined } from "@ant-design/icons";

const ONEM_RENK = { YUKSEK: "red", ORTA: "gold", DUSUK: "default" };
const COZUM_RENK = {
  cozuldu: "green",
  kismen: "gold",
  cozulmedi: "red",
  bilinmiyor: "default",
};
// GORUNUM icin Turkce (aksanli) karsiliklar - bkz. MusteriSesi.jsx'teki
// ayni haritanin gerekcesi. Veri hala aksansiz (YUKSEK, bilinmiyor) tasinir.
const ONEM_ADI = { YUKSEK: "YÜKSEK", ORTA: "ORTA", DUSUK: "DÜŞÜK" };
const COZUM_ADI = {
  cozuldu: "Çözüldü",
  kismen: "Kısmen Çözüldü",
  cozulmedi: "Çözülmedi",
  bilinmiyor: "Bilinmiyor",
};

/**
 * SikayetDetayModal — Tek bir şikayetin detaylı görünümü.
 *
 * Sentetik veri için frontend'den direkt veri alır.
 * Gösterilen bilgiler:
 * - Temiz metin (PII maskeli)
 * - Tema
 * - Önem derecesi + gerekçe
 * - Çözüm durumu
 * - Yineleme/düşük bilgi bayrakları
 * - Eşleşen kampanya bilgisi (varsa)
 */
export default function SikayetDetayModal({ sikayetId, acik, onKapat, temaAdHaritasi = {} }) {
  // sikayetId artık ID değil, tüm şikayet verisi
  const veri = sikayetId;

  return (
    <Modal
      title="Şikayet Detayı"
      open={acik}
      onCancel={onKapat}
      footer={null}
      width={720}
      closeIcon={<CloseOutlined />}
    >
      {veri && (
        <div>
          {/* Şikayet Metni */}
          <div
            style={{
              padding: 16,
              background: "var(--musteri-sesi-amber-50)",
              border: "1px solid var(--musteri-sesi-amber-300)",
              borderRadius: 8,
              marginBottom: 16,
              fontSize: 14,
              lineHeight: 1.6,
              color: "var(--musteri-sesi-amber-900)",
            }}
          >
            {veri.metin}
          </div>

          {/* Detaylar */}
          <Descriptions
            bordered
            column={1}
            size="small"
            labelStyle={{
              background: "var(--zemin-yumusak)",
              fontWeight: 600,
              width: "30%",
            }}
          >
            <Descriptions.Item label="Şikayet ID">
              {veri.id}
            </Descriptions.Item>

            <Descriptions.Item label="Tema">
              {veri.tema ? (
                <Tag className="sikayet-tema-tag">{temaAdHaritasi[veri.tema] || veri.tema}</Tag>
              ) : (
                <span style={{ color: "var(--yazi-soluk)" }}>—</span>
              )}
            </Descriptions.Item>

            <Descriptions.Item label="Önem Derecesi">
              <Tag color={ONEM_RENK[veri.onem_derecesi] || "default"}>
                {ONEM_ADI[veri.onem_derecesi] || veri.onem_derecesi}
              </Tag>
            </Descriptions.Item>

            {veri.onem_gerekcesi && (
              <Descriptions.Item label="Önem Gerekçesi">
                <span style={{ fontSize: 12, fontStyle: "italic" }}>
                  {veri.onem_gerekcesi}
                </span>
              </Descriptions.Item>
            )}

            <Descriptions.Item label="Çözüm Durumu">
              <Tag color={COZUM_RENK[veri.cozum_durumu] || "default"}>
                {COZUM_ADI[veri.cozum_durumu] || veri.cozum_durumu}
              </Tag>
            </Descriptions.Item>

            {/* İşaretler */}
            <Descriptions.Item label="İşaretler">
              <Space size={4}>
                {veri.yineleme_supheli && (
                  <Tag color="purple">Yineleme Şüpheli</Tag>
                )}
                {veri.dusuk_bilgi_supheli && (
                  <Tag color="default">Düşük Bilgi Şüpheli</Tag>
                )}
                {!veri.yineleme_supheli && !veri.dusuk_bilgi_supheli && (
                  <span style={{ color: "var(--yazi-soluk)" }}>
                    İşaret yok
                  </span>
                )}
              </Space>
            </Descriptions.Item>

            {/* Eşleşen Kampanya - sentetik veride yok */}
            {veri.eslesen_kampanya_id && (
              <Descriptions.Item label="Eşleşen Kampanya">
                <Space direction="vertical" size={2}>
                  <div>
                    <strong>Kampanya ID:</strong> {veri.eslesen_kampanya_id}
                  </div>
                  {veri.eslesen_banka && (
                    <div>
                      <strong>Banka:</strong> {veri.eslesen_banka}
                    </div>
                  )}
                  {veri.eslesen_urun_turu && (
                    <div>
                      <strong>Ürün Türü:</strong> {veri.eslesen_urun_turu}
                    </div>
                  )}
                  {veri.eslesme_guveni !== undefined && (
                    <div>
                      <strong>Eşleşme Güveni:</strong>{" "}
                      {(veri.eslesme_guveni * 100).toFixed(1)}%
                    </div>
                  )}
                </Space>
              </Descriptions.Item>
            )}

            {/* Güven skoru - API'den gelen veri için */}
            {veri.guven !== undefined && (
              <Descriptions.Item label="Tema Güven Skoru">
                {(veri.guven * 100).toFixed(1)}%
              </Descriptions.Item>
            )}
          </Descriptions>

        </div>
      )}
    </Modal>
  );
}

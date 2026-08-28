import { Button, Col, DatePicker, Input, Row, Select, Space } from "antd";
import { SearchOutlined, ClearOutlined } from "@ant-design/icons";

const { RangePicker } = DatePicker;

/**
 * MusteriSesiFiltre — Müşteri Sesi sayfası için filtreleme paneli.
 *
 * Filtreler:
 * - Tema (10 tema dropdown)
 * - Önem derecesi (YÜKSEK/ORTA/DÜŞÜK)
 * - Çözüm durumu (çözüldü/kısmen/çözülmedi/bilinmiyor)
 * - Tarih aralığı
 * - Metin arama (temiz_metin'de)
 */
export default function MusteriSesiFiltre({ filtreler, onDegistir, temalar }) {
  const handleTemizle = () => {
    onDegistir({});
  };

  return (
    <div
      style={{
        padding: 16,
        background: "var(--kart)",
        border: "1px solid var(--kenarlik)",
        borderRadius: 12,
        marginBottom: 16,
      }}
    >
      <Row gutter={[12, 12]}>
        {/* Metin Arama */}
        <Col xs={24} sm={12} md={8}>
          <Input
            placeholder="Şikayet metninde ara..."
            prefix={<SearchOutlined style={{ color: "var(--yazi-soluk)" }} />}
            value={filtreler.metin || ""}
            onChange={(e) =>
              onDegistir({ ...filtreler, metin: e.target.value })
            }
            allowClear
          />
        </Col>

        {/* Tema Filtresi */}
        <Col xs={24} sm={12} md={8}>
          <Select
            placeholder="Tema seçin"
            style={{ width: "100%" }}
            value={filtreler.tema || undefined}
            onChange={(value) => onDegistir({ ...filtreler, tema: value })}
            allowClear
            getPopupContainer={(trigger) => trigger.parentElement}
            // DUZELTME (28 Agustos 2026): dropdown kullaniciya tema KODUNU
            // (REWARD_NOT_CREDITED gibi, complaint/tema_siniflandirici.py'nin
            // ic kimligi) gosteriyordu. `temalar` {kod, ad} ciftleri tasir
            // (ad = Turkce karsilik, ör. "Ödül yatmadı") - deger (filtreleme
            // icin) kod'dur, GORUNEN metin `label` alanindaki ad'dir. Eski
            // kayitli (duz string) bicimle de geriye donuk calisir.
            options={(temalar || []).map((tema) => {
              const kod = typeof tema === "string" ? tema : tema.kod;
              const ad = typeof tema === "string" ? tema : tema.ad || tema.kod;
              return { value: kod, label: ad };
            })}
          />
        </Col>

        {/* Önem Derecesi */}
        <Col xs={24} sm={12} md={8}>
          <Select
            placeholder="Önem derecesi"
            style={{ width: "100%" }}
            value={filtreler.onem || undefined}
            onChange={(value) => onDegistir({ ...filtreler, onem: value })}
            allowClear
          >
            <Select.Option value="YUKSEK">YÜKSEK</Select.Option>
            <Select.Option value="ORTA">ORTA</Select.Option>
            <Select.Option value="DUSUK">DÜŞÜK</Select.Option>
          </Select>
        </Col>

        {/* Çözüm Durumu */}
        <Col xs={24} sm={12} md={8}>
          <Select
            placeholder="Çözüm durumu"
            style={{ width: "100%" }}
            value={filtreler.cozum || undefined}
            onChange={(value) => onDegistir({ ...filtreler, cozum: value })}
            allowClear
          >
            <Select.Option value="cozuldu">Çözüldü</Select.Option>
            <Select.Option value="kismen">Kısmen Çözüldü</Select.Option>
            <Select.Option value="cozulmedi">Çözülmedi</Select.Option>
            <Select.Option value="bilinmiyor">Bilinmiyor</Select.Option>
          </Select>
        </Col>

        {/* Tarih Aralığı */}
        <Col xs={24} sm={12} md={8}>
          <RangePicker
            style={{ width: "100%" }}
            placeholder={["Başlangıç", "Bitiş"]}
            value={filtreler.tarih || null}
            onChange={(dates) =>
              onDegistir({ ...filtreler, tarih: dates })
            }
            format="YYYY-MM-DD"
          />
        </Col>

        {/* Temizle Butonu */}
        <Col xs={24} sm={12} md={8}>
          <Button
            icon={<ClearOutlined />}
            onClick={handleTemizle}
            style={{ width: "100%" }}
          >
            Filtreleri Temizle
          </Button>
        </Col>
      </Row>
    </div>
  );
}

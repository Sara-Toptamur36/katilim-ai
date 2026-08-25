import { useState } from "react";
import { Select, Button, Space, Table, Alert, Tag, Typography } from "antd";
import { karsilastir } from "../api/client";
import { useAudit } from "../context/AuditContext";

// api/comparison/compare_engine.py'daki KRITERLER sozlugu ile BIREBIR ayni
// olmali - sunucu, bu listenin disindaki bir kriteri 422 ile reddeder.
const KRITERLER = [
  { value: "en_dusuk_kar_payi", label: "En düşük kâr payı oranı" },
  { value: "en_yuksek_odul", label: "En yüksek ödül miktarı" },
  { value: "en_uzun_vade", label: "En uzun vade seçeneği" },
  { value: "en_dusuk_masraf", label: "En düşük masraf/tahsis ücreti" },
  // Şartname Md. 5.7'nin KENDİ örnek senaryosu: "kâr payı açısından C
  // Bankası, vade açısından A Bankası daha avantajlıdır". Backend bunu
  // eksen eksen kazanan mantığıyla üretiyordu ama arayüzde çağrılacak
  // bir yer YOKTU - şartnamenin amiral kriteri erişilemez duruyordu.
  { value: "en_avantajli", label: "En avantajlı (çok eksenli)" },
  { value: "en_yuksek_tutar", label: "En yüksek finansman tutarı" },
  // Nakit iade / indirim: çıkarım motoru bu değerleri üretiyor ve 60
  // kayıtta dolu, ama kriter olmadığı için o kampanyalar ASIL avantajları
  // üzerinden hiç sıralanamıyordu (bkz. comparison/compare_engine.py).
  { value: "en_yuksek_nakit_iade", label: "En yüksek nakit iade oranı" },
  { value: "en_yuksek_indirim", label: "En yüksek indirim oranı" },
];

const KRITER_ETIKETLERI = {
  en_dusuk_kar_payi: "En düşük kâr payı oranı",
  en_yuksek_odul: "En yüksek ödül miktarı",
  en_uzun_vade: "En uzun vade seçeneği",
  en_dusuk_masraf: "En düşük masraf/tahsis ücreti",
  en_avantajli: "En avantajlı (çok eksenli)",
  en_yuksek_tutar: "En yüksek finansman tutarı",
  en_yuksek_nakit_iade: "En yüksek nakit iade oranı",
  en_yuksek_indirim: "En yüksek indirim oranı",
};

const sonucKolonlari = [
  { title: "#", dataIndex: "sira", key: "sira", width: 50 },
  { title: "Banka", dataIndex: "banka", key: "banka" },
  { title: "Kampanya", dataIndex: "kampanya_adi", key: "kampanya_adi" },
  {
    title: "Kriter Değeri",
    dataIndex: "kriter_degeri",
    key: "kriter_degeri",
    render: (deger) => (deger != null ? deger : "Belirtilmemiş"),
  },
  {
    title: "Eksik Alanlar",
    dataIndex: "eksik_alanlar",
    key: "eksik_alanlar",
    render: (alanlar) =>
      alanlar && alanlar.length > 0 ? (
        alanlar.map((a) => (
          <Tag key={a} color="orange">
            {a}
          </Tag>
        ))
      ) : (
        <Tag color="green">Eksik yok</Tag>
      ),
  },
];

// Kriter state'i ana bileşene (Karsilastirma.jsx) taşındı. Böylece kampanya seçicisi
// seçili kritere göre dolu verisi olan kampanyaları üst sıraya alabilir.
export default function KarsilastirmaPaneli({
  secilenIdler,
  kriter = "en_dusuk_kar_payi",
  onKriterDegis,
  veriOlanSayisi = 0,
}) {
  const { auditEkle } = useAudit();
  const [sonuc, setSonuc] = useState(null);
  const [yukleniyor, setYukleniyor] = useState(false);
  const [hata, setHata] = useState(null);

  const karsilastirmayiCalistir = async () => {
    setYukleniyor(true);
    setHata(null);
    try {
      const veri = await karsilastir(secilenIdler, kriter);
      setSonuc(veri);

      // POST /karsilastir yanıtında gelen audit verisi Jüri Audit Paneline iletilir
      if (veri?.audit) {
        const kriterAdi = KRITER_ETIKETLERI[kriter] || kriter;
        auditEkle(veri.audit, `Karşılaştırma: ${kriterAdi}`);
      }
    } catch (e) {
      setHata(e.response?.data?.detail || e.message);
      setSonuc(null);
    } finally {
      setYukleniyor(false);
    }
  };


  return (
    <div style={{ marginBottom: 12 }}>
      <Space wrap style={{ marginBottom: 12 }} align="center">
        <Select
          style={{ width: 260 }}
          value={kriter}
          onChange={onKriterDegis}
          options={KRITERLER}
        />
        <Typography.Text type="secondary" style={{ fontSize: 13 }}>
          Bu kriterde veri olan {veriOlanSayisi} kampanya var
        </Typography.Text>
        <Button
          type="primary"
          onClick={karsilastirmayiCalistir}
          disabled={secilenIdler.length < 2}
          loading={yukleniyor}
        >
          Karşılaştır ({secilenIdler.length} seçili)
        </Button>
      </Space>

      {secilenIdler.length < 2 && (
        <p style={{ color: "var(--yazi-soluk)", marginBottom: 12 }}>
          Karşılaştırmak için yukarıdaki listeden en az 2 kampanya seçin.
        </p>
      )}

      {hata && (
        <Alert
          type="error"
          message="Karşılaştırma başarısız"
          description={hata}
          showIcon
          style={{ marginBottom: 12 }}
        />
      )}

      {sonuc && (
        <>
          {sonuc.audit?.sebep && (
            <Alert
              type="info"
              message={sonuc.audit.sebep}
              style={{ marginBottom: 12 }}
              showIcon
            />
          )}
          <Table
            columns={sonucKolonlari}
            dataSource={sonuc.sonuclar}
            rowKey="id"
            pagination={false}
            size="small"
            scroll={{ x: "max-content" }}
          />

          {/* EKSEN KIRILIMI - yalnızca kompozit kriterde döner.
              Şartname Md. 5.7 tek bir "kazanan" istemiyor; hangi EKSENDE
              kimin öne çıktığını istiyor. Backend bunu üretiyordu, burada
              gösterilmiyordu. `durum` alanı da aynen aktarılır: ödül
              birimleri karışıksa ("Bankkart Lira" ile "TL") o eksen
              KAZANANSIZ kalır - uydurma bir sıralama yapılmaz. */}
          {sonuc.eksen_kirilimi?.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <Typography.Text strong>Eksen bazında öne çıkanlar</Typography.Text>
              <Typography.Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 8 }}>
                Tek bir kazanan yerine her ölçütte kimin önde olduğu ayrı gösterilir.
              </Typography.Paragraph>
              <Space direction="vertical" size={6} style={{ width: "100%" }}>
                {sonuc.eksen_kirilimi.map((e) => {
                  const kazananlar = e.kazananlar ?? [];
                  const olculemez = kazananlar.length === 0;
                  return (
                    <div
                      key={e.kriter}
                      style={{
                        padding: "6px 10px",
                        borderLeft: `3px solid ${olculemez ? "#b89a5c" : "#169276"}`,
                        background: "var(--kart-ustu)",
                        borderRadius: "0 4px 4px 0",
                        fontSize: 13,
                      }}
                    >
                      <strong>{e.aciklama ?? e.kriter}</strong>
                      {olculemez ? (
                        <span style={{ marginLeft: 8 }}>
                          <Tag color="default">Ölçülemedi</Tag>
                          {e.durum === "birim_karisik" && e.birimler?.length > 0 && (
                            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                              Ödül birimleri karışık ({e.birimler.join(", ")}) — farklı
                              birimler karşılaştırılmaz.
                            </Typography.Text>
                          )}
                        </span>
                      ) : (
                        <span style={{ marginLeft: 8 }}>
                          {e.deger != null && <Tag color="green">{String(e.deger)}</Tag>}
                          {kazananlar.map((k, i) => (
                            <Tag key={i} color="blue">
                              {k.banka} — {k.kampanya_adi}
                            </Tag>
                          ))}
                        </span>
                      )}
                    </div>
                  );
                })}
              </Space>
            </div>
          )}
        </>
      )}
    </div>
  );
}


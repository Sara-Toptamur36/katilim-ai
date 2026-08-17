import { useEffect, useState } from "react";
import { Alert, Skeleton, Space, Tag, Tooltip, Typography } from "antd";
import { tazelikGetir } from "../api/client";

// Mentor raporu II, P0 #1: "freshness metrigini dashboard'da gorunur yapin."
//
// TASARIM: "Bilinmiyor" ile "eski" AYNI SEY DEGILDIR ve ayni gri hucreye
// indirgenmez. Indeks durum dosyasi yoksa API None doner ve burada
// "bilinmiyor" yazar - "guncel" gibi gostermek yaniltici olurdu.

const BAYAT_ESIGI_GUN = 3;

function tarihMetni(isoMetin) {
  if (!isoMetin) return null;
  const t = new Date(isoMetin);
  return t.toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" });
}

function TazelikEtiketi({ baslik, tarih, gunOnce, ipucu }) {
  if (!tarih) {
    return (
      <Tooltip title="Bu bilgi kayıtlı değil — tahmin üretilmiyor">
        <span>
          <Typography.Text type="secondary">{baslik}: </Typography.Text>
          <Tag>bilinmiyor</Tag>
        </span>
      </Tooltip>
    );
  }

  const bayat = gunOnce != null && gunOnce > BAYAT_ESIGI_GUN;
  return (
    <Tooltip title={ipucu}>
      <span>
        <Typography.Text type="secondary">{baslik}: </Typography.Text>
        <Tag color={bayat ? "orange" : "green"}>
          {tarihMetni(tarih)}
          {gunOnce != null && gunOnce > 0 && ` · ${gunOnce} gün önce`}
        </Tag>
      </span>
    </Tooltip>
  );
}

export default function TazelikSeridi() {
  const [veri, setVeri] = useState(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(null);

  useEffect(() => {
    tazelikGetir()
      .then(setVeri)
      .catch((e) => setHata(e.message))
      .finally(() => setYukleniyor(false));
  }, []);

  if (yukleniyor) return <Skeleton active paragraph={{ rows: 1 }} />;
  if (hata) {
    return (
      <Alert
        type="warning"
        title="Veri güncelliği okunamadı"
        description={hata}
        showIcon
        style={{ marginBottom: 16 }}
      />
    );
  }
  if (!veri) return null;

  return (
    <div style={{ marginBottom: 16 }}>
      <Space wrap size={16}>
        <TazelikEtiketi
          baslik="Son tarama"
          tarih={veri.son_tarama}
          gunOnce={veri.tarama_gun_once}
          ipucu="Bankaların sayfalarından en son ne zaman veri toplandı"
        />
        <TazelikEtiketi
          baslik="RAG indeksi"
          tarih={veri.rag_indeks_kuruldu}
          gunOnce={veri.rag_indeks_gun_once}
          ipucu={
            veri.rag_parca_sayisi
              ? `${veri.rag_belge_sayisi} belge → ${veri.rag_parca_sayisi} parça`
              : "İndeksin en son ne zaman kurulduğu"
          }
        />
        {veri.tekil_kampanya != null && (
          <Tooltip title="Scraper eski taramaları silmez (değişiklik takibi için); anlık görüntü sayısı tekil kampanyadan fazladır">
            <span>
              <Typography.Text type="secondary">Kampanya: </Typography.Text>
              <Tag>
                {veri.tekil_kampanya} tekil · {veri.anlik_goruntu} anlık görüntü
              </Tag>
            </span>
          </Tooltip>
        )}
      </Space>

      {/* En kritik durum: indeks kurulduktan SONRA veri toplanmis. RAG
          cevaplari en yeni kampanyalari icermiyor olabilir - bunu
          kullanicidan saklamak, guncel olmayan cevabi guncel gibi
          gostermek olurdu. */}
      {veri.indeks_ham_veriden_eski_mi === true && (
        <Alert
          type="warning"
          title="RAG indeksi ham veriden eski"
          description="İndeks kurulduktan sonra yeni kampanya verisi toplandı. Sohbet yanıtları en güncel kampanyaları içermeyebilir. Tazelemek için: python -m chunking.indeksleyici"
          showIcon
          style={{ marginTop: 8 }}
        />
      )}
    </div>
  );
}

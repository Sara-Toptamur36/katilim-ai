import { useEffect, useState } from "react";
import { Alert, Skeleton, Space, Tag, Tooltip, Typography } from "antd";
import { tazelikGetir } from "../api/client";

// Mentor raporu II, P0 #1: "freshness metrigini dashboard'da gorunur yapin."
//
// TASARIM: "Bilinmiyor" ile "eski" AYNI SEY DEGILDIR ve ayni gri hucreye
// indirgenmez. Indeks durum dosyasi yoksa API None doner ve burada
// "bilinmiyor" yazar - "guncel" gibi gostermek yaniltici olurdu.
//
// YENİ: demo_mode, dataset_version, rag_index_version, model_version,
// rule_version, git_commit alanları da gösteriliyor (TazelikYanit).

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

function VersiyonEtiketi({ baslik, deger, ipucu, renk = "default" }) {
  if (!deger) {
    return (
      <Tooltip title={`${baslik} bilgisi bilinmiyor — tahmin üretilmiyor`}>
        <span>
          <Typography.Text type="secondary">{baslik}: </Typography.Text>
          <Tag>—</Tag>
        </span>
      </Tooltip>
    );
  }
  return (
    <Tooltip title={ipucu}>
      <span>
        <Typography.Text type="secondary">{baslik}: </Typography.Text>
        <Tag color={renk} style={{ fontFamily: "monospace", fontSize: 11 }}>
          {deger}
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
      {/* Yerel veri modu banneri — backend DEMO_MODE=true veya mock veri akarken */}
      {veri.demo_mode && (
        <Alert
          type="warning"
          showIcon
          message={
            <span>
              🟡 <strong>YEREL VERİ MODU</strong> — Yerel doğrulanmış veri (PostgreSQL/Qdrant/Ollama).
              Gerçek canlı veri değil.
            </span>
          }
          style={{ marginBottom: 10 }}
        />
      )}

      {/* Tazelik satırı */}
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
          <Tooltip title="Bankaların sayfalarından taranan ham veri (scraper/raw_data) - veritabanına yüklenmiş kayıt sayısından farklıdır, bkz. Alan Bazında Veri Doluluğu kartı. Scraper eski taramaları silmez (değişiklik takibi için); anlık görüntü sayısı tekil kampanyadan fazladır">
            <span>
              {/* Etiket BILEREK "ham korpus" diyor: hemen asagidaki Alan
                  Bazinda Veri Dolulugu karti VERITABANI sayisini (536 kayit)
                  gosteriyor, burasi ise scraper/raw_data altindaki dosyalari
                  sayiyor. Onceki surumde ikisi de yalnizca "kampanya" diyordu
                  ve ayni ekranda iki farkli sayi celiski gibi gorunuyordu -
                  fark yalnizca tooltip'te yaziyordu, hover etmeyen goremiyordu. */}
              <Typography.Text type="secondary">Ham korpus: </Typography.Text>
              <Tag>
                {veri.tekil_kampanya} tekil · {veri.anlik_goruntu} anlık görüntü
              </Tag>
            </span>
          </Tooltip>
        )}
      </Space>

      {/* Versiyon satırı */}
      <Space wrap size={12} style={{ marginTop: 10 }}>
        <VersiyonEtiketi
          baslik="Model"
          deger={veri.model_version}
          ipucu="Kullanılan LLM model adı"
          renk="blue"
        />
        <VersiyonEtiketi
          baslik="Dataset"
          deger={veri.dataset_version}
          ipucu="Veri seti versiyonu. DATASET_VERSION ortam değişkeninden okunur."
        />
        <VersiyonEtiketi
          baslik="RAG indeks"
          deger={veri.rag_index_version}
          ipucu="RAG vektör indeks versiyonu. RAG_INDEX_VERSION ortam değişkeninden okunur."
        />
        <VersiyonEtiketi
          baslik="Kural"
          deger={veri.rule_version}
          ipucu="Guardrail/kapsam kural versiyonu. RULE_VERSION ortam değişkeninden okunur."
        />
        {veri.git_commit && (
          <Tooltip title={`Son git commit: ${veri.git_commit}`}>
            <span>
              <Typography.Text type="secondary">Commit: </Typography.Text>
              <Tag style={{ fontFamily: "monospace", fontSize: 10 }}>
                {veri.git_commit.slice(0, 7)}
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

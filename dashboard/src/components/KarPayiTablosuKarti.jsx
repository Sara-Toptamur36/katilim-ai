import { Card, Table, Typography } from "antd";

// Bankalar "Kâr Payı Oranları"nı çoğu zaman VADE/TUTAR dilimine göre
// değişen bir tablo halinde yayınlıyor (Rehber Bölüm 18) - kar_payi_orani_
// percent TEK bir sayıdır ve bu tabloyu doğru şekilde tek sayıya indirmek
// çoğu zaman UYDURMA bir seçim olurdu (bkz. extraction/tablo_extractor.py
// docstring'i - aynı vadede farklı tutar diliminde farklı oran, ya da aynı
// sayfada "sigortalı"/"sigortasız" için iki farklı oran seti gibi gerçek
// örnekler ölçüldü). Bu kart, kaynakta bulunan tabloyu OLDUĞU GİBİ gösterir;
// hiçbir satır/sütun uydurulmaz veya seçilmez.
//
// Yalnizca kar_payi_tablosu DOLU olan kampanyalarda render edilir (Dashboard.jsx) -
// alan çoğu kampanya türünde (kart/ödül vb.) zaten kavramsal olarak
// uygulanamaz, her kampanyada boş bir kart göstermek gürültü olurdu.

export default function KarPayiTablosuKarti({ tablolar }) {
  if (!tablolar || tablolar.length === 0) return null;

  return (
    <Card size="small" title="Kâr Payı Oranları Tablosu (kaynak sayfadan)">
      <Typography.Paragraph type="secondary" style={{ marginBottom: 12 }}>
        Kaynak sayfada vadeye/tutara göre değişen birden fazla oran olabilir;
        tek bir "kâr payı oranı" olarak özetlenmez, tablo olduğu gibi gösterilir.
      </Typography.Paragraph>
      {tablolar.map((tablo, i) => {
        const kolonlar = tablo.sutunlar.map((s) => ({
          title: s,
          dataIndex: s,
          key: s,
        }));
        return (
          <Table
            key={tablo.tablo_index ?? i}
            columns={kolonlar}
            dataSource={tablo.satirlar.map((satir, j) => ({ key: j, ...satir }))}
            pagination={false}
            size="small"
            style={{ marginBottom: i < tablolar.length - 1 ? 16 : 0 }}
          />
        );
      })}
    </Card>
  );
}

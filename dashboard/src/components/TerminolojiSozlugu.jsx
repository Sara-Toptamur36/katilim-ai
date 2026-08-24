import { useEffect, useMemo, useState } from "react";
import { Alert, Collapse, Empty, Input, Skeleton, Space, Tag, Typography } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import { terminolojiGetir } from "../api/client";

// Sozluk artik API'den gelir (GET /terminoloji). Onceki surumde bu bilesen
// terminolojiMock.js'teki AYRI bir kopyayi okuyordu; o kopya gercek
// terminology/sozluk.json'dan sapmisti (8 kavram / 31 kavram). Mock silindi.

// Backend'deki agent/intent.py::turkce_ascii_katla ile AYNI mantik, iki
// bilincli farkla:
//
// 1) toLocaleLowerCase("tr") KULLANILMAZ: o, duz ASCII "I" harfini
//    noktasiz "ı"ya cevirir; kullanici "FINANSMAN" yazdiginda "fınansman"
//    olusur ve veri tarafindaki "finansman" ile eslesmez. Yalnizca Turkce
//    noktali "İ" duzeltilir, ASCII "I"ya dokunulmaz (o harf hem "I" hem
//    "ı" olabilir - yanlis donusum yeni uyusmazlik yaratir).
//
// 2) Sapkali harfler (â î û) de katlanir - backend'in haritasinda bunlar
//    YOK. Gerekce olculdu: sozlukte "Murâbaha", "İcâre", "Müşâreke",
//    "İstisnâ" gibi sapkali standart terimler var ama kullanici bunlari
//    dogal olarak sapkasiz yazar. Katlama olmadan "murabaha" aramasi
//    SIFIR sonuc donuyordu (canli panelde dogrulandi).
const TR_KATLAMA = { ş: "s", ı: "i", ğ: "g", ü: "u", ö: "o", ç: "c", â: "a", î: "i", û: "u" };

const turkceKatla = (metin) =>
  metin
    .replace(/İ/g, "i")
    .toLowerCase()
    .replace(/[şığüöçâîû]/g, (h) => TR_KATLAMA[h]);

// Eşleşen metin parçasını <mark> etiketi ile vurgulama fonksiyonu
const vurgula = (metin, aramaMetni) => {
  if (!metin) return "";
  const q = turkceKatla((aramaMetni || "").trim());
  if (!q) return metin;

  const katlanmis = turkceKatla(metin);
  const sonuclar = [];
  let kalisIndeks = 0;
  let bulmaIndeksi = katlanmis.indexOf(q, kalisIndeks);

  while (bulmaIndeksi !== -1) {
    if (bulmaIndeksi > kalisIndeks) {
      sonuclar.push(metin.slice(kalisIndeks, bulmaIndeksi));
    }
    const eslesenParca = metin.slice(bulmaIndeksi, bulmaIndeksi + q.length);
    sonuclar.push(
      <mark key={bulmaIndeksi} className="arama-vurgu">
        {eslesenParca}
      </mark>
    );
    kalisIndeks = bulmaIndeksi + q.length;
    bulmaIndeksi = katlanmis.indexOf(q, kalisIndeks);
  }

  if (kalisIndeks < metin.length) {
    sonuclar.push(metin.slice(kalisIndeks));
  }

  return sonuclar.length > 0 ? sonuclar : metin;
};

export default function TerminolojiSozlugu() {
  const [terimler, setTerimler] = useState([]);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(null);
  const [arama, setArama] = useState("");

  useEffect(() => {
    terminolojiGetir()
      .then(setTerimler)
      .catch((e) => setHata(e.message))
      .finally(() => setYukleniyor(false));
  }, []);

  const suzulmus = useMemo(() => {
    const q = turkceKatla(arama.trim());
    if (!q) return terimler;
    return terimler.filter((t) =>
      [t.standart_terim, t.gelenek_karsilik, t.aciklama].some((alan) =>
        turkceKatla(alan || "").includes(q)
      )
    );
  }, [terimler, arama]);

  if (yukleniyor) return <Skeleton active paragraph={{ rows: 4 }} />;

  if (hata) {
    return (
      <Alert
        type="error"
        message="Terminoloji sözlüğü alınamadı"
        description={hata}
        showIcon
      />
    );
  }

  const aramaTerm = turkceKatla(arama.trim());

  return (
    <>
      <Input
        prefix={<SearchOutlined style={{ color: "var(--yazi-soluk)" }} />}
        value={arama}
        onChange={(e) => setArama(e.target.value)}
        placeholder="Kavram ara: kâr payı, murabaha, mevduat..."
        allowClear
        style={{ maxWidth: 420, marginBottom: 12 }}
      />

      <Typography.Paragraph type="secondary" style={{ marginBottom: 12 }}>
        {suzulmus.length} / {terimler.length} kavram. Her kavramın geleneksel
        bankacılık karşılığı ve tanım kaynağı birlikte gösterilir (Şartname Md. 5.5).
      </Typography.Paragraph>

      {suzulmus.length === 0 ? (
        <Empty description="Bu aramaya uyan kavram yok" />
      ) : (
        <Collapse
          items={suzulmus.map((t) => {
            // Eşleşmenin nerede olduğunu tespit et (terimde / geleneksel karşılığında / açıklamada)
            const eslesmeYerleri = [];
            if (aramaTerm) {
              if (turkceKatla(t.standart_terim || "").includes(aramaTerm)) {
                eslesmeYerleri.push({ key: "terim", label: "terimde", color: "blue" });
              }
              if (turkceKatla(t.gelenek_karsilik || "").includes(aramaTerm)) {
                eslesmeYerleri.push({ key: "gelenek", label: "geleneksel karşılığında", color: "purple" });
              }
              if (turkceKatla(t.aciklama || "").includes(aramaTerm)) {
                eslesmeYerleri.push({ key: "aciklama", label: "açıklamada", color: "orange" });
              }
            }

            return {
              key: t.anahtar,
              label: (
                <Space size="small" wrap align="center">
                  <span>{vurgula(t.standart_terim, arama)}</span>
                  <Tag style={{ margin: 0 }}>{vurgula(t.gelenek_karsilik, arama)}</Tag>
                  {eslesmeYerleri.map((ey) => (
                    <Tag key={ey.key} color={ey.color} style={{ fontSize: 11, margin: 0 }}>
                      {ey.label}
                    </Tag>
                  ))}
                </Space>
              ),
              children: (
                <>
                  <p>
                    <strong>Geleneksel bankacılıktaki karşılığı:</strong>{" "}
                    {vurgula(t.gelenek_karsilik, arama)}
                  </p>
                  <p>
                    <strong>Açıklama:</strong> {vurgula(t.aciklama, arama)}
                  </p>
                  <p>
                    <strong>Tanım kaynağı:</strong> {t.kaynak}
                  </p>
                  {t.ornek_kaynak && (
                    <p>
                      <strong>Gerçek veride görüldüğü yer:</strong> {t.ornek_kaynak}
                    </p>
                  )}
                  {t.sema_alani && t.sema_alani.length > 0 && (
                    <p>
                      <strong>Karşılık geldiği veri alanı:</strong>{" "}
                      {t.sema_alani.map((alan) => (
                        <Tag key={alan}>{alan}</Tag>
                      ))}
                    </p>
                  )}
                </>
              ),
            };
          })}
        />
      )}
    </>
  );
}


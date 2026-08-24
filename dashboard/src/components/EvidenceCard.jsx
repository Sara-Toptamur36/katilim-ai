import { Card, Tag, Tooltip, Typography } from "antd";
import {
  LinkOutlined,
  CalendarOutlined,
  DatabaseOutlined,
  CheckCircleOutlined,
  WarningOutlined,
} from "@ant-design/icons";

/**
 * EvidenceCard — Tek bir kaynağı "nereden, nasıl, ne kadar güvenle?" gösterir.
 *
 * evidence_type:
 *   SOURCE    → Resmi kaynakta bu şekilde yazıyor        🟢
 *   EXTRACTED → NLP modeli metinden çıkardı              🔵
 *   CALCULATED→ Deterministik Python ile hesaplandı      🟠
 *   CLASSIFIED→ Anahtar kelimeyle sınıflandırıldı        🟣
 *   INFERRED  → Bağlamdan çıkarıldı                      🔶
 *
 * demo_snapshot: True ise "DEMO SNAPSHOT" rozeti gösterilir.
 *
 * Güvenli URL: Sadece izinli resmi domainlere <a href> oluşturulur.
 * Güvensiz/harici URL'lerde link oluşturulmaz, uyarı ikonu gösterilir.
 */

const GUVENLI_DOMAIN = [
  "kuveytturk.com.tr",
  "albarakaturk.com.tr",
  "turkiyefinans.com.tr",
  "ziraatkatilim.com.tr",
  "vakifkatilim.com.tr",
  "emlakkatilim.com.tr",
  "hayatfinans.com.tr",
  "katilimemeklilik.com.tr",
  "bereket.com.tr",
];

function guvenliUrlMi(url) {
  if (!url) return false;
  try {
    const p = new URL(url);
    if (p.protocol !== "https:") return false;
    return GUVENLI_DOMAIN.some((d) => p.hostname === d || p.hostname.endsWith("." + d));
  } catch {
    return false;
  }
}

const EVIDENCE_TYPE_META = {
  SOURCE:     { renk: "green",   ikon: "🟢", etiket: "Kaynak metinden",         tip: "Bu değer resmi kaynakta bu şekilde yazıyor." },
  EXTRACTED:  { renk: "blue",    ikon: "🔵", etiket: "Model tarafından çıkarıldı", tip: "NLP modeli (Regex/GLiNER/Qwen) bu değeri metinden çıkardı." },
  CALCULATED: { renk: "orange",  ikon: "🟠", etiket: "Hesaplandı",              tip: "Bu değer deterministik Python ile hesaplandı (LLM değil)." },
  CLASSIFIED: { renk: "purple",  ikon: "🟣", etiket: "Sınıflandırıldı",        tip: "Model bu değeri anahtar kelime sınıflandırmasıyla belirledi." },
  INFERRED:   { renk: "volcano", ikon: "🔶", etiket: "Çıkarıldı (inferred)",    tip: "Bu değer doğrudan kaynakta yazmıyor, bağlamdan çıkarıldı." },
};

function GuncellikTag({ guncellik, kampanyaBitis }) {
  if (guncellik === "suresi_dolmus")
    return (
      <Tag color="red">
        <WarningOutlined /> Süresi dolmuş{kampanyaBitis ? ` — ${kampanyaBitis}` : ""}
      </Tag>
    );
  if (guncellik === "aktif")
    return (
      <Tag color="green">
        <CheckCircleOutlined /> Güncel{kampanyaBitis ? ` — ${kampanyaBitis} tarihine kadar` : ""}
      </Tag>
    );
  return <Tag color="default">Tarih bilinmiyor</Tag>;
}

export default function EvidenceCard({ kaynak, boyut = "normal" }) {
  if (!kaynak) return null;

  const kucuk = boyut === "kucuk";
  const tip = EVIDENCE_TYPE_META[kaynak.evidence_type] ?? null;
  const urlGecerli = guvenliUrlMi(kaynak.kaynak_url);

  // Kısa chunk_id gösterimi
  const chunkKisa = kaynak.chunk_id
    ? kaynak.chunk_id.length > 20
      ? kaynak.chunk_id.slice(0, 16) + "…"
      : kaynak.chunk_id
    : null;

  return (
    <Card
      size="small"
      style={{
        border: "1px solid var(--kenarlik)",
        borderLeft: `3px solid ${tip ? `var(--${tip.renk}, #1677ff)` : "#1677ff"}`,
        marginBottom: kucuk ? 8 : 12,
        position: "relative",
        borderRadius: 6,
      }}
    >
      {/* DEMO SNAPSHOT rozeti */}
      {kaynak.demo_snapshot && (
        <div
          style={{
            position: "absolute",
            top: 4,
            right: 4,
            background: "#7c5c00",
            color: "#fff8e0",
            fontSize: 10,
            fontWeight: 700,
            padding: "2px 6px",
            borderRadius: 4,
            letterSpacing: "0.05em",
            zIndex: 1,
          }}
        >
          DEMO SNAPSHOT
        </div>
      )}

      {/* Üst: kaynak adı + evidence_type + güven */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 8,
        }}
      >
        <div style={{ flex: 1, marginRight: 12 }}>
          {/* Kaynak başlığı */}
          <div style={{ fontWeight: 600, fontSize: kucuk ? 12 : 13, marginBottom: 4 }}>
            {urlGecerli ? (
              <Typography.Link
                href={kaynak.kaynak_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                <LinkOutlined style={{ marginRight: 4 }} />
                {kaynak.banka
                  ? `${kaynak.banka}${kaynak.kampanya_adi ? " — " + kaynak.kampanya_adi : ""}`
                  : kaynak.kaynak_url}
              </Typography.Link>
            ) : (
              <span>
                {kaynak.banka
                  ? `${kaynak.banka}${kaynak.kampanya_adi ? " — " + kaynak.kampanya_adi : ""}`
                  : (kaynak.kaynak_url ?? "Kaynak")}
                {kaynak.kaynak_url && !urlGecerli && (
                  <Tooltip title="Harici link doğrulanamadı — yalnızca resmi katılım bankası domainlerine bağlantı açılır.">
                    <WarningOutlined style={{ marginLeft: 6, color: "#c28e28", fontSize: 11 }} />
                  </Tooltip>
                )}
              </span>
            )}
          </div>

          {/* Tag satırı: güncellik + evidence_type */}
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
            <GuncellikTag
              guncellik={kaynak.guncellik}
              kampanyaBitis={kaynak.kampanya_bitis}
            />
            {tip && (
              <Tooltip title={tip.tip}>
                <Tag color={tip.renk} style={{ cursor: "help" }}>
                  {tip.ikon} {tip.etiket}
                </Tag>
              </Tooltip>
            )}
          </div>
        </div>

        {/* Güven skoru */}
        {kaynak.similarity_score != null && (
          <Tooltip title="Retrieval benzerlik skoru — doğruluk oranı değil, vektör arama benzerliğidir.">
            <div style={{ textAlign: "right", cursor: "help" }}>
              <div style={{ fontSize: 10, color: "#8c8c8c" }}>Benzerlik</div>
              <div
                style={{
                  fontSize: 15,
                  fontWeight: 700,
                  color:
                    kaynak.similarity_score >= 0.8
                      ? "#169276"
                      : kaynak.similarity_score >= 0.6
                      ? "#c28e28"
                      : "#c94f4f",
                }}
              >
                {(kaynak.similarity_score * 100).toFixed(0)}%
              </div>
            </div>
          </Tooltip>
        )}

        {/* ÇIKARIM GÜVENİ — arama skorlarından AYRI bir bileşendir.
            Benzerlik/sıralama skorları "bu parça soruya ne kadar uyuyor"
            der; bu ise "bu kampanyanın alanları metinden ne kadar güvenle
            ÇIKARILDI" der. İkisini tek sayıya indirmek, Jüri Audit
            Paneli'nin bileşen bazlı skor ayrımını yok ederdi.
            Kayıt eşleşmediyse None gelir ve hiç gösterilmez - uydurulmaz. */}
        {kaynak.entity_confidence != null && (
          <Tooltip title="Çıkarım güveni — bu kampanyanın alanlarının kaynak metinden ne kadar güvenle çıkarıldığı. Arama benzerliğinden farklıdır.">
            <div style={{ textAlign: "right", cursor: "help" }}>
              <div style={{ fontSize: 10, color: "#8c8c8c" }}>Çıkarım</div>
              <div
                style={{
                  fontSize: 15,
                  fontWeight: 700,
                  color:
                    kaynak.entity_confidence >= 0.8
                      ? "#169276"
                      : kaynak.entity_confidence >= 0.6
                      ? "#c28e28"
                      : "#c94f4f",
                }}
              >
                {(kaynak.entity_confidence * 100).toFixed(0)}%
              </div>
            </div>
          </Tooltip>
        )}
      </div>

      {/* Meta bilgiler */}
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
        {kaynak.belge_tarihi && (
          <Tag icon={<CalendarOutlined />} color="default">
            {kaynak.belge_tarihi}
          </Tag>
        )}
        {chunkKisa && (
          <Tooltip title={`Chunk ID: ${kaynak.chunk_id}`}>
            <Tag
              icon={<DatabaseOutlined />}
              style={{ fontFamily: "monospace", fontSize: 10, cursor: "help" }}
            >
              {chunkKisa}
            </Tag>
          </Tooltip>
        )}
      </div>

      {/* Evidence span */}
      {kaynak.metin && (
        <blockquote
          style={{
            margin: 0,
            padding: "8px 12px",
            borderLeft: "3px solid #1677ff",
            background: "var(--kart-ustu)",
            borderRadius: "0 6px 6px 0",
            fontSize: 12,
            lineHeight: 1.6,
          }}
        >
          <Typography.Text type="secondary" italic>
            "{kaynak.metin}"
          </Typography.Text>
        </blockquote>
      )}
    </Card>
  );
}

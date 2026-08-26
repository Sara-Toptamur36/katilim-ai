import { useState } from "react";
import { Modal } from "antd";
import {
  OLCUMLER,
  OLCUM_TARIHI,
  VERI_TARIHI,
  OLCUM_VERI_SETI,
  ZAMAN_EKSENI,
} from "../data/olcumler";
import { useCanliVeriOzet } from "../hooks/useCanliVeriOzet";

// Model Metrikleri ve Veri Kaynakları panelleri ONCEDEN Genel Bakış'taydı.
// DENETIM BULGUSU (26.08.2026): ilk giren biri (jüri) Genel Bakış'ta daha
// ürünü anlamadan Makro F1/Recall gibi ML terimleriyle karşılaşıyordu, ve
// bu statik/tek seferlik ölçüm raporu Jüri Audit Paneli'ndeki canlı karar
// iziyle aynı "sisteme güven" temasını taşıdığı halde başka bir sayfadaydı.
// Bu bileşen ikisini Jüri Audit Paneli'ne taşır - aynı hap+modal davranışı
// (tasarım/içerik AYNEN korunur), sadece konumu değişir.
export default function ModelVeriPanelleri() {
  const [metrikPaneliAcik, setMetrikPaneliAcik] = useState(false);
  const [veriPaneliAcik, setVeriPaneliAcik] = useState(false);

  const {
    tekilKampanya,
    anlikGoruntu,
    urunAilesi,
    ragParca,
    bankaDagilimi,
    bankaDagilimiToplami,
    enBuyukBankaTekil,
    baskinBankalar,
    baskinYuzde,
    zayifBankalar,
  } = useCanliVeriOzet();

  const modelPaneliniAc = () => {
    setVeriPaneliAcik(false);
    setMetrikPaneliAcik(true);
  };

  const veriPaneliniAc = () => {
    setMetrikPaneliAcik(false);
    setVeriPaneliAcik(true);
  };

  const bentoKartStil = {
    background: "var(--kart)",
    border: "1px solid var(--kenarlik)",
    borderRadius: 14,
    padding: 16,
    boxShadow: "0 1px 3px rgba(60,50,30,0.05)",
  };
  const bentoBaslikStil = {
    fontSize: 11,
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    color: "var(--yazi-soluk)",
    marginBottom: 12,
    fontWeight: 700,
  };
  const DolulukCubugu = ({ yuzde, renk }) => (
    <div style={{ height: 5, borderRadius: 3, background: "var(--kenarlik)", marginTop: 8, overflow: "hidden" }}>
      <div style={{ width: `${yuzde}%`, height: "100%", borderRadius: 3, background: renk }} />
    </div>
  );

  const hapStil = {
    height: 28,
    borderRadius: 14,
    padding: "0 12px",
    fontSize: 12,
    fontWeight: 600,
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    background: "var(--kart)",
    border: "1px solid var(--kenarlik)",
    color: "var(--yazi-koyu)",
    cursor: "pointer",
    transition: "all 0.2s ease",
  };

  return (
    <>
      <style>{`
        .metrik-modal .ant-modal-mask {
          background: rgba(12, 30, 26, 0.55) !important;
          backdrop-filter: blur(6px);
        }
        .metrik-modal .ant-modal {
          padding-bottom: 0 !important;
        }
        .metrik-modal .ant-modal-content {
          border-radius: 18px !important;
          padding: 24px !important;
        }
        .metrik-modal .ant-modal-header {
          margin-bottom: 0 !important;
          padding-bottom: 16px !important;
          border-bottom: 1px solid var(--kenarlik) !important;
        }
        .metrik-modal .ant-modal-body {
          max-height: 85vh;
          overflow-y: auto;
          padding-top: 20px !important;
        }
        .bento-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
        }
        @media (max-width: 900px) {
          .bento-grid { grid-template-columns: repeat(2, 1fr) !important; }
        }
        @media (max-width: 640px) {
          .bento-grid { grid-template-columns: 1fr !important; }
        }
        @media (max-width: 1100px) {
          .metrik-modal .ant-modal {
            width: 94% !important;
            max-width: 94vw !important;
          }
        }
      `}</style>

      <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
        <div
          onClick={modelPaneliniAc}
          style={hapStil}
          onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#d8c48c")}
          onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--kenarlik)")}
          title="Model metrikleri detay panelini aç"
        >
          <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#d8c48c" }} />
          Model Metrikleri
        </div>

        <div
          onClick={veriPaneliniAc}
          style={hapStil}
          onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#d8c48c")}
          onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--kenarlik)")}
          title="Veri kaynakları kapsam panelini aç"
        >
          <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#d8c48c" }} />
          Veri Kaynakları
        </div>
      </div>

      {/* ========================================================
          MODEL METRİKLERİ DETAY PANELİ (MODAL — BENTO DÜZEN)
          ======================================================== */}
      <Modal
        open={metrikPaneliAcik}
        onCancel={() => setMetrikPaneliAcik(false)}
        footer={null}
        width={1000}
        centered
        className="metrik-modal"
        title={
          <div>
            <div style={{ fontSize: 20, fontWeight: 650, color: "var(--yazi-koyu)" }}>
              Model Metrikleri
            </div>
            <div style={{ fontSize: 12, color: "var(--yazi-soluk)", fontWeight: 400, marginTop: 2 }}>
              Son ölçüm: {OLCUM_TARIHI} · {OLCUM_VERI_SETI} üzerinde
            </div>
          </div>
        }
      >
        <div className="bento-grid">
          {/* Kart A: Dolu Alan */}
          <div style={bentoKartStil}>
            <div style={bentoBaslikStil}>DOLU ALAN</div>
            <div style={{ fontSize: 34, fontWeight: 700, color: "#b8873a", lineHeight: 1 }}>
              %{OLCUMLER.cikarim.doluAlanDogrulugu.toString().replace(".", ",")}
            </div>
            <div style={{ fontSize: 12, color: "var(--yazi-normal)", marginTop: 4 }}>Doğruluk</div>
            <DolulukCubugu yuzde={OLCUMLER.cikarim.doluAlanDogrulugu} renk="#d4a34b" />
            <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 6 }}>{OLCUMLER.cikarim.doluAlanDetay}</div>
          </div>

          {/* Kart B: Boş Alan */}
          <div style={bentoKartStil}>
            <div style={bentoBaslikStil}>BOŞ ALAN</div>
            <div style={{ fontSize: 34, fontWeight: 700, color: "#0c765f", lineHeight: 1 }}>
              %{OLCUMLER.cikarim.bosAlanDogrulugu.toString().replace(".", ",")}
            </div>
            <div style={{ fontSize: 12, color: "var(--yazi-normal)", marginTop: 4 }}>Yanlış pozitif kontrolü</div>
            <DolulukCubugu yuzde={OLCUMLER.cikarim.bosAlanDogrulugu} renk="#169276" />
            <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 6 }}>{OLCUMLER.cikarim.bosAlanDetay}</div>
          </div>

          {/* Kart C: Makro F1 */}
          <div style={bentoKartStil}>
            <div style={bentoBaslikStil}>MAKRO F1</div>
            <div style={{ fontSize: 34, fontWeight: 700, color: "#b8873a", lineHeight: 1 }}>
              %{OLCUMLER.cikarim.makroF1.toString().replace(".", ",")}
            </div>
            <div style={{ fontSize: 12, color: "var(--yazi-normal)", marginTop: 4 }}>Alan bazlı</div>
            <DolulukCubugu yuzde={OLCUMLER.cikarim.makroF1} renk="#d4a34b" />
            <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 6 }}>{OLCUMLER.cikarim.makroF1Detay}</div>
          </div>

          {/* RAG Performansı — 2 sütun */}
          <div style={{ ...bentoKartStil, gridColumn: "span 2" }}>
            <div style={bentoBaslikStil}>RAG PERFORMANSI</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
                  <span style={{ fontSize: 13, color: "var(--yazi-normal)" }}>Recall@1</span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "#0c765f" }}>
                    %{OLCUMLER.rag.recall1.toString().replace(".", ",")}
                    <span style={{ fontSize: 11, color: "var(--yazi-soluk)", fontWeight: 400, marginLeft: 6 }}>
                      {OLCUMLER.rag.recall1Not}
                    </span>
                  </span>
                </div>
                <div style={{ height: 5, borderRadius: 3, background: "var(--kenarlik)", position: "relative", overflow: "hidden" }}>
                  <div style={{ position: "absolute", left: 0, top: 0, width: `${OLCUMLER.rag.recall1}%`, height: "100%", background: "#169276", borderRadius: 3 }} />
                </div>
              </div>

              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
                  <span style={{ fontSize: 13, color: "var(--yazi-normal)" }}>Recall@3</span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "#0c765f" }}>
                    %{OLCUMLER.rag.recall3.toString().replace(".", ",")}
                    <span style={{ fontSize: 11, color: "var(--yazi-soluk)", fontWeight: 400, marginLeft: 6 }}>{OLCUMLER.rag.recall5Detay}</span>
                  </span>
                </div>
                <DolulukCubugu yuzde={OLCUMLER.rag.recall3} renk="#169276" />
              </div>

              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
                  <span style={{ fontSize: 13, color: "var(--yazi-normal)" }}>Recall@5</span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "#0c765f" }}>
                    %{OLCUMLER.rag.recall5.toString().replace(".", ",")}
                    <span style={{ fontSize: 11, color: "var(--yazi-soluk)", fontWeight: 400, marginLeft: 6 }}>{OLCUMLER.rag.recall5Detay}</span>
                  </span>
                </div>
                <DolulukCubugu yuzde={OLCUMLER.rag.recall5} renk="#169276" />
              </div>

              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
                  <span style={{ fontSize: 13, color: "var(--yazi-normal)" }}>Çekimserlik</span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "#0c765f" }}>
                    %{OLCUMLER.rag.abstention}
                    <span style={{ fontSize: 11, color: "var(--yazi-soluk)", fontWeight: 400, marginLeft: 6 }}>{OLCUMLER.rag.abstentionDetay}</span>
                  </span>
                </div>
                <DolulukCubugu yuzde={OLCUMLER.rag.abstention} renk="#0c765f" />
              </div>
            </div>

            <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 14, paddingTop: 10, borderTop: "1px solid var(--kenarlik)" }}>
              İndeks: {OLCUMLER.rag.indekslenenParca} parça / {OLCUMLER.rag.belgeSayisi} belge · {OLCUMLER.rag.indeksTarihi}
            </div>
          </div>

          {/* Kapsam Ölçümü — 1 sütun */}
          <div style={bentoKartStil}>
            <div style={bentoBaslikStil}>KAPSAM ÖLÇÜMÜ</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 13, color: "var(--yazi-normal)" }}>Hassasiyet</span>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 14, fontWeight: 650, color: "var(--yazi-koyu)" }}>{OLCUMLER.kapsam.hassasiyet}</span>
                  <span style={{ fontSize: 10, fontWeight: 700, background: "rgba(12,118,95,0.12)", color: "#0c765f", padding: "2px 6px", borderRadius: 6 }}>%100</span>
                </div>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 13, color: "var(--yazi-normal)" }}>Özgüllük</span>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 14, fontWeight: 650, color: "var(--yazi-koyu)" }}>{OLCUMLER.kapsam.ozgulluk}</span>
                  <span style={{ fontSize: 10, fontWeight: 700, background: "rgba(12,118,95,0.12)", color: "#0c765f", padding: "2px 6px", borderRadius: 6 }}>%100</span>
                </div>
              </div>
            </div>
            <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 14 }}>Scope Guard</div>
          </div>

          {/* Otomatik Test — 1 sütun */}
          <div style={bentoKartStil}>
            <div style={bentoBaslikStil}>OTOMATİK TEST</div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
              <span style={{ fontSize: 28, fontWeight: 700, color: "#0c765f", lineHeight: 1 }}>{OLCUMLER.test.gecen}</span>
              <span style={{ fontSize: 12, color: "var(--yazi-normal)" }}>geçen test</span>
              <span style={{ fontSize: 10, fontWeight: 600, background: "var(--kenarlik)", color: "var(--yazi-soluk)", padding: "2px 7px", borderRadius: 6, marginLeft: "auto" }}>+{OLCUMLER.test.yavas} yavaş</span>
            </div>
            <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 14 }}>CI her push'ta çalışır.</div>
          </div>

          {/* Bilinen Hatalar — 2 sütun */}
          <div style={{ ...bentoKartStil, gridColumn: "span 2" }}>
            <div style={bentoBaslikStil}>BİLİNEN HATALAR</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
              {OLCUMLER.bilinenHatalar.map((hata, idx) => (
                <div key={hata.kod}>
                  {idx > 0 && <div style={{ borderTop: "1px solid var(--kenarlik)", margin: "10px 0" }} />}
                  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: 11, fontWeight: 700, background: "var(--hata-zemin)", color: "var(--hata-yazi)", padding: "2px 7px", borderRadius: 6, flexShrink: 0 }}>{hata.kod}</span>
                      <span style={{ fontWeight: 650, fontSize: 13, color: "var(--yazi-koyu)" }}>{hata.alan}</span>
                    </div>
                    <div style={{ fontSize: 12, color: "var(--yazi-normal)", lineHeight: 1.45, paddingLeft: 2 }}>{hata.aciklama}</div>
                  </div>
                </div>
              ))}
            </div>
            <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 12, paddingTop: 8, borderTop: "1px solid var(--kenarlik)" }}>
              Hatalar gizlenmez, kayıt altındadır.
            </div>
          </div>

          <div style={{ gridColumn: "1 / -1", fontSize: 11, color: "var(--yazi-soluk)", marginBottom: -4 }}>
            Altın renkli değerler çıkarım doğruluğunu, yeşil renkli değerler güvenilirlik ölçümlerini (yanlış pozitif kontrolü, kaynak bulma, çekimserlik) gösterir.
          </div>

          <div
            style={{
              gridColumn: "1 / -1",
              background: "var(--uyari-zemin)",
              border: "1px solid var(--kenarlik)",
              borderRadius: 12,
              padding: 14,
              display: "flex",
              alignItems: "flex-start",
              gap: 10,
              fontSize: 12.5,
              color: "var(--uyari-yazi)",
              lineHeight: 1.5,
            }}
          >
            <span style={{ fontSize: 16, flexShrink: 0, marginTop: 1 }}>⚠</span>
            {/* DENETIM BULGUSU (26.08.2026): eskiden bu uyari cikarim VE RAG'i
                TEK cumlede "yeniden olculmedi" diye birlikte etiketliyordu -
                ama cikarim {OLCUM_TARIHI}'nde GUNCEL 291 kayitlik canli
                sette olculdu (yani zaten "yeni set"), yalniz RAG hala eski
                indekste. Iki farkli gercegi tek cumleye sikistirmak yanlis
                bilgi veriyordu, ayri ayri yazildi. */}
            <span>
              Çıkarım oranları (Dolu/Boş Alan, Makro F1) <strong>{OLCUM_TARIHI}</strong> tarihinde{" "}
              <strong>291 canlı kayıt</strong> üzerinde, güncel veriyle ölçüldü. RAG Performansı ise{" "}
              <strong>{OLCUMLER.rag.indeksTarihi}</strong> tarihindeki <strong>{OLCUMLER.rag.indekslenenParca} parçalık</strong> indekste
              ölçüldü; canlı indeks o tarihten sonra {ragParca} parçaya büyüdü — <strong>yalnızca RAG oranları
              yeni indekste henüz yeniden ölçülmedi</strong>.
            </span>
          </div>
        </div>
      </Modal>

      {/* ========================================================
          VERİ KAYNAKLARI DETAY PANELİ (MODAL — BENTO DÜZEN)
          ======================================================== */}
      <Modal
        open={veriPaneliAcik}
        onCancel={() => setVeriPaneliAcik(false)}
        footer={null}
        width={1000}
        centered
        className="metrik-modal"
        title={
          <div>
            <div style={{ fontSize: 20, fontWeight: 650, color: "var(--yazi-koyu)" }}>
              Veri Kaynakları
            </div>
            <div style={{ fontSize: 12, color: "var(--yazi-soluk)", fontWeight: 400, marginTop: 2 }}>
              Kapsam raporu: {VERI_TARIHI} · PostgreSQL'den okundu
            </div>
          </div>
        }
      >
        <div className="bento-grid">
          {/* Kart A: TEKİL KAMPANYA */}
          <div style={bentoKartStil}>
            <div style={bentoBaslikStil}>TEKİL KAMPANYA</div>
            <div style={{ fontSize: 34, fontWeight: 700, color: "#0c5144", lineHeight: 1 }}>
              {tekilKampanya}
            </div>
            <div style={{ fontSize: 12, color: "var(--yazi-normal)", marginTop: 4 }}>Toplanan</div>
            <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 14 }}>
              {anlikGoruntu} tarihli anlık görüntü
            </div>
          </div>

          {/* Kart B: BANKA KAPSAMI */}
          <div style={bentoKartStil}>
            <div style={bentoBaslikStil}>BANKA KAPSAMI</div>
            <div style={{ fontSize: 34, fontWeight: 700, color: "#169276", lineHeight: 1 }}>
              {OLCUMLER.veri.kapsananBanka} / {OLCUMLER.veri.toplamBanka}
            </div>
            <div style={{ fontSize: 12, color: "var(--yazi-normal)", marginTop: 4 }}>Kapsanan katılım bankası</div>
            <DolulukCubugu yuzde={(OLCUMLER.veri.kapsananBanka / OLCUMLER.veri.toplamBanka) * 100} renk="#169276" />
            <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 6 }}>
              {OLCUMLER.veri.haricBanka} hariç
            </div>
          </div>

          {/* Kart C: GOLD VERİ SETİ */}
          <div style={bentoKartStil}>
            <div style={bentoBaslikStil}>GOLD VERİ SETİ</div>
            <div style={{ fontSize: 34, fontWeight: 700, color: "#b8873a", lineHeight: 1 }}>
              {OLCUMLER.veri.goldKayit}
            </div>
            <div style={{ fontSize: 12, color: "var(--yazi-normal)", marginTop: 4 }}>Elle doğrulanmış kayıt</div>
            <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 14 }}>
              referans veri seti
            </div>
          </div>

          {/* Banka Dağılımı Kartı (2 sütun) */}
          <div style={{ ...bentoKartStil, gridColumn: "span 2" }}>
            <div style={bentoBaslikStil}>BANKA BAZINDA DAĞILIM</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {bankaDagilimi.map((b) => {
                const yuzde = (b.tekil / enBuyukBankaTekil) * 100;
                const baskinMi = baskinBankalar.includes(b.banka);
                const cubukRengi = baskinMi ? "#d4a34b" : "#169276";

                return (
                  <div key={b.banka} style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <span style={{ fontSize: 13, fontWeight: 500, color: "var(--yazi-koyu)" }}>
                          {b.banka}
                        </span>
                        {baskinMi && (
                          <span style={{ fontSize: 10, fontWeight: 600, background: "var(--uyari-zemin)", color: "var(--uyari-yazi)", padding: "1px 5px", borderRadius: 5 }}>
                            baskın
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: 11, color: "var(--yazi-soluk)", display: "flex", alignItems: "center", gap: 4 }}>
                        <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>{b.tekil}</span>
                        <span>|</span>
                        <span>{b.snapshot ?? "—"}</span>
                        <span>|</span>
                        <span>{b.gold ?? "—"}</span>
                      </div>
                    </div>
                    <div style={{ width: "100%", height: 5, background: "var(--kenarlik)", borderRadius: 3, overflow: "hidden" }}>
                      <div style={{ width: `${yuzde}%`, height: "100%", background: cubukRengi, borderRadius: 3 }} />
                    </div>
                  </div>
                );
              })}

              <div style={{ borderTop: "2px solid var(--kenarlik)", paddingTop: 8, marginTop: 4, display: "flex", justifyContent: "space-between", alignItems: "center", fontWeight: 700 }}>
                <span style={{ fontSize: 13, color: "var(--yazi-koyu)" }}>Toplam</span>
                <div style={{ fontSize: 11, color: "var(--yazi-koyu)", display: "flex", alignItems: "center", gap: 4 }}>
                  <span>{bankaDagilimiToplami}</span>
                  <span>|</span>
                  <span>{bankaDagilimi.reduce((s, b) => s + (b.snapshot ?? 0), 0)}</span>
                  <span>|</span>
                  <span>{bankaDagilimi.reduce((s, b) => s + (b.gold ?? 0), 0)}</span>
                </div>
              </div>
            </div>

            {/* DENETIM BULGUSU (26.08.2026): eskiden burada "veri kapsami
                boslugu" deniyordu - bu, dusuk sayili bankalarin taramada
                KACIRILDIGINI ima ediyordu. Gercekte oyle degil: ör. T.O.M.
                Katilim'in kendi sitesi zaten tek bir sayfada birkac
                kampanya yayinliyor (bkz. docs/extraction_accuracy_
                raporu.md, "C6" bulgusu) - dusuk sayi bankanin kendi
                yayinladigi kampanya adedidir, tarama eksikligi degil. */}
            <div
              style={{
                background: "var(--uyari-zemin)",
                border: "1px solid var(--kenarlik)",
                borderRadius: 8,
                padding: "10px 12px",
                fontSize: 11.5,
                color: "var(--uyari-yazi)",
                lineHeight: 1.45,
                marginTop: 12,
              }}
            >
              Altın renkli iki banka ({baskinBankalar.join(" ve ")}) toplam kampanyaların %{baskinYuzde}'sini oluşturuyor. Diğer uçta {zayifBankalar} kampanya var — bu bir tarama eksikliği değil, bu bankaların o an sitesinde yayında olan kampanya sayısı bu kadardır.
            </div>
          </div>

          {/* Zaman Ekseni Kartı (1 sütun) */}
          <div style={bentoKartStil}>
            <div style={bentoBaslikStil}>ZAMAN EKSENİ</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 13 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ color: "var(--yazi-normal)" }}>İlk görülme</span>
                <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>{ZAMAN_EKSENI.ilkGorulme}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ color: "var(--yazi-normal)" }}>Son görülme</span>
                <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>{ZAMAN_EKSENI.sonGorulme}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ color: "var(--yazi-normal)" }}>Bayatlık</span>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ fontWeight: 600, color: "#0c765f" }}>{ZAMAN_EKSENI.bayatlikGun} gün</span>
                  <span style={{ fontSize: 10, fontWeight: 600, background: "rgba(12,118,95,0.12)", color: "#0c765f", padding: "1px 5px", borderRadius: 5 }}>güncel</span>
                </div>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ color: "var(--yazi-normal)" }}>Değişen kampanya</span>
                <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>{ZAMAN_EKSENI.degisenKampanya} / {tekilKampanya}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ color: "var(--yazi-normal)" }}>Ortalama versiyon</span>
                <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>{ZAMAN_EKSENI.ortalamaVersiyon.toString().replace(".", ",")}</span>
              </div>
            </div>
          </div>

          {/* Ürün Ailesi Kartı (2 sütun) */}
          <div style={{ ...bentoKartStil, gridColumn: "span 2" }}>
            <div style={bentoBaslikStil}>ÜRÜN AİLESİ DAĞILIMI</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {urunAilesi.map((u) => {
                const dusukMu = u.doluluk < 25;
                const yaziRengi = dusukMu ? "#b8873a" : "#0c765f";
                const cubukRengi = dusukMu ? "#d4a34b" : "#169276";
                const kaynaktaYokMu = u.ad === "Belirtilmemiş";

                return (
                  <div key={u.ad} style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <span style={{ fontSize: 13, fontWeight: 500, color: "var(--yazi-koyu)" }}>{u.ad}</span>
                        {kaynaktaYokMu && (
                          <span style={{ fontSize: 10, fontWeight: 600, background: "var(--kart-ustu)", color: "var(--yazi-soluk)", padding: "1px 5px", borderRadius: 5 }}>
                            kaynakta yok
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 12 }}>
                        <span style={{ fontWeight: 600, color: "var(--yazi-koyu)" }}>{u.sayi}</span>
                        <span style={{ fontWeight: 600, color: yaziRengi, minWidth: 46, textAlign: "right" }}>
                          %{u.doluluk.toString().replace(".", ",")}
                        </span>
                      </div>
                    </div>
                    <div style={{ width: "100%", height: 5, background: "var(--kenarlik)", borderRadius: 3, overflow: "hidden" }}>
                      <div style={{ width: `${u.doluluk}%`, height: "100%", background: cubukRengi, borderRadius: 3 }} />
                    </div>
                  </div>
                );
              })}
            </div>

            <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 12, paddingTop: 8, borderTop: "1px solid var(--kenarlik)" }}>
              Alan doluluk, o üründeki kampanyaların yapılandırılmış alanlarının ne kadarının dolu olduğunu gösterir. Düşük oran veri eksikliğidir, hata değildir.
            </div>
          </div>

          {/* Kapsam Dışı Banka Kartı (1 sütun) */}
          <div style={{ ...bentoKartStil, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <span style={bentoBaslikStil}>KAPSAM DIŞI BANKA</span>
                <span style={{ fontSize: 10, fontWeight: 600, background: "var(--kenarlik)", color: "var(--yazi-soluk)", padding: "1px 6px", borderRadius: 5 }}>1 banka</span>
              </div>
              <div style={{ fontSize: 18, fontWeight: 700, color: "var(--yazi-koyu)", marginBottom: 6 }}>
                {OLCUMLER.veri.haricBanka}
              </div>
              <div style={{ fontSize: 12, color: "var(--yazi-normal)", lineHeight: 1.5 }}>
                BDDK listesinde yer alıyor ancak ürün/kampanya yayımlamadığı için hariç tutuldu.
              </div>
            </div>
            <div style={{ fontSize: 11, color: "var(--yazi-soluk)", marginTop: 14 }}>
              Periyodik olarak yeniden kontrol ediliyor.
            </div>
          </div>

          <div
            style={{
              gridColumn: "1 / -1",
              background: "var(--zemin-yumusak)",
              border: "1px solid var(--kenarlik)",
              borderRadius: 12,
              padding: 14,
              fontSize: 12.5,
              color: "var(--yazi-normal)",
              lineHeight: 1.5,
            }}
          >
            Bilinen sınırlama: Aktif/Süresi dolmuş yaşam döngüsü durumu yalnızca PostgreSQL'de hesaplanır. Bu rapor veritabanı okumadığı için aktif kampanya sayısı içermez.
          </div>
        </div>
      </Modal>
    </>
  );
}

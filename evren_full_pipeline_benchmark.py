"""EVREN FULL PIPELINE BENCHMARK - Regex → NER → EVREN LLM → Validation

AMAÇ: Mevcut extraction pipeline'ının her aşamasını (Regex, NER, EVREN LLM,
Validation) AYRI AYRI ölçerek her katmanın gerçek katkısını sayısal olarak
ortaya çıkarmak.

HİÇBİR KOD DEĞİŞTİRİLMEZ - mevcut production pipeline kullanılır.

ÖLÇÜLEN 4 SEVIYE:
  1. REGEX ONLY     : Sadece regex çıktısı
  2. REGEX + NER    : Regex + NER birleşik sonucu
  3. REGEX + NER + EVREN : EVREN LLM eklendikten sonra
  4. FINAL OUTPUT   : Validation/normalization sonrası

Kullanım:
    python evren_full_pipeline_benchmark.py
"""

import ortam_yukle  # noqa: F401 - .env yükle

import json
import time
from pathlib import Path
from typing import Any

from extraction import hybrid_pipeline as hp
from extraction import regex_extractor as regex
from scraper.scripts.extraction_accuracy import (
    ALAN_ESLEME,
    ALAN_NORMALIZE,
    _degerler_esit_mi,
    altin_kayitlari_yukle,
)
from scraper.scripts.gold_eslesme import scraper_kaydini_bul

GOLD = Path(__file__).parent / "gold_dataset" / "altin_veri_seti.json"
RESULTS_JSON = Path(__file__).parent / "EVREN_FULL_PIPELINE_RESULTS.json"
REPORT_MD = Path(__file__).parent / "EVREN_FULL_PIPELINE_BENCHMARK.md"

# Her aşamanın TP/FP/FN'lerini ayrı tutacağız
STAGE_NAMES = ["regex", "regex_ner", "regex_ner_evren", "final"]


class BenchmarkSayac:
    """Bir aşama için TP/FP/FN sayıları"""
    def __init__(self):
        self.tp = 0
        self.fp = 0
        self.fn = 0
        self.tp_fields: list[dict] = []
        self.fp_fields: list[dict] = []
        self.fn_fields: list[dict] = []


def benchmark_calistir() -> dict:
    """Ana benchmark fonksiyonu - tüm aşamaları ölçer"""
    
    print("\n" + "=" * 80)
    print("EVREN FULL PIPELINE BENCHMARK BAŞLIYOR")
    print("=" * 80)
    print(f"Golden dataset: {GOLD}")
    print("HİÇBİR KOD DEĞİŞTİRİLMİYOR - Production pipeline kullanılıyor\n")
    
    # Aşama sayaçları
    sayaclar = {stage: BenchmarkSayac() for stage in STAGE_NAMES}
    
    # Alan bazlı sayaçlar (her aşama için ayrı)
    alan_sayaclar = {
        stage: {alan: {"tp": 0, "fp": 0, "fn": 0} for alan in ALAN_ESLEME}
        for stage in STAGE_NAMES
    }
    
    # EVREN katkı istatistikleri
    evren_stats = {
        "toplam_cagri": 0,
        "yeni_dogru_alan": 0,
        "yanlıs_alan": 0,
        "recovery_ornekleri": [],  # Regex+NER bulamadı ama EVREN buldu
        "called_records": [],
    }
    
    # NER katkı istatistikleri
    ner_stats = {
        "toplam_cagri": 0,
        "yeni_dogru_alan": 0,
        "yanlıs_alan": 0,
        "called_records": [],
    }
    
    # Performans ölçümleri
    timings = {
        "total": 0,
        "cold_start": None,
        "records": [],
    }
    
    # Tüm kayıtların detaylı sonuçları
    detailed_results = []
    
    # Kayıt sayaçları
    canli_kayit_sayisi = 0
    toplam_gold_kayit = 0
    
    altin_kayitlar = [k for k in altin_kayitlari_yukle() if (k.get("giren_kisi") or "").strip()]
    toplam_gold_kayit = len(altin_kayitlar)
    
    print(f"Toplam golden kayıt (imzalı): {toplam_gold_kayit}")
    print(f"Test başlıyor...\n")
    
    start_total = time.time()
    first_record = True
    
    for idx, altin in enumerate(altin_kayitlar, 1):
        if idx % 10 == 0:
            print(f"İşleniyor: {idx}/{toplam_gold_kayit} kayıt...")
        
        # Scraper verisiyle eşleştir
        cikti_json = scraper_kaydini_bul(altin)
        if cikti_json is None:
            continue
        
        canli_kayit_sayisi += 1
        ham_metin = cikti_json["ham_metin"]
        kayit_id = altin["kayit_id"]
        
        record_start = time.time()
        
        # === GERÇEK HİBRİT PİPELİNE ÇAĞRISI ===
        # Bu, production'da kullanılan gerçek fonksiyon
        try:
            hibrit_sonuc = hp.kaydi_hibrit_cikar(ham_metin)
        except Exception as e:
            print(f"HATA [{kayit_id}]: {e}")
            continue
        
        record_time = (time.time() - record_start) * 1000
        timings["records"].append(record_time)
        
        if first_record:
            timings["cold_start"] = record_time
            first_record = False
        
        # Metadata çıkar
        kaynaklar = hibrit_sonuc.pop("_kaynaklar", {})
        izler = hibrit_sonuc.pop("_izler", {})
        adaylar = hibrit_sonuc.pop("_adaylar", {})
        catismalar = hibrit_sonuc.pop("_catismalar", {})
        kampanya_avantaji = hibrit_sonuc.pop("kampanya_avantaji", None)
        
        # === AŞAMA BAZLI SONUÇLARI AYIR ===
        # Hangi alanın hangi aşamadan geldiğini kaynaklar dict'i gösteriyor
        
        stage_results = {
            "regex": {},
            "regex_ner": {},
            "regex_ner_evren": {},
            "final": hibrit_sonuc.copy(),  # Final = validation sonrası
        }
        
        # Aşamaları simüle et
        for alan, deger in hibrit_sonuc.items():
            if deger is None:
                continue
            
            kaynak = kaynaklar.get(alan, "")
            
            # Regex aşaması
            if kaynak == "regex":
                stage_results["regex"][alan] = deger
                stage_results["regex_ner"][alan] = deger
                stage_results["regex_ner_evren"][alan] = deger
            
            # NER aşaması
            elif kaynak == "ner":
                stage_results["regex_ner"][alan] = deger
                stage_results["regex_ner_evren"][alan] = deger
            
            # EVREN LLM aşaması
            elif kaynak == "llm":
                stage_results["regex_ner_evren"][alan] = deger
        
        # NER/EVREN çağrı kontrolü
        ner_called = any("ner" in [a.get("katman") for a in adaylar.get(alan_key, [])] 
                        for alan_key in adaylar)
        llm_called = any("llm" in [a.get("katman") for a in adaylar.get(alan_key, [])] 
                        for alan_key in adaylar)
        
        if ner_called:
            ner_stats["toplam_cagri"] += 1
            ner_stats["called_records"].append(kayit_id)
        
        if llm_called:
            evren_stats["toplam_cagri"] += 1
            evren_stats["called_records"].append(kayit_id)
        
        # === HER AŞAMA İÇİN GROUND TRUTH İLE KARŞILAŞTIR ===
        belirtilmemis = altin.get("alan_belirtilmemis") or {}
        
        record_detail = {
            "record_id": kayit_id,
            "ground_truth": {},
            "stages": {},
            "field_sources": kaynaklar.copy(),
            "time_ms": record_time,
        }
        
        for extractor_alan, gold_alan in ALAN_ESLEME.items():
            beklenen = altin.get(gold_alan)
            
            # Normalizasyon uygula
            normalize = ALAN_NORMALIZE.get(gold_alan)
            if normalize and beklenen:
                beklenen = normalize(beklenen)
            
            # Ground truth'u kaydet
            if beklenen is not None or belirtilmemis.get(gold_alan):
                record_detail["ground_truth"][extractor_alan] = beklenen
            
            # Her aşama için karşılaştır
            for stage_name in STAGE_NAMES:
                bulunan = stage_results[stage_name].get(extractor_alan)
                
                if normalize and bulunan:
                    bulunan = normalize(bulunan)
                
                # Aşama sonucunu kaydet
                if stage_name not in record_detail["stages"]:
                    record_detail["stages"][stage_name] = {}
                record_detail["stages"][stage_name][extractor_alan] = bulunan
                
                # Sadece ground truth'ta olan alanları ölç
                if beklenen is None:
                    if belirtilmemis.get(gold_alan) and bulunan is not None:
                        # False Positive
                        sayaclar[stage_name].fp += 1
                        sayaclar[stage_name].fp_fields.append({
                            "record_id": kayit_id,
                            "alan": extractor_alan,
                            "predicted": bulunan,
                        })
                        alan_sayaclar[stage_name][extractor_alan]["fp"] += 1
                    continue
                
                # Beklenen değer var
                if _degerler_esit_mi(beklenen, bulunan):
                    # True Positive
                    sayaclar[stage_name].tp += 1
                    sayaclar[stage_name].tp_fields.append({
                        "record_id": kayit_id,
                        "alan": extractor_alan,
                        "value": bulunan,
                    })
                    alan_sayaclar[stage_name][extractor_alan]["tp"] += 1
                else:
                    # False Negative
                    sayaclar[stage_name].fn += 1
                    sayaclar[stage_name].fn_fields.append({
                        "record_id": kayit_id,
                        "alan": extractor_alan,
                        "expected": beklenen,
                        "predicted": bulunan,
                    })
                    alan_sayaclar[stage_name][extractor_alan]["fn"] += 1
                
                # EVREN RECOVERY: Regex+NER bulamadı ama EVREN buldu
                if (stage_name == "regex_ner_evren" and 
                    _degerler_esit_mi(beklenen, bulunan) and
                    stage_results["regex_ner"].get(extractor_alan) is None and
                    kaynak == "llm"):
                    evren_stats["recovery_ornekleri"].append({
                        "record_id": kayit_id,
                        "alan": extractor_alan,
                        "value": bulunan,
                        "ground_truth": beklenen,
                    })
        
        detailed_results.append(record_detail)
    
    timings["total"] = (time.time() - start_total) * 1000
    
    # EVREN/NER katkı hesapla
    for stage_name in ["regex_ner", "regex_ner_evren"]:
        prev_stage = "regex" if stage_name == "regex_ner" else "regex_ner"
        yeni_tp = sayaclar[stage_name].tp - sayaclar[prev_stage].tp
        yeni_fp = sayaclar[stage_name].fp - sayaclar[prev_stage].fp
        
        if stage_name == "regex_ner":
            ner_stats["yeni_dogru_alan"] = yeni_tp
            ner_stats["yanlıs_alan"] = yeni_fp
        else:
            evren_stats["yeni_dogru_alan"] = yeni_tp
            evren_stats["yanlıs_alan"] = yeni_fp
    
    print(f"\n✅ Test tamamlandı!")
    print(f"Canlı kayıt sayısı: {canli_kayit_sayisi}/{toplam_gold_kayit}")
    print(f"Toplam süre: {timings['total']/1000:.1f} saniye\n")
    
    # Sonuçları dön
    return {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_gold_records": toplam_gold_kayit,
            "canli_kayit_sayisi": canli_kayit_sayisi,
        },
        "stages": {
            stage: {
                "tp": sayaclar[stage].tp,
                "fp": sayaclar[stage].fp,
                "fn": sayaclar[stage].fn,
                "precision": round(sayaclar[stage].tp / (sayaclar[stage].tp + sayaclar[stage].fp) * 100, 2) 
                             if (sayaclar[stage].tp + sayaclar[stage].fp) > 0 else 0.0,
                "recall": round(sayaclar[stage].tp / (sayaclar[stage].tp + sayaclar[stage].fn) * 100, 2)
                         if (sayaclar[stage].tp + sayaclar[stage].fn) > 0 else 0.0,
                "f1": 0.0,  # Hesaplanacak
            }
            for stage in STAGE_NAMES
        },
        "field_level": alan_sayaclar,
        "evren_contribution": evren_stats,
        "ner_contribution": ner_stats,
        "timings": timings,
        "detailed_records": detailed_results,
        "false_positives": {stage: sayaclar[stage].fp_fields for stage in STAGE_NAMES},
        "false_negatives": {stage: sayaclar[stage].fn_fields for stage in STAGE_NAMES},
    }


def hesapla_f1(sonuc: dict):
    """Precision ve Recall'dan F1 hesapla"""
    for stage in STAGE_NAMES:
        p = sonuc["stages"][stage]["precision"]
        r = sonuc["stages"][stage]["recall"]
        if p > 0 and r > 0:
            sonuc["stages"][stage]["f1"] = round(2 * p * r / (p + r), 2)
        else:
            sonuc["stages"][stage]["f1"] = 0.0


def json_kaydet(sonuc: dict):
    """Detaylı sonuçları JSON'a kaydet"""
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(sonuc, f, indent=2, ensure_ascii=False)
    print(f"✅ Detaylı sonuçlar kaydedildi: {RESULTS_JSON}")


def rapor_olustur(sonuc: dict):
    """Markdown rapor oluştur"""
    
    lines = []
    lines.append("# EVREN FULL PIPELINE BENCHMARK RAPORU")
    lines.append("")
    lines.append(f"**Tarih:** {sonuc['metadata']['timestamp']}")
    lines.append(f"**Toplam Golden Kayıt:** {sonuc['metadata']['total_gold_records']}")
    lines.append(f"**Canlı Kayıt Sayısı:** {sonuc['metadata']['canli_kayit_sayisi']}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # ANA TABLO
    lines.append("## 1. PIPELINE PERFORMANS TABLOSU")
    lines.append("")
    lines.append("| Pipeline | TP | FP | FN | Precision | Recall | F1 |")
    lines.append("|----------|----|----|----|-----------| -------|-----|")
    
    stage_labels = {
        "regex": "Regex",
        "regex_ner": "Regex + NER",
        "regex_ner_evren": "Regex + NER + EVREN",
        "final": "Final",
    }
    
    for stage in STAGE_NAMES:
        s = sonuc["stages"][stage]
        lines.append(f"| {stage_labels[stage]} | {s['tp']} | {s['fp']} | {s['fn']} | {s['precision']:.2f}% | {s['recall']:.2f}% | {s['f1']:.2f}% |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # EVREN KATKI TABLOSU
    lines.append("## 2. AŞAMA KATKILARI")
    lines.append("")
    lines.append("| Aşama | Yeni Doğru Alan | Eklenen FP | Toplam TP | Çağrı Sayısı |")
    lines.append("|-------|-----------------|-----------|-----------|--------------|")
    
    regex_tp = sonuc["stages"]["regex"]["tp"]
    ner_tp = sonuc["stages"]["regex_ner"]["tp"]
    evren_tp = sonuc["stages"]["regex_ner_evren"]["tp"]
    
    regex_fp = sonuc["stages"]["regex"]["fp"]
    ner_fp = sonuc["stages"]["regex_ner"]["fp"]
    evren_fp = sonuc["stages"]["regex_ner_evren"]["fp"]
    
    lines.append(f"| Regex | {regex_tp} | {regex_fp} | {regex_tp} | - |")
    lines.append(f"| NER | +{ner_tp - regex_tp} | +{ner_fp - regex_fp} | {ner_tp} | {sonuc['ner_contribution']['toplam_cagri']} |")
    lines.append(f"| EVREN | +{evren_tp - ner_tp} | +{evren_fp - ner_fp} | {evren_tp} | {sonuc['evren_contribution']['toplam_cagri']} |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # EVREN DETAYLI ANALİZ
    lines.append("## 3. EVREN KATKI ANALİZİ")
    lines.append("")
    lines.append(f"**Toplam EVREN Çağrısı:** {sonuc['evren_contribution']['toplam_cagri']}")
    lines.append(f"**Yeni Doğru Alan:** {sonuc['evren_contribution']['yeni_dogru_alan']}")
    lines.append(f"**Yanlış Alan:** {sonuc['evren_contribution']['yanlıs_alan']}")
    lines.append(f"**Recovery Örnekleri (Regex+NER bulamadı, EVREN buldu):** {len(sonuc['evren_contribution']['recovery_ornekleri'])}")
    lines.append("")
    
    if sonuc['evren_contribution']['recovery_ornekleri']:
        lines.append("### EVREN Recovery Örnekleri")
        lines.append("")
        lines.append("Regex ve NER'in bulamadığı ancak EVREN'in bulduğu alanlar:")
        lines.append("")
        for ex in sonuc['evren_contribution']['recovery_ornekleri'][:10]:
            lines.append(f"- [{ex['record_id']}] `{ex['alan']}` = `{ex['value']}` (GT: `{ex['ground_truth']}`)")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # NER DETAYLI ANALİZ
    lines.append("## 4. NER KATKI ANALİZİ")
    lines.append("")
    lines.append(f"**Toplam NER Çağrısı:** {sonuc['ner_contribution']['toplam_cagri']}")
    lines.append(f"**Yeni Doğru Alan:** {sonuc['ner_contribution']['yeni_dogru_alan']}")
    lines.append(f"**Yanlış Alan:** {sonuc['ner_contribution']['yanlıs_alan']}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # PERFORMANS
    lines.append("## 5. PERFORMANS")
    lines.append("")
    lines.append(f"**Toplam Süre:** {sonuc['timings']['total']/1000:.1f} saniye")
    
    if sonuc['timings']['cold_start']:
        lines.append(f"**İlk Kayıt (Cold Start):** {sonuc['timings']['cold_start']:.1f} ms")
    
    if sonuc['timings']['records']:
        avg_time = sum(sonuc['timings']['records']) / len(sonuc['timings']['records'])
        lines.append(f"**Ortalama Kayıt Başı:** {avg_time:.1f} ms")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # FALSE POSITIVES
    lines.append("## 6. FALSE POSITIVE ANALİZİ")
    lines.append("")
    
    for stage in ["regex_ner_evren"]:  # Sadece final aşamayı göster
        fps = sonuc["false_positives"][stage]
        if fps:
            lines.append(f"### {stage_labels[stage]} ({len(fps)} FP)")
            lines.append("")
            # Kaynak bazlı grupla
            by_source = {}
            for fp in fps:
                alan = fp["alan"]
                source = sonuc["detailed_records"][0]["field_sources"].get(alan, "unknown")  # İlk kaydın source'u
                if source not in by_source:
                    by_source[source] = []
                by_source[source].append(fp)
            
            for source, fps_list in by_source.items():
                lines.append(f"**Kaynak: {source}** ({len(fps_list)} FP)")
                for fp in fps_list[:5]:
                    lines.append(f"- [{fp['record_id']}] `{fp['alan']}` = `{fp['predicted']}`")
                lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # FALSE NEGATIVES
    lines.append("## 7. FALSE NEGATIVE ANALİZİ (En Çok Kaçırılan Alanlar)")
    lines.append("")
    
    # Final aşamadaki FN'leri alan bazında grupla
    fns = sonuc["false_negatives"]["final"]
    if fns:
        fn_by_field = {}
        for fn in fns:
            alan = fn["alan"]
            if alan not in fn_by_field:
                fn_by_field[alan] = []
            fn_by_field[alan].append(fn)
        
        # En çok kaçırılan alanları sırala
        sorted_fields = sorted(fn_by_field.items(), key=lambda x: len(x[1]), reverse=True)
        
        lines.append(f"**Toplam FN:** {len(fns)}")
        lines.append("")
        
        for alan, fn_list in sorted_fields[:10]:
            lines.append(f"### `{alan}` ({len(fn_list)} FN)")
            lines.append("")
            for fn in fn_list[:3]:
                lines.append(f"- [{fn['record_id']}] Beklenen: `{fn['expected']}`, Bulunan: `{fn['predicted']}`")
            lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # GENEL DEĞERLENDİRME
    lines.append("## 8. GENEL DEĞERLENDİRME")
    lines.append("")
    
    final_f1 = sonuc["stages"]["final"]["f1"]
    regex_f1 = sonuc["stages"]["regex"]["f1"]
    improvement = final_f1 - regex_f1
    
    lines.append(f"- **Regex Only F1:** {regex_f1:.2f}%")
    lines.append(f"- **Final Pipeline F1:** {final_f1:.2f}%")
    lines.append(f"- **İyileşme:** +{improvement:.2f} puan")
    lines.append("")
    
    ner_tp_gain = sonuc["stages"]["regex_ner"]["tp"] - sonuc["stages"]["regex"]["tp"]
    evren_tp_gain = sonuc["stages"]["regex_ner_evren"]["tp"] - sonuc["stages"]["regex_ner"]["tp"]
    
    lines.append(f"- **NER Katkısı:** +{ner_tp_gain} doğru alan")
    lines.append(f"- **EVREN Katkısı:** +{evren_tp_gain} doğru alan")
    lines.append(f"- **EVREN Recovery Oranı:** {len(sonuc['evren_contribution']['recovery_ornekleri'])}/{sonuc['evren_contribution']['toplam_cagri']} çağrıda yeni alan buldu")
    lines.append("")
    
    # Markdown dosyasına yaz
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"✅ Markdown rapor oluşturuldu: {REPORT_MD}")


def ozet_yazdir(sonuc: dict):
    """Konsola özet yazdır"""
    print("\n" + "=" * 80)
    print("BENCHMARK SONUÇLARI")
    print("=" * 80)
    print("")
    print(f"DATASET:")
    print(f"  Toplam kayıt: {sonuc['metadata']['canli_kayit_sayisi']}")
    print("")
    
    for stage, label in [("regex", "REGEX"), ("regex_ner", "REGEX + NER"), 
                         ("regex_ner_evren", "REGEX + NER + EVREN"), ("final", "FINAL")]:
        s = sonuc["stages"][stage]
        print(f"{label}:")
        print(f"  Precision: {s['precision']:.2f}%")
        print(f"  Recall: {s['recall']:.2f}%")
        print(f"  F1: {s['f1']:.2f}%")
        print("")
    
    print("EVREN:")
    print(f"  Toplam çağrı: {sonuc['evren_contribution']['toplam_cagri']}")
    print(f"  Yeni doğru alan: {sonuc['evren_contribution']['yeni_dogru_alan']}")
    print(f"  Yanlış alan: {sonuc['evren_contribution']['yanlıs_alan']}")
    print(f"  Recovery örnekleri: {len(sonuc['evren_contribution']['recovery_ornekleri'])}")
    print("")
    
    print("NER:")
    print(f"  Toplam çağrı: {sonuc['ner_contribution']['toplam_cagri']}")
    print(f"  Yeni doğru alan: {sonuc['ner_contribution']['yeni_dogru_alan']}")
    print(f"  Yanlış alan: {sonuc['ner_contribution']['yanlıs_alan']}")
    print("")
    
    # En çok kaçırılan alanlar
    fns = sonuc["false_negatives"]["final"]
    if fns:
        fn_by_field = {}
        for fn in fns:
            alan = fn["alan"]
            fn_by_field[alan] = fn_by_field.get(alan, 0) + 1
        
        sorted_fields = sorted(fn_by_field.items(), key=lambda x: x[1], reverse=True)[:5]
        print("EN ÇOK KAÇIRILAN ALANLAR:")
        for alan, count in sorted_fields:
            print(f"  {alan}: {count} FN")
    print("")
    
    print("GENEL SONUÇ:")
    print(f"  Regex → Final iyileşme: +{sonuc['stages']['final']['f1'] - sonuc['stages']['regex']['f1']:.2f} puan F1")
    print(f"  EVREN gerçekten katkı sağlıyor: {sonuc['evren_contribution']['yeni_dogru_alan'] > 0}")
    print("")
    print(f"Dosyalar:")
    print(f"  - {RESULTS_JSON}")
    print(f"  - {REPORT_MD}")
    print("")


def main():
    """Ana fonksiyon"""
    try:
        sonuc = benchmark_calistir()
        hesapla_f1(sonuc)
        ozet_yazdir(sonuc)
        json_kaydet(sonuc)
        rapor_olustur(sonuc)
    except KeyboardInterrupt:
        print("\n\n❌ Test kullanıcı tarafından durduruldu")
    except Exception as e:
        print(f"\n\n❌ HATA: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

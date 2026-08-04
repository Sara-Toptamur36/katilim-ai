"""Extraction Accuracy olcumu (Zeynep Veri Toplama Rehberi, Sprint 3 Gun 4).

Regex cikarim motorunu (extraction/regex_extractor.py), scraper'in gercek
verisi + Altin Veri Seti referans degerleriyle karsilastirip alan bazli
dogruluk yuzdesi hesaplar.

BAGIMSIZLIK NOTU: Bu olcum Docker/PostgreSQL GEREKTIRMEZ ve aktif olarak
bir sey yapilmasini beklemez - `kaydi_cikar()` saf bir fonksiyondur
(veritabani yok), dogrudan scraper'in urettigi ham_metin uzerinde cagrilir.

Rapor Bolum 13: Extraction Accuracy hedefi >= %95 (henuz gercek veriyle
olculmemis bir hedefti - bu script ilk gercek olcumu yapar).

SPRINT 2 GENELLESTIRMESI: `extraction_accuracy_hesapla()` artik hangi
cikarim fonksiyonunun olculecegini parametre olarak alir (varsayilan
kaydi_cikar - mevcut regex-only davranis/regresyon testi degismedi).
Boylece extraction/hybrid_pipeline.py::kaydi_hibrit_cikar() gibi ayni
{"alan": deger, ..., "_izler": {...}} seklini doner uyumlu herhangi bir
fonksiyon da AYNI altin veri setiyle olculebilir - bkz.
scraper/scripts/hibrit_extraction_accuracy.py (NER+LLM katmanlarinin
eklenmesi regex'in tek basina dogrulugunu gercekten artiriyor mu sorusu
icin).

Kullanim:
    python -m scraper.scripts.extraction_accuracy
"""

from __future__ import annotations

import json
from pathlib import Path

from extraction.regex_extractor import kaydi_cikar
from scraper.scripts.gold_eslesme import scraper_kaydini_bul

GOLD = Path(__file__).resolve().parent.parent.parent / "gold_dataset" / "altin_veri_seti.json"

# Altin Veri Seti alan adindan (sutun basligi), regex_extractor.kaydi_cikar()
# cikti alan adina esleme - ikisi ayni kavram icin farkli isim kullaniyor
# (ör. gold "kar_payi_orani" <-> extractor "kar_payi_orani_percent").
ALAN_ESLEME = {
    "kar_payi_orani_percent": "kar_payi_orani",
    "vade_ay": "vade_ay",
    "odul_miktari": "odul_miktari",
    "odul_birimi": "odul_birimi",
    "finansman_tutari": "finansman_tutari",
    "taksit_sayisi": "taksit_sayisi",
    "erteleme_suresi_ay": "erteleme_suresi_ay",
}

TOLERANS = 0.01  # ondalik yuvarlama farkini tolere et (ör. 2.990001 vs 2.99)


def _degerler_esit_mi(beklenen, bulunan) -> bool:
    if isinstance(beklenen, (int, float)) and isinstance(bulunan, (int, float)):
        return abs(beklenen - bulunan) <= TOLERANS
    return beklenen == bulunan


def altin_kayitlari_yukle() -> list[dict]:
    with open(GOLD, encoding="utf-8") as f:
        return json.load(f)


def extraction_accuracy_hesapla(cikarim_fonksiyonu=kaydi_cikar) -> dict:
    """Alan bazli dogruluk: her altin kayittaki her DOLU alan icin,
    `cikarim_fonksiyonu(ham_metin)` cikariminin ayni degeri uretip
    uretmedigini kontrol eder.

    `cikarim_fonksiyonu`, kaydi_cikar() ile AYNI imzaya (ham_metin -> dict)
    ve alan adlarina sahip herhangi bir fonksiyon olabilir - ornegin
    extraction/hybrid_pipeline.py::kaydi_hibrit_cikar(). Varsayilan deger
    kaydi_cikar (regex) - mevcut cagiran kodlar/testler etkilenmez.

    Yalnizca (a) altin kayitta o alan gercekten doluysa VE (b) kampanya
    hala sitede canliysa (scraper_kaydini_bul bir kayit buluyorsa) olcuma
    dahil edilir - rotasyona ugramis kampanyalar (bkz.
    tests/test_scraper_regresyon.py) dogruluk oranini haksiz yere
    dusurmesin: bu veri kaybi kampanya rotasyonudur, cikarim hatasi degil.
    """
    toplam_alan = 0
    dogru_alan = 0
    hatalar: list[dict] = []
    canli_kayit_sayisi = 0

    for altin in altin_kayitlari_yukle():
        cikti_json = scraper_kaydini_bul(altin)
        if cikti_json is None:
            continue
        canli_kayit_sayisi += 1

        cikarilan = cikarim_fonksiyonu(cikti_json["ham_metin"])

        for extractor_alan, gold_alan in ALAN_ESLEME.items():
            beklenen = altin.get(gold_alan)
            if beklenen is None:
                continue  # altin kayitta bu alan yoksa olcume katma
            toplam_alan += 1
            bulunan = cikarilan.get(extractor_alan)
            if _degerler_esit_mi(beklenen, bulunan):
                dogru_alan += 1
            else:
                hatalar.append(
                    {
                        "kayit_id": altin["kayit_id"],
                        "alan": extractor_alan,
                        "beklenen": beklenen,
                        "bulunan": bulunan,
                    }
                )

    oran = round(dogru_alan / toplam_alan * 100, 2) if toplam_alan else 0.0
    return {
        "accuracy": oran,
        "toplam_alan": toplam_alan,
        "dogru_alan": dogru_alan,
        "canli_kayit_sayisi": canli_kayit_sayisi,
        "hatalar": hatalar,
    }


if __name__ == "__main__":
    sonuc = extraction_accuracy_hesapla()
    print(f"Extraction Accuracy: %{sonuc['accuracy']} ({sonuc['dogru_alan']}/{sonuc['toplam_alan']} alan)")
    print(f"Olcume dahil edilen canli kayit sayisi: {sonuc['canli_kayit_sayisi']}")
    if sonuc["hatalar"]:
        print(f"\nHatalar ({len(sonuc['hatalar'])}):")
        for h in sonuc["hatalar"]:
            print(f"  [{h['kayit_id']}] {h['alan']}: beklenen={h['beklenen']!r} bulunan={h['bulunan']!r}")

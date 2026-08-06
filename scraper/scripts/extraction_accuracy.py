"""Extraction Accuracy olcumu (Zeynep Veri Toplama Rehberi, Sprint 3 Gun 4).

Regex cikarim motorunu (extraction/regex_extractor.py), scraper'in gercek
verisi + Altin Veri Seti referans degerleriyle karsilastirip alan bazli
dogruluk yuzdesi hesaplar.

BAGIMSIZLIK NOTU: Bu olcum Docker/PostgreSQL GEREKTIRMEZ ve aktif olarak
bir sey yapilmasini beklemez - `kaydi_cikar()` saf bir fonksiyondur
(veritabani yok), dogrudan scraper'in urettigi ham_metin uzerinde cagrilir.

Rapor Bolum 13: Extraction Accuracy hedefi >= %95 (henuz gercek veriyle
olculmemis bir hedefti - bu script ilk gercek olcumu yapar).

IKI AYRI METRIK OLCULUR - tek bir "accuracy" sayisi yaniltici olur:

  1. accuracy (dolu alan dogrulugu): Altin Veri Seti'nde DOLU olan
     alanlarda motor dogru degeri buluyor mu? "Kacirma" (recall) hatasini
     olcer.

  2. bos_alan_dogrulugu (yanlis pozitif kontrolu): Kaynakta GERCEKTEN
     OLMAYAN bir alan icin motor deger UYDURUYOR mu? Bu, finansal bir
     uygulamada kacirmaktan DAHA TEHLIKELIDIR (kullanici olmayan bir
     kampanya kosuluna guvenerek karar verebilir).

NEDEN AYRI OLCULMELI: Ilk yazimda yalnizca (1) olculuyordu; gold'da bos
olan alanlar `continue` ile atlaniyordu. Bu, hicbir alani doldurmayan bos
bir motorun bile yuksek "accuracy" almasini engellemiyordu - motor bir
alani uydurdugunda hicbir ceza yoktu. (2) bu acigi kapatir.

BOS ALAN OLCUMUNUN KAPSAMI: Yanlis pozitif yalnizca, altin kayitta
`alan_belirtilmemis[alan] is True` ile ACIKCA "kaynakta belirtilmemis"
diye isaretlenmis alanlarda sayilir. Gold'da bos olup bayraklanMAMIS
alanlar olcum disi tutulur - cunku orada "kaynakta yok" ile "etiketleyici
bu sutunu doldurmadi" ayirt edilemez; ikisini karistirmak motoru haksiz
yere cezalandirirdi. Bu yuzden `bos_alan_olculebilen` degeri, toplam bos
alan sayisindan dusuktur (bkz. altin veri setinde taksit_sayisi /
erteleme_suresi_ay sutunlari hic doldurulmamis).

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
    bos_alan_olculebilen = 0
    yanlis_pozitifler: list[dict] = []

    for altin in altin_kayitlari_yukle():
        cikti_json = scraper_kaydini_bul(altin)
        if cikti_json is None:
            continue
        canli_kayit_sayisi += 1

        cikarilan = cikarim_fonksiyonu(cikti_json["ham_metin"])
        belirtilmemis = altin.get("alan_belirtilmemis") or {}

        for extractor_alan, gold_alan in ALAN_ESLEME.items():
            beklenen = altin.get(gold_alan)
            bulunan = cikarilan.get(extractor_alan)

            if beklenen is None:
                # Altin kayitta bu alan bos. Yalnizca ACIKCA "kaynakta
                # belirtilmemis" diye bayraklanmissa yanlis pozitif olcumune
                # girer (bkz. modul docstring'i, "BOS ALAN OLCUMUNUN KAPSAMI").
                if belirtilmemis.get(gold_alan) is True:
                    bos_alan_olculebilen += 1
                    if bulunan is not None:
                        yanlis_pozitifler.append(
                            {
                                "kayit_id": altin["kayit_id"],
                                "alan": extractor_alan,
                                "uydurulan": bulunan,
                            }
                        )
                continue

            toplam_alan += 1
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
    bos_alan_dogru = bos_alan_olculebilen - len(yanlis_pozitifler)
    bos_oran = (
        round(bos_alan_dogru / bos_alan_olculebilen * 100, 2)
        if bos_alan_olculebilen
        else 0.0
    )

    return {
        "accuracy": oran,
        "toplam_alan": toplam_alan,
        "dogru_alan": dogru_alan,
        "canli_kayit_sayisi": canli_kayit_sayisi,
        "hatalar": hatalar,
        # --- Yanlis pozitif (bos alan) metrigi ---
        "bos_alan_dogrulugu": bos_oran,
        "bos_alan_olculebilen": bos_alan_olculebilen,
        "yanlis_pozitif_sayisi": len(yanlis_pozitifler),
        "yanlis_pozitifler": yanlis_pozitifler,
    }


def ozet_yazdir(sonuc: dict) -> None:
    """Olcum sonucunu iki metrikle birlikte yazdirir (hem bu script hem
    hibrit_extraction_accuracy.py ayni ciktiyi kullanir)."""
    print(
        f"1) Dolu alan dogrulugu : %{sonuc['accuracy']} "
        f"({sonuc['dogru_alan']}/{sonuc['toplam_alan']} alan)"
    )
    print(
        f"2) Bos alan dogrulugu  : %{sonuc['bos_alan_dogrulugu']} "
        f"({sonuc['bos_alan_olculebilen'] - sonuc['yanlis_pozitif_sayisi']}"
        f"/{sonuc['bos_alan_olculebilen']} alan) "
        f"- {sonuc['yanlis_pozitif_sayisi']} yanlis pozitif"
    )
    print(f"Olcume dahil edilen canli kayit sayisi: {sonuc['canli_kayit_sayisi']}")

    if sonuc["hatalar"]:
        print(f"\nDolu alan hatalari - kacirilan/yanlis ({len(sonuc['hatalar'])}):")
        for h in sonuc["hatalar"]:
            print(f"  [{h['kayit_id']}] {h['alan']}: beklenen={h['beklenen']!r} bulunan={h['bulunan']!r}")

    if sonuc["yanlis_pozitifler"]:
        print(
            f"\nYANLIS POZITIF - kaynakta olmayan alana deger uretildi "
            f"({len(sonuc['yanlis_pozitifler'])}):"
        )
        for y in sonuc["yanlis_pozitifler"]:
            print(f"  [{y['kayit_id']}] {y['alan']}: uydurulan={y['uydurulan']!r}")


if __name__ == "__main__":
    ozet_yazdir(extraction_accuracy_hesapla())

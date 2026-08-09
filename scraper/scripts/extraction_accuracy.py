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


# ---------------------------------------------------------------------------
# Alan bazli Precision / Recall / F1
# ---------------------------------------------------------------------------
# NEDEN: Iki toplam metrik ("dolu alan dogrulugu" ve "bos alan dogrulugu")
# sistemin GENEL saglığını gosterir ama HANGI ALANIN zayif oldugunu
# sayiyla soylemez. Sartnamenin en agir kriteri "Model Basarisi ve
# Anlamlandirma Yetenegi" (%30) tam da bunu sorar. Alan kirilimi olmadan
# "kar payi orani mi yoksa odul birimi mi sorunlu?" sorusuna cevap yok.
#
# TANIMLAR (slot-filling standardi):
#   TP  gold'da deger var, motor AYNI degeri buldu
#   FN  gold'da deger var, motor bulamadi (None)
#   FP  gold'da alan "kaynakta belirtilmemis", motor bir deger uydurdu
#   TN  gold'da alan "kaynakta belirtilmemis", motor da bos birakti
#
# YANLIS DEGER HEM FP HEM FN SAYILIR (bilincli karar): gold 1.89 derken
# motor 10.0 bulduysa, hem dogru degeri KACIRMIS (FN) hem de yanlis bir
# deger IDDIA ETMISTIR (FP). Yalnizca FN saymak, finansal bir uygulamada
# daha tehlikeli olan "yanlis deger gosterme" hatasini gizlerdi; yalnizca
# FP saymak ise recall'u oldugundan yuksek gosterirdi.
_SAYAC_ALANLARI = ("dogru", "yanlis_deger", "kacirilan", "uydurulan", "dogru_bos")


def _bos_sayac() -> dict[str, int]:
    return {a: 0 for a in _SAYAC_ALANLARI}


def prf_hesapla(sayac: dict[str, int]) -> dict[str, float | int | None]:
    """Bir alanin sayaclarindan precision/recall/F1 uretir.

    Olculebilir hicbir ornek yoksa (gold sutunu bos) oranlar None doner -
    0.0 dondurmek "motor bu alanda basarisiz" gibi YANLIS bir izlenim
    yaratirdi; dogru ifade "bu alan HENUZ OLCULEMIYOR"dur.
    """
    tp = sayac["dogru"]
    fp = sayac["uydurulan"] + sayac["yanlis_deger"]
    fn = sayac["kacirilan"] + sayac["yanlis_deger"]

    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision and recall
        else (0.0 if precision is not None and recall is not None else None)
    )
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": sayac["dogru_bos"],
        "destek": tp + fn,  # gold'da gercekten deger bulunan ornek sayisi
        "precision": round(precision * 100, 2) if precision is not None else None,
        "recall": round(recall * 100, 2) if recall is not None else None,
        "f1": round(f1 * 100, 2) if f1 is not None else None,
    }


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
    # Alan bazli P/R/F1 AYNI gecişte toplanir - ayri bir fonksiyon olsaydi
    # cikarim iki kez calisirdi ve hibrit olcumde bu, her kayit icin
    # ikinci bir LLM cagrisi demekti (olculdu: cagri basina 150-300 sn).
    sayaclar: dict[str, dict[str, int]] = {a: _bos_sayac() for a in ALAN_ESLEME}
    # Hangi katman kac alan doldurdu ve bunlarin kaci OLCUM DISI kaldi?
    # Ablation icin kritik: bir katmanin F1'e etkisi 0 cikabilir ama bu
    # "hicbir sey yapmadi" demek DEGILDIR - doldurdugu alanlar gold'da
    # etiketlenmemis olabilir, yani katkisi da hatasi da gorunmez olur.
    katman_katkisi: dict[str, dict[str, int]] = {}

    for altin in altin_kayitlari_yukle():
        cikti_json = scraper_kaydini_bul(altin)
        if cikti_json is None:
            continue
        canli_kayit_sayisi += 1

        cikarilan = cikarim_fonksiyonu(cikti_json["ham_metin"])
        belirtilmemis = altin.get("alan_belirtilmemis") or {}
        # Yalnizca hibrit boru hatti doldurur; regex-only fonksiyonda yoktur.
        kaynaklar = cikarilan.get("_kaynaklar") or {}

        for extractor_alan, gold_alan in ALAN_ESLEME.items():
            beklenen = altin.get(gold_alan)
            bulunan = cikarilan.get(extractor_alan)

            # Katman katkisi: bu alan olcume giriyor mu?
            if bulunan is not None and extractor_alan in kaynaklar:
                olculuyor = beklenen is not None or belirtilmemis.get(gold_alan) is True
                katkı = katman_katkisi.setdefault(
                    kaynaklar[extractor_alan], {"toplam": 0, "olcum_disi": 0}
                )
                katkı["toplam"] += 1
                if not olculuyor:
                    katkı["olcum_disi"] += 1

            if beklenen is None:
                # Altin kayitta bu alan bos. Yalnizca ACIKCA "kaynakta
                # belirtilmemis" diye bayraklanmissa yanlis pozitif olcumune
                # girer (bkz. modul docstring'i, "BOS ALAN OLCUMUNUN KAPSAMI").
                if belirtilmemis.get(gold_alan) is True:
                    bos_alan_olculebilen += 1
                    if bulunan is not None:
                        sayaclar[extractor_alan]["uydurulan"] += 1
                        yanlis_pozitifler.append(
                            {
                                "kayit_id": altin["kayit_id"],
                                "alan": extractor_alan,
                                "uydurulan": bulunan,
                            }
                        )
                    else:
                        sayaclar[extractor_alan]["dogru_bos"] += 1
                continue

            toplam_alan += 1
            if _degerler_esit_mi(beklenen, bulunan):
                dogru_alan += 1
                sayaclar[extractor_alan]["dogru"] += 1
            else:
                # Kacirma (None) ile yanlis deger uretme AYRI sayilir -
                # ikincisi hem precision'i hem recall'u dusurur.
                anahtar = "kacirilan" if bulunan is None else "yanlis_deger"
                sayaclar[extractor_alan][anahtar] += 1
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
        # --- Alan bazli P/R/F1 (sartname %30 kriterinin kirilimi) ---
        "alan_bazli": {alan: prf_hesapla(s) for alan, s in sayaclar.items()},
        # Ham sayaclar da doner: P/R/F1'de `fp`, "kaynakta olmayani
        # uydurma" ile "yanlis deger bulma"yi TEK sayida birlestirir ve
        # ikisi geri ayrilamaz. Hangi hata turunun bastigini gormek
        # (ve olcumun kendisini dogrulamak) icin ham dokum korunur.
        "alan_sayaclari": sayaclar,
        # katman -> {"toplam": doldurdugu alan, "olcum_disi": gold'da
        # etiketlenmedigi icin dogrulanamayan alan sayisi}
        "katman_katkisi": katman_katkisi,
    }


def alan_bazli_tablo_yazdir(sonuc: dict) -> None:
    """Alan kirilimli P/R/F1 tablosu - hangi alanin zayif oldugunu gosterir."""
    alan_bazli = sonuc.get("alan_bazli") or {}
    if not alan_bazli:
        return

    print("\n--- Alan bazli Precision / Recall / F1 ---")
    print(
        f"{'alan':<26}{'destek':>7}{'TP':>5}{'FP':>5}{'FN':>5}"
        f"{'P%':>8}{'R%':>8}{'F1%':>8}"
    )
    print("-" * 72)

    olculebilenler = []
    for alan in sorted(alan_bazli, key=lambda a: -(alan_bazli[a]["destek"])):
        m = alan_bazli[alan]
        if m["destek"] == 0 and m["tn"] == 0 and m["fp"] == 0:
            # Gold sutunu hic doldurulmamis - bu alan OLCULEMIYOR.
            print(f"{alan:<26}{'-':>7}{'-':>5}{'-':>5}{'-':>5}{'olculemiyor':>26}")
            continue
        olculebilenler.append(m)
        bicim = lambda d: f"{d:>8.2f}" if d is not None else f"{'-':>8}"  # noqa: E731
        print(
            f"{alan:<26}{m['destek']:>7}{m['tp']:>5}{m['fp']:>5}{m['fn']:>5}"
            f"{bicim(m['precision'])}{bicim(m['recall'])}{bicim(m['f1'])}"
        )

    if olculebilenler:
        # MAKRO ortalama: her alan esit agirlikta. Mikro ortalama buyuk
        # alanlarin (ör. kar_payi_orani) sonucunu one cikarirdi; makro,
        # kucuk ama kritik alanlardaki zayifligi gizlemez.
        for ad, anahtar in (("Makro P", "precision"), ("Makro R", "recall"), ("Makro F1", "f1")):
            degerler = [m[anahtar] for m in olculebilenler if m[anahtar] is not None]
            if degerler:
                print(f"  {ad:<10}: %{sum(degerler) / len(degerler):.2f}  ({len(degerler)} alan)")

    olculemeyen = [a for a, m in alan_bazli.items() if m["destek"] == 0 and m["tn"] == 0 and m["fp"] == 0]
    if olculemeyen:
        print(
            f"\n  OLCULEMEYEN {len(olculemeyen)} alan: {', '.join(sorted(olculemeyen))}\n"
            "  Altin Veri Seti'nde bu sutunlar henuz etiketlenmedi - motorun\n"
            "  basarisiz oldugu ANLAMINA GELMEZ, olcum kapsami disindadir.\n"
            "  Kapatmak icin: python gold_dataset/etiketleme_yardimcisi.py"
        )


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

    alan_bazli_tablo_yazdir(sonuc)

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

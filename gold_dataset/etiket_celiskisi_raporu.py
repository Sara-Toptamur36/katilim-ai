"""Altin Veri Seti ile cikarim motorunun CELISTIGI yerleri raporlar.

NEDEN AYRI BIR RAPOR (scraper/scripts/extraction_accuracy.py varken):
Dogruluk olcumu "kac alan yanlis" sorusunu cevaplar; bu rapor "HANGI
ETIKET tartismali" sorusunu cevaplar. Ikisi ayni sey degildir - bir
celiskinin iki tarafi da hatali OLMAYABILIR: motorun kurali ile
etiketleyicinin kurali farkli olabilir. O durumda duzeltilecek yer kod
degil, ETIKETLEME KURALIDIR.

Somut ornek (23 Agustos 2026 olcumu): korpusta "vade farksiz" gecen 20
kayittan 7'sinde gold `kar_payi_orani = 0`, 13'unde `belirtilmemis`
diyor. Ayni kanit, iki farkli karar. Motor tutarli davraniyor ve
metrikte 13 yanlis pozitif olarak cezalandiriliyor. Bu bir kod hatasi
degil, cozulmemis bir etiketleme kuralidir - ve yalnizca boyle bir
raporla gorunur hale gelir.

Cikti: docs/gold_etiket_inceleme.md (etiketleyen ekibin uzerinde
calisabilecegi liste; her satirda motorun KANIT SPANI var, boylece
kaynak sayfayi acmadan karar verilebilir).

Kullanim:
    python -m gold_dataset.etiket_celiskisi_raporu
"""

from __future__ import annotations

import ortam_yukle  # noqa: F401 - side effect: .env process ortamina yuklenir

import json
import re
from pathlib import Path

from extraction.regex_extractor import kaydi_cikar
from scraper.scripts.gold_eslesme import scraper_kaydini_bul

KOK = Path(__file__).resolve().parent.parent
GOLD = KOK / "gold_dataset" / "altin_veri_seti.json"
CIKTI = KOK / "docs" / "gold_etiket_inceleme.md"

# scraper/scripts/extraction_accuracy.ALAN_ESLEME ile ayni kapsam - iki
# yerde ayri liste tutulursa biri buyuyup digeri geride kalir.
ALAN_ESLEME = {
    "kar_payi_orani_percent": "kar_payi_orani",
    "vade_ay": "vade_ay",
    "odul_miktari": "odul_miktari",
    "odul_birimi": "odul_birimi",
    "finansman_tutari": "finansman_tutari",
    "taksit_sayisi": "taksit_sayisi",
    "erteleme_suresi_ay": "erteleme_suresi_ay",
}

RE_VADE_FARKSIZ = re.compile(r"vade\s*farks[ıi]z", re.IGNORECASE)


def celiskileri_topla() -> dict:
    """Motor ile gold'un ayristigi yerleri gruplara ayirir."""
    gold = json.loads(GOLD.read_text(encoding="utf-8"))

    vade_farksiz_sifir: list[str] = []
    vade_farksiz_bos: list[str] = []
    uydurulan: list[tuple] = []

    for kayit in gold:
        ham = scraper_kaydini_bul(kayit)
        if not ham:
            continue  # kaynak sayfa rotasyona girmis - olcum disi
        metin = ham.get("ham_metin") or ""
        cikti = kaydi_cikar(metin)
        izler = cikti.get("_izler", {})
        belirtilmemis = kayit.get("alan_belirtilmemis") or {}

        if RE_VADE_FARKSIZ.search(metin):
            if kayit.get("kar_payi_orani") == 0:
                vade_farksiz_sifir.append(kayit["kayit_id"])
            elif belirtilmemis.get("kar_payi_orani") is True:
                vade_farksiz_bos.append(kayit["kayit_id"])

        for motor_alan, gold_alan in ALAN_ESLEME.items():
            if belirtilmemis.get(gold_alan) is not True:
                continue
            deger = cikti.get(motor_alan)
            if deger is None:
                continue
            # "vade farksiz" grubu YUKARIDA ayrica ele alindi - burada
            # tekrar listelenirse tablo 13 satirlik gurultuyle dolar.
            if (
                motor_alan == "kar_payi_orani_percent"
                and deger == 0.0
                and RE_VADE_FARKSIZ.search(metin)
            ):
                continue
            span, guven = izler.get(motor_alan, ("?", 0))
            uydurulan.append(
                (kayit["kayit_id"], gold_alan, deger, span[:60].replace("\n", " "), guven)
            )

    return {
        "vade_farksiz_sifir": vade_farksiz_sifir,
        "vade_farksiz_bos": vade_farksiz_bos,
        "uydurulan": sorted(uydurulan),
    }


def _markdown_uret(veri: dict) -> str:
    sifir = veri["vade_farksiz_sifir"]
    bos = veri["vade_farksiz_bos"]
    satirlar = veri["uydurulan"]

    s = [
        "# Altın Veri Seti — Etiket İnceleme Listesi",
        "",
        "*Bu dosya üretilmiştir; elle düzenlemeyin.*",
        "*Yeniden üretmek için: `python -m gold_dataset.etiket_celiskisi_raporu`*",
        "",
        "Bu liste **motorun hatalarını değil**, motor ile altın veri setinin",
        "ÇELİŞTİĞİ yerleri gösterir. Her satırda motorun bulduğu değer ve o değeri",
        "hangi metin parçasından çıkardığı (kanıt spanı) var — böylece kaynak",
        "sayfayı açmadan karar verilebilir. Çelişkilerin bir kısmında **gold**",
        "haklı, bir kısmında **motor**.",
        "",
        "---",
        "",
        "## 1. `vade farksız` — aynı kanıt, iki farklı etiket (EN ÖNCELİKLİ)",
        "",
        "Tek başına en büyük metrik kaldıracı. Korpusta `vade farksız` geçen",
        "kayıtların **{}'inde** gold `kar_payi_orani = 0` diyor,".format(len(sifir)),
        "**{}'ünde** ise `belirtilmemiş` diyor.".format(len(bos)),
        "",
        "**`0` etiketlenmiş ({}):** ".format(len(sifir))
        + ", ".join("`{}`".format(x) for x in sifir),
        "",
        "**`belirtilmemiş` etiketlenmiş ({}):** ".format(len(bos))
        + ", ".join("`{}`".format(x) for x in bos),
        "",
        "**Karar verilmesi gereken:** Katılım bankacılığında *vade farkı*,",
        "geleneksel faizin karşılığıdır; *vade farksız* olması o işlem için oranın",
        "sıfır olduğu anlamına gelir. Motor bu yorumu benimsiyor ve",
        "`terminology/sozluk.json` içindeki `sifir_oran_ifadesi` kavramıyla",
        "tutarlı davranıyor. İki seçenek de savunulabilir — ama **biri seçilip**",
        "**tüm kayıtlara birden** uygulanmalı:",
        "",
        "- **(A) `vade farksız` ⇒ `0`.** İkinci grup ({} kayıt) `0` yapılır.".format(len(bos)),
        "  Beklenen etki: yanlış pozitif {} → ~{}, kâr payı oranı F1".format(
            len(satirlar) + len(bos), len(satirlar)
        ),
        "  belirgin şekilde yükselir.",
        "- **(B) `vade farksız` ⇒ `belirtilmemiş`.** Birinci grup ({} kayıt)".format(len(sifir)),
        "  boşaltılır ve `regex_extractor.py` içindeki `RE_VADE_FARKSIZ` kolu kaldırılır.",
        "",
        "> **Ayrı bir sonucu var:** bir *kart* kampanyasının `kar_payi_orani = 0`",
        "> taşıması, `comparison/compare_engine.py` içindeki `en_dusuk_kar_payi`",
        "> sıralamasını (ASC) kazanmasına yol açıyor — konut finansmanının %1,87'si",
        "> bir taksit kampanyasının 0'ına yeniliyor. Ödül birimleri için zaten var",
        "> olan `odul_birimi_tekil_mi()` korumasının kâr payı ekseninde karşılığı yok.",
        "",
        "---",
        "",
        "## 2. Motorun değer bulduğu, gold'un `belirtilmemiş` dediği alanlar",
        "",
        "**Kanıt spanına bakın:** ifade metinde gerçekten geçiyorsa gold eksik,",
        "geçmiyorsa motor uyduruyor.",
        "",
        "| Kayıt | Alan | Motorun bulduğu | Kanıt spanı | Güven |",
        "|---|---|---|---|---|",
    ]
    for kid, alan, deger, span, guven in satirlar:
        s.append(
            "| `{}` | `{}` | {} | `{}` | {} |".format(kid, alan, deger, span, guven)
        )
    s += [
        "",
        "**Okuma kılavuzu (25 Ağustos 2026'da DÜZELTİLDİ):** ilk sezgi",
        "\"güven 0.85 üstü = gold eksik\" idi - bu satırlar tek tek kaynakla",
        "doğrulandığında YANLIŞ çıktı. Bu korpusta yüksek güven çoğunlukla",
        "motorun BAĞLAM DIŞI bir sayıyı (üst sınır, eşik/tavan, başka bir",
        "kampanyanın başlığı, site menüsü) doğru alanmış gibi bulduğu anlamına",
        "geliyor. Önce kaydın KENDİ `notlar` alanına bakın - konu zaten",
        "`BELİRSİZ <alan>: ...` diye açıklanmışsa gold kasıtlı ve doğrudur,",
        "motora güvenmeyin. Kanıt spanı sayfanın gövdesinde değil bir menü",
        "başlığında/başka kampanyada duruyorsa (ör. \"Kuveyt Türk Kampüs'e",
        "Gelenlere Toplamda 13.500 TL Hediye!\" gibi bir link satırı), bu",
        "scraper'ın içerik sınırlama hatasıdır - alanı DOLDURMAYIN.",
        "",
        "---",
        "",
        "Ölçümün kendisi: `python -m scraper.scripts.extraction_accuracy`",
    ]
    return "\n".join(s) + "\n"


if __name__ == "__main__":
    veri = celiskileri_topla()
    CIKTI.write_text(_markdown_uret(veri), encoding="utf-8")
    print("Yazildi:", CIKTI.relative_to(KOK))
    print(
        "  'vade farksiz' celiskisi : {} adet '0' / {} adet 'belirtilmemis'".format(
            len(veri["vade_farksiz_sifir"]), len(veri["vade_farksiz_bos"])
        )
    )
    print("  diger celiskili alan     : {}".format(len(veri["uydurulan"])))

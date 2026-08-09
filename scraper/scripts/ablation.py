"""Ablation olcumu: her cikarim katmani NE KATIYOR?

Hibrit boru hatti uc katmandan olusuyor (regex -> NER -> LLM) ama
"hibrit %86" gibi tek bir sayi, katmanlarin KENDI katkisini gostermez.
Ust katmanlar tek tek kapatilarak uc varyant ayni Altin Veri Seti'ne
karsi olculur:

    1. regex          - deterministik temel katman
    2. regex + NER    - GLiNER'in bos alanlara katkisi
    3. regex + NER + LLM - Qwen2.5'in kalan bos alanlara katkisi

Tablo, her varyant icin dolu/bos alan dogrulugunu, makro F1'i ve alan
bazli F1 degisimini basar. Boylece "NER gercekten ise yariyor mu?" ve
"LLM'in 150-300 sn'lik maliyeti kendini oduyor mu?" sorulari sayiyla
cevaplanir.

>>> OLLAMA KAPALIYSA UCUNCU VARYANT ANLAMSIZDIR (kritik) <<<
llm_ile_cikar, Ollama'ya erisemedigi zaman HATA FIRLATMAZ - kademeli
fallback ilkesi geregi sessizce None doner (extraction/llm_extractor.py).
Bu, ablation icin tehlikeli bir tuzaktir: tablo "LLM hicbir sey katmadi"
gibi gorunur, oysa LLM hic CALISMAMISTIR. Bu yuzden betik once
servisi kontrol eder ve kapaliysa sonucu ACIKCA gecersiz sayar.

Kullanim:
    ollama serve            # ucuncu varyant icin sart
    python -m scraper.scripts.ablation
    python -m scraper.scripts.ablation --llmsiz   # yalnizca ilk iki varyant
"""

from __future__ import annotations

import argparse
import time

from extraction.hybrid_pipeline import kaydi_hibrit_cikar
from extraction.llm_extractor import _ollama_hazir_mi
from extraction.regex_extractor import kaydi_cikar
from scraper.scripts.extraction_accuracy import extraction_accuracy_hesapla


def _regex_ner(ham_metin: str) -> dict:
    return kaydi_hibrit_cikar(ham_metin, llm_kullan=False)


VARYANTLAR = (
    ("regex", kaydi_cikar, False),
    ("regex+NER", _regex_ner, False),
    ("regex+NER+LLM", kaydi_hibrit_cikar, True),
)


def _makro_f1(sonuc: dict) -> float | None:
    degerler = [
        m["f1"] for m in sonuc["alan_bazli"].values() if m["f1"] is not None
    ]
    return round(sum(degerler) / len(degerler), 2) if degerler else None


def ablation_calistir(llm_dahil: bool = True) -> list[dict]:
    ollama_var = _ollama_hazir_mi()
    sonuclar = []

    for ad, fonksiyon, llm_gerekli in VARYANTLAR:
        if llm_gerekli and not llm_dahil:
            continue
        print(f"  {ad} olculuyor...", flush=True)
        basla = time.monotonic()
        sonuc = extraction_accuracy_hesapla(fonksiyon)
        sonuclar.append(
            {
                "ad": ad,
                "sure_sn": round(time.monotonic() - basla, 1),
                "gecerli": (not llm_gerekli) or ollama_var,
                "sonuc": sonuc,
            }
        )
    return sonuclar


def tablo_yazdir(sonuclar: list[dict]) -> None:
    print("\n=== Ablation: katman katkisi ===\n")
    print(f"{'varyant':<18}{'dolu%':>8}{'bos%':>8}{'makroF1':>18}{'YP':>5}{'sure':>9}")
    print("-" * 66)

    onceki_f1 = None
    for v in sonuclar:
        s = v["sonuc"]
        f1 = _makro_f1(s)
        f1_metin = f"{f1:.2f}" if f1 is not None else "-"
        if onceki_f1 is not None and f1 is not None:
            f1_metin += f" ({f1 - onceki_f1:+.2f})"
        onceki_f1 = f1 if f1 is not None else onceki_f1

        isaret = "" if v["gecerli"] else "  <-- GECERSIZ"
        print(
            f"{v['ad']:<18}{s['accuracy']:>8.2f}{s['bos_alan_dogrulugu']:>8.2f}"
            f"{f1_metin:>18}{s['yanlis_pozitif_sayisi']:>5}{v['sure_sn']:>8.1f}s{isaret}"
        )

    gecersizler = [v["ad"] for v in sonuclar if not v["gecerli"]]
    if gecersizler:
        print(
            f"\n  UYARI - {', '.join(gecersizler)} GECERSIZ: Ollama'ya erisilemiyor.\n"
            "  llm_ile_cikar hata firlatmadan None doner (kademeli fallback),\n"
            "  bu yuzden bu satir aslinda regex+NER sonucudur - 'LLM katki\n"
            "  yapmadi' diye OKUNMAMALIDIR. `ollama serve` ile tekrar calistirin."
        )

    _katman_katkisi_yazdir(sonuclar)
    _alan_bazli_karsilastir(sonuclar)


def _katman_katkisi_yazdir(sonuclar: list[dict]) -> None:
    """F1 farki 0 cikan bir katman gercekten hicbir sey yapmamis olmayabilir.

    Katman, gold'da ETIKETLENMEMIS alanlari doldurmus olabilir - o zaman
    ne katkisi ne hatasi olcume yansir. Bu tablo, "gorunmez" katkiyi
    ayirir; olcum disi orani yuksekse F1 farki YANILTICIDIR.
    """
    ilgili = [
        v for v in sonuclar if v["sonuc"].get("katman_katkisi") and v["gecerli"]
    ]
    if not ilgili:
        return

    print("\n--- Katman katkisi (olculebilirlik kontrolu) ---")
    for v in ilgili:
        katkilar = v["sonuc"]["katman_katkisi"]
        ust_katmanlar = {k: d for k, d in katkilar.items() if k != "regex"}
        if not ust_katmanlar:
            continue
        print(f"  {v['ad']}:")
        for katman, d in sorted(ust_katmanlar.items()):
            gorunur = d["toplam"] - d["olcum_disi"]
            print(
                f"    {katman:<6} {d['toplam']:>3} alan doldurdu  ->  "
                f"{gorunur:>3} olcume girdi, {d['olcum_disi']:>3} OLCUM DISI"
            )
            if d["toplam"] and d["olcum_disi"] == d["toplam"]:
                print(
                    f"           UYARI: {katman} katmaninin TUM katkisi olcum\n"
                    "           disinda. Bu katmanin F1 farkinin 0 olmasi 'katki\n"
                    "           yapmadi' DEGIL, 'dogrulanamiyor' anlamina gelir -\n"
                    "           dogru da olabilir yanlis da. Altin Veri Seti'nde\n"
                    "           ilgili sutunlar etiketlenmeden yorumlanmamali."
                )


def _alan_bazli_karsilastir(sonuclar: list[dict]) -> None:
    """Hangi alanda hangi katman fark yaratti?"""
    gecerliler = [v for v in sonuclar if v["gecerli"]]
    if len(gecerliler) < 2:
        return

    alanlar = sorted(gecerliler[0]["sonuc"]["alan_bazli"])
    print("\n--- Alan bazli F1 (yalnizca gecerli varyantlar) ---")
    baslik = f"{'alan':<26}" + "".join(f"{v['ad']:>16}" for v in gecerliler)
    print(baslik)
    print("-" * len(baslik))

    for alan in alanlar:
        hucreler = []
        for v in gecerliler:
            f1 = v["sonuc"]["alan_bazli"][alan]["f1"]
            hucreler.append(f"{f1:>16.2f}" if f1 is not None else f"{'-':>16}")
        print(f"{alan:<26}" + "".join(hucreler))

    print(
        "\n  '-' = o alan Altin Veri Seti'nde henuz etiketlenmedi (olcum disi),\n"
        "  katmanin basarisiz oldugu anlamina GELMEZ."
    )


def main() -> int:
    ayristirici = argparse.ArgumentParser(description="Cikarim katmani ablation olcumu")
    ayristirici.add_argument(
        "--llmsiz", action="store_true", help="LLM varyantini atla (hizli calistirma)"
    )
    secim = ayristirici.parse_args()

    if not secim.llmsiz and not _ollama_hazir_mi():
        print(
            "UYARI: Ollama calismiyor. Ucuncu varyant olculecek ama sonucu\n"
            "       GECERSIZ isaretlenecek. Yalnizca ilk ikisi icin: --llmsiz\n"
        )

    print("Ablation basliyor (NER modeli ilk cagrida yuklenir)...\n")
    tablo_yazdir(ablation_calistir(llm_dahil=not secim.llmsiz))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

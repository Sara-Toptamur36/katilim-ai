"""Veritabanindaki BAYAT "vade farksiz" sifir oranlarini temizler.

--------------------------------------------------------------------------
NEDEN GEREKLI
--------------------------------------------------------------------------
`gold_dataset/vade_farksiz_duzelt.py` ayni kurali ALTIN SETE uyguladi;
`extraction/regex_extractor.py` RE_VADE_FARKSIZ kuralini motordan kaldirdi
(23 Agustos 2026). Ama VERITABANI ikisinin de disinda kaldi: oradaki
degerler motorun ESKI halinin ciktisi ve kendiliginden tazelenmiyor.

Kendiliginden tazelenmemesinin sebebi olculdu - regex_ile_zenginlestir.py
yalnizca BOS alani doldurur:

    if mevcut_deger is None and yeni_deger is not None:

Motor artik bu kayitlar icin None donuyor, ama sutunda duran eski 0.0
"mevcut deger" oldugu icin dokunulmuyor. Yani betigi kac kere calistirirsan
calistir bayat sifir DB'de kaliyor.

--------------------------------------------------------------------------
BEDELI (Havin'in 24.08.2026 arayuz raporu, Md. 1 ile ayni ekran)
--------------------------------------------------------------------------
`en_dusuk_kar_payi` siralamasi ASC'dir: uydurma 0,0 HER ZAMAN gercek
oranlari yener. Durum hesaplamasi duzeltilip Karsilastirma sayfasi veri
gostermeye basladiginda ilk bes sonucun besi de tek bankadan %0,0 olarak
geldi - juriye gosterilecek Md. 5.7 ekraninin en ust satiri yanlis olurdu.
Zeynep'in gerekcesindeki ayni tuzak: "uydurma 0, gercek konut
finansmaninin %1,87'sini yeniyordu."

--------------------------------------------------------------------------
KURAL KOPYALANMAZ, ICE AKTARILIR
--------------------------------------------------------------------------
Desenler `gold_dataset.vade_farksiz_duzelt`'ten import edilir. Kopyalansaydi
iki taraf zamanla ayrisir ve "gold boyle diyor, DB soyle" celiskisi tam da
bu betigin duzelttigi hatanin yeniden dogmasi olurdu.

Kullanim:
    python -m extraction.vade_farksiz_db_duzelt          # yalnizca rapor
    python -m extraction.vade_farksiz_db_duzelt --yaz    # DB'ye uygula
"""

from __future__ import annotations

import argparse

from api.db import OturumYerel
from api.models import Kampanya
from extraction.regex_ile_zenginlestir import _ham_metinleri_url_ile_esle

# TEK KAYNAK: altin set tarafiyla ayni iki desen. Bkz. modul docstring'i.
from gold_dataset.vade_farksiz_duzelt import RE_ACIK_SIFIR, RE_VADE_FARKSIZ


def etkilenen_satirlar(oturum) -> tuple[list[dict], list[dict]]:
    """(bosaltilacaklar, dokunulmayanlar) - ikisi de gerekceleriyle.

    Yalnizca `kar_payi_orani_percent == 0.0` olan satirlar incelenir;
    sayisal bir oran yazilmis kayitlara hic bakilmaz.
    """
    url_veri = _ham_metinleri_url_ile_esle()
    bosalt: list[dict] = []
    koru: list[dict] = []

    for satir in oturum.query(Kampanya).all():
        if satir.kar_payi_orani_percent != 0.0:
            continue

        veri = url_veri.get(satir.kaynak_url)
        metin = (veri or {}).get("ham_metin") or ""
        ortak = {
            "id": satir.id,
            "banka": satir.banka,
            "kampanya_adi": satir.kampanya_adi,
        }

        if not metin:
            # Kaynak metin yoksa karar verecek kanit da yok. Silmek,
            # dogru olabilecek bir degeri kanitsiz atmak olurdu.
            koru.append({**ortak, "sebep": "kaynak metin yok - elle incelenmeli"})
        elif RE_ACIK_SIFIR.search(metin):
            koru.append({**ortak, "sebep": "metinde acikca 'kar paysiz' / '0 kar payli'"})
        elif RE_VADE_FARKSIZ.search(metin):
            bosalt.append({**ortak, "sebep": "tek kanit 'vade farksiz' - kart taksit ifadesi"})
        else:
            koru.append({**ortak, "sebep": "sifirin kaynagi belirlenemedi - elle incelenmeli"})

    return bosalt, koru


def db_ye_uygula(oturum, bosalt: list[dict]) -> int:
    """Etkilenen satirlarin kar payi oranini BOSALTIR (None yapar).

    `alan_belirtilmemis[...] = True` da yazilir: sema bu bayragi "kaynakta
    belirtilmemis" diye tanimlar (bkz. api/schemas.py), yani deger sessizce
    kaybolmus gibi degil, BILEREK bos birakilmis gibi gorunur - denetim izi
    korunur (rapor Bolum 5.7/15).
    """
    hedefler = {b["id"] for b in bosalt}
    yazilan = 0
    for satir in oturum.query(Kampanya).filter(Kampanya.id.in_(hedefler)).all():
        satir.kar_payi_orani_percent = None
        satir.kar_payi_orani_decimal = None
        bayrak = dict(satir.alan_belirtilmemis or {})
        bayrak["kar_payi_orani_percent"] = True
        satir.alan_belirtilmemis = bayrak
        yazilan += 1
    oturum.commit()
    return yazilan


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--yaz", action="store_true", help="Degisikligi DB'ye uygula")
    secim = a.parse_args()

    oturum = OturumYerel()
    try:
        bosalt, koru = etkilenen_satirlar(oturum)

        print(f"  bosaltilacak : {len(bosalt)}")
        print(f"  dokunulmayan : {len(koru)}")

        if bosalt:
            print("\n  Bosaltilacaklar:")
            for b in bosalt[:20]:
                print(f"    {b['id']:>5}  {b['banka'][:18]:<20}{b['kampanya_adi'][:44]}")
            if len(bosalt) > 20:
                print(f"    ... toplam {len(bosalt)}")

        if koru:
            print("\n  Korunanlar (sebep bazinda):")
            sebepler: dict[str, int] = {}
            for k in koru:
                sebepler[k["sebep"]] = sebepler.get(k["sebep"], 0) + 1
            for s, n in sorted(sebepler.items(), key=lambda x: -x[1]):
                print(f"    {s:<48}{n:>4}")

        if secim.yaz:
            n = db_ye_uygula(oturum, bosalt)
            print(f"\n  {n} satirin kar payi orani bosaltildi.")
        else:
            print("\n  (Uygulamak icin --yaz)")
    finally:
        oturum.close()


if __name__ == "__main__":
    main()

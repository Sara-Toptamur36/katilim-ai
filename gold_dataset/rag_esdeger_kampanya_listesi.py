"""banka_ve_konu sorulari icin ESDEGER KAMPANYA isaretleme listesi uretir.

--------------------------------------------------------------------------
NEDEN GEREKLI (docs/rag_tasarim_ve_olcum.md, Bulgu 14)
--------------------------------------------------------------------------
`banka_ve_konu` sorulari "banka + tur" formatindadir ("Ziraat Katilim
kart") ve kampanya adi tasimaz. O bankanin o turdeki HER kampanyasi
meshru cevaptir, ama `beklenen_sluglar` yalnizca ALTIN SETTE etiketlenmis
olanlari icerir. Olculdu: 28 sorunun gold'da 55 dogru cevabi var,
korpusta esdegeri 344 - kapsama %16. Sonuc olarak bu kategorinin recall'u
retrieval kalitesini degil GOLD KAPSAMASINI olcuyor.

--------------------------------------------------------------------------
DAIRESELLIK NEREDE VE NASIL ONLENDI
--------------------------------------------------------------------------
Ilk surumde aday listesi `kampanya_turu == "Kart Kampanyasi"` ile
suzuluyordu. `kampanya_turu` MAKINE ciktisidir (olculen F1 ~%78) ve bu
suzgec iki farkli hata uretiyordu:

  YANLIS POZITIF - makine yanlislikla "Kart" demis.
      Insan HAYIR isaretleyerek duzeltebiliyordu.  [sorun degildi]

  YANLIS NEGATIF - makine gercek bir kart kampanyasini KACIRMIS.
      O kayit aday listesine HIC GIRMIYORDU, dolayisiyla insan onu
      EVET isaretleyemiyordu bile.  [ASIL DAIRESELLIK]

Yani insan onayi yalnizca BUDAYABILIYOR, EKLEYEMIYORDU: dogru cevap
kumesinin sinirlarini makine ciziyordu. Olculdu (25.08.2026):

    banka                  toplam   makine "Kart" dedi   insanin GORMEDIGI
    Kuveyt Turk               110                   70                  40
    Albaraka Turk              37                    9                  28
    Turkiye Finans             25                   10                  15

Albaraka'da insan 37 kampanyanin yalnizca 9'unu goruyordu.

DUZELTME: aday listesi artik YALNIZCA BANKAYA gore suzuluyor. Banka
olgusal bir bilgidir - kaynak URL'den gelir, hicbir model uretmez.
Tur karari tumuyle insana birakilir; makinenin onerisi ayri bir sutunda
SEFFAF sekilde gosterilir ama hicbir kaydi listeden ELEMEZ.

Bedeli: 293 -> 488 aday. Karsiligi: dogru cevap kumesinin sinirini artik
makine degil insan ciziyor.

--------------------------------------------------------------------------
BU BETIK NE URETIR
--------------------------------------------------------------------------
Her aday kampanya icin, kararin 293 URL acmadan verilebilmesi gereken
bilgiyi toplar:

    soru              hangi soru icin aday
    kampanya_adi      kaynak sayfadaki ad
    sayfa_basligi     sayfanin ilk anlamli satiri (cogu kez tek basina yeter)
    kanit             SAYFA METNINDEN cekilmis, konuyla ilgili cumle(ler)
    makine_onerisi    motorun tur tahmini - YALNIZCA BILGI, suzgec DEGIL
    gold_da_var_mi    zaten dogru cevap listesinde mi
    kaynak_url        supheye dusuldugunde acilacak adres
    DOGRU_CEVAP_MI    <- ELLE DOLDURULACAK TEK SUTUN (EVET / HAYIR)

Kanit, kaydin makine etiketinden BAGIMSIZ olarak sayfa metninden
cikarilir - makinenin "Kart degil" dedigi bir kayitta da kart kaniti
aranir. Amac, makinenin kacirdigini insanin gorebilmesidir.

Kullanim:
    python -m gold_dataset.rag_esdeger_kampanya_listesi
    python -m gold_dataset.rag_esdeger_kampanya_listesi --retrieval  # top5 sutunu da doldur (yavas)
"""

from __future__ import annotations

import ortam_yukle  # noqa: F401 - side effect: .env process ortamina yuklenir

import argparse
import collections
import json
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

CIKTI = KOK / "gold_dataset" / "rag_esdeger_kampanyalar.xlsx"

# Motorun "Kart Kampanyasi" vb. atarken baktigi anahtar kelimeler -
# kanit cumlesini bulmak icin AYNI listeden okunur, kopyalanmaz.
from extraction.regex_extractor import (  # noqa: E402
    KAMPANYA_TURU_ANAHTAR_KELIMELERI,
    turkce_ascii_kucult,
)
from scraper.scripts.rag_degerlendirme import (  # noqa: E402
    _BELIRSIZLIK_ESIGI,
    _TUR_ESLEME,
    _indekste_olan_sluglar,
)


def _ham_metinler() -> dict[str, str]:
    esleme: dict[str, str] = {}
    for dosya in (KOK / "scraper" / "raw_data").glob("*/json/*.json"):
        try:
            kayit = json.loads(dosya.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        url = kayit.get("url")
        metin = kayit.get("ham_metin") or kayit.get("normalize_metin")
        if url and metin:
            esleme[url] = metin
    return esleme


# KANIT ARAMA TERIMLERI - motorun siniflandirma kurallarindan GENIS.
#
# Bilerek boyle: bu terimler karar VERMEZ, insana gosterilecek cumleyi
# BULUR. Motorun kacirdigini insanin gorebilmesi icin motorun kurallarindan
# daha kapsayici olmalari gerekir - dar tutulsaydi, makinenin gormedigini
# insan da goremezdi ve dairesellik baska bir kilikta geri gelirdi.
_KANIT_TERIMLERI = {
    "Kart Kampanyasi": [
        "kredi kart", "banka kart", "bankkart", "kartla", "kart sahip",
        "kartlar", "paraf", "troy", "world", "maximum", "bonus", "axess",
        "chip para", "sanal kart", "temassiz", "pos",
    ],
    "Finansman Kampanyasi": [
        "finansman", "kredi", "vade", "taksit", "kar payi", "odeme plani",
    ],
    "Ihtiyac Finansmani Kampanyasi": [
        "ihtiyac finansman", "ihtiyac kredi", "finansman", "kredi", "vade",
        "kar payi", "tahsis",
    ],
}


def _sayfa_basligi(metin: str) -> str:
    """Sayfanin ilk anlamli satiri - cogu kararda tek basina yeterli."""
    for satir in metin.split(chr(10)):
        sade = " ".join(satir.split())
        if len(sade) >= 12:
            return sade[:110]
    return ""


def _kanit_cumleleri(
    metin: str, tur: str, kalip_satirlar: set[str] | None = None, azami: int = 2
) -> str:
    """Sayfa metninden, sorunun KONUSUYLA ilgili cumleler.

    Kaydin makine etiketine HIC BAKMAZ: motorun "Kart degil" dedigi bir
    sayfada da kart kaniti aranir. Boylece yanlis negatifler insanin
    onune gelir.

    Kanit bulunamamasi da bilgidir - "kanit yok" satiri, o kaydin
    muhtemelen HAYIR oldugunu hizlica gosterir.
    """
    if not metin:
        return "(kaynak metin yok)"

    # SITE KALIBINDAN GELEN KANIT SAYILMAZ.
    # Olculdu: banka menuleri "Kredi Kartlari", "Kar Payi Hesaplama" gibi
    # ifadeler tasiyor ve bunlar HER sayfada geciyor. Menuden alinmis bir
    # cumleyi kanit diye gostermek, insana 100+ satirlik sahte pozitif
    # okutur. Kalip tespiti chunking/parcalayici'den ODUNC ALINIR -
    # kendi kopyasi yazilmaz.
    kalip_satirlar = kalip_satirlar or set()
    satirlar = [
        s_ for s_ in (" ".join(x.split()) for x in metin.split(chr(10)))
        if s_ and s_ not in kalip_satirlar
    ]
    icerik = chr(10).join(satirlar)

    kucuk = turkce_ascii_kucult(icerik)
    bulunanlar: list[str] = []
    gorulen: set[int] = set()

    for terim in _KANIT_TERIMLERI.get(tur, []):
        yer = kucuk.find(turkce_ascii_kucult(terim))
        if yer < 0:
            continue
        # Ayni cumleyi iki terim icin tekrar yazma
        blok = yer // 120
        if blok in gorulen:
            continue
        gorulen.add(blok)
        pencere = icerik[max(0, yer - 60) : yer + 100]
        bulunanlar.append(" ".join(pencere.split()))
        if len(bulunanlar) >= azami:
            break

    return "  ||  ".join(bulunanlar) if bulunanlar else "(konuyla ilgili ifade bulunamadi)"


def adaylari_topla(retrieval: bool = False) -> list[dict]:
    from api.db import OturumYerel
    from api.models import Kampanya

    oturum = OturumYerel()
    try:
        kampanyalar = oturum.query(Kampanya).all()
    finally:
        oturum.close()

    sayim = collections.Counter(
        (k.banka, k.kampanya_turu) for k in kampanyalar if k.kampanya_turu
    )
    bankalar = {b for b, _ in sayim}
    mevcut = _indekste_olan_sluglar()
    metinler = _ham_metinler()

    # Site kalibi (menu/footer) tespiti - parcalayicinin AYNI mantigi.
    from chunking.indeksleyici import ham_kayitlari_yukle
    from chunking.parcalayici import kalip_satirlari_bul

    kaliplar = kalip_satirlari_bul(ham_kayitlari_yukle())

    sorular = json.loads(
        (KOK / "gold_dataset" / "rag_soru_seti.json").read_text(encoding="utf-8")
    )

    satirlar: list[dict] = []
    for soru_kaydi in sorular:
        if soru_kaydi.get("kategori") != "banka_ve_konu":
            continue
        beklenen = [s for s in soru_kaydi["beklenen_sluglar"] if s in mevcut]
        if not beklenen:
            continue

        soru = soru_kaydi["soru"]
        banka = next((b for b in bankalar if soru.startswith(b)), None)
        tur = next(
            (
                v
                for anahtar, v in sorted(_TUR_ESLEME.items(), key=lambda x: -len(x[0]))
                if soru.lower().endswith(anahtar)
            ),
            None,
        )
        if not (banka and tur) or sayim.get((banka, tur), 0) <= _BELIRSIZLIK_ESIGI:
            continue  # zaten olculebilir - elle is gerektirmiyor
        # NOT: yukaridaki esik yalnizca HANGI SORULARIN elle is gerektirdigine
        # karar verir. Asagidaki aday suzgeci makine turunu KULLANMAZ.

        top5: set[str] = set()
        if retrieval:
            from chunking.retriever import getir

            sonuc = getir(soru, limit=5, exact=True)
            top5 = {
                (p.get("ustveri") or {}).get("kaynak_url", "").rstrip("/").split("/")[-1]
                for p in sonuc.parcalar
            }

        # SUZGEC YALNIZCA BANKA: olgusal bilgi, kaynak URL'den gelir.
        # Makine turu ELEME YAPMAZ - yalnizca bir sutunda gosterilir.
        for k in kampanyalar:
            if k.banka != banka:
                continue
            slug = (k.kaynak_url or "").rstrip("/").split("/")[-1]
            metin = metinler.get(k.kaynak_url, "")
            satirlar.append(
                {
                    "soru": soru,
                    "kampanya_adi": k.kampanya_adi,
                    "sayfa_basligi": _sayfa_basligi(metin),
                    "kanit": _kanit_cumleleri(
                        metin, tur, kaliplar.get(k.banka or "", set())
                    ),
                    "makine_onerisi": k.kampanya_turu or "(belirlenemedi)",
                    "gold_da_var_mi": "EVET" if slug in beklenen else "",
                    "retrieval_top5": "EVET" if slug in top5 else "",
                    "kaynak_url": k.kaynak_url,
                    "slug": slug,
                    "DOGRU_CEVAP_MI": "EVET" if slug in beklenen else "",
                }
            )
    return satirlar


def excele_yaz(satirlar: list[dict]) -> None:
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = openpyxl.Workbook()
    sh = wb.active
    sh.title = "Esdeger Kampanyalar"

    basliklar = [
        "soru", "kampanya_adi", "sayfa_basligi", "kanit",
        "makine_onerisi", "gold_da_var_mi", "retrieval_top5",
        "kaynak_url", "slug", "DOGRU_CEVAP_MI",
    ]
    sh.append(basliklar)
    sh.append([
        "hangi soru icin aday",
        "kaynak sayfadaki ad",
        "sayfanin ilk anlamli satiri",
        "SAYFA METNINDEN cekilen kanit (makine etiketinden bagimsiz)",
        "motorun tahmini - BILGI AMACLI, eleme yapmaz",
        "zaten dogru cevap listesinde",
        "sistem su an donduruyor mu",
        "supheye dusunce ac",
        "(otomatik)",
        "<< ELLE DOLDUR: EVET / HAYIR >>",
    ])

    kalin = Font(bold=True)
    sari = PatternFill("solid", fgColor="FFF2CC")
    for hucre in sh[1]:
        hucre.font = kalin
    for hucre in sh[2]:
        hucre.font = Font(italic=True, size=9)
    for satir in (1, 2):
        sh.cell(satir, len(basliklar)).fill = sari

    for s in satirlar:
        sh.append([s[b] for b in basliklar])

    genislik = {"soru": 28, "kampanya_adi": 40, "sayfa_basligi": 46,
                "kanit": 78, "makine_onerisi": 22, "gold_da_var_mi": 13,
                "retrieval_top5": 13, "kaynak_url": 42, "slug": 30,
                "DOGRU_CEVAP_MI": 20}
    for i, b in enumerate(basliklar, start=1):
        sh.column_dimensions[sh.cell(1, i).column_letter].width = genislik[b]
    for satir in sh.iter_rows(min_row=3):
        satir[2].alignment = Alignment(wrap_text=True, vertical="top")
        satir[3].alignment = Alignment(wrap_text=True, vertical="top")

    sh.freeze_panes = "A3"
    wb.save(CIKTI)


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument(
        "--retrieval",
        action="store_true",
        help="retrieval_top5 sutununu da doldur (gomme modeli yuklenir, yavas)",
    )
    secim = a.parse_args()

    satirlar = adaylari_topla(retrieval=secim.retrieval)
    excele_yaz(satirlar)

    sorulara_gore = collections.Counter(s["soru"] for s in satirlar)
    zaten = sum(1 for s in satirlar if s["gold_da_var_mi"] == "EVET")

    kanitli = sum(1 for x in satirlar if not x["kanit"].startswith("("))
    makine_disi = sum(
        1 for x in satirlar
        if x["makine_onerisi"] not in ("Kart Kampanyasi", "Finansman Kampanyasi",
                                       "Ihtiyac Finansmani Kampanyasi")
    )
    print(f"  {CIKTI.name} yazildi")
    print(f"  toplam aday      : {len(satirlar)}")
    print(f"  kaniti olan      : {kanitli}  (digerlerinde konuyla ilgili ifade yok)")
    print(f"  makinenin ELEDIGI: {makine_disi}  <- eski listede HIC gorunmuyorlardi")
    print(f"  zaten gold'da    : {zaten} (satirlari onceden EVET isaretli)")
    print(f"  karar bekleyen   : {len(satirlar) - zaten}")
    print()
    print("  Soru bazinda:")
    for soru, n in sorulara_gore.most_common():
        print(f"    {soru[:36]:<38}{n:>5} aday")
    print()
    print("  Doldurduktan sonra:")
    print("    python -m gold_dataset.rag_soru_seti_guncelle")


if __name__ == "__main__":
    main()

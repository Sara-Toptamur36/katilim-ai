"""Etiketteki tarih ile BUGUNKU kaynak metnin cakismadigi kayitlari bulur.

--------------------------------------------------------------------------
NE YAPAR, NE YAPMAZ
--------------------------------------------------------------------------
YAPAR: altin setteki dolu bir tarih alanini alir, kaynagin bugunku ham
metninde o tarihin gorunup gorunmedigine bakar. Gorunmuyorsa metindeki
tarih ifadelerini CUMLESIYLE birlikte onune koyar.

YAPMAZ: hicbir hucreyi degistirmez, Excel'e yazmaz, kimseyi imzalamaz.
Uretilen "aday" bir ONERIDIR - kaynak cumle okunmadan Excel'e gecirilirse
Kural 4 ("deger sayfadan gelir") cignenmis olur.

--------------------------------------------------------------------------
NEDEN GEREKLI
--------------------------------------------------------------------------
Etiketler 28 Temmuz 2026'da girildi; korpus 1-22 Agustos arasinda
tazelendi. Kampanyalar bu arada rotasyona girdi. Olculen durum: kanit
spani uretilemeyen 32 alanin 29'u tarih ve hepsinin sebebi ayni - etiket
YANLIS DEGIL, dayandigi metin artik korpusta yok.

Bunun iki bedeli var:
  1. Cikarim motoru bugunku metinden "Agustos" cikarir, altin set
     "Temmuz" der, olcum bunu HATA sayar - motor kendi suclu olmadigi bir
     hatayi tasir.
  2. O kayitlarda kanit spani uretmek imkansizdir.

--------------------------------------------------------------------------
KULLANIM
--------------------------------------------------------------------------
    python gold_dataset/tarih_celiskisi_raporu.py
    python gold_dataset/tarih_celiskisi_raporu.py --kayit TEK-004 TF-003

Cikti bir KARAR TABLOSUDUR: her satirda etiketteki deger, kaynaktaki
cumle ve aday deger yan yana durur. Karar okuyanindir.
"""

from __future__ import annotations

import ortam_yukle  # noqa: F401 - side effect: .env process ortamina yuklenir

import argparse
import json
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

GOLD = KOK / "gold_dataset" / "altin_veri_seti.json"

TARIH_ALANLARI = ("kampanya_baslangic", "kampanya_bitis")


def _ay_kaliplari() -> tuple[str, dict[str, int]]:
    """Ay adi kalibi ve ay -> NUMARA eslemesi.

    TUZAK (bir kez dusuldu): TR_AY_ADLARI 12 degil 18 elemanlidir - Turkce
    karakterli ve karaktersiz yazimlar ayri ayri durur ("ağustos" ve
    "agustos"). enumerate() ile sira numarasi vermek Agustos'u 10. ay
    yapiyordu ve rapor "1 Agustos" cumlesinden 2026-10-01 uretiyordu.
    Numara daima normalizer'in kendi sozlugunden okunur."""
    from extraction.normalizer import _TR_AYLAR, TR_AY_ADLARI

    return "|".join(TR_AY_ADLARI), dict(_TR_AYLAR)


def _aralik_kaliplari() -> list[tuple[str, re.Pattern[str]]]:
    """Aralik ifadeleri - excel_to_json._tarih_izi bunlari tek tarih olarak
    gorur, oysa kampanya donemi cogunlukla aralik olarak yazilir."""
    ay, _ = _ay_kaliplari()
    return [
        # "1-31 Ağustos 2026"
        ("gun-gun ay yil", re.compile(
            rf"(\d{{1,2}})\s*[-–]\s*(\d{{1,2}})\s+({ay})\s+(\d{{4}})", re.IGNORECASE)),
        # "01 Ağustos - 31 Ağustos 2026" / "16 Haziran - 31 Ağustos 2026"
        ("gun ay - gun ay yil", re.compile(
            rf"(\d{{1,2}})\s+({ay})\s*[-–]\s*(\d{{1,2}})\s+({ay})\s*(\d{{4}})",
            re.IGNORECASE)),
        # "13.08.2024 - 1.01.2027"
        ("tam - tam", re.compile(
            r"(\d{1,2})[-./](\d{1,2})[-./](\d{4})\s*[-–]\s*"
            r"(\d{1,2})[-./](\d{1,2})[-./](\d{4})")),
    ]


def _iso(gun: int, ay: int, yil: int) -> str:
    return f"{yil:04d}-{ay:02d}-{gun:02d}"


def _araliklari_cikar(metin: str) -> list[dict]:
    """Metindeki tarih ARALIKLARINI (baslangic, bitis) cumlesiyle dondurur."""
    from gold_dataset.excel_to_json import _CEREZ_BAGLAMI

    _, ay_no = _ay_kaliplari()

    bulunanlar: list[dict] = []
    for etiket, kalip in _aralik_kaliplari():
        for m in kalip.finditer(metin):
            cevre = metin[max(0, m.start() - 220):m.end() + 220]
            if _CEREZ_BAGLAMI.search(cevre):
                continue  # cerez/gizlilik metnindeki tarih kampanya tarihi degil

            g = m.groups()
            try:
                if etiket == "gun-gun ay yil":
                    ay = ay_no[g[2].lower()]
                    bas, bit = _iso(int(g[0]), ay, int(g[3])), _iso(int(g[1]), ay, int(g[3]))
                elif etiket == "gun ay - gun ay yil":
                    yil = int(g[4])
                    bas = _iso(int(g[0]), ay_no[g[1].lower()], yil)
                    bit = _iso(int(g[2]), ay_no[g[3].lower()], yil)
                else:
                    bas = _iso(int(g[0]), int(g[1]), int(g[2]))
                    bit = _iso(int(g[3]), int(g[4]), int(g[5]))
            except (KeyError, ValueError):
                continue  # ay adi taninmadi ya da sayi bozuk - sessizce atlamak
                          # yerine bu aday hic uretilmez, insan cumleyi gorur

            bulunanlar.append({
                "ifade": " ".join(m.group(0).split()),
                "baslangic": bas,
                "bitis": bit,
                "cumle": _cumleyi_bul(metin, m.group(0)),
            })
    return bulunanlar


def _cumleyi_bul(metin: str, ifade: str) -> str:
    for satir in metin.split("\n"):
        if ifade in satir:
            return " ".join(satir.split())[:200]
    return ""


def celiskileri_bul(kayit_suzgeci: set[str] | None = None) -> list[dict]:
    from gold_dataset.excel_to_json import span_metinde_var
    from gold_dataset.kanit_spani_oner import _tarih_bicimleri
    from gold_dataset.sprint_is_listesi import _ham_kampanyalar, _slug

    ham = _ham_kampanyalar()
    with open(GOLD, encoding="utf-8") as f:
        kayitlar = json.load(f)

    celiskiler: list[dict] = []
    for k in kayitlar:
        if k.get("giren_kisi") == "ORNEK":
            continue
        if kayit_suzgeci and k["kayit_id"] not in kayit_suzgeci:
            continue

        kaynak = ham.get(_slug(k.get("kaynak_url") or ""))
        if not kaynak:
            continue  # kaynagi kaybolmus kayit - karsilastiracak metin yok
        metin = kaynak.get("normalize_metin") or ""

        eksikler = []
        for alan in TARIH_ALANLARI:
            deger = k.get(alan)
            if not deger:
                continue
            # kanit_spani_oner._adaylar KULLANILMAZ: o, span olarak
            # gosterilebilecek makul uzunlukta bir SATIR arar (12-200
            # karakter). Buradaki soru farkli - "bu tarih metinde geciyor
            # mu". TEK-012'nin etiketi dogruydu ama tarihi tasiyan satir
            # 200 karakteri astigi icin celiski sanilmisti.
            #
            # Karsilastirma span_metinde_var uzerinden yapilir: duz `in`
            # kullanildiginda HF-008 celiski gorunuyordu, oysa etiketi
            # dogruydu - kaynaktaki "2 Temmuz" kirilmaz bosluk (U+00A0)
            # tasiyordu.
            if not any(span_metinde_var(b, metin)
                       for b in _tarih_bicimleri(str(deger))):
                eksikler.append((alan, deger))
        if not eksikler:
            continue

        celiskiler.append({
            "kayit_id": k["kayit_id"],
            "banka": k.get("banka"),
            "giris_tarihi": k.get("giris_tarihi"),
            "snapshot": (kaynak.get("erisim_zamani") or "?")[:10],
            "etiket": {"kampanya_baslangic": k.get("kampanya_baslangic"),
                       "kampanya_bitis": k.get("kampanya_bitis")},
            "kaynakta_bulunamayan": eksikler,
            "kaynaktaki_araliklar": _araliklari_cikar(metin),
            "kaynak_url": k.get("kaynak_url"),
        })
    return celiskiler


def _yazdir(celiskiler: list[dict]) -> None:
    netler = [c for c in celiskiler if c["kaynaktaki_araliklar"]]
    belirsizler = [c for c in celiskiler if not c["kaynaktaki_araliklar"]]

    print(f"\nEtiketi bugunku kaynakta bulunamayan kayit: {len(celiskiler)}")
    print(f"  kaynakta net tarih araligi VAR : {len(netler)}  -> asagida aday duruyor")
    print(f"  kaynakta net aralik YOK        : {len(belirsizler)}  -> sayfaya bakmak gerek")

    if netler:
        print("\n" + "=" * 78)
        print("A) KAYNAKTA NET ARALIK VAR - cumleyi okuyup karar verin")
        print("=" * 78)
        for c in netler:
            print(f"\n  {c['kayit_id']}  ({c['banka']})")
            print(f"    etiket    : {c['etiket']['kampanya_baslangic']} .. "
                  f"{c['etiket']['kampanya_bitis']}   "
                  f"(girildi {c['giris_tarihi']}, metin {c['snapshot']} tarihli)")
            print("    bulunamayan: " + ", ".join(f"{a}={d}" for a, d in
                                                  c["kaynakta_bulunamayan"]))
            for aralik in c["kaynaktaki_araliklar"][:3]:
                print(f"    ADAY      : {aralik['baslangic']} .. {aralik['bitis']}")
                print(f"      kaynak  : \"{aralik['cumle']}\"")

    if belirsizler:
        print("\n" + "=" * 78)
        print("B) KAYNAKTA NET ARALIK YOK - sayfayi acip bakmak gerekiyor")
        print("=" * 78)
        for c in belirsizler:
            print(f"  {c['kayit_id']:<9} {c['banka']:<22} "
                  f"etiket {c['etiket']['kampanya_baslangic']} .. "
                  f"{c['etiket']['kampanya_bitis']}")
            print(f"            {c['kaynak_url']}")

    print("\n" + "-" * 78)
    print("ADAY bir ONERIDIR. Excel'e gecirmeden once kaynak cumleyi okuyun;")
    print("degeri gordugunuze ikna olmadan giren_kisi sutununu imzalamayin.")


def main() -> None:
    a = argparse.ArgumentParser(
        description="Etiket tarihi ile bugunku kaynagi karsilastirir (yazmaz)")
    a.add_argument("--kayit", nargs="*", help="Yalnizca bu kayitlari incele")
    s = a.parse_args()

    celiskiler = celiskileri_bul(set(s.kayit) if s.kayit else None)
    _yazdir(celiskiler)


if __name__ == "__main__":
    main()

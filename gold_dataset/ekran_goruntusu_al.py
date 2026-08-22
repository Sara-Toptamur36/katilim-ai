"""Altin veri setindeki kayitlarin kaynak sayfalarinin ekran goruntusunu alir.

--------------------------------------------------------------------------
NE ISE YARAR
--------------------------------------------------------------------------
Altin veri setinde her kaydin yaninda, o kaydin cikarildigi sayfanin
ekran goruntusu durur (`gold_dataset/ekran_goruntuleri/<kayit_id>.png`).
Bir deger tartismali oldugunda bakilacak yer orasidir.

Bu betik, ekran goruntusu EKSIK olan kayitlar icin sayfayi acar ve
goruntuyu kaydeder.

--------------------------------------------------------------------------
EKRAN GORUNTUSU "INSAN DOGRULAMASI" DEGILDIR
--------------------------------------------------------------------------
Bu betigin urettigi dosya yalnizca KANITTIR: "etiketleme aninda sayfa
boyle goruyordu" der. Etiketin DOGRU oldugunu soylemez.

Altin veri setinde bir kaydin dogrulanmis sayilmasi icin bir kisinin
goruntuyle etiketi karsilastirmasi ve `giren_kisi` alanini doldurmasi
gerekir. Bu betik `giren_kisi` alanina DOKUNMAZ ve notlardaki
"TASLAK - insan dogrulamasi ... BEKLIYOR" ibaresini KALDIRMAZ.

--------------------------------------------------------------------------
SAYFA DEGISMIS OLABILIR - OLCULUR VE RAPORLANIR
--------------------------------------------------------------------------
Kampanya sayfalari doner. Bugun alinan goruntu, etiketin cikarildigi
metinle ayni olmayabilir; oyleyse goruntu o etiketi DESTEKLEMEZ ve bunu
bilmek sarttir.

Bu yuzden her sayfa icin canli metin, `scraper/raw_data` altindaki
anlik goruntuyle karsilastirilir ve benzerlik oranı rapora yazilir.
Esigin altinda kalanlar "DEGISMIS" olarak isaretlenir - goruntu yine de
kaydedilir (sayfanin bugunku hali de bir bilgidir) ama kayit insan
kontrolune ayrica cikarilir.

Kullanim:
    python gold_dataset/ekran_goruntusu_al.py            # eksikleri al
    python gold_dataset/ekran_goruntusu_al.py --kayit ZK-017 KT-012
    python gold_dataset/ekran_goruntusu_al.py --yeniden  # varsa da yeniden al
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
import time
from datetime import date
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

GOLD = KOK / "gold_dataset" / "altin_veri_seti.json"
GORUNTU_DIZIN = KOK / "gold_dataset" / "ekran_goruntuleri"
RAPOR = KOK / "gold_dataset" / "ekran_goruntusu_raporu.json"

# ------------------------------------------------------------------
# SIMETRIK BENZERLIK YANLIS ARAC - OLCULDU
# ------------------------------------------------------------------
# Ilk surum canli metinle anlik goruntuyu simetrik oranla karsilastirdi
# ve ZK-017 (BAUHAUS) icin %71 verip "DEGISMIS" dedi. Sayfa DEGISMEMISTI:
# canli sayfa anlik goruntude HIC OLMAYAN bir blok tasiyor -
# "Kampanya Donemi / 01-04-2025 - 31-08-2026". Scraper o bolgeyi
# yakalamamis. Simetrik oran, "sayfa degisti" ile "anlik goruntu eksik"
# durumlarini AYNI sayiya indiriyor ve ikisi cok farkli sonuclar dogurur.
#
# Dogru soru: ETIKETIN CIKARILDIGI METIN hala sayfada duruyor mu?
# Bu bir KAPSANMA olcusudur - anlik goruntunun ne kadari canli metinde
# bulunuyor. Canli sayfanin fazladan icerik tasimasi kapsanmayi
# DUSURMEZ; eksiltmesi dusurur.
KAPSANMA_ESIGI = 0.90

# Canli metin anlik goruntuden bu kat daha uzunsa, anlik goruntu
# muhtemelen EKSIK yakalanmis demektir (yukaridaki ZK-017 ornegi).
# Etiket eksik metinden cikarildiysa "kaynakta yok" denen bir alan
# aslinda sayfada olabilir - bu, olculen alanlarda dogrudan hatadir.
EKSIK_YAKALAMA_KATI = 1.5

# Bankalar arasi nezaket beklemesi (saniye). Ard arda onlarca istek
# atmak hem kaba hem de engellenmeye davetiye.
# Ilk kosuda 42 sayfanin 18'i zaman asimina dustu: 2 saniyelik araliklarla
# ard arda istek atinca bankalarin on bellekleri/WAF'lari yavaslatiyor.
# Daha uzun bekleme + daha uzun zaman asimi ile hepsi aliniyor.
BEKLEME = 5.0

VIEWPORT = {"width": 1280, "height": 900}


def _url_duzelt(ham: str) -> str:
    """Altin sette adresler sema olmadan duruyor ('www.banka.com.tr/...')."""
    ham = (ham or "").strip()
    if not ham:
        return ""
    return ham if ham.startswith(("http://", "https://")) else "https://" + ham


def _anlik_goruntu_metni(kaynak_url: str) -> str | None:
    """Kaydin scraper anlik goruntusundeki metni (varsa)."""
    from gold_dataset.sprint_is_listesi import _ham_kampanyalar, _slug

    ham = _ham_kampanyalar()
    kayit = ham.get(_slug(kaynak_url))
    return (kayit or {}).get("normalize_metin")


def _hedef_kayitlar(kayitlar: list[dict], istenen: list[str] | None,
                    yeniden: bool) -> list[dict]:
    secilen = []
    for k in kayitlar:
        if k["kayit_id"].startswith(("A-", "B-", "C-", "D-")):
            continue  # ornek satirlar - gercek kampanya degil
        if istenen and k["kayit_id"] not in istenen:
            continue
        if not k.get("kaynak_url"):
            continue
        if not yeniden and (GORUNTU_DIZIN / f"{k['kayit_id']}.png").exists():
            continue
        secilen.append(k)
    return secilen


def _kiyasla(anlik: str, canli: str) -> dict:
    """Anlik goruntu metninin ne kadari canli sayfada duruyor?

    Eslesen bloklarin toplam uzunlugu / anlik goruntu uzunlugu. 1.0'a
    yakin deger "etiketin dayandigi metin hala orada" demektir.
    """
    olcer = difflib.SequenceMatcher(None, anlik, canli, autojunk=False)
    eslesen = sum(b.size for b in olcer.get_matching_blocks())
    kapsanma = eslesen / len(anlik) if anlik else 0.0
    sonuc = {
        "kapsanma": round(kapsanma, 3),
        "anlik_uzunluk": len(anlik),
        "canli_uzunluk": len(canli),
        "durum": "tamam" if kapsanma >= KAPSANMA_ESIGI else "DEGISMIS",
    }
    if anlik and len(canli) >= len(anlik) * EKSIK_YAKALAMA_KATI:
        sonuc["anlik_goruntu_eksik"] = True
    return sonuc


def _tarayici_ac(p):
    """Chromium'u acar.

    Playwright 1.62'de varsayilan headless motoru AYRI bir paket
    ("chromium_headless_shell"); yalnizca `playwright install chromium`
    calistirilmis makinelerde o paket bulunmaz ve varsayilan cagri
    "Executable doesn't exist" hatasi verir. Tam Chromium ise kurulmustur
    ve headless calisir - bu yuzden once o denenir.
    """
    try:
        return p.chromium.launch(headless=True, channel="chromium")
    except Exception:  # noqa: BLE001 - kanal yoksa varsayilana dus
        return p.chromium.launch(headless=True)


def goruntuleri_al(kayitlar: list[dict]) -> list[dict]:
    from playwright.sync_api import sync_playwright

    from scraper.scripts.js_scraper import popuplari_kapat, sayfa_metnini_al

    GORUNTU_DIZIN.mkdir(parents=True, exist_ok=True)
    sonuclar: list[dict] = []

    with sync_playwright() as p:
        tarayici = _tarayici_ac(p)
        baglam = tarayici.new_context(viewport=VIEWPORT)
        try:
            for sira, kayit in enumerate(kayitlar, 1):
                kid = kayit["kayit_id"]
                url = _url_duzelt(kayit["kaynak_url"])
                hedef = GORUNTU_DIZIN / f"{kid}.png"
                satir = {"kayit_id": kid, "banka": kayit.get("banka"), "url": url}
                print(f"  [{sira:>3}/{len(kayitlar)}] {kid:<8} {url[:64]}")

                sayfa = baglam.new_page()
                try:
                    sayfa.goto(url, timeout=60000, wait_until="domcontentloaded")
                    # Cerez penceresi: js_scraper'in kendi seciciler listesi
                    # yalnizca REDDET/KAPAT dugmelerini hedefler - hicbir
                    # sey KABUL EDILMEZ.
                    popuplari_kapat(sayfa)
                    try:
                        sayfa.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:  # noqa: BLE001 - surekli istek atan sayfa
                        pass
                    sayfa.wait_for_timeout(800)

                    sayfa.screenshot(path=str(hedef), full_page=True)
                    satir["dosya"] = hedef.name
                    satir["boyut_kb"] = round(hedef.stat().st_size / 1024, 1)

                    canli = sayfa_metnini_al(sayfa)
                    anlik = _anlik_goruntu_metni(kayit["kaynak_url"])
                    if anlik:
                        satir.update(_kiyasla(anlik, canli))
                    else:
                        # Anlik goruntu yoksa karsilastirilacak sey de yok.
                        satir["kapsanma"] = None
                        satir["durum"] = "karsilastirilamadi"
                except Exception as hata:  # noqa: BLE001 - tek sayfa patlarsa digerleri devam etsin
                    satir["durum"] = "HATA"
                    satir["hata"] = f"{type(hata).__name__}: {str(hata)[:160]}"
                    print(f"           HATA: {satir['hata']}")
                finally:
                    sayfa.close()

                sonuclar.append(satir)
                if sira < len(kayitlar):
                    time.sleep(BEKLEME)
        finally:
            baglam.close()
            tarayici.close()
    return sonuclar


def main() -> None:
    a = argparse.ArgumentParser(description="Altin kayitlarin ekran goruntusunu alir")
    a.add_argument("--kayit", nargs="*", help="Yalnizca bu kayit_id'ler")
    a.add_argument("--yeniden", action="store_true", help="Mevcut goruntuyu da yenile")
    s = a.parse_args()

    with open(GOLD, encoding="utf-8") as f:
        kayitlar = json.load(f)
    hedefler = _hedef_kayitlar(kayitlar, s.kayit, s.yeniden)
    if not hedefler:
        print("Alinacak ekran goruntusu yok.")
        return

    print(f"{len(hedefler)} kayit icin ekran goruntusu alinacak.\n")
    sonuclar = goruntuleri_al(hedefler)

    sayim: dict[str, int] = {}
    for r in sonuclar:
        sayim[r["durum"]] = sayim.get(r["durum"], 0) + 1

    print("\n" + "=" * 66)
    print("  SONUC")
    print("=" * 66)
    for durum, n in sorted(sayim.items()):
        print(f"  {durum:<22}{n:>4}")

    degismis = [r for r in sonuclar if r["durum"] == "DEGISMIS"]
    if degismis:
        print(f"\n  DEGISMIS SAYFALAR ({len(degismis)}) - goruntu KAYDEDILDI ama")
        print("  etiketin cikarildigi metnin bir kismi artik sayfada YOK.")
        print("  Etiket bu goruntuyle DOGRULANAMAZ; kayit tekrar okunmali:")
        for r in degismis:
            print(f"    {r['kayit_id']:<8} kapsanma %{r['kapsanma'] * 100:.0f}"
                  f"  {r['url'][:52]}")

    eksik = [r for r in sonuclar if r.get("anlik_goruntu_eksik")]
    if eksik:
        print(f"\n  ANLIK GORUNTU EKSIK ({len(eksik)}) - sayfa DEGISMEDI, taramada")
        print("  eksik yakalanmis. Etiket eksik metinden cikarildigi icin")
        print("  'kaynakta yok' denen alanlar SAYFADA OLABILIR:")
        for r in eksik:
            print(f"    {r['kayit_id']:<8} anlik {r['anlik_uzunluk']:>5} krk ->"
                  f" canli {r['canli_uzunluk']:>5} krk   {r['url'][:44]}")

    hatalar = [r for r in sonuclar if r["durum"] == "HATA"]
    if hatalar:
        print(f"\n  ALINAMAYAN ({len(hatalar)}):")
        for r in hatalar:
            print(f"    {r['kayit_id']:<8} {r.get('hata', '')[:70]}")

    with open(RAPOR, "w", encoding="utf-8") as f:
        json.dump({"tarih": date.today().isoformat(),
                   "kapsanma_esigi": KAPSANMA_ESIGI,
                   "sonuclar": sonuclar}, f, ensure_ascii=False, indent=2)
    print(f"\n  Rapor: {RAPOR.relative_to(KOK)}")
    print("  NOT: ekran goruntusu KANITTIR, insan dogrulamasi DEGILDIR -")
    print("  kayitlarin 'giren_kisi' alani ve TASLAK ibaresi degistirilmedi.")


if __name__ == "__main__":
    main()

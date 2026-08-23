"""Altin kayitlarin kaynak sayfalarini JS ile YENIDEN tarar.

--------------------------------------------------------------------------
NEDEN GEREKTI - OLCULEN HATA
--------------------------------------------------------------------------
Altin kayitlarin bir kismi STATIK tarayiciyla cekilmis anlik goruntulerden
etiketlendi (`sayfa_turu: "HTML"`). O sayfalarin bir bolumu JS ile
geliyor ve statik tarayici goremiyor:

  ZK-017 (BAUHAUS): anlik goruntu 997 karakter, canli sayfa 1.775.
  Anlik goruntude OLMAYAN blok: "Kampanya Donemi / 01-04-2025 - 31-08-2026"

Kayit bu eksik metinden etiketlendigi icin `kampanya_baslangic` ve
`kampanya_bitis` bos birakildi ve nota "Kampanya tarihi sayfada YOK"
yazildi. Ikisi de YANLIS - tarih sayfada duruyordu.

Bu, olculen alanlarda dogrudan hatadir: "kaynakta belirtilmemis" diye
isaretlenen bir alan yanlis pozitif olcumune girer ve motor, aslinda
DOGRU buldugu bir degerden ceza yer.

--------------------------------------------------------------------------
NEDEN js_scraper.js_sayfa_tara DOGRUDAN KULLANILMIYOR
--------------------------------------------------------------------------
O fonksiyon kaydi `banka: <banka_kodu>` ("kuveytturk") ile yaziyor, oysa
korpustaki kayitlarda `banka` GORUNEN ADDIR ("Kuveyt Türk"); ayrica
`normalize_metin` uretmiyor. Dogrudan cagirmak korpusun seklini bozar -
kumeleme ve is listesi banka adina gore gruplar. Bu yuzden sayfa burada
cekilir ama kayit, MEVCUT kaydin alanlari korunarak yazilir.

Kullanim:
    python gold_dataset/kaynak_tazele.py                 # TASLAK kayitlar
    python gold_dataset/kaynak_tazele.py --kayit ZK-017
    python gold_dataset/kaynak_tazele.py --hepsi         # tum gercek kayitlar
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

GOLD = KOK / "gold_dataset" / "altin_veri_seti.json"
HAM_DIZIN = KOK / "scraper" / "raw_data"
RAPOR = KOK / "gold_dataset" / "kaynak_tazeleme_raporu.json"

BEKLEME = 5.0
VIEWPORT = {"width": 1280, "height": 1400}


def _slug(url: str) -> str:
    return (url or "").rstrip("/").split("/")[-1]


def _mevcut_kayitlar() -> dict[str, tuple[Path, dict]]:
    """slug -> (dosya yolu, EN GUNCEL ham kayit)."""
    sonuc: dict[str, tuple[Path, dict]] = {}
    for yol in glob.glob(str(HAM_DIZIN / "*" / "json" / "*.json")):
        try:
            with open(yol, encoding="utf-8") as f:
                kayit = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        sl = _slug(kayit.get("url"))
        if not sl:
            continue
        onceki = sonuc.get(sl)
        if onceki is None or (kayit.get("erisim_zamani") or "") > (
            onceki[1].get("erisim_zamani") or ""
        ):
            sonuc[sl] = (Path(yol), kayit)
    return sonuc


def _url_duzelt(ham: str) -> str:
    ham = (ham or "").strip()
    return ham if ham.startswith(("http://", "https://")) else "https://" + ham


def _yeni_dosya_yolu(eski_yol: Path) -> Path:
    """Ayni klasore, BUGUNUN tarihiyle yeni bir dosya adi.

    Eski dosya SILINMEZ: kampanya sayfalarinin tarihcesi (scraper/scripts/
    kampanya_tarihcesi.py) eski anlik goruntulere dayanir ve etiketin
    hangi metinden cikarildigini geriye donuk gormek gerekebilir.
    """
    ad = eski_yol.name
    _, kalan = ad.split("_", 1)
    return eski_yol.parent / f"{datetime.now().strftime('%Y%m%d')}_{kalan}"


def _kimlik_kelimeleri(metin: str) -> set[str]:
    from extraction.normalizer import turkce_ascii_kucult

    return {
        k[:6] for k in re.split(r"[^a-z0-9]+", turkce_ascii_kucult(metin))
        if len(k) >= 4
    }


def _kimlik_kaybi(slug: str, eski_metin: str, yeni_metin: str) -> bool:
    """Yeni metin, kampanyayi eskisinden DAHA AZ mi tanitiyor?"""
    from extraction.normalizer import turkce_ascii_kucult

    slug_kelimeleri = {
        k for k in re.split(r"[^a-z0-9]+", turkce_ascii_kucult(slug))
        if len(k) >= 4
    } - {"kampanya", "kampanyalar", "detay"}
    if not slug_kelimeleri:
        return False
    yeni = _kimlik_kelimeleri(yeni_metin)
    eski = _kimlik_kelimeleri(eski_metin)
    return (sum(1 for k in slug_kelimeleri if k[:6] in yeni)
            < sum(1 for k in slug_kelimeleri if k[:6] in eski))


def tazele(hedefler: list[dict], mevcut: dict) -> list[dict]:
    from playwright.sync_api import sync_playwright

    from gold_dataset.ekran_goruntusu_al import _tarayici_ac
    from scraper.scripts import ortak
    from scraper.scripts.js_scraper import popuplari_kapat, sayfa_metnini_al

    sonuclar: list[dict] = []
    with sync_playwright() as p:
        tarayici = _tarayici_ac(p)
        baglam = tarayici.new_context(viewport=VIEWPORT,
                                      user_agent=ortak.USER_AGENT)
        try:
            for sira, kayit in enumerate(hedefler, 1):
                kid = kayit["kayit_id"]
                sl = _slug(kayit.get("kaynak_url"))
                eski_yol, eski = mevcut[sl]
                url = _url_duzelt(kayit["kaynak_url"])
                satir = {"kayit_id": kid, "slug": sl, "url": url,
                         "eski_uzunluk": len(eski.get("normalize_metin") or ""),
                         "eski_sayfa_turu": eski.get("sayfa_turu")}
                print(f"  [{sira:>3}/{len(hedefler)}] {kid:<8} {sl[:52]}")

                sayfa = baglam.new_page()
                try:
                    sayfa.goto(url, timeout=60000, wait_until="domcontentloaded")
                    popuplari_kapat(sayfa)
                    try:
                        sayfa.wait_for_load_state("networkidle", timeout=12000)
                    except Exception:  # noqa: BLE001 - surekli istek atan sayfa
                        pass
                    sayfa.wait_for_timeout(800)
                    metin = sayfa_metnini_al(sayfa)
                except Exception as hata:  # noqa: BLE001
                    satir["durum"] = "HATA"
                    satir["hata"] = f"{type(hata).__name__}: {str(hata)[:140]}"
                    print(f"           HATA: {satir['hata']}")
                    sonuclar.append(satir)
                    sayfa.close()
                    time.sleep(BEKLEME)
                    continue
                finally:
                    if not sayfa.is_closed():
                        sayfa.close()

                dogrulama = ortak.dogrulama_kontrolu(metin)
                if not dogrulama.basarili:
                    satir["durum"] = "DOGRULAMA BASARISIZ"
                    satir["sorunlar"] = dogrulama.sorunlar
                    print(f"           DOGRULAMA: {dogrulama.sorunlar}")
                    sonuclar.append(satir)
                    time.sleep(BEKLEME)
                    continue

                # KOTULESME KORUMASI. `dogrulama_kontrolu` uzunluk ve
                # kodlama bakar; saf gezinti metni o esikleri GECER.
                # Olculdu: bazi Kuveyt Turk sayfalarinda JS ile cekilen
                # metin kampanya govdesi yerine yalnizca menu/altbilgi
                # geldi ("Hakkimizda / Finans Portali / ... Copyright
                # 2026 Kuveyt Turk"). O metni yazmak, calisan bir anlik
                # goruntuyu BOZMAK olurdu - ve altin kaydin kanit spanlari
                # bir anda "kirik" gorunurdu.
                #
                # Olcut: kampanyanin KIMLIGI. Slug'in ayirt edici
                # kelimelerinden kac tanesi metinde geciyor? Yeni metin
                # eskisinden AZ tanitiyorsa yazilmaz.
                if _kimlik_kaybi(sl, eski.get("normalize_metin") or "", metin):
                    satir["durum"] = "KOTULESIRDI - YAZILMADI"
                    print("           KOTULESIRDI: yeni metin kampanyayi "
                          "tanitmiyor, eski anlik goruntu korundu")
                    sonuclar.append(satir)
                    time.sleep(BEKLEME)
                    continue

                # MEVCUT KAYDIN ALANLARI KORUNUR: banka gorunen adi,
                # kategori vb. korpusun geri kalaniyla tutarli kalmali.
                yeni_kayit = {
                    **eski,
                    "sayfa_turu": "JS",
                    "erisim_zamani": datetime.now().isoformat(),
                    "ham_metin": metin,
                    "normalize_metin": metin,
                    "icerik_hash": ortak.icerik_hashi(metin),
                    "onceki_icerik_hash": eski.get("icerik_hash"),
                    "tazeleme_notu": (
                        "JS ile yeniden tarandi: statik tarama sayfanin bir "
                        "bolumunu yakalamamisti (bkz. gold_dataset/kaynak_tazele.py)"
                    ),
                }
                yeni_yol = _yeni_dosya_yolu(eski_yol)
                with open(yeni_yol, "w", encoding="utf-8") as f:
                    json.dump(yeni_kayit, f, ensure_ascii=False, indent=2)

                satir["yeni_uzunluk"] = len(metin)
                satir["dosya"] = yeni_yol.name
                satir["degisti"] = eski.get("icerik_hash") != yeni_kayit["icerik_hash"]
                buyume = (len(metin) / satir["eski_uzunluk"]) if satir["eski_uzunluk"] else 0
                satir["buyume_kati"] = round(buyume, 2)
                satir["durum"] = "GENISLEDI" if buyume >= 1.15 else "ayni"
                sonuclar.append(satir)
                time.sleep(BEKLEME)
        finally:
            baglam.close()
            tarayici.close()
    return sonuclar


def main() -> None:
    a = argparse.ArgumentParser(description="Altin kayitlarin kaynagini JS ile tazeler")
    a.add_argument("--kayit", nargs="*", help="Yalnizca bu kayit_id'ler")
    a.add_argument("--hepsi", action="store_true",
                   help="TASLAK olmayanlari da tazele")
    s = a.parse_args()

    with open(GOLD, encoding="utf-8") as f:
        kayitlar = json.load(f)
    mevcut = _mevcut_kayitlar()

    hedefler = []
    for k in kayitlar:
        if k["kayit_id"].startswith(("A-", "B-", "C-", "D-")):
            continue
        if s.kayit and k["kayit_id"] not in s.kayit:
            continue
        if not s.kayit and not s.hepsi and not (k.get("notlar") or "").startswith("TASLAK"):
            continue
        if _slug(k.get("kaynak_url")) not in mevcut:
            continue  # kaynak sayfasi korpusta yok - tazelenecek bir sey de yok
        hedefler.append(k)

    if not hedefler:
        print("Tazelenecek kayit yok.")
        return
    print(f"{len(hedefler)} kaydin kaynagi JS ile yeniden taranacak.\n")
    sonuclar = tazele(hedefler, mevcut)

    genisleyen = [r for r in sonuclar if r.get("durum") == "GENISLEDI"]
    print("\n" + "=" * 70)
    print(f"  GENISLEYEN ANLIK GORUNTU: {len(genisleyen)} / {len(sonuclar)}")
    print("=" * 70)
    for r in sorted(genisleyen, key=lambda z: -z["buyume_kati"]):
        print(f"  {r['kayit_id']:<8} {r['eski_uzunluk']:>5} -> {r['yeni_uzunluk']:>5} krk"
              f"  (x{r['buyume_kati']})  {r['slug'][:40]}")
    korunan = [r for r in sonuclar if r.get("durum") == "KOTULESIRDI - YAZILMADI"]
    if korunan:
        print(f"\n  KOTULESIRDI, YAZILMADI ({len(korunan)}): "
              + ", ".join(r["kayit_id"] for r in korunan))
        print("  Bu sayfalarda JS ile cekilen metin kampanyayi tanitmiyordu;")
        print("  eski anlik goruntuler oldugu gibi korundu.")

    hatali = [r for r in sonuclar if r.get("durum") in ("HATA", "DOGRULAMA BASARISIZ")]
    if hatali:
        print(f"\n  ALINAMAYAN ({len(hatali)}): "
              + ", ".join(r["kayit_id"] for r in hatali))

    with open(RAPOR, "w", encoding="utf-8") as f:
        json.dump({"tarih": datetime.now().isoformat(), "sonuclar": sonuclar},
                  f, ensure_ascii=False, indent=2)
    print(f"\n  Rapor: {RAPOR}")
    print("  ESKI ANLIK GORUNTULER SILINMEDI - etiketin hangi metinden")
    print("  cikarildigi geriye donuk gorulebilsin diye duruyorlar.")


if __name__ == "__main__":
    main()

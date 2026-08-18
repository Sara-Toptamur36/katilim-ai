"""Banka x urun ailesi x zaman x alan eksenli veri kapsam raporu.

NEDEN: Mentorluk raporu II (Bolum 6.3) "veri eksikligi yalnizca toplam
kampanya sayisina bakilarak analiz edilmemeli" diyor - 4 eksenli bir
coverage matrisi istiyor (Zeynep_Veri rehberi Faz 1 / Gorev 2).

NEDEN POSTGRES DEGIL, DOGRUDAN raw_data: Bu script'in ilk suruma Kampanya
tablosunu (Postgres) okuyordu, ama coverage raporu icin gereken tek sey
zaten scraper/raw_data'daki ham metin - Yagmur'un hibrit cikarim
katmaninin (NER/LLM) urettigi ek dogruluk burada gerekmiyor, kampanya_turu
ve finansal alanlarin VAR/YOK bilgisi icin regex_extractor.kaydi_cikar
yeterli (ayni yaklasim kampanya_tarihcesi.py'de de kullaniliyor - bkz. o
modulun "NEDEN HIBRIT DEGIL REGEX" bolumu). Boylece bu rapor Postgres/
Docker calismadan da uretilebilir - yerel gelistirme ortaminda Docker
kullanilamadigi durumlar icin onemli bir esneklik.

SINIRLAMA: ACTIVE/EXPIRED yasam dongusu durumu yalnizca Postgres'te
hesaplaniyor (bkz. api/models.py, scraper lifecycle mantigi) - bu rapor
DB'ye bakmadigi icin "aktif kampanya sayisi" ureteMEZ, sadece "tekil
kampanya" ve "snapshot" sayilarini uretir. Bu bilinen bir bosluk olarak
raporun kendisinde de belirtilir (bkz. _markdown_uret).

Kullanim (Docker/DB GEREKMEZ):
    python -m scraper.scripts.coverage_raporu
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from extraction.regex_extractor import kaydi_cikar
from scraper.scripts.gold_eslesme import KOD_HARITASI

KOK = Path(__file__).resolve().parents[2]
RAW_DATA_KOK = KOK / "scraper" / "raw_data"
BANKA_CONFIG_DOSYASI = KOK / "scraper" / "config" / "bankalar.json"
GOLD_DOSYASI = KOK / "gold_dataset" / "altin_veri_seti.json"
CIKTI_DOSYASI = KOK / "docs" / "veri_coverage.md"

# Alan ekseni icin izlenen finansal alanlar - rehberdeki "kar payi / vade /
# taksit / odul / masraf" listesiyle birebir ayni (regex_extractor.kaydi_cikar
# ciktisindaki alan adlari).
_ALAN_EKSENI_ALANLARI = [
    "kar_payi_orani_percent",
    "vade_ay",
    "taksit_sayisi",
    "odul_miktari",
    "masraf_durumu",
]


def _banka_kod_ad_haritasi() -> dict[str, str]:
    """kod -> goruntu adi (ör. 'hayatfinans' -> 'Hayat Finans')."""
    with open(BANKA_CONFIG_DOSYASI, encoding="utf-8") as f:
        config = json.load(f)
    return {kod: bilgi["ad"] for kod, bilgi in config.items()}


def _banka_adi_normalize_et(ham_deger: str, kod_ad_haritasi: dict[str, str]) -> str:
    """raw_data'daki 'banka' alani ya goruntu adi ya da banka kodu olabilir
    (statik_scraper.py goruntu adi yazar, js_scraper.py - hayatfinans/tombank
    icin - banka KODUNU yazar). Normalize edilmezse ayni banka raporda iki
    farkli satir olarak gorunur."""
    if ham_deger in kod_ad_haritasi:
        return kod_ad_haritasi[ham_deger]
    return ham_deger


def _tum_ham_kayitlari_oku() -> list[dict]:
    kayitlar = []
    for dosya in RAW_DATA_KOK.glob("*/json/*.json"):
        try:
            with open(dosya, encoding="utf-8") as f:
                kayitlar.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            continue
    return kayitlar


def _url_gruplari_ve_banka_haritasi(
    kod_ad_haritasi: dict[str, str],
) -> tuple[dict[str, list[dict]], dict[str, str]]:
    url_gruplari: dict[str, list[dict]] = defaultdict(list)
    banka_of_url: dict[str, str] = {}
    for kayit in _tum_ham_kayitlari_oku():
        url = kayit.get("url")
        if not url:
            continue
        url_gruplari[url].append(kayit)
        ham_banka = kayit.get("banka")
        if ham_banka:
            banka_of_url[url] = _banka_adi_normalize_et(ham_banka, kod_ad_haritasi)
    return dict(url_gruplari), banka_of_url


def _en_son_kayitlar(url_gruplari: dict[str, list[dict]]) -> dict[str, dict]:
    """Her URL icin en son erisim_zamani'na sahip kaydi doner - urun ailesi
    ve alan eksenlerinde ayni kampanyanin eski versiyonlarini TEKRAR
    saymamak icin (bkz. modul docstring'i, kampanya_tarihcesi.py ile ayni
    "en guncel versiyon" ilkesi)."""
    sonuc = {}
    for url, kayitlar in url_gruplari.items():
        en_son = max(kayitlar, key=lambda k: k.get("erisim_zamani") or "")
        sonuc[url] = en_son
    return sonuc


def _snapshot_istatistikleri(
    url_gruplari: dict[str, list[dict]], banka_of_url: dict[str, str]
) -> dict[str, dict]:
    """Banka goruntu adina gore: snapshot sayisi, benzersiz URL (tekil
    kampanya) sayisi, kampanya basina versiyon sayisi, ilk/son gorulme."""
    sonuc: dict[str, dict] = defaultdict(
        lambda: {"snapshot": 0, "benzersiz_url": 0, "versiyonlar": [], "tarihler": []}
    )
    for url, kayitlar in url_gruplari.items():
        banka = banka_of_url.get(url, "Bilinmiyor")
        s = sonuc[banka]
        s["snapshot"] += len(kayitlar)
        s["benzersiz_url"] += 1
        s["versiyonlar"].append(len(kayitlar))
        for k in kayitlar:
            t = (k.get("erisim_zamani") or "")[:10]
            if t:
                s["tarihler"].append(t)
    return dict(sonuc)


def _gold_sayilari_banka_bazinda(kod_ad_haritasi: dict[str, str]) -> dict[str, int]:
    """gold_dataset/altin_veri_seti.json kayitlarini kayit_id onekinden
    (ör. 'KT-001' -> 'KT' -> 'kuveytturk', bkz. gold_eslesme.KOD_HARITASI)
    banka goruntu adina gore sayar. 'A-001' gibi referans/ornek kayitlar
    (KOD_HARITASI'nde karsiligi olmadigi icin) dogal olarak atlanir."""
    if not GOLD_DOSYASI.exists():
        return {}
    with open(GOLD_DOSYASI, encoding="utf-8") as f:
        kayitlar = json.load(f)

    sayac: dict[str, int] = defaultdict(int)
    for kayit in kayitlar:
        onek = kayit.get("kayit_id", "").split("-")[0]
        kod = KOD_HARITASI.get(onek)
        if kod:
            sayac[kod_ad_haritasi.get(kod, kod)] += 1
    return dict(sayac)


def banka_ekseni(
    snapshot_ist: dict[str, dict], gold_sayilari: dict[str, int]
) -> list[dict]:
    tum_bankalar = set(snapshot_ist) | set(gold_sayilari)
    satirlar = []
    for banka in sorted(tum_bankalar):
        sn = snapshot_ist.get(banka, {"snapshot": 0, "benzersiz_url": 0})
        satirlar.append(
            {
                "banka": banka,
                "tekil_kampanya": sn["benzersiz_url"],
                "snapshot": sn["snapshot"],
                "gold": gold_sayilari.get(banka, 0),
            }
        )
    return satirlar


def urun_ailesi_ekseni(en_son_kayitlar: dict[str, dict]) -> list[dict]:
    tur_bazinda: dict[str, list[dict]] = defaultdict(list)
    for kayit in en_son_kayitlar.values():
        cikan = kaydi_cikar(kayit.get("ham_metin", ""))
        tur = cikan.get("kampanya_turu") or "Belirtilmemis"
        tur_bazinda[tur].append(cikan)

    satirlar = []
    for tur, grup in sorted(tur_bazinda.items(), key=lambda kv: -len(kv[1])):
        toplam_alan = len(grup) * len(_ALAN_EKSENI_ALANLARI)
        dolu_alan = sum(
            1 for c in grup for alan in _ALAN_EKSENI_ALANLARI if c.get(alan) is not None
        )
        doluluk = (dolu_alan / toplam_alan * 100) if toplam_alan else 0.0
        satirlar.append({"urun_ailesi": tur, "sayi": len(grup), "alan_doluluk_yuzde": round(doluluk, 1)})
    return satirlar


def zaman_ekseni(snapshot_ist: dict[str, dict]) -> dict:
    tum_tarihler: list[str] = []
    tum_versiyonlar: list[int] = []
    for ist in snapshot_ist.values():
        tum_tarihler.extend(ist["tarihler"])
        tum_versiyonlar.extend(ist["versiyonlar"])

    if not tum_tarihler:
        return {
            "ilk_gorulme": None,
            "son_gorulme": None,
            "ortalama_versiyon": 0.0,
            "bayatlik_gun": None,
            "coklu_versiyonlu_kampanya": 0,
        }

    ilk = min(tum_tarihler)
    son = max(tum_tarihler)
    try:
        bayatlik = (date.today() - datetime.strptime(son, "%Y-%m-%d").date()).days
    except ValueError:
        bayatlik = None

    return {
        "ilk_gorulme": ilk,
        "son_gorulme": son,
        "ortalama_versiyon": round(sum(tum_versiyonlar) / len(tum_versiyonlar), 2),
        "bayatlik_gun": bayatlik,
        "coklu_versiyonlu_kampanya": sum(1 for v in tum_versiyonlar if v > 1),
    }


def alan_ekseni(en_son_kayitlar: dict[str, dict]) -> list[dict]:
    cikimlar = [kaydi_cikar(k.get("ham_metin", "")) for k in en_son_kayitlar.values()]
    toplam = len(cikimlar)
    satirlar = []
    for alan in _ALAN_EKSENI_ALANLARI:
        dolu = sum(1 for c in cikimlar if c.get(alan) is not None)
        yuzde = (dolu / toplam * 100) if toplam else 0.0
        satirlar.append({"alan": alan, "dolu": dolu, "toplam": toplam, "yuzde": round(yuzde, 1)})
    return satirlar


def _markdown_uret(banka: list[dict], urun: list[dict], zaman: dict, alan: list[dict]) -> str:
    satirlar = [
        "# Veri Kapsam Raporu (4 Eksenli)",
        "",
        f"Uretim tarihi: {date.today().isoformat()}",
        "",
        "Mentorluk raporu II (Bolum 6.3): \"veri eksikligi yalnizca toplam kampanya "
        "sayisina bakilarak analiz edilmemeli\" - bu rapor banka, urun ailesi, zaman "
        "ve alan eksenlerinde ayri ayri kapsam gosterir. Yeni veri toplamaz; "
        "scraper/raw_data'daki mevcut veriyi regex ile ozetler (bkz. script docstring'i - "
        "Postgres/Docker'a bagimli DEGILDIR).",
        "",
        "**Bilinen sinirlama:** ACTIVE/EXPIRED yasam dongusu durumu yalnizca "
        "Postgres'te hesaplanir; bu rapor DB okumadigi icin \"aktif kampanya\" "
        "sayisi icermiyor - yalnizca tekil kampanya ve snapshot sayilari.",
        "",
        "## 1. Banka ekseni",
        "",
        "| Banka | Tekil kampanya | Snapshot (raw_data) | Gold kayit |",
        "|---|---|---|---|",
    ]
    for s in banka:
        satirlar.append(f"| {s['banka']} | {s['tekil_kampanya']} | {s['snapshot']} | {s['gold']} |")

    satirlar += [
        "",
        "## 2. Urun ailesi ekseni",
        "",
        "En son gorulen versiyon uzerinden hesaplanir (ayni kampanyanin eski "
        "snapshot'lari tekrar sayilmaz).",
        "",
        "| Urun ailesi (kampanya_turu) | Sayi | Alan doluluk % |",
        "|---|---|---|",
    ]
    for s in urun:
        satirlar.append(f"| {s['urun_ailesi']} | {s['sayi']} | %{s['alan_doluluk_yuzde']} |")

    satirlar += [
        "",
        "## 3. Zaman ekseni",
        "",
        f"- Ilk gorulme: {zaman['ilk_gorulme']}",
        f"- Son gorulme: {zaman['son_gorulme']}",
        f"- Kampanya basina ortalama versiyon sayisi: {zaman['ortalama_versiyon']}",
        f"- Coklu versiyonlu (gercekten degismis) kampanya sayisi: {zaman['coklu_versiyonlu_kampanya']}",
        f"- Bayatlik (son taramadan bu yana gecen gun): {zaman['bayatlik_gun']}",
        "",
        "## 4. Alan ekseni",
        "",
        "Kar payi / vade / taksit / odul / masraf alanlarinin en son versiyonda ne "
        "siklikta dolu oldugu (regex katmaniyla - Yagmur'un NER/LLM katmani daha "
        "fazla doldurabilir, bu rapor bir ALT SINIR gosterir, kesin doluluk degil).",
        "",
        "| Alan | Dolu | Toplam | Doluluk % |",
        "|---|---|---|---|",
    ]
    for s in alan:
        satirlar.append(f"| {s['alan']} | {s['dolu']} | {s['toplam']} | %{s['yuzde']} |")

    satirlar.append("")
    return "\n".join(satirlar)


def rapor_uret() -> str:
    kod_ad_haritasi = _banka_kod_ad_haritasi()
    url_gruplari, banka_of_url = _url_gruplari_ve_banka_haritasi(kod_ad_haritasi)
    en_son_kayitlar = _en_son_kayitlar(url_gruplari)
    snapshot_ist = _snapshot_istatistikleri(url_gruplari, banka_of_url)
    gold_sayilari = _gold_sayilari_banka_bazinda(kod_ad_haritasi)

    banka = banka_ekseni(snapshot_ist, gold_sayilari)
    urun = urun_ailesi_ekseni(en_son_kayitlar)
    zaman = zaman_ekseni(snapshot_ist)
    alan = alan_ekseni(en_son_kayitlar)
    return _markdown_uret(banka, urun, zaman, alan)


def kaydet() -> Path:
    metin = rapor_uret()
    CIKTI_DOSYASI.write_text(metin, encoding="utf-8")
    return CIKTI_DOSYASI


if __name__ == "__main__":
    yol = kaydet()
    print(f"Rapor yazildi: {yol}")

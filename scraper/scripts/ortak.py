"""Scraper ortak yardimci fonksiyonlari.

Zeynep Veri Toplama Rehberi'ndeki (Bolum 15.1, 19-23) teknik referansin
kod karsiligidir. Tum banka-ozel scraper'lar (statik_scraper.py, ileride
Playwright/PDF modulleri) bu modulu kullanir - boylece nazik davranma,
retry, hash/duplicate ve kayit mantigi HER bankada aynidir.

TASARIM ILKESI: Bu modul, projenin genel "eksik veri gizlenmez, isaretlenir"
ilkesini veri toplama katmaninda da uygular - dogrulama basarisiz olursa
kayit sessizce atlanmaz, nedeni loglanir.
"""

from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.robotparser import RobotFileParser

import requests

BASE_DIR = Path(__file__).resolve().parent.parent  # scraper/
RAW_DATA_DIR = BASE_DIR / "raw_data"
LOGS_DIR = BASE_DIR / "logs"

USER_AGENT = (
    "PeacewAI-KatilimAI-Scraper/0.1 "
    "(TEKNOFEST 2026 egitim/arastirma projesi; "
    "yalnizca herkese acik kampanya sayfalarini okur; "
    "iletisim: peacewai-katilimai proje ekibi)"
)

VARSAYILAN_HEADERS = {"User-Agent": USER_AGENT}

ANAHTAR_KELIMELER = ["kampanya", "kâr payı", "kar payi", "finansman", "oran"]
MIN_METIN_UZUNLUGU = 1000

GECICI_HATALAR = {429, 500, 502, 503, 504}  # tekrar denenir
KALICI_HATALAR = {403, 404}  # tekrar DENENMEZ


# ---------------------------------------------------------------------------
# Loglama (Bolum 21 - hata durumlarini kaydet)
# ---------------------------------------------------------------------------


def log_yaz(banka_kod: str, mesaj: str) -> None:
    """Basit metin tabanli log - scraper/logs/{banka_kod}.log.

    logs/ klasoru .gitignore'da (loglar repoya girmez); yalnizca yerel
    hata ayiklama icindir.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    satir = f"[{datetime.now().isoformat(timespec='seconds')}] {mesaj}\n"
    with open(LOGS_DIR / f"{banka_kod}.log", "a", encoding="utf-8") as f:
        f.write(satir)


# ---------------------------------------------------------------------------
# robots.txt kontrolu (Bolum 19)
# ---------------------------------------------------------------------------


def robots_kontrol_et(ana_sayfa: str) -> tuple[RobotFileParser | None, float | None]:
    """robots.txt'i okur. Donen: (parser, crawl_delay).

    robots.txt hic ulasilamazsa (site yoksa/hata verirse) None doner -
    bu durumda cagiran taraf ihtiyatli davranip yalnizca bilinen/
    onceden dogrulanmis sayfalari cekmelidir.
    """
    rp = RobotFileParser()
    rp.set_url(ana_sayfa.rstrip("/") + "/robots.txt")
    try:
        rp.read()
    except Exception as e:  # noqa: BLE001 - robots okunamazsa devam edemeyiz
        log_yaz("genel", f"robots.txt okunamadi ({ana_sayfa}): {e}")
        return None, None
    return rp, rp.crawl_delay("*")


def izinli_mi(rp: RobotFileParser | None, url: str) -> bool:
    """robots.txt yoksa/okunamadiysa temkinli davranip True doner
    (cogu banka kampanya sayfasi zaten herkese acik ve Disallow'da degildir -
    Bolum 19.1) ama bu durumu log'a yazar ki fark edilsin."""
    if rp is None:
        return True
    return rp.can_fetch("*", url)


# ---------------------------------------------------------------------------
# Nazik davranma (Bolum 20)
# ---------------------------------------------------------------------------


def nazik_bekle(crawl_delay: float | None = None) -> None:
    """Her istekten sonra rastgele 1-3 sn bekler; robots.txt Crawl-delay
    belirtmisse (ve daha uzunsa) onu esas alir."""
    minimum, maksimum = 1.0, 3.0
    if crawl_delay:
        minimum = max(minimum, crawl_delay)
        maksimum = max(maksimum, crawl_delay + 1)
    time.sleep(random.uniform(minimum, maksimum))


# ---------------------------------------------------------------------------
# Retry (Bolum 21.1) - yalnizca gecici hatalarda tekrar dene
# ---------------------------------------------------------------------------


def istek_at_retry_ile(
    url: str, maks_deneme: int = 3, baslangic_bekleme: float = 2.0, timeout: int = 10
) -> requests.Response:
    """403/404'te ASLA tekrar denemez (Bolum 21.1); yalnizca timeout/
    connection error/429/5xx gecici sayilir ve exponential backoff ile
    tekrar denenir."""
    son_hata: Exception | None = None
    for deneme in range(1, maks_deneme + 1):
        try:
            yanit = requests.get(url, timeout=timeout, headers=VARSAYILAN_HEADERS)
        except (requests.Timeout, requests.ConnectionError) as e:
            son_hata = e
            if deneme == maks_deneme:
                raise
            bekleme = baslangic_bekleme * (2 ** (deneme - 1))
            log_yaz("genel", f"Deneme {deneme} basarisiz ({url}): {e} - {bekleme}sn sonra tekrar")
            time.sleep(bekleme)
            continue

        if yanit.status_code == 200:
            return yanit

        if yanit.status_code in KALICI_HATALAR:
            yanit.raise_for_status()

        if yanit.status_code in GECICI_HATALAR and deneme < maks_deneme:
            bekleme = baslangic_bekleme * (2 ** (deneme - 1))
            log_yaz("genel", f"HTTP {yanit.status_code} ({url}) - {bekleme}sn sonra tekrar")
            time.sleep(bekleme)
            continue

        yanit.raise_for_status()

    raise RuntimeError(f"{maks_deneme} denemeden sonra basarisiz: {url}") from son_hata


# ---------------------------------------------------------------------------
# Dogrulama kontrolu (Bolum 15.1)
# ---------------------------------------------------------------------------


@dataclass
class DogrulamaSonucu:
    basarili: bool
    sorunlar: list[str] = field(default_factory=list)


def dogrulama_kontrolu(metin: str) -> DogrulamaSonucu:
    """Cekilen metnin 'gercekten' kullanilabilir olup olmadigini kontrol
    eder. Ucunden biri bile basarisiz olursa kayit ONERILMEZ."""
    sorunlar: list[str] = []

    if not metin or not metin.strip():
        sorunlar.append("sayfa metni bos")

    if len(metin) < MIN_METIN_UZUNLUGU:
        sorunlar.append(f"metin cok kisa ({len(metin)} karakter, min {MIN_METIN_UZUNLUGU})")

    if not any(k in metin.lower() for k in ANAHTAR_KELIMELER):
        sorunlar.append("beklenen anahtar kelimelerden hicbiri bulunamadi")

    if "�" in metin or "Ã" in metin:
        sorunlar.append("encoding bozuk gorunuyor (mojibake)")

    return DogrulamaSonucu(basarili=not sorunlar, sorunlar=sorunlar)


# ---------------------------------------------------------------------------
# Hash tabanli delta + duplicate kontrolu (Bolum 22)
# ---------------------------------------------------------------------------


def icerik_hashi(metin: str) -> str:
    return hashlib.sha256(metin.encode("utf-8")).hexdigest()


def icerik_degisti_mi(yeni_metin: str, onceki_hash: str | None) -> tuple[bool, str]:
    yeni_hash = icerik_hashi(yeni_metin)
    return (yeni_hash != onceki_hash, yeni_hash)


def gorulen_hashleri_yukle(banka_kod: str) -> dict[str, str]:
    """O bankanin json/ klasorundeki mevcut kayitlardan {hash: url} haritasi
    kurar - boylece program yeniden baslatilsa da duplicate hafizasi kaybolmaz."""
    gorulen: dict[str, str] = {}
    json_klasor = RAW_DATA_DIR / banka_kod / "json"
    if not json_klasor.exists():
        return gorulen
    for dosya in sorted(json_klasor.glob("*.json")):
        try:
            with open(dosya, encoding="utf-8") as f:
                kayit = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        h = kayit.get("icerik_hash")
        u = kayit.get("url")
        if h and u:
            gorulen.setdefault(h, u)
    return gorulen


def url_hashlerini_yukle(banka_kod: str) -> dict[str, str]:
    """O bankanin json/ klasorundeki mevcut kayitlardan {url: hash} haritasi
    kurar. `gorulen_hashleri_yukle`den farki: bu, AYNI url'nin bir onceki
    taramaya gore icerigi degisti mi sorusuna cevap vermek icindir
    (Bolum 22.1 - delta kontrolu); `gorulen_hashleri_yukle` ise FARKLI
    url'lerin ayni icerigi tasiyip tasimadigini kontrol eder (22.2)."""
    harita: dict[str, str] = {}
    json_klasor = RAW_DATA_DIR / banka_kod / "json"
    if not json_klasor.exists():
        return harita
    for dosya in sorted(json_klasor.glob("*.json")):
        try:
            with open(dosya, encoding="utf-8") as f:
                kayit = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        h = kayit.get("icerik_hash")
        u = kayit.get("url")
        if h and u:
            harita[u] = h
    return harita


def duplicate_mi(sayfa_metni: str, bu_url: str, gorulen_hashler: dict[str, str]) -> str | None:
    """Ayni icerik daha once BASKA bir URL'de gorulmus mu? Duplicate ise
    ilk gorulen URL'yi, degilse None doner. Yeni ise kaydini gorulen_hashler'e
    ekler (yan etkili - cagiran fonksiyon dict'i saklamaya devam eder)."""
    h = icerik_hashi(sayfa_metni)
    if h in gorulen_hashler and gorulen_hashler[h] != bu_url:
        return gorulen_hashler[h]
    gorulen_hashler[h] = bu_url
    return None


# ---------------------------------------------------------------------------
# Kaydetme (Bolum 23)
# ---------------------------------------------------------------------------


def _dosya_adi_uret(banka_kod: str, slug: str) -> str:
    tarih = datetime.now().strftime("%Y%m%d")
    temiz_slug = slug.strip("/").replace("/", "_") or "index"
    return f"{tarih}_{banka_kod}_{temiz_slug}"


def ham_kaydet(banka_kod: str, slug: str, sayfa_metni: str) -> Path:
    """Islemeden ONCE ham metni raw/ klasorune yazar (Bolum 23.1)."""
    klasor = RAW_DATA_DIR / banka_kod / "raw"
    klasor.mkdir(parents=True, exist_ok=True)
    dosya = klasor / f"{_dosya_adi_uret(banka_kod, slug)}.txt"
    with open(dosya, "w", encoding="utf-8") as f:
        f.write(sayfa_metni)
    return dosya


def islenmis_kaydet(banka_kod: str, slug: str, kayit: dict) -> Path:
    """Islenmis kaydi json/ klasorune yazar. ensure_ascii=False + utf-8:
    Turkce karakterler ASLA bozulmaz (Bolum 23.2)."""
    klasor = RAW_DATA_DIR / banka_kod / "json"
    klasor.mkdir(parents=True, exist_ok=True)
    dosya = klasor / f"{_dosya_adi_uret(banka_kod, slug)}.json"
    with open(dosya, "w", encoding="utf-8") as f:
        json.dump(kayit, f, ensure_ascii=False, indent=2)
    return dosya

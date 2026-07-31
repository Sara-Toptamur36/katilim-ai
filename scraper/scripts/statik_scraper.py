"""Statik (HTML) kampanya sayfalari icin config-driven scraper.

Rehber Bolum 15 (statik scraper), 14.3 (toplu link cikarma) ve Sprint 1
Gun 5 (config-driven yapi) karsiligidir. Banka farklari
scraper/config/bankalar.json'da tutulur; bu dosya banka-ozel kod
icermez, yalnizca config'i okuyup ayni akisi her banka icin calistirir.

Yalnizca "HTML statik" olarak dogrulanmis bankalar icindir (Bolum 13.3
Tablo 6) - JS ile yuklenen sayfalar icin Playwright tabanli ayri bir
modul gerekir (henuz yazilmadi, bkz. docs/veri_toplama_notlari.md).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from preprocessing.normalizer import metni_normalize_et
from scraper.scripts import ortak

CONFIG_DOSYASI = ortak.BASE_DIR / "config" / "bankalar.json"


def config_yukle(yol: Path = CONFIG_DOSYASI) -> dict:
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


def kampanya_linklerini_topla(ayar: dict) -> list[str]:
    """Kampanya listesi sayfa(lar)indan detay linklerini toplar (Bolum 14.3).

    Yalnizca bankanin KENDI domaininde ve `detay_link_deseni`ne uyan
    linkler alinir. Bu filtre ozellikle Albaraka icin onemli: kampanya
    listesi sayfasindaki Facebook/Twitter paylasim butonlari, gercek
    detay URL'sini kendi query string'leri icinde tasiyor
    (ör. facebook.com/sharer.php?u=https://www.albaraka.com.tr/...) -
    domain filtresi olmadan bunlar da "link" sanilip toplanirdi.
    """
    ana_domain = urlparse(ayar["ana_sayfa"]).netloc
    desen = ayar["detay_link_deseni"]
    linkler: set[str] = set()

    for liste_url in ayar["kampanya_listesi"]:
        rp, crawl_delay = ortak.robots_kontrol_et(ayar["ana_sayfa"])
        if not ortak.izinli_mi(rp, liste_url):
            ortak.log_yaz(ayar["kod"], f"robots.txt engelledi (liste): {liste_url}")
            continue

        yanit = ortak.istek_at_retry_ile(liste_url)
        soup = BeautifulSoup(yanit.text, "html.parser")

        for a in soup.find_all("a", href=True):
            tam_url = urljoin(liste_url, a["href"])
            parcalar = urlparse(tam_url)
            if parcalar.netloc != ana_domain:
                continue  # sosyal medya / farkli domain echo linki - atla
            if desen not in tam_url:
                continue
            if tam_url.rstrip("/").endswith(desen.rstrip("/")):
                continue  # bos sablon linki (ör. sadece ".../detay/")
            linkler.add(tam_url.split("?")[0].split("#")[0])

        ortak.nazik_bekle(crawl_delay or ayar.get("crawl_delay"))

    return sorted(linkler)


def sayfa_tara(
    banka_kod: str,
    ayar: dict,
    url: str,
    gorulen_hashler: dict[str, str],
    kategori: str = "kampanya",
) -> dict:
    """Tek bir kampanya detay sayfasini ceker, dogrular, normalize eder,
    kaydeder. Donen sozluk her zaman en az {"url", "durum"} tasir."""
    slug = urlparse(url).path

    rp, crawl_delay = ortak.robots_kontrol_et(ayar["ana_sayfa"])
    if not ortak.izinli_mi(rp, url):
        ortak.log_yaz(banka_kod, f"robots.txt engelledi, atlandi: {url}")
        return {"url": url, "durum": "robots_engelledi"}

    try:
        yanit = ortak.istek_at_retry_ile(url)
    except Exception as e:  # noqa: BLE001 - kalici/gecici tum hatalar burada yakalanir
        ortak.log_yaz(banka_kod, f"CEKME HATASI ({url}): {e}")
        return {"url": url, "durum": "hata", "hata": str(e)}

    soup = BeautifulSoup(yanit.text, "html.parser")

    icerik_secici = ayar.get("icerik_secici")
    secili = soup.select_one(icerik_secici) if icerik_secici else None
    sayfa_metni = (secili or soup).get_text("\n", strip=True)

    dogrulama = ortak.dogrulama_kontrolu(sayfa_metni)
    if not dogrulama.basarili:
        ortak.log_yaz(banka_kod, f"DOGRULAMA BASARISIZ ({url}): {dogrulama.sorunlar}")
        return {"url": url, "durum": "dogrulama_basarisiz", "sorunlar": dogrulama.sorunlar}

    onceki_url = ortak.duplicate_mi(sayfa_metni, url, gorulen_hashler)
    if onceki_url:
        ortak.log_yaz(banka_kod, f"DUPLICATE: {url} -> zaten islenmis: {onceki_url}")
        return {"url": url, "durum": "duplicate", "ilk_url": onceki_url}

    normalize_metin = metni_normalize_et(sayfa_metni)
    guncel_hash = ortak.icerik_hashi(sayfa_metni)

    ortak.ham_kaydet(banka_kod, slug, sayfa_metni)

    ham_kayit = {
        "banka": ayar["ad"],
        "kategori": kategori,
        "url": url,
        "sayfa_turu": ayar.get("sayfa_turu", "HTML"),
        "erisim_zamani": datetime.now().isoformat(),
        "ham_metin": sayfa_metni,
        "normalize_metin": normalize_metin,
        "icerik_hash": guncel_hash,
        "http_durumu": yanit.status_code,
        "content_type": yanit.headers.get("Content-Type"),
        "encoding": yanit.encoding,
    }
    json_dosya = ortak.islenmis_kaydet(banka_kod, slug, ham_kayit)

    ortak.nazik_bekle(crawl_delay or ayar.get("crawl_delay"))

    return {"url": url, "durum": "basarili", "json_dosya": str(json_dosya)}


def banka_tara(banka_kod: str, ayar: dict) -> dict:
    """Bir bankanin kampanya listesini + tum detay sayfalarini tarar.

    Donen ozet: {"basarili": [...], "atlandi": [...], "hatali": [...]}
    - her biri {url, durum, ...} sozlukleri listesi.
    """
    gorulen_hashler = ortak.gorulen_hashleri_yukle(banka_kod)
    ozet: dict[str, list] = {"basarili": [], "atlandi": [], "hatali": []}

    try:
        linkler = kampanya_linklerini_topla(ayar)
    except Exception as e:  # noqa: BLE001
        ortak.log_yaz(banka_kod, f"LISTE SAYFASI HATASI: {e}")
        ozet["hatali"].append({"url": ayar["kampanya_listesi"], "hata": str(e)})
        return ozet

    ortak.log_yaz(banka_kod, f"{len(linkler)} kampanya linki bulundu")

    for url in linkler:
        sonuc = sayfa_tara(banka_kod, ayar, url, gorulen_hashler)
        if sonuc["durum"] == "basarili":
            ozet["basarili"].append(sonuc)
        elif sonuc["durum"] == "hata":
            ozet["hatali"].append(sonuc)
        else:
            ozet["atlandi"].append(sonuc)

    return ozet

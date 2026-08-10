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
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from preprocessing.kapsam import kampanya_govdesini_ayikla
from preprocessing.normalizer import metni_normalize_et
from scraper.scripts import ortak, pdf_isle, tablo_isle

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

    `haric_link_desenleri` (config, opsiyonel): query string DAHIL tam
    URL'de bu alt metinlerden biri geçiyorsa link tamamen atlanir - query
    strip edilmeden ONCE kontrol edilir. Ziraat Katilim icin gerekli:
    "?IsArchived=true" ile isaretli arsivlenmis kampanyalar, query strip
    edildikten sonra normal bir kampanyayla ayni URL'ye donusur ve
    yanlislikla "guncel" sanilirdi (Bolum 13.3).
    """
    ana_domain = urlparse(ayar["ana_sayfa"]).netloc
    desen = ayar["detay_link_deseni"]
    haric_desenler = ayar.get("haric_link_desenleri", [])
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
            # Kucuk/buyuk harf duyarsiz karsilastirma: bazi bankalar (ör.
            # Turkiye Finans'in ASPX/SharePoint URL'leri, ".../Sayfalar/...")
            # yol bilesenlerinde buyuk harf kullanir - sabit kucuk harfli
            # bir desen bunlari sessizce (0 sonucla) kacirirdi.
            tam_url_kucuk = tam_url.lower()
            if desen.lower() not in tam_url_kucuk:
                continue
            if tam_url.rstrip("/").lower().endswith(desen.rstrip("/").lower()):
                continue  # bos sablon linki (ör. sadece ".../detay/")
            if any(h.lower() in tam_url_kucuk for h in haric_desenler):
                continue  # ör. arsivlenmis kampanya (Ziraat: ?IsArchived=true)
            linkler.add(tam_url.split("?")[0].split("#")[0])

        ortak.nazik_bekle(crawl_delay or ayar.get("crawl_delay"))

    return sorted(linkler)


def sayfa_tara(
    banka_kod: str,
    ayar: dict,
    url: str,
    gorulen_hashler: dict[str, str],
    url_hashler: dict[str, str] | None = None,
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

    # KAPSAM: icerik secicisi bazen sayfanin sonundaki "ilgili
    # kampanyalar" tanitim blogunu da aliyor ve o blok BASKA
    # kampanyalarin tutarlarini iceriyor (bkz. preprocessing/kapsam.py).
    sayfa_metni = kampanya_govdesini_ayikla(sayfa_metni)

    dogrulama = ortak.dogrulama_kontrolu(sayfa_metni)
    if not dogrulama.basarili:
        ortak.log_yaz(banka_kod, f"DOGRULAMA BASARISIZ ({url}): {dogrulama.sorunlar}")
        return {"url": url, "durum": "dogrulama_basarisiz", "sorunlar": dogrulama.sorunlar}
    if dogrulama.kisa_icerik:
        ortak.log_yaz(banka_kod, f"KISA AMA GECERLI, kaydedildi ({len(sayfa_metni)} karakter): {url}")

    # Bolum 22.1 - Delta kontrolu: bu URL daha once tarandiysa VE icerigi
    # degismediyse yeniden islemeye gerek yok (Sprint 3 Gun 5 - periyodik
    # calistirmada gereksiz is yapmama garantisi).
    guncel_hash = ortak.icerik_hashi(sayfa_metni)
    if url_hashler is not None:
        degisti, _ = ortak.icerik_degisti_mi(sayfa_metni, url_hashler.get(url))
        if not degisti:
            ortak.log_yaz(banka_kod, f"DEGISMEDI, atlandi: {url}")
            return {"url": url, "durum": "degismedi"}

    # Bolum 22.2 - Duplicate kontrolu: ayni icerik BASKA bir URL'de mi?
    onceki_url = ortak.duplicate_mi(sayfa_metni, url, gorulen_hashler)
    if onceki_url:
        ortak.log_yaz(banka_kod, f"DUPLICATE: {url} -> zaten islenmis: {onceki_url}")
        return {"url": url, "durum": "duplicate", "ilk_url": onceki_url}

    normalize_metin = metni_normalize_et(sayfa_metni)

    ortak.ham_kaydet(banka_kod, slug, sayfa_metni)

    # Bolum 17/18: sayfada PDF eki veya HTML tablosu var mi? (get_text()
    # tablo yapisini duzlestirir - bu yuzden TAM soup uzerinden, icerik
    # secicisiyle sinirlamadan bakilir)
    pdf_kayitlari = pdf_isle.pdflari_isle(banka_kod, soup, url)
    tablolar = tablo_isle.tablolari_json_yap(tablo_isle.sayfadaki_tablolari_al(yanit.text))

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
        "pdf_dosyalari": pdf_kayitlari,
        "tablolar": tablolar,
        "icerik_kalitesi": "kisa" if dogrulama.kisa_icerik else "tam",
    }
    json_dosya = ortak.islenmis_kaydet(banka_kod, slug, ham_kayit)
    if url_hashler is not None:
        url_hashler[url] = guncel_hash

    ortak.nazik_bekle(crawl_delay or ayar.get("crawl_delay"))

    return {"url": url, "durum": "basarili", "json_dosya": str(json_dosya)}


def _slug_uret(baslik: str, yedek_indeks: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", baslik.lower()).strip("-")
    return slug or f"kampanya-{yedek_indeks}"


def tek_sayfa_coklu_kampanya_tara(banka_kod: str, ayar: dict) -> dict:
    """Kampanyalarin ayri detay URL'leri OLMADIGI, hepsinin TEK bir sayfada
    (ör. accordion panellerinde) durdugu bankalar icin (T.O.M. Katilim,
    Bolum 13.3).

    Her panel, kendi ONCESINDEKI baslik etiketiyle (h1-h5) birlikte,
    sentetik bir URL (liste_url + '#slug') ile AYRI bir "sanal" kampanya
    kaydi olarak islenir - boylece hash/duplicate/delta kontrolu ve
    Yagmur'un url bazli cikarim eslesmesi normal calisir, tek bir dev
    kayida karisik butun kampanyalar yazilmaz.
    """
    liste_url = ayar["kampanya_listesi"][0]
    kapsayici_secici = ayar["kampanya_kapsayici_secici"]
    govde_secici = ayar["kampanya_govde_secici"]

    rp, crawl_delay = ortak.robots_kontrol_et(ayar["ana_sayfa"])
    if not ortak.izinli_mi(rp, liste_url):
        ortak.log_yaz(banka_kod, f"robots.txt engelledi: {liste_url}")
        return {"basarili": [], "atlandi": [{"url": liste_url, "durum": "robots_engelledi"}], "hatali": []}

    yanit = ortak.istek_at_retry_ile(liste_url)
    soup = BeautifulSoup(yanit.text, "html.parser")

    gorulen_hashler = ortak.gorulen_hashleri_yukle(banka_kod)
    url_hashler = ortak.url_hashlerini_yukle(banka_kod)
    ozet: dict[str, list] = {"basarili": [], "atlandi": [], "hatali": []}

    for i, panel in enumerate(soup.select(kapsayici_secici)):
        govde = panel.select_one(govde_secici)
        if govde is None:
            continue

        baslik_tag = panel.find_previous(["h1", "h2", "h3", "h4", "h5"])
        direkt_metin = baslik_tag.find(string=True, recursive=False) if baslik_tag else None
        baslik = (
            direkt_metin.strip()
            if direkt_metin
            else (baslik_tag.get_text(" ", strip=True) if baslik_tag else f"Kampanya {i + 1}")
        )

        slug = _slug_uret(baslik, i)
        sentetik_url = f"{liste_url}#{slug}"
        sayfa_metni = f"{baslik}\n{govde.get_text(chr(10), strip=True)}"

        dogrulama = ortak.dogrulama_kontrolu(sayfa_metni)
        if not dogrulama.basarili:
            ortak.log_yaz(banka_kod, f"DOGRULAMA BASARISIZ ({sentetik_url}): {dogrulama.sorunlar}")
            ozet["atlandi"].append(
                {"url": sentetik_url, "durum": "dogrulama_basarisiz", "sorunlar": dogrulama.sorunlar}
            )
            continue
        if dogrulama.kisa_icerik:
            ortak.log_yaz(
                banka_kod, f"KISA AMA GECERLI, kaydedildi ({len(sayfa_metni)} karakter): {sentetik_url}"
            )

        guncel_hash = ortak.icerik_hashi(sayfa_metni)
        degisti, _ = ortak.icerik_degisti_mi(sayfa_metni, url_hashler.get(sentetik_url))
        if not degisti:
            ortak.log_yaz(banka_kod, f"DEGISMEDI, atlandi: {sentetik_url}")
            ozet["atlandi"].append({"url": sentetik_url, "durum": "degismedi"})
            continue

        onceki_url = ortak.duplicate_mi(sayfa_metni, sentetik_url, gorulen_hashler)
        if onceki_url:
            ozet["atlandi"].append({"url": sentetik_url, "durum": "duplicate", "ilk_url": onceki_url})
            continue

        normalize_metin = metni_normalize_et(sayfa_metni)
        ortak.ham_kaydet(banka_kod, slug, sayfa_metni)

        ham_kayit = {
            "banka": ayar["ad"],
            "kategori": "kampanya",
            "url": sentetik_url,
            "sayfa_turu": ayar.get("sayfa_turu", "HTML"),
            "erisim_zamani": datetime.now().isoformat(),
            "ham_metin": sayfa_metni,
            "normalize_metin": normalize_metin,
            "icerik_hash": guncel_hash,
            "http_durumu": yanit.status_code,
            "content_type": yanit.headers.get("Content-Type"),
            "encoding": yanit.encoding,
            "pdf_dosyalari": [],
            "tablolar": [],
            "icerik_kalitesi": "kisa" if dogrulama.kisa_icerik else "tam",
        }
        json_dosya = ortak.islenmis_kaydet(banka_kod, slug, ham_kayit)
        url_hashler[sentetik_url] = guncel_hash

        ozet["basarili"].append({"url": sentetik_url, "durum": "basarili", "json_dosya": str(json_dosya)})

    ortak.nazik_bekle(crawl_delay or ayar.get("crawl_delay"))
    return ozet


def banka_tara(banka_kod: str, ayar: dict) -> dict:
    """Bir bankanin kampanya listesini + tum detay sayfalarini tarar.

    Donen ozet: {"basarili": [...], "atlandi": [...], "hatali": [...]}
    - her biri {url, durum, ...} sozlukleri listesi.

    `cok_kampanyali_sayfa` config bayragi varsa (T.O.M. gibi ayri detay
    URL'si olmayan bankalar), farkli bir akisa (tek_sayfa_coklu_kampanya_tara)
    yonlendirilir.
    """
    if ayar.get("cok_kampanyali_sayfa"):
        return tek_sayfa_coklu_kampanya_tara(banka_kod, ayar)

    gorulen_hashler = ortak.gorulen_hashleri_yukle(banka_kod)
    url_hashler = ortak.url_hashlerini_yukle(banka_kod)
    ozet: dict[str, list] = {"basarili": [], "atlandi": [], "hatali": []}

    try:
        linkler = kampanya_linklerini_topla(ayar)
    except Exception as e:  # noqa: BLE001
        ortak.log_yaz(banka_kod, f"LISTE SAYFASI HATASI: {e}")
        ozet["hatali"].append({"url": ayar["kampanya_listesi"], "hata": str(e)})
        return ozet

    ortak.log_yaz(banka_kod, f"{len(linkler)} kampanya linki bulundu")

    for url in linkler:
        sonuc = sayfa_tara(banka_kod, ayar, url, gorulen_hashler, url_hashler)
        if sonuc["durum"] == "basarili":
            ozet["basarili"].append(sonuc)
        elif sonuc["durum"] == "hata":
            ozet["hatali"].append(sonuc)
        else:
            ozet["atlandi"].append(sonuc)

    return ozet

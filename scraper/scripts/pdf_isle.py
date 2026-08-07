"""PDF dokumanlarini bulma, indirme ve metne cevirme.

Rehber Bolum 17. Bankalar ucret tarifesi / bilgilendirme formu gibi
belgeleri PDF olarak sayfaya ekler. Bu modul: (17.1) sayfadaki PDF
linklerini bulur, (17.2) indirir, (17.3) metin tabanli PDF'lerden
pypdf ile metin cikarir.

OCR (Bolum 17.4, taranmis/goruntu PDF'ler icin) BU MODULDE YOK -
pytesseract + Tesseract binary'sinin ayrica yerel kurulmasini gerektirir
(Windows'ta ayri bir indirme/PATH adimidir). `pdf_metne_cevir` taranmis
bir PDF'te bos/cok kisa metin donecektir; boyle bir durumda kayda
dusuk confidence ile isaretlenip Yagmur'a iletilmesi rehberin onerdigi
yoldur (Bolum 17.4 karar kurali: 1-2 taranmis PDF varsa elle kopyalamak,
OCR kurulumuyla ugrasmaktan daha hizlidir).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from pypdf import PdfReader

from scraper.scripts import ortak


def _ayni_alan_adi_mi(sayfa_url: str, hedef_url: str) -> bool:
    """Hedef PDF, sayfayla AYNI alan adinda mi?

    GUVENLIK (SSRF korumasi): Bu modul, KONTROLUMUZ DISINDAKI banka
    sayfalarindan link topluyor. Dogrulama olmadan, sayfadaki herhangi
    bir ".pdf" ile biten baglanti indirilirdi - kotu niyetli ya da ele
    gecirilmis bir sayfa bunu ic servislere yonlendirmek icin
    kullanabilirdi:
        http://localhost:6333/...        (Qdrant)
        http://127.0.0.1:5432/...        (PostgreSQL)
        http://169.254.169.254/...       (bulut metadata servisi)
    Banka bilgilendirme PDF'leri zaten kendi alan adlarinda yayinlanir,
    bu yuzden "ayni alan adi" kurali mesru kullanimda kayip yaratmaz.

    Alt alan adlari kabul edilir (ornegin sayfa "www.banka.com.tr" iken
    PDF "cdn.banka.com.tr"de olabilir) - kok alan adi karsilastirilir.
    """
    sayfa_host = (urlparse(sayfa_url).hostname or "").lower()
    hedef_host = (urlparse(hedef_url).hostname or "").lower()
    if not sayfa_host or not hedef_host:
        return False
    if hedef_host == sayfa_host:
        return True
    # Kok alan adi (son iki-uc etiket) uzerinden alt alan adi kontrolu
    return hedef_host.endswith("." + ".".join(sayfa_host.split(".")[-3:])) or \
        hedef_host.endswith("." + ".".join(sayfa_host.split(".")[-2:]))


def pdf_linklerini_bul(soup: BeautifulSoup, sayfa_url: str) -> list[str]:
    """Sayfadaki <a href="...pdf"> linklerini tam URL olarak dondurur.

    Query string/fragment atilir (ör. "...pdf?v=2" ve "...pdf" ayni dosyayi
    isaret eder) - boylece ayni PDF iki kez indirilmez (Bolum 22.2'deki
    duplicate mantigiyla ayni ilke).

    Yalnizca http/https semasindaki ve sayfayla AYNI alan adindaki
    linkler donulur (bkz. _ayni_alan_adi_mi - SSRF korumasi)."""
    linkler = []
    for a in soup.find_all("a", href=True):
        if not a["href"].lower().split("?")[0].split("#")[0].endswith(".pdf"):
            continue
        tam_url = urljoin(sayfa_url, a["href"]).split("?")[0].split("#")[0]
        if urlparse(tam_url).scheme not in ("http", "https"):
            continue  # file://, ftp://, data: vb. reddedilir
        if not _ayni_alan_adi_mi(sayfa_url, tam_url):
            continue
        linkler.append(tam_url)
    return sorted(set(linkler))


def pdf_indir(banka_kod: str, pdf_url: str) -> Path:
    """PDF'yi indirip scraper/raw_data/{banka}/pdf/ klasorune yazar."""
    yanit = ortak.istek_at_retry_ile(pdf_url, timeout=15)
    klasor = ortak.RAW_DATA_DIR / banka_kod / "pdf"
    klasor.mkdir(parents=True, exist_ok=True)

    dosya_adi = pdf_url.rstrip("/").split("/")[-1].split("?")[0] or "dosya.pdf"
    tarih = datetime.now().strftime("%Y%m%d")
    dosya = klasor / f"{tarih}_{banka_kod}_{dosya_adi}"
    with open(dosya, "wb") as f:  # "wb": PDF ikili (binary) bir dosyadir
        f.write(yanit.content)
    return dosya


def pdf_metne_cevir(pdf_yolu: Path) -> str:
    """Metin tabanli PDF'den metin cikarir.

    Taranmis (goruntu) bir PDF verilirse extract_text() bos/anlamsiz
    doner - bu, OCR gerektigi anlamina gelir (Bolum 17.4). Bu fonksiyon
    kendisi OCR YAPMAZ; cagiran taraf donen metnin kisaligina bakarak
    karar vermelidir.
    """
    reader = PdfReader(str(pdf_yolu))
    metin = ""
    for sayfa in reader.pages:
        metin += sayfa.extract_text() or ""
    return metin


def pdflari_isle(banka_kod: str, soup: BeautifulSoup, sayfa_url: str) -> list[dict]:
    """Bir sayfadaki tum PDF'leri bulur, indirir, metne cevirir.

    Donen liste her PDF icin {url, dosya, metin_uzunlugu, tarama_supheli}
    sozlugu tasir. Bir PDF indirilemez/islenemezse o PDF atlanir, log'a
    yazilir - diger PDF'ler/sayfanin geri kalani etkilenmez.
    """
    sonuclar: list[dict] = []
    for pdf_url in pdf_linklerini_bul(soup, sayfa_url):
        try:
            pdf_yolu = pdf_indir(banka_kod, pdf_url)
            metin = pdf_metne_cevir(pdf_yolu)
        except Exception as e:  # noqa: BLE001 - bir PDF patlarsa digerleri devam etsin
            ortak.log_yaz(banka_kod, f"PDF islenemedi ({pdf_url}): {e}")
            continue

        sonuclar.append(
            {
                "url": pdf_url,
                "dosya": str(pdf_yolu),
                "metin_uzunlugu": len(metin),
                # < 200 karakter: muhtemelen taranmis/goruntu PDF, OCR gerekir (Bolum 17.4)
                "tarama_supheli": len(metin) < 200,
            }
        )
    return sonuclar

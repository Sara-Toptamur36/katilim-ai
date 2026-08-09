"""JavaScript ile yuklenen sayfalar icin Playwright tabanli scraper.

Rehber Bolum 16. Kuveyt Turk / Albaraka Turk / Vakif Katilim'in ucu de
"HTML statik" olarak dogrulandigi icin (Bolum 13.3, Tablo 6) Sprint 1'de
bu modul CALISTIRILMADI - statik_scraper.py yeterliydi. Bu modul, Sprint
2-3'te JS ile yuklenen bir sayfaya (ör. Ziraat/Emlak Katilim icin Bolum
14.2'deki CTRL+U + CTRL+F testi JS sonucu verirse) ihtiyac duyuldugunda
hazir olsun diye simdiden yazildi.

KURULUM NOTU (henuz yapilmadi): Bu modulun calismasi icin `playwright`
pip paketi yeterli degildir; tarayici motorlarinin da indirilmesi
gerekir:

    playwright install chromium

Bu, tek seferlik ama boyutlu (~100+ MB) bir indirmedir - Sprint 1'de 3
hedef banka da JS gerektirmedigi icin bu adim simdilik atlandi. JS'e
ihtiyac duyulan ilk bankada bu komut calistirilmali.
"""

from __future__ import annotations

from datetime import datetime

from scraper.scripts import ortak

# Her banka icin, o sitede DevTools ile bulunan cerez/pop-up butonu
# secicisi buraya eklenir (Bolum 16.1). Bilinen genel adaylar onceden
# doldurulmustur; yeni bankaya gecince DevTools ile dogrulanmalidir.
CEREZ_SECICILERI = [
    "button:has-text('Yalnızca Gerekli')",
    "button:has-text('Reddet')",
    "button:has-text('Tümünü Reddet')",
    "#onetrust-reject-all-handler",
    ".cookie-reject",
    "button[aria-label='Kapat']",
    ".modal-close",
]

# Ana govde yerine dogrudan kampanya iceriginin bulundugu kapsayiciyi
# hedeflemek, pop-up/menu sizintisini kokten onler (Bolum 16.1).
GENEL_ICERIK_ADAYLARI = ["main", "article", ".kampanya-detay", "#icerik"]


def popuplari_kapat(sayfa) -> bool:
    """Cerez/pop-up pencerelerini kapatmayi dener. Bulamazsa sessizce
    False doner - bu bir hata degil, cogu sayfada zaten pop-up olmaz."""
    for secici in CEREZ_SECICILERI:
        try:
            oge = sayfa.locator(secici).first
            if oge.is_visible(timeout=1500):
                oge.click()
                sayfa.wait_for_timeout(500)
                return True
        except Exception:  # noqa: BLE001 - bu secici bu sayfada yok, sonrakini dene
            continue
    return False


def sayfa_metnini_al(sayfa, icerik_secicileri: list[str] | None = None) -> str:
    """Once ozel bir icerik secicisi dener; hicbiri yoksa tum body'i alir."""
    for secici in icerik_secicileri or GENEL_ICERIK_ADAYLARI:
        try:
            oge = sayfa.locator(secici).first
            if oge.is_visible(timeout=1000):
                return oge.inner_text()
        except Exception:  # noqa: BLE001
            continue
    return sayfa.inner_text("body")


def chromium_hazir_mi() -> bool:
    """`playwright install chromium` calistirilmis mi? (Bolum 16 kurulum
    notu). CI'da ve bu adimi henuz atmamis gelistirici makinelerinde
    tarayici motoru YOKTUR - bu durumda JS testleri hata vermek yerine
    atlanmalidir (bkz. test_js_scraper.py, Ollama/Qdrant testleriyle
    ayni desen)."""
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            tarayici = p.chromium.launch(headless=True)
            tarayici.close()
        return True
    except Exception:  # noqa: BLE001 - executable yok/bozuk, herhangi bir hata "hazir degil" demektir
        return False


def js_sayfa_tara(banka_kod: str, url: str, icerik_secicileri: list[str] | None = None) -> dict:
    """JS ile yuklenen tek bir sayfayi Playwright ile ceker.

    NOT: `playwright install chromium` calistirilmadan bu fonksiyon
    "Executable doesn't exist" hatasi verir - modul docstring'ine bakin.
    """
    from playwright.sync_api import sync_playwright  # yerel import: agir bagimlilik

    with sync_playwright() as p:
        tarayici = p.chromium.launch(headless=True)
        sayfa = tarayici.new_page()
        sayfa.goto(url, timeout=15000)

        popuplari_kapat(sayfa)
        sayfa.wait_for_load_state("networkidle")

        sayfa_metni = sayfa_metnini_al(sayfa, icerik_secicileri)
        html = sayfa.content()

        tarayici.close()

    dogrulama = ortak.dogrulama_kontrolu(sayfa_metni)
    if not dogrulama.basarili:
        ortak.log_yaz(banka_kod, f"DOGRULAMA BASARISIZ (JS, {url}): {dogrulama.sorunlar}")
        return {"url": url, "durum": "dogrulama_basarisiz", "sorunlar": dogrulama.sorunlar}

    ortak.ham_kaydet(banka_kod, url, sayfa_metni)
    ham_kayit = {
        "banka": banka_kod,
        "url": url,
        "sayfa_turu": "JS",
        "erisim_zamani": datetime.now().isoformat(),
        "ham_metin": sayfa_metni,
        "icerik_hash": ortak.icerik_hashi(sayfa_metni),
    }
    json_dosya = ortak.islenmis_kaydet(banka_kod, url, ham_kayit)
    return {"url": url, "durum": "basarili", "json_dosya": str(json_dosya)}

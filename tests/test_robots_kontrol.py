"""ortak.robots_kontrol_et testleri.

DENETIM BULGUSU (18 Agustos 2026, hadiyanindakibanka.com/T.O.M. Hadi):
robots_kontrol_et onceden urllib.robotparser.RobotFileParser.read()
kullaniyordu - bu, stdlib'in KENDI genel User-Agent'iyla ("Python-urllib/x.y")
istek atar. Bu site (robots.txt'i acikca "Allow: /" diyen, tamamen izinli
bir dosya) o generic UA'yi 403 ile reddediyordu; robotparser 401/403'te
TUM siteyi yasakli sayar (kendi belgelenmis davranisi) - sonuc: gercekte
izinli bir siteye "yasak" damgasi vuruluyordu, cunku sorun sitenin kurallari
degil, kontrolun kullandigi istemciydi. Duzeltme: robots.txt da diger tum
sayfalar gibi projenin kendi saydam User-Agent'iyla (requests + VARSAYILAN_
HEADERS) cekilir, sonuc RobotFileParser.parse()'a beslenir.
"""

import requests

from scraper.scripts import ortak


def _sahte_yanit(status_code: int, metin: str = "") -> requests.Response:
    yanit = requests.models.Response()
    yanit.status_code = status_code
    yanit._content = metin.encode("utf-8")
    return yanit


def test_gercek_ua_ile_izinli_robots_txt_dogru_okunur(monkeypatch):
    """Ana regresyon testi: 'Allow: /' diyen bir robots.txt, projenin
    kendi User-Agent'iyla cekildiginde GERCEKTEN izin verir (eski urllib
    tabanli okuma bunu yanlislikla yasaklardı)."""
    icerik = "User-agent: *\nAllow: /\nDisallow: /*arama-sonuclari?q=\n"
    monkeypatch.setattr(
        ortak.requests, "get", lambda *a, **k: _sahte_yanit(200, icerik)
    )
    ortak._ROBOTS_CACHE.clear()

    rp, _ = ortak.robots_kontrol_et("https://ornek-banka.com.tr")
    assert ortak.izinli_mi(rp, "https://ornek-banka.com.tr/kampanyalar")


def test_404_robots_txt_yoksa_her_sey_izinli_sayilir(monkeypatch):
    """Standart kural: robots.txt hic yoksa (404), site herkese acik
    sayilir - sessiz 'yasak' varsayilmaz."""
    monkeypatch.setattr(ortak.requests, "get", lambda *a, **k: _sahte_yanit(404))
    ortak._ROBOTS_CACHE.clear()

    rp, gecikme = ortak.robots_kontrol_et("https://ornek-banka-404.com.tr")
    assert ortak.izinli_mi(rp, "https://ornek-banka-404.com.tr/kampanyalar")


def test_gercek_403_tum_siteyi_yasakli_sayar(monkeypatch):
    """Projenin KENDI saydam User-Agent'iyla bile 403 aliniyorsa, bu artik
    bir istemci sorunu degil - gercek bir yasaktir, robotparser'in kendi
    kuraliyla tutarli sekilde tum site yasakli sayilmali."""
    monkeypatch.setattr(ortak.requests, "get", lambda *a, **k: _sahte_yanit(403))
    ortak._ROBOTS_CACHE.clear()

    rp, _ = ortak.robots_kontrol_et("https://yasakli-banka.com.tr")
    assert not ortak.izinli_mi(rp, "https://yasakli-banka.com.tr/kampanyalar")


def test_ag_hatasinda_temkinli_none_doner(monkeypatch):
    """Baglanti hatasinda (None, None) donmeli - cagiran taraf ihtiyatli
    davransin diye (izinli_mi bu durumda True doner ama loglanir)."""
    def patlat(*a, **k):
        raise requests.ConnectionError("baglanti kurulamadi")

    monkeypatch.setattr(ortak.requests, "get", patlat)
    ortak._ROBOTS_CACHE.clear()

    rp, gecikme = ortak.robots_kontrol_et("https://erisilemeyen-banka.com.tr")
    assert rp is None
    assert gecikme is None


def test_ayni_ana_sayfa_ikinci_kez_ag_istegi_yapmaz(monkeypatch):
    """Onbellekleme: ayni banka icin robots.txt yalnizca BIR kez cekilir
    (Bolum 20 - siteye karsi nazik davranma ilkesi)."""
    cagri_sayaci = {"n": 0}

    def sahte_get(*a, **k):
        cagri_sayaci["n"] += 1
        return _sahte_yanit(200, "User-agent: *\nAllow: /\n")

    monkeypatch.setattr(ortak.requests, "get", sahte_get)
    ortak._ROBOTS_CACHE.clear()

    ortak.robots_kontrol_et("https://tekrar-eden-banka.com.tr")
    ortak.robots_kontrol_et("https://tekrar-eden-banka.com.tr")
    assert cagri_sayaci["n"] == 1

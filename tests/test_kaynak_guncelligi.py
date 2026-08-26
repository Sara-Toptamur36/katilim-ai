"""Kaynak guncelligi: suresi dolmus kampanya GIZLENMEZ, ISARETLENIR.

--------------------------------------------------------------------------
NEDEN FILTRE DEGIL ISARET
--------------------------------------------------------------------------
Retriever'da bir `hedef_tarih` filtresi vardi ve IKI YONDEN de calismiyordu:

  1. Hicbir cagiran gecmiyordu - uretimdeki tek cagri
     agent/router.py::rag_aracini_cagir icinde `getir(soru, limit=3)`.
  2. Calissaydi bile sonuc donmezdi: filtre `valid_at_start` /
     `valid_at_end` alanlarina bakiyor, ama indeks payload'i yalnizca
     metin/banka/kaynak_url/kampanya_adi/erisim_zamani tasiyor. Qdrant'ta
     payload'da olmayan bir anahtara `must` kosulu hicbir noktayi
     eslestirmez - RAG her soruya "kaynak bulamadim" derdi.

Filtre yerine ISARET secildi (karar: 23 Agustos 2026). Gerekce: tarih
yanlis cikarilmissa filtre GECERLI bir kampanyayi sessizce gorunmez
yapar; juri demosunda fark edilmesi en zor hata turu budur. Isaret
hicbir seyi gizlemez - kullanici kaynagi ve uyariyi birlikte gorur.
"""

from datetime import date

import pytest

from agent.router import _guncellik_belirle


BUGUN = date(2026, 8, 23)


def test_gecmis_tarih_SURESI_DOLMUS():
    assert _guncellik_belirle(date(2026, 7, 31), BUGUN) == "suresi_dolmus"


def test_gelecek_tarih_AKTIF():
    assert _guncellik_belirle(date(2026, 12, 31), BUGUN) == "aktif"


def test_BUGUN_biten_kampanya_hala_aktif():
    """Son gun dahildir - "31 Agustos'a kadar gecerli" 31 Agustos'u kapsar."""
    assert _guncellik_belirle(BUGUN, BUGUN) == "aktif"


def test_tarih_YOKSA_aktif_VARSAYILMAZ():
    """Bilinmeyen tarihli kampanyayi gecerli saymak, kullaniciya
    soylemedigimiz bir sey iddia etmek olurdu."""
    assert _guncellik_belirle(None, BUGUN) == "bilinmiyor"


def test_bozuk_tarih_sessizce_AKTIF_olmaz():
    """Ayristirilamayan bir deger "aktif" degil "bilinmiyor" olmali -
    hata yonu guvenli tarafa dusmeli."""
    assert _guncellik_belirle("gecersiz-tarih", BUGUN) == "bilinmiyor"
    assert _guncellik_belirle("", BUGUN) == "bilinmiyor"


def test_ISO_metin_tarih_de_calisir():
    """Kayit katmani tarihi metin olarak verebilir (JSON'dan gelince)."""
    assert _guncellik_belirle("2026-07-31", BUGUN) == "suresi_dolmus"
    assert _guncellik_belirle("2026-12-31T00:00:00", BUGUN) == "aktif"


def test_sema_guncellik_alanini_TASIR():
    """Alan semada yoksa Pydantic degeri SESSIZCE duserdi - bu daha once
    `metin` alaninda yasandi (bkz. Kaynak docstring'i)."""
    from api.schemas import Kaynak

    k = Kaynak(banka="X", kampanya_bitis=date(2026, 7, 31), guncellik="suresi_dolmus")
    assert k.guncellik == "suresi_dolmus"
    assert k.kampanya_bitis == date(2026, 7, 31)
    # Varsayilan "aktif" DEGIL - bilinmeyen bilinmiyordur.
    assert Kaynak().guncellik == "bilinmiyor"


def test_gecersiz_guncellik_degeri_REDDEDILIR():
    from pydantic import ValidationError

    from api.schemas import Kaynak

    with pytest.raises(ValidationError):
        Kaynak(guncellik="belki")


def test_rag_kaynaklari_guncellik_alanini_DOLDURUR():
    """Uctan uca: kayit_getirici enjekte edilirse her kaynak isaretlenir."""
    from types import SimpleNamespace
    from unittest.mock import patch

    from agent import router

    sahte_kayit = SimpleNamespace(
        id=7, kaynak_url="https://banka.example/kampanya",
        kampanya_bitis=date(2026, 7, 31),
    )
    sahte_sonuc = SimpleNamespace(
        yeterli_kaynak_var=True, sebep=None, terim_ortusmesi=0.9,
        eslesen_terimler=["ornek"], terim_agirliklari=[],
        parcalar=[{"skor": 0.9, "ustveri": {
            "metin": "Ornek kampanya metni", "banka": "Test Bankasi",
            "kampanya_adi": "Ornek", "kaynak_url": "https://banka.example/kampanya",
            "erisim_zamani": "2026-08-01T10:00:00"}}],
    )
    with patch("chunking.retriever.getir", return_value=sahte_sonuc):
        sonuc = router.rag_aracini_cagir("ornek soru", kayit_getirici=lambda b: [sahte_kayit])

    assert sonuc["basarili"]
    kaynak = sonuc["kaynaklar"][0]
    assert kaynak["guncellik"] == "suresi_dolmus", (
        "suresi dolmus kaynak isaretlenmedi - demoda sessizce gecerli gorunur")
    assert kaynak["kampanya_bitis"] == date(2026, 7, 31)
    assert kaynak["kampanya_id"] == 7, "kayit tek seferde bulunurken id kaybolmus"


def test_kaynak_GIZLENMEZ_yalnizca_isaretlenir():
    """Asil davranis sozu: suresi dolmus olsa bile kaynak DONER."""
    from types import SimpleNamespace
    from unittest.mock import patch

    from agent import router

    eski = SimpleNamespace(id=1, kaynak_url="u1", kampanya_bitis=date(2020, 1, 1))
    sahte_sonuc = SimpleNamespace(
        yeterli_kaynak_var=True, sebep=None, terim_ortusmesi=0.9,
        eslesen_terimler=["ornek"], terim_agirliklari=[],
        parcalar=[{"skor": 0.9, "ustveri": {
            "metin": "Cok eski kampanya", "banka": "Test Bankasi",
            "kampanya_adi": "Eski", "kaynak_url": "u1",
            "erisim_zamani": "2020-01-01T10:00:00"}}],
    )
    with patch("chunking.retriever.getir", return_value=sahte_sonuc):
        sonuc = router.rag_aracini_cagir("soru", kayit_getirici=lambda b: [eski])

    assert len(sonuc["kaynaklar"]) == 1, "suresi dolmus kaynak GIZLENMIS - filtre degil isaret olmali"
    assert sonuc["kaynaklar"][0]["guncellik"] == "suresi_dolmus"

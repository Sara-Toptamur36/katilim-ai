"""extraction/vade_farksiz_db_duzelt.py testleri.

Bu betik VERI SILER (kar payi oranini bosaltir), dolayisiyla yanlis
calismasinin bedeli dogrudan veri kaybidir. Testler iki seyi olcer:

  1. KARAR dogru mu - hangi kanit hangi sonuca goturuyor.
  2. Kural altin set tarafiyla AYNI mi - iki taraf ayrisirsa "gold boyle
     diyor, DB soyle" celiskisi dogar ki bu, betigin duzelttigi hatanin
     ta kendisidir.

Gercek veritabani GEREKMEZ: karar mantigi ham metne bakar, DB'ye degil.
"""

from __future__ import annotations

import pytest

from extraction.vade_farksiz_db_duzelt import etkilenen_satirlar


class SahteSatir:
    def __init__(self, id, kar_payi_orani_percent, kaynak_url,
                 banka="Kuveyt Turk", kampanya_adi="Test"):
        self.id = id
        self.kar_payi_orani_percent = kar_payi_orani_percent
        self.kaynak_url = kaynak_url
        self.banka = banka
        self.kampanya_adi = kampanya_adi


class SahteSorgu:
    def __init__(self, satirlar):
        self._satirlar = satirlar

    def all(self):
        return self._satirlar


class SahteOturum:
    def __init__(self, satirlar):
        self._satirlar = satirlar

    def query(self, _model):
        return SahteSorgu(self._satirlar)


@pytest.fixture
def metinleri_sabitle(monkeypatch):
    """_ham_metinleri_url_ile_esle'yi testin verdigi metinlerle degistirir."""

    def uygula(url_metin: dict[str, str]):
        monkeypatch.setattr(
            "extraction.vade_farksiz_db_duzelt._ham_metinleri_url_ile_esle",
            lambda: {u: {"ham_metin": m} for u, m in url_metin.items()},
        )

    return uygula


def test_tek_kanit_vade_farksizsa_bosaltilir(metinleri_sabitle):
    """ASIL DUZELTME: kart taksit ifadesi finansman orani sayilmaz."""
    metinleri_sabitle({"u1": "Marketlerde vade farksiz 6 taksit firsati"})
    bosalt, koru = etkilenen_satirlar(SahteOturum([SahteSatir(1, 0.0, "u1")]))
    assert [b["id"] for b in bosalt] == [1]
    assert koru == []


def test_acikca_kar_paysiz_yazan_kayit_KORUNUR(metinleri_sabitle):
    """Gercek sifirlar kaybolmamali - motorda da bu kural korunuyor."""
    metinleri_sabitle({"u1": "Bu finansman tamamen kar paysiz sunulmaktadir"})
    bosalt, koru = etkilenen_satirlar(SahteOturum([SahteSatir(1, 0.0, "u1")]))
    assert bosalt == []
    assert koru[0]["sebep"].startswith("metinde acikca")


def test_hem_kar_paysiz_hem_vade_farksiz_varsa_KORUNUR(metinleri_sabitle):
    """Acik kanit, zayif kanittan once gelir - silme yonunde riske girilmez."""
    metinleri_sabitle({"u1": "0 kar payli kampanya, ayrica vade farksiz 3 taksit"})
    bosalt, koru = etkilenen_satirlar(SahteOturum([SahteSatir(1, 0.0, "u1")]))
    assert bosalt == []


def test_kaynak_metni_olmayan_kayit_SILINMEZ(metinleri_sabitle):
    """Kanit yoksa karar da yok. Kanitsiz silmek veri kaybidir."""
    metinleri_sabitle({})
    bosalt, koru = etkilenen_satirlar(SahteOturum([SahteSatir(1, 0.0, "yok")]))
    assert bosalt == []
    assert "kaynak metin yok" in koru[0]["sebep"]


def test_sebebi_belirlenemeyen_sifir_SILINMEZ(metinleri_sabitle):
    metinleri_sabitle({"u1": "Kampanya kosullari icin subelerimize danisiniz"})
    bosalt, koru = etkilenen_satirlar(SahteOturum([SahteSatir(1, 0.0, "u1")]))
    assert bosalt == []
    assert "belirlenemedi" in koru[0]["sebep"]


def test_sifir_OLMAYAN_oranlara_hic_dokunulmaz(metinleri_sabitle):
    """Sayisal oran yazilmis kayitlar bu betigin konusu degil."""
    metinleri_sabitle({"u1": "vade farksiz 6 taksit"})
    satirlar = [SahteSatir(1, 1.87, "u1"), SahteSatir(2, None, "u1")]
    bosalt, koru = etkilenen_satirlar(SahteOturum(satirlar))
    assert bosalt == []
    assert koru == []


def test_kural_altin_set_tarafiyla_AYNI_nesnedir():
    """Desenler kopyalanmamali, ice aktarilmali.

    Kopyalanirsa iki taraf zamanla ayrisir; DB ile altin set ayni kanit
    icin farkli karar verir. Bu test, kopyalanmis bir desenin sessizce
    eklenmesini imkansiz kilar.
    """
    from gold_dataset import vade_farksiz_duzelt as altin
    from extraction import vade_farksiz_db_duzelt as db

    assert db.RE_VADE_FARKSIZ is altin.RE_VADE_FARKSIZ
    assert db.RE_ACIK_SIFIR is altin.RE_ACIK_SIFIR

"""RAG sonuclarinda site kalibi (menu/cerez/footer) kalmadigini dogrular.

--------------------------------------------------------------------------
NEDEN BU TEST VAR
--------------------------------------------------------------------------
Havin'in 24.08.2026 arayuz raporu Md. 2: "Kuveyt Turk'un konut finansmani
orani ne" sorusuna donen cevap site menusuydu - "Finans Portali Ozel
Bankacilik ... Sube ve ATM'ler Dijital Bankacilik ...". Vektor skorlari
0,17 / 0,13 / 0,08 gibi cok dusuk oldugu halde sistem cevap uretiyordu.

Cekimserlik kurali bunu yakalayamiyordu cunku menu sitedeki HER urunu
listeliyor: "Konut Finansmani" da menude geciyor, "Kuveyt Turk" de - terim
ortusmesi 0,667 cikip 0,60 esigini geciyordu.

Cozum esikte DEGIL, indekste arandi (bkz. chunking/parcalayici.py,
"NAVIGASYON / SITE KALIBI ELEME"): olculen kalibrasyonda cevaplanabilir
sorularin en dususu de 0,667 - esik yukseltilseydi gercek sorular da
cevapsiz kalirdi.

--------------------------------------------------------------------------
OLCULEN SONUC
--------------------------------------------------------------------------
Eleme sonrasi ayni soru artik menu degil, GERCEK Kuveyt Turk konut
finansmani metnini donduruyor ve o metin %1,99 oranini aciken yaziyor -
yani soru cevaplanabilir bir sorudur ve cevaplanmasi DOGRUDUR.

--------------------------------------------------------------------------
BU TEST NEYI KORUR
--------------------------------------------------------------------------
Iki yonu birden - tek yon yaniltir:
  1. Sonuclarda site kalibi olmamali.
  2. Cevaplanabilir sorular HALA cevaplanmali. Yalnizca (1)'i olcmek,
     "her seye bilmiyorum diyen" bir sistemi basarili gosterirdi.

Canli Qdrant + gomme modeli gerektirir; yoksa SKIP eder (CI'da beklenen
durum, test_kampanya_repository.py ile ayni desen).
"""

from __future__ import annotations

import pytest


def _indeks_hazir_mi() -> bool:
    try:
        from chunking.qdrant_baglanti import VARSAYILAN_KOLEKSIYON, qdrant_hazir_mi

        if not qdrant_hazir_mi():
            return False
        from qdrant_client import QdrantClient

        from chunking.qdrant_baglanti import QDRANT_URL

        bilgi = QdrantClient(url=QDRANT_URL).get_collection(VARSAYILAN_KOLEKSIYON)
        return (bilgi.points_count or 0) > 0
    except Exception:  # noqa: BLE001 - erisilemiyorsa test atlanir
        return False


INDEKS_YOK = "Qdrant indeksi yok (docker compose up -d qdrant && python -m chunking.indeksleyici)"

pytestmark = pytest.mark.skipif(not _indeks_hazir_mi(), reason=INDEKS_YOK)

# Kalip metinden gelen, hicbir kampanya bilgisi tasimayan izler.
KALIP_IZLERI = (
    "Öne Çıkan Aramalar",
    "Şube ve ATM'ler",
    "Çerez Ayarları",
    "Faydalı Linkler",
    "Zorunlu Çerezler",
)


def _parca_metinleri(soru: str) -> tuple[list[str], bool]:
    from chunking.retriever import getir

    sonuc = getir(soru)
    metinler = [(p.get("ustveri") or {}).get("metin", "") for p in sonuc.parcalar]
    return metinler, sonuc.yeterli_kaynak_var


@pytest.mark.parametrize(
    "soru",
    [
        "Kuveyt Türk'ün konut finansmanı oranı ne",  # Havin'in bildirdigi soru
        "vade farksız taksit kampanyası var mı",
        "yeni müşterilere özel kampanya",
    ],
)
def test_sonuclarda_site_kalibi_YOK(soru):
    """ASIL DUZELTME: menu artik indekste degil, sonuclara da gelemez."""
    metinler, _ = _parca_metinleri(soru)
    kirli = [m[:90] for m in metinler if any(iz in m for iz in KALIP_IZLERI)]
    assert not kirli, f"Site kalibi iceren parca dondu: {kirli}"


@pytest.mark.parametrize(
    "soru",
    [
        "Kuveyt Türk'ün konut finansmanı oranı ne",
        "vade farksız taksit kampanyası var mı",
        "market harcamalarında nakit iade kampanyası",
        "kredi kartı taksit fırsatı",
    ],
)
def test_cevaplanabilir_sorular_HALA_cevaplaniyor(soru):
    """ASIRI CEKIMSERLIK BEKCISI.

    Kalip elemesi fazla agresif olursa gercek icerik de indeksten dusar ve
    sistem cevaplanabilir sorulara "bilmiyorum" demeye baslar. Bu, menu
    kirliliginden daha kotu bir bozulmadir - bu yuzden ayri olculur.
    """
    _, yeterli = _parca_metinleri(soru)
    assert yeterli, f"Cevaplanabilir soru cekimser kaldi: {soru}"


def test_alan_disi_soru_CEKIMSER_kaliyor():
    """Cekimserlik yetisi elemeden sonra da calisiyor mu?"""
    _, yeterli = _parca_metinleri("uluslararası uzay istasyonu kaç metre")
    assert not yeterli

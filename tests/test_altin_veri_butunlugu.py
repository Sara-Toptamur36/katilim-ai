"""Altin Veri Seti butunlugu (gorev 21 - etiketleme sprinti altyapisi).

Altin Veri Seti, cikarim motorunun OLCULDUGU referanstir. Referansta bir
hata olursa olcum sessizce yanlis cikar ve sebebi motorda aranir - saatler
kaybedilir. Bu testler referansin KENDI tutarliligini korur.

--------------------------------------------------------------------------
KANIT SPANI (evidence span)
--------------------------------------------------------------------------
Bir altin degerin yaninda, o degeri HAKLI CIKARAN kaynak cumlesi durur:

    "vade_ay": 12,
    "kanit_spanlari": {"vade_ay": "12 ay vadeye kadar finansman imkani"}

Neden gerekli: bugun bir deger tartismali oldugunda tek yol bankanin
sayfasini yeniden acmaktir - sayfa degismisse (kampanya rotasyonu)
kanit tamamen kaybolur. Span, etiketleme anindaki gerekceyi DONDURUR.

Bu testler spanin GERCEKTEN kaynak metinde gectigini dogrular; kopyalama
hatasi ya da elle yazilmis "yaklasik" bir cumle sessizce gecemez.

--------------------------------------------------------------------------
KANIT SPANI SU AN ZORUNLU DEGIL
--------------------------------------------------------------------------
58 kaydin spanlari elle doldurulacak (bkz. gold_dataset/
etiketleme_yardimcisi.py --span). Test, span YOKSA sikayet etmez; VARSA
dogru olmasini sart kosar. Zorunlu hale getirmek, doldurma isi bitmeden
CI'i kirmizi birakirdi.
"""

import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
GOLD = KOK / "gold_dataset" / "altin_veri_seti.json"

sys.path.insert(0, str(KOK))

SAHTE_ONEKLER = ("A-", "B-", "C-", "D-")

# Bu alanlar olcume girer (scraper/scripts/extraction_accuracy.py ile ayni
# kume) - kanit spani beklenen alanlar bunlardir.
OLCULEN_ALANLAR = (
    "kar_payi_orani",
    "vade_ay",
    "finansman_tutari",
    "odul_miktari",
    "odul_birimi",
    "taksit_sayisi",
    "erteleme_suresi_ay",
)


@pytest.fixture(scope="module")
def kayitlar():
    with open(GOLD, encoding="utf-8") as f:
        return [k for k in json.load(f) if not k["kayit_id"].startswith(SAHTE_ONEKLER)]


def _ham_metin(kayit: dict) -> str | None:
    """Kaydin kaynak metnini bulur; bulunamazsa None (kampanya rotasyonu -
    sayfa siteden kaldirilmis olabilir)."""
    from scraper.scripts.gold_eslesme import scraper_kaydini_bul

    try:
        eslesen = scraper_kaydini_bul(kayit)
    except Exception:  # noqa: BLE001 - eslesme yoksa test atlanir, patlamaz
        return None
    if not eslesen:
        return None
    return eslesen.get("normalize_metin") or eslesen.get("ham_metin") or ""


# ---------------------------------------------------------------------------
# Null-negatif tutarliligi
# ---------------------------------------------------------------------------


def test_bos_isaretli_alanin_degeri_DOLU_OLAMAZ(kayitlar):
    """`alan_belirtilmemis[x] = true` "kaynakta yok" demektir. Deger ayni
    anda dolu ise ikisinden biri yanlistir ve olcum bunu FARK ETMEZ:
    dolu deger dogru sayilir, bayrak da bos-alan dogruluguna girer."""
    ihlaller = [
        (k["kayit_id"], alan, k.get(alan))
        for k in kayitlar
        for alan, isaret in (k.get("alan_belirtilmemis") or {}).items()
        if isaret and k.get(alan) not in (None, "", [])
    ]
    assert not ihlaller, f"bayrak 'bos' diyor ama deger dolu: {ihlaller}"


def test_alan_belirtilmemis_yalnizca_bool_tasir(kayitlar):
    """Metin/None gibi degerler sessizce "truthy" davranip bos alan
    olcumunu bozardi."""
    for k in kayitlar:
        for alan, isaret in (k.get("alan_belirtilmemis") or {}).items():
            assert isinstance(isaret, bool), f"{k['kayit_id']}.{alan} = {isaret!r}"


# ---------------------------------------------------------------------------
# Kanit spani
# ---------------------------------------------------------------------------


def test_kanit_spani_kaynak_metinde_GERCEKTEN_geciyor(kayitlar):
    """Span varsa, kaynak metinde birebir bulunmali.

    Kopyalama hatasi ya da elle "ozetlenmis" bir cumle, sonradan
    dogrulanamayan bir gerekce demektir - referansin degerini yok eder.
    """
    from extraction.normalizer import turkce_ascii_kucult

    hatalar: list[str] = []
    kontrol_edilen = 0

    for k in kayitlar:
        spanlar = k.get("kanit_spanlari") or {}
        if not spanlar:
            continue
        metin = _ham_metin(k)
        if metin is None:
            continue  # sayfa artik yok - bu testin konusu degil
        katlanmis = turkce_ascii_kucult(metin)
        for alan, span in spanlar.items():
            if not span:
                continue
            kontrol_edilen += 1
            if turkce_ascii_kucult(span) not in katlanmis:
                hatalar.append(f"{k['kayit_id']}.{alan}: {span[:60]!r}")

    assert not hatalar, (
        f"{len(hatalar)} kanit spani kaynak metinde bulunamadi "
        f"({kontrol_edilen} span kontrol edildi): " + "; ".join(hatalar[:5])
    )


def test_kanit_spani_yalnizca_DOLU_alanlara_verilir(kayitlar):
    """Bos bir alanin kaniti olamaz: "kaynakta yok" iddiasinin kaniti,
    metinde bir cumle GOSTERMEK degil, gosterememektir."""
    hatalar = [
        f"{k['kayit_id']}.{alan}"
        for k in kayitlar
        for alan, span in (k.get("kanit_spanlari") or {}).items()
        if span and k.get(alan) in (None, "", [])
    ]
    assert not hatalar, f"bos alana kanit spani verilmis: {hatalar}"


def test_kanit_spani_bilinen_alanlara_ait(kayitlar):
    """Yazim hatasi bir spani sessizce olcum disi birakirdi."""
    bilinen = set(OLCULEN_ALANLAR) | {"masraf_durumu", "kampanya_bitis", "hedef_kitle"}
    hatalar = [
        f"{k['kayit_id']}.{alan}"
        for k in kayitlar
        for alan in (k.get("kanit_spanlari") or {})
        if alan not in bilinen
    ]
    assert not hatalar, f"taninmayan alan adi: {hatalar}"


# ---------------------------------------------------------------------------
# Sprint takibi - "kac kayit kaldi" sorusu olculebilir olmali
# ---------------------------------------------------------------------------


def test_sprint_ilerlemesi_raporlanir(kayitlar, capsys):
    """Bu test hicbir sey DOGRULAMAZ; sprint ilerlemesini gorunur kilar.
    Hedef 200-300 kayit (gorev 21) ve nerede oldugumuz her kosuda yazilir."""
    spani_olan = sum(1 for k in kayitlar if k.get("kanit_spanlari"))
    with capsys.disabled():
        print(
            f"\n  Altin Veri Seti: {len(kayitlar)} kayit "
            f"(hedef 200-300) | kanit spani girilmis: {spani_olan}"
        )
    assert kayitlar, "altin veri seti bos olamaz"

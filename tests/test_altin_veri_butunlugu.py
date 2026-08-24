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
    # TEK KAYNAK: bosluk toleransinin tanimi excel_to_json'da durur;
    # burada kopyalanirsa iki yerde ayrisir ve testin kabul ettigiyle
    # uretimin kabul ettigi sey birbirinden kayar.
    from gold_dataset.excel_to_json import span_metinde_var

    hatalar: list[str] = []
    kontrol_edilen = 0

    for k in kayitlar:
        spanlar = k.get("kanit_spanlari") or {}
        if not spanlar:
            continue
        metin = _ham_metin(k)
        if metin is None:
            continue  # sayfa artik yok - bu testin konusu degil
        for alan, span in spanlar.items():
            if not span:
                continue
            kontrol_edilen += 1
            if not span_metinde_var(span, metin):
                hatalar.append(f"{k['kayit_id']}.{alan}: {span[:60]!r}")

    assert not hatalar, (
        f"{len(hatalar)} kanit spani kaynak metinde bulunamadi "
        f"({kontrol_edilen} span kontrol edildi): " + "; ".join(hatalar[:5])
    )


def test_kaynak_url_kampanya_sayfasini_gosterir(kayitlar):
    """Her kayit KENDI kampanya sayfasini gostermeli - liste sayfasini degil.

    Rehber E sutunu: "Kampanyanin TAM adresi (ana sayfa degil)". Denetimde
    uc kayit (TOM-001/002/003) ayni adresi gosteriyordu:
    tombank.com.tr/kampanyalar.html. TOM Bank kampanyalarini tek sayfada
    anchor olarak yayimliyor; scraper fragment'i dogru yakalamisti ama
    altin sete yazilirken dusmustu.

    Iki sonucu vardi: kayitlar mukerrer gorunuyordu ve split kaynak_url'ye
    gore grupladigi icin ucu tek grup sayiliyordu.
    """
    from collections import Counter

    urller = [
        (k["kayit_id"], (k.get("kaynak_url") or "").rstrip("/"))
        for k in kayitlar
        if k.get("kaynak_url")
    ]

    sayim = Counter(u for _kid, u in urller)
    mukerrer = {u: n for u, n in sayim.items() if n > 1}
    assert not mukerrer, (
        "ayni kaynak_url birden fazla kayitta - muhtemelen liste sayfasi "
        f"yazilmis, kampanyanin kendi adresi degil: {mukerrer}"
    )


def test_kanit_spani_ALANIN_DEGERINI_destekliyor(kayitlar):
    """Span kaynakta gecmesi YETMEZ - o alanin DEGERINI de icermeli.

    Ustteki test spanin kaynakta bulundugunu dogrular; bu test spanin
    DOGRU cumle oldugunu dogrular. Aradaki fark halusinasyonun saklandigi
    yerdir: kaynaktan alinmis ama ILGISIZ bir cumle ustteki testi gecer,
    cunku metinde gercekten vardir. Denetimde boyle bir kayit bulundu -
    TF-010'un tarih spani, tarih GECMEYEN bir cumleydi; kayit "kanitli"
    gorunuyordu ama kanit baska bir seyi soyluyordu.

    Yalnizca sayisal ve tarih alanlari kontrol edilir; hedef_kitle gibi
    serbest metin alanlarinda etiket bir insan ozetidir ve kaynakta
    birebir gecmez.
    """
    from gold_dataset.excel_to_json import span_metinde_var
    from gold_dataset.kanit_spani_oner import _sayi_bicimleri, _tarih_bicimleri

    SAYISAL = {"kar_payi_orani", "maliyet_orani", "vade_ay", "finansman_tutari",
               "odul_miktari", "taksit_sayisi", "erteleme_suresi_ay"}
    TARIH = {"kampanya_baslangic", "kampanya_bitis"}

    def aralik_destekliyor(deger: str, span: str) -> bool:
        """'1-30 Haziran 2026' iki ucu da destekler; tam tarih kaliplari
        boyle bir spanla eslesmez, bu yuzden ayrica bakilir."""
        from gold_dataset.tarih_celiskisi_raporu import _araliklari_cikar

        return any(
            deger in (a["baslangic"], a["bitis"]) for a in _araliklari_cikar(span)
        )

    hatalar = []
    for k in kayitlar:
        for alan, span in (k.get("kanit_spanlari") or {}).items():
            deger = k.get(alan)
            if deger is None or not span:
                continue
            if alan in TARIH:
                if aralik_destekliyor(str(deger), span):
                    continue
                bicimler = _tarih_bicimleri(str(deger))
            elif alan in SAYISAL:
                bicimler = _sayi_bicimleri(deger)
            else:
                continue
            if bicimler and not any(span_metinde_var(b, span) for b in bicimler):
                hatalar.append(f"{k['kayit_id']}.{alan}={deger!r} span={span[:50]!r}")

    assert not hatalar, (
        f"{len(hatalar)} kanit spani, dayandigi alanin degerini icermiyor: "
        + "; ".join(hatalar[:5])
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
    """Yazim hatasi bir spani sessizce olcum disi birakirdi.

    IZINLI ALAN LISTESI TEK YERDE: excel_to_json.py. Ilk surumde bu test
    kendi kopyasini tutuyordu ve listeler AYRISTI - Excel'in kabul ettigi
    `kampanya_baslangic` burada "taninmayan alan" sayildi. Kopya liste,
    ayni kurali iki yerde tutmanin klasik bedelidir.
    """
    from gold_dataset.excel_to_json import SPAN_VERILEBILIR_ALANLAR

    bilinen = SPAN_VERILEBILIR_ALANLAR
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
    Hedef 200-300 kayit (gorev 21) ve nerede oldugumuz her kosuda yazilir.

    IMZALI VE TASLAK AYRI SAYILIR: kuyruktan acilan taslak satirlar da bu
    dosyada durur ama hicbiri olcume girmez. Tek sayida birlestirmek
    "303 kayit (hedef 200-300)" gibi HEDEFE ULASILMIS gorunen bir satir
    uretiyordu - oysa imzali kayit 103'tu."""
    imzali = [k for k in kayitlar if (k.get("giren_kisi") or "").strip()]
    taslak = [k for k in kayitlar if not (k.get("giren_kisi") or "").strip()]
    spani_olan = sum(1 for k in imzali if k.get("kanit_spanlari"))
    with capsys.disabled():
        print(
            f"\n  Altin Veri Seti: {len(imzali)} IMZALI kayit (hedef 200-300)"
            f" | kanit spani girilmis: {spani_olan}"
            f"\n  Kuyrukta bekleyen taslak: {len(taslak)} (olcum disi)"
        )
    assert kayitlar, "altin veri seti bos olamaz"

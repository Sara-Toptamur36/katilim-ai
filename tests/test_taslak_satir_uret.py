"""gold_dataset/taslak_satir_uret.py testleri.

Bu betik altin veri setine SATIR ACAR. Yanlis calisirsa olculen referansi
kirletir; testler bu yuzden once "ne YAZMADIGINA" bakar.
"""

import json
import re
from pathlib import Path

import pytest

from gold_dataset.taslak_satir_uret import (
    BANKA_ONEKLERI,
    YAZILMAYAN_ALANLAR,
    _sonraki_idler,
    taslaklari_planla,
)

_GOLD_DOSYASI = (
    Path(__file__).resolve().parent.parent / "gold_dataset" / "altin_veri_seti.json"
)


def _gold():
    with open(_GOLD_DOSYASI, encoding="utf-8") as f:
        return json.load(f)


def test_olculen_alanlar_asla_planlanmaz():
    """EN KRITIK TEST - dairesellik yasagi.

    Altin set, cikarim motorunun kendisine karsi olculdugu referanstir.
    Bu betik olculen bir alani doldursaydi motor kendi turunden bir
    ciktiya karsi olculmus olurdu (Calisma Rehberi, Kural 5)."""
    for satir in taslaklari_planla(sayi=5):
        yazilan = {a for a in satir if not a.startswith("_")}
        assert not (yazilan & YAZILMAYAN_ALANLAR), (
            f"olculen alan planlanmis: {yazilan & YAZILMAYAN_ALANLAR}"
        )


def test_giren_kisi_planlanmaz():
    """Imza bir iddiadir (Kural 3) - betik kimse adina iddia edemez."""
    for satir in taslaklari_planla(sayi=5):
        assert "giren_kisi" not in satir


def test_kayit_id_mevcutlarla_cakismaz():
    """Kural 6: ayni ID iki kez kullanilirsa donusturme hata verir."""
    mevcut = {k["kayit_id"] for k in _gold()}
    uretilen = [s["kayit_id"] for s in taslaklari_planla(sayi=15)]

    assert not (set(uretilen) & mevcut), "mevcut bir ID yeniden uretilmis"
    assert len(uretilen) == len(set(uretilen)), "ayni ID iki kez uretilmis"


def test_kayit_id_bankanin_onekini_tasir():
    for satir in taslaklari_planla(sayi=15):
        onek = BANKA_ONEKLERI[satir["banka"]]
        assert satir["kayit_id"].startswith(f"{onek}-"), satir["kayit_id"]


def test_kayit_id_en_buyuk_numaradan_devam_eder():
    """Bosluk doldurulmaz: silinmis bir kaydin ID'sini yeniden kullanmak,
    o ID'ye atifta bulunan eski notlarla karismaya yol acar."""
    en_buyuk = _sonraki_idler(_gold())
    for satir in taslaklari_planla(sayi=15):
        onek, no = re.fullmatch(r"([A-Z]+)-(\d+)", satir["kayit_id"]).groups()
        assert int(no) > en_buyuk.get(onek, 0)


def test_altin_sette_zaten_olan_url_planlanmaz():
    mevcut_urller = {(k.get("kaynak_url") or "").rstrip("/") for k in _gold()}
    for satir in taslaklari_planla(sayi=30):
        assert satir["kaynak_url"].rstrip("/") not in mevcut_urller


def test_planlama_gold_dosyasini_degistirmez():
    """--yaz denmeden hicbir dosyaya dokunulmaz."""
    onceki = _GOLD_DOSYASI.read_bytes()
    taslaklari_planla(sayi=10)
    assert _GOLD_DOSYASI.read_bytes() == onceki


def test_banka_suzgeci_yalnizca_o_bankayi_dondurur():
    """Suzgec, istenen banka disinda satir uretmemeli.

    KUYRUGUN DOLU OLDUGU VARSAYILMAZ: burada once `assert plan` vardi ve
    kuyruktaki 200 adayin tamami acildiginda test kirildi - oysa "aday
    kalmadi" bir hata degil, kuyrugun bitmis olmasidir. Testin isi
    suzgecin dogru suzmesi; kac aday kaldigi ayri bir sorudur."""
    hepsi = taslaklari_planla(sayi=5)
    if not hepsi:
        pytest.skip("kuyrukta acilmamis aday kalmadi - suzulecek sey yok")

    banka = hepsi[0]["banka"]
    plan = taslaklari_planla(sayi=5, banka_suzgeci=banka)
    assert plan, f"{banka} suzgecte kayboldu ama suzgecsiz listede vardi"
    assert all(s["banka"] == banka for s in plan)


def test_acilmis_satir_yeniden_planlanmaz():
    """Ayni aday iki kez acilmamali - Excel'de mukerrer ID'ye yol acardi.

    Kuyruk tukendiginde bos liste doner; bu dogru davranistir."""
    mevcut_urller = {(k.get("kaynak_url") or "").rstrip("/") for k in _gold()}
    plan = taslaklari_planla(sayi=250)
    yeniden_acilan = [s for s in plan
                      if s["kaynak_url"].rstrip("/") in mevcut_urller]
    assert not yeniden_acilan, f"zaten acilmis satir yeniden planlandi: {yeniden_acilan}"

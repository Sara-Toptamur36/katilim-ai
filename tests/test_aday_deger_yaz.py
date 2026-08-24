"""gold_dataset/aday_deger_yaz.py testleri.

Bu betik altin veri setine deger yazar - yani hatasi dogrudan olculen
referansa sizar. Testler "calisiyor mu"dan cok "yazmamasi gerekeni
yaziyor mu"ya bakar.
"""

import json
from pathlib import Path

from gold_dataset.aday_deger_yaz import IZINLI_ALANLAR, YASAK_SUTUNLAR, dogrula

_GOLD_DOSYASI = (
    Path(__file__).resolve().parent.parent / "gold_dataset" / "altin_veri_seti.json"
)


def _gold() -> list[dict]:
    with open(_GOLD_DOSYASI, encoding="utf-8") as f:
        return json.load(f)


def _bir_taslak_id() -> str | None:
    for k in _gold():
        if not (k.get("giren_kisi") or "").strip() and k.get("giren_kisi") != "ORNEK":
            return k["kayit_id"]
    return None


def test_imza_sutunu_asla_izinli_degil():
    """Kural 3: imza bir iddiadir - betik kimse adina iddia edemez."""
    assert "giren_kisi" in YASAK_SUTUNLAR
    assert "giren_kisi" not in IZINLI_ALANLAR


def test_span_yazilan_alanlar_excel_to_json_ile_uyumlu():
    """Bu betigin span yazdigi her alan, donusturucunun de TANIDIGI bir
    alan olmali.

    Olculdu: `oran_periyodu` icin span yaziliyordu ama
    SPAN_VERILEBILIR_ALANLAR listesinde olmadigi icin her donusturmede
    'kanit_spanlari'nda taninmayan alan' uyarisi cikiyordu. Uyarilar
    birikince gercek sorunlar gorunmez hale gelir."""
    from gold_dataset.aday_deger_yaz import SPAN_ISTEMEYEN
    from gold_dataset.excel_to_json import SPAN_VERILEBILIR_ALANLAR

    span_yazilanlar = IZINLI_ALANLAR - SPAN_ISTEMEYEN
    taninmayan = span_yazilanlar - SPAN_VERILEBILIR_ALANLAR
    assert not taninmayan, (
        f"bu alanlara span yaziliyor ama excel_to_json tanimiyor: "
        f"{sorted(taninmayan)} - ya SPAN_ISTEMEYEN'e ekleyin ya da "
        "SPAN_VERILEBILIR_ALANLAR'a"
    )


def test_kaynakta_bulunmayan_span_degeri_reddeder():
    """SPAN ZORUNLULUGU - betigin asil koruma mekanizmasi.

    Uydurulmus ya da hatirlanmis bir deger kaynak cumleye baglanamaz;
    baglanamayan deger dosyaya giremez."""
    taslak = _bir_taslak_id()
    if taslak is None:
        return  # kuyrukta taslak kalmamis

    kabul, ret = dogrula([{
        "kayit_id": taslak,
        "alanlar": {"vade_ay": 12},
        "spanlar": {"vade_ay": "bu cumle hicbir kaynakta gecmiyor xyzzy"},
    }])
    assert all(not k["alanlar"] for k in kabul), "uydurma spanli deger kabul edildi"
    assert any("span kaynakta bulunamadi" in r for r in ret)


def test_spansiz_sayisal_deger_reddedilir():
    taslak = _bir_taslak_id()
    if taslak is None:
        return

    kabul, ret = dogrula([{
        "kayit_id": taslak,
        "alanlar": {"kar_payi_orani": 2.99},
        "spanlar": {},
    }])
    assert all(not k["alanlar"] for k in kabul)
    assert any("span verilmedi" in r for r in ret)


def test_imzali_kayda_dokunulmaz():
    """Insan imzalamis bir satiri makine adayi ezemez."""
    imzalilar = [k for k in _gold()
                 if (k.get("giren_kisi") or "").strip()
                 and k.get("giren_kisi") != "ORNEK"]
    if not imzalilar:
        return

    hedef = imzalilar[0]["kayit_id"]
    kabul, ret = dogrula([{
        "kayit_id": hedef,
        "alanlar": {"vade_ay": 99},
        "spanlar": {"vade_ay": "herhangi bir cumle"},
    }])
    assert not kabul, "imzali kayit icin aday kabul edildi"
    assert any("IMZALI kayit" in r for r in ret)


def test_izinsiz_alan_reddedilir():
    taslak = _bir_taslak_id()
    if taslak is None:
        return

    kabul, ret = dogrula([{
        "kayit_id": taslak,
        "alanlar": {"giren_kisi": "Birisi", "kayit_id": "XX-999"},
        "spanlar": {},
    }])
    assert all(not k["alanlar"] for k in kabul)
    assert any("bu sutuna yazilmaz" in r for r in ret)


def test_dogrulama_dosyaya_dokunmaz():
    """dogrula() yalnizca okur; yazma islemi ayri bir adimdir."""
    onceki = _GOLD_DOSYASI.read_bytes()
    dogrula([{"kayit_id": "YOK-999", "alanlar": {}, "spanlar": {}}])
    assert _GOLD_DOSYASI.read_bytes() == onceki


def test_makine_adaylari_olcume_girmez():
    """EN KRITIK: aday deger tasiyan hicbir kayit olcume girmemeli.

    Bu betikle doldurulmus bir satir, insan imzalayana kadar
    alan_belirtilmemis bayragi tasimaz - yani cikarim motoru o satirda
    ne uretirse uretsin ne odul ne ceza alir."""
    for kayit in _gold():
        imzasiz = not (kayit.get("giren_kisi") or "").strip()
        if imzasiz and kayit.get("giren_kisi") != "ORNEK":
            assert kayit.get("alan_belirtilmemis") == {}, (
                f"{kayit['kayit_id']}: imzasiz kayit olcume girmis"
            )


def test_yazilan_spanlarin_hepsi_butunluk_testinden_gecer():
    """Betigin kabul ettigi span, butunluk testinin de kabul ettigi span
    olmali.

    Olculdu: betik _ham_kampanyalar() ile EN GUNCEL snapshot'a bakiyordu,
    tests/test_altin_veri_butunlugu.py ise scraper_kaydini_bul ile baska
    bir snapshot'a. TEK-025'te betik span'i kabul etti, butunluk testi
    ayni span'i reddetti. Iki taraf ayni cozumleyiciyi kullanmazsa bu
    kacinilmazdir; bu test kaymayi erken yakalar."""
    from gold_dataset.excel_to_json import span_metinde_var
    from gold_dataset.aday_deger_yaz import DAMGA
    from scraper.scripts.gold_eslesme import scraper_kaydini_bul

    hatalar = []
    for kayit in _gold():
        if DAMGA not in (kayit.get("notlar") or ""):
            continue
        spanlar = kayit.get("kanit_spanlari") or {}
        if not spanlar:
            continue
        try:
            eslesen = scraper_kaydini_bul(kayit) or {}
        except Exception:  # noqa: BLE001
            continue
        metin = eslesen.get("normalize_metin") or eslesen.get("ham_metin") or ""
        if not metin:
            continue
        for alan, span in spanlar.items():
            if span and not span_metinde_var(span, metin):
                hatalar.append(f"{kayit['kayit_id']}.{alan}")

    assert not hatalar, (
        f"makine adayi spani butunluk testinin kaynaginda bulunamadi: {hatalar}"
    )


def test_makine_adayi_damgasi_gorunur():
    """Aday deger tasiyan satir, notlar sutunundan taninabilmeli.

    Damga olmasa, sonradan bakan biri bu degerlerin insan tarafindan mi
    yoksa makine tarafindan mi girildigini ayirt edemezdi."""
    from gold_dataset.aday_deger_yaz import DAMGA

    damgalilar = [k for k in _gold() if DAMGA in (k.get("notlar") or "")]
    for kayit in damgalilar:
        assert not (kayit.get("giren_kisi") or "").strip(), (
            f"{kayit['kayit_id']}: makine adayi damgali ama IMZALI - "
            "imzalayan kisi damgayi kaldirmali"
        )

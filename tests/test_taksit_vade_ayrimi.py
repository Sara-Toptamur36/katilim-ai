"""taksit_sayisi ile vade_ay ayrimi (gold_dataset/excel_to_json.py).

Sentetik kayitlarla calisir - altin veri setinin ICERIGINE bakmaz.
Sebep: bu uyari su an 8 gercek kaydi isaretliyor; ekip onlari kaynagina
bakip duzeltince test kirilmamali. Testin isi kuralin KENDISIDIR, o
anki ihlal sayisi degil.
"""

from gold_dataset.excel_to_json import _taksit_vade_karisikligi


def _kayit(**k):
    return {"kampanya_adi": "", "vade_ay": None, "taksit_sayisi": None, **k}


def test_adda_taksit_var_deger_vade_ayda_ise_UYARIR():
    u = _taksit_vade_karisikligi(
        _kayit(kampanya_adi="MTV Ödemelerinde Vade Farksız 3 Taksit", vade_ay=3), "VK-001"
    )
    assert len(u) == 1 and "vade_ay=3" in u[0]


def test_aya_varan_taksit_kalibi_da_yakalanir():
    u = _taksit_vade_karisikligi(
        _kayit(kampanya_adi="Hepsiburada'da Peşin Fiyatına 9 Aya Varan Taksit", vade_ay=9),
        "DK-006",
    )
    assert len(u) == 1


def test_deger_dogru_alandaysa_SUSAR():
    """AL-002 boyle: ad '3 Taksit', deger taksit_sayisi=3. Dogru kayit
    uyari uretmemeli - yoksa uyari listesi gurultuye bogulur ve okunmaz."""
    u = _taksit_vade_karisikligi(
        _kayit(kampanya_adi="MTV Ödemelerinize Vade Farksız 3 Taksit", taksit_sayisi=3),
        "AL-002",
    )
    assert u == []


def test_sayilar_TUTMUYORSA_susar():
    """Ad '3 Taksit' ama vade_ay=12 ise bu karisiklik degil; kampanya
    hem 3 taksit hem 12 ay vade tasiyor olabilir. Uydurma uyari,
    gercek uyariyi golgeler."""
    u = _taksit_vade_karisikligi(
        _kayit(kampanya_adi="Vade Farksız 3 Taksit", vade_ay=12), "X-001"
    )
    assert u == []


def test_adda_taksit_yoksa_susar():
    """KT-001 'Alisveris Finansmani' boyle: vade_ay=6 pekala gercek bir
    finansman vadesi olabilir. Ad kanit sunmuyorsa kod susar."""
    u = _taksit_vade_karisikligi(
        _kayit(kampanya_adi="Taksitlio'da Yeni Müşterilere Özel Finansman", vade_ay=6),
        "KT-001",
    )
    assert u == []


def test_ikisi_de_doluysa_susar():
    """Etiketleyici iki alani da bilerek doldurmussa karar verilmis
    demektir; uyari onu geri cevirmez."""
    u = _taksit_vade_karisikligi(
        _kayit(kampanya_adi="Vade Farksız 3 Taksit", vade_ay=3, taksit_sayisi=3), "X-002"
    )
    assert u == []


# ---------------------------------------------------------------------------
# TARIH BEKCISI
# ---------------------------------------------------------------------------
# "Kaynakta yok" bir IDDIADIR ve kaynaga sorulabilir. Bu kor nokta iki kez
# isirdi: Ziraat "Kampanya Donemi", Vakif "Kampanya Gecerlilik Tarihi"
# diyor; ikisi de gozden kacti ve TF-005'in notunda "bitis tarihi sayfada
# belirtilmemis" yaziyordu - oysa yaziyordu.


def test_tarih_bekcisi_SESSIZCE_atlanmaz():
    """En tehlikeli hali: kontrol calismiyor ama cikti 'Uyari yok' diyor.

    Olculdu: betik `python gold_dataset/excel_to_json.py` seklinde
    calistirildiginda sys.path[0] repo koku degil gold_dataset/ olur;
    ilk surum ImportError'i sessizce yutup [] donuyordu. Kontrol hic
    calismadan her sey yolunda GORUNUYORDU.
    """
    from gold_dataset.excel_to_json import tarih_bekcisi

    # Kaynagi olan, tarihi DOLU bir kayit uyari uretmemeli...
    import json
    from pathlib import Path

    kok = Path(__file__).resolve().parent.parent
    with open(kok / "gold_dataset" / "altin_veri_seti.json", encoding="utf-8") as f:
        kayitlar = json.load(f)

    # ...ama ayni kaydin tarihleri BOSALTILIRSA uretmeli.
    hedef = next(k for k in kayitlar
                 if k["kayit_id"] == "VK-009")
    bosaltilmis = [dict(hedef, kampanya_baslangic=None, kampanya_bitis=None)]
    uyarilar = tarih_bekcisi(bosaltilmis)
    assert any("VK-009" in u for u in uyarilar), (
        "tarih bekcisi calismiyor ya da sessizce atlaniyor: " + str(uyarilar))
    assert not any("ATLANDI" in u for u in uyarilar), (
        "kontrol atlandi - modul/korpus yuklenememis: " + str(uyarilar))


def test_tarih_bekcisi_CEREZ_metnini_saymaz():
    """Cerez politikasindaki tarih kampanya tarihi degildir.

    Olculdu: Dunya Katilim sayfalarinda "17/08/2026" cerez aciklamasindan
    geliyor ve DK-001 ile DK-004'te KALICI yanlis alarm uretiyordu.
    Surekli uyaran bir kontrol okunmaz hale gelir.
    """
    from gold_dataset.excel_to_json import _tarih_izi

    cerez = ("Kalici cerez, tarayici kapandiktan sonra belirli bir sona erme "
             "tarihine kadar kalici olan cerez turudur. 17/08/2026")
    assert _tarih_izi(cerez) == [], "cerez metnindeki tarih sayilmis"

    gercek = "Kampanya Gecerlilik Tarihi 22 Nisan 2026 - 31 Aralık 2026"
    assert _tarih_izi(gercek), "gercek kampanya tarihi kacirildi"

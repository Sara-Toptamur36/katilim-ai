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

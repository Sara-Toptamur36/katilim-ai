"""gold_dataset/tarih_celiskisi_raporu.py testleri.

Bu arac bir ONERI uretir ve onerisi insan eliyle altin veri setine
girebilir - yani hatasi dogrudan olculen referansa sizar. Testler bu
yuzden "calisiyor mu"dan cok "yanlis deger uretiyor mu"ya bakar.
"""

import json
from pathlib import Path

from gold_dataset.tarih_celiskisi_raporu import _araliklari_cikar, celiskileri_bul

_GOLD_DOSYASI = (
    Path(__file__).resolve().parent.parent / "gold_dataset" / "altin_veri_seti.json"
)


def test_ay_adi_dogru_numaraya_cevrilir():
    """REGRESYON - bir kez yanlis uretildi.

    TR_AY_ADLARI 12 degil 18 elemanlidir (Turkce karakterli ve
    karaktersiz yazimlar ayri durur). Ay numarasi enumerate() ile
    verildiginde Agustos 10. ay oluyordu ve arac "1 Agustos - 31 Agustos
    2026" cumlesinden 2026-10-01 .. 2026-10-31 uretiyordu. Bu deger
    Excel'e gecseydi altin set sessizce bozulurdu."""
    araliklar = _araliklari_cikar(
        "Kampanya 1 Ağustos - 31 Ağustos 2026 tarihleri arasında geçerlidir.")
    assert araliklar, "aralik hic bulunamadi"
    assert araliklar[0]["baslangic"] == "2026-08-01"
    assert araliklar[0]["bitis"] == "2026-08-31"


def test_turkce_karaktersiz_ay_adi_da_cevrilir():
    """Bazi sayfalar 'Agustos' yaziyor - ayni ay."""
    araliklar = _araliklari_cikar("Kampanya 1 Agustos - 31 Agustos 2026 arasinda")
    assert araliklar[0]["baslangic"] == "2026-08-01"
    assert araliklar[0]["bitis"] == "2026-08-31"


def test_farkli_aylardan_olusan_aralik():
    araliklar = _araliklari_cikar("Kampanya Dönemi: 16 Haziran - 31 Ağustos 2026")
    assert araliklar[0]["baslangic"] == "2026-06-16"
    assert araliklar[0]["bitis"] == "2026-08-31"


def test_gun_gun_ay_yil_kalibi():
    """'1-31 Ağustos 2026' - tek ay adi, iki gun."""
    araliklar = _araliklari_cikar("Kampanya 1-31 Ağustos 2026 tarihleri arasında geçerlidir.")
    assert araliklar[0]["baslangic"] == "2026-08-01"
    assert araliklar[0]["bitis"] == "2026-08-31"


def test_noktali_tam_tarih_araligi():
    """Tek ve cift basamakli gun karisik yazilabiliyor: '1.01.2027'."""
    araliklar = _araliklari_cikar("13.08.2024 - 1.01.2027")
    assert araliklar[0]["baslangic"] == "2024-08-13"
    assert araliklar[0]["bitis"] == "2027-01-01"


def test_cerez_metnindeki_tarih_aday_sayilmaz():
    """Cerez/gizlilik metnindeki tarih kampanya donemi degildir."""
    metin = ("Çerez politikamız 1 Ocak - 31 Ocak 2026 tarihleri arasında "
             "güncellenmiştir. Tarayıcı ayarlarınızdan çerezleri yönetebilirsiniz.")
    assert _araliklari_cikar(metin) == []


def test_taninmayan_ay_adi_aday_uretmez():
    """Ay adi cozulemezse SESSIZCE YANLIS deger uretmek yerine hic aday
    uretilmez - insan cumleyi kendisi okur."""
    assert _araliklari_cikar("Kampanya 1 Zilhicce - 31 Zilhicce 2026 arasında") == []


def test_rapor_gold_dosyasini_degistirmez():
    """DAVRANIS SOZLESMESI: bu arac yalnizca okur.

    Onerdigi degeri kendisi yazsaydi, olculen referans arac ciktisiyla
    dolar ve motor kendi ciktisina karsi olculmus olurdu (dairesellik)."""
    onceki = _GOLD_DOSYASI.read_bytes()
    celiskileri_bul()
    assert _GOLD_DOSYASI.read_bytes() == onceki


def test_celiskiler_gercek_kayitlara_isaret_eder():
    """Uretilen her celiski gercek bir kayit_id tasimali."""
    with open(_GOLD_DOSYASI, encoding="utf-8") as f:
        gecerli_idler = {k["kayit_id"] for k in json.load(f)}

    for celiski in celiskileri_bul():
        assert celiski["kayit_id"] in gecerli_idler
        assert celiski["kaynakta_bulunamayan"], "bos celiski uretilmis"


def test_kayit_suzgeci_calisir():
    hepsi = celiskileri_bul()
    if not hepsi:
        return  # celiski kalmadiysa suzgec test edilecek bir sey yok
    hedef = hepsi[0]["kayit_id"]
    suzulmus = celiskileri_bul({hedef})
    assert [c["kayit_id"] for c in suzulmus] == [hedef]

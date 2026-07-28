"""Terminoloji sozlugu ve genisletme servisi testleri (Sprint 1, Gun 2-3)."""

from terminology.genisletme import benzer_terim_bul
from terminology.sozluk import gelenek_karsiligi_bul, sema_alanlarini_bul, sozluk_yukle

# Sartname Bolum 5.5'te gecen zorunlu kavramlar
ZORUNLU_KAVRAMLAR = {
    "kar_payi_orani": "Kâr Payı Oranı",
    "finansman_maliyeti": "Finansman Maliyeti",
    "katilim_fonu": "Katılım Fonu",
    "masrafsiz_finansman": "Masrafsız Finansman",
    "avantajli_finansman": "Avantajlı Finansman",
}

# On Degerlendirme Raporu Bolum 3'teki 3 somut ornekten 2 tanesi
# (standart yuzde ornegi zaten kar_payi_orani'nin kendi varyantlarinda var)
RAPOR_BOLUM3_KAVRAMLARI = {
    "kesirli_kar_paylasimi": "Kesirli Kâr Paylaşım Oranı",  # Vakif Katilim "98/2" ornegi
    "sifir_oran_ifadesi": "Niteliksel Sıfır Oran İfadesi",  # Albaraka "Kar payi yok" ornegi
}


def test_sartname_kavramlari_sozlukte_var():
    sozluk = sozluk_yukle()
    for anahtar, standart_terim in ZORUNLU_KAVRAMLAR.items():
        assert anahtar in sozluk, f"{anahtar} sozlukte eksik"
        assert sozluk[anahtar]["standart_terim"] == standart_terim
        assert sozluk[anahtar]["gelenek_karsilik"]
        assert len(sozluk[anahtar]["varyantlar"]) > 0


def test_rapor_bolum3_ornekleri_sozlukte_var():
    sozluk = sozluk_yukle()
    for anahtar, standart_terim in RAPOR_BOLUM3_KAVRAMLARI.items():
        assert anahtar in sozluk, f"{anahtar} sozlukte eksik"
        assert sozluk[anahtar]["standart_terim"] == standart_terim
        assert len(sozluk[anahtar]["varyantlar"]) > 0
        assert "ornek_kaynak" in sozluk[anahtar]


def test_gelenek_karsiligi_bul():
    assert gelenek_karsiligi_bul("kar_payi_orani") == "Faiz Oranı"
    assert gelenek_karsiligi_bul("olmayan_bir_anahtar") is None


def test_sema_alanlarini_bul():
    assert "kar_payi_orani_percent" in sema_alanlarini_bul("kar_payi_orani")
    assert "kar_payi_orani_decimal" in sema_alanlarini_bul("kar_payi_orani")
    assert sema_alanlarini_bul("olmayan_bir_anahtar") == []


def test_benzer_terim_bul_tam_eslesme():
    anahtar, skor = benzer_terim_bul("masrafsiz finansman")
    assert anahtar == "masrafsiz_finansman"
    assert skor == 1.0


def test_benzer_terim_bul_yakin_varyant():
    anahtar, skor = benzer_terim_bul(
        "avantajli oranli finansman firsati, 12 aya varan taksit"
    )
    assert anahtar == "avantajli_finansman"
    assert skor >= 0.75


def test_benzer_terim_bul_esik_altinda_none_doner():
    anahtar, skor = benzer_terim_bul("tamamen alakasiz ve rastgele bir cumle burada")
    assert anahtar is None
    assert skor < 0.75


def test_benzer_terim_bul_kesirli_kar_paylasimi_izole_ifade():
    """Rapor Bolum 3 - Vakif Katilim ornegi, izole/kisa ifade olarak."""
    anahtar, skor = benzer_terim_bul("98/2 kar paylasimli finansman")
    assert anahtar == "kesirli_kar_paylasimi"
    assert skor >= 0.75


def test_benzer_terim_bul_sifir_oran_ifadesi_izole_ifade():
    """Rapor Bolum 3 - Albaraka ornegi, izole/kisa ifade olarak."""
    anahtar, skor = benzer_terim_bul("kar payi yok")
    assert anahtar == "sifir_oran_ifadesi"
    assert skor == 1.0


def test_benzer_terim_bul_tam_cumlede_zayif_kalir():
    """BILINEN SINIRLAMA: benzer_terim_bul() izole/kisa aday ifadeler icin
    tasarlanmistir (rehber Sprint 1 Gun 3 notu). Rapordaki gercek cumleyi
    ('Kar payi yok. Beklemek yok.') OLDUGU GIBI, tam cumle olarak verirsen
    SequenceMatcher orani dusup esigin (0.75) altinda kalabilir - bu bir
    hata degil, fonksiyonun kapsami disi bir kullanimdir. Sprint 2'de
    regex/NER, sozluge izole aday ifadeler (tam cumleler degil) vermelidir.
    """
    anahtar, skor = benzer_terim_bul("Kar payi yok. Beklemek yok.")
    assert anahtar is None
    assert skor < 0.75

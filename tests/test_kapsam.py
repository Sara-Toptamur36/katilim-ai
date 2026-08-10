"""preprocessing/kapsam.py testleri - sayfa kapsami kirlenmesi.

KILITLENEN DENGE: blok GERCEKTEN capraz kampanya listesi ise kirpilir,
degilse metne DOKUNULMAZ. Fazla genis bir kural, gercek kampanya
kosullarini silerdi - bu, sessiz veri kaybi olurdu.
"""

from preprocessing.kapsam import kampanya_govdesini_ayikla


GERCEK_AL001_SONU = """\
Kullanım Alanları (Sektörler):
Sağlık, Eğitim
Kredi kartına vade farksız taksit kampanyaları hakkında detaylı bilgi almak için:
Sağlık Kampanyası | Albaraka Türk
"Albaraka Mobil'den kampanyaya katılım sağlayarak, World kartlarınız ile yapacağınız 1.000 TL- 100.000 TL arası sağlık harcamalarınıza vade farksız 6 taksit fırsatını kaçırmayın!"
Eğitim Kampanyası | Albaraka Türk
"Siz de hemen Eğitim Harcamalarına Vade Farksız 6 Taksit kampanyasına katılın."
"""


def test_capraz_kampanya_blogu_kirpilir():
    """Gercek AL-001 sayfa sonu."""
    sonuc = kampanya_govdesini_ayikla(GERCEK_AL001_SONU)
    assert "Sağlık, Eğitim" in sonuc, "Kampanyanin kendi icerigi korunmali"
    assert "detaylı bilgi almak için" not in sonuc
    assert "Sağlık Kampanyası | Albaraka Türk" not in sonuc


def test_baska_kampanyanin_tutari_metinden_CIKAR():
    """Kirpmanin asil amaci: baska kampanyanin tutari bu kampanyaya
    atfedilmesin. AL-001'de 100.000 TL aslinda AL-005'in tutari."""
    sonuc = kampanya_govdesini_ayikla(GERCEK_AL001_SONU)
    assert "100.000 TL" not in sonuc


def test_capraz_baslik_yoksa_metne_DOKUNULMAZ():
    """"...hakkinda detayli bilgi almak icin" ifadesi kampanyanin kendi
    metninde de gecebilir (ör. bir telefon numarasina yonlendirme).
    Ardindan capraz kampanya basligi GELMIYORSA kesilmemeli."""
    metin = (
        "Kampanya kosullari asagidadir.\n"
        "Detaylı bilgi almak için 0850 222 5 666 numarasını arayabilirsiniz.\n"
        "Kampanya 31 Aralık 2026 tarihine kadar geçerlidir.\n"
        "Kâr payı oranı %1,89'dur."
    )
    assert kampanya_govdesini_ayikla(metin) == metin


def test_blok_yoksa_metin_aynen_doner():
    metin = "Konut finansmanında %1,89 kâr payı oranı ve 120 ay vade fırsatı."
    assert kampanya_govdesini_ayikla(metin) == metin


def test_bos_metin_guvenli():
    assert kampanya_govdesini_ayikla("") == ""
    assert kampanya_govdesini_ayikla(None) is None


def test_kirpma_kampanyanin_kendi_kosullarini_silmez():
    """Yonlendirme blogu sayfanin SONUNDA olur; oncesindeki her sey
    kampanyaya aittir ve korunmalidir."""
    metin = (
        "%0 kâr payı ile 40.000 TL'ye kadar Pratik Finansman Kart.\n"
        "Vade: 6 aya kadar\n"
        "Kredi kartına vade farksız taksit kampanyaları hakkında detaylı bilgi almak için:\n"
        "Sağlık Kampanyası | Albaraka Türk\n"
        "\"1.000 TL- 100.000 TL arası sağlık harcamalarınıza 6 taksit\""
    )
    sonuc = kampanya_govdesini_ayikla(metin)
    assert "40.000 TL'ye kadar Pratik Finansman Kart" in sonuc
    assert "Vade: 6 aya kadar" in sonuc
    assert "100.000" not in sonuc

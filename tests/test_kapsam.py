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


GERCEK_TOMBANKHADI_SONU = """\
T.O.M. Bank ve YENİ MAĞAZACILIK A.Ş. kampanyayı durdurma, iptal etme, kampanyada değişiklik yapma hakkını saklı tutar.
İlginizi Çekebilir
Toplam 1500 TL hoş geldin hediyesi!  TOM1500 koduyla müşterimiz ol, 1500 TL senin olsun!
Kampanya Detayı
Hadi Alışveriş Kredisi ile Klima, Süpürge ve Televizyonlarda Vade Farksız 12 Taksit!
Kampanya Detayı
Hadi Black Kredi Kartı ile Restoderm’de %30 İndirim!
Kampanya Detayı
"""


def test_ilginizi_cekebilir_blogu_kirpilir():
    """Gercek tombankhadi sayfa sonu (25 Agustos 2026 ile bulundu - 10/10
    tombankhadi sayfasinda ayni blok tekrar ediyor, dar kapsamli DEGIL)."""
    sonuc = kampanya_govdesini_ayikla(GERCEK_TOMBANKHADI_SONU)
    assert "kampanyayı durdurma" in sonuc, "Kampanyanin kendi icerigi korunmali"
    assert "İlginizi Çekebilir" not in sonuc
    assert "Kampanya Detayı" not in sonuc


def test_ilginizi_cekebilir_baska_kampanyanin_degeri_metinden_CIKAR():
    """Kirpmanin asil amaci: 1500 TL / 12 taksit / %30 gibi BASKA
    kampanyalarin degerleri bu kampanyaya atfedilmesin."""
    sonuc = kampanya_govdesini_ayikla(GERCEK_TOMBANKHADI_SONU)
    assert "1500 TL" not in sonuc
    assert "12 Taksit" not in sonuc
    assert "%30" not in sonuc


def test_ilginizi_cekebilir_dogrulayici_yoksa_metne_DOKUNULMAZ():
    """"İlginizi Çekebilir" baska bir baglamda (ör. genel site menusu)
    gecebilir. Ardindan "Kampanya Detayı" kalibi GELMIYORSA kesilmemeli -
    bkz. kuveytturk/albaraka footer menusu (Blog, Kampanyalar, Hesaplama
    Araçları gibi tekil kelimeler, "Kampanya Detayı" degil)."""
    metin = (
        "Kampanya koşulları yukarıdadır.\n"
        "İlginizi Çekebilir\n"
        "Blog\n"
        "Finans Portalı\n"
        "Kampanyalar\n"
    )
    assert kampanya_govdesini_ayikla(metin) == metin

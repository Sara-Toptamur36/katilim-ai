"""chunking/parcalayici.py testleri.

Saf mantik - dis servis (Qdrant/embedding modeli) GEREKTIRMEZ, CI'da
her zaman calisir.
"""

import json
from pathlib import Path

from chunking.parcalayici import (
    _gurultu_mu,
    basligi_bul,
    belgeyi_parcala,
    kayitlari_parcala,
)

RAW_DATA = Path(__file__).parent.parent / "scraper" / "raw_data"


# ---------------------------------------------------------------------------
# Gurultu filtresi
# ---------------------------------------------------------------------------


def test_tarayici_artigi_gurultu_sayilir():
    """Gercek veride belgelerin %41'inde geciyordu - hicbir kampanya
    bilgisi tasimaz."""
    assert _gurultu_mu("Your browser does not support the audio element.") is True


def test_sosyal_medya_butonlari_gurultu_sayilir():
    for satir in ["Facebook'da paylaş", "LinkedIn'de paylaş", "Whatsapp'da paylaş", "X'de paylaş"]:
        assert _gurultu_mu(satir) is True, satir


def test_gezinme_ve_form_alanlari_gurultu_sayilir():
    for satir in ["Ana Sayfa", "Kampanyalar", "Hemen Başvur", "T.C. Kimlik Numarası"]:
        assert _gurultu_mu(satir) is True, satir


def test_gercek_kampanya_kosulu_gurultu_SAYILMAZ():
    """KRITIK: gurultu filtresi asiri genis olursa gercek bilgi kaybolur."""
    gercek = [
        "Ücretsiz ve ticari kredi kartlarımız kampanyaya dahil değildir.",
        "2 ay ertelemeli İhtiyaç Kart'ta yeni müşterilere özel %1,99 oran fırsatı",
        "Kampanya 31 Aralık 2026 tarihine kadar geçerlidir.",
    ]
    for satir in gercek:
        assert _gurultu_mu(satir) is False, satir


def test_turkce_buyuk_i_gurultu_eslesmesini_bozmaz():
    """'İ'.lower() Turkce'de bozuk karakter uretir - projede daha once
    uc ayri yerde bulunan hata (terminology/, agent/intent.py)."""
    assert _gurultu_mu("KENDİM İÇİN") is True


# ---------------------------------------------------------------------------
# Baslik tespiti
# ---------------------------------------------------------------------------


def test_baslik_url_slugundan_alinir():
    """Olculdu: metin sezgisi yaniliyor, slug tutarli dogru."""
    baslik = basligi_bul(
        "Sektör: Giyim ve Aksesuar\nBazı açıklama metni burada yer alır.",
        "https://www.emlakkatilim.com.tr/tr/bireysel/kampanyalar/kampanya/decathlonda-4-taksit",
    )
    assert "Decathlonda 4 Taksit" == baslik


def test_slug_cok_kisaysa_metne_dusulur():
    """'lc-waikiki' gibi kisa slug tek basina kampanyayi tanimlamaz."""
    baslik = basligi_bul(
        "Dünya Katılım TROY kartlarınızla LC Waikiki'de 3.000 TL indirim fırsatı",
        "https://www.dunyakatilim.com.tr/kampanyalar/lc-waikiki",
    )
    assert "TROY" in baslik


# ---------------------------------------------------------------------------
# Parcalama
# ---------------------------------------------------------------------------


def test_parcalara_baslik_onek_olarak_eklenir():
    """Bir parca tek basina HANGI kampanyaya ait oldugunu soyleyebilmeli -
    retrieval kalitesine en cok katki yapan karar (bkz. modul docstring)."""
    parcalar = belgeyi_parcala(
        "Kampanya kapsamında 100.000 TL'ye kadar finansman sağlanır ve "
        "bu tutar için 12 aya varan taksit seçenekleri sunulmaktadır.",
        baslik="Test Kampanyasi",
    )
    assert parcalar
    assert all("Test Kampanyasi" in p for p in parcalar)


def test_cok_kisa_parcalar_elenir():
    parcalar = belgeyi_parcala("Kısa.", baslik="Baslik")
    assert parcalar == []


def test_uzun_metin_birden_fazla_parcaya_bolunur():
    uzun_satirlar = "\n".join(
        f"Bu {i}. kampanya koşulu maddesidir ve yeterince uzun bir metin içerir." for i in range(40)
    )
    parcalar = belgeyi_parcala(uzun_satirlar, baslik="Baslik", hedef_boyut=300)
    assert len(parcalar) > 1


def test_ayni_icerik_tekillestirilir():
    """Ortak yasal uyarilar farkli kampanyalarda tekrar ediyor; sonuc
    listesi ayni metni birden fazla gostermemeli."""
    ortak = (
        "Bankamız kampanya koşullarını değiştirme ve kampanyayı durdurma hakkına sahiptir. "
        "Ücretsiz ve ticari kredi kartlarımız kampanyaya dahil değildir."
    )
    kayitlar = [
        {"ham_metin": ortak, "url": "https://x.com/kampanya-bir-ornek", "banka": "A"},
        {"ham_metin": ortak, "url": "https://x.com/kampanya-iki-ornek", "banka": "B"},
    ]
    parcalar = kayitlari_parcala(kayitlar)
    metinler = [p["metin"] for p in parcalar]
    assert len(metinler) == len(set(metinler)), "Yinelenen parca indekslenmis"


def test_parcalar_provenance_tasir():
    """Rapor Bolum 9: kaynagi gosterilemeyen bir cevabin degeri yoktur."""
    kayitlar = [
        {
            "ham_metin": "Kampanya kapsamında 100.000 TL'ye kadar finansman ve 12 ay taksit sunulur.",
            "url": "https://ornek.com/kampanyalar/ornek-kampanya-adi",
            "banka": "Kuveyt Türk",
            "erisim_zamani": "2026-08-06T10:00:00",
        }
    ]
    parca = kayitlari_parcala(kayitlar)[0]
    assert parca["kaynak_url"] == "https://ornek.com/kampanyalar/ornek-kampanya-adi"
    assert parca["banka"] == "Kuveyt Türk"
    assert parca["kampanya_adi"]


# ---------------------------------------------------------------------------
# Gercek veriyle regresyon
# ---------------------------------------------------------------------------


def test_gercek_veride_naif_yontemden_belirgin_az_parca_uretir():
    """Semantik parcalama + tekillestirme, naif satir bolmeye gore
    indeksi belirgin kuculmeli (spike Bulgu 3)."""
    kayitlar = []
    for dosya in sorted(RAW_DATA.glob("*/json/*.json")):
        with open(dosya, encoding="utf-8") as f:
            kayitlar.append(json.load(f))
    assert len(kayitlar) >= 100, "beklenen fixture sayisi degisti"

    parcalar = kayitlari_parcala(kayitlar)
    assert parcalar, "Hic parca uretilmedi"

    # Her parca provenance tasimali
    assert all(p["kaynak_url"] for p in parcalar)
    # Tekillestirme gercekten calismali
    metinler = [p["metin"] for p in parcalar]
    assert len(metinler) == len(set(metinler))
    # Parca sayisi belge sayisindan fazla ama makul olmali
    assert len(kayitlar) < len(parcalar) < len(kayitlar) * 10

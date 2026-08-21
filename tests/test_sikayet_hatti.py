"""Sikayet hatti: izin kapisi, PII temizligi, eslesme ve bag guveni.

BU TESTLERIN ASIL ISI dort KIRMIZI CIZGIYI (Rehber_Zeynep_Veri.md)
calisan kontrole donusturmektir:

  1. Ham metin izin kapisi gecmeden diske yazilmaz
  2. PII temizligi kayittan ONCE
  3. Sikayet verisi kampanya tablosuna karismaz
  4. "Sikayet orani" denmez - payda yoksa "gozlenen yogunluk"

Bir kural, ihlal edildiginde kirmizi vermiyorsa kural degil temennidir.
"""

import json
from datetime import date

import pytest

from complaint.izin_kapisi import (
    IzinYok,
    izin_var_mi,
    izinleri_oku,
    izni_zorunlu_kil,
)
from complaint.kampanya_eslestirme import ASGARI_GUVEN, kampanya_esle
from complaint.pii_temizleme import temizle
from complaint.toplama import hazirla, yogunluk_ozeti


class SahteKampanya:
    """CampaignRecord'un eslestirme icin gereken yuzeyi."""

    def __init__(self, id, banka, kampanya_adi, odul_birimi=None,
                 kampanya_baslangic=None, kampanya_bitis=None):
        self.id = id
        self.banka = banka
        self.kampanya_adi = kampanya_adi
        self.odul_birimi = odul_birimi
        self.kampanya_baslangic = kampanya_baslangic
        self.kampanya_bitis = kampanya_bitis


@pytest.fixture
def izin_dosyasi(tmp_path):
    yol = tmp_path / "izin.json"
    yol.write_text(
        json.dumps([{
            "kaynak": "test_kaynagi",
            "onaylayan": "Hukuk Birimi",
            "kurum": "PeacewAI",
            "onay_tarihi": "2026-08-01",
            "kapsam": "tema analizi",
        }]),
        encoding="utf-8",
    )
    return yol


# ---------------------------------------------------------------------------
# KIRMIZI CIZGI 1 - izin kapisi
# ---------------------------------------------------------------------------


def test_izin_kaydi_yoksa_varsayilan_IZIN_YOK(tmp_path):
    """Dosya yoksa "izin var" sayilmaz. Varsayilan HER ZAMAN yokluktur."""
    assert izinleri_oku(tmp_path / "olmayan.json") == []
    assert izin_var_mi("herhangi", dosya=tmp_path / "olmayan.json") is False


def test_izin_yoksa_toplama_calismaz(tmp_path):
    """Kirmizi cizginin kendisi: izin gecilmeden veri islenmez."""
    with pytest.raises(IzinYok):
        hazirla("odulum yatmadi", kaynak="gercek_platform",
                bugun=date(2026, 8, 21))


def test_bozuk_izin_dosyasi_izin_VAR_saymaz(tmp_path):
    """Bozuk JSON en guvenli sekilde yorumlanir: izin yok."""
    yol = tmp_path / "bozuk.json"
    yol.write_text("{ bu gecerli json degil", encoding="utf-8")
    assert izin_var_mi("test_kaynagi", dosya=yol) is False


def test_eksik_alanli_izin_gecersizdir(tmp_path):
    """Yarim doldurulmus kayit izin saymaz - "onaylayan" kim belli degilse
    denetlenebilir bir onay yoktur."""
    yol = tmp_path / "eksik.json"
    yol.write_text(
        json.dumps([{"kaynak": "test_kaynagi", "onay_tarihi": "2026-08-01"}]),
        encoding="utf-8",
    )
    assert izin_var_mi("test_kaynagi", dosya=yol) is False


def test_izin_kaynak_bazlidir(izin_dosyasi):
    """Bir kaynak icin alinan izin digerini KAPSAMAZ."""
    assert izin_var_mi("test_kaynagi", bugun=date(2026, 8, 21), dosya=izin_dosyasi)
    assert not izin_var_mi("baska_platform", bugun=date(2026, 8, 21), dosya=izin_dosyasi)


def test_suresi_dolmus_izin_gecersizdir(tmp_path):
    yol = tmp_path / "suresi_dolmus.json"
    yol.write_text(
        json.dumps([{
            "kaynak": "k", "onaylayan": "H", "kurum": "P",
            "onay_tarihi": "2026-01-01", "kapsam": "t",
            "gecerlilik_bitis": "2026-06-30",
        }]),
        encoding="utf-8",
    )
    assert izin_var_mi("k", bugun=date(2026, 6, 30), dosya=yol) is True
    assert izin_var_mi("k", bugun=date(2026, 7, 1), dosya=yol) is False


def test_ileri_tarihli_onay_henuz_gecerli_degil(tmp_path):
    yol = tmp_path / "ileri.json"
    yol.write_text(
        json.dumps([{
            "kaynak": "k", "onaylayan": "H", "kurum": "P",
            "onay_tarihi": "2026-12-01", "kapsam": "t",
        }]),
        encoding="utf-8",
    )
    assert izin_var_mi("k", bugun=date(2026, 8, 21), dosya=yol) is False


def test_izin_hatasi_ne_yapilacagini_soyluyor(tmp_path):
    """Hata mesaji suclamaz, YOL GOSTERIR - hangi dosya, hangi alanlar."""
    with pytest.raises(IzinYok) as e:
        izni_zorunlu_kil("bir_kaynak", dosya=tmp_path / "yok.json")
    metin = str(e.value)
    assert "sikayet_izin_durumu.json" in metin
    assert "onaylayan" in metin


# ---------------------------------------------------------------------------
# KIRMIZI CIZGI 2 - PII temizligi KAYITTAN ONCE
# ---------------------------------------------------------------------------


def test_tckn_iban_telefon_eposta_maskelenir():
    sonuc = temizle(
        "TCKN 10000000146, IBAN TR330006100519786457841326, "
        "tel 0532 111 22 33, mail ali@example.com"
    )
    assert "10000000146" not in sonuc.metin
    assert "TR330006100519786457841326" not in sonuc.metin
    assert "ali@example.com" not in sonuc.metin
    assert "[TCKN]" in sonuc.metin and "[IBAN]" in sonuc.metin


def test_gecersiz_11_hane_TCKN_sanilip_silinmez():
    """Musteri/siparis numarasi da 11 haneli olabilir. Resmi algoritmayi
    gecmeyen sayi metinde KALIR - aksi halde metin okunmaz olurdu."""
    sonuc = temizle("Musteri numaram 12345678901, odulum yatmadi")
    assert "12345678901" in sonuc.metin
    assert "tckn" not in sonuc.bulunanlar


def test_pii_yoksa_insan_kontrolu_istenmez():
    sonuc = temizle("Kampanyadan yararlanamadim, kosullar belirsizdi")
    assert sonuc.pii_bulundu_mu is False
    assert sonuc.insan_kontrolu_gerekir is False


def test_pii_bulunursa_insan_kontrolu_isaretlenir():
    """Kisi adlari yakalanamiyor (bilinen sinir) - PII bulunan metin
    sessizce "temiz" ilan edilmez."""
    assert temizle("tel 0532 111 22 33").insan_kontrolu_gerekir is True


def test_hazirlanan_kayit_ham_metni_TASIMAZ():
    """`HazirSikayet` ham metin alani icermemeli - donerse cagiran taraf
    yanlislikla saklayabilirdi."""
    hazir = hazirla("TCKN 10000000146 odulum yatmadi", kaynak="sentetik",
                    izin_zorunlu=False)
    assert not hasattr(hazir, "ham_metin")
    assert "10000000146" not in hazir.temiz_metin


def test_tema_siniflandirmasi_TEMIZLENMIS_metinden_yapilir():
    hazir = hazirla("odul hesabima yatmadi, tel 0532 111 22 33",
                    kaynak="sentetik", izin_zorunlu=False)
    assert hazir.tema == "REWARD_NOT_CREDITED"
    assert "0532" not in (hazir.tema_kaniti or "")


# ---------------------------------------------------------------------------
# KIRMIZI CIZGI 3 - kampanya verisine karismaz
# ---------------------------------------------------------------------------


def test_sikayet_tablosunda_kampanyaya_foreign_key_YOKTUR():
    """Eslesme bir HIPOTEZDIR; FK koymak onu semanin garantisi gibi
    gosterirdi (bkz. complaint/kampanya_eslestirme.py)."""
    from api.models import Sikayet

    assert Sikayet.__tablename__ == "sikayetler"
    yabanci = [fk for s in Sikayet.__table__.columns for fk in s.foreign_keys]
    assert yabanci == []


def test_sikayet_tablosunda_ham_metin_sutunu_YOKTUR():
    from api.models import Sikayet

    sutunlar = set(Sikayet.__table__.columns.keys())
    assert "temiz_metin" in sutunlar
    assert "ham_metin" not in sutunlar


# ---------------------------------------------------------------------------
# KIRMIZI CIZGI 4 - "oran" degil "gozlenen yogunluk"
# ---------------------------------------------------------------------------


def test_ozet_oran_uretmez_adet_doner():
    sikayetler = [
        hazirla("odul yatmadi", kaynak="s", izin_zorunlu=False),
        hazirla("odul gecmedi", kaynak="s", izin_zorunlu=False),
        hazirla("anlasilmaz bir metin", kaynak="s", izin_zorunlu=False),
    ]
    ozet = yogunluk_ozeti(sikayetler)

    assert ozet["olcu"] == "gozlenen_yogunluk"
    assert ozet["temalar"]["REWARD_NOT_CREDITED"] == 2
    assert ozet["temalar"]["SINIFLANDIRILAMADI"] == 1
    # Hicbir yerde yuzde/oran alani olmamali
    assert not any("oran" in a or "yuzde" in a for a in ozet)


# ---------------------------------------------------------------------------
# Gorev 24 - eslesme ve bag guveni
# ---------------------------------------------------------------------------


def test_banka_adi_TEK_BASINA_eslesmeye_yetmez():
    """Bir bankanin onlarca kampanyasi var; hangisi oldugunu soylemek
    icin ikinci bir sinyal gerekir."""
    k = SahteKampanya(1, "Kuveyt Turk", "Egitim Harcamalarina Taksit")
    sonuc = kampanya_esle("Kuveyt Turk ile ilgili bir sorunum var", [k])
    assert sonuc.eslesti_mi is False
    assert sonuc.guven < ASGARI_GUVEN


def test_banka_ve_kampanya_adi_birlikte_eslesir():
    k = SahteKampanya(7, "Kuveyt Turk", "Egitim Harcamalarina Taksit")
    sonuc = kampanya_esle(
        "Kuveyt Turk egitim harcamalarina taksit kampanyasindan yararlanamadim", [k]
    )
    assert sonuc.kampanya_id == 7
    assert sonuc.guven >= ASGARI_GUVEN
    assert "banka" in sonuc.gerekce


def test_zaman_penceresi_disi_eslesme_ELENIR():
    """Henuz baslamamis kampanya hakkinda sikayet edilemez - guven
    dusurulmez, SIFIRLANIR."""
    k = SahteKampanya(3, "Ziraat Katilim", "Saglik Sektorunde Taksit",
                      kampanya_baslangic=date(2026, 9, 1))
    sonuc = kampanya_esle(
        "Ziraat Katilim saglik sektorunde taksit kampanyasi",
        [k],
        sikayet_tarihi=date(2026, 3, 1),
    )
    assert sonuc.eslesti_mi is False
    assert sonuc.gerekce.get("pencere_disi") is True


def test_tarih_bilinmiyorsa_pencere_kontrolu_UYGULANMAZ():
    """Bilinmeyen tarih "pencere disi" demek DEGILDIR."""
    k = SahteKampanya(4, "Ziraat Katilim", "Saglik Sektorunde Taksit",
                      kampanya_bitis=date(2026, 1, 1))
    sonuc = kampanya_esle(
        "Ziraat Katilim saglik sektorunde taksit sorunu", [k], sikayet_tarihi=None
    )
    assert sonuc.gerekce.get("zaman_penceresi") == "bilinmiyor"
    assert sonuc.gerekce.get("pencere_disi") is None


def test_beraberlikte_eslesme_URETILMEZ():
    """Iki kampanya ayni puani aldiysa hangisi oldugunu soyleyemeyiz;
    rastgele secmek olmayan bir kesinlik uretmek olurdu."""
    a = SahteKampanya(1, "Kuveyt Turk", "Taksit Firsati")
    b = SahteKampanya(2, "Kuveyt Turk", "Taksit Firsati")
    sonuc = kampanya_esle("Kuveyt Turk taksit firsati sorunu", [a, b])
    assert sonuc.eslesti_mi is False
    assert "ayirt edilemedi" in sonuc.gerekce["sebep"]


def test_eslesmeyince_NEDEN_eslesmedigi_yazilir():
    """Sessiz bosluk birakilmaz."""
    k = SahteKampanya(1, "Albaraka Turk", "Konut Finansmani")
    sonuc = kampanya_esle("bambaska bir konu hakkinda sikayet", [k])
    assert sonuc.eslesti_mi is False
    assert "sebep" in sonuc.gerekce


def test_kampanya_yoksa_eslesme_denenmez():
    sonuc = kampanya_esle("herhangi bir sikayet", [])
    assert sonuc.eslesti_mi is False
    assert sonuc.guven == 0.0


def test_pencere_icinde_olmak_PUAN_KAZANDIRMAZ():
    """DENETIM BULGUSU (gercek veriyle calistirilirken): pencereye 0.10
    puan verilmisti ve yalnizca banka adi gecen bir sikayet (0.40 + 0.10)
    esigi asip eslesiyordu. Ayni anda onlarca kampanya yururluktedir;
    "o tarihte aktifti" HANGI kampanya oldugunu soylemez.

    Modulun kendi ilkesi de bunu soyluyordu ("pencere puan degil eleme")
    - kod docstring ile CELISIYORDU."""
    k = SahteKampanya(1, "A Bankasi", "Konut Finansmani Kampanyasi",
                      kampanya_baslangic=date(2026, 1, 1),
                      kampanya_bitis=date(2026, 12, 31))

    sonuc = kampanya_esle(
        "A Bankasi'nin kampanyasina katildim ama odulum yatmadi",
        [k],
        sikayet_tarihi=date(2026, 8, 1),
    )

    assert sonuc.eslesti_mi is False, "banka adi + pencere eslesmeye yetmemeli"
    assert sonuc.gerekce["zaman_penceresi"] == "icinde"


def test_esik_banka_agirligindan_buyuk_kalmali():
    """Bu iliski bozulursa banka adi TEK BASINA eslesme uretmeye baslar -
    testin isi o sessiz gerilemeyi yakalamak."""
    from complaint.kampanya_eslestirme import AGIRLIK_BANKA

    assert ASGARI_GUVEN > AGIRLIK_BANKA


def test_banka_ve_odul_birimi_birlikte_eslesir():
    """Ikinci AYIRT EDICI sinyal geldiginde eslesme kurulur."""
    k = SahteKampanya(9, "D Bankasi", "Kart Harcamalarina Mil Hediyesi",
                      odul_birimi="Mil")
    sonuc = kampanya_esle("D Bankasi kartimdan Mil hediyesi yatmadi", [k])
    assert sonuc.kampanya_id == 9
    assert sonuc.gerekce.get("odul_birimi") == "Mil"

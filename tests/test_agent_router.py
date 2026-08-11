"""agent/router.py testleri."""

from datetime import date

from agent.router import (
    hesaplama_aracini_cagir,
    karsilastirma_aracini_cagir,
    sozluk_aracini_cagir,
)
from api.schemas import CampaignRecord


def _kayit(banka: str, oran_percent: float | None, oran_decimal: float | None = None) -> CampaignRecord:
    return CampaignRecord(
        banka=banka,
        kampanya_adi=f"{banka} Ornek Kampanya",
        kaynak_url="https://ornek.com",
        kar_payi_orani_percent=oran_percent,
        kar_payi_orani_decimal=oran_decimal if oran_decimal is not None else (
            oran_percent / 100 if oran_percent is not None else None
        ),
    )


# ---------------------------------------------------------------------------
# Calculator Tool
# ---------------------------------------------------------------------------


def test_hesaplama_araci_dogru_hesap_yapar():
    sonuc = hesaplama_aracini_cagir("500.000 TL, %1,99 oranla 24 ay vadeyle taksitim ne kadar olur?")
    assert sonuc["basarili"] is True
    assert sonuc["veri"]["anapara"] == 500000.0
    assert sonuc["veri"]["aylik_taksit"] > 0


def test_hesaplama_araci_eksik_parametrede_sebep_bildirir():
    sonuc = hesaplama_aracini_cagir("Taksitimi hesaplar misin?")
    assert sonuc["basarili"] is False
    assert "anapara" in sonuc["sebep"]


# ---------------------------------------------------------------------------
# Dictionary Tool
# ---------------------------------------------------------------------------


def test_sozluk_araci_bilinen_terimi_bulur():
    sonuc = sozluk_aracini_cagir("Kâr payı oranı ne demek?")
    assert sonuc["basarili"] is True
    assert "Faiz" in sonuc["cevap"] or "faiz" in sonuc["cevap"].lower()


def test_sozluk_araci_alakasiz_terimde_basarisiz_doner():
    sonuc = sozluk_aracini_cagir("Marsta hayat var mi nedir?")
    assert sonuc["basarili"] is False


# ---------------------------------------------------------------------------
# Comparison (SQL) Tool
# ---------------------------------------------------------------------------


def test_karsilastirma_araci_iki_taninan_banka_ile_calisir():
    def sahte_getirici(banka: str) -> list[CampaignRecord]:
        veriler = {
            "Kuveyt Türk": [_kayit("Kuveyt Türk", 1.99)],
            "Albaraka Türk": [_kayit("Albaraka Türk", 1.5)],
        }
        return veriler.get(banka, [])

    soru = "Kuveyt Türk ile Albaraka Türk'ü karsilastir, en dusuk oranli hangisi?"
    sonuc = karsilastirma_aracini_cagir(soru, sahte_getirici)
    assert sonuc["basarili"] is True
    assert sonuc["veri"]["kriter"] == "en_dusuk_kar_payi"


def test_karsilastirma_araci_tek_banka_tespit_edilirse_basarisiz_doner():
    """Rapor Bolum 5.7/15: yetersiz bilgi sessizce yanlis cevaba
    donusturulmez, acikca bildirilir."""
    def sahte_getirici(banka: str) -> list[CampaignRecord]:
        return [_kayit(banka, 1.0)]

    sonuc = karsilastirma_aracini_cagir("Kuveyt Türk'ün orani nedir?", sahte_getirici)
    assert sonuc["basarili"] is False
    assert "banka" in sonuc["sebep"].lower()


def test_karsilastirma_araci_dogru_turkce_diyakritiklerle_de_calisir():
    """Gercek /chat uctan uca testinde bulundu: kullanicilar dogal olarak
    'karşılaştır'/'en düşük' gibi Turkce karakterlerle yazar, ama anahtar
    kelime listeleri ASCII'dir ('karsilastir'/'en dusuk'). Katlama
    olmadan bu soru hicbir zaman eslesmezdi (bkz. agent/intent.py
    turkce_ascii_katla)."""
    def sahte_getirici(banka: str) -> list[CampaignRecord]:
        veriler = {
            "Kuveyt Türk": [_kayit("Kuveyt Türk", 1.99)],
            "Albaraka Türk": [_kayit("Albaraka Türk", 1.5)],
        }
        return veriler.get(banka, [])

    soru = "Kuveyt Türk ve Albaraka Türk karşılaştırması yap, en düşük kâr payı hangisinde?"
    sonuc = karsilastirma_aracini_cagir(soru, sahte_getirici)
    assert sonuc["basarili"] is True
    assert sonuc["veri"]["kriter"] == "en_dusuk_kar_payi"


def test_karsilastirma_araci_diyakritiksiz_yazilan_banka_adiyla_da_calisir():
    """Ters yon: banka adi 'Kuveyt Türk' iken kullanici Turkce klavyesi
    olmadan 'Kuveyt Turk' yazsa bile eslesmeli (iki yonlu katlama)."""
    def sahte_getirici(banka: str) -> list[CampaignRecord]:
        veriler = {
            "Kuveyt Türk": [_kayit("Kuveyt Türk", 1.99)],
            "Albaraka Türk": [_kayit("Albaraka Türk", 1.5)],
        }
        return veriler.get(banka, [])

    soru = "Kuveyt Turk ile Albaraka Turk'u karsilastir"
    sonuc = karsilastirma_aracini_cagir(soru, sahte_getirici)
    assert sonuc["basarili"] is True


def test_karsilastirma_kriteri_soru_metninden_dogru_tespit_edilir():
    def sahte_getirici(banka: str) -> list[CampaignRecord]:
        return [
            CampaignRecord(
                banka=banka,
                kampanya_adi="Ornek",
                kaynak_url="https://ornek.com",
                odul_miktari=1000.0 if banka == "Kuveyt Türk" else 500.0,
                odul_birimi="TL",
            )
        ]

    soru = "Kuveyt Türk ile Albaraka Türk'te en yuksek odul hangisinde?"
    sonuc = karsilastirma_aracini_cagir(soru, sahte_getirici)
    assert sonuc["basarili"] is True
    assert sonuc["veri"]["kriter"] == "en_yuksek_odul"


def test_karsilastirma_avantajli_kelimesi_kompozit_kriteri_tetikler():
    """Sartname Md. 5.7'nin kendi terimi 'En Avantajli Kampanya' - bu
    kelime hicbir zaman tek bir alt kritere (ör. en dusuk oran) daralmaz."""
    def sahte_getirici(banka: str) -> list[CampaignRecord]:
        return [_kayit(banka, 1.99 if banka == "Kuveyt Türk" else 1.5)]

    soru = "Kuveyt Türk mü daha avantajlı, Albaraka Türk mü?"
    sonuc = karsilastirma_aracini_cagir(soru, sahte_getirici)
    assert sonuc["basarili"] is True
    assert sonuc["veri"]["kriter"] == "en_avantajli"


def test_karsilastirma_en_dusuk_oran_avantajli_kompozitiyle_karismaz():
    """'oran' kelimesi acikca gecince hala rate-ozgu kritere gitmeli -
    'avantajli' anahtar kelimesiyle cakismamali (sozluk sirasi kontrolu)."""
    def sahte_getirici(banka: str) -> list[CampaignRecord]:
        return [_kayit(banka, 1.99 if banka == "Kuveyt Türk" else 1.5)]

    soru = "Kuveyt Türk ile Albaraka Türk'ü karsilastir, en dusuk oran hangisinde?"
    sonuc = karsilastirma_aracini_cagir(soru, sahte_getirici)
    assert sonuc["veri"]["kriter"] == "en_dusuk_kar_payi"

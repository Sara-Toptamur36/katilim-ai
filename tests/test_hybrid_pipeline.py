"""extraction/hybrid_pipeline.py testleri (Sprint 2 Gun 3).

Bazi testler ner_ile_cikar/llm_ile_cikar'i monkeypatch ile izole eder
(regex'in doldurdugu bir alanin asla ezilmedigini, gereksiz yere NER/LLM
cagrilmadigini kanitlamak icin - bu, gercek model/servis cagirmadan
DAVRANISI dogrular). Diger testler gercek GLiNER/Ollama servisleriyle
uctan uca calisir (diger test dosyalarindaki AYNI kural).
"""

import json
from pathlib import Path

import extraction.hybrid_pipeline as hp
from extraction.hybrid_pipeline import kaydi_hibrit_cikar

RAW_DATA = Path(__file__).parent.parent / "scraper" / "raw_data"


def test_regex_her_seyi_doldurursa_ner_ve_llm_hic_cagrilmaz(monkeypatch):
    """Performans kurali: regex zaten tum alanlari doldurmussa, NER model
    yuklemesi ve Ollama'ya HTTP istegi gibi pahali islemler HIC
    tetiklenmemeli."""

    def _cagrilirsa_patlat(*args, **kwargs):
        raise AssertionError("NER/LLM cagrilmamali - regex zaten her seyi doldurdu")

    monkeypatch.setattr(hp, "ner_ile_cikar", _cagrilirsa_patlat)
    monkeypatch.setattr(hp, "llm_ile_cikar", _cagrilirsa_patlat)

    def _sahte_regex(ham_metin):
        return {alan: "sahte-deger" for alan in hp._NER_LLM_DESTEKLI_ALANLAR} | {
            "kampanya_turu": None,
            "kampanya_baslangic": None,
            "_izler": {alan: ("sahte", 0.9) for alan in hp._NER_LLM_DESTEKLI_ALANLAR},
        }

    monkeypatch.setattr(hp, "kaydi_cikar", _sahte_regex)

    sonuc = kaydi_hibrit_cikar("herhangi bir metin")
    for alan in hp._NER_LLM_DESTEKLI_ALANLAR:
        assert sonuc["_kaynaklar"][alan] == "regex"


def test_regexin_doldurdugu_alan_ner_tarafindan_ezilmez(monkeypatch):
    """Savunma testi: NER, sadece_bu_alanlar filtresine uymasa/hata
    yapsa bile, hibrit boru hattinin kendi birlestirme mantigi regex'in
    zaten doldurdugu bir alanin uzerine YAZMAMALI."""

    def _sahte_regex(ham_metin):
        alanlar = {alan: None for alan in hp._NER_LLM_DESTEKLI_ALANLAR}
        alanlar.update({"kampanya_turu": None, "kampanya_baslangic": None})
        alanlar["vade_ay"] = 120
        return alanlar | {"_izler": {"vade_ay": ("120 ay", 0.85)}}

    def _hatali_ner(ham_metin, sadece_bu_alanlar=None):
        # sadece_bu_alanlar'i yok sayip vade_ay icin FARKLI (yanlis) bir
        # deger dondurmeye calisan bozuk bir NER simulasyonu.
        return {"vade_ay": 36, "_izler": {"vade_ay": ("36 ay", 0.5)}}

    monkeypatch.setattr(hp, "kaydi_cikar", _sahte_regex)
    monkeypatch.setattr(hp, "ner_ile_cikar", _hatali_ner)
    monkeypatch.setattr(hp, "llm_ile_cikar", lambda *a, **k: {"_izler": {}})

    sonuc = kaydi_hibrit_cikar("herhangi bir metin")
    assert sonuc["vade_ay"] == 120
    assert sonuc["_kaynaklar"]["vade_ay"] == "regex"


def test_ner_doldurdugu_alan_kaynak_olarak_isaretlenir(monkeypatch):
    def _sahte_regex(ham_metin):
        alanlar = {alan: None for alan in hp._NER_LLM_DESTEKLI_ALANLAR}
        alanlar.update({"kampanya_turu": None, "kampanya_baslangic": None})
        return alanlar | {"_izler": {}}

    def _sahte_ner(ham_metin, sadece_bu_alanlar=None):
        return {"erteleme_suresi_ay": 3, "_izler": {"erteleme_suresi_ay": ("3 ay ödemesiz", 0.8)}}

    monkeypatch.setattr(hp, "kaydi_cikar", _sahte_regex)
    monkeypatch.setattr(hp, "ner_ile_cikar", _sahte_ner)
    monkeypatch.setattr(hp, "llm_ile_cikar", lambda *a, **k: {"_izler": {}})

    sonuc = kaydi_hibrit_cikar("3 ay ödemesiz dönem fırsatı.")
    assert sonuc["erteleme_suresi_ay"] == 3
    assert sonuc["_kaynaklar"]["erteleme_suresi_ay"] == "ner"
    assert sonuc["_izler"]["erteleme_suresi_ay"] == ("3 ay ödemesiz", 0.8)


def test_ner_bulamazsa_llm_denenir_ve_kaynak_isaretlenir(monkeypatch):
    def _sahte_regex(ham_metin):
        alanlar = {alan: None for alan in hp._NER_LLM_DESTEKLI_ALANLAR}
        alanlar.update({"kampanya_turu": None, "kampanya_baslangic": None})
        return alanlar | {"_izler": {}}

    def _bos_ner(ham_metin, sadece_bu_alanlar=None):
        return {alan: None for alan in sadece_bu_alanlar} | {"_izler": {}}

    def _sahte_llm(ham_metin, sadece_bu_alanlar=None, model=None):
        return {"hedef_kitle": "Yeni müşteri", "_izler": {"hedef_kitle": ("Yeni müşteri", 0.6)}}

    monkeypatch.setattr(hp, "kaydi_cikar", _sahte_regex)
    monkeypatch.setattr(hp, "ner_ile_cikar", _bos_ner)
    monkeypatch.setattr(hp, "llm_ile_cikar", _sahte_llm)

    sonuc = kaydi_hibrit_cikar("herhangi bir metin")
    assert sonuc["hedef_kitle"] == "Yeni müşteri"
    assert sonuc["_kaynaklar"]["hedef_kitle"] == "llm"


def test_kampanya_turu_ve_baslangic_ner_llme_hic_sorulmaz(monkeypatch):
    """KAPSAM DISI ALANLAR: bu iki alan icin regex bulamazsa None kalir,
    NER/LLM'e hic sorulmamali (ikisi de bu alanlari desteklemiyor)."""
    sorulan_alanlar: list[set] = []

    def _sahte_regex(ham_metin):
        alanlar = {alan: None for alan in hp._NER_LLM_DESTEKLI_ALANLAR}
        alanlar.update({"kampanya_turu": None, "kampanya_baslangic": None})
        return alanlar | {"_izler": {}}

    def _kaydeden_ner(ham_metin, sadece_bu_alanlar=None):
        sorulan_alanlar.append(sadece_bu_alanlar)
        return {alan: None for alan in sadece_bu_alanlar} | {"_izler": {}}

    monkeypatch.setattr(hp, "kaydi_cikar", _sahte_regex)
    monkeypatch.setattr(hp, "ner_ile_cikar", _kaydeden_ner)
    monkeypatch.setattr(hp, "llm_ile_cikar", lambda *a, **k: {"_izler": {}})

    sonuc = kaydi_hibrit_cikar("herhangi bir metin")
    assert sonuc["kampanya_turu"] is None
    assert sonuc["kampanya_baslangic"] is None
    assert "kampanya_turu" not in sorulan_alanlar[0]
    assert "kampanya_baslangic" not in sorulan_alanlar[0]


def test_gercek_veriyle_uctan_uca_calisir():
    """Gercek Albaraka kampanya metniyle GLiNER + Ollama'nin ikisi de
    devrede uctan uca calisir - hicbir hata firlatmadan, tutarli bir
    sonuc uretir."""
    with open(
        RAW_DATA / "albaraka" / "json" / "20260731_albaraka_tr_kampanyalar_detay_vade-farksiz-kampanyasi.json",
        encoding="utf-8",
    ) as f:
        kayit = json.load(f)

    sonuc = kaydi_hibrit_cikar(kayit["ham_metin"])
    assert "_izler" in sonuc
    assert "_kaynaklar" in sonuc
    for alan, kaynak in sonuc["_kaynaklar"].items():
        assert kaynak in ("regex", "ner", "llm")
        assert sonuc[alan] is not None


# ---------------------------------------------------------------------------
# Aday + uzlastirici (guven esikli devralma) - "regex kilitleme" duzeltmesi
# ---------------------------------------------------------------------------


def _bos_regex_ciktisi(**dolu):
    """Tum alanlari None olan bir regex ciktisi uretir, verilenleri doldurur."""
    alanlar = {alan: None for alan in hp._NER_LLM_DESTEKLI_ALANLAR}
    alanlar.update({"kampanya_turu": None, "kampanya_baslangic": None})
    izler = {}
    for alan, (deger, guven) in dolu.items():
        alanlar[alan] = deger
        izler[alan] = (str(deger), guven)
    return alanlar | {"_izler": izler}


def test_dusuk_guvenli_regex_degeri_daha_guvenli_ner_ile_duzeltilir(monkeypatch):
    """DENETIM BULGUSU (mentor: "regex kilitleme riski"): Eskiden bir
    katmanin doldurdugu alan ASLA ezilmiyordu; regex yanlis bir deger
    urettiginde hata KALICI oluyordu. Olculen kanit: 6 yanlis pozitifin
    4'u regex'in 0.6 guvenli "genel yuzde" fallback'inden geliyordu.

    Artik guveni esigin ALTINDA olan bir alan, daha yuksek guvenli bir
    aday tarafindan devralinabilir."""
    monkeypatch.setattr(
        hp, "kaydi_cikar",
        lambda m: _bos_regex_ciktisi(kar_payi_orani_percent=(10.0, 0.6)),
    )
    monkeypatch.setattr(
        hp, "ner_ile_cikar",
        lambda m, sadece_bu_alanlar=None: {
            "kar_payi_orani_percent": 1.89,
            "_izler": {"kar_payi_orani_percent": ("%1,89", 0.75)},
        },
    )
    monkeypatch.setattr(hp, "llm_ile_cikar", lambda *a, **k: {"_izler": {}})

    sonuc = kaydi_hibrit_cikar("metin")
    assert sonuc["kar_payi_orani_percent"] == 1.89, "Dusuk guvenli deger duzeltilmedi"
    assert sonuc["_kaynaklar"]["kar_payi_orani_percent"] == "ner"


def test_yuksek_guvenli_regex_degeri_korunur(monkeypatch):
    """Kilitleme esigi yuksek kesinligi KORUMALI: regex'in baglam
    eslesmeli (0.85-0.9) sonuclari daha dusuk guvenli bir adayla
    degistirilmemeli."""
    monkeypatch.setattr(
        hp, "kaydi_cikar",
        lambda m: _bos_regex_ciktisi(kar_payi_orani_percent=(1.89, 0.9)),
    )
    monkeypatch.setattr(
        hp, "ner_ile_cikar",
        lambda m, sadece_bu_alanlar=None: {
            "kar_payi_orani_percent": 99.0,
            "_izler": {"kar_payi_orani_percent": ("%99", 0.7)},
        },
    )
    monkeypatch.setattr(hp, "llm_ile_cikar", lambda *a, **k: {"_izler": {}})

    sonuc = kaydi_hibrit_cikar("metin")
    assert sonuc["kar_payi_orani_percent"] == 1.89
    assert sonuc["_kaynaklar"]["kar_payi_orani_percent"] == "regex"


def test_catisma_audit_icin_kaydedilir(monkeypatch):
    """Juri Audit Paneli: hangi katman ne onerdi, neden bu secildi?"""
    monkeypatch.setattr(
        hp, "kaydi_cikar",
        lambda m: _bos_regex_ciktisi(vade_ay=(120, 0.9)),
    )
    monkeypatch.setattr(
        hp, "ner_ile_cikar",
        lambda m, sadece_bu_alanlar=None: {
            "vade_ay": 36, "_izler": {"vade_ay": ("36 ay", 0.5)},
        },
    )
    monkeypatch.setattr(hp, "llm_ile_cikar", lambda *a, **k: {"_izler": {}})

    sonuc = kaydi_hibrit_cikar("metin")
    catismalar = sonuc["_catismalar"]
    assert len(catismalar) == 1
    c = catismalar[0]
    assert c["alan"] == "vade_ay"
    assert c["devralindi"] is False
    assert c["yeni_katman"] == "ner"
    # Adaylar da izlenebilir olmali
    assert len(sonuc["_adaylar"]["vade_ay"]) == 2


def test_dusuk_guvenli_alanlar_LLMe_SORULMAZ(monkeypatch):
    """MALIYET KURALI: LLM her alana SABIT 0.6 guven verir; devralma
    `yeni > mevcut` istedigi icin 0.6'lik bir aday, 0.6'lik bir alani
    devralamaz. Yani dusuk guvenli alani LLM'e sormak matematiksel olarak
    hicbir zaman ise yaramaz - yalnizca 150-300 sn'lik bir cagriyi bosa
    harcar. LLM'e YALNIZCA bos alanlar sorulmali."""
    monkeypatch.setattr(
        hp, "kaydi_cikar",
        lambda m: _bos_regex_ciktisi(
            kar_payi_orani_percent=(10.0, 0.6),   # dusuk guvenli, DOLU
            vade_ay=(12, 0.9),
            taksit_sayisi=(6, 0.85),
            erteleme_suresi_ay=(2, 0.85),
            finansman_tutari=(1000.0, 0.85),
            odul_miktari=(50.0, 0.85),
            odul_birimi=("TL", 0.85),
            masraf_durumu=("yok", 0.85),
            hedef_kitle=("yeni", 0.85),
            kampanya_bitis=("2026-12-31", 0.85),
            kar_payi_orani_decimal=(0.1, 0.6),
        ),
    )
    monkeypatch.setattr(hp, "ner_ile_cikar", lambda m, sadece_bu_alanlar=None: {"_izler": {}})

    llm_sorulan = {}

    def _izleyen_llm(ham_metin, sadece_bu_alanlar=None):
        llm_sorulan["alanlar"] = sadece_bu_alanlar
        return {"_izler": {}}

    monkeypatch.setattr(hp, "llm_ile_cikar", _izleyen_llm)
    kaydi_hibrit_cikar("metin")

    # Hicbir alan BOS degil -> LLM hic cagrilmamali
    assert "alanlar" not in llm_sorulan, (
        f"LLM gereksiz cagrildi: {llm_sorulan.get('alanlar')}"
    )

"""Hibrit Bilgi Cikarim Boru Hatti (Sprint 2 Gun 3).

Sartname madde 5.3/5.6: uc bagimsiz cikarim katmanini (regex -> NER ->
LLM) kademeli olarak birlestirir. Rapor Bolum 5.6: "regex + LLM hibrit
kullanilir cunku regex sayisal alanlarda halusinasyon riski tasimadan
yuksek kesinlik saglar; LLM ise regex'in yakalayamadigi dolayli
ifadeleri genelleyebilir. Asla yalnizca LLM'e guvenilmez."

TEMEL KURAL: Bir katmanin doldurdugu alan, sonraki katman tarafindan
ASLA EZILMEZ. Regex en yuksek kesinlikli katmandir ve her zaman once
calisir; NER ve LLM yalnizca regex'in (ve sirasiyla NER'in) BOS
biraktigi alanlara bakar. Bu, ner_extractor.py ve llm_extractor.py'nin
kendi testlerinde de dogrulanan `sadece_bu_alanlar` sozlesmesiyle
saglanir (bkz. tests/test_ner_extractor.py::
test_sadece_bu_alanlar_filtresi_disindaki_alanlari_doldurmaz).

PERFORMANS: Regex zaten TUM alanlari doldurduysa (ornegin kisa/basit
bir kampanya metni), NER modeli hic yuklenmez ve Ollama'ya hic istek
atilmaz - gereksiz gecikme/kaynak kullanimindan kacinilir.

BILINEN SINIRLAMA: regex hicbir alani bulamadigi en kotu durumda, NER'e
tek seferde COK sayida alan sorulmus olabilir - ner_extractor.py'nin
kendi modul dokumantasyonunda belirttigi gibi, GLiNER'e ayni anda cok
etiket sorulmasi bazi alanlarda (ornegin odul/finansman tutari
karisikligi) guveni dusurebilir. Gercek kampanya metinlerinde regex
genellikle alanlarin coğunu zaten doldurdugu icin (Extraction Accuracy
%84.38) bu durum nadir olmalidir; NER/LLM katmanlarinin kendi ic
guven esikleri (GLiNER: 0.4, LLM'in kar_payi/odul guard'lari) yine de
supheli sonuclari elemeye devam eder.

KAPSAM DISI ALANLAR: "kampanya_turu" (anahtar-kelime siniflandirmasi,
span-cikarim gorevine uygun degil) ve "kampanya_baslangic" (NER/LLM
etiket/alan setine henuz eklenmedi) yalnizca regex tarafindan
doldurulur - bu iki alan icin regex bulamazsa deger None kalir. Bu,
hybrid_pipeline.py'nin bilerek biraktigi bir kapsam sinirlamasidir,
ekiple degerlendirilmesi gereken ayri bir tasarim sorusudur.
"""

from __future__ import annotations

from extraction.llm_extractor import llm_ile_cikar
from extraction.ner_extractor import ner_ile_cikar
from extraction.regex_extractor import kaydi_cikar

# NER ve LLM'in ortak olarak destekledigi alanlar (bkz. ner_extractor.
# _ETIKET_ESLEME ve llm_extractor._ALAN_ACIKLAMALARI - ikisi de ayni
# alan kumesini kapsar). "kampanya_turu"/"kampanya_baslangic" BURADA
# YOK (bkz. modul docstring'i, "KAPSAM DISI ALANLAR").
_NER_LLM_DESTEKLI_ALANLAR = {
    "kar_payi_orani_percent", "kar_payi_orani_decimal",
    "vade_ay", "taksit_sayisi", "erteleme_suresi_ay",
    "finansman_tutari", "odul_miktari", "odul_birimi",
    "masraf_durumu", "hedef_kitle", "kampanya_bitis",
}


def _eksik_alanlari_bul(alanlar: dict) -> set[str]:
    return {alan for alan in _NER_LLM_DESTEKLI_ALANLAR if alanlar.get(alan) is None}


def _katman_sonucunu_birlestir(
    alanlar: dict, izler: dict, kaynaklar: dict, katman_sonucu: dict, katman_adi: str
) -> None:
    """katman_sonucu'ndaki degerleri, `alanlar` icinde HALA None olan
    alanlara yazar. Daha once baska bir katman tarafindan doldurulmus
    bir alan asla ezilmez - hibrit boru hattinin tek kuralı budur."""
    katman_izler = katman_sonucu.get("_izler", {})
    for alan, deger in katman_sonucu.items():
        if alan == "_izler" or deger is None:
            continue
        if alanlar.get(alan) is not None:
            continue
        alanlar[alan] = deger
        if alan in katman_izler:
            izler[alan] = katman_izler[alan]
        kaynaklar[alan] = katman_adi


def kaydi_hibrit_cikar(ham_metin: str) -> dict:
    """Regex -> NER -> LLM sirasiyla ham metinden CampaignRecord
    alanlarini cikarir.

    Donen sozluk regex_extractor.kaydi_cikar() ile ayni alanlara ek
    olarak iki denetim alani tasir:
      - "_izler": {"alan": (kaynak_span, guven)} - uc motorun ortak
        formati (regex_extractor.kaydi_cikar / ner_extractor.
        ner_ile_cikar / llm_extractor.llm_ile_cikar ile ayni sekil).
      - "_kaynaklar": {"alan": "regex" | "ner" | "llm"} - alani HANGI
        katmanin doldurdugunu tasir (Juri Audit Paneli / hata ayiklama
        icin - rapor Bolum 15).

    Bir katman bulamadigi/basarisiz oldugu alanlari sessizce atlar
    (ornegin Ollama kapaliysa llm_ile_cikar tum alanlari None doner) -
    hicbir katman zorunlu degildir, en kotu durumda regex'in tek basina
    urettigi sonuc donulur (kademeli fallback, rapor Bolum 8).
    """
    alanlar = kaydi_cikar(ham_metin)
    izler = alanlar.pop("_izler")
    kaynaklar = {alan: "regex" for alan in izler}

    eksik = _eksik_alanlari_bul(alanlar)
    if eksik:
        ner_sonucu = ner_ile_cikar(ham_metin, sadece_bu_alanlar=eksik)
        _katman_sonucunu_birlestir(alanlar, izler, kaynaklar, ner_sonucu, "ner")

    eksik = _eksik_alanlari_bul(alanlar)
    if eksik:
        llm_sonucu = llm_ile_cikar(ham_metin, sadece_bu_alanlar=eksik)
        _katman_sonucunu_birlestir(alanlar, izler, kaynaklar, llm_sonucu, "llm")

    alanlar["_izler"] = izler
    alanlar["_kaynaklar"] = kaynaklar
    return alanlar

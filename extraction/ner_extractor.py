"""GLiNER Tabanli Bilgi Cikarim Motoru (Faz 2 - baglamsal katman).

Sartname madde 5.3 "Finansal Bilgi Cikarimi" icin regex'in kacirdigi
baglamsal/dolayli ifadeleri yakalayan orta-guvenli katman.

NEDEN BERTURK DEGIL, GLINER: Sprint 2 Gun 1'de once BERTurk denendi
(dbmdz/bert-base-turkish-cased) - bu checkpoint NER icin hic fine-tune
edilmemis (rastgele baslatilmis siniflandirma katmani, LABEL_0/LABEL_1).
Gercek bir NER fine-tune'u (savasy/bert-base-turkish-ner-cased) denendiginde
ise klasik varliklari (ORG: "Kuveyt Turk") dogru buluyor ama rehberin
kendi one gordugu gibi hicbir finansal kavrami (kar payi orani, vade,
tutar) yakalayamiyor - bu beklenen bir durum, cunku model kisi/yer/kurum
icin egitilmis, finansal alan icin degil. Ayrica bankanin adi zaten
scraper'in ham kaydinda (banka alani) hazir geliyor, NER ile ayrica
cikarilmasina gerek yok.

GLiNER (zero-shot, urchade/gliner_multi-v2.1) ise etiket adini dogrudan
soyleyerek calisir, finansal kavramlari yakalayabiliyor - ama regex kadar
kesin degil, gercek veriyle test edilirken 4 onemli bulgu ortaya cikti:

1. TUM etiketler birden sorulunca dusuk guvenle yanlis kategoriye
   dusebiliyor: "400 TL Bankkart Lira" -> "finansman tutari" sandi (0.52),
   "odul miktari" DEGIL. Ama SADECE odul alanlari sorulduğunda ayni ifade
   dogru kategoriye VE cok daha yuksek guvenle giriyor (0.87). Bu yuzden
   `sadece_bu_alanlar` parametresi ZORUNLU kullanilmali - hybrid_pipeline
   NER'e her zaman regex'in bos biraktigi SPESIFIK alanlari sormali, tum
   etiketleri birden degil.
2. Bazi acik ifadeleri de kaciriyor: "40.000 TL'ye kadar" gibi bir tutar,
   ayni cumlede baska bir odul/oran bulunmuşsa atlanabiliyor.
3. UZUN METINLERDE SESSIZCE KIRPIYOR: GLiNER'in ic tokenizer'i ~384 token
   sinirinda kesiyor ("Sentence of length 603 has been truncated to 384"
   gibi bir uyari veriyor ama METNI KIRPIYOR, hata vermiyor). Gercek
   kampanya sayfalarinin cogu bu sinirin altinda ama uzun sayfalarda
   sayfanin SONUNDAKI bilgi (ör. kampanya kosullari, tarih araligi)
   hic gorulmeyebilir - LLM icin planlanan token butcesi yonetimi
   (rehber Sprint 2 Gun 2) NER icin de dusunulmeli.
4. TURKCE AKSAN DUYARLI: "yuzde 1,89 kar payi orani" (ASCII, aksansiz)
   HIC bulunamadi, ama "yüzde 1,89 kâr payı oranı" (dogru Turkce
   karakterlerle) 0.44 guvenle dogru bulundu. Bu, regex'teki â/ı
   tuzagindan FARKLI bir sorun - regex'te karakter siniflariyla (â|a)
   duzeltilebiliyordu, ama GLiNER'in kendi anlamsal eslestirmesi aksansiz
   metinde zayifliyor, kod tarafinda basit bir duzeltmesi yok. Gercek
   taranmis web metni genelde dogru aksanli oldugu icin bu risk dusuk,
   ama OCR/PDF kaynakli metinlerde (Zeynep'in PDF islem hattinda) aksan
   kaybi olursa NER performansi dusebilir.
5. KESIRLI ORAN TUZAGI (KRITIK): "98/2" gibi kesirli kar paylasim
   formatlari (terminology/sozluk.json'daki kesirli_kar_paylasimi
   kavrami) GLiNER tarafindan "kar payi orani" olarak etiketlenebiliyor
   (gercek Albaraka verisinde dogrulandi: "98/2 paylasim oranli Dijital
   Katilma hesabinizi"). Bunu dogrudan yuzdeye_cevir()'e vermek '98/2'yi
   YANLISLIKLA %98 yapardi - bu yuzden `_kesirli_oran_mi()` guard'i ile
   bu format ASLA otomatik yuzdeye cevrilmez, alan bos (None) birakilir.

Bu yuzden GLiNER'in ciktisi TEK BASINA guvenilmez - regex zaten doldurmus
alanlara asla dokunulmaz (yalnizca BOS alanlar icin denenir), ve dusuk
guven skorlari Validator/Confidence katmaninda (Sprint 2 Gun 3, hybrid_pipeline)
ayrica degerlendirilir.
"""

from __future__ import annotations

import re
from typing import Optional

from extraction.normalizer import aya_cevir, tarihe_cevir, tutara_cevir, yuzdeye_cevir

_MODEL_ADI = "urchade/gliner_multi-v2.1"


def _ilk_sayi(ham: str) -> Optional[int]:
    """'12 taksit' / '12' -> 12. Taksit sayisi icin - vade_ay'daki 'ay'
    zorunlulugu burada aranmaz, sadece ilk tam sayi alinir."""
    m = re.search(r"\d+", ham)
    return int(m.group(0)) if m else None


def _kar_payi_makul_mu(percent: float) -> bool:
    """extraction/regex_extractor.py'deki AYNI kontrol (tutarlilik icin
    kopyalandi - iki motor da bagimsiz calisabilmeli). Aylik kar payi
    oranlari gercek veride %0-%10 araliginda gozlemlendi; %15 ustu bir
    deger GLiNER'in yanlis bir yuzdeyi (ör. yillik maliyet orani) kar
    payi sanmasi ihtimalidir - supheli deger, uydurmaktan iyidir None
    birakmak (rapor Bolum 5.7/15)."""
    return 0.0 <= percent <= 15.0


_KESIRLI_ORAN_DESENI = re.compile(r"\d{1,3}\s*/\s*\d{1,3}")


def _kesirli_oran_mi(ham: str) -> bool:
    """'98/2' gibi kesirli kar paylasim formatlarini tespit eder. GLiNER
    bu ifadeyi 'kar payi orani' etiketiyle yakalayabiliyor (gercek Albaraka
    verisinde "98/2 paylasim oranli" ornegiyle dogrulandi), ama bunu
    yuzdeye_cevir()'e vermek '98/2' -> %98 gibi TAMAMEN YANLIS ve tehlikeli
    bir yorum uretir - '98/2' musteri/banka paylasim orani anlamina gelir,
    duz bir yuzde DEGILDIR (terminology/sozluk.json'daki kesirli_kar_paylasimi
    kavramiyla ayni tuzak - regex_extractor.py da bu formati bilerek
    yuzdeye cevirmez, ham deger olarak birakir)."""
    return bool(_KESIRLI_ORAN_DESENI.search(ham))


# "kâr payı oranı" ozel durum - TEK entity'den IKI alan (percent + decimal)
# doldurulmasi gerekiyor (rapor Bolum 5.1: formul karisikligini onlemek
# icin yuzde ikili saklanir), bu yuzden asagidaki genel tek-alan
# eslemesinin DISINDA, ayri islenir (bkz. ner_ile_cikar).
_KAR_PAYI_ETIKETI = "kâr payı oranı"

# GLiNER etiketi -> (CampaignRecord alan adi, donusum fonksiyonu ya da None)
# None ise ham metin oldugu gibi saklanir (masraf_durumu, hedef_kitle gibi
# serbest metin alanlari icin donusum gerekmez). "kâr payı oranı" BURADA
# YOK - yukarida ayri ele alinir.
_ETIKET_ESLEME: dict[str, tuple[str, Optional[callable]]] = {
    "vade süresi": ("vade_ay", aya_cevir),
    "taksit sayısı": ("taksit_sayisi", _ilk_sayi),
    "ödemesiz dönem": ("erteleme_suresi_ay", aya_cevir),
    "finansman tutarı": ("finansman_tutari", tutara_cevir),
    "ödül miktarı": ("odul_miktari", tutara_cevir),
    "ödül birimi": ("odul_birimi", None),
    "masraf durumu": ("masraf_durumu", None),
    "hedef müşteri segmenti": ("hedef_kitle", None),
    "kampanya tarihi": ("kampanya_bitis", tarihe_cevir),
}

_TUM_ALAN_ADLARI = ["kar_payi_orani_percent", "kar_payi_orani_decimal"] + [
    alan for alan, _ in _ETIKET_ESLEME.values()
]

_GUVEN_ESIGI = 0.4

_model = None


def _model_yukle():
    """GLiNER modelini bir kere yukler, sonraki cagrilar cache'ten doner
    (model yuklemesi/indirmesi pahalidir, her metin icin tekrar yapilmamali)."""
    global _model
    if _model is None:
        from gliner import GLiNER

        _model = GLiNER.from_pretrained(_MODEL_ADI)
    return _model


def ner_ile_cikar(
    ham_metin: str, sadece_bu_alanlar: Optional[set[str]] = None
) -> dict:
    """GLiNER ile ham metinden CampaignRecord alanlarini cikarmaya calisir.

    `sadece_bu_alanlar` verilirse (ornek: regex'in bos biraktigi alan
    adlari), yalnizca o alanlara karsilik gelen etiketler aranir - hem
    performans hem de zaten regex'in yuksek guvenle doldurdugu bir alani
    NER'in dusuk guvenle EZMEMESI icin (hybrid_pipeline.py'nin Sprint 2
    Gun 3'te uygulayacagi kural budur).

    Donen: {"alan_adi": deger, ..., "_izler": {"alan_adi": (ham_span, guven)}}
    Regex_extractor.kaydi_cikar() ile AYNI seklde - hybrid_pipeline'da
    dogrudan birlestirilebilsin diye.
    """
    model = _model_yukle()

    kar_payi_isteniyor = sadece_bu_alanlar is None or bool(
        sadece_bu_alanlar & {"kar_payi_orani_percent", "kar_payi_orani_decimal"}
    )
    if sadece_bu_alanlar is None:
        etiketler_ve_eslesme = dict(_ETIKET_ESLEME)
    else:
        etiketler_ve_eslesme = {
            etiket: esleme
            for etiket, esleme in _ETIKET_ESLEME.items()
            if esleme[0] in sadece_bu_alanlar
        }
    if kar_payi_isteniyor:
        etiketler_ve_eslesme[_KAR_PAYI_ETIKETI] = None  # ozel islenecek, esleme kullanilmaz

    alanlar: dict = {alan: None for alan in _TUM_ALAN_ADLARI}
    izler: dict[str, tuple[str, float]] = {}

    if not etiketler_ve_eslesme:
        alanlar["_izler"] = izler
        return alanlar

    etiket_listesi = list(etiketler_ve_eslesme.keys())
    varliklar = model.predict_entities(ham_metin, etiket_listesi, threshold=_GUVEN_ESIGI)

    # Ayni alan icin birden fazla aday varsa EN YUKSEK skorlu olan tutulur.
    for varlik in sorted(varliklar, key=lambda v: v["score"], reverse=True):
        ham_deger = varlik["text"]
        guven = round(float(varlik["score"]), 4)

        if varlik["label"] == _KAR_PAYI_ETIKETI:
            if alanlar["kar_payi_orani_percent"] is not None:
                continue
            if _kesirli_oran_mi(ham_deger):
                # "98/2" gibi kesirli paylasim orani - ASLA duz yuzdeye
                # cevrilmez (bkz. _kesirli_oran_mi docstring). Sprint 2'de
                # bu format icin ayri bir kesirli-oran alani/kavrami
                # eklenmesi gerekebilir (rehber Sprint 1'de terminology
                # tarafinda zaten "kesirli_kar_paylasimi" olarak var,
                # extraction semasina henuz baglanmadi).
                continue
            oran_decimal = yuzdeye_cevir(ham_deger)
            if oran_decimal is None or not _kar_payi_makul_mu(round(oran_decimal * 100, 4)):
                continue
            alanlar["kar_payi_orani_decimal"] = oran_decimal
            alanlar["kar_payi_orani_percent"] = round(oran_decimal * 100, 4)
            izler["kar_payi_orani_percent"] = (ham_deger, guven)
            continue

        alan_adi, donusum = etiketler_ve_eslesme[varlik["label"]]
        if alanlar[alan_adi] is not None:
            continue  # bu alan icin zaten daha yuksek skorlu bir aday bulundu

        deger = donusum(ham_deger) if donusum else ham_deger
        if deger is None:
            continue  # donusum basarisiz oldu (ör. sayi cikarilamadi), atla

        alanlar[alan_adi] = deger
        izler[alan_adi] = (ham_deger, guven)

    alanlar["_izler"] = izler
    return alanlar

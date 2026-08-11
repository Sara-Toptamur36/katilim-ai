"""Hibrit Bilgi Cikarim Boru Hatti (Sprint 2 Gun 3).

Sartname madde 5.3/5.6: uc bagimsiz cikarim katmanini (regex -> NER ->
LLM) kademeli olarak birlestirir. Rapor Bolum 5.6: "regex + LLM hibrit
kullanilir cunku regex sayisal alanlarda halusinasyon riski tasimadan
yuksek kesinlik saglar; LLM ise regex'in yakalayamadigi dolayli
ifadeleri genelleyebilir. Asla yalnizca LLM'e guvenilmez."

TEMEL KURAL - ADAY + UZLASTIRICI (guven esikli):
Her katman bir alan icin ADAY deger uretir. Bir alan, onu dolduran
katmanin guveni KILITLEME_GUVEN_ESIGI'nin (0.8) ustundeyse kilitlenir
ve sonraki katmanlar onu ezemez. Altindaysa daha yuksek guvenli bir
aday devralabilir.

NEDEN DEGISTI: Ilk tasarimda kural "bir katmanin doldurdugu alan ASLA
ezilmez" idi. Bu yuksek kesinlik saglıyordu ama regex YANLIS bir deger
urettiginde hata KALICI oluyordu. Olculen kanit
(docs/extraction_accuracy_raporu.md): 6 yanlis pozitifin 4'u
kar_payi_orani alanindaydi ve regex'in 0.6 guvenli "genel yuzde"
fallback'inden geliyordu - sonraki katmanlar bunlari duzeltemiyordu.
Mentor denetiminde de "regex kilitleme riski" olarak isaretlendi.

Esik, regex'in guvenilir baglam-eslesmeli kaliplarinin (0.85-0.9) ile
hataya acik fallback'inin (0.6) arasina konmustur: yuksek kesinlik
korunur, hatali dusuk-guvenli tahminler duzeltilebilir hale gelir.

Her catisma `_catismalar` altinda kaydedilir (hangi katman ne onerdi,
neden bu secildi) - Juri Audit Paneli icin.

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

KAPSAM DISI ALANLAR (yalnizca regex doldurur, NER/LLM'e sorulmaz):
  - "kampanya_turu"      : anahtar-kelime siniflandirmasi, span-cikarim degil
  - "kampanya_baslangic" : NER/LLM etiket/alan setine henuz eklenmedi
  - "tahsis_ucreti"      : gercek veride TL tutari olarak neredeyse hic
                           gecmiyor; regex bunu yalnizca "masraf alinmaz"
                           ifadesinden 0.0 olarak turetir (bkz.
                           regex_extractor.py masraf blogu). LLM'e sormak,
                           olmayan bir tutari uydurmasini davet ederdi.
  - "kampanya_avantaji"  : cikarilan alanlardan DERLENIR, metinden
                           cikarilmaz (bkz. regex_extractor.
                           kampanya_avantajini_olustur) - bu yuzden
                           katmanlar arasi uzlastirmaya hic girmez.
Bu alanlar icin regex bulamazsa deger None kalir; bilerek birakilmis
kapsam sinirlamalaridir.
"""

from __future__ import annotations

from extraction.llm_extractor import llm_ile_cikar
from extraction.ner_extractor import ner_ile_cikar
from extraction.regex_extractor import kampanya_avantajini_olustur, kaydi_cikar

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

# DENETIM BULGUSU (ablation olcumu, docs/extraction_accuracy_raporu.md
# "Ablation: katman katkisi" bolumu): NER'e finansman_tutari sorulmasi
# OLCULEBILIR HICBIR KATKI SAGLAMAZ ve GERCEK ZARAR VERIR. Kart
# kampanyalarinda ("400 TL Bankkart Lira", "1.250 TL Worldpuan" gibi)
# GLiNER odul tutarini finansman_tutari sanip 7/7 yanlis pozitif uretti
# (Makro F1 -3,81, 6 saniyelik model yuklemesi + 186 saniyelik toplu
# cagri karsiliginda). Bu, ner_extractor.py'nin kendi modul
# dokumantasyonundaki 1. bulguyla (odul/finansman tutari karisikligi,
# "400 TL Bankkart Lira" -> "finansman tutari" (0.52) sanmasi) birebir
# ortusuyor - tesadufi degil, GLiNER'in bu iki kavrami ayirt edemedigi
# sistemik bir sinirdir. LLM ayni sekilde zarar verdigi OLCULMEDI (LLM'in
# kendi odul-anahtar-kelime guard'i - llm_extractor.py - zaten bu
# turden bir karisikliga karsi ayrica korumali), bu yuzden yalnizca NER
# icin disarida birakilir, LLM icin degil.
_NER_HARIC_ALANLAR = {"finansman_tutari"}


# LLM katmaninin urettigi sabit guven (bkz. llm_extractor.py: izlere
# her alan icin 0.6 yazilir). Asagida neden onemli oldugu aciklaniyor.
_LLM_SABIT_GUVENI = 0.6


def _adaya_acik_alanlar(
    alanlar: dict, izler: dict, dusuk_guvenlileri_dahil_et: bool
) -> set[str]:
    """Sonraki katmana sorulacak alanlar.

    `dusuk_guvenlileri_dahil_et=True` ise bos alanlara EK OLARAK, dusuk
    guvenle doldurulmus alanlar da sorulur - bu, regex'in YANLIS ama dolu
    biraktigi bir alanin duzeltilebilmesini saglar ("regex kilitleme"
    sorununun cozumu).

    NEDEN HER KATMAN ICIN AYNI DEGIL: LLM katmani her alana SABIT 0.6
    guven verir (llm_extractor.py). Devralma kurali `yeni_guven >
    mevcut_guven` istedigi icin, LLM ancak guveni 0.6'DAN KUCUK bir alani
    devralabilir - regex ise en dusuk 0.6 uretir. Yani dusuk guvenli
    alanlari LLM'e sormak MATEMATIKSEL OLARAK hicbir zaman devralmaya yol
    acmaz; yalnizca gereksiz LLM cagrisi yapar (olculdu: GPU'suz makinede
    cagri basina 150-300 sn). Bu yuzden dusuk guvenli alanlar YALNIZCA
    NER'e sorulur - GLiNER degisken guven uretir (esik 0.4) ve gercekten
    devralabilir.
    """
    acik = set()
    for alan in _NER_LLM_DESTEKLI_ALANLAR:
        if alanlar.get(alan) is None:
            acik.add(alan)
        elif dusuk_guvenlileri_dahil_et and (
            izler.get(alan, (None, 0.0))[1] < KILITLEME_GUVEN_ESIGI
        ):
            acik.add(alan)
    return acik


# KILITLEME ESIGI: Bir katman bir alani BU guvenin uzerinde doldurduysa
# sonraki katmanlar onu ezemez. Altindaysa daha yuksek guvenli bir aday
# devralabilir.
#
# 0.8 degeri gercek olcume dayanir (docs/extraction_accuracy_raporu.md):
# regex'in baglam eslesmeli kaliplari 0.85-0.9 guven uretir ve bunlar
# guvenilirdir; 0.6'lik "genel yuzde" fallback'i ise olculen 6 yanlis
# pozitifin 4'unu tek basina uretmisti. Esik tam bu ikisinin arasina
# konarak yuksek kesinlik korunur, hatali dusuk-guvenli tahminler ise
# duzeltilebilir hale gelir.
KILITLEME_GUVEN_ESIGI = 0.8


def _katman_sonucunu_birlestir(
    alanlar: dict,
    izler: dict,
    kaynaklar: dict,
    katman_sonucu: dict,
    katman_adi: str,
    adaylar: dict,
    catismalar: list,
) -> None:
    """Katmanin urettigi degerleri ADAY olarak kaydeder ve gerekiyorsa
    mevcut degeri devralir.

    ESKI DAVRANIS (ve neden degisti): once "bir katmanin doldurdugu alan
    ASLA ezilmez" kurali vardi. Bu, yuksek kesinlik saglıyordu ama regex
    YANLIS bir deger urettiginde hata KALICI oluyordu - sonraki katmanlar
    duzeltemiyordu. Mentor denetiminde de "regex kilitleme riski" olarak
    isaretlendi.

    YENI DAVRANIS: alan, onu dolduran katmanin guveni
    KILITLEME_GUVEN_ESIGI'nin ustundeyse kilitlidir. Altindaysa, daha
    yuksek guvenli bir aday devralabilir. Devralma olsun olmasin, farkli
    deger oneren her katman `_catismalar`'a yazilir - Juri Audit
    Paneli'nde "hangi katman ne onerdi, neden bu secildi?" gorunur.
    """
    katman_izler = katman_sonucu.get("_izler", {})

    for alan, deger in katman_sonucu.items():
        if alan == "_izler" or deger is None:
            continue

        guven = katman_izler.get(alan, (None, 0.0))[1]
        adaylar.setdefault(alan, []).append(
            {"katman": katman_adi, "deger": deger, "guven": guven}
        )

        mevcut = alanlar.get(alan)
        if mevcut is None:
            alanlar[alan] = deger
            if alan in katman_izler:
                izler[alan] = katman_izler[alan]
            kaynaklar[alan] = katman_adi
            continue

        # Alan zaten dolu - ayni degeri oneriyorsa yapacak bir sey yok
        if mevcut == deger:
            continue

        mevcut_guven = izler.get(alan, (None, 0.0))[1]
        devralindi = (
            mevcut_guven < KILITLEME_GUVEN_ESIGI and guven > mevcut_guven
        )

        catismalar.append(
            {
                "alan": alan,
                "korunan" if not devralindi else "onceki": mevcut,
                "onceki_katman": kaynaklar.get(alan),
                "onceki_guven": mevcut_guven,
                "yeni_katman": katman_adi,
                "yeni_deger": deger,
                "yeni_guven": guven,
                "devralindi": devralindi,
            }
        )

        if devralindi:
            alanlar[alan] = deger
            if alan in katman_izler:
                izler[alan] = katman_izler[alan]
            kaynaklar[alan] = katman_adi


def kaydi_hibrit_cikar(
    ham_metin: str, ner_kullan: bool = True, llm_kullan: bool = True
) -> dict:
    """Regex -> NER -> LLM sirasiyla ham metinden CampaignRecord
    alanlarini cikarir.

    KATMAN ANAHTARLARI (`ner_kullan` / `llm_kullan`): ablation olcumu
    icin eklendi - "her katman NE KATIYOR?" sorusu ancak ust katmanlar
    kapatilarak cevaplanabilir (bkz. scraper/scripts/ablation.py).
    Varsayilanlar True'dur; mevcut cagiran kod etkilenmez.

    Regex katmani kapatilamaz: boru hattinin temeli odur ve digerleri
    onun bos biraktigi alanlar uzerinde calisir.

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
    adaylar: dict[str, list[dict]] = {
        alan: [{"katman": "regex", "deger": alanlar.get(alan), "guven": iz[1]}]
        for alan, iz in izler.items()
    }
    catismalar: list[dict] = []

    # NER: bos alanlar + dusuk guvenli alanlar (ucuz, gercekten devralabilir)
    # EKSI _NER_HARIC_ALANLAR (olculdu: zarar verdigi kanitlanan alanlar,
    # bkz. modul basi DENETIM BULGUSU).
    if ner_kullan:
        acik = _adaya_acik_alanlar(alanlar, izler, dusuk_guvenlileri_dahil_et=True) - _NER_HARIC_ALANLAR
        if acik:
            ner_sonucu = ner_ile_cikar(ham_metin, sadece_bu_alanlar=acik)
            _katman_sonucunu_birlestir(
                alanlar, izler, kaynaklar, ner_sonucu, "ner", adaylar, catismalar
            )

    # LLM: YALNIZCA hala bos alanlar (bkz. _adaya_acik_alanlar docstring'i -
    # sabit 0.6 guveniyle dusuk guvenli bir alani devralmasi imkansiz,
    # sormak yalnizca 150-300 sn'lik bir cagriyi bosa harcardi)
    if llm_kullan:
        acik = _adaya_acik_alanlar(alanlar, izler, dusuk_guvenlileri_dahil_et=False)
        if acik:
            llm_sonucu = llm_ile_cikar(ham_metin, sadece_bu_alanlar=acik)
            _katman_sonucunu_birlestir(
                alanlar, izler, kaynaklar, llm_sonucu, "llm", adaylar, catismalar
            )

    # Avantaj ozeti TUM katmanlar bittikten SONRA yeniden derlenir.
    # kaydi_cikar() bunu regex sonuclariyla zaten kurmustu; NER/LLM
    # arada yeni alanlar doldurmus olabilir (ornegin odul_miktari) ve
    # ozetin onlari da icermesi gerekir - aksi halde hibrit boru hatti,
    # regex-only calistirmayla AYNI avantaj metnini uretirdi.
    alanlar["kampanya_avantaji"] = kampanya_avantajini_olustur(alanlar)

    alanlar["_izler"] = izler
    alanlar["_kaynaklar"] = kaynaklar
    # Juri Audit Paneli / hata ayiklama icin: her alan icin hangi katman
    # ne onerdi, hangi catismalar yasandi ve neden bu deger secildi?
    alanlar["_adaylar"] = adaylar
    alanlar["_catismalar"] = catismalar
    return alanlar

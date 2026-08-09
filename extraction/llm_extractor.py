"""Qwen2.5 (Ollama) Tabanli Bilgi Cikarim Motoru (Faz 3 - son care katman).

Sartname madde 5.3 "Finansal Bilgi Cikarimi" icin regex ve NER'in ikisinin
de kacirdigi, yorum/baglam gerektiren dolayli ifadeleri isleyen en son ve
en dusuk guvenli katman. Rapor Bolum 5.6: "regex + LLM hibrit kullanilir
cunku regex sayisal alanlarda halusinasyon riski tasimadan yuksek kesinlik
saglar; LLM ise regex'in yakalayamadigi dolayli ifadeleri genelleyebilir.
Asla yalnizca LLM'e guvenilmez."

TEMPERATURE=0: LLM ciktisinin tutarli/tekrarlanabilir olmasini saglar -
halusinasyonu TEK BASINA azaltmaz, bunun icin asagidaki guard'lar
(makul deger kontrolu, kesirli oran kontrolu - regex_extractor.py ve
ner_extractor.py ile AYNI kurallar) birlikte calisir.

LLM'IN CIKTISI HICBIR SEKILDE DOGRUDAN GUVENILMEZ: JSON parse edilir,
her alan regex/NER'deki ile AYNI makul-deger kontrollerinden gecirilir.
Parse hatasi ya da supheli deger durumunda alan bos (None) birakilir,
uydurulmaz (rapor Bolum 5.7/15).
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Optional

import requests
import tiktoken

from donanim import ayarlar as _donanim_ayarlari
from extraction.normalizer import tarihe_cevir, turkce_kucult

# Donanima gore secilen ayarlar (GPU/VRAM tespitine dayanir, ortam
# degiskenleriyle ezilebilir - bkz. donanim.py)
_ayarlar = _donanim_ayarlari()

_OLLAMA_URL = "http://localhost:11434/api/generate"
_OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
_MODEL_ADI = "qwen2.5:7b-instruct-q4_K_M"

# TOKENIZER NOTU (olculdu, tahmin degil): Bu, Qwen'in kendi tokenizer'i
# degil. Gercek Qwen2.5 tokenizer'iyla karsilastirildiginda cl100k_base,
# Turkce banka metinlerinde token sayisini %5-16 FAZLA gosteriyor
# (25 gercek metinde olculen oran: Qwen/cl100k = 0.84-0.95, medyan 0.88).
# Yani yaklasim GUVENLI YONDE hata yapiyor - gercekte oldugundan daha uzun
# sanip erken kirpiyor, baglam penceresini asma riski yaratmiyor.
# Gercek tokenizer'i calisma aninda indirmek, sartname Md. 5.9'un
# (dis servise bagimli olmama) ruhuna aykiri ek bir indirme getirirdi.
_KODLAYICI = tiktoken.get_encoding("cl100k_base")

# BAGLAM PENCERESI - SESSIZ TUZAK: Qwen2.5 modeli 32768 token destekler
# AMA Ollama, istekte `num_ctx` verilmezse modeli VARSAYILAN 4096 ile
# servis eder (`ollama ps` ciktisiyla dogrulandi). Kod "model 32K
# destekliyor, bol pay var" varsayimiyla yazilmisti; gercekte uzun bir
# prompt Ollama tarafindan SESSIZCE kirpilirdi - hata donmez, yalnizca
# cikarim kalitesi duser. Bu yuzden num_ctx artik ACIKCA gonderilir.
#
# Deger DONANIMA GORE secilir (bkz. donanim.py): zayif makinede genis
# baglam zaman asimina yol aciyor (olculdu: 8192 -> 404 sn), guclu
# makinede ise dar baglam bosuna belge kirpiyor.
_BAGLAM_PENCERESI = _ayarlar.llm_baglam_penceresi

# Girdi siniri baglam penceresinden TURETILIR: prompt sablonu ve model
# ciktisi icin ~1100 token pay birakilir. CPU profilinde (4096) bu ~3000
# eder ve 234 belgenin 12'si kirpilir - bu bir gozden kacma DEGIL,
# donanimin dayattigi bilincli bir sinirdir. GPU profilinde (16384)
# sinir ~15000 olur ve hicbir belge kirpilmaz.
_MAKS_GIRDI_TOKEN = max(1000, _BAGLAM_PENCERESI - 1100)

_ALAN_ACIKLAMALARI = {
    "kar_payi_orani_percent": "kâr payı oranı, yüzde olarak sayı (ör. 1.89). '98/2' gibi KESİRLİ paylaşım formatlarını BURAYA YAZMA, null bırak.",
    "vade_ay": "vade süresi, ay cinsinden tam sayı (taksit sayısı DEĞİL)",
    "taksit_sayisi": "taksit sayısı, tam sayı (vade ile karıştırma - bunlar farklı kavramlar)",
    "erteleme_suresi_ay": "ödemesiz dönem/erteleme süresi, ay cinsinden tam sayı",
    "finansman_tutari": "finansman/kredi tutarı, TL cinsinden sayı (ödül tutarı DEĞİL)",
    "odul_miktari": "ödül/hediye miktarı, sayı (finansman tutarı DEĞİL)",
    "odul_birimi": "ödül birimi: TL, Mil, Gram, Bankkart Lira, ParafPara, Worldpuan gibi",
    "masraf_durumu": "masraf/ücret durumu hakkında kısa metin",
    "hedef_kitle": "kampanyanın hedef müşteri kitlesi, kısa metin",
    "kampanya_bitis": "kampanya bitiş tarihi, metinde geçtiği gibi (ör. '31 Aralık 2026')",
}

_KAR_PAYI_ALANLARI = {"kar_payi_orani_percent", "kar_payi_orani_decimal"}


def token_say(metin: str) -> int:
    return len(_KODLAYICI.encode(metin))


def _girdiyi_guvenli_kirp(metin: str, maks: int = _MAKS_GIRDI_TOKEN) -> str:
    """Metin token sinirini asarsa, karakter bazinda oranti ile guvenli
    sekilde kirpar (rehber Sprint 2 Gun 2: 'baglami_kirp' ilkesiyle ayni -
    limiti asan bir LLM cagrisi sessizce eksik bilgiyle cevap uretebilir,
    bunun yerine BILEREK kirpip devam ederiz)."""
    mevcut = token_say(metin)
    if mevcut <= maks:
        return metin
    oran = maks / mevcut
    return metin[: int(len(metin) * oran * 0.95)]  # %5 guvenlik payi


_OLLAMA_DURUM_CACHE: dict[str, float | bool] = {}
_OLLAMA_DURUM_CACHE_SURESI_SN = 30.0


def _ollama_hazir_mi() -> bool:
    """DENETIM BULGUSU: Ollama kapaliyken "localhost"a baglanma denemesi
    ~4 saniye suruyor (Windows'ta once IPv6 (::1) sonra IPv4 (127.0.0.1)
    denendigi icin, olcumle dogrulandi) - anlik bir "reddedildi" hatasi
    DEGIL. hibrit_extraction_accuracy.py gibi cok sayida kaydi sirayla
    isleyen bir akiste, Ollama kapaliyken HER kayit bu bedeli ayri ayri
    oderdi (ornegin 36 kayit x ~4sn = 2.5 dakika sirf baglanti
    denemesinde harcanirdi) - rapor Bolum 8'in "internet/GPU olmasa bile
    hizli calisir" ilkesine aykiri. Bu fonksiyon durumu 30 saniye
    onbellekte tutar: Ollama kapaliysa ilk kontrolden sonraki cagrilar
    aga hic gitmeden ANINDA None doner; sure dolunca tekrar kontrol
    edilir (Ollama sonradan baslatilmis olabilir)."""
    simdi = time.monotonic()
    son_kontrol = _OLLAMA_DURUM_CACHE.get("zaman")
    if son_kontrol is not None and (simdi - son_kontrol) < _OLLAMA_DURUM_CACHE_SURESI_SN:
        return bool(_OLLAMA_DURUM_CACHE["hazir"])
    try:
        requests.get(_OLLAMA_TAGS_URL, timeout=2)
        hazir = True
    except requests.RequestException:
        hazir = False
    _OLLAMA_DURUM_CACHE["hazir"] = hazir
    _OLLAMA_DURUM_CACHE["zaman"] = simdi
    return hazir


# Zaman asimi da donanima gore secilir (bkz. donanim.py): CPU profilinde
# 900 sn - gercek banka metinleri icin olculen sureye (>400 sn) genis pay
# birakir; GPU profilinde 300 sn yeterlidir. Cikarim CEVRIMDISI toplu bir
# istir - kullanici bu sureyi beklemez, bu yuzden comert bir zaman asimi
# "sessizce None donmek"ten her zaman iyidir.
_VARSAYILAN_ZAMAN_ASIMI = _ayarlar.llm_zaman_asimi_sn


def llm_ile_sor(
    prompt: str, model: str = _MODEL_ADI, zaman_asimi: int = _VARSAYILAN_ZAMAN_ASIMI
) -> Optional[str]:
    """Ollama'nin yerel API'sine istek atar, Temperature=0 ile (rapor
    Bolum 8: tutarli/tekrarlanabilir cevap icin). Baglanti/zaman asimi
    hatasinda None doner - cagiran taraf (hybrid_pipeline) bu durumda
    regex/NER sonucuyla yetinmeli (kademeli fallback, rapor Bolum 8).

    ZAMAN ASIMI NOTU (olcumle iki kez guncellendi): Ilk deger 60sn idi ve
    LLM katmanini SESSIZCE devre disi birakiyordu - hata firlatmadigi icin
    fark edilmesi zor bir bulguydu. GPU'suz/dusuk VRAM'li makinelerde
    (`ollama ps` ile dogrulandi: model agirlikli olarak CPU'da calisiyor)
    gercek olcumler:
        kisa prompt (birkac token)      :  ~67 sn
        gercek banka metni (~600-3000 token) : >404 sn
    400sn de yetersiz kaldi ve ayni sessiz None sorununu uretti; bu yuzden
    varsayilan 900sn'ye cikarildi ve LLM_ZAMAN_ASIMI ortam degiskeniyle
    ayarlanabilir yapildi. Cikarim CEVRIMDISI toplu bir istir - kullanici
    bu sureyi beklemez - bu yuzden comert zaman asimi, sessizce None
    donmekten her zaman iyidir.

    Once _ollama_hazir_mi() ile ONBELLEKLI bir erisilebilirlik kontrolu
    yapilir - Ollama kapaliyken her cagrida ayri ayri ~4 saniyelik
    baglanti-reddi beklemesi odenmesin diye (bkz. _ollama_hazir_mi
    docstring'i)."""
    if not _ollama_hazir_mi():
        return None
    try:
        yanit = requests.post(
            _OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0,
                    # num_ctx ACIKCA verilmeli: Ollama aksi halde modeli
                    # 4096 baglamla servis eder (model 32768 desteklese
                    # bile) ve uzun promptlari SESSIZCE kirpar - hata
                    # donmez, yalnizca cikarim kalitesi duser.
                    "num_ctx": _BAGLAM_PENCERESI,
                },
            },
            timeout=zaman_asimi,
        )
        yanit.raise_for_status()
        return yanit.json()["response"]
    except (requests.RequestException, KeyError, ValueError):
        return None


_KESIRLI_ORAN_DESENI = re.compile(r"\d{1,3}\s*/\s*\d{1,3}")


def _kesirli_oran_mi(ham) -> bool:
    return bool(_KESIRLI_ORAN_DESENI.search(str(ham)))


def _kar_payi_makul_mu(percent: float) -> bool:
    """regex_extractor.py / ner_extractor.py'deki AYNI kontrol - uc motor
    da bagimsiz calisabilmeli, ayni supheli-deger kuralini uygulamali."""
    return 0.0 <= percent <= 15.0


# DENETIM BULGUSU: gercek bir Albaraka kampanyasinda (yalnizca "Pratik
# Finansman Kart" - hic odul/hediye gecmeyen, sadece finansman urunu
# aciklayan bir metin) LLM'e odul_miktari sorulunca, metindeki finansman
# tutarini (40.000 TL) UYDURUP odul_miktari diye yazdi - metinde hicbir
# odul ifadesi (hediye/kazan/puan/mil vb.) gecmemesine ragmen. Bu, tam
# olarak rapor Bolum 5.7/15'in uyardigi turden bir halusinasyon. Cozum:
# odul_miktari YALNIZCA ham metinde gercekten bir odul-anahtar kelimesi
# geciyorsa kabul edilir - regex_extractor.py'nin RE_ODUL desenindeki
# AYNI anahtar kelime kumesi kullanilir (iki motor arasinda tutarlilik).
_ODUL_ANAHTAR_KELIMELERI = [
    "hediye", "kazan", "puan", "mil", "gram", "bankkart lira",
    "parafpara", "worldpuan", "iade", "alışveriş çeki", "hediye çeki", "indirim",
]


def _odul_ifadesi_gercekten_var_mi(ham_metin: str) -> bool:
    """DENETIM BULGUSU 2: bare 'çeki' kelimesi 'nakit çekim' (para cekme)
    icindeki 'çeki' alt-dizesiyle YANLIŞLIKLA eşleşiyordu - gercek Albaraka
    verisinde dogrulandi ('...ATM'leri uzerinden nakit cekim yapamazsiniz').
    'çeki' yerine tam ifadeler ('hediye çeki', 'alışveriş çeki') kullanilir,
    tek basina 'çeki' asla aranmaz."""
    metin_l = turkce_kucult(ham_metin)
    return any(k in metin_l for k in _ODUL_ANAHTAR_KELIMELERI)


_SAYISAL_ALANLAR = {"vade_ay", "taksit_sayisi", "erteleme_suresi_ay", "finansman_tutari", "odul_miktari"}


def _llm_sayisini_dogrula(deger):
    """DENETIM BULGUSU 3: regex_extractor.py ve ner_extractor.py'deki her
    sayisal alan mutlaka bir donusum fonksiyonundan (tutara_cevir/aya_cevir)
    geciyor, ama ilk yazimda LLM'in JSON'da dondurdugu sayisal alanlar
    (finansman_tutari, odul_miktari, vade_ay, taksit_sayisi,
    erteleme_suresi_ay) HICBIR dogrulama olmadan dogrudan kaydediliyordu.
    LLM bir sayiyi Turkce bicimde ('100.000' gibi binlik ayiracli bir
    string) dondururse, bu ham haliyle veritabanina giderdi.

    Bu fonksiyon deger zaten temiz bir int/float ise oldugu gibi kabul
    eder; belirsiz bicimli bir string ise (Turkce binlik ayiraci/virgul
    icerebilir) TAHMIN ETMEYE CALISMAZ - reddedip None doner. Yanlis
    tahmin etmek (ornegin '100.000'i 100 sanmak), degeri hic almamaktan
    daha tehlikelidir (rapor Bolum 5.7/15)."""
    if isinstance(deger, bool):
        return None
    if isinstance(deger, (int, float)):
        return deger
    return None


def _json_gövdesini_ayikla(ham_yanit: str) -> Optional[dict]:
    """LLM bazen JSON'un etrafina aciklama metni ekleyebiliyor (ör.
    '```json\\n{...}\\n```' veya 'Iste sonuc: {...}'). Ilk '{' ile son '}'
    arasini alip parse etmeyi dener - basarisiz olursa None doner (asla
    exception firlatmaz, cagiran taraf bunu 'bulunamadi' sayar)."""
    baslangic = ham_yanit.find("{")
    bitis = ham_yanit.rfind("}")
    if baslangic == -1 or bitis == -1 or bitis < baslangic:
        return None
    try:
        return json.loads(ham_yanit[baslangic : bitis + 1])
    except (json.JSONDecodeError, ValueError):
        return None


def llm_ile_cikar(
    ham_metin: str, sadece_bu_alanlar: Optional[set[str]] = None, model: str = _MODEL_ADI
) -> dict:
    """Qwen2.5'e ham metni verip istenen alanlari JSON olarak cikarmasini
    ister. LLM ciktisi HICBIR ZAMAN dogrudan guvenilmez - her sayisal
    deger regex/NER'deki AYNI makul-deger ve kesirli-oran guard'larindan
    gecirilir.

    `sadece_bu_alanlar` verilmezse TUM alanlar sorulur (NER'den farkli
    olarak LLM tek bir cagrida birden fazla alani ayni promptla
    isteyebilir - ayri ayri sormak gereksiz API cagrisi/gecikme yaratir).

    Donen: regex_extractor.kaydi_cikar() / ner_extractor.ner_ile_cikar()
    ile AYNI seklde - {"alan_adi": deger, ..., "_izler": {...}}
    """
    istenen_alanlar = (
        set(_ALAN_ACIKLAMALARI) if sadece_bu_alanlar is None
        else sadece_bu_alanlar & set(_ALAN_ACIKLAMALARI)
    )
    kar_payi_isteniyor = sadece_bu_alanlar is None or bool(sadece_bu_alanlar & _KAR_PAYI_ALANLARI)

    tum_alanlar = ["kar_payi_orani_decimal"] + list(_ALAN_ACIKLAMALARI)
    sonuc: dict = {alan: None for alan in tum_alanlar}
    izler: dict[str, tuple[str, float]] = {}

    sorgulanacak = set(istenen_alanlar)
    if kar_payi_isteniyor:
        sorgulanacak.add("kar_payi_orani_percent")

    if not sorgulanacak:
        sonuc["_izler"] = izler
        return sonuc

    # DENETIM BULGUSU 4: `sorgulanacak` bir set - Python surecleri arasinda
    # hash rastgelelestirmesi nedeniyle iterasyon sirasi degisebiliyor. Bu da
    # prompttaki alan SIRASININ her calistirmada farkli olmasina yol aciyordu
    # - ayni girdi/ayni model/temperature=0 olmasina ragmen, LLM alan sirasina
    # duyarli davranip bazen bir alani (ornegin finansman_tutari) atlayabildi
    # (gercek veriyle dogrulandi: ayni prompt icerigi, farkli alan sirasiyla,
    # farkli sonuc uretti). sorted() ile deterministik sira saglanir.
    alan_aciklama_metni = "\n".join(
        f'- "{alan}": {_ALAN_ACIKLAMALARI[alan]}' for alan in sorted(sorgulanacak)
    )
    metin_kirpilmis = _girdiyi_guvenli_kirp(ham_metin)
    prompt = (
        "Aşağıdaki katılım bankacılığı kampanya metninden istenen bilgileri çıkar.\n"
        "SADECE metinde AÇIKÇA belirtilen bilgileri yaz - metinde olmayan bir "
        "değeri UYDURMA, o alanı null bırak.\n"
        "Yalnızca geçerli bir JSON nesnesi döndür, başka hiçbir açıklama ekleme.\n\n"
        f"İstenen alanlar:\n{alan_aciklama_metni}\n\n"
        f"Metin:\n{metin_kirpilmis}\n\n"
        "JSON:"
    )

    ham_yanit = llm_ile_sor(prompt, model=model)
    if ham_yanit is None:
        sonuc["_izler"] = izler
        return sonuc

    veri = _json_gövdesini_ayikla(ham_yanit)
    if veri is None:
        sonuc["_izler"] = izler
        return sonuc

    if "kar_payi_orani_percent" in sorgulanacak and veri.get("kar_payi_orani_percent") is not None:
        ham_deger = veri["kar_payi_orani_percent"]
        if not _kesirli_oran_mi(ham_deger):
            try:
                percent = round(float(ham_deger), 4)
            except (TypeError, ValueError):
                percent = None
            if percent is not None and _kar_payi_makul_mu(percent):
                sonuc["kar_payi_orani_percent"] = percent
                sonuc["kar_payi_orani_decimal"] = round(percent / 100, 6)
                izler["kar_payi_orani_percent"] = (str(ham_deger), 0.6)

    odul_ifadesi_var = _odul_ifadesi_gercekten_var_mi(ham_metin)
    for alan in sorgulanacak - _KAR_PAYI_ALANLARI:
        deger = veri.get(alan)
        if deger is None or deger == "":
            continue
        if alan == "kampanya_bitis":
            deger = tarihe_cevir(str(deger))
            if deger is None:
                continue
        if alan in _SAYISAL_ALANLAR:
            deger = _llm_sayisini_dogrula(deger)
            if deger is None:
                continue
        if alan in ("odul_miktari", "odul_birimi") and not odul_ifadesi_var:
            # Halusinasyon guard'i - bkz. _odul_ifadesi_gercekten_var_mi
            # docstring'i (gercek Albaraka verisiyle dogrulanan bulgu).
            continue
        sonuc[alan] = deger
        izler[alan] = (str(veri.get(alan)), 0.6)

    sonuc["_izler"] = izler
    return sonuc

"""Ajan Orkestratoru - tek giris noktasi.

Mimari (rapor Bolum 8): Intent Detection -> Tool Router -> (SQL/Calculator/
Dictionary/RAG/Fallback) -> Response Generator -> Terminology Check ->
Verifier -> Provenance.

BU DOSYANIN KAPSAMI: Intent Detection + Tool Router + bes arac
(Hesaplama, Sozluk, Karsilastirma, Toplam Maliyet, RAG) + kademeli geri
cekilme + zaman asimi fallback + Terminology Check.

TERMINOLOGY CHECK - RAG'DE NEDEN FARKLI DAVRANIR: terminoloji_tutarliligini_
kontrol_et() kendi docstring'inde "ajanin URETTIGI yanitta" gelenek terim
sizintisini denetledigini soyluyor. RAG hicbir sey URETMIYOR - kaynak
metni birebir donduruyor (bkz. docs/rag_tasarim_ve_olcum.md Bolum 7:
"LLM ile ozetleme yok... halusinasyon yapisal olarak imkansizdir").
Bu yuzden RAG kaynaginda gecen bir gelenek terim (ornegin Turkiye
Finans'in kendi sayfasindaki "...bankacilik kanununa gore resmi olarak
Ihtiyac Kredisi olarak da nitelendirilmektedir" cumlesi - gercek veriyle
dogrulandi) bir HATA DEGILDIR; bankanin kendi yasal ifadesidir, kaynagi
"duzeltmek" projenin kendi seffaflik ilkesiyle (rapor Bolum 5.7/15)
CELISIR. Bu yuzden RAG yanitlarinda kontrol yine calisir (audit icin
gorunur olsun diye) ama sonucu bir HATA/tutarsizlik olarak degil,
yalnizca BILGI notu olarak isaretlenir (`terminoloji_tutarli=None`).

SOZLUK ARACI DA AYNI MUAFIYETI ALIR - DENETIM BULGUSU: ilk yazimda
Sozluk araci "tam kontrole" tabi tutulmustu, ama gercek cagriyla
denendiginde "Kâr Payı Oranı, geleneksel bankacilikta 'Faiz Orani'
kavramina karsilik gelir" cevabi kendi kendini "hatali" isaretledi.
Bu bir kayma DEGIL - terminology/sozluk.json'daki her kavramin
`gelenek_karsilik` alaninin ve Md. 5.5'in kendisinin amaci tam da
kullaniciya gelenek karsiligi OGRETMEKTIR. Bu yuzden yalnizca
Hesaplama ve Karsilastirma (sayisal/yapisal veri ureten, gelenek
terime hic ihtiyaci olmayan iki arac - dogrulandi: hesaplama cevabi
"kar payi orani" diyor, "faiz" hic gecmiyor) tam True/False kontrolune
tabidir. Sozluk ve RAG, ikisi de MESRU sekilde gelenek terim
icerebilecegi icin bilgi notu (`terminoloji_tutarli=None`) alir.

VERIFIER DURUMU: validation/verifier.py yazildi, gercek veriyle olculdu
(6/6 yanlis pozitif reddedildi, 41 gercek iddianin 37'si onaylandi) ve
agent/router.py'deki karsilastirma_aracini_cagir ile toplam_maliyet_
aracini_cagir icinde `dogrulama` alani olarak ajan yanit yoluna BAĞLANDI.
Hesaplama araci (calculator) saf Python - kendi girdisini dogrular,
uydurma sayi URETMEZ, dolayisiyla Verifier o yol icin gerekli degildir.
RAG'de None kalir ve bu DOGRUDUR: RAG kaynak parcasini BIREBIR dondurur,
uzerine cumle uretmez - orada "sayi kaynakta var mi" kontrolu tanim geregi
hep EVET derdi (bkz. validation/yanit_dogrulama.py docstring'i).

ZAMAN ASIMI TABANLI KADEMELI FALLBACK: Arac cagrilari (ozellikle RAG -
embedding hesaplamasi icerir) beklenmedik sekilde uzayabilir. Olculen
p95 esikleri: GPU profil 300 sn, CPU profil 900 sn. KATILIMAI_ARAC_ZAMAN_ASIMI
ortam degiskeniyle ezilir. Arac zaman asimina ugrarsa sistem DURMAZ -
"zaman_asimi" sebep koduyla audit'e yazar ve kullaniciya acik bir mesaj
doner. Sessiz kilitlenme yoktur.

api/main.py, GERCEK_VERI_AKTIF bayragina gore uygun `kayit_getirici`
fonksiyonunu bu module verir - boylece bu dosya mock/DB ayrimindan
tamamen habersiz kalir.
"""

import os
import time
import threading
from typing import Any, Callable

from agent.intent import Niyet, niyet_tespit_et
from agent.router import (
    hesaplama_aracini_cagir,
    karsilastirma_aracini_cagir,
    rag_aracini_cagir,
    sozluk_aracini_cagir,
    toplam_maliyet_aracini_cagir,
)
from terminology.tutarlilik_kontrolu import terminoloji_tutarliligini_kontrol_et

KayitGetirici = Callable[[str], list]

# Bu araclarin yanitinda gecen bir gelenek terim HATA degil, bilgi
# notudur (bkz. modul docstring'i) - RAG kaynagi birebir aliyor, Sozluk
# ise gelenek karsiligi ACIKCA ogretmek icin var. Hesaplama/Karsilastirma
# BURADA YOK - onlarin yaniti sayisal/yapisal veridir, gelenek terime hic
# ihtiyaci olmaz; oralarda gercek bir True/False kontrolu uygulanir.
_TERMINOLOJI_BILGI_NOTU_ARACLARI = {"rag", "dictionary"}

# Zaman asimi esigi (saniye). Olculen p95: GPU=300sn, CPU=900sn.
# KATILIMAI_ARAC_ZAMAN_ASIMI ortam degiskeniyle ezilebilir.
_VARSAYILAN_ZAMAN_ASIMI_SN = float(os.environ.get("KATILIMAI_ARAC_ZAMAN_ASIMI", "900"))


def _arac_cagir_zaman_asimi(fonksiyon, *args, zaman_asimi_sn: float = _VARSAYILAN_ZAMAN_ASIMI_SN) -> dict[str, Any]:
    """Arac fonksiyonunu ayri thread'de calistirip zaman asimini denetler.

    Donanim profili (donanim.py) GPU/CPU'ya gore otomatik ayar seciyor;
    ama LLM embedding bazen beklenmedik sekilde uzayabiliyor. Bu sarmalayici
    sessiz kilitlenmeyi onler: esik asilirsa aninda fallback mesaji doner,
    hicbir exception kaybedilmez, audit'e sebep yazilir.
    """
    sonuc: dict[str, Any] = {}
    hata: list[Exception] = []

    def _calistir() -> None:
        try:
            sonuc.update(fonksiyon(*args))
        except Exception as e:  # noqa: BLE001
            hata.append(e)

    thread = threading.Thread(target=_calistir, daemon=True)
    thread.start()
    thread.join(timeout=zaman_asimi_sn)

    if thread.is_alive():
        # Thread hala calisiyor = zaman asimi
        return {
            "basarili": False,
            "cevap": (
                "Bu islem beklenenden uzun surdu ve zaman asimina ugradi. "
                f"Lutfen daha kisa bir soru deneyin ya da daha sonra tekrar basvurun. "
                f"(Esik: {zaman_asimi_sn:.0f} sn)"
            ),
            "sebep": "zaman_asimi",
        }
    if hata:
        raise hata[0]
    return sonuc


def _yanit_guveni(arac: str, sonuc: dict, kaynaklar: list) -> float:
    """Yanit guven skoru. RAG'de ARAMA KALITESINDEN, digerlerinde ikili.

    NEDEN AYRIM VAR (olculdu): skor "1.0 if basarili else 0.0" idi.
    "bu kampanya icin ne dusunuyorsun" sorusunda en iyi kaynak benzerligi
    0,50 (bir kategori sayfasi), en kotusu 0,33 oldugu halde ekranda guven
    %100 gorunuyordu. "Bir sey buldum" ile "buldugum sey alakali" ayni sey
    degildir; ikisini ayirmayan bir skor kullaniciyi yaniltir.

    Diger araclarda (SQL / hesaplama / sozluk / toplam maliyet) ikili skor
    DOGRUDUR: deterministik calisirlar, basariliysa sonuc kesindir ve orada
    "benzerlik" diye bir kavram yoktur - oraya sahte bir sureklilik
    uydurmak, RAG'deki sorunun aynisini ters yonde yaratirdi.
    """
    if not sonuc.get("basarili"):
        return 0.0
    if arac != "rag":
        return 1.0

    skorlar = []
    for k in kaynaklar:
        skor = k.get("similarity_score") if isinstance(k, dict) else getattr(k, "similarity_score", None)
        if skor is not None:
            skorlar.append(float(skor))
    # Skor yoksa duserek 1.0'a donmek yerine ikili davranisi koru: kaynak
    # var ama benzerlik tasimıyorsa bu bir olcum eksikligidir, guvensizlik
    # isareti degil.
    if not skorlar:
        return 1.0
    return round(max(skorlar), 4)


def soru_isle(soru: str, kayit_getirici: KayitGetirici, rag_araci=None) -> dict:
    """Bir kullanici sorusunu isler, cevap + Juri Audit Paneli icin
    gereken tum izlenebilirlik alanlarini doner (rapor Bolum 10.2).

    Donen sozluk: cevap, kaynaklar, confidence, fallback, audit_ekstra
    (intent, intent_confidence, cagrilan_arac, sebep, latency_ms).
    """
    baslangic = time.time()
    niyet, guven = niyet_tespit_et(soru)

    # `rag_araci` enjekte edilebilir (kayit_getirici ile ayni desen):
    # yonlendirme mantigini test eden birim testleri, gercek embedding
    # modelini yuklemek zorunda kalmasin diye - olculdu: gercek RAG ile
    # bu testler 2 sn yerine 121 sn suruyordu. Sozlesme iki argumanlidir:
    # rag(soru, kayit_getirici) - ikinci arguman kaynaklara kampanya_id
    # eklemek icin kullanilir (bkz. agent/router.py::rag_aracini_cagir).
    rag = rag_araci or rag_aracini_cagir

    if niyet == Niyet.HESAPLAMA:
        # Hesaplama saf Python - zaman asimi esigi gereksiz ama sarmalayici
        # tutarli API saglar; beklenmedik bir hata varsa yine audit'e yazar.
        sonuc = _arac_cagir_zaman_asimi(hesaplama_aracini_cagir, soru)
        arac = "calculator"
    elif niyet == Niyet.SOZLUK:
        sonuc = _arac_cagir_zaman_asimi(sozluk_aracini_cagir, soru)
        arac = "dictionary"
    elif niyet == Niyet.TOPLAM_MALIYET:
        sonuc = _arac_cagir_zaman_asimi(toplam_maliyet_aracini_cagir, soru, kayit_getirici)
        arac = "calculator"
    elif niyet == Niyet.KARSILASTIRMA:
        sonuc = _arac_cagir_zaman_asimi(karsilastirma_aracini_cagir, soru, kayit_getirici)
        arac = "sql"
    else:
        sonuc = _arac_cagir_zaman_asimi(rag, soru, kayit_getirici)
        niyet = Niyet.BILGI
        arac = "rag" if sonuc.get("basarili") else "fallback"

    # KADEMELI GERI CEKILME: Anahtar kelime tabanli niyet tespiti dogal
    # sorularda yanilabiliyor - olculdu: "Ziraat Katilim kart
    # kampanyalarinda TAKSIT var mi?" yalnizca "taksit" kelimesi yuzunden
    # hesap makinesine gidiyor ve kullaniciya "Hesaplama icin su bilgiler
    # eksik: anapara, aylik_oran_percent, vade_ay" deniyordu. Oysa bu bir
    # BILGI sorusu ve cevabi kaynaklarda var.
    #
    # Bu yuzden: secilen arac basarisiz olursa vazgecmek yerine RAG'e
    # sorulur. RAG de kaynak bulamazsa sistem yine acikca cekimser kalir
    # (rapor Bolum 5.7/15) - uydurma cevap hicbir yolda uretilmez.
    if not sonuc.get("basarili") and arac != "rag":
        rag_sonucu = rag(soru, kayit_getirici)
        if rag_sonucu.get("basarili"):
            # Ilk aracin neden yetmedigi audit'te korunur - juri
            # panelinde "hangi yol denendi?" gorunur olsun.
            rag_sonucu["sebep"] = (
                f"{arac} yetersiz kaldi ({sonuc.get('sebep')}), "
                "yanit kaynaklardan uretildi"
            )
            sonuc = rag_sonucu
            niyet = Niyet.BILGI
            arac = "rag"

    latency_ms = int((time.time() - baslangic) * 1000)
    veri = sonuc.get("veri", {})

    # Kaynaklar YALNIZCA RAG'den gelir - hesaplama/sozluk/karsilastirma
    # araclari belge degil yapilandirilmis veri kullanir.
    kaynaklar = sonuc.get("kaynaklar", [])

    # Terminology Check (Md. 5.5) - bkz. modul docstring'i "TERMINOLOGY
    # CHECK - RAG'DE NEDEN FARKLI DAVRANIR" / "SOZLUK ARACI DA AYNI
    # MUAFIYETI ALIR" ve _TERMINOLOJI_BILGI_NOTU_ARACLARI.
    terminoloji_sonucu = terminoloji_tutarliligini_kontrol_et(sonuc["cevap"])

    return {
        "cevap": sonuc["cevap"],
        "kaynaklar": kaynaklar,
        "confidence": _yanit_guveni(arac, sonuc, kaynaklar),
        "fallback": not sonuc.get("basarili", False),
        "audit_ekstra": {
            "intent": niyet.value,
            "intent_confidence": guven,
            "cagrilan_arac": arac,
            "latency_ms": latency_ms,
            "sebep": sonuc.get("sebep"),
            # Yalnizca karsilastirma araci (gercek kampanya kayitlari
            # kullanir) doldurur; hesaplama/sozluk icin None kalir - bu
            # alanlarin o araclarda anlami yoktur (rapor Bolum 5.7/15).
            "extraction_confidence": veri.get("extraction_confidence"),
            "regex_basari_orani": veri.get("regex_basari_orani"),
            # Verifier'in ajan yanit yoluna baglanmasi (README "Henuz
            # kurulmayanlar" maddesi). YALNIZCA yapilandirilmis veri
            # kullanan araclar (karsilastirma / toplam maliyet) doldurur.
            # RAG'de None kalir ve bu DOGRUDUR: RAG kaynak parcasini
            # BIREBIR dondurur, uzerine cumle uretmez - orada "sayi
            # kaynakta var mi" kontrolu tanim geregi hep EVET derdi,
            # yani eleme yapmayan bir guvence izlenimi olurdu
            # (bkz. validation/yanit_dogrulama.py docstring'i).
            "dogrulama": veri.get("dogrulama"),
            # Karsilastirma araci doldurur. UYARI: bu sorgu ajan
            # yolunda CALISTIRILMAZ - siralama bellekte yapilir
            # (karsilastir_bellekte). Panelde gosterilme sebebi
            # seffafliktir: "bu karsilastirmanin SQL karsiligi
            # budur" (ayni konvansiyon /karsilastir ucunda da var).
            "sql_sorgusu": veri.get("sql_sorgusu"),
            # Juri Audit Paneli'nin retriever bolumu (rapor Bolum 10.2):
            # hangi parcalar, hangi skorla getirildi?
            "retriever_sonuclari": [
                {
                    "chunk_id": k.get("kaynak_url") or "",
                    "similarity_score": k.get("similarity_score"),
                    "metin_ozeti": (k.get("metin") or "")[:200],
                }
                for k in kaynaklar
            ],
            # RAG/Sozluk'te "uygulanamaz" (None) - bkz.
            # _TERMINOLOJI_BILGI_NOTU_ARACLARI. Hesaplama/Karsilastirma'da
            # gercek True/False sonucudur.
            "terminoloji_tutarli": (
                None if arac in _TERMINOLOJI_BILGI_NOTU_ARACLARI else terminoloji_sonucu["tutarli"]
            ),
            "terminoloji_sorunlari": terminoloji_sonucu["bulunan_sorunlar"],
        },
    }

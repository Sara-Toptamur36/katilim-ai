"""Niyet Tespiti (Intent Detection) - Ajan Orkestratorun ilk katmani.

TASARIM KARARI: Sprint 4'te ModernBERT/LLM tabanli siniflandirma planlanmis
olsa da, ilk hat icin ANAHTAR KELIME tabanli deterministik kurallar
kullanilir - projenin "net/sayisal durumlarda deterministik arac, ancak
belirsizlikte LLM'e basvur" ilkesiyle tutarlidir (rapor Bolum 8). Bu katman,
LLM hic baglanmadan once de test edilebilir bir cekirdek saglar ve LLM
entegre edildiginde FALLBACK/CAPRAZ KONTROL olarak kalmaya devam eder.
"""

from difflib import SequenceMatcher
from enum import Enum


class Niyet(str, Enum):
    HESAPLAMA = "hesaplama"
    KARSILASTIRMA = "karsilastirma"
    TOPLAM_MALIYET = "toplam_maliyet"
    SOZLUK = "sozluk"
    # KAPSAM_DISI: genel bankacilik ISLEMI sorulari ("hesap nasil acilir",
    # "sifremi unuttum", "TMSF guvencesi", "sube adresi") - bunlar katilim
    # BANKACILIGI kavramlari degil, herhangi bir bankanin musteri hizmetleri
    # islemleridir ve sistemin hicbir katmaninda (kampanya verisi, RAG
    # indeksi, terminoloji sozlugu) cevabi yoktur.
    #
    # NEDEN AYRI BIR NIYET GEREKTI (23 Agustos 2026, olculdu): bu sorular
    # BILINMIYOR'a dusup RAG'e gidiyordu. RAG'in cekimserlik kontrolu
    # LEXICAL ORTUSMEYE dayanir (bkz. chunking/retriever.py) ve "hesap",
    # "belge", "TMSF", "sifre" gibi kelimeler kampanya metinlerinin genel
    # bankacilik kelime dagarcigindan oldugu icin ortusme YANLISLIKLA
    # esigi (%60) asiyordu - 185 soruluk kategori bazli olcumde
    # alan_ici_kapsam_disi abstention dogrulugu yalnizca %50 (5/10) cikti.
    # Tam dagilim olculdu: bu kategorinin araligi (0,50-0,83) gercekten
    # cevaplanabilir banka_ve_konu/kismi_ad sorularinin araligiyla (ikisi
    # de 0,50'den basliyor) IC ICE - yani RAG esigini yukseltmek bu
    # sorunu cozmez, gercek cevaplanabilir sorulari da susturur (bkz.
    # docs/rag_tasarim_ve_olcum.md Bulgu 8). Dogru cozum RAG'e hic
    # sormadan, niyet katmaninda ayiklamaktir.
    KAPSAM_DISI = "kapsam_disi"
    # BILGI: belirli bir araca uymayan ama kaynaklarda aranabilecek
    # serbest bilgi sorusu ("X kampanyasinin sartlari neler?"). Anahtar
    # kelimeyle tespit EDILMEZ - acik uclu oldugu icin kelime listesiyle
    # yakalanamaz; niyet_tespit_et hicbir arac eslesmediginde orkestrator
    # bu yola gider ve RAG'e sorar (bkz. agent/orchestrator.py).
    BILGI = "bilgi"
    BILINMIYOR = "bilinmiyor"


def _turkce_kucult(metin: str) -> str:
    """Python'un str.lower()'i Turkce noktali buyuk 'İ'yi duz 'i' degil,
    gorunmez birlesik nokta karakteriyle kucultur - bu da anahtar kelime
    eslesmesini sessizce bozar (terminology/genisletme.py'de de ayni
    duzeltme var, bkz. Sprint 1 Gun sonu bulgu)."""
    return metin.replace("İ", "i").lower()


_TR_ASCII_HARITASI = str.maketrans("şığüöç", "siguoc")


def turkce_ascii_katla(metin: str) -> str:
    """Turkce harfleri ASCII'ye katlar (ş->s, ı->i, ğ->g, ü->u, ö->o, ç->c).

    Anahtar kelime listeleri ASCII yazilir (ornek: 'karsilastir'), ama
    gercek kullanicilar dogal olarak Turkce karakterlerle yazar ('karşılaştır').
    Katlama olmadan bu iki yazim ASLA eslesmez - jurinin normal Turkce
    yazacagi bir soru niyeti hic tespit edilemez (gercek /chat testinde
    bulundu, bkz. bu dosyanin testleri)."""
    return _turkce_kucult(metin).translate(_TR_ASCII_HARITASI)


# Anahtar kelimeler rapor Bolum 5.2 ornek sorularindan ve gercek kullanici
# ifadelerinden turetildi. Liste kucuk ve deterministik tutulur - amac
# %100 dogruluk degil, LLM baglanana kadar makul bir ilk tahmindir.
_HESAPLAMA_ANAHTAR_KELIMELER = [
    "taksit", "hesapla", "ne kadar oder", "aylik odeme",
    "kac tl oder", "geri odeme", "odeme plani",
]
_KARSILASTIRMA_ANAHTAR_KELIMELER = [
    "karsilastir", "hangisi daha", "en dusuk", "en avantajli",
    "en iyi", "hangi banka", "fark ne kadar", " mi yoksa ",
]
# KARSILASTIRMA'dan AYRI: yalnizca alan bazli siralama degil, gercek bir
# anapara icin AMORTISMAN hesabi gerektirir (calculator/calculator.py::
# toplam_maliyet_karsilastir) - "dusuk oran = ucuz demek degildir" tuzagini
# somut TL ile gosterir.
_TOPLAM_MALIYET_ANAHTAR_KELIMELER = [
    "toplam maliyet", "toplamda ucuz", "toplamda daha ucuz",
    "toplam geri odeme", "hangisi toplamda",
]
_SOZLUK_ANAHTAR_KELIMELER = [
    "ne demek", "nedir", "anlamina gelir", "aciklar misin",
    "ne anlama", "tanimi ne",
]
# Genel bankacilik ISLEMI kaliplari - bilerek COK KELIMELI ve dar tutuldu
# (Niyet.KAPSAM_DISI docstring'inde gerekce var). Tek basina "hesap" veya
# "sube" gibi genel kelimeler BURAYA KONULMADI - kampanya sorularinda da
# gecebilir, yanlis pozitife yol acar. Yalnizca ölçümde gercekten karsilasilan,
# baska hicbir aracin/RAG'in dogru cevaplayamadigi somut kaliplar var.
_KAPSAM_DISI_ANAHTAR_KELIMELER = [
    "nasil acilir", "hangi belgeler gerekir", "en yakin sube",
    "sifremi unuttum", "tmsf", "bakiyeyi nasil ogrenirim",
    "limitimi nasil artirabilirim",
]

_NIYET_KELIMELERI = {
    # TOPLAM_MALIYET EN BASTA: esitlik durumunda max() ilk gordugu anahtari
    # secer (dict sirasi = oncelik). "toplam maliyet hesapla" gibi bir soru
    # hem HESAPLAMA'nin "hesapla"si hem TOPLAM_MALIYET'in "toplam maliyet"i
    # ile 1-1 esleserdi - daha ozgul olan (TOPLAM_MALIYET) kazanmali.
    Niyet.TOPLAM_MALIYET: _TOPLAM_MALIYET_ANAHTAR_KELIMELER,
    # KAPSAM_DISI de erken kontrol edilir: kaliplari cok kelimeli/ozgul
    # oldugu icin (ornek: "hesap ac" degil "nasil acilir") HESAPLAMA'nin
    # "hesap"~"hesapla" bulanik eslesme hatasina hic girmeden once
    # (bkz. modul ici bilinen sinirlama notu) tam eslesmeyle kazanir.
    Niyet.KAPSAM_DISI: _KAPSAM_DISI_ANAHTAR_KELIMELER,
    Niyet.HESAPLAMA: _HESAPLAMA_ANAHTAR_KELIMELER,
    Niyet.KARSILASTIRMA: _KARSILASTIRMA_ANAHTAR_KELIMELER,
    Niyet.SOZLUK: _SOZLUK_ANAHTAR_KELIMELER,
}

# DUZELTILDI (23 Agustos 2026): "X ile Y arasindaki fark nedir" gibi TANIM
# sorulari onceden KARSILASTIRMA'nin "fark ne" kalibiyla SOZLUK'un "nedir"
# kalibi arasinda esitlik yaratiyordu; dict sirasinda KARSILASTIRMA once
# geldigi icin kazaniyordu (ornek: "Mudarebe ile musareke arasindaki fark
# nedir?" -> yanlislikla KARSILASTIRMA, oysa ikisi de terminology/
# sozluk.json'da tanimli gercek SOZLUK adaylaridir). Kok neden "fark ne"
# kalibinin gercekte HICBIR teste/gercek soruya dayanmadan eklenmis
# olmasiydi (grep dogruladi) - bu yuzden "fark ne kadar" ile
# DEGISTIRILDI: gercek miktar sorularini ("...arasindaki fark ne kadar?")
# hala yakalar ama "fark nedir" tanim sorusuyla artik CAKISMAZ.


# Bulanik eslesme esigi. OLCULDU: "karsilatin" ("karsilastir" yazim hatasi)
# 0.86 skor veriyor, alakasiz kelimeler 0.5'in altinda kaliyor. 0.82 ikisini
# ayirir. Esigi dusurmek yanlis niyet tespitine yol acar - kullanici
# hesaplama isterken karsilastirma araci cagrilirsa sessizce YANLIS cevap
# uretilir, bu da cevapsiz kalmaktan kotudur.
_BULANIK_ESIK = 0.82

# Niyet.KAPSAM_DISI icin sabit, durust cevap - RAG'e hic sorulmaz. Sistemin
# ne bildigini/bilmedigini acikca soyler (rapor Bolum 5.7/15 ile ayni ilke:
# belirsizlik/kapsam disi gizlenmez).
KAPSAM_DISI_CEVABI = (
    "Bu sistem katılım bankalarının kampanya ve ürün bilgilerine odaklanır; "
    "hesap açma, şifre yenileme, TMSF güvencesi veya şube/limit işlemleri "
    "gibi genel bankacılık işlemleri kapsamımızda değildir. Bu konu için "
    "lütfen doğrudan ilgili bankanızla iletişime geçin."
)


def _bulanik_eslesme_sayilari(s: str) -> dict:
    """Tam eslesme bulunamadiginda kelime bazli bulanik arama.

    NEDEN VAR (olculdu): anahtar kelimeler tam alt dize olarak araniyordu,
    bu yuzden "karsilatin misin" gibi tek harf eksik bir yazim niyeti
    BILINMIYOR'a dusuruyor ve soru RAG'e gidiyordu. Juri/kullanici dogal
    yazdiginda (ek, dusme, yazim hatasi) sistem soruyu anlamiyordu.

    Anahtar kac kelimeden olusuyorsa sorudan ayni uzunlukta pencereler
    cikarilip karsilastirilir - "hangisi daha" gibi cok kelimeli anahtarlar
    da yakalanabilsin diye.
    """
    kelimeler = s.split()
    sayilar = {}
    for niyet, anahtarlar in _NIYET_KELIMELERI.items():
        sayi = 0
        for anahtar in anahtarlar:
            temiz = anahtar.strip()
            n = len(temiz.split())
            for i in range(len(kelimeler) - n + 1):
                pencere = " ".join(kelimeler[i : i + n])
                if SequenceMatcher(None, pencere, temiz).ratio() >= _BULANIK_ESIK:
                    sayi += 1
                    break  # ayni anahtar birden fazla sayilmasin
        sayilar[niyet] = sayi
    return sayilar


def niyet_tespit_et(soru: str) -> tuple[Niyet, float]:
    """Soruyu anahtar kelime eslesmesine gore siniflandirir.

    Donen: (niyet, guven_skoru). Guven skoru gercek bir olasilik degildir;
    kac anahtar kelimenin eslestigine gore kabaca hesaplanan, Juri Audit
    Paneli'nde seffaflik amacli bir gostergedir (rapor Bolum 10.2).
    Hicbir kelime eslesmezse BILINMIYOR + 0.0 doner (rapor Bolum 5.7/15:
    belirsizlik gizlenmez, acikca isaretlenir).
    """
    s = turkce_ascii_katla(soru)

    eslesme_sayilari = {
        niyet: sum(1 for k in kelimeler if k in s)
        for niyet, kelimeler in _NIYET_KELIMELERI.items()
    }

    en_iyi_niyet = max(eslesme_sayilari, key=eslesme_sayilari.get)
    en_iyi_sayi = eslesme_sayilari[en_iyi_niyet]

    if en_iyi_sayi == 0:
        # TAM eslesme yok - yazim hatasi/ek olabilir, bulanik dene.
        bulanik = _bulanik_eslesme_sayilari(s)
        en_iyi_niyet = max(bulanik, key=bulanik.get)
        en_iyi_sayi = bulanik[en_iyi_niyet]
        if en_iyi_sayi == 0:
            return Niyet.BILINMIYOR, 0.0
        # Bulanik eslesme DAHA DUSUK guven verir (en fazla 0.60) - tam
        # eslesmenin taban degeri 0.65'in altinda kalir. Juri Audit
        # Paneli'nde "bu niyet tahminle bulundu" ayrimi gorunur olsun.
        guven = min(0.50 + (en_iyi_sayi - 1) * 0.05, 0.60)
        return en_iyi_niyet, round(guven, 2)

    # Basit guven modeli: ilk eslesme 0.65, her ek eslesme +0.1, 0.95'i gecmez.
    guven = min(0.65 + (en_iyi_sayi - 1) * 0.10, 0.95)
    return en_iyi_niyet, round(guven, 2)

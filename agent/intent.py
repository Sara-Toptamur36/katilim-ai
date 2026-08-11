"""Niyet Tespiti (Intent Detection) - Ajan Orkestratorun ilk katmani.

TASARIM KARARI: Sprint 4'te ModernBERT/LLM tabanli siniflandirma planlanmis
olsa da, ilk hat icin ANAHTAR KELIME tabanli deterministik kurallar
kullanilir - projenin "net/sayisal durumlarda deterministik arac, ancak
belirsizlikte LLM'e basvur" ilkesiyle tutarlidir (rapor Bolum 8). Bu katman,
LLM hic baglanmadan once de test edilebilir bir cekirdek saglar ve LLM
entegre edildiginde FALLBACK/CAPRAZ KONTROL olarak kalmaya devam eder.
"""

from enum import Enum


class Niyet(str, Enum):
    HESAPLAMA = "hesaplama"
    KARSILASTIRMA = "karsilastirma"
    TOPLAM_MALIYET = "toplam_maliyet"
    SOZLUK = "sozluk"
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
    "en iyi", "hangi banka", "fark ne", " mi yoksa ",
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

_NIYET_KELIMELERI = {
    # TOPLAM_MALIYET EN BASTA: esitlik durumunda max() ilk gordugu anahtari
    # secer (dict sirasi = oncelik). "toplam maliyet hesapla" gibi bir soru
    # hem HESAPLAMA'nin "hesapla"si hem TOPLAM_MALIYET'in "toplam maliyet"i
    # ile 1-1 esleserdi - daha ozgul olan (TOPLAM_MALIYET) kazanmali.
    Niyet.TOPLAM_MALIYET: _TOPLAM_MALIYET_ANAHTAR_KELIMELER,
    Niyet.HESAPLAMA: _HESAPLAMA_ANAHTAR_KELIMELER,
    Niyet.KARSILASTIRMA: _KARSILASTIRMA_ANAHTAR_KELIMELER,
    Niyet.SOZLUK: _SOZLUK_ANAHTAR_KELIMELER,
}


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
        return Niyet.BILINMIYOR, 0.0

    # Basit guven modeli: ilk eslesme 0.65, her ek eslesme +0.1, 0.95'i gecmez.
    guven = min(0.65 + (en_iyi_sayi - 1) * 0.10, 0.95)
    return en_iyi_niyet, round(guven, 2)

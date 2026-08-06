"""Seyrek (lexical/BM25) vektor uretimi - hibrit aramanin kelime tarafi.

NEDEN GEREKLI: Spike olcumu (docs/qdrant_spike_raporu.md, Bulgu 2) yalnizca
yogun (dense) embedding kullanildiginda ALAKALI ve TAMAMEN ALAKASIZ sorgu
arasindaki skor farkinin yalnizca 0,0455 oldugunu gosterdi - "uzay
istasyonunda yercekimi" sorusu bile 0,78 aliyordu. Bu, ham benzerlik
skoruna bakip "kaynak buldum" demeyi guvenilmez kilar.

Lexical arama bu sorunu dogrudan cozer: "Worldpuan", "ParafPara",
"Bankkart", "98/2", banka adlari gibi AYIRT EDICI terimler birebir
eslesir; alakasiz bir sorguda hicbir terim eslesmez ve aday listesine
hic girmez.

IDF SUNUCU TARAFINDA: Bu modul yalnizca terim FREKANSLARINI uretir.
Terimin nadirligini (IDF) Qdrant kendisi hesaplar
(models.Modifier.IDF) - boylece korpus istatistigini istemcide tutup
guncel tutma yuku olmaz.

TURKCE ICIN IKI OZEL KARAR:

1. KARARLI HASH: Python'un yerlesik hash()'i string'ler icin her SUREÇTE
   farkli sonuc verir (PYTHONHASHSEED rastgeleligi). Terim kimlikleri
   indeksleme ve sorgulama arasinda ayni kalmak ZORUNDA oldugu icin
   (farkli sureclerde calisirlar) zlib.crc32 kullanilir - deterministik
   ve dogrudan uint32 uretir.

2. EK DAYANIKLILIGI: Turkce eklemeli bir dildir - "kampanya",
   "kampanyadan", "kampanyaya", "kampanyanin" ayni koke ait ama farkli
   token'dir. Tam morfolojik cozumleme (Zemberek vb.) agir bir bagimlilik
   getirir; bunun yerine uzun token'lar icin AYRICA bir govde oneki
   dusuk agirlikla indekslenir. Tam eslesme yuksek agirligini korur,
   ekli bicimler de yakalanir.
"""

from __future__ import annotations

import re
import zlib
from collections import Counter

# Kelime, sayi (%1,99 / 100.000) ve oran (98/2) bicimlerini korur.
_TOKEN_DESENI = re.compile(r"[0-9]+(?:[.,/][0-9]+)*|[a-zçğıöşüâîû]+", re.IGNORECASE)

GOVDE_ONEK_UZUNLUGU = 5
GOVDE_ASGARI_TOKEN = 7  # bu uzunluktan kisa token'lara govde onegi uretilmez
GOVDE_AGIRLIGI = 0.4    # tam eslesmeden dusuk agirlik

# Cok yaygin, ayirt edici olmayan Turkce kelimeler. IDF bunlari zaten
# bastirir; yine de indeksten cikarmak seyrek vektoru kucultur.
_ETKISIZ_KELIMELER = {
    "ve", "ile", "veya", "bir", "bu", "da", "de", "için", "icin", "olan",
    "olarak", "gibi", "daha", "en", "her", "tüm", "tum", "ya", "ki", "mi",
    "ise", "ancak", "sadece", "kadar", "sonra", "önce", "once",
    # SORU KELIMELERI: her soruda gecer, hicbir belgeyi digerinden
    # ayirt etmez. Elenmeleri ayrica ABSTENTION dogrulugunu artirir -
    # olculdu: "Python'da liste nasil siralanir?" gibi alan disi bir
    # soru, yalnizca "nasil" gibi ortak kelimeler eslestigi icin
    # "kaynak buldum" sayilabiliyordu.
    "nasıl", "nasil", "neden", "niçin", "nicin", "hangi", "hangisi",
    "kim", "nerede", "nereden", "ne", "kaç", "kac", "mı", "mu", "mü",
    "var", "yok", "olur", "midir", "nedir", "neler", "nelerdir",
}


def _turkce_kucult(metin: str) -> str:
    """Turkce noktali buyuk 'İ' str.lower() ile bozulur (i + birlesik
    nokta) - projede bu hata daha once uc ayri yerde bulundu."""
    return metin.replace("İ", "i").lower()


def metni_tokenlara_ayir(metin: str) -> list[str]:
    """Metni arama token'larina ayirir (etkisiz kelimeler elenir)."""
    kucuk = _turkce_kucult(metin)
    return [t for t in _TOKEN_DESENI.findall(kucuk) if t not in _ETKISIZ_KELIMELER]


def terim_kimligi(token: str) -> int:
    """Token -> kararli uint32 kimlik (bkz. modul docstring, Karar 1)."""
    return zlib.crc32(token.encode("utf-8"))


def seyrek_vektor_uret(metin: str) -> tuple[list[int], list[float]]:
    """Metinden (indeksler, degerler) seyrek vektoru uretir.

    Deger = terim frekansi (govde onekleri dusuk agirlikla). Nadirlik
    agirligini (IDF) Qdrant uygular.
    """
    tokenlar = metni_tokenlara_ayir(metin)
    if not tokenlar:
        return [], []

    agirliklar: Counter[int] = Counter()
    for token in tokenlar:
        agirliklar[terim_kimligi(token)] += 1.0
        if len(token) >= GOVDE_ASGARI_TOKEN:
            govde = token[:GOVDE_ONEK_UZUNLUGU]
            # Govde onegini tam token'dan AYIRT ETMEK icin isaretlenir;
            # aksi halde kisa bir kelime ile uzun bir kelimenin govdesi
            # ayni kimligi alip yanlis eslesme uretirdi.
            agirliklar[terim_kimligi(f"{govde}~")] += GOVDE_AGIRLIGI

    indeksler = list(agirliklar.keys())
    degerler = [agirliklar[i] for i in indeksler]
    return indeksler, degerler

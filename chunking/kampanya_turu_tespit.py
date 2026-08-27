"""Sorgu metninden kampanya turunu tanir - retrieval'da SOFT-BOOST icin.

NEDEN VAR (Mentorluk III raporu 7.5/5.3, banka_ve_konu Recall@5 hala
zayif): chunking/banka_tespit.py bankayi metadata FILTRESINE tasiyarak
banka_ve_konu kategorisinde olculebilir kazanc sagladi (bkz. o dosyanin
docstring'i - k=1/k=3'te net iyilesme). Ayni sorunun ikinci bacagi -
"hangi TUR" - hic kullanilmiyordu. Bu modul sorgudaki tur ifadesini
(kart/ihtiyac finansmani/konut vb.) extraction/regex_extractor.py::
_kampanya_turunu_tespit_et ile AYNI kanonik etiketlere (api/schemas.py::
KampanyaTuru) cevirir.

NEDEN FILTRE DEGIL BOOST (kritik, bilincli tasarim karari): _kampanya_
turunu_tespit_et'in olculen F1'i %78,55 - mukemmel degil (bkz. docs/
kampanya_turu_olcum_raporu.md). Bunu SERT bir Qdrant filtresi yapmak,
DOGRU cevabi yanlis siniflandirma yuzunden aday havuzundan tamamen
SILERDI - bu, kaciran bir aramadan daha kotudur (rapor Bolum 5.7/15
ilkesiyle ayni ruh: yanlis eleme, uydurmadan farksiz bir guven kaybidir).
Bu yuzden chunking/retriever.py bu modulu bir HARD filtre olarak degil,
aday havuzu icinde bir SIRALAMA boostu olarak kullanir - hicbir aday
elenmez, yalnizca turu eslesenler one alinir.

ELLE ACMAK ICIN: KATILIMAI_TUR_BOOST=true (varsayilan false - bkz.
chunking/retriever.py::getir docstring'i, KATILIMAI_BANKA_OTOMATIK ile
AYNI "once olc, sonra varsayilan yap" ilkesi. Bu bayrak HENUZ olculmedi).

QUERY-SIDE SOZLUK, DOKUMAN-TARAFI SOZLUGUNDEN BILEREK FARKLI:
extraction/regex_extractor.py::KAMPANYA_TURU_ANAHTAR_KELIMELERI uzun
kampanya SAYFASI metni icin ayarlandi ("kredi kart", "kart avantaj" gibi
coklu-kelime ifadeler) - kisa bir kullanici sorgusunda ("Kuveyt Turk
kart") bu ifadeler hic gecmez. Bu yuzden asagidaki KANONIK_TURLER,
scraper/scripts/rag_degerlendirme.py::_TUR_ESLEME ile BIREBIR AYNI
takma adlari kullanir - o sozluk zaten gercek banka_ve_konu sorularina
(rag_soru_seti.json) karsi dogrulanmis durumda; burada TEKRAR icat
etmek iki taraf arasinda sessiz bir kayma riski dogururdu.
"""

from __future__ import annotations

import re
import unicodedata

# api/schemas.py::KampanyaTuru degerleriyle BIREBIR ayni olmali - bir
# yazim farki boost'u sessizce hicbir seye eslemez (bkz. chunking/
# banka_tespit.py::KANONIK_BANKALAR'daki ayni uyari).
KANONIK_TURLER: dict[str, tuple[str, ...]] = {
    "Kart Kampanyasi": ("kart",),
    "Ihtiyac Finansmani Kampanyasi": ("ihtiyac finansmani",),
    "Konut Finansmani Kampanyasi": ("konut finansmani",),
    "Tasit Finansmani Kampanyasi": ("tasit finansmani",),
    "Yeni Musteri Kampanyasi": ("yeni musteri",),
    "Alisveris Puani Kampanyasi": ("alisveris puani",),
    "Yatirim Urunu Kampanyasi": ("yatirim urunu",),
    "Finansman Kampanyasi": ("finansman",),
}

_KATLAMA = str.maketrans("çğıöşüâîû", "cgiosuaiu")


def _katla(metin: str) -> str:
    """chunking/banka_tespit.py::_katla ile AYNI ilke - diyakritik/buyuk-
    kucuk farki eslesmeyi degistirmemeli."""
    kucuk = metin.replace("I", "ı").replace("İ", "i").lower()
    ayrik = unicodedata.normalize("NFKD", kucuk)
    ayrik = "".join(c for c in ayrik if not unicodedata.combining(c))
    return ayrik.translate(_KATLAMA)


# UZUN ONCE: "ihtiyac finansmani" (2 kelime), bare "finansman" (1 kelime)
# tarafindan yanlislikla yutulmamali. Kelime siniri zaten bunu engeller
# ("finansmani" icindeki "finansman" alt-dizgesi \w siniri yuzunden
# eslesmez) ama uzunluk sirasi niyeti acikca dogrular.
_TAKMA_ADLAR: list[tuple[str, str]] = sorted(
    ((takma, kanonik) for kanonik, takmalar in KANONIK_TURLER.items() for takma in takmalar),
    key=lambda ikili: -len(ikili[0]),
)


def kampanya_turu_tespit(sorgu: str) -> str | None:
    """Sorguda tur ifadesi geciyor mu? Geciyorsa kanonik KampanyaTuru degeri, yoksa None.

    banka_tespit()'in AKSINE eslesen terimi sorgudan CIKARMAZ: bu deger
    bir HARD filtreye degil, aday havuzu icindeki bir SIRALAMA boostuna
    beslenir (bkz. chunking/retriever.py) - aday havuzu zaten TUM turleri
    iceriyor, yani tur kelimesinin sorguda kalmasi vektor aramasindaki
    ayirt ediciligini yitirmez (banka adinin aksine, o TUM adaylarda
    ortak oldugu icin cikarilmasi gerekiyordu).
    """
    katlanmis = _katla(sorgu)
    for takma, kanonik in _TAKMA_ADLAR:
        # Kelime siniri: "kart" kelimesi "bankkart" icinde eslesmemeli.
        desen = re.compile(rf"(?<!\w){re.escape(takma)}(?!\w)")
        if desen.search(katlanmis):
            return kanonik
    return None

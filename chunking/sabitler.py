# Ortak sabitler ve listeler (Dairesel bagimliligi onlemek icin)

# _govde() fonksiyonunda kirpilmayacak (stemming yapilmayacak) marka ve ozel jargonlar listesi.
# Bu listedeki kelimeler BM25 aramasinda dogrudan gecer.
MARKA_KORUMA_LISTESI: frozenset[str] = frozenset({
    # Garanti BBVA
    "parafpara",
    # Yapi Kredi
    "worldpuan", "worldcard",
    # Vakif / Ziraat
    "bankkart",
    # Genel markalar
    "bonus", "maximum", "axess", "cardfinans",
    # Ucus programlari
    "mil", "miles",
})

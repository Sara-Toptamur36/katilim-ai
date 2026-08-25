"""Qdrant vektor veritabani erisim katmani.

api/db.py'nin (PostgreSQL) Qdrant karsiligi: baglanti kurulumu ve temel
islemler burada toplanir, cagiran taraf qdrant_client API'sini dogrudan
bilmek zorunda kalmaz.

KAPSAM NOTU: Bu dosya RAG'in TAMAMI DEGILDIR - yalnizca altyapi katmanidir
(baglan, koleksiyon ac, vektor yaz, ara). Semantik chunking stratejisi,
metadata semasi ve retrieval kalitesi NLP tarafinin (Yagmur) alanidir;
bu katman ona hazir bir zemin birakir, kararlarini onceden vermez.

ERISILEBILIRLIK: Qdrant kapaliyken cagrilar hata FIRLATMAK yerine
`qdrant_hazir_mi()` ile onceden kontrol edilebilir - extraction/
llm_extractor.py'deki Ollama kontrolüyle ayni desen (30 sn onbellekli),
cunku kapali bir servise baglanma denemesi Windows'ta anlik degil
saniyeler suruyor ve cok kayitli akislarda bu bedel katlanarak artiyor.
"""

from __future__ import annotations

import os
import time
from typing import Any, Optional

import requests

import evren_istemci

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")

# KOLEKSIYON ADI EMBEDDING SAGLAYICISINA GORE OTOMATIK AYRILIR (bkz.
# docs/adr/0002-evren-cikarim-entegrasyonu.md): EVREN'in bge-m3-embed'i
# 1024, yerel e5-base 768 boyutlu vektor uretiyor - ikisi AYNI koleksiyona
# yazilamaz (Qdrant boyut uyumsuzlugunda hata verir, ya da daha kotusu,
# koleksiyon ilk olusturuldugu boyutta SABIT kalir ve farkli boyuttaki
# sonraki yazmalar sessizce yanlis sonuc uretebilir). QDRANT_KOLEKSIYON
# ORTAM DEGISKENI ACIKCA VERILMISSE bu otomatik ayrim devre disi kalir -
# kullanicinin ELLE sectigi bir isim her zaman kazanir.
_KOLEKSIYON_ELLE_VERILMIS = "QDRANT_KOLEKSIYON" in os.environ
_KOLEKSIYON_TABANI = os.environ.get("QDRANT_KOLEKSIYON", "kampanya_parcalari")
VARSAYILAN_KOLEKSIYON = (
    _KOLEKSIYON_TABANI
    if _KOLEKSIYON_ELLE_VERILMIS
    else (
        f"{_KOLEKSIYON_TABANI}_evren" if evren_istemci.aktif_mi() else _KOLEKSIYON_TABANI
    )
)

# YEREL DOSYA MODU (sunucusuz). Tanimliysa Qdrant sunucusu yerine bu
# klasore yazilir - Docker/servis kurulamayan makinelerde (ornegin GPU'suz
# Windows demo makinesi) RAG yolunu acik tutar. OLCULDU: yerel mod hibrit
# koleksiyonu (yogun + seyrek, Modifier.IDF dahil) tam destekliyor.
#
# Tanimli DEGILSE davranis DEGISMEZ: QDRANT_URL uzerinden sunucuya baglanir.
# Uretimde ve CI'da bu degisken bos birakilir.
QDRANT_YEREL_YOL = os.environ.get("QDRANT_YEREL_YOL", "").strip()

_istemci = None
_DURUM_CACHE: dict[str, Any] = {}
_DURUM_CACHE_SURESI_SN = 30.0


def qdrant_hazir_mi() -> bool:
    """Qdrant servisi ayakta mi? Sonuc 30 saniye onbellege alinir.

    Onbellek gerekcesi extraction/llm_extractor.py::_ollama_hazir_mi ile
    ayni: servis kapaliyken her cagrida ayri ayri baglanti-reddi beklemesi
    odenmesin.
    """
    # Yerel dosya modunda ortada bir servis yok - klasor yazilabiliyorsa
    # hazir sayilir. HTTP kontrolu yapilirsa her zaman False donerdi ve
    # RAG yolu bosuna kapali kalirdi.
    if QDRANT_YEREL_YOL:
        return True

    simdi = time.monotonic()
    son = _DURUM_CACHE.get("zaman")
    if son is not None and (simdi - son) < _DURUM_CACHE_SURESI_SN:
        return bool(_DURUM_CACHE["hazir"])
    try:
        yanit = requests.get(f"{QDRANT_URL}/", timeout=2)
        hazir = yanit.status_code == 200
    except requests.RequestException:
        hazir = False
    _DURUM_CACHE["hazir"] = hazir
    _DURUM_CACHE["zaman"] = simdi
    return hazir


def istemci_al():
    """QdrantClient ornegini (tembel) olusturur."""
    global _istemci
    if _istemci is None:
        from qdrant_client import QdrantClient

        if QDRANT_YEREL_YOL:
            _istemci = QdrantClient(path=QDRANT_YEREL_YOL)
        else:
            _istemci = QdrantClient(url=QDRANT_URL)
    return _istemci


# Hibrit koleksiyonda vektorler ISIMLENDIRILIR (tek isimsiz vektor yerine)
YOGUN_AD = "yogun"
SEYREK_AD = "seyrek"


def koleksiyon_hazirla(
    koleksiyon: str = VARSAYILAN_KOLEKSIYON,
    vektor_boyutu: int = 768,
    sifirla: bool = False,
) -> None:
    """Koleksiyonu olusturur (yoksa).

    `sifirla=True` verilirse ONCE SILER - yalnizca spike/test icin;
    gercek indeksleme akisinda veri kaybina yol acar, bu yuzden
    varsayilani False.
    """
    from qdrant_client.models import Distance, VectorParams

    istemci = istemci_al()
    if sifirla and istemci.collection_exists(koleksiyon):
        istemci.delete_collection(koleksiyon)

    if not istemci.collection_exists(koleksiyon):
        istemci.create_collection(
            collection_name=koleksiyon,
            # COSINE: embedding.py vektorleri normalize edilmis donduruyor
            # (normalize_embeddings=True), normalize vektorlerde kosinus
            # benzerligi dogru olcudur.
            vectors_config=VectorParams(size=vektor_boyutu, distance=Distance.COSINE),
        )


def hibrit_koleksiyon_hazirla(
    koleksiyon: str = VARSAYILAN_KOLEKSIYON,
    vektor_boyutu: int = 768,
    sifirla: bool = False,
) -> None:
    """Hem YOGUN (anlamsal) hem SEYREK (kelime/BM25) vektor tasiyan
    koleksiyon olusturur.

    Seyrek vektore `Modifier.IDF` verilir: terim frekanslarini biz
    gonderiyoruz, nadirlik agirligini (IDF) Qdrant sunucu tarafinda
    hesapliyor - korpus istatistigini istemcide tutmaya gerek kalmiyor
    (bkz. chunking/seyrek_vektor.py).
    """
    from qdrant_client.models import (
        Distance,
        Modifier,
        SparseVectorParams,
        VectorParams,
    )

    istemci = istemci_al()
    if sifirla and istemci.collection_exists(koleksiyon):
        istemci.delete_collection(koleksiyon)

    if not istemci.collection_exists(koleksiyon):
        istemci.create_collection(
            collection_name=koleksiyon,
            vectors_config={
                YOGUN_AD: VectorParams(size=vektor_boyutu, distance=Distance.COSINE)
            },
            sparse_vectors_config={
                SEYREK_AD: SparseVectorParams(modifier=Modifier.IDF)
            },
        )


def parcalari_ekle(
    vektorler: list[list[float]],
    ustveriler: list[dict],
    koleksiyon: str = VARSAYILAN_KOLEKSIYON,
    baslangic_id: int = 0,
) -> int:
    """Vektorleri ustverileriyle birlikte yazar, yazilan kayit sayisini doner.

    `ustveriler` her parca icin kaynak bilgisini tasimali (banka, kaynak_url,
    metin vb.) - rapor Bolum 9 (provenance): bir cevabin hangi belgeden
    geldigi gosterilemiyorsa RAG'in degeri yoktur.
    """
    from qdrant_client.models import PointStruct

    if len(vektorler) != len(ustveriler):
        raise ValueError(
            f"vektor sayisi ({len(vektorler)}) ile ustveri sayisi "
            f"({len(ustveriler)}) eslesmiyor"
        )

    noktalar = [
        PointStruct(id=baslangic_id + i, vector=v, payload=u)
        for i, (v, u) in enumerate(zip(vektorler, ustveriler))
    ]
    istemci_al().upsert(collection_name=koleksiyon, points=noktalar)
    return len(noktalar)


def ara(
    sorgu_vektoru: list[float],
    limit: int = 5,
    koleksiyon: str = VARSAYILAN_KOLEKSIYON,
) -> list[dict]:
    """En benzer parcalari doner: [{"skor": float, "ustveri": {...}}, ...]"""
    sonuclar = istemci_al().query_points(
        collection_name=koleksiyon, query=sorgu_vektoru, limit=limit
    ).points
    return [{"skor": s.score, "ustveri": s.payload} for s in sonuclar]


def hibrit_parcalari_ekle(
    yogun_vektorler: list[list[float]],
    seyrek_vektorler: list[tuple[list[int], list[float]]],
    ustveriler: list[dict],
    koleksiyon: str = VARSAYILAN_KOLEKSIYON,
    baslangic_id: int = 0,
) -> int:
    """Yogun + seyrek vektorleri birlikte yazar."""
    from qdrant_client.models import PointStruct, SparseVector

    if not (len(yogun_vektorler) == len(seyrek_vektorler) == len(ustveriler)):
        raise ValueError(
            f"yogun ({len(yogun_vektorler)}), seyrek ({len(seyrek_vektorler)}) ve "
            f"ustveri ({len(ustveriler)}) sayilari eslesmiyor"
        )

    noktalar = []
    for i, (yogun, (indeksler, degerler), ustveri) in enumerate(
        zip(yogun_vektorler, seyrek_vektorler, ustveriler)
    ):
        noktalar.append(
            PointStruct(
                id=baslangic_id + i,
                vector={
                    YOGUN_AD: yogun,
                    SEYREK_AD: SparseVector(indices=indeksler, values=degerler),
                },
                payload=ustveri,
            )
        )

    istemci_al().upsert(collection_name=koleksiyon, points=noktalar)
    return len(noktalar)


def hibrit_ara(
    yogun_sorgu: list[float],
    seyrek_sorgu: tuple[list[int], list[float]],
    limit: int = 5,
    koleksiyon: str = VARSAYILAN_KOLEKSIYON,
    aday_limiti: int = 20,
    filtre=None,
    exact: bool = False,
) -> list[dict]:
    """Yogun + seyrek aramayi birlikte calistirip RRF ile birlestirir.

    RRF (Reciprocal Rank Fusion): iki aramanin SIRALAMALARINI birlestirir,
    ham skorlarini degil. Bu onemli - yogun ve seyrek skorlar farkli
    olceklerdedir (kosinus 0-1, BM25 sinirsiz), dogrudan toplanamazlar.

    `filtre` verilirse (ornegin belirli bir banka) her iki aramaya da
    uygulanir.

    `exact=True`: HNSW yaklasik arama yerine tam brute-force tarama yapar.
    Recall@1 oynamasini onlemek icin olcum/test doneminde kullanilir;
    uretim yolunda (hizli yanit onemli) False birakilmalidir.
    
    DENETIM BULGUSU (24.08.2026): Menu kirliligi onlemi icin ham vektor
    skoru da donduruluyor. RRF skoru siralama birlestirme skorudur ve
    en ustteki sonuc her zaman ~1.0 civari alir; ham vektor skoru ise
    gercek anlam benzerligini gosterir (0-1 arasi cosine similarity).
    """
    from qdrant_client.models import (
        Filter,
        Fusion,
        FusionQuery,
        HasIdCondition,
        Prefetch,
        SearchParams,
        SparseVector,
    )

    indeksler, degerler = seyrek_sorgu
    arama_params = SearchParams(exact=exact) if exact else None

    on_aramalar = [
        Prefetch(
            query=yogun_sorgu,
            using=YOGUN_AD,
            limit=aday_limiti,
            filter=filtre,
            params=arama_params,
        ),
    ]
    # Sorguda hic token yoksa (ornegin yalnizca noktalama) seyrek arama
    # anlamsizdir - Qdrant'a bos vektor gondermek yerine atlanir.
    if indeksler:
        on_aramalar.append(
            Prefetch(
                query=SparseVector(indices=indeksler, values=degerler),
                using=SEYREK_AD,
                limit=aday_limiti,
                filter=filtre,
                params=arama_params,
            )
        )

    # RRF birlesik sonuclari al
    sonuclar = istemci_al().query_points(
        collection_name=koleksiyon,
        prefetch=on_aramalar,
        query=FusionQuery(fusion=Fusion.RRF),
        limit=limit,
    ).points
    
    # Ham vektor skorlarini ayri bir aramadan al (menu kirliligi kontrolu icin)
    # YALNIZCA yogun vektor aramasinin skorlari - seyrek arama keyword bazli,
    # menu kirliligi zaten keyword eslesmesindendir.
    # API NOTU: `.search()` qdrant-client 1.18'de KALDIRILDI (kurulu surum
    # 1.18.0). Cagrildiginda AttributeError firlatiyor ve bu satir hibrit
    # aramanin ICINDE oldugu icin TUM RAG yolunu dusuruyordu - `getir()`
    # istisna atiyor, chatbot hicbir soruya cevap veremiyordu (olculdu
    # 25.08.2026: tests/test_rag_uctan_uca.py'de 10 hata).
    #
    # Ayni islemin guncel karsiligi `query_points`: yogun vektor uzerinde
    # tek basina arama yapmak icin `using=` ile vektor adi verilir.
    # Yukaridaki RRF cagrisi zaten bu API'yi kullaniyordu; yalnizca bu
    # ikinci cagri eski imzada kalmisti.
    # SKORLAR RRF SONUCLARININ KENDISI ICIN SORULUR.
    #
    # Onceki hali ayri bir "en iyi `limit` yogun sonuc" araması yapiyor ve
    # ID'leriyle eslestirmeye calisiyordu. Ama RRF, yogun VE seyrek aramanin
    # FUZYONUDUR - dondurdugu kayitlar yogun-only ilk N ile buyuk olcude
    # ortusmez. Olculdu (25.08.2026): tipik bir sorguda 5 parcanin 2-3'u
    # eslesmiyor ve `0.0` aliyordu.
    #
    # Bedeli sessizdi ama gercekti: retriever `max(vektor_skoru)` alip
    # ASGARI_VEKTOR_SKORU ile karsilastiriyor. Hicbiri eslesmezse max=0.0
    # cikar ve MESRU bir soru "vektor skoru cok dusuk" diye reddedilir -
    # yani cekimserlik karari, ID ortusmesinin rastlantisina baglanmis olur.
    #
    # Dogrusu: skoru, elde olan kayitlarin TAM KENDISI icin sormak.
    kimlikler = [s.id for s in sonuclar]
    ham_vektor_sonuclari = (
        istemci_al()
        .query_points(
            collection_name=koleksiyon,
            query=yogun_sorgu,
            using=YOGUN_AD,
            limit=len(kimlikler),
            query_filter=Filter(must=[HasIdCondition(has_id=kimlikler)]),
            search_params=arama_params,
        )
        .points
        if kimlikler
        else []
    )
    
    # RRF sonuc ID'leriyle ham vektor skorlarini eslestir
    ham_skor_map = {s.id: s.score for s in ham_vektor_sonuclari}
    
    return [
        {
            "skor": s.score,
            "ustveri": {
                **(s.payload or {}),
                "vektor_skoru": ham_skor_map.get(s.id, 0.0),
            }
        }
        for s in sonuclar
    ]


def yogun_ara(
    yogun_sorgu: list[float],
    limit: int = 5,
    koleksiyon: str = VARSAYILAN_KOLEKSIYON,
    filtre=None,
    exact: bool = False,
) -> list[dict]:
    """SAF yogun (dense-only) arama - seyrek vektor/RRF fuzyonu YOK.

    NEDEN VAR (bkz. docs/adr/0002-evren-cikarim-entegrasyonu.md, RAG_MODE):
    EVREN dokumantasyonunun kendi olcumunde hibrit fuzyon (0,85) ve
    yeniden siralama (0,55) saf yogun getirmenin (0,95) ALTINDA kaliyor.
    Bu fonksiyon, chunking/retriever.py::getir() icinde RAG_MODE=dense
    iken kullanilir - hibrit_ara() ile AYNI koleksiyon semasini (named
    "yogun"/"seyrek" vektorler) hedefler, yalnizca seyrek prefetch/fuzyon
    adimini atlar.

    DONUS BICIMI hibrit_ara() ILE BIREBIR AYNI - {"skor":..., "ustveri":
    {..., "vektor_skoru": ...}} - boylece chunking/retriever.py'deki
    "menu kirliligi" esik kontrolu (ASGARI_VEKTOR_SKORU, DENETIM BULGUSU
    24.08.2026) hangi arama modu kullanilirsa kullanilsin degismeden
    calisir. Burada `vektor_skoru` == `skor` (ikisi de ayni ham kosinus
    benzerligi) - hibrit_ara()'daki gibi AYRI bir ikinci sorguya gerek
    yok, zaten tek bir dense sorgu yapiliyor.
    """
    from qdrant_client.models import SearchParams

    arama_params = SearchParams(exact=exact) if exact else None
    # `.search()` DEGIL `.query_points()` - bkz. hibrit_ara() icindeki AYNI
    # denetim bulgusu (25 Agustos 2026, qdrant-client==1.18.0'da .search() yok).
    sonuclar = istemci_al().query_points(
        collection_name=koleksiyon,
        query=yogun_sorgu,
        using=YOGUN_AD,
        limit=limit,
        query_filter=filtre,
        search_params=arama_params,
    ).points
    return [
        {
            "skor": s.score,
            "ustveri": {**(s.payload or {}), "vektor_skoru": s.score},
        }
        for s in sonuclar
    ]


def coklu_filtre(banka: str | None = None, hedef_tarih: str | None = None):
    """Banka ve/veya tarihe (valid_at) gore Qdrant filtresi uretir.

    ==================================================================
    UYARI - `hedef_tarih` SU AN CALISMAZ, ACMAYIN
    ==================================================================
    Denetlendi (23 Agustos 2026): bu parametre `valid_at_start` ve
    `valid_at_end` alanlarina bakiyor, ama INDEKS PAYLOAD'INDA BU
    ALANLAR YOK. Indeksleyicinin yazdigi alanlar tam olarak sunlar
    (bkz. chunking/parcalayici.py):

        metin · banka · kaynak_url · kampanya_adi · erisim_zamani

    Qdrant'ta payload'da bulunmayan bir anahtara `must` kosulu HICBIR
    noktayi eslestirmez. Yani `hedef_tarih` verilirse arama BOS doner
    ve RAG her soruya "yeterli kaynak bulamadim" der - demoyu
    duzeltmek yerine tamamen bozar.

    Ayrica `erisim_zamani` TARAMA zamanidir, kampanya gecerlilik
    tarihi degil; onu tarih filtresi olarak kullanmak da yanlis olur.

    SECILEN YOL: filtrelemek yerine ISARETLEMEK. Kaynak her zaman
    donuyor, suresi dolmussa kullaniciya "sureli dolmus" rozetiyle
    gosteriliyor (bkz. agent/router.py::_guncellik_belirle ve
    api/schemas.py::Kaynak.guncellik). Gerekce: tarih yanlis
    cikarilmissa filtre GECERLI bir kampanyayi sessizce gorunmez
    yapar - juri demosunda fark edilmesi en zor hata turu budur.

    Bu parametreyi calisir hale getirmek isteyen once indeksleyiciye
    gecerlilik tarihlerini eklemeli ve indeksi yeniden kurmalidir.
    ==================================================================

    
    hedef_tarih (YYYY-MM-DD): Kampanyanin bu tarihte aktif oldugunu kontrol eder.
    (valid_at baslangicindan buyuk, bitisinden kucuk vs. - eger tek bir tarih alaniysa ona esitlik veya aralik)
    Scraper valid_at saglamadiginda erisim_zamani uzerinden de fallback yapilabilir,
    ancak mentör isteği dogrultusunda 'valid_at' veya genel bir zaman kiyaslamasi kullanilmalidir.
    """
    from qdrant_client.models import FieldCondition, Filter, MatchValue, Range
    kosullar = []
    if banka:
        kosullar.append(FieldCondition(key="banka", match=MatchValue(value=banka)))
    if hedef_tarih:
        # Geçmişe yönelik sorgularda 'valid_at' aralığı.
        # Basitlik acisindan 'valid_at_start' <= hedef_tarih <= 'valid_at_end' seklinde eklenebilir, 
        # ancak simdilik tek valid_at timestamp/date kontrolu (veya erisim_zamani) farz ediyoruz:
        # 'valid_at' kaydi var mi diye filtreleyebilir veya simdilik Range ile >= lte kullanabiliriz.
        # Asagidaki yapi, mentör raporundaki valid_at mentigini kurar:
        kosullar.append(FieldCondition(
            key="valid_at_start",
            range=Range(lte=hedef_tarih)
        ))
        kosullar.append(FieldCondition(
            key="valid_at_end",
            range=Range(gte=hedef_tarih)
        ))
    if not kosullar:
        return None
    return Filter(must=kosullar)


def koleksiyon_sayisi(koleksiyon: str = VARSAYILAN_KOLEKSIYON) -> Optional[int]:
    """Koleksiyondaki kayit sayisi; koleksiyon yoksa None."""
    istemci = istemci_al()
    if not istemci.collection_exists(koleksiyon):
        return None
    return istemci.count(collection_name=koleksiyon).count

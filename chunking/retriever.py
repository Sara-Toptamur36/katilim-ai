"""Retriever: kullanici sorusundan kaynakli parcalara.

Hibrit arama (yogun + seyrek, RRF birlestirme) + ABSTENTION kurali.

ABSTENTION NEDEN BURADA: Spike olcumu (docs/qdrant_spike_raporu.md,
Bulgu 2) yogun benzerlik skorunun tek basina "ilgili mi?" sorusunu
cevaplayamadigini gosterdi - tamamen alakasiz bir soru bile 0,78
aliyordu. Bir RAG sistemi, kaynagi olmayan soruya cevap uretirse
projenin temel ilkesini (rapor Bolum 5.7/15: eksik bilgi gizlenmez,
uydurulmaz) dogrudan ihlal eder.

KULLANILAN OLCUT - RRF skoru degil, LEXICAL ORTUSME:
RRF skoru bir SIRALAMA birlestirme skorudur; en ustteki sonuc her zaman
~1.0 civari alir, sorgu alakali olsa da olmasa da. Yani RRF skoruna esik
koymak ise yaramaz. Bunun yerine, donen parcalarin sorgunun AYIRT EDICI
terimlerini gercekten icerip icermedigine bakilir:

  - Alakali soru: sorgu terimleri parcalarda gecer (ortusme > 0)
  - Alakasiz soru ("uzay istasyonu"): hicbir terim gecmez (ortusme = 0)

Bu olcut, ham vektor benzerliginin aksine ALAKASIZ sorgularda net sifira
duser ve yorumlanabilir bir gerekce uretir ("hangi terimler eslesti?").
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import evren_istemci
from chunking.banka_tespit import banka_tespit
from chunking.embedding import sorguyu_vektore_cevir
from chunking.qdrant_baglanti import (
    VARSAYILAN_KOLEKSIYON,
    coklu_filtre,
    hibrit_ara,
    qdrant_hazir_mi,
    yogun_ara,
)
from chunking.reranker import rerank
from chunking.seyrek_vektor import (
    GOVDE_ASGARI_TOKEN,
    GOVDE_ONEK_UZUNLUGU,
    metni_tokenlara_ayir,
    seyrek_vektor_uret,
)

# Sorgunun ayirt edici terimlerinin en az bu orani donen parcalarda
# gecmezse "kaynak bulunamadi" sayilir.
#
# ESIK TAHMINLE DEGIL OLCUMLE SECILDI: gercek indeks uzerinde iki sinif
# sorgunun ortusme dagilimi cikarildi -
#   cevaplanabilir dogal sorular : en dusuk 0,667
#   alan disi sorular            : en yuksek 0,500
# 0,60 bu iki sinifin arasindaki bosluga oturur; her iki yonde de pay
# birakir (asiri cekimserlik ve uydurma cevap arasindaki denge).
#
# SINIRLILIK (durustluk notu): kalibrasyon kucuk bir ornekleme (6
# cevaplanabilir + 5 alan disi soru) dayanir. Daha genis bir soru seti
# olustukca yeniden olculmeli - bu yuzden sabit burada, tek yerde tutulur.
ASGARI_TERIM_ORTUSMESI = 0.60

# DENETIM BULGUSU (24.08.2026): Terim ortusme kontrolu YALNIZ BASINA
# YETERSIZ - site menu metni ("Konut Finansmani", "Kart Kampanyalari")
# genel terimleri icerir, sorgu terimleri gecse de vektor skoru cok dusuk
# (0.17/0.13/0.08). COZUM: terim ortusmesi GEREKLI ama YETERLI degil -
# bunun yaninda en yuksek vektor skorunun da makul olmasi gerekir.
#
# Ölcüldü: gerçek sorularda (Recall@5 %88.24 olan sette) en düşük top-1
# skor ~0.45 civari. Menu kirliliği sorununda 0.17. Esik 0.40 bu ikisinin
# arasina oturur.
#
# UYARI - BU ESIK YALNIZCA YEREL e5-base ICIN OLCULDU (bkz. docs/adr/0002):
# EVREN'in bge-m3-embed'i FARKLI bir model, kosinus benzerlik dagilimi
# ayni oldugunun garantisi yok. Gercek EVREN_API_KEY ile yeniden
# olculmeden bu deger EVREN yolunda da (dense VEYA hibrit modda) aynen
# kullaniliyor - bu BILINCLI bir gecici karar, kalibre edilmis bir
# sonuc DEGIL. ASGARI_VEKTOR_SKORU ortam degiskeniyle ezilebilir; EVREN
# ile gercek olcum yapildiginda burasi guncellenmeli.
ASGARI_VEKTOR_SKORU = float(os.environ.get("ASGARI_VEKTOR_SKORU", "0.40"))

# Cok kisa sorgularda ("murabaha nedir") tek terim bile yeterli olabilir;
# bu uzunlugun altinda oran yerine "en az 1 terim" kurali uygulanir.
KISA_SORGU_TERIM_SAYISI = 2


@dataclass
class RetrieverSonucu:
    """Retriever ciktisi - abstention karari ve gerekcesiyle birlikte."""

    parcalar: list[dict] = field(default_factory=list)
    yeterli_kaynak_var: bool = False
    terim_ortusmesi: float = 0.0
    eslesen_terimler: list[str] = field(default_factory=list)
    sebep: str | None = None


def _ayirt_edici_terimler(sorgu: str) -> list[str]:
    """Sorgunun arama icin anlamli terimleri (etkisiz kelimeler elenmis)."""
    return metni_tokenlara_ayir(sorgu)


def _govde(token: str) -> str:
    """Seyrek vektorle AYNI govde kurali - tutarlilik icin ayni sabitler."""
    return token[:GOVDE_ONEK_UZUNLUGU] if len(token) >= GOVDE_ASGARI_TOKEN else token


def _terim_ortusmesi(terimler: list[str], parcalar: list[dict]) -> tuple[float, list[str]]:
    """Sorgu terimlerinin kaci donen parcalarda geciyor?

    GOVDE DUYARLI: Turkce eklemeli oldugu icin tam token karsilastirmasi
    yaniltici olur - kullanicinin "kazanma" dedigi yerde metinde "kazanin"
    gecer ve tam eslesme BULUNAMAZ. Olculdu: "Worldpuan kazanma kosullari
    neler?" (cevaplanabilir bir soru) tam eslesmeyle yalnizca 0,50
    ortusme aliyordu - alan disi sorularin en yuksegiyle ayni seviye,
    yani ayirt edilemez hale geliyordu.

    Govde oneki, indeksleme tarafinda (chunking/seyrek_vektor.py) zaten
    kullanilan kuralin AYNISIDIR - iki taraf ayni normalizasyonu
    uygulamazsa olcum tutarsiz olur.
    """
    if not terimler:
        return 0.0, []

    birlesik = " ".join(
        (p.get("ustveri") or {}).get("metin", "") for p in parcalar
    )
    parca_tokenlari = set(metni_tokenlara_ayir(birlesik))
    parca_govdeleri = {_govde(t) for t in parca_tokenlari}

    eslesen = [
        t for t in terimler if t in parca_tokenlari or _govde(t) in parca_govdeleri
    ]
    return len(eslesen) / len(terimler), eslesen


def getir(
    soru: str,
    limit: int = 5,
    koleksiyon: str = VARSAYILAN_KOLEKSIYON,
    banka: str | None = None,
    hedef_tarih: str | None = None,
    exact: bool | None = None,
    banka_otomatik: bool | None = None,
    yeniden_sirala: bool | None = None,
    rag_modu: str | None = None,
) -> RetrieverSonucu:
    """Soruya en ilgili parcalari getirir; kaynak yetersizse bunu bildirir.

    `banka` verilirse arama o bankaya daraltilir (metadata filtresi).
    `hedef_tarih` SU AN CALISMAZ - baktigi valid_at alanlari indeks
    payload'inda yok, verilirse arama BOS doner. Ayrintili gerekce ve
    secilen alternatif icin bkz. qdrant_baglanti.coklu_filtre.

    `exact` parametresi Qdrant'in yaklasik HNSW aramasi yerine tam tarama
    (brute-force) kullanip kullanmayacagini belirler. None verilirse
    KATILIMAI_RAG_EXACT_MOD ortam degiskeni okunur ("true" ise exact=True).

    NEDEN GEREKLI (README ve docs/rag_tasarim_ve_olcum.md'de raporlandi):
    Qdrant HNSW varsayilan yaklasik aramasi Recall@1'i kosudan kosuya
    oynatiyordu (olculdu: 29/30/29). Cok yakin skorlu adaylarda 1. siranin
    degismesi buyuk indekslerde kacinilamaz. Olcum tutarli olmasi icin bu
    bayrak `true` verilmelidir. Uretim yolunda (hizli yanit onemli) exact
    gereksizdir - yalnizca olcum/test doneminde kullanilir.

    `banka_otomatik` sorguda gecen banka adinin metadata filtresine
    cevrilip cevrilmeyecegini belirler (bkz. chunking/banka_tespit.py -
    `banka_ve_konu` kategorisinin Recall@5 %50 sorununun dogrudan
    hedefi). `banka` parametresi ACIKCA verilmisse otomatik tespit
    devreye GIRMEZ - cagiranin karari her zaman ustundur.

    VARSAYILAN ACIK (25 Agustos 2026 - olculup dogrulandi). Onceden
    "henuz olculmedi" gerekcesiyle kapaliydi (bkz. asagidaki OLCUM YOLU).
    Duzeltilmis retriever koduyla (bkz. Bulgu 9, docs/rag_tasarim_ve_
    olcum.md) 185 soruluk sette KAPALI/ACIK karsilastirmasi kosuldu:

        k=1  banka_ve_konu %9,52  -> %23,81   (GENEL %66,39 -> %68,91)
        k=3  banka_ve_konu %28,57 -> %38,10   (GENEL %80,67 -> %82,35)
        k=5  banka_ve_konu %52,38 -> %47,62   (GENEL %88,24 -> %87,39)

    Uretimde agent/router.py::rag_aracini_cagir HER ZAMAN limit=3
    kullaniyor (limit=5 yalnizca bu olcum script'inde) - yani k=1/k=3'teki
    net kazanc GERCEKTEN KULLANILAN yol icin gecerli. k=5'teki kucuk
    dusus (21 sorudan 1'i) 21'lik ornekte gurultu seviyesinde ve
    kullanilmayan bir k degerinde - kazanci geciktirmeye deger degil.

    ELLE KAPATMAK ICIN: `KATILIMAI_BANKA_OTOMATIK=false` (ya da
    parametreyi acikca `banka_otomatik=False` vererek).

    OLCUM YOLU (tekrar dogrulamak icin): `KATILIMAI_BANKA_OTOMATIK=true`
    ile `python -m scraper.scripts.rag_degerlendirme` kosulur ve
    `banka_ve_konu` kategorisinin Recall'u kapali kosuyla karsilastirilir.

    `yeniden_sirala` cross-encoder reranker'i acar/kapatir. None verilirse
    KATILIMAI_RERANK okunur, varsayilan ACIK.

    `rag_modu` "hibrit" (yogun+seyrek, RRF) ya da "dense" (yalniz yogun)
    degerini alir. None verilirse RAG_MODE ortam degiskeni okunur; o da
    tanimli degilse SAGLAYICIYA GORE otomatik secilir - bkz.
    docs/adr/0002-evren-cikarim-entegrasyonu.md: EVREN'in bge-m3-embed'iyle
    hibrit fuzyon bu projede HENUZ OLCULMEDI (EVREN'in kendi olcumu farkli
    bir gomme modeliyle yapildi, bu depoya dogrudan tasinamaz), bu yuzden
    EVREN aktifken varsayilan "dense"tir. Yerel e5-base ile hibrit yolu
    docs/rag_tasarim_ve_olcum.md'de ZATEN OLCULUP varsayilan yapilmisti -
    bu davranis DEGISMEDI, yerel saglayicida varsayilan hala "hibrit"tir.
    Bu bayrak, iki modu ayni gold set uzerinde karsilastirmali olarak
    olcmeyi (Recall@1/@3, gecikme) mumkun kilmak icin var.

    NEDEN BAYRAKLI (metodoloji): bu iki katman da retrieval sonucunu
    degistirir. Kapatilabilir olmadiklari surece "katkisi ne kadar?"
    sorusu OLCULEMEZ - depodaki her kalite karari olcumle alindi
    (bkz. docs/rag_tasarim_ve_olcum.md), bu ikisi de ayni cubuga tabi.
    scraper/scripts/rag_degerlendirme.py bu bayraklarla A/B kosar.
    """
    if exact is None:
        exact = os.environ.get("KATILIMAI_RAG_EXACT_MOD", "false").lower() == "true"
    if banka_otomatik is None:
        banka_otomatik = os.environ.get("KATILIMAI_BANKA_OTOMATIK", "true").lower() == "true"
    if yeniden_sirala is None:
        yeniden_sirala = os.environ.get("KATILIMAI_RERANK", "true").lower() == "true"
    if rag_modu is None:
        rag_modu = os.environ.get(
            "RAG_MODE", "dense" if evren_istemci.aktif_mi() else "hibrit"
        ).strip().lower()
    if rag_modu not in ("hibrit", "dense"):
        raise ValueError(f"Bilinmeyen RAG_MODE: {rag_modu!r} (beklenen: 'hibrit' | 'dense')")

    if not qdrant_hazir_mi():
        return RetrieverSonucu(sebep="Vektor veritabanina (Qdrant) erisilemiyor")

    # --- Banka adi: aramadan filtreye ------------------------------------
    tespit_edilen_banka: str | None = None
    arama_sorgusu = soru
    if banka is None and banka_otomatik:
        tespit_edilen_banka, arama_sorgusu = banka_tespit(soru)
        banka = tespit_edilen_banka

    terimler = _ayirt_edici_terimler(arama_sorgusu)
    if not terimler:
        return RetrieverSonucu(sebep="Soruda aranabilir bir terim bulunamadi")

    def _ara(filtre_bankasi: str | None, sorgu_metni: str) -> list[dict]:
        # Ilk asamada RRF ile daha genis bir aday havuzu (örn. 20) aliyoruz.
        #
        # DENENDI VE GERI ALINDI (23 Agustos 2026, olculdu): 40'a cikarilinca
        # banka_ve_konu Recall@1 %14,29->%19,05 iyilesti AMA ayni kategoride
        # Recall@5 %52,38->%38,1'e, dogal_soru Recall@5 %92,86->%71,43'e,
        # GENEL Recall@5 %88,24->%83,19'a geriledi. Daha genis havuz cross-
        # encoder'a daha fazla dikkat dagitici aday sunuyor ve @1'deki kucuk
        # kazanci @3/@5'te daha buyuk bir kayipla odetiyor - net etki olumsuz.
        # Bkz. docs/rag_tasarim_ve_olcum.md Bulgu 6.
        genis_limit = max(20, limit * 2)
        filtre = coklu_filtre(banka=filtre_bankasi, hedef_tarih=hedef_tarih)
        if rag_modu == "dense":
            return yogun_ara(
                yogun_sorgu=sorguyu_vektore_cevir(sorgu_metni),
                limit=genis_limit,
                koleksiyon=koleksiyon,
                filtre=filtre,
                exact=exact,
            )
        return hibrit_ara(
            yogun_sorgu=sorguyu_vektore_cevir(sorgu_metni),
            seyrek_sorgu=seyrek_vektor_uret(sorgu_metni),
            limit=genis_limit,
            koleksiyon=koleksiyon,
            filtre=filtre,
            exact=exact,
        )

    aday_havuzu = _ara(banka, arama_sorgusu)

    # GERI DUSME: otomatik tespit yanlis bir bankaya daraltmis olabilir
    # (ör. indeks payload'indaki yazim bu listeyle uyusmuyorsa filtre HIC
    # nokta eslemez). Boyle bir durumda sessizce "kaynak yok" demek yerine
    # filtresiz aramayi tekrarlariz - otomatik tespit sistemi hicbir
    # kosulda mevcut davranistan KOTU hale getirmemelidir.
    if not aday_havuzu and tespit_edilen_banka is not None:
        tespit_edilen_banka = None
        banka = None
        arama_sorgusu = soru
        terimler = _ayirt_edici_terimler(soru)
        aday_havuzu = _ara(None, soru)

    if not aday_havuzu:
        return RetrieverSonucu(sebep="Arama hicbir sonuc dondurmedi")

    # --- Vektor skoru + terim ortusmesi kontrolu (menu kirliligi onlemi) --
    # DENETIM BULGUSU (25 Agustos 2026, IKI ASAMALI): bu iki kontrol
    # ONCEDEN reranker'in zaten `limit`e (3-5) kestigi SON listede
    # hesaplaniyordu - yorumdaki "ilk parcadaki en yuksek vektor skoru"
    # niyetiyle CELISIYORDU, cunku reranker capraz-kodlayici skoruna gore
    # siralar, vektor skoruna gore degil: gercek en yuksek vektor skorlu
    # aday reranker'in kestigi limit-disi bir yerde kalmis olabilirdi.
    #
    # ILK DUZELTME DENEMESI (ayni gun, GERI ALINDI): iki kontrolu de TUM
    # genis aday havuzunda (genis_limit=20+) hesaplamak once dogru
    # gorundu. OLCULDU ve YANLIS cikti: ASGARI_TERIM_ORTUSMESI esigi
    # (0,60) 20/21 Agustos'ta yalnizca DAR (limit boyutundaki) bir kumeye
    # gore kalibre edilmisti - `_terim_ortusmesi` butun parcalarin metnini
    # TEK bir birlesik dizgede arar, 20 adayin birlesik metni cok daha
    # genis bir "rastgele eslesme yuzeyi" yaratir. Gercek olcum: abstention
    # dogrulugu alan_disi'nda %86,67->%66,67, alan_ici_kapsam_disi'nda
    # %50,0->%20,0'e DUSTU (bkz. docs/rag_tasarim_ve_olcum.md, Bulgu 9
    # guncellemesi) - konuyla alakasiz sorular ("Fotosentez hangi
    # organelde gerceklesir?" gibi) sirf 20 farkli parcanin birlesik
    # kelime dagarcigi genisledigi icin yanlislikla esik gecti.
    #
    # DOGRU KAPSAM: reranker'dan ONCE ama AYNI BOYUTTA (ilk `limit` aday,
    # QDRANT'IN KENDI SIRALAMASIYLA - RRF/dense skoruna gore, capraz-
    # kodlayiciya gore DEGIL). Bu, hem orijinal hatayi cozer (kontrol
    # artik reranker'in yeniden siraladigi kumeye degil, gercek getirme
    # sirasina bakiyor) HEM DE terim ortusmesi kalibrasyonunun dayandigi
    # kume BOYUTUNU korur.
    on_siralama_ilk_k = aday_havuzu[:limit]

    # Ilk parcadaki en yuksek vektor skorunu kontrol et. Parcalarda
    # "score" alani RRF skorudur (siralama birlesimi) - ham vektor skoru
    # degil. Ham vektor skoru "ustveri.vektor_skoru" alaninda korunur
    # (qdrant_baglanti.hibrit_ara'da eklenir).
    en_yuksek_vektor_skoru = max(
        (
            (p.get("ustveri") or {}).get("vektor_skoru", 0.0)
            for p in on_siralama_ilk_k
        ),
        default=0.0,
    )

    ortusme, eslesen = _terim_ortusmesi(terimler, on_siralama_ilk_k)

    if len(terimler) <= KISA_SORGU_TERIM_SAYISI:
        yeterli_ortusme = len(eslesen) >= 1
    else:
        yeterli_ortusme = ortusme >= ASGARI_TERIM_ORTUSMESI

    # IKI KOSUL DA GERCEKLESMELI: terim ortusmesi + vektor skoru
    yeterli = yeterli_ortusme and en_yuksek_vektor_skoru >= ASGARI_VEKTOR_SKORU

    # Banka metadata ile eslesti - kanit listesinde gorunmeli.
    # ABSTENTION ACISINDAN: banka adi artik sorgu terimleri arasinda DEGIL
    # (filtreye tasindi), bu yuzden ortusme oranini SEYRELTMEZ. Bu dogru
    # davranis: "Kuveyt Türk kart" sorusunda banka kosulu metinle degil
    # metadata ile, kesin olarak saglanmistir - onu metinde de aramak ayni
    # kosulu iki kez talep etmek olurdu.
    if tespit_edilen_banka is not None:
        eslesen = [f"{tespit_edilen_banka} (metadata)", *eslesen]

    sebep = None
    if not yeterli:
        if not yeterli_ortusme:
            sebep = (
                f"Sorudaki terimlerin yalnizca %{ortusme * 100:.0f}'i kaynaklarda "
                "gecti - guvenilir bir cevap icin yetersiz"
            )
        else:
            sebep = (
                f"Terim ortusmesi yeterli (%{ortusme * 100:.0f}) ama en yuksek "
                f"vektor skoru cok dusuk ({en_yuksek_vektor_skoru:.2f} < {ASGARI_VEKTOR_SKORU}) - "
                "muhtemelen genel menu/navigasyon metni"
            )

    # Ucuncu asamada (Reranker) GOSTERILECEK parcalar capraz kodlayiciyla
    # siralanip kesilir - abstention KARARI yukarida, genis havuzla zaten
    # verildi. `yeterli=False` iken reranker HIC calistirilmaz: cekimser
    # sonucta agent/router.py::rag_aracini_cagir `parcalar`'a hic bakmaz
    # (erken doner), capraz-kodlayiciyi bosuna calistirmanin anlami yok.
    if yeterli and yeniden_sirala:
        parcalar = rerank(soru, aday_havuzu, top_k=limit)
    else:
        parcalar = aday_havuzu[:limit]

    return RetrieverSonucu(
        parcalar=parcalar,
        yeterli_kaynak_var=yeterli,
        terim_ortusmesi=round(ortusme, 3),
        eslesen_terimler=eslesen,
        sebep=sebep,
    )

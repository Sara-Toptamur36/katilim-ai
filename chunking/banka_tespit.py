"""Sorgu metninden banka adini tanir ve metadata filtresine cevirir.

NEDEN VAR (olculmus gerekce - docs/rag_tasarim_ve_olcum.md, 20/21 Agustos
olcumu): Degerlendirme setinin en zor kategorisi `banka_ve_konu`
(28 soru) Recall@5'te %50,0 ve Recall@1'de %0,0 aldi. Bu sorular tam
olarak su bicimde: "Kuveyt Turk kart", "Vakif Katilim yatirim urunu" -
yani kampanya ADI verilmiyor, yalnizca BANKA + GENEL KONU.

Sorunun kaynagi soyle: sorgudaki ayirt edici token'larin cogunlugunu
banka adi olusturuyor ("kuveyt", "turk"). Hem yogun hem seyrek arama bu
token'lara yuksek agirlik veriyor ve top-20 aday havuzu o bankanin
ALAKASIZ kampanyalariyla doluyor. Geriye kalan tek ayirt edici terim
("kart") skorda bogulup gidiyor.

COZUM - ayni bilgiyi ARAMA yerine FILTRE olarak kullanmak: banka adi
indeks payload'inda zaten `banka` alani olarak duruyor
(chunking/parcalayici.py: metin, banka, kaynak_url, kampanya_adi,
erisim_zamani) ve chunking/qdrant_baglanti.coklu_filtre bunu destekliyor
- ama retriever bu filtreyi hicbir yerden doldurmuyordu. Banka adini
sorgudan cikarip filtreye tasidigimizda:

  - aday havuzu 878 parcadan o bankanin parcalarina iner,
  - kalan sorgu ("kart") tum ayirt ediciligini geri kazanir.

Ek model, ek indirme, ek servis GEREKTIRMEZ - on-prem kisitlariyla
(Sartname Md. 5.9) tam uyumlu, tamamen deterministik bir kazanctir.

TAKMA AD SECIMI - bilincli olarak muhafazakar:
Tek kelimelik takma adlar yalnizca BASKA hicbir seye benzemeyen
isimler icin acildi (kuveyt, albaraka). "turkiye", "finans", "katilim",
"dunya", "hayat" gibi kelimeler ya iki bankada birden geciyor ya da
gunluk Turkce'de baska anlam tasiyor ("dunyanin en dusuk orani",
"hayat sigortasi"). Bunlari takma ad yapmak, banka adi GECMEYEN bir
soruyu yanlislikla tek bankaya daraltirdi - bu, kaciran bir aramadan
daha kotudur, cunku sessizce yanlis kaynak dondurur.
"""

from __future__ import annotations

import re
import unicodedata

# Indeks payload'indaki `banka` degerleri ile BIREBIR ayni yazilmalidir -
# scraper'in urettigi kayitlardan dogrulandi (9 banka, 513 kayit).
# Buradaki bir yazim farki filtreyi sessizce BOS sonuca dusurur.
KANONIK_BANKALAR: dict[str, tuple[str, ...]] = {
    "Kuveyt Türk": ("kuveyt turk", "kuveytturk", "kuveyt"),
    "Albaraka Türk": ("albaraka turk", "albaraka"),
    "Vakıf Katılım": ("vakif katilim", "vakifkatilim"),
    "Türkiye Finans": ("turkiye finans", "turkiyefinans"),
    "Ziraat Katılım": ("ziraat katilim", "ziraatkatilim"),
    "Türkiye Emlak Katılım": (
        "turkiye emlak katilim",
        "emlak katilim",
        "emlakkatilim",
    ),
    "Dünya Katılım": ("dunya katilim", "dunyakatilim"),
    "Hayat Finans": ("hayat finans", "hayatfinans"),
    "T.O.M. Katılım": ("t.o.m. katilim", "tom katilim", "tombank"),
}

_KATLAMA = str.maketrans("çğıöşüâîû", "cgiosuaiu")


def _katla(metin: str) -> str:
    """Diyakritikleri ve buyuk/kucuk farkini eleyerek karsilastirilabilir hale getirir.

    extraction/regex_extractor.py'deki katlama ile ayni ilke: kullanicinin
    "Vakif" mi "Vakıf" mi yazdigi eslesmeyi degistirmemeli.
    """
    kucuk = metin.replace("I", "ı").replace("İ", "i").lower()
    ayrik = unicodedata.normalize("NFKD", kucuk)
    ayrik = "".join(c for c in ayrik if not unicodedata.combining(c))
    return ayrik.translate(_KATLAMA)


# UZUN ONCE: "turkiye emlak katilim" (3 kelime), "turkiye finans"tan ONCE
# denenmeli - kisa olan once eslesirse Emlak Katilim sorusu yanlis bankaya
# gider. Sirayi uzunluga gore sabitlemek bu hatayi yapisal olarak imkansiz
# kilar (elle siralamaya guvenmez).
_TAKMA_ADLAR: list[tuple[str, str]] = sorted(
    ((takma, kanonik) for kanonik, takmalar in KANONIK_BANKALAR.items() for takma in takmalar),
    key=lambda ikili: -len(ikili[0]),
)


def banka_tespit(sorgu: str) -> tuple[str | None, str]:
    """Sorguda banka adi geciyor mu? Geciyorsa (kanonik_ad, banka_adi_cikarilmis_sorgu).

    Doner:
        (None, sorgu)                 - banka adi bulunamadi, sorgu degismedi
        ("Kuveyt Türk", "kart")       - banka filtreye tasindi, konu geriye kaldi

    KALAN SORGU NEDEN ONEMLI: banka adi filtreye donustukten sonra arama
    vektorlerinde de kalirsa hicbir sey kazanilmaz - aday havuzunun tamami
    zaten o bankadan geldigi icin "kuveyt turk" token'lari her parcada
    esit skor uretir, yani ayirt edici gucu sifirdir ama diger terimleri
    bastirmaya devam eder. Bu yuzden cikarilir.

    Kalan sorgu BOS kalirsa (kullanici yalnizca "Kuveyt Türk" yazdiysa)
    orijinal sorgu dondurulur - bos vektorle arama yapilamaz.
    """
    katlanmis = _katla(sorgu)

    for takma, kanonik in _TAKMA_ADLAR:
        # Kelime siniri: "tom" kelimesi "otomatik" icinde eslesmemeli.
        desen = re.compile(rf"(?<!\w){re.escape(takma)}(?!\w)")
        eslesme = desen.search(katlanmis)
        if not eslesme:
            continue

        # Katlama karakter sayisini degistirmez (harf->harf), bu yuzden
        # katlanmis metindeki konumlar HAM sorguda da gecerlidir.
        kalan = (sorgu[: eslesme.start()] + " " + sorgu[eslesme.end() :]).strip()
        kalan = re.sub(r"\s{2,}", " ", kalan)
        return kanonik, (kalan if kalan else sorgu)

    return None, sorgu

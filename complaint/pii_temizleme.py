"""PII temizleme: sikayet metninden kisisel veriyi KAYITTAN ONCE siler.

KIRMIZI CIZGI (Rehber_Zeynep_Veri.md): "PII temizligi kayittan ONCE.
Sonra temizlemek gec kalmaktir."

Bu siralamanin sebebi teknik degil hukuki: ham metin bir kez diske
yazildiginda, sonradan temizlense bile "islenmis" sayilir. Bu yuzden
complaint/toplama.py ham metni HIC saklamaz - temizlenmis surumu uretir
ve yalnizca onu dondurur.

--------------------------------------------------------------------------
NE YAKALANIR
--------------------------------------------------------------------------
TCKN, IBAN, telefon, e-posta, kart numarasi. Hepsi Turkiye bicimleriyle.

TCKN'de SADECE "11 hane" yetmez: musteri numarasi, siparis numarasi,
referans kodu da 11 haneli olabilir ve hepsini silmek metni okunmaz
hale getirirdi. Bu yuzden resmi ALGORITMA dogrulamasi uygulanir - ayni
ilke extraction/regex_extractor.py'deki "sayi tek basina yetmez, baglam
gerekir" dersinin PII tarafindaki karsiligi.

--------------------------------------------------------------------------
NE YAKALANMAZ (bilinen sinir, gizlenmiyor)
--------------------------------------------------------------------------
Serbest metindeki KISI ADLARI. Bunun icin NER gerekir ve elimizdeki
GLiNER zero-shot modeli Turkce adlarda guvenilir degil (bkz.
extraction/ner_extractor.py Bulgu 1-4). Yanlis bir guvence vermektense
sinir acikca yazilir: ad iceren metinler icin insan gozden gecirmesi
gerekir. `temizle()` bunu `insan_kontrolu_gerekir` bayragiyla soyler.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Maskeleme etiketleri - silinen seyin TURU korunur ki tema
# siniflandirmasi baglamini tamamen kaybetmesin ("[TELEFON]" gormek,
# metnin bir iletisim sikayeti oldugunu anlamaya yardim eder).
ETIKET = {
    "tckn": "[TCKN]",
    "iban": "[IBAN]",
    "kart": "[KART]",
    "telefon": "[TELEFON]",
    "eposta": "[EPOSTA]",
}

# IBAN: TR + 24 hane (bosluklu yazim yaygin).
_IBAN = re.compile(r"\bTR\s?(?:\d\s?){24}\b", re.IGNORECASE)

# Kart: 16 hane, bosluk/tire ile gruplanmis olabilir.
_KART = re.compile(r"\b(?:\d[ -]?){15}\d\b")

# Telefon: 05xx / +905xx / 5xx bicimleri, ayraclarla.
_TELEFON = re.compile(r"(?:\+90|0)?[\s(-]?5\d{2}[\s)-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}\b")

_EPOSTA = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")

# TCKN adayi: 11 hane. Gecerliligi ALGORITMAYLA sinanir (bkz. _tckn_gecerli_mi).
_TCKN_ADAYI = re.compile(r"\b\d{11}\b")


def _tckn_gecerli_mi(deger: str) -> bool:
    """Resmi TCKN dogrulama algoritmasi.

    Musteri/siparis numaralarini TCKN sanip silmemek icin gerekli:
    rastgele 11 haneli bir sayinin bu sinavi gecme olasiligi ~%1.
    """
    if len(deger) != 11 or not deger.isdigit() or deger[0] == "0":
        return False
    h = [int(c) for c in deger]
    tek = h[0] + h[2] + h[4] + h[6] + h[8]
    cift = h[1] + h[3] + h[5] + h[7]
    if (tek * 7 - cift) % 10 != h[9]:
        return False
    return sum(h[:10]) % 10 == h[10]


@dataclass
class TemizlemeSonucu:
    metin: str
    bulunanlar: dict[str, int] = field(default_factory=dict)
    insan_kontrolu_gerekir: bool = False

    @property
    def pii_bulundu_mu(self) -> bool:
        return bool(self.bulunanlar)


def _maskele(metin: str, desen: re.Pattern, etiket: str, sayac: dict) -> str:
    adet = 0

    def _degistir(_m):
        nonlocal adet
        adet += 1
        return etiket

    sonuc = desen.sub(_degistir, metin)
    if adet:
        sayac[etiket.strip("[]").lower()] = sayac.get(etiket.strip("[]").lower(), 0) + adet
    return sonuc


def temizle(ham_metin: str) -> TemizlemeSonucu:
    """Metni maskeler. Ham metin DONDURULMEZ - cagiran taraf yalnizca
    temizlenmis surumu gorur, boylece yanlislikla saklanamaz."""
    sayac: dict[str, int] = {}
    metin = ham_metin

    # SIRA ONEMLI: IBAN ve kart, telefon deseniyle capisabilecek uzun
    # rakam dizileridir - once uzun/spesifik olanlar maskelenir, yoksa
    # telefon deseni IBAN'in ortasindan parca kopariyordu (olculdu).
    metin = _maskele(metin, _IBAN, ETIKET["iban"], sayac)
    metin = _maskele(metin, _KART, ETIKET["kart"], sayac)

    # TCKN: desen 11 haneyi bulur, algoritma karar verir.
    tckn_adedi = 0

    def _tckn_degistir(m):
        nonlocal tckn_adedi
        if _tckn_gecerli_mi(m.group(0)):
            tckn_adedi += 1
            return ETIKET["tckn"]
        return m.group(0)  # gecerli TCKN degil - DOKUNULMAZ

    metin = _TCKN_ADAYI.sub(_tckn_degistir, metin)
    if tckn_adedi:
        sayac["tckn"] = tckn_adedi

    metin = _maskele(metin, _EPOSTA, ETIKET["eposta"], sayac)
    metin = _maskele(metin, _TELEFON, ETIKET["telefon"], sayac)

    return TemizlemeSonucu(
        metin=metin,
        bulunanlar=sayac,
        # Kisi adlari yakalanamiyor (bkz. modul docstring'i). PII bulunan
        # her metin, ayni cumlede ad da gecebilecegi icin insan gozden
        # gecirmesine isaretlenir - sessizce "temiz" denmez.
        insan_kontrolu_gerekir=bool(sayac),
    )

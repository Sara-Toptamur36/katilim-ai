"""Sozlukte birebir olmayan ama benzer ifadeleri de taniyabilen genisletme
servisi (Sprint 1, Gun 3).

SequenceMatcher, iki metnin yazim benzerligini 0-1 arasinda olcer (anlam
benzerligi degil - bu Sprint 3'teki embedding tabanli benzerlikten farkli,
daha basit bir ilk adimdir).
"""

from difflib import SequenceMatcher

from terminology.sozluk import sozluk_yukle


def _turkce_kucult(metin: str) -> str:
    """Python'un standart str.lower() Turkce noktali buyuk 'İ' harfini
    duz 'i' degil, gorunmez bir birlesik nokta karakteriyle kucultur
    (ornek: 'İ'.lower() -> 'i' + U+0307), bu da ALL-CAPS/Title Case
    gercek taranmis metinde SequenceMatcher oranini haksiz yere dusurur.
    Duz ASCII 'I' harfine bilerek dokunulmuyor - o hem 'I' hem 'ı'
    anlamina gelebilir (belirsiz), yanlis donusum yeni uyusmazlik yaratir.
    """
    return metin.replace("İ", "i").lower()


# gelenek_karsilik alani bu isaretle basliyorsa, o kavramin geleneksel
# bankacilikta karsiligi YOKTUR (ornek: musaraka, danisma_kurulu). Boyle
# girdiler ters aramaya KATILMAZ - "— (katilim bankaciligina ozgu...)"
# aciklama cumlesini bir terimmis gibi eslestirmek sacma sonuc uretir.
KARSILIK_YOK_ISARETI = "—"


def benzer_terim_bul(
    ifade: str, sozluk: dict | None = None, esik: float = 0.75
) -> tuple[str | None, float]:
    """Sozlukteki varyantlarla karsilastirip en cok benzeyen anahtari bulur.

    Donen skor esigin altindaysa (varsayilan 0.75) eslesme guvenilmez
    sayilir ve anahtar None olarak dondurulur.
    """
    sozluk = sozluk if sozluk is not None else sozluk_yukle()
    en_iyi_eslesme = None
    en_iyi_skor = 0.0
    for anahtar, veri in sozluk.items():
        for varyant in veri["varyantlar"]:
            skor = SequenceMatcher(
                None, _turkce_kucult(ifade), _turkce_kucult(varyant)
            ).ratio()
            if skor > en_iyi_skor:
                en_iyi_skor = skor
                en_iyi_eslesme = anahtar
    if en_iyi_skor >= esik:
        return en_iyi_eslesme, en_iyi_skor
    return None, en_iyi_skor


def gelenek_terimden_bul(
    ifade: str, sozluk: dict | None = None, esik: float = 0.75
) -> tuple[str | None, float]:
    """TERS ARAMA: kullanici GELENEK terimle sorarsa ("faiz orani nedir?")
    hangi katilim kavramini kastettigini bulur.

    NEDEN VAR (olculdu): sozluk yalnizca `varyantlar` uzerinden aranirken
    "Faiz orani nedir?" sorusuna sistem "'faiz orani' terimini sozlugumde
    bulamadim" diyordu. Oysa Md. 5.5 tam olarak bu ayrimi ogretmeyi
    istiyor - kullanicinin bildigi terim gelenek terimdir, ogrenmesi
    gereken katilim karsiligidir. Bulamamak degil, ceviriyi ogretmek
    dogru davranistir.

    `varyantlar` DEGIL, `gelenek_karsilik` alani taranir; karsiligi
    olmayan kavramlar (bkz. KARSILIK_YOK_ISARETI) disarida birakilir.

    Donen: (anahtar, skor) - benzer_terim_bul ile ayni sozlesme.
    """
    sozluk = sozluk if sozluk is not None else sozluk_yukle()
    en_iyi_eslesme = None
    en_iyi_skor = 0.0
    for anahtar, veri in sozluk.items():
        karsilik = veri.get("gelenek_karsilik", "")
        if not karsilik or karsilik.startswith(KARSILIK_YOK_ISARETI):
            continue
        # Parantez ici aciklamalar ("Kredi Maliyeti (Faiz + Masraflar
        # Toplami)") eslesme oranini duşurur - yalnizca terimin kendisi
        # karsilastirilir.
        terim = karsilik.split("(")[0].strip()
        skor = SequenceMatcher(
            None, _turkce_kucult(ifade), _turkce_kucult(terim)
        ).ratio()
        if skor > en_iyi_skor:
            en_iyi_skor = skor
            en_iyi_eslesme = anahtar
    if en_iyi_skor >= esik:
        return en_iyi_eslesme, en_iyi_skor
    return None, en_iyi_skor

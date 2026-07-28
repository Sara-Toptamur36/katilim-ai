"""Sozlukte birebir olmayan ama benzer ifadeleri de taniyabilen genisletme
servisi (Sprint 1, Gun 3).

SequenceMatcher, iki metnin yazim benzerligini 0-1 arasinda olcer (anlam
benzerligi degil - bu Sprint 3'teki embedding tabanli benzerlikten farkli,
daha basit bir ilk adimdir).
"""

from difflib import SequenceMatcher

from terminology.sozluk import sozluk_yukle


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
            skor = SequenceMatcher(None, ifade.lower(), varyant.lower()).ratio()
            if skor > en_iyi_skor:
                en_iyi_skor = skor
                en_iyi_eslesme = anahtar
    if en_iyi_skor >= esik:
        return en_iyi_eslesme, en_iyi_skor
    return None, en_iyi_skor

"""Terminoloji sozlugunu okumaya yarayan yardimci fonksiyonlar.

Sozluk, katilim bankaciligina ozgu kavramlari (rapor Bolum 5.5) gelenek
bankacilik karsiliklarina ve CampaignRecord sema alanlarina (api/schemas.py)
baglar.
"""

import json
from pathlib import Path

SOZLUK_YOLU = Path(__file__).parent / "sozluk.json"


def sozluk_yukle(yol: Path | str = SOZLUK_YOLU) -> dict:
    """sozluk.json dosyasini okuyup dict olarak dondurur."""
    with open(yol, "r", encoding="utf-8") as f:
        return json.load(f)


def gelenek_karsiligi_bul(anahtar: str, sozluk: dict | None = None) -> str | None:
    """Verilen sozluk anahtarinin (ornek: 'kar_payi_orani') geleneksel
    bankacilik karsiligini dondurur. Anahtar bulunamazsa None doner."""
    sozluk = sozluk if sozluk is not None else sozluk_yukle()
    veri = sozluk.get(anahtar)
    return veri["gelenek_karsilik"] if veri else None


def sema_alanlarini_bul(anahtar: str, sozluk: dict | None = None) -> list[str]:
    """Verilen kavramin CampaignRecord semasindaki hangi alan(lar)a
    karsilik geldigini dondurur (ornek: 'kar_payi_orani' -> ['kar_payi_orani_percent', ...])."""
    sozluk = sozluk if sozluk is not None else sozluk_yukle()
    veri = sozluk.get(anahtar)
    return veri["sema_alani"] if veri else []

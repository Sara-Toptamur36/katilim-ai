"""RAG indeksinin son kurulum durumu - yaz/oku.

NEDEN AYRI MODUL: Bu durumu YAZAN taraf chunking/indeksleyici.py'dir ve o
modul embedding/Qdrant zincirini import eder. OKUYAN taraf ise api/main.py -
API'nin indeksleme bagimliliklarini yuklemesi icin hicbir sebep yok.
Kucuk ve bagimsiz bir modul, API acilis suresini gereksiz yere uzatmaz.

NEDEN DOSYA: Qdrant koleksiyon ustverisinde "olusturulma zamani" alani yok,
dolayisiyla indeksin ne zaman kuruldugunu Qdrant'a sorarak ogrenemiyoruz.
logs/ .gitignore'da - bu bir calisma zamani durumu, kaynak kod degil.
"""

from __future__ import annotations

import json
from pathlib import Path

DURUM_DOSYASI = Path(__file__).resolve().parent.parent / "logs" / "rag_indeks_durumu.json"


def indeks_durumu_oku() -> dict | None:
    """Son indekslemenin ozeti.

    Dosya yoksa None doner - bu "indeks eski" DEGIL, "indeks durumu
    bilinmiyor" demektir. Ikisi farkli seylerdir ve arayuzde de farkli
    gosterilir (bkz. README tasarim ilkesi 1: belirsizlik gizlenmez).
    """
    try:
        with open(DURUM_DOSYASI, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def indeks_durumu_yaz(ozet: dict) -> None:
    DURUM_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
    with open(DURUM_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(ozet, f, ensure_ascii=False, indent=2)

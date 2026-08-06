"""Tam indeksleme boru hatti: ham scraper verisi -> aranabilir Qdrant indeksi.

Zincir:
    scraper/raw_data/*/json/*.json
      -> chunking/parcalayici.py   (semantik parcalama + tekillestirme)
      -> chunking/embedding.py     (yogun/anlamsal vektor)
      -> chunking/seyrek_vektor.py (seyrek/kelime vektoru)
      -> Qdrant hibrit koleksiyonu

TEKRAR CALISTIRILABILIR: Varsayilan olarak koleksiyonu SIFIRDAN kurar
(`sifirla=True`). Bunun gerekcesi, parcalama mantigi degistiginde eski
parcalarin indekste kalip sonuclari kirletmesidir - parca kimlikleri
icerige degil siraya bagli oldugu icin kismi guncelleme guvenilir
olmazdi. Indeksleme tek seferlik ve toplu bir istir (olculdu: ~700 parca
icin birkac dakika), bu yuzden sifirdan kurmak kabul edilebilir.

Kullanim:
    docker compose up -d qdrant
    python -m chunking.indeksleyici
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from chunking.embedding import VEKTOR_BOYUTU, belgeleri_vektore_cevir
from chunking.parcalayici import kayitlari_parcala
from chunking.qdrant_baglanti import (
    QDRANT_URL,
    VARSAYILAN_KOLEKSIYON,
    hibrit_koleksiyon_hazirla,
    hibrit_parcalari_ekle,
    koleksiyon_sayisi,
    qdrant_hazir_mi,
)
from chunking.seyrek_vektor import seyrek_vektor_uret

RAW_DATA = Path(__file__).resolve().parent.parent / "scraper" / "raw_data"

# Embedding'i toplu yapmak tek tek yapmaktan belirgin hizli (olculdu:
# 20 metin tek cagrida ~0.9 sn). Cok buyuk yigin bellek tuketir.
YIGIN_BOYUTU = 32


def ham_kayitlari_yukle() -> list[dict]:
    kayitlar = []
    for dosya in sorted(RAW_DATA.glob("*/json/*.json")):
        try:
            with open(dosya, encoding="utf-8") as f:
                kayitlar.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            continue
    return kayitlar


def indeksle(
    koleksiyon: str = VARSAYILAN_KOLEKSIYON,
    sifirla: bool = True,
    ilerleme_yaz: bool = False,
) -> dict:
    """Tum ham veriyi parcalayip Qdrant'a indeksler."""
    if not qdrant_hazir_mi():
        raise RuntimeError(
            f"Qdrant'a erisilemiyor ({QDRANT_URL}). "
            "Once calistirin: docker compose up -d qdrant"
        )

    t0 = time.monotonic()
    kayitlar = ham_kayitlari_yukle()
    parcalar = kayitlari_parcala(kayitlar)
    parcalama_sn = time.monotonic() - t0

    if not parcalar:
        raise RuntimeError("Hic parca uretilemedi - scraper verisi bos olabilir")

    hibrit_koleksiyon_hazirla(koleksiyon, vektor_boyutu=VEKTOR_BOYUTU, sifirla=sifirla)

    t1 = time.monotonic()
    yazilan = 0
    for baslangic in range(0, len(parcalar), YIGIN_BOYUTU):
        yigin = parcalar[baslangic : baslangic + YIGIN_BOYUTU]
        metinler = [p["metin"] for p in yigin]

        yogun = belgeleri_vektore_cevir(metinler)
        seyrek = [seyrek_vektor_uret(m) for m in metinler]

        yazilan += hibrit_parcalari_ekle(
            yogun, seyrek, yigin, koleksiyon=koleksiyon, baslangic_id=baslangic
        )
        if ilerleme_yaz:
            print(f"  {yazilan}/{len(parcalar)} parca indekslendi", flush=True)

    indeksleme_sn = time.monotonic() - t1

    return {
        "belge_sayisi": len(kayitlar),
        "parca_sayisi": len(parcalar),
        "yazilan": yazilan,
        "koleksiyondaki_kayit": koleksiyon_sayisi(koleksiyon),
        "sureler_sn": {
            "parcalama": round(parcalama_sn, 2),
            "indeksleme": round(indeksleme_sn, 2),
        },
    }


if __name__ == "__main__":
    print("Indeksleme basliyor (embedding modeli ilk cagrida yuklenir)...")
    sonuc = indeksle(ilerleme_yaz=True)
    print()
    print("=== Indeksleme tamamlandi ===")
    print(f"Belge      : {sonuc['belge_sayisi']}")
    print(f"Parca      : {sonuc['parca_sayisi']}")
    print(f"Indekslenen: {sonuc['yazilan']} (koleksiyonda: {sonuc['koleksiyondaki_kayit']})")
    print(f"Sureler    : {sonuc['sureler_sn']}")

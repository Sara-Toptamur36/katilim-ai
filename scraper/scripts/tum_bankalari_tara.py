"""Config'teki tum bankalari tek komutla tarayan orkestrator.

Rehber Sprint 3 Gun 5 (Bolum "Periyodik Calistirma + Delta Kontrolu").
Simdiden yazilmasinin nedeni: config-driven yapi zaten Sprint 1'de
kuruldugu icin, "tek komutla tum bankalari tara" ozelligi ek bir
mimari degisiklik gerektirmiyor - yalnizca config'i donup ayni
fonksiyonu cagirmak yeterli.

KRITIK TASARIM KARARI - continue: Bir banka hata verirse (site coktu,
yapisi degisti) tum tarama DURMAZ; diger bankalarin verisi bir
bankanin sorunu yuzunden kaybedilmez.

Kullanim:
    python -m scraper.scripts.tum_bankalari_tara
"""

from __future__ import annotations

from datetime import datetime

from scraper.scripts import ortak
from scraper.scripts.statik_scraper import banka_tara, config_yukle


def tumunu_tara() -> dict:
    bankalar = config_yukle()

    genel_ozet: dict[str, dict] = {}

    for kod, ayar in bankalar.items():
        if ayar.get("sayfa_turu") != "HTML":
            ortak.log_yaz(kod, "atlandi: bu scraper yalnizca HTML statik bankalari destekliyor")
            continue
        try:
            ozet = banka_tara(kod, ayar)
        except Exception as e:  # noqa: BLE001 - bir banka patlarsa digerleri devam etsin
            ortak.log_yaz(kod, f"BANKA GENELİ HATA: {e}")
            genel_ozet[kod] = {"basarili": [], "atlandi": [], "hatali": [{"hata": str(e)}]}
            continue
        genel_ozet[kod] = ozet

    print(f"[{datetime.now().isoformat(timespec='seconds')}] Tarama ozeti:")
    for kod, ozet in genel_ozet.items():
        print(
            f"  {kod:15} basarili={len(ozet['basarili']):3}  "
            f"atlandi={len(ozet['atlandi']):3}  hatali={len(ozet['hatali']):3}"
        )

    return genel_ozet


if __name__ == "__main__":
    tumunu_tara()

"""Scraper'in urettigi ham JSON kayitlarini PostgreSQL'e yukler.

Zeynep Veri Toplama Rehberi Bolum 8 (Sprint 2 Gun 3) ile ayni tasarimi
izler: scraper/raw_data/{banka}/json/*.json dosyalarini okur, her biri
icin kampanyalar tablosunda bir satir olusturur.

ONEMLI - Yagmur'un cikarim katmaniyla catisma onlenir: bu script SADECE
KAYNAK/IZLENEBILIRLIK alanlarini (banka, kaynak_url, belge_tarihi) yazar.
Finansal alanlar (kar_payi_orani, vade_ay, odul_miktari vb.) henuz
CIKARILMADI - hepsi NULL birakilir ve alan_belirtilmemis'te True olarak
isaretlenir (rapor Bolum 5.7/15 - seffaflik ilkesi). Yagmur'un regex/NER/LLM
katmani calistiginda bu alanlari AYRI bir guncelleme adiminda dolduracak.

Idempotent: ayni kaynak_url tekrar calistirildiginda var olan satir
GUNCELLENMEZ (yalnizca "son gorulme" tarihi tazelenir) - boylece bu script
tekrar tekrar calistirilsa bile Yagmur'un sonradan doldurdugu cikarim
degerlerini SILMEZ/UZERINE YAZMAZ.

Kullanim:
    python -m scraper.scripts.postgrese_yukle
"""

import json
import re
from datetime import datetime
from pathlib import Path

from api.db import OturumYerel
from api.models import Kampanya

RAW_DATA_KOK = Path(__file__).resolve().parents[1] / "raw_data"

# Cikarim henuz yapilmadigi icin bu alanlarin hepsi "belirtilmemis" isaretlenir.
HENUZ_CIKARILMAMIS_ALANLAR = [
    "kampanya_turu",
    "kar_payi_orani_percent",
    "kar_payi_orani_decimal",
    "vade_ay",
    "taksit_sayisi",
    "erteleme_suresi_ay",
    "finansman_tutari",
    "odul_miktari",
    "odul_birimi",
    "kampanya_avantaji",
    "masraf_durumu",
    "tahsis_ucreti",
    "kampanya_baslangic",
    "kampanya_bitis",
    "hedef_kitle",
]


def _url_slug_to_baslik(url: str) -> str:
    """URL'nin son parcasindan okunabilir bir gecici baslik uretir.

    NOT: Bu, gercek kampanya basligi DEGILDIR - yalnizca kampanya_adi
    alani NOT NULL oldugu icin bir yer tutucudur. Yagmur'un cikarim
    katmani calistiginda daha dogru bir baslikla guncellenmelidir.
    """
    son_parca = url.rstrip("/").split("/")[-1]
    son_parca = re.sub(r"[?#].*$", "", son_parca)  # sorgu string'i varsa at
    kelimeler = son_parca.replace("_", "-").split("-")
    return " ".join(k.capitalize() for k in kelimeler if k) or "Baslik Belirlenemedi"


def _json_kayitlarini_bul() -> list[Path]:
    return sorted(RAW_DATA_KOK.glob("*/json/*.json"))


def yukle() -> dict:
    """Tum ham JSON kayitlarini okuyup veritabanina yazar.

    Donen ozet: {"eklendi": N, "atlandi": M, "hatali": [...]}
    """
    ozet = {"eklendi": 0, "atlandi": 0, "hatali": []}
    oturum = OturumYerel()

    try:
        for dosya in _json_kayitlarini_bul():
            try:
                with open(dosya, encoding="utf-8") as f:
                    kayit = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                ozet["hatali"].append((str(dosya), str(e)))
                continue

            kaynak_url = kayit.get("url")
            banka = kayit.get("banka")
            if not kaynak_url or not banka:
                ozet["hatali"].append((str(dosya), "url veya banka alani eksik"))
                continue

            mevcut = (
                oturum.query(Kampanya)
                .filter(Kampanya.kaynak_url == kaynak_url)
                .first()
            )

            if mevcut:
                # Zaten var - cikarim alanlarina DOKUNMA, sadece son gorulme
                # tarihini tazele (Yagmur'un doldurdugu degerleri korumak icin).
                mevcut.belge_tarihi = _tarihi_cikar(kayit.get("erisim_zamani"))
                ozet["atlandi"] += 1
                continue

            yeni = Kampanya(
                banka=banka,
                kampanya_adi=_url_slug_to_baslik(kaynak_url),
                kampanya_turu=None,
                kaynak_url=kaynak_url,
                belge_tarihi=_tarihi_cikar(kayit.get("erisim_zamani")),
                durum="BILINMIYOR",
                confidence=0.0,
                cikarim_yontemi=None,
                alan_belirtilmemis={alan: True for alan in HENUZ_CIKARILMAMIS_ALANLAR},
            )
            oturum.add(yeni)
            ozet["eklendi"] += 1

        oturum.commit()
    finally:
        oturum.close()

    return ozet


def _tarihi_cikar(iso_zaman: str | None):
    if not iso_zaman:
        return None
    try:
        return datetime.fromisoformat(iso_zaman).date()
    except ValueError:
        return None


if __name__ == "__main__":
    sonuc = yukle()
    print(f"Yuklendi: {sonuc['eklendi']} yeni, {sonuc['atlandi']} zaten vardi (tazelendi)")
    if sonuc["hatali"]:
        print(f"Hatali {len(sonuc['hatali'])} dosya:")
        for dosya, hata in sonuc["hatali"]:
            print(f"  {dosya}: {hata}")

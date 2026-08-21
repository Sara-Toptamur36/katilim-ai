"""Izin kapisi: sikayet verisi toplanmadan ONCE gecilmesi gereken kapi.

KIRMIZI CIZGI (Rehber_Zeynep_Veri.md): "Sikayet ham metni izin kapisi
gecmeden diske YAZILMAZ. Faz 2'de bile once izin, sonra veri."

Bu modul o cizgiyi bir NIYET BEYANI olmaktan cikarip CALISAN BIR KONTROLE
donusturur. Izin kaydi yoksa toplama/kayit fonksiyonlari calismaz -
"dikkat edelim" notu degil, calistirilamayan kod.

--------------------------------------------------------------------------
NE OLDUGU VE NE OLMADIGI
--------------------------------------------------------------------------
BU BIR HUKUKI ONAY DEGILDIR. Buradaki kayit, kurumsal/hukuki (KVKK) surecin
TAMAMLANDIGINI *isaretler*; sureci kendisi yurutmez. Dosyayi elle olusturup
"izin var" yazmak, izni almis olmak anlamina gelmez - kapiyi acan kisi
kaydi kendi adiyla imzalar ve bu kayit denetlenebilir kalir.

Kapinin degeri sudur: izin ALINMADAN once kimse "sadece deneme yapiyorum"
diyerek gercek sikayet metnini diske yazamaz. Kazayla ingest, en sik
gorulen KVKK ihlali bicimidir.

--------------------------------------------------------------------------
NEDEN KAYNAK BAZLI
--------------------------------------------------------------------------
Izin, veri kaynagi bazinda verilir. "Sikayetvar icin izin alindi" ile
"tum sikayet platformlari icin izin alindi" ayni sey degildir; ikincisi
alinmamis bir izni varmis gibi gostermek olurdu.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

IZIN_DOSYASI = Path(__file__).resolve().parent.parent / "logs" / "sikayet_izin_durumu.json"

# Izin kaydinda BULUNMASI ZORUNLU alanlar. Eksik alan = gecersiz izin;
# yarim doldurulmus bir kayit "izin var" saymaz (bkz. _kaydi_dogrula).
ZORUNLU_ALANLAR = ("kaynak", "onaylayan", "kurum", "onay_tarihi", "kapsam")


class IzinYok(RuntimeError):
    """Izin kapisi acilmadan sikayet verisine dokunulmaya calisildi."""


@dataclass(frozen=True)
class Izin:
    kaynak: str
    onaylayan: str
    kurum: str
    onay_tarihi: date
    kapsam: str
    gecerlilik_bitis: date | None = None

    def gecerli_mi(self, bugun: date | None = None) -> bool:
        bugun = bugun or datetime.now(timezone.utc).date()
        if self.onay_tarihi > bugun:
            return False  # ileri tarihli onay henuz yururlukte degil
        if self.gecerlilik_bitis is None:
            return True
        return bugun <= self.gecerlilik_bitis


def _tarihe_cevir(deger) -> date | None:
    if deger in (None, ""):
        return None
    if isinstance(deger, date):
        return deger
    return date.fromisoformat(str(deger))


def _kaydi_dogrula(ham: dict) -> Izin | None:
    """Eksik/bozuk kayit SESSIZCE "izin var" sayilmaz - None doner."""
    if not all(ham.get(a) for a in ZORUNLU_ALANLAR):
        return None
    try:
        return Izin(
            kaynak=str(ham["kaynak"]),
            onaylayan=str(ham["onaylayan"]),
            kurum=str(ham["kurum"]),
            onay_tarihi=_tarihe_cevir(ham["onay_tarihi"]),
            kapsam=str(ham["kapsam"]),
            gecerlilik_bitis=_tarihe_cevir(ham.get("gecerlilik_bitis")),
        )
    except (ValueError, TypeError):
        return None


def izinleri_oku(dosya: Path | None = None) -> list[Izin]:
    """Kayitli izinler. Dosya yoksa BOS liste - "izin yok" varsayilandir."""
    yol = dosya or IZIN_DOSYASI
    if not yol.exists():
        return []
    try:
        ham = json.loads(yol.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # Bozuk dosya "izin var" anlamina GELMEZ; en guvenli yorum yokluktur.
        return []
    kayitlar = ham if isinstance(ham, list) else [ham]
    return [i for i in (_kaydi_dogrula(k) for k in kayitlar) if i is not None]


def izin_var_mi(kaynak: str, bugun: date | None = None, dosya: Path | None = None) -> bool:
    """Bu KAYNAK icin gecerli bir izin var mi?"""
    return any(
        i.kaynak.lower() == kaynak.lower() and i.gecerli_mi(bugun)
        for i in izinleri_oku(dosya)
    )


def izni_zorunlu_kil(kaynak: str, bugun: date | None = None, dosya: Path | None = None) -> Izin:
    """Izin yoksa IzinYok firlatir. Sikayet verisine dokunan HER yol bunu
    once cagirmali (bkz. complaint/toplama.py)."""
    for i in izinleri_oku(dosya):
        if i.kaynak.lower() == kaynak.lower() and i.gecerli_mi(bugun):
            return i
    raise IzinYok(
        f"'{kaynak}' kaynagi icin kayitli ve gecerli bir izin yok. "
        f"Sikayet verisi TOPLANAMAZ ve DISKE YAZILAMAZ. "
        f"Kurumsal/hukuki (KVKK) onay tamamlandiktan sonra izin kaydi "
        f"{IZIN_DOSYASI} dosyasina eklenmelidir "
        f"(zorunlu alanlar: {', '.join(ZORUNLU_ALANLAR)})."
    )

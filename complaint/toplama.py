"""Sikayet toplama hatti: izin -> PII temizligi -> siniflandirma -> kayit.

SIRA BU MODULUN TAMAMIDIR. Adimlarin sirasi bir tercih degil, iki
kirmizi cizginin (Rehber_Zeynep_Veri.md) kodla uygulanmis halidir:

    1. IZIN     - izin kapisi gecilmeden hicbir sey islenmez
    2. PII      - temizlik KAYITTAN ONCE; ham metin fonksiyondan bile cikmaz
    3. TEMA     - kural tabanli siniflandirma
    4. ESLESME  - kampanya baglantisi (hipotez, esik altinda uretilmez)
    5. KAYIT    - yalnizca temizlenmis surum, AYRI tabloya

--------------------------------------------------------------------------
HAM METIN NEDEN GERI DONDURULMUYOR
--------------------------------------------------------------------------
`hazirla()` ham metni ne doner ne loglar. Donerse cagiran taraf onu
yanlislikla saklayabilir ve "temizlik kayittan once" garantisi cagri
yerine baglanir - yani garanti olmaktan cikar. Tek cikis temizlenmis
metindir.

--------------------------------------------------------------------------
BU HAT SU AN GERCEK VERIYLE CALISMIYOR
--------------------------------------------------------------------------
Kod hazir, VERI YOK: kurumsal/hukuki (KVKK) onay tamamlanmadigi icin
izin kaydi da yok, dolayisiyla `hazirla()` gercek bir kaynak icin
IzinYok firlatir. Sentetik ornekler uzerinde calistirmak icin
`izin_zorunlu=False` verilir - bu BILEREK acik bir kapi degildir:
diske yazan `kaydet()` bu bayragi TANIMAZ, her zaman izin arar.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Sequence

from complaint.izin_kapisi import Izin, izni_zorunlu_kil
from complaint.kampanya_eslestirme import EslesmeSonucu, kampanya_esle
from complaint.pii_temizleme import temizle
from complaint.tema_siniflandirici import tema_siniflandir


@dataclass
class HazirSikayet:
    """Kayda hazir sikayet. HAM METIN ICERMEZ."""

    temiz_metin: str
    pii_bulundu: bool
    insan_kontrolu_gerekir: bool
    tema: str | None
    tema_kaniti: str | None
    kaynak: str
    sikayet_tarihi: date | None
    eslesme: EslesmeSonucu


def hazirla(
    ham_metin: str,
    kaynak: str,
    kampanyalar: Sequence[Any] = (),
    sikayet_tarihi: date | None = None,
    izin_zorunlu: bool = True,
    bugun: date | None = None,
) -> HazirSikayet:
    """Tek bir sikayeti kayda hazirlar.

    izin_zorunlu=False YALNIZCA sentetik/test verisi icindir; gercek
    kaynaklarda kullanilmamalidir (bkz. modul docstring'i).
    """
    if izin_zorunlu:
        izni_zorunlu_kil(kaynak, bugun=bugun)

    # PII, baska HICBIR islemden once. Tema siniflandirmasi da
    # temizlenmis metin uzerinde calisir - siniflandirici ham metni
    # gormemeli.
    temizlenmis = temizle(ham_metin)

    # Siniflandirici TEMIZLENMIS metni gorur - ham metni hicbir alt
    # katman gormemeli.
    tema_sonucu = tema_siniflandir(temizlenmis.metin)
    eslesen = tema_sonucu.get("eslesen_ifadeler") or []

    eslesme = kampanya_esle(
        temizlenmis.metin, kampanyalar, sikayet_tarihi=sikayet_tarihi
    )

    return HazirSikayet(
        temiz_metin=temizlenmis.metin,
        pii_bulundu=temizlenmis.pii_bulundu_mu,
        insan_kontrolu_gerekir=temizlenmis.insan_kontrolu_gerekir,
        tema=tema_sonucu.get("tema"),
        # Kanit, eslesen ifadelerin kendisidir - "neden bu temaya girdi?"
        # sorusu sayiyla degil METINLE cevaplanabilmeli.
        tema_kaniti=", ".join(eslesen)[:200] or None,
        kaynak=kaynak,
        sikayet_tarihi=sikayet_tarihi,
        eslesme=eslesme,
    )


def kaydet(oturum, hazir: HazirSikayet, bugun: date | None = None):
    """Hazirlanmis sikayeti AYRI `sikayetler` tablosuna yazar.

    Izin BURADA DA sorulur - `hazirla()` sentetik veri icin izin
    atlayabildigi halde, diske yazan bu fonksiyon bayrak tanimaz.
    Tek bir yerde unutulan kontrol, tum garantiyi bosa cikarirdi.
    """
    from api.models import Sikayet

    izin: Izin = izni_zorunlu_kil(hazir.kaynak, bugun=bugun)

    satir = Sikayet(
        temiz_metin=hazir.temiz_metin,
        pii_bulundu=hazir.pii_bulundu,
        insan_kontrolu_gerekir=hazir.insan_kontrolu_gerekir,
        tema=hazir.tema,
        tema_kaniti=hazir.tema_kaniti,
        kaynak=hazir.kaynak,
        izin_onaylayan=izin.onaylayan,
        izin_onay_tarihi=izin.onay_tarihi,
        eslesen_kampanya_id=hazir.eslesme.kampanya_id,
        eslesme_guveni=hazir.eslesme.guven,
        eslesme_gerekcesi=hazir.eslesme.gerekce,
        sikayet_tarihi=hazir.sikayet_tarihi,
    )
    oturum.add(satir)
    return satir


def yogunluk_ozeti(sikayetler: Sequence[HazirSikayet]) -> dict[str, Any]:
    """Tema bazli GOZLENEN YOGUNLUK.

    KIRMIZI CIZGI: "'Sikayet orani' deme. Musteri/islem paydasi yoksa
    oran degildir; 'gozlenen yogunluk' de." Bu yuzden burada yuzde
    HESAPLANMAZ, ADET donulur ve alan adi `adet`tir. Toplam sikayet
    sayisina bolmek de oran uretmez - o yalnizca "sikayet edenler
    icindeki pay"dir, musteri tabanina oran degildir.
    """
    sayim: dict[str, int] = {}
    for s in sikayetler:
        anahtar = s.tema or "SINIFLANDIRILAMADI"
        sayim[anahtar] = sayim.get(anahtar, 0) + 1

    return {
        "olcu": "gozlenen_yogunluk",
        "aciklama": (
            "Adetlerdir, oran DEGILDIR - musteri/islem paydasi bilinmiyor."
        ),
        "toplam_sikayet": len(sikayetler),
        "temalar": dict(sorted(sayim.items(), key=lambda x: -x[1])),
    }

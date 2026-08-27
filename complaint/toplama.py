"""Sikayet toplama hatti: izin -> PII temizligi -> yineleme -> siniflandirma -> kayit.

SIRA BU MODULUN TAMAMIDIR. Adimlarin sirasi bir tercih degil, iki
kirmizi cizginin (Rehber_Zeynep_Veri.md) kodla uygulanmis halidir:

    1. IZIN     - izin kapisi gecilmeden hicbir sey islenmez
    2. PII      - temizlik KAYITTAN ONCE; ham metin fonksiyondan bile cikmaz
    3. YINELEME - ayni icerik ikinci kez ISLENMEZ degil, ISARETLENIR
    4. TEMA     - kural tabanli siniflandirma (+ kural setinin surumu)
    5. ESLESME  - kampanya baglantisi (hipotez, esik altinda uretilmez)
    6. KAYIT    - yalnizca temizlenmis surum, AYRI tabloya

--------------------------------------------------------------------------
HAM METIN NEDEN GERI DONDURULMUYOR
--------------------------------------------------------------------------
`hazirla()` ham metni ne doner ne loglar. Donerse cagiran taraf onu
yanlislikla saklayabilir ve "temizlik kayittan once" garantisi cagri
yerine baglanir - yani garanti olmaktan cikar. Tek cikis temizlenmis
metindir.

--------------------------------------------------------------------------
YINELEME/SPAM NEDEN "ENGELLEME" DEGIL "ISARETLEME"
--------------------------------------------------------------------------
Ayni musterinin ayni sikayeti iki kez yazmasi ile organize bir spam
kampanyasi ayni sey degildir - ikisini ayirt edecek veri (gercek
Sikayetvar akisi) henuz yok. Bu yuzden yineleme supheli bir kayit
SESSIZCE ATILMAZ: extraction/kampanya_eslestirme katmanlarindaki "esik
altinda uretme ama sessizce de kaybetme" ilkesinin ayni uygulamasi -
`yineleme_supheli=True` ile KAYDEDILIR, insan_kontrolu_gerekir gibi bir
inceleme bayragidir, karar degildir.

--------------------------------------------------------------------------
YINELEME ANAHTARI NEDEN NORMALIZE EDILIR
--------------------------------------------------------------------------
Ham karsilastirma (`==`) sonuna nokta konmus bir sikayeti konmamis
olandan FARKLI sayar - oysa ikisi ayni sikayettir. Bu yuzden anahtar,
kucuk harfe cevrilip (turkce_ascii_kucult - "İ"/"I" ayrimi dahil),
noktalama/fazla bosluk silinip CIKARILIR; hash bu normalize edilmis
metin uzerinden alinir (bkz. _dedup_anahtari).

BILINEN SINIR: cok kisa/genel sikayetler (ör. "param gitti") PII
maskelemesinden sonra farkli kisilerde ayni anahtara dusebilir - bu
yanlis pozitif riski bilerek kabul edilir, cunku sonuc ENGELLEME degil
ISARETLEMEDIR (insan karar verir).

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

import hashlib
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Sequence

from complaint.izin_kapisi import Izin, izni_zorunlu_kil
from complaint.kampanya_eslestirme import EslesmeSonucu, kampanya_esle
from complaint.pii_temizleme import temizle
from complaint.tema_siniflandirici import tema_siniflandir
from extraction.normalizer import turkce_ascii_kucult

# Anahtar cikariminda katlanmis metinden silinen her sey: noktalama,
# ozel karakter. \w Turkce harfleri de kapsar (re.UNICODE varsayilan).
_NOKTALAMA = re.compile(r"[^\w\s]", re.UNICODE)
_FAZLA_BOSLUK = re.compile(r"\s+")


def _dedup_anahtari(temiz_metin: str) -> str:
    """Yineleme kontrolu icin normalize edilmis icerik anahtari.

    Kucuk harfe cevir (Turkce diyakritik dahil) -> noktalamayi sil ->
    fazla boslugu katla -> hashle. Ham metin DEGIL, PII TEMIZLIGINDEN
    GECMIS `temiz_metin` uzerinden hesaplanir - bu fonksiyon hicbir
    zaman ham veriyi gormemeli (modulun genel ilkesiyle tutarli).
    """
    katlanmis = turkce_ascii_kucult(temiz_metin or "")
    noktalamasiz = _NOKTALAMA.sub(" ", katlanmis)
    normalize = _FAZLA_BOSLUK.sub(" ", noktalamasiz).strip()
    return hashlib.sha256(normalize.encode("utf-8")).hexdigest()


@dataclass
class HazirSikayet:
    """Kayda hazir sikayet. HAM METIN ICERMEZ."""

    temiz_metin: str
    pii_bulundu: bool
    insan_kontrolu_gerekir: bool
    icerik_hash: str
    yineleme_supheli: bool
    tema: str | None
    tema_kaniti: str | None
    tema_surumu: str | None
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
    bilinen_icerik_hashleri: Sequence[str] | None = None,
) -> HazirSikayet:
    """Tek bir sikayeti kayda hazirlar.

    izin_zorunlu=False YALNIZCA sentetik/test verisi icindir; gercek
    kaynaklarda kullanilmamalidir (bkz. modul docstring'i).

    `bilinen_icerik_hashleri`: cagiran tarafin (ör. toplu ingest isi)
    zaten gordugu/kaydettigi anahtarlar. Verilmezse yineleme kontrolu
    hicbir seyle KARSILASTIRAMAZ ve `yineleme_supheli` hep False doner -
    bu sessiz bir "temiz" iddiasi degildir, "kiyaslanacak veri verilmedi"
    demektir (cagiran taraf DB'den mevcut hash'leri sorgulayip gecmelidir).
    """
    if izin_zorunlu:
        izni_zorunlu_kil(kaynak, bugun=bugun)

    # PII, baska HICBIR islemden once. Sonraki her adim (yineleme, tema)
    # temizlenmis metin uzerinde calisir - ham metni hicbir alt katman
    # gormemeli.
    temizlenmis = temizle(ham_metin)

    anahtar = _dedup_anahtari(temizlenmis.metin)
    yineleme_supheli = anahtar in (bilinen_icerik_hashleri or ())

    tema_sonucu = tema_siniflandir(temizlenmis.metin)
    eslesen = tema_sonucu.get("eslesen_ifadeler") or []

    eslesme = kampanya_esle(
        temizlenmis.metin, kampanyalar, sikayet_tarihi=sikayet_tarihi
    )

    return HazirSikayet(
        temiz_metin=temizlenmis.metin,
        pii_bulundu=temizlenmis.pii_bulundu_mu,
        insan_kontrolu_gerekir=temizlenmis.insan_kontrolu_gerekir,
        icerik_hash=anahtar,
        yineleme_supheli=yineleme_supheli,
        tema=tema_sonucu.get("tema"),
        # Kanit, eslesen ifadelerin kendisidir - "neden bu temaya girdi?"
        # sorusu sayiyla degil METINLE cevaplanabilmeli.
        tema_kaniti=", ".join(eslesen)[:200] or None,
        tema_surumu=tema_sonucu.get("tema_surumu"),
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
        icerik_hash=hazir.icerik_hash,
        yineleme_supheli=hazir.yineleme_supheli,
        tema=hazir.tema,
        tema_kaniti=hazir.tema_kaniti,
        tema_surumu=hazir.tema_surumu,
        # Cozum sureci (acik/islemde/cozuldu) Faz 2'de, gercek destek
        # akisi baglaninca islenir - simdiden "acik" gibi bir deger
        # UYDURULMAZ; sutun bilerek None birakilir (bkz. api/models.py).
        cozum_durumu=None,
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


def yogunluk_ozeti(
    sikayetler: Sequence[HazirSikayet], izin_var: bool = False
) -> dict[str, Any]:
    """Tema bazli GOZLENEN YOGUNLUK.

    KIRMIZI CIZGI: "'Sikayet orani' deme. Musteri/islem paydasi yoksa
    oran degildir; 'gozlenen yogunluk' de." Bu yuzden burada yuzde
    HESAPLANMAZ, ADET donulur ve alan adi `adet`tir. Toplam sikayet
    sayisina bolmek de oran uretmez - o yalnizca "sikayet edenler
    icindeki pay"dir, musteri tabanina oran degildir.

    `kapsam_durumu`: `toplam_sikayet == 0` iken TEK BASINA "veri yok"
    demek yaniltici olabilir - iki farkli "yok" durumu vardir ve
    dashboard bunlari AYNI CUMLEYLE anlatmamali:
        izin_yok            - hicbir kaynak icin gecerli izin yoktur,
                               veri toplanmasi zaten baslamamistir
        izin_var_veri_yok   - en az bir kaynak icin izin var ama henuz
                               hic sikayet islenmemistir (izin sonrasi
                               akis bekleniyor)
        veri_var            - en az bir sikayet islenmis/kaydedilmistir
    `izin_var` parametresi cagiran tarafca saglanir (bkz.
    complaint/izin_kapisi.py::herhangi_bir_izin_var_mi) - bu fonksiyon
    izin dosyasina kendisi bakmaz, yalnizca ELINE VERILENI degerlendirir.
    """
    sayim: dict[str, int] = {}
    for s in sikayetler:
        anahtar = s.tema or "SINIFLANDIRILAMADI"
        sayim[anahtar] = sayim.get(anahtar, 0) + 1

    if sikayetler:
        kapsam_durumu = "veri_var"
    elif izin_var:
        kapsam_durumu = "izin_var_veri_yok"
    else:
        kapsam_durumu = "izin_yok"

    return {
        "olcu": "gozlenen_yogunluk",
        "aciklama": (
            "Adetlerdir, oran DEGILDIR - musteri/islem paydasi bilinmiyor."
        ),
        "kapsam_durumu": kapsam_durumu,
        "toplam_sikayet": len(sikayetler),
        "temalar": dict(sorted(sayim.items(), key=lambda x: -x[1])),
    }

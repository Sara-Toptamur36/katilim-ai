"""Sikayet <-> kampanya eslestirmesi ve BAG GUVENI (link confidence).

Sorulan soru: "Bu sikayet hangi kampanya hakkinda?" Cevap cogu zaman
KESIN DEGILDIR - musteri kampanya adini yazmaz, "gecen ay aldigim
karttan puan yatmadi" der. Bu modul o belirsizligi GIZLEMEZ, SAYIYA
DOKER.

--------------------------------------------------------------------------
TASARIM: ESLESME BIR HIPOTEZDIR
--------------------------------------------------------------------------
Dusuk guvenli bir eslesme URETILMEZ, None donulur (bkz. ASGARI_GUVEN).
Bunun sebebi extraction katmanindaki ilkeyle ayni: kaynakta olmayan bir
iddiayi uretmektense cekimser kalmak. Yanlis eslesmis bir sikayet,
masum bir kampanyayi "sikayet edilen kampanya" gibi gosterir - bu,
bos birakmaktan cok daha zararlidir.

Ayni sebeple api/models.py::Sikayet tablosunda kampanyalara FOREIGN KEY
YOKTUR: eslesme silinebilir/duzeltilebilir bir tahmindir, semanin
garantisi degil.

--------------------------------------------------------------------------
DORT SINYAL, ESIT AGIRLIK DEGIL
--------------------------------------------------------------------------
    banka        0.45  - en ayirt edici; yanlis banka = kesin yanlis eslesme
    kampanya adi 0.35  - ad gecerse cok guclu ama nadiren gecer
    odul birimi  0.20  - "worldpuan" gibi banka-ozel birimler daraltir

Zaman penceresinin PUANI YOKTUR - yalnizca eler (asagi bak).

Agirliklar UYDURULMUS degil, eleme gucune gore siralanmistir; yine de
kalibre edilmis olasilik DEGILDIR ve oyle sunulmamalidir. `gerekce`
alani hangi sinyalin katkida bulundugunu tek tek gosterir ki sayi tek
basina kalmasin.

--------------------------------------------------------------------------
ZAMAN PENCERESI: PUAN DEGIL, ELEME
--------------------------------------------------------------------------
Sikayet tarihi kampanyanin yururluk penceresinin DISINDAYSA eslesme
elenir - guveni dusurmekle kalmaz, sifirlanir. Henuz baslamamis ya da
coktan bitmis bir kampanya hakkinda sikayet edilemez. Tarih bilinmiyorsa
pencere kontrolu UYGULANMAZ (bilinmeyen, "disarida" demek degildir).

PENCERE ICINDE OLMAK PUAN KAZANDIRMAZ. Once 0.10'luk bir puan verilmisti;
gercek veriyle calistirinca hatali oldugu goruldu: yalnizca banka adi
gecen bir sikayet (0.40) + pencere puani (0.10) esigi asip eslesiyordu -
oysa ayni anda onlarca kampanya yururluktedir, "o tarihte aktifti"
HANGI kampanya oldugunu soylemez. Ayrica bu, modulun kendi
"pencere puan degil eleme" ilkesiyle celisiyordu.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Sequence

from extraction.normalizer import turkce_ascii_kucult

AGIRLIK_BANKA = 0.45
AGIRLIK_KAMPANYA_ADI = 0.35
AGIRLIK_ODUL_BIRIMI = 0.20

# Bu esigin altinda eslesme URETILMEZ. Yalnizca banka adinin gecmesi
# (0.45) tek basina yetmemeli: bir bankanin onlarca kampanyasi var ve
# hangisi oldugunu soylemek icin ikinci bir sinyal gerekir. Esik,
# banka agirligindan BUYUK secilmistir - bu iliski korunmalidir.
ASGARI_GUVEN = 0.50

# Kampanya bittikten sonra sikayet gelmesi NORMALDIR (odul gecikmesi,
# ekstre donemi). Pencereye tolerans eklenir; olculmus bir deger degil,
# bilincli bir varsayimdir ve boyle isaretlenir.
PENCERE_TOLERANSI_GUN = 60

# Kampanya adindaki ayirt edici olmayan kelimeler - eslesmeye sayilmaz,
# yoksa "Kampanyasi" kelimesi her kampanyayi her sikayete baglardi.
_ETKISIZ_KELIMELER = {
    "kampanya", "kampanyasi", "kampanyalari", "firsat", "firsati",
    "ozel", "yeni", "avantajli", "avantaj", "ile", "ve", "icin",
}


@dataclass
class EslesmeSonucu:
    kampanya_id: int | None
    guven: float
    gerekce: dict[str, Any] = field(default_factory=dict)

    @property
    def eslesti_mi(self) -> bool:
        return self.kampanya_id is not None


def _kelimeler(metin: str) -> set[str]:
    katlanmis = turkce_ascii_kucult(metin or "")
    return {
        k.strip(".,;:!?()")
        for k in katlanmis.split()
        if len(k) > 3 and k not in _ETKISIZ_KELIMELER
    }


def _pencere_icinde_mi(sikayet_tarihi: date | None, kampanya) -> bool | None:
    """True/False/None. None = "tarih bilinmiyor, kontrol uygulanamaz" -
    bu False ile KARISTIRILMAMALI (bilinmeyen, disarida demek degildir)."""
    if sikayet_tarihi is None:
        return None
    baslangic = getattr(kampanya, "kampanya_baslangic", None)
    bitis = getattr(kampanya, "kampanya_bitis", None)
    if baslangic is None and bitis is None:
        return None
    if baslangic and sikayet_tarihi < baslangic:
        return False
    if bitis and sikayet_tarihi > bitis + timedelta(days=PENCERE_TOLERANSI_GUN):
        return False
    return True


def _tek_kampanyayi_puanla(
    temiz_metin: str, kampanya, sikayet_tarihi: date | None
) -> tuple[float, dict[str, Any]]:
    metin_katlanmis = turkce_ascii_kucult(temiz_metin or "")
    metin_kelimeleri = _kelimeler(temiz_metin)
    gerekce: dict[str, Any] = {}
    puan = 0.0

    pencere = _pencere_icinde_mi(sikayet_tarihi, kampanya)
    if pencere is False:
        # ELEME - puan toplamaya hic baslanmaz.
        return 0.0, {"pencere_disi": True}

    banka = getattr(kampanya, "banka", None)
    if banka and turkce_ascii_kucult(banka) in metin_katlanmis:
        puan += AGIRLIK_BANKA
        gerekce["banka"] = banka

    ad = getattr(kampanya, "kampanya_adi", None)
    ad_kelimeleri = _kelimeler(ad or "")
    ortak = ad_kelimeleri & metin_kelimeleri
    if ortak:
        # Kismi ortusme kismi puan alir: adin yarisi gectiyse yarim puan.
        oran = len(ortak) / len(ad_kelimeleri)
        puan += AGIRLIK_KAMPANYA_ADI * oran
        gerekce["kampanya_adi_ortak_kelimeler"] = sorted(ortak)

    birim = getattr(kampanya, "odul_birimi", None)
    if birim and turkce_ascii_kucult(birim) in metin_katlanmis:
        puan += AGIRLIK_ODUL_BIRIMI
        gerekce["odul_birimi"] = birim

    # Pencere PUAN KAZANDIRMAZ - yalnizca yukarida eler. Gerekcede
    # gorunur kalir ki eslesmenin hangi zaman baglaminda kuruldugu
    # denetlenebilsin.
    gerekce["zaman_penceresi"] = "icinde" if pencere is True else "bilinmiyor"

    return round(min(puan, 1.0), 4), gerekce


def kampanya_esle(
    temiz_metin: str,
    kampanyalar: Sequence[Any],
    sikayet_tarihi: date | None = None,
    asgari_guven: float = ASGARI_GUVEN,
) -> EslesmeSonucu:
    """En iyi kampanyayi ve bag guvenini doner.

    Esigin altinda kalirsa `kampanya_id=None` doner ve gerekcede NEDEN
    eslesmedigi yazar - sessiz bir bosluk birakilmaz.
    """
    if not kampanyalar:
        return EslesmeSonucu(None, 0.0, {"sebep": "karsilastirilacak kampanya yok"})

    puanlar = [
        (kampanya, *_tek_kampanyayi_puanla(temiz_metin, kampanya, sikayet_tarihi))
        for kampanya in kampanyalar
    ]
    puanlar.sort(key=lambda p: p[1], reverse=True)
    en_iyi, en_iyi_puan, en_iyi_gerekce = puanlar[0]

    # BERABERLIK KONTROLU: iki kampanya ayni puani aldiysa hangisi
    # oldugunu SOYLEYEMEYIZ. Rastgele birini secmek, olmayan bir
    # kesinlik uretmek olurdu.
    if len(puanlar) > 1 and abs(puanlar[1][1] - en_iyi_puan) < 1e-9 and en_iyi_puan > 0:
        return EslesmeSonucu(
            None,
            en_iyi_puan,
            {
                "sebep": "birden fazla kampanya ayni guveni aldi, ayirt edilemedi",
                "aday_sayisi": sum(1 for p in puanlar if abs(p[1] - en_iyi_puan) < 1e-9),
                "guven": en_iyi_puan,
            },
        )

    if en_iyi_puan < asgari_guven:
        return EslesmeSonucu(
            None,
            en_iyi_puan,
            {
                "sebep": f"en yuksek guven {en_iyi_puan} < esik {asgari_guven}",
                "en_yakin_aday": getattr(en_iyi, "kampanya_adi", None),
                **en_iyi_gerekce,
            },
        )

    return EslesmeSonucu(getattr(en_iyi, "id", None), en_iyi_puan, en_iyi_gerekce)

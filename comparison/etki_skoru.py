"""Kampanya Etki Skoru - finansal bileşen.

NE CEVAPLIYOR: `/karsilastir` "hangisi daha ucuz?" sorusunu cevaplar.
Kullanicinin asil sordugu ise "bu kampanya IYI bir kampanya mi?" - yani
piyasaya gore nerede duruyor. Etki skoru bunu olcer.

NEDEN AGIRLIKLI FORMUL YOK: `0.4 x kar_payi + 0.3 x vade + ...` gibi bir
formul yazmak, agirliklari UYDURMAK demektir; juri hakli olarak "neden
0,4?" diye sorar ve cevabimiz olmaz. comparison/compare_engine.py'deki
`en_avantajli` de ayni gerekceyle formul kullanmaz:

    "Yeni bir agirlikli formul UYDURULMAZ: sartnamenin kendi Ornek
     Temsili Senaryo-2'sinde gosterdigi gibi eksen eksen kazanan
     belirlenir."

Bunun yerine EKSEN YUZDELIGI kullanilir: her eksende bu kampanya
karsilastirilabilir kumenin neresinde? Skor, bu yuzdeliklerin
ortalamasidir. Uydurulan bir sayi yok; her bilesen sayilabilir bir
gercek ("kar payinda ilk %10'da").

CEKIMSERLIK: Kume kucukse ya da olculebilir eksen azsa skor URETILMEZ.
Gerekcesi olculdu - altin veri setinde Tasit Finansmani turunde TEK bir
kayit var; rakibi olmayan bir kampanyaya "piyasada birinci" demek
anlamsizdir. Bu, "0 sikayet = 0 memnuniyet degildir" kuralinin finansal
taraftaki karsiligidir: veri yoksa sayi uretilmez.
"""

from typing import Any, Sequence

from api.schemas import CampaignRecord
from comparison.compare_engine import (
    AVANTAJLI_ALT_KRITERLER,
    BIRIM_BAGIMLI_EKSENLER,
    KRITERLER,
    odul_birimi_tekil_mi,
)

# Skorun eksenleri BILEREK sartnamenin Md. 5.7 ornek listesindeki 4 kriterle
# sinirli. `en_yuksek_tutar` (bonus kriter) skora KATILMAZ: yuksek limit
# kullaniciya daha ucuz bir urun sunmaz, yalnizca daha fazlasini
# kullanabilecegini soyler. Skora katmak, sartnamede olmayan bir agirlik
# eklemek olurdu.
SKOR_EKSENLERI = AVANTAJLI_ALT_KRITERLER

# Bu esiklerin altinda skor URETILMEZ (bkz. modul basligi - cekimserlik).
ASGARI_KUME = 3          # kendisi dahil en az 3 kampanya
ASGARI_EKSEN = 2         # en az 2 eksen olculebilmeli
ASGARI_EKSEN_KUME = 2    # bir eksende siralama icin en az 2 olculebilir deger


def _ayni_kayit_mi(a: CampaignRecord, b: CampaignRecord) -> bool:
    """Iki kaydin ayni olup olmadigi.

    DIKKAT: yalnizca `a.id == b.id` yazmak YANLIS - veritabanina henuz
    yazilmamis kayitlarda id `None`'dir ve `None == None` True doner, yani
    ilgisiz iki kayit "ayni" sayilir. Once nesne kimligine bakilir; id
    karsilastirmasi ancak ikisi de gercek bir id tasiyorsa yapilir.
    """
    if a is b:
        return True
    return a.id is not None and a.id == b.id


def karsilastirilabilir_kume(
    kayit: CampaignRecord,
    tum_kayitlar: Sequence[CampaignRecord],
) -> list[CampaignRecord]:
    """Bu kampanyanin gercek rakipleri: AYNI TURDEKI AKTIF kampanyalar.

    Farkli turleri karsilastirmak anlamsizdir - bir konut finansmanini
    kart kampanyasiyla siralamak, elmayla armudu siralamaktir.

    Kaydin KENDISI kumeye dahildir (yuzdelik icin gereklidir). Kayit
    aktif degilse bile eklenir: suresi dolmus bir kampanyayi goruntuleyen
    kullanici da "bu, bugunku tekliflere gore nerede duruyordu?" cevabini
    alabilmelidir.
    """
    tur = kayit.kampanya_turu.value
    kume = [
        k
        for k in tum_kayitlar
        if k.kampanya_turu.value == tur and k.durum.value == "ACTIVE"
    ]
    if not any(_ayni_kayit_mi(k, kayit) for k in kume):
        kume = [*kume, kayit]
    return kume


def eksen_yuzdeligi(
    kayit: CampaignRecord, kume: Sequence[CampaignRecord], eksen_adi: str
) -> dict[str, Any]:
    """Bu kayit, bu eksende kumenin neresinde? 0.0 (en kotu) - 1.0 (en iyi).

    Yontem - yuzdelik sira:
        (kendisinden kotu olan sayisi + 0.5 x esit olan diger sayisi)
        -------------------------------------------------------------
                     (olculebilir kayit sayisi - 1)

    Esitlikte 0.5 sayilmasi, iki esit kaydin ayni yuzdeligi almasini
    saglar - biri digerine haksizca ustun gosterilmez.

    Bos deger olan kayitlar hesaba HIC girmez; sifir SAYILMAZ. Bos alan
    "bu kampanyada masraf yok" degil "kaynakta belirtilmemis" demektir
    (bkz. README tasarim ilkesi 1).
    """
    tanim = KRITERLER[eksen_adi]
    kendi_deger = getattr(kayit, tanim.alan, None)

    sonuc: dict[str, Any] = {
        "eksen": eksen_adi,
        "aciklama": tanim.aciklama,
        "deger": kendi_deger,
        "yuzdelik": None,
        "olculebilir_kayit": 0,
        "durum": "olculdu",
    }

    if kendi_deger is None:
        sonuc["durum"] = "deger_yok"
        return sonuc

    # Birim bagimli eksende (odul) birimler karisiksa siralama yapilmaz -
    # 10.000 Mil ile 5.000 TL arasinda "daha yuksek" diye bir sey yoktur.
    if eksen_adi in BIRIM_BAGIMLI_EKSENLER:
        tekil, birimler = odul_birimi_tekil_mi(kume)
        if not tekil:
            sonuc["durum"] = "birim_karisik"
            sonuc["birimler"] = sorted(birimler)
            return sonuc
        sonuc["birim"] = kayit.odul_birimi

    degerler = [
        getattr(k, tanim.alan) for k in kume if getattr(k, tanim.alan, None) is not None
    ]
    sonuc["olculebilir_kayit"] = len(degerler)

    if len(degerler) < ASGARI_EKSEN_KUME:
        # Tek bir degerle siralama olmaz - kime gore "iyi"?
        sonuc["durum"] = "yetersiz_eksen_kume"
        return sonuc

    if tanim.daha_iyi == "dusuk":
        daha_kotu = sum(1 for d in degerler if d > kendi_deger)
    else:
        daha_kotu = sum(1 for d in degerler if d < kendi_deger)
    esit_diger = sum(1 for d in degerler if d == kendi_deger) - 1

    sonuc["yuzdelik"] = round(
        (daha_kotu + 0.5 * esit_diger) / (len(degerler) - 1), 4
    )
    return sonuc


def finansal_skor(
    kayit: CampaignRecord, tum_kayitlar: Sequence[CampaignRecord]
) -> dict[str, Any]:
    """Kampanyanin finansal etki skoru + eksen kirilimi.

    Skor TEK BASINA dondurulmez - `eksen_kirilimi` her zaman yanindadir.
    Tek bir sayiya bakip karar vermek, sayinin nereden geldigini
    gizlemek olur.
    """
    kume = karsilastirilabilir_kume(kayit, tum_kayitlar)
    kirilim = [eksen_yuzdeligi(kayit, kume, e) for e in SKOR_EKSENLERI]
    olculenler = [e for e in kirilim if e["yuzdelik"] is not None]

    temel: dict[str, Any] = {
        "skor": None,
        "eksen_kirilimi": kirilim,
        "kullanilan_eksen": len(olculenler),
        "karsilastirma_kumesi": len(kume),
        "kampanya_turu": kayit.kampanya_turu.value,
    }

    # NOT: Bu metinler DOGRUDAN kullaniciya gosteriliyor (dashboard
    # EtkiSkoruKarti), o yuzden duzgun Turkce yazilir - terminology/
    # sozluk.json'daki kullaniciya donuk degerlerle ayni kural. ASCII
    # katlama yalnizca kod yorumlari ve tanimlayicilar icindir.
    if len(kume) < ASGARI_KUME:
        return {
            **temel,
            "durum": "yetersiz_kume",
            "sebep": (
                f"Bu türde karşılaştırılabilir yalnızca {len(kume)} aktif kampanya var "
                f"(en az {ASGARI_KUME} gerekli). Rakibi olmayan bir kampanyaya "
                "\"piyasada önde\" denemez."
            ),
        }

    if len(olculenler) < ASGARI_EKSEN:
        return {
            **temel,
            "durum": "yetersiz_eksen",
            "sebep": (
                f"Yalnızca {len(olculenler)} eksen ölçülebildi "
                f"(en az {ASGARI_EKSEN} gerekli). Kalan eksenlerde ya değer "
                "kaynakta belirtilmemiş ya da karşılaştırılabilir değil."
            ),
        }

    return {
        **temel,
        "skor": round(sum(e["yuzdelik"] for e in olculenler) / len(olculenler), 4),
        "durum": "olculdu",
        "sebep": None,
    }


def etki_skoru(
    kayit: CampaignRecord, tum_kayitlar: Sequence[CampaignRecord]
) -> dict[str, Any]:
    """Etki skoru = finansal bilesen + musteri geri bildirim bileseni.

    MUSTERI BILESENI SU AN YOK ve bu bilincli olarak gorunur birakiliyor.
    Geri bildirim kaynagi henuz tanimli degil (bkz. yol haritasi - toplama
    ve anonimlestirme ayri bir is). Bos gecmek yerine "hesaplanamadi"
    demek, sistemin bilmedigini soylemesidir.

    SIFIR YAZILMAZ: geri bildirim yoklugu "musteriler memnun degil"
    anlamina gelmez. Bu, cikarim tarafindaki "bos alan sifir degildir"
    kuralinin ayni uygulamasidir.
    """
    finansal = finansal_skor(kayit, tum_kayitlar)

    geri_bildirim = {
        "skor": None,
        "durum": "veri_yok",
        "ornek_sayisi": 0,
        "sebep": (
            "Yeterli geri bildirim bulunamadığından müşteri geri bildirim "
            "göstergesi hesaplanamamıştır."
        ),
    }

    if finansal["durum"] == "olculdu":
        bilesik_durum = "kismi"
        aciklama = (
            "Yalnızca finansal bileşen hesaplandı; müşteri geri bildirimi henüz yok."
        )
    else:
        bilesik_durum = "hesaplanamadi"
        aciklama = finansal["sebep"]

    return {
        "kampanya_id": kayit.id,
        "banka": kayit.banka,
        "kampanya_adi": kayit.kampanya_adi,
        "finansal": finansal,
        "musteri_geri_bildirim": geri_bildirim,
        "durum": bilesik_durum,
        "aciklama": aciklama,
    }

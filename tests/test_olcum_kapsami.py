"""Dogruluk olcumunun KAPSAMINI kilitleyen testler (23 Agustos 2026).

Buradaki uc kural, ölçülen sayinin ne anlama geldigini belirliyor. Ucu de
sessizce bozulabilecek turden: bozulduklarinda hicbir istisna atmaz,
yalnizca metrik yanlislasir. Bu yuzden ayri ayri test edilirler.

  1. Imzasiz (taslak) kayitlar olcume GIRMEZ.
  2. hedef_kitle karsilastirmasi SEGMENT duzeyinde yapilir.
  3. "vade farksiz" ifadesi tek basina kar payi orani kaniti SAYILMAZ -
     ve gold bu kurala uyumlu kalir.
"""

import json
import re
from pathlib import Path

from extraction.regex_extractor import hedef_kitle_segmenti

GOLD = Path(__file__).parent.parent / "gold_dataset" / "altin_veri_seti.json"
RE_VADE_FARKSIZ = re.compile(r"vade\s*farks[ıi]z", re.IGNORECASE)
RE_ACIK_SIFIR = re.compile(r"k[aâ]r\s*pays[ıi]z|\b0\s*k[aâ]r\s*pay", re.IGNORECASE)


def _gold():
    return json.loads(GOLD.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. Imza filtresi
# ---------------------------------------------------------------------------


def test_imzasiz_kayitlar_olcume_girmez():
    """Olcum yalnizca `giren_kisi` dolu kayitlari sayar.

    NEDEN: etiketleme kuyrugundan acilan taslaklarda bir okuyucu aday
    deger yazmis olabilir ama kimse IMZALAMAMISTIR. Depoda kural buydu
    (tests/test_altin_veri_butunlugu.py "IMZALI kayit" sayar) ama
    dogruluk olcumu filtreyi uygulamiyordu: butunluk testi 107 kayit
    sayarken olcum 293 kayit uzerinden kosuyordu. "Kac kayit uzerinde
    olctunuz?" sorusunun tek bir cevabi olmali.

    GERCEK VERIYE BAGLI DEGIL: burada once `len(imzali) < len(gold)` on
    kosulu vardi ve "veri setinde imzasiz kayit VARDIR" varsayiyordu. 24
    Agustos'ta kuyruktaki 200 taslagin tamami imzalanip set %100 imzali
    hale gelince test kirildi - oysa kural hala geceriydi, yalnizca
    ornegi kalmamisti. Filtre artik SENTETIK bir imzasiz kayitla
    dogrulanir; kural, gercek verinin o anki halinden bagimsiz olarak
    test edilir.
    """
    import json as _json
    import tempfile
    from pathlib import Path as _Path

    from scraper.scripts import extraction_accuracy as olcum

    gold = _gold()
    imzali = [k for k in gold if (k.get("giren_kisi") or "").strip()]

    # 1. Gercek veri uzerindeki degismez: olculen kayit sayisi imzali
    #    kayit sayisini asamaz.
    taban = olcum.extraction_accuracy_hesapla()
    assert taban["canli_kayit_sayisi"] <= len(imzali), (
        f"Olcum {taban['canli_kayit_sayisi']} kayit saydi ama yalnizca "
        f"{len(imzali)} imzali kayit var - imza filtresi devre disi kalmis."
    )

    # 2. Filtrenin kendisi: TUM imzalar kaldirildiginda olcum hicbir
    #    kayit saymamali.
    #
    #    Neden "yeni bir imzasiz kayit ekle" degil: denendi ve test
    #    BOSUNA geciyordu. Eklenen sentetik kayit, kaynak metni
    #    bulunamadigi icin zaten olcume girmiyordu; imzasi olsa da
    #    olmasa da sayi degismiyordu, yani filtre hic sinanmiyordu.
    #    Mevcut kayitlarin imzasini kaldirmak bu tuzagi kapatir: taban
    #    olcumde sayilan kayitlarin AYNISI, yalnizca imzasiz halleriyle
    #    olculur.
    if taban["canli_kayit_sayisi"] == 0:
        return  # olculebilir kayit yok, filtre denenemez

    imzasiz_gold = [dict(k, giren_kisi="") for k in gold]

    with tempfile.TemporaryDirectory() as gecici:
        sahte_gold = _Path(gecici) / "gold.json"
        sahte_gold.write_text(
            _json.dumps(imzasiz_gold, ensure_ascii=False), encoding="utf-8"
        )
        gercek_yol = olcum.GOLD
        try:
            olcum.GOLD = sahte_gold
            imzasiz_sonuc = olcum.extraction_accuracy_hesapla()
        finally:
            olcum.GOLD = gercek_yol

    assert imzasiz_sonuc["canli_kayit_sayisi"] == 0, (
        f"Butun imzalar kaldirildigi halde olcum "
        f"{imzasiz_sonuc['canli_kayit_sayisi']} kayit saydi "
        "- imza filtresi devre disi."
    )


# ---------------------------------------------------------------------------
# 2. hedef_kitle segment karsilastirmasi
# ---------------------------------------------------------------------------


def test_hedef_kitle_serbest_metin_segmente_indirgenir():
    """Altin verideki serbest metin, Sartname Md. 5.3 segmentine cevrilir.

    Gold bu alani serbest metin doldurmus (299 kayitta 177 tekil deger),
    motor ise kategori uretiyor. Tam dize karsilastirmasi bu iki gosterim
    arasinda MATEMATIKSEL OLARAK imkansizdi - alan 287 destekle F1 %0,00
    veriyordu. Sartname alani zaten kategori olarak tanimliyor.
    """
    assert hedef_kitle_segmenti(
        "Ziraat Katilim Bankkart kredi karti sahipleri (ticari kartlar haric)"
    ) == "Belirli segment"
    assert hedef_kitle_segmenti("Yeni ev sahibi olmak isteyenler") == "Yeni müşteri"
    assert hedef_kitle_segmenti("Maas musterilerine ozel") == "Maaş müşterisi"
    assert hedef_kitle_segmenti("Mevcut musterilere ozel") == "Mevcut müşteri"


def test_hedef_kitle_kanit_yoksa_bos_doner():
    """"Belirli segment" bir catch-all DEGIL - kanit ister.

    Her kayda varsayilan olarak yazilsaydi olcum bedava yukselirdi ve
    alan hicbir bilgi tasimazdi. Hedef kitle ipucu icermeyen bir metin
    None dondurmeli.
    """
    assert hedef_kitle_segmenti("Aylik kar payi orani %1,89 ile 120 ay vade") is None
    assert hedef_kitle_segmenti("Konut finansmani firsati sunulmaktadir") is None
    assert hedef_kitle_segmenti(None) is None
    assert hedef_kitle_segmenti("") is None


def test_olcum_ve_motor_ayni_segment_kuralini_kullanir():
    """Olcum tarafi kendi kopyasini tutmaz - ayni fonksiyonu cagirir.

    Iki yerde iki kural olsaydi zamanla ayrisir ve olcum, motorun
    basarisini degil iki kural arasindaki farki olcerdi.
    """
    from scraper.scripts.extraction_accuracy import ALAN_NORMALIZE

    assert ALAN_NORMALIZE["hedef_kitle"] is hedef_kitle_segmenti


# ---------------------------------------------------------------------------
# 3. "vade farksiz" tek kural
# ---------------------------------------------------------------------------


def test_vade_farksiz_tek_basina_kar_payi_kaniti_sayilmaz():
    """Motor "vade farksiz" gorunce kar payi orani UYDURMAZ.

    "Vade farksiz 6 taksit" bir KART TAKSIT ifadesidir, finansman kar
    payi orani degildir. Gercekten sifir kar payli kampanyalar bunu
    acikca yaziyor ("kar paysiz", "0 kar payli") ve o kurallar korunuyor.

    Uydurma sifir yalnizca yanlis degil, AKTIF OLARAK ZARARLIYDI:
    comparison/compare_engine.py "en dusuk kar payi" kriterini ASC
    siraladigi icin bir kart kampanyasinin uydurma 0'i, gercek konut
    finansmaninin %1,87'sini her karsilastirmada yeniyordu.
    """
    from extraction.regex_extractor import kaydi_cikar

    metin = "Saglik harcamalarinza vade farksiz 6 taksit imkani!"
    assert kaydi_cikar(metin)["kar_payi_orani_percent"] is None

    # Acik sifir ifadeleri KORUNUYOR - gercek sifirlar kaybolmamali
    assert kaydi_cikar("Kar paysiz finansman firsati")["kar_payi_orani_percent"] == 0.0
    assert kaydi_cikar("0 kar payli 12 ay vade")["kar_payi_orani_percent"] == 0.0


def test_gold_vade_farksiz_kuralina_uyumlu():
    """Gold'da "vade farksiz" tek kaniti olan kayit kar payi 0 TASIMAZ.

    Bu kural bir kez ihlal edildiginde metrik sessizce cokuyor: iki ayri
    commit ZIT yonde karar verdiginde (gold'a 0 yazildi, motordan kural
    kaldirildi) kar_payi_orani recall'u %90,91'den %15,38'e dustu ve
    kimse fark etmedi. Bu test o kombinasyonu bir daha mumkun kilmaz.
    """
    from scraper.scripts.gold_eslesme import scraper_kaydini_bul

    ihlaller = []
    for kayit in _gold():
        if kayit.get("kar_payi_orani") != 0:
            continue
        ham = scraper_kaydini_bul(kayit)
        if ham is None:
            continue
        metin = ham.get("ham_metin") or ""
        if RE_ACIK_SIFIR.search(metin):
            continue  # acikca "kar paysiz" diyor - dogru etiket
        if RE_VADE_FARKSIZ.search(metin):
            ihlaller.append(kayit["kayit_id"])

    assert not ihlaller, (
        "Bu kayitlarda kar_payi_orani = 0 ama tek kanit 'vade farksiz': "
        f"{sorted(ihlaller)}. Duzeltmek icin: "
        "python -m gold_dataset.vade_farksiz_duzelt --yaz && "
        "python gold_dataset/excel_to_json.py"
    )

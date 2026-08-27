"""Sikayet BORU HATTININ TAMAMINI sentetik veri seti uzerinde olcer.

NEDEN AYRI BIR DOSYA: tests/test_sentetik_musteri_sesi.py yalnizca
`tema_siniflandir()` cagiriyor - yani complaint/toplama.py::hazirla
hattinin 6 adimindan SADECE 4.'sunu (tema) olcuyordu. v1.0 setinde
olculen bosluk sudur (27 Agustos 2026'da sayildi):

    22 ornegin  0'inda PII vardi
    22 ornegin  0'i insan_kontrolu_gerekir tetikliyordu
    22 icerik_hash'in 22'si tekildi - yineleme hic calismiyordu

Bu dosya veri setinin v1.1 gruplarini kullanarak 2. (PII) ve 3.
(yineleme) adimlari da olcer. Hat `izin_zorunlu=False` ile kosulur -
bu bayrak complaint/toplama.py docstring'inde tam olarak bunun icin
tanimlidir ("Sentetik ornekler uzerinde calistirmak icin").

--------------------------------------------------------------------------
VERITABANINA YAZILMAZ
--------------------------------------------------------------------------
`kaydet()` bu dosyada HIC cagrilmaz ve `sikayetler` tablosuna hicbir sey
yazilmaz. Veri setinin kendi `_aciklama` alani bunu sart kosuyor:
"icerigi veritabanina, altin veri setine ve RAG indeksine ASLA girmez".
Sentetik satir yazsaydik GET /musteri-sesi/yogunluk-ozeti bugunku dogru
`kapsam_durumu: "izin_yok"` cevabindan `"veri_var"`a doner ve juriye
gercek olmayan bir sikayet yogunlugu gosterirdik.

--------------------------------------------------------------------------
NEDEN HER OLCUM IKI YONLU
--------------------------------------------------------------------------
docs/kapsam_ve_veri_ayrimi.md'deki ayni ilke: yalnizca hassasiyet
olculseydi "her rakam dizisini sil" diyen bir kontrol %100 alirdi;
yalnizca ozgulluk olculseydi "hicbir seyi silme" diyen bir kontrol %100
alirdi. Ikisi birlikte anlamlidir.
"""

import json
from pathlib import Path

import pytest

from complaint.izin_kapisi import IzinYok
from complaint.kampanya_eslestirme import kampanya_esle
from complaint.pii_temizleme import temizle
from complaint.toplama import hazirla

VERI_YOLU = (
    Path(__file__).parent / "veri" / "kapsam_disi" / "sentetik_musteri_sesi.json"
)

# Bu setin kaynak adi. GERCEK bir platform adi DEGILDIR - izin kapisinda
# kayitli bir kaynaga karsilik gelmez (bkz. test_sentetik_kaynak_icin_izin_yok).
KAYNAK = "sentetik_musteri_sesi"


def _veri() -> dict:
    with open(VERI_YOLU, encoding="utf-8") as f:
        return json.load(f)


VERI = _veri()
GECERLI_TEMALAR = {t["kod"] for t in VERI["temalar"]}
PII_ORNEKLERI = VERI["pii_ornekleri"]
PII_KARSI_ORNEKLERI = VERI["pii_karsi_ornekleri"]
YINELEME_CIFTLERI = VERI["yineleme_ciftleri"]
YINELEME_KARSI_CIFTLERI = VERI["yineleme_karsi_ciftleri"]
BILINEN_SINIRLAMALAR = VERI["bilinen_sinirlamalar"]

# v1.2 (27 Agustos 2026) - severity/resolution/spam katmanlari
ONEM_ORNEKLERI = VERI["onem_ornekleri"]
COZUM_ORNEKLERI = VERI["cozum_ornekleri"]
DUSUK_BILGI_ORNEKLERI = VERI["dusuk_bilgi_ornekleri"]
DUSUK_BILGI_KARSI_ORNEKLERI = VERI["dusuk_bilgi_karsi_ornekleri"]


def _hazirla(metin: str, **kw):
    """Hattin tamami - izin kapisi disinda (sentetik veri, bkz. modul basligi)."""
    return hazirla(metin, kaynak=KAYNAK, izin_zorunlu=False, **kw)


# ==========================================================================
# 0. VERI SETININ KENDI TUTARLILIGI
# ==========================================================================


def test_veri_seti_surumu_guncel():
    """Surum etiketi ile icerik birlikte ilerlemeli - gruplar eklendi ama
    surum eskide kalsaydi, hangi setle olculdugu belirsizlesirdi."""
    assert VERI["_surum"].startswith("1.4")
    assert len(VERI["_surum_gecmisi"]) == 5


def test_kimlikler_tekil():
    """Ayni id iki kayitta olsaydi, basarisiz bir olcum hangi kayda ait
    oldugu anlasilamazdi."""
    tum_idler = [
        k["id"]
        for grup in (
            VERI["ornekler"], VERI["alan_disi_ornekler"], PII_ORNEKLERI,
            PII_KARSI_ORNEKLERI, YINELEME_CIFTLERI, YINELEME_KARSI_CIFTLERI,
            BILINEN_SINIRLAMALAR,
        )
        for k in grup
    ]
    assert len(tum_idler) == len(set(tum_idler)), "tekrar eden id var"


@pytest.mark.parametrize(
    "kayit", PII_ORNEKLERI + PII_KARSI_ORNEKLERI, ids=lambda k: k["id"]
)
def test_pii_kayitlarinin_beklenen_temasi_gecerli(kayit):
    assert kayit["beklenen_tema"] in GECERLI_TEMALAR


# ==========================================================================
# 1. IZIN KAPISI - sentetik kaynak icin de KAPALI
# ==========================================================================


def test_sentetik_kaynak_icin_izin_yok():
    """Bu set icin de izin kaydi YOKTUR ve olusturulmamistir.

    `izin_zorunlu=False` bir KAPI DEGIL, sentetik veri icin tanimli bir
    olcum yoludur; bayrak verilmediginde kapi normal calisir. Bu test,
    olcumu acmak ugruna izin dosyasi olusturulmadiginin kanitidir.
    """
    with pytest.raises(IzinYok):
        hazirla("odul yatmadi", kaynak=KAYNAK)


# ==========================================================================
# 2. PII - HASSASIYET (maskelenmesi gereken maskelendi mi)
# ==========================================================================


@pytest.mark.parametrize("kayit", PII_ORNEKLERI, ids=lambda k: k["id"])
def test_pii_beklenen_maskeler_uretilir(kayit):
    sonuc = temizle(kayit["metin"])
    assert sonuc.bulunanlar == kayit["beklenen_maskeler"], (
        f"{kayit['id']} - beklenen: {kayit['beklenen_maskeler']}, "
        f"bulunan: {sonuc.bulunanlar}, metin: {kayit['metin']!r}"
    )


@pytest.mark.parametrize("kayit", PII_ORNEKLERI, ids=lambda k: k["id"])
def test_pii_ham_deger_temiz_metinde_kalmaz(kayit):
    """Asil garanti: maskelenen degerin KENDISI cikti metninde gorunmemeli.

    `bulunanlar` sayacinin dolu olmasi tek basina yetmez - sayac dogru
    ama metin degismemis olsaydi, sayaci kontrol eden bir test yesil
    kalir, PII ise diske sizardi.
    """
    sonuc = temizle(kayit["metin"])
    for ham_deger in ("10000000146", "TR330006100519786457841326",
                      "4242 4242 4242 4242", "ornek.musteri@eposta.com"):
        if ham_deger in kayit["metin"]:
            assert ham_deger not in sonuc.metin, (
                f"{kayit['id']} - ham PII degeri temiz metinde KALDI: {ham_deger!r}"
            )


@pytest.mark.parametrize("kayit", PII_ORNEKLERI, ids=lambda k: k["id"])
def test_pii_bulunan_metin_insan_kontrolune_isaretlenir(kayit):
    assert temizle(kayit["metin"]).insan_kontrolu_gerekir is True


# ==========================================================================
# 3. PII - OZGULLUK (maskelenmemesi gereken rahat birakildi mi)
# ==========================================================================


@pytest.mark.parametrize("kayit", PII_KARSI_ORNEKLERI, ids=lambda k: k["id"])
def test_pii_karsi_ornek_hic_maskelenmez(kayit):
    """Musteri no, referans no, tutar ve tarih kisisel veri DEGILDIR.

    Silinselerdi sikayetin finansal icerigi kaybolur, tema siniflandirmasi
    ve kampanya eslesmesi dayanaksiz kalirdi.
    """
    sonuc = temizle(kayit["metin"])
    assert sonuc.bulunanlar == {}, (
        f"{kayit['id']} - YANLIS ALARM: {sonuc.bulunanlar}, metin: {kayit['metin']!r}"
    )
    assert sonuc.metin == kayit["metin"], f"{kayit['id']} - metin degistirilmis"
    assert sonuc.insan_kontrolu_gerekir is False


# ==========================================================================
# 4. MASKELEME TEMAYI BOZMUYOR
# ==========================================================================


@pytest.mark.parametrize(
    "kayit", PII_ORNEKLERI + PII_KARSI_ORNEKLERI, ids=lambda k: k["id"]
)
def test_maskeleme_sonrasi_tema_hala_dogru(kayit):
    """complaint/pii_temizleme.py::ETIKET'in tasarim gerekcesinin kaniti.

    Etiketler silinen seyin TURUNU koruyor ("[TELEFON]") cunku tema
    siniflandirmasi maskelemeden SONRAKI metin uzerinde calisiyor
    (bkz. toplama.py::hazirla sirasi). Bu test, PII temizliginin
    siniflandirmayi kor etmedigini gosterir.
    """
    hazir = _hazirla(kayit["metin"])
    assert hazir.tema == kayit["beklenen_tema"], (
        f"{kayit['id']} - maskeleme sonrasi tema kaydi: beklenen "
        f"{kayit['beklenen_tema']}, bulunan {hazir.tema}, "
        f"temiz metin: {hazir.temiz_metin!r}"
    )
    assert hazir.tema_kaniti, f"{kayit['id']} - tema atandi ama kanit bos"


@pytest.mark.parametrize("kayit", PII_ORNEKLERI, ids=lambda k: k["id"])
def test_hazirla_ham_metni_disari_vermez(kayit):
    """HazirSikayet ham metin ICERMEZ (toplama.py modul basligi).

    Alanlarin hicbirinde maskelenmemis PII bulunmamali - `temiz_metin`
    disinda bir alandan sizarsa garanti bosa cikardi.
    """
    hazir = _hazirla(kayit["metin"])
    tum_metin = " ".join(
        str(v) for v in (hazir.temiz_metin, hazir.tema_kaniti, hazir.kaynak)
    )
    for ham_deger in ("10000000146", "TR330006100519786457841326",
                      "4242 4242 4242 4242", "ornek.musteri@eposta.com"):
        if ham_deger in kayit["metin"]:
            assert ham_deger not in tum_metin


# ==========================================================================
# 5. YINELEME
# ==========================================================================


@pytest.mark.parametrize("cift", YINELEME_CIFTLERI, ids=lambda c: c["id"])
def test_yineleme_cifti_ayni_hash_uretir(cift):
    """Noktalama/harf/bosluk farki AYNI sikayeti farkli gostermemeli."""
    a = _hazirla(cift["metin_a"]).icerik_hash
    b = _hazirla(cift["metin_b"]).icerik_hash
    assert a == b, (
        f"{cift['id']} - ayni sayilmasi gereken iki metin farkli hash uretti: "
        f"{cift['metin_a']!r} / {cift['metin_b']!r}"
    )


@pytest.mark.parametrize("cift", YINELEME_KARSI_CIFTLERI, ids=lambda c: c["id"])
def test_yineleme_karsi_cifti_farkli_hash_uretir(cift):
    """OZGULLUK: normalizasyon fazla agresif olsaydi farkli sikayetler
    ayni sayilir ve gercek bir sikayet "yineleme" diye isaretlenirdi."""
    a = _hazirla(cift["metin_a"]).icerik_hash
    b = _hazirla(cift["metin_b"]).icerik_hash
    assert a != b, (
        f"{cift['id']} - farkli olmasi gereken iki metin CAKISTI: "
        f"{cift['metin_a']!r} / {cift['metin_b']!r}"
    )


@pytest.mark.parametrize("cift", YINELEME_CIFTLERI, ids=lambda c: c["id"])
def test_yineleme_supheli_isaretlenir_ama_kayit_durur(cift):
    """KIRMIZI CIZGI: yineleme supheli kayit SILINMEZ, ISARETLENIR.

    Ikinci kayit yine tam bir HazirSikayet olarak doner - temasi, kaniti
    ve temiz metni yerindedir; yalnizca insan incelemesine bayraklanir.
    """
    ilk = _hazirla(cift["metin_a"])
    ikinci = _hazirla(cift["metin_b"], bilinen_icerik_hashleri=[ilk.icerik_hash])

    assert ilk.yineleme_supheli is False, f"{cift['id']} - ilk kayit supheli sayildi"
    assert ikinci.yineleme_supheli is True, f"{cift['id']} - yineleme yakalanmadi"
    assert ikinci.temiz_metin, f"{cift['id']} - yineleme kaydi SESSIZCE DUSURULMUS"


def test_bilinen_hash_verilmezse_sessiz_temiz_iddiasi_yok():
    """`bilinen_icerik_hashleri` verilmediginde False donmesi "yineleme
    yok" DEMEK DEGILDIR - "kiyaslanacak veri verilmedi" demektir
    (toplama.py::hazirla docstring'i). Bu ayrimi test kilitler."""
    cift = YINELEME_CIFTLERI[0]
    ilk = _hazirla(cift["metin_a"])
    ikinci_kiyassiz = _hazirla(cift["metin_b"])

    assert ikinci_kiyassiz.yineleme_supheli is False
    assert ikinci_kiyassiz.icerik_hash == ilk.icerik_hash  # hash AYNI, bayrak False


# ==========================================================================
# 6. BILINEN SINIRLAMALAR - dondurulmus kararlar
# ==========================================================================


def test_bilinen_sinirlama_kisi_adi_isaretlenmiyor():
    """SM-BS1: kisi adi iceren metin SESSIZCE "temiz" sayiliyor.

    Bu test YESIL kaldiginda "sorun yok" demek DEGILDIR - "bilinen
    sinirlama hala ayni yerde" demektir. Biri `insan_kontrolu_gerekir`
    mantigini duzeltirse bu test KIRILIR ve karar yeniden tartisilir.
    """
    kayit = next(s for s in BILINEN_SINIRLAMALAR if s["id"] == "SM-BS1")
    sonuc = temizle(kayit["metin"])

    assert sonuc.bulunanlar == kayit["gozlenen_davranis"]["bulunanlar"]
    assert (
        sonuc.insan_kontrolu_gerekir
        == kayit["gozlenen_davranis"]["insan_kontrolu_gerekir"]
    )
    # Ad metinde AYNEN duruyor - maskelenmedigi acikca gosteriliyor.
    assert "Ayse" in sonuc.metin


def test_bilinen_sinirlama_maskeleme_boslugu_yutuyor():
    """SM-BS2: kozmetik sinir - maske komsu boslugu tuketiyor."""
    kayit = next(s for s in BILINEN_SINIRLAMALAR if s["id"] == "SM-BS2")
    sonuc = temizle(kayit["metin"])
    assert sonuc.metin == kayit["gozlenen_davranis"]["temiz_metin"]
    # Ama tema YINE DE dogru atanir - sinirin kozmetik oldugunun kaniti.
    assert _hazirla(kayit["metin"]).tema == "REWARD_NOT_CREDITED"


# ==========================================================================
# 7. SIZINTI GUARDI - yeni gruplar da urun verisine karismamali
# ==========================================================================


def test_v11_ornekleri_urun_verisine_sizmamis():
    """tests/test_sentetik_musteri_sesi.py'deki AYNI desen, v1.1 gruplari icin.

    Ozellikle onemli: bu gruplar TCKN/IBAN/kart desenli degerler iceriyor.
    Uydurma olsalar bile urun verisinde gorunmeleri, veri ayriminin
    bozuldugunun isareti olurdu.
    """
    kok = Path(__file__).resolve().parent.parent
    aranacak_dizinler = [kok / "scraper" / "raw_data", kok / "gold_dataset"]

    imzalar = [
        k["metin"] for k in PII_ORNEKLERI + PII_KARSI_ORNEKLERI
        if len(k["metin"]) > 40
    ]
    assert imzalar, "Sizinti guardi icin yeterince uzun ifade bulunamadi"

    for dizin in aranacak_dizinler:
        if not dizin.exists():
            continue
        for dosya in dizin.rglob("*.json"):
            icerik = dosya.read_text(encoding="utf-8", errors="ignore")
            for imza in imzalar:
                assert imza not in icerik, (
                    f"Sentetik v1.1 ornegi urun verisine sizmis: {dosya}"
                )


# ==========================================================================
# 8. OLCUM OZETI - juri/mentor icin tek bakista skor
# ==========================================================================


def test_olcum_ozeti_raporlanabilir(capsys):
    pii_dogru = sum(
        1 for k in PII_ORNEKLERI
        if temizle(k["metin"]).bulunanlar == k["beklenen_maskeler"]
    )
    ozgulluk_dogru = sum(
        1 for k in PII_KARSI_ORNEKLERI if temizle(k["metin"]).bulunanlar == {}
    )
    yineleme_dogru = sum(
        1 for c in YINELEME_CIFTLERI
        if _hazirla(c["metin_a"]).icerik_hash == _hazirla(c["metin_b"]).icerik_hash
    )
    yineleme_ozgulluk = sum(
        1 for c in YINELEME_KARSI_CIFTLERI
        if _hazirla(c["metin_a"]).icerik_hash != _hazirla(c["metin_b"]).icerik_hash
    )
    tema_korundu = sum(
        1 for k in PII_ORNEKLERI + PII_KARSI_ORNEKLERI
        if _hazirla(k["metin"]).tema == k["beklenen_tema"]
    )

    with capsys.disabled():
        print(
            f"\n  Sikayet hatti (sentetik v{VERI['_surum'].split()[0]}):\n"
            f"    PII hassasiyet        {pii_dogru}/{len(PII_ORNEKLERI)}\n"
            f"    PII ozgulluk          {ozgulluk_dogru}/{len(PII_KARSI_ORNEKLERI)}\n"
            f"    Yineleme yakalama     {yineleme_dogru}/{len(YINELEME_CIFTLERI)}\n"
            f"    Yineleme ozgulluk     {yineleme_ozgulluk}/{len(YINELEME_KARSI_CIFTLERI)}\n"
            f"    Maskeleme sonrasi tema {tema_korundu}/"
            f"{len(PII_ORNEKLERI) + len(PII_KARSI_ORNEKLERI)}\n"
            f"    Bilinen sinirlama     {len(BILINEN_SINIRLAMALAR)} (dondurulmus)"
        )

    assert pii_dogru == len(PII_ORNEKLERI)
    assert ozgulluk_dogru == len(PII_KARSI_ORNEKLERI)
    assert yineleme_dogru == len(YINELEME_CIFTLERI)
    assert yineleme_ozgulluk == len(YINELEME_KARSI_CIFTLERI)
    assert tema_korundu == len(PII_ORNEKLERI) + len(PII_KARSI_ORNEKLERI)


# ==========================================================================
# 9. ONEM DERECESI (severity) - v1.2, 27 Agustos 2026
# ==========================================================================


@pytest.mark.parametrize("kayit", ONEM_ORNEKLERI, ids=lambda k: k["id"])
def test_onem_derecesi_beklendigi_gibi(kayit):
    hazir = _hazirla(kayit["metin"])
    assert hazir.onem_derecesi == kayit["beklenen_onem_derecesi"], (
        f"{kayit['id']} - beklenen {kayit['beklenen_onem_derecesi']}, "
        f"bulunan {hazir.onem_derecesi}, gerekce: {hazir.onem_gerekce}"
    )
    assert hazir.onem_gerekce, f"{kayit['id']} - onem derecesi kanitsiz uretildi"


def test_onem_derecesi_varsayilan_orta_asiri_iddia_degil():
    """Kirmizi cizgi: kanit yoksa en YUKSEK ya da en DUSUK degil, ORTA
    ('ayirt edici sinyal yok') uretilir - tema_siniflandirici.py ve
    kampanya_eslestirme.py'deki AYNI cekimserlik ilkesi."""
    from complaint.onem_derecesi import ORTA

    varsayilan = next(
        k for k in ONEM_ORNEKLERI if k["beklenen_onem_derecesi"] == "ORTA"
    )
    assert _hazirla(varsayilan["metin"]).onem_gerekce["sebep"] == (
        "yuksek_veya_dusuk_sinyal_gorulmedi_varsayilan"
    )
    assert varsayilan["beklenen_onem_derecesi"] == ORTA


# ==========================================================================
# 10. COZUM DURUMU (resolution) - v1.2
# ==========================================================================


@pytest.mark.parametrize("kayit", COZUM_ORNEKLERI, ids=lambda k: k["id"])
def test_cozum_durumu_beklendigi_gibi(kayit):
    hazir = _hazirla(kayit["metin"])
    assert hazir.cozum_durumu == kayit["beklenen_cozum_durumu"], (
        f"{kayit['id']} - beklenen {kayit['beklenen_cozum_durumu']}, "
        f"bulunan {hazir.cozum_durumu}, gerekce: {hazir.cozum_gerekce}"
    )


def test_cozum_durumu_varsayilan_bilinmiyor_cozulmedi_degil():
    """Kirmizi cizgi: cozum sinyali yoksa 'cozulmedi' bir IDDIA olurdu -
    metin cozum surecinin nerede oldugunu soylemiyorsa dogru cevap
    'bilinmiyor'dur, en olumsuz varsayim degil."""
    from complaint.cozum_tespiti import BILINMIYOR

    varsayilan = next(
        k for k in COZUM_ORNEKLERI if k["beklenen_cozum_durumu"] == "bilinmiyor"
    )
    assert varsayilan["beklenen_cozum_durumu"] == BILINMIYOR
    # v1.0/v1.1'deki 20+9+4 orneginin BUYUK COGUNLUGU da ayni sekilde
    # cozum sinyali icermiyor - yani 'bilinmiyor' istisna degil, kuraldir.
    # Bilinen 2 istisna (SM-019, SM-P05) ACIKCA "cozulmedi" ifadesi tasir -
    # bunlar YANLIS ALARM degil, dogru tespittir (metinde kelimesi kelimesine
    # gecer), o yuzden isimleriyle DISLANIR.
    ISTISNA_ID = {"SM-019", "SM-P05"}
    tum_diger = [
        (o["id"], o["metin"]) for o in VERI["ornekler"]
    ] + [
        (k["id"], k["metin"]) for k in PII_ORNEKLERI + PII_KARSI_ORNEKLERI
    ]
    for kid, metin in tum_diger:
        cozum = _hazirla(metin).cozum_durumu
        if kid in ISTISNA_ID:
            assert cozum == "cozulmedi", f"{kid} - artik 'cozulmedi' icermiyor, istisna listesi guncel degil"
        else:
            assert cozum == "bilinmiyor", f"{kid} - beklenmedik cozum sinyali: {cozum} ({metin!r})"


# ==========================================================================
# 11. DUSUK BILGI / SPAM ISARETI - v1.2
# ==========================================================================


@pytest.mark.parametrize("kayit", DUSUK_BILGI_ORNEKLERI, ids=lambda k: k["id"])
def test_dusuk_bilgi_supheli_yakalanir(kayit):
    hazir = _hazirla(kayit["metin"])
    assert hazir.dusuk_bilgi_supheli is True, (
        f"{kayit['id']} - cok kisa metin isaretlenmedi: {kayit['metin']!r}"
    )
    # ENGELLEME degil ISARETLEME - kayit yine tam olarak uretilir.
    assert hazir.temiz_metin, f"{kayit['id']} - kayit SESSIZCE DUSURULMUS"


@pytest.mark.parametrize("kayit", DUSUK_BILGI_KARSI_ORNEKLERI, ids=lambda k: k["id"])
def test_dusuk_bilgi_ozgulluk_gercek_sikayet_isaretlenmez(kayit):
    """OZGULLUK: esikte veya uzerinde olan gercek icerikli kisa
    sikayetler YANLIS ALARM olarak isaretlenmemeli."""
    hazir = _hazirla(kayit["metin"])
    assert hazir.dusuk_bilgi_supheli is False, (
        f"{kayit['id']} - YANLIS ALARM: {kayit['metin']!r}"
    )


# ==========================================================================
# 12. UC SEVIYELI ENTITY RESOLUTION (BANK / PRODUCT / CAMPAIGN) - v1.2
# ==========================================================================
#
# Mentor geri bildirimi: "kampanya eslestirmeyi ZORUNLU degil OPSIYONEL
# yapmaniz dogru" + "Seviye 1 BANK cok yuksek guven, Seviye 2 PRODUCT
# orta/yuksek guven, Seviye 3 CAMPAIGN cogu zaman dusuk guven". Bu blok
# tam olarak bu senaryoyu sentetik bir kampanya nesnesiyle dogrular:
# banka ve urun turu bilinir, SPESIFIK kampanya adi hic gecmez.


class _SentetikKampanya:
    """Gercek api/models.py::Kampanya yerine test icin minimal nesne -
    kampanya_eslestirme.py yalnizca getattr ile alan okur, ORM'e bagli
    degildir (bkz. modul docstring'i: 'Sequence[Any]')."""

    def __init__(self, id, banka, kampanya_adi, kampanya_turu, odul_birimi=None):
        self.id = id
        self.banka = banka
        self.kampanya_adi = kampanya_adi
        self.kampanya_turu = kampanya_turu
        self.odul_birimi = odul_birimi
        self.kampanya_baslangic = None
        self.kampanya_bitis = None


ENTITY_RESOLUTION_ORNEKLERI = VERI["entity_resolution_ornekleri"]


def _kampanya_nesnesi(sozluk: dict) -> _SentetikKampanya:
    return _SentetikKampanya(**sozluk)


@pytest.mark.parametrize(
    "kayit", ENTITY_RESOLUTION_ORNEKLERI, ids=lambda k: k["id"]
)
def test_uc_seviyeli_entity_resolution_veri_setinden(kayit):
    """SM-ER1: musteri bankayi ve urun turunu belirtir ama SPESIFIK
    kampanya adini hic yazmaz (gercek musteri dilinde en yaygin durum) -
    Seviye 3 esigi asilmaz, Seviye 1/2 yine de taninir. SM-ER2 (kontrol
    grubu): kampanya adi da gecince Seviye 3 de esigi asar - uc seviyenin
    BIRBIRINI ENGELLEMEDIGINI, BAGIMSIZ olculdugunu gosterir."""
    sonuc = kampanya_esle(kayit["metin"], [_kampanya_nesnesi(kayit["kampanya"])])
    beklenen = kayit["beklenen"]

    assert sonuc.banka_eslesti == beklenen["banka_eslesti"], kayit["id"]
    assert (sonuc.urun_turu_guven > 0.0) == beklenen["urun_turu_guven_pozitif"], kayit["id"]
    assert (sonuc.kampanya_id is not None) == beklenen["kampanya_esti"], (
        f"{kayit['id']} - kampanya_id={sonuc.kampanya_id}, guven={sonuc.guven}"
    )


def test_urun_turu_bilinmeyen_kampanyada_seviye2_sifir_kalir():
    """OZGULLUK: kampanya_turu 'Belirlenemedi' ise Seviye 2 icin sahte
    bir guven UYDURULMAZ, 0.0 kalir."""
    belirsiz = _SentetikKampanya(
        id=202, banka="A Bankasi", kampanya_adi="Test Kampanyasi",
        kampanya_turu="Belirlenemedi",
    )
    sonuc = kampanya_esle("A Bankasi ile ilgili bir sorunum var", [belirsiz])
    assert sonuc.urun_turu_guven == 0.0


# ==========================================================================
# 13. v1.2 OLCUM OZETI
# ==========================================================================


def test_v12_olcum_ozeti_raporlanabilir(capsys):
    onem_dogru = sum(
        1 for k in ONEM_ORNEKLERI
        if _hazirla(k["metin"]).onem_derecesi == k["beklenen_onem_derecesi"]
    )
    cozum_dogru = sum(
        1 for k in COZUM_ORNEKLERI
        if _hazirla(k["metin"]).cozum_durumu == k["beklenen_cozum_durumu"]
    )
    dusuk_bilgi_yakalama = sum(
        1 for k in DUSUK_BILGI_ORNEKLERI if _hazirla(k["metin"]).dusuk_bilgi_supheli
    )
    dusuk_bilgi_ozgulluk = sum(
        1 for k in DUSUK_BILGI_KARSI_ORNEKLERI
        if not _hazirla(k["metin"]).dusuk_bilgi_supheli
    )

    with capsys.disabled():
        print(
            f"\n  Sikayet hatti (sentetik v1.2 - severity/resolution/spam):\n"
            f"    Onem derecesi          {onem_dogru}/{len(ONEM_ORNEKLERI)}\n"
            f"    Cozum durumu           {cozum_dogru}/{len(COZUM_ORNEKLERI)}\n"
            f"    Dusuk-bilgi yakalama   {dusuk_bilgi_yakalama}/{len(DUSUK_BILGI_ORNEKLERI)}\n"
            f"    Dusuk-bilgi ozgulluk   {dusuk_bilgi_ozgulluk}/{len(DUSUK_BILGI_KARSI_ORNEKLERI)}\n"
            f"    Entity resolution      3 seviye (banka/urun/kampanya) bagimsiz dogrulandi"
        )

    assert onem_dogru == len(ONEM_ORNEKLERI)
    assert cozum_dogru == len(COZUM_ORNEKLERI)
    assert dusuk_bilgi_yakalama == len(DUSUK_BILGI_ORNEKLERI)
    assert dusuk_bilgi_ozgulluk == len(DUSUK_BILGI_KARSI_ORNEKLERI)

"""Altin Veri Seti'ni Excel'den JSON'a cevirir.

NEDEN GEREKLI: Excel insanlarin doldurmasi icin kolay, ama testler ve
Extraction Accuracy hesabi JSON okur. Bu betik ikisi arasindaki koprudur.

KULLANIM:
    python gold_dataset/excel_to_json.py

Excel'i her guncelledikten sonra bunu calistir ve uretilen JSON'u commit'le.
CI, regresyon testlerinde bu JSON'u kullanir.

---------------------------------------------------------------------------
BOS HUCRE NE ZAMAN "KAYNAKTA YOK" SAYILIR (olcumun dogrulugu buna bagli)
---------------------------------------------------------------------------
Excel'in "1. Nasil Doldurulur" sayfasindaki kural nettir ve GECERLIDIR:
bilgi sayfada yoksa hucre BOS birakilir; '-', 'yok', '0' YAZILMAZ.

Ama bu kural yalnizca etiketleyicinin GERCEKTEN BAKTIGI sutunlar icin
anlamlidir. Sonradan eklenen bir sutunda tum hucreler dogal olarak bostur
ve bu "kaynakta yok" DEMEK DEGILDIR - sadece "henuz kimse bakmadi"
demektir. Ikisini karistirmak, hic etiketlenmemis bir sutunu "hepsi bos,
demek ki motor hic uydurmuyor" diye BEDAVA yuksek puana cevirirdi.

Bu yuzden bos hucrenin anlamini SUTUN belirler:

  * INCELENMIS_ALANLAR : bir etiketleme oturumunda tek tek gozden
    gecirilmis sutunlar. Bos hucre = "kaynakta belirtilmemis" ->
    `alan_belirtilmemis` bayragi konur, yanlis pozitif OLCULEBILIR.

  * Listede olmayan sutunlar : olcum disi. scraper/scripts/
    extraction_accuracy.py bunlarda yanlis pozitif saymaz.

BIR SUTUNUN ETIKETLEMESI BITINCE yapilacak tek is: sutun adini
INCELENMIS_ALANLAR'a eklemek. Etiketlemeyi hizlandirmak icin:
    python gold_dataset/etiketleme_yardimcisi.py
"""

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

import openpyxl

KLASOR = Path(__file__).parent
EXCEL = KLASOR / "altin_veri_seti.xlsx"
JSON_CIKTI = KLASOR / "altin_veri_seti.json"

SAYFA = "2. Altin Veri Seti"
VERI_BASLANGIC_SATIRI = 3  # 1: baslik, 2: aciklama

SAYISAL_ALANLAR = {
    "kar_payi_orani",
    "maliyet_orani",
    "vade_ay",
    "finansman_tutari",
    "odul_miktari",
    # Vade ile KARISTIRILMAMALI - ucu de ayri kavram (bkz.
    # extraction/regex_extractor.py: "12 aya varan taksit" vade DEGILDIR).
    "taksit_sayisi",
    "erteleme_suresi_ay",
}
TARIH_ALANLARI = {"kampanya_baslangic", "kampanya_bitis", "giris_tarihi"}

# --------------------------------------------------------------------------
# KANIT SPANI (evidence span)
# --------------------------------------------------------------------------
# Bir altin degerin yaninda, o degeri HAKLI CIKARAN kaynak cumlesi durur.
# Neden gerekli: bir deger tartismali oldugunda tek yol bankanin sayfasini
# yeniden acmaktir - sayfa degismisse (kampanya rotasyonu) gerekce tamamen
# kaybolur. Span, etiketleme anindaki kaniti DONDURUR.
#
# EXCEL BICIMI - hucreye satir basina bir eslesme yazilir:
#
#     odul_miktari: bir müşteri en fazla 2.000 TL Worldpuan kazanabilir
#     kampanya_bitis: Kampanya 1–31 Ağustos 2026 tarihlerinde geçerlidir
#
# Hucreye JSON yazdirmak insan icin iskence olurdu; bu bicim Excel'de
# okunabilir kalir ve ayristirmasi tek satirdir.
#
# Secilen cumle kaynak metinde BIREBIR gecmelidir - tests/
# test_altin_veri_butunlugu.py bunu her kosuda dogrular, yani elle
# "ozetlenmis" bir cumle sessizce gecemez.
SPAN_ALANI = "kanit_spanlari"

# Span verilebilecek alanlar. Yazim hatasi bir spani sessizce olcum
# disi birakirdi; taninmayan ad UYARI uretir.
SPAN_VERILEBILIR_ALANLAR = {
    "kar_payi_orani", "vade_ay", "finansman_tutari", "odul_miktari",
    "odul_birimi", "taksit_sayisi", "erteleme_suresi_ay",
    "masraf_durumu", "kampanya_bitis", "kampanya_baslangic", "hedef_kitle",
}


def span_metinde_var(span: str, metin: str) -> bool:
    """Kanit spani kaynak metinde geciyor mu?

    BOSLUK FARKI ICERIK FARKI DEGILDIR. Olculdu: ayni sayfa statik
    tarayiciyla duz bosluk, JS tarayicisiyla KIRILMAZ BOSLUK (U+00A0)
    ve farkli satir sonlariyla geliyor. Sayfalar JS ile yeniden
    tarandiginda YEDI kaydin kanit spani bir anda "kirik" gorundu -
    oysa cumleler harfi harfine ayniydi, yalnizca bosluklar degismisti.

    KURAL GEVSEMIYOR: karakter dizisi yine birebir eslesmek zorunda;
    yalnizca ardisik bosluklar tek boslugua indirilir. "Yaklasik
    dogru" elle yazilmis bir cumle hala GECMEZ - spanin butun degeri
    tam da budur.
    """
    from extraction.normalizer import turkce_ascii_kucult

    def sadelestir(metin_parcasi: str) -> str:
        katlanmis = turkce_ascii_kucult(metin_parcasi).replace("\xa0", " ")
        return re.sub(r"\s+", " ", katlanmis).strip()

    return bool(span) and sadelestir(span) in sadelestir(metin)


def _spanlari_ayristir(ham, kayit_id: str, uyarilar: list[str]) -> dict:
    """"alan: cumle" satirlarini sozluge cevirir.

    Bozuk satir SESSIZCE ATILMAZ - uyari uretir. Sessiz atma, etiketleyici
    span girdigini sanirken olcumun onu hic gormemesi demek olurdu.
    """
    if ham is None or not str(ham).strip():
        return {}

    spanlar: dict[str, str] = {}
    for satir in str(ham).splitlines():
        sade = satir.strip()
        if not sade:
            continue
        if ":" not in sade:
            uyarilar.append(
                f"[{kayit_id}] kanit_spanlari satiri 'alan: cumle' bicminde degil: {sade[:50]!r}"
            )
            continue
        alan, _, cumle = sade.partition(":")
        alan, cumle = alan.strip(), cumle.strip()
        if alan not in SPAN_VERILEBILIR_ALANLAR:
            uyarilar.append(f"[{kayit_id}] kanit_spanlari'nda taninmayan alan: {alan!r}")
            continue
        if not cumle:
            uyarilar.append(f"[{kayit_id}] {alan} icin kanit cumlesi bos")
            continue
        spanlar[alan] = cumle
    return spanlar

GECERLI_PERIYOTLAR = {"aylik", "yillik", "belirsiz"}

# Etiketleme oturumunda tek tek gozden gecirilmis sutunlar: burada bos
# hucre "kaynakta belirtilmemis" demektir (bkz. modul docstring'i).
# 28 Temmuz 2026 oturumunun kapsami.
INCELENMIS_ALANLAR = (
    "kar_payi_orani",
    "vade_ay",
    "odul_miktari",
    "masraf_durumu",
    "kampanya_bitis",
    "hedef_kitle",
    # 9 Agustos 2026: bos birakilan 42 kaydin tamami kaynak metne karsi
    # gozden gecirildi (gold_dataset/etiketleme_yardimcisi.py). 26'sinda
    # finansman baglaminda hicbir tutar gecmiyor, 12'sinin kaynagi
    # rotasyonla kaybolmus, 4'unde gecen tutarlar ise HARCAMA ESIGI ya da
    # ODUL ("1.000 TL ve uzeri harcamaniza 10.000 Mil") - finansman
    # tutari degil. Hicbiri deger almadi.
    "finansman_tutari",
    # 23 Agustos 2026: iki sutun daha olcume acildi. Denetimde bulunan
    # durum: taksit_sayisi 80, erteleme_suresi_ay 97 kayitta NE DOLU NE
    # BOS-ISARETLI idi - yani motor oraya uydurma bir deger yazsa bu
    # olcume HIC girmiyordu (bedava puan).
    #
    # Kapatmak icin yapilanlar:
    #   - metinde o alandan hic soz etmeyen kayitlar (taksit 59,
    #     erteleme 79) kaynak metinle tek tek tarandi, deger yok,
    #   - iz bulunan 12 kayit elle okundu; 4'unde deger vardi ve
    #     dolduruldu (ZK-004, AL-001, TF-001, TF-005), 3'unde iz yan
    #     menudeki BASKA kampanyalardan geliyordu (VK-009, VK-010,
    #     ZK-011) - bos birakildi,
    #   - kaynagi kaybolmus 14 kayit kampanya adi + turu + kaydin kendi
    #     ozet alanlariyla dogrulandi,
    #   - 9 kayitta deger YANLIS ALANDAYDI (vade_ay), taksit_sayisi'na
    #     tasindi (bkz. _taksit_vade_karisikligi).
    "taksit_sayisi",
    "erteleme_suresi_ay",
)

# Semada/Excel'de VAR ama henuz bir etiketleme oturumundan gecmemis
# sutunlar. Bos hucreleri "kaynakta yok" SAYILMAZ - olcum disidir.
# Etiketlemesi biten sutun buradan cikarilip INCELENMIS_ALANLAR'a eklenir.
#
INCELENMEMIS_ALANLAR = (
    # 23 Agustos 2026: liste BOSALDI - taksit_sayisi ve
    # erteleme_suresi_ay INCELENMIS_ALANLAR'a tasindi. Semadaki her
    # olculen sutun artik yanlis pozitif olcumune giriyor.
)


class DogrulamaHatasi(Exception):
    """Altin Veri Seti'nde duzeltilmesi gereken bir sorun bulundu."""


def _tarihe_cevir(deger, kayit_id: str, alan: str) -> str | None:
    if deger is None or str(deger).strip() == "":
        return None
    if isinstance(deger, (datetime, date)):
        return deger.strftime("%Y-%m-%d")
    metin = str(deger).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", metin):
        return metin
    raise DogrulamaHatasi(
        f"[{kayit_id}] {alan}: tarih formati YYYY-AA-GG olmali, bulunan: {metin!r}"
    )


def _sayiya_cevir(deger, kayit_id: str, alan: str) -> float | int | None:
    if deger is None or str(deger).strip() == "":
        return None
    if isinstance(deger, (int, float)):
        return deger

    metin = str(deger).strip()
    # Sik yapilan hatalari yakala ve ACIK hata ver (sessizce duzeltme)
    if "%" in metin or "TL" in metin.upper() or re.search(r"[A-Za-zıİşŞğĞüÜöÖçÇ]", metin):
        raise DogrulamaHatasi(
            f"[{kayit_id}] {alan}: yalnizca sayi yazilmali (birim/isaret olmadan). "
            f"Bulunan: {metin!r}. Ornek dogru yazim: 1.89"
        )
    if "," in metin:
        raise DogrulamaHatasi(
            f"[{kayit_id}] {alan}: ondalik ayraci NOKTA olmali. "
            f"Bulunan: {metin!r} -> {metin.replace(',', '.')!r} olmali"
        )
    try:
        return float(metin) if "." in metin else int(metin)
    except ValueError:
        raise DogrulamaHatasi(f"[{kayit_id}] {alan}: sayiya cevrilemedi: {metin!r}")


# ---------------------------------------------------------------------------
# TARIH BEKCISI - "kaynakta yok" iddiasini kaynaga sorar
# ---------------------------------------------------------------------------
# Bu kor nokta IKI KEZ isirdi:
#   * Ziraat sayfalari tarihi "Kampanya Donemi" basligi altinda veriyor;
#     statik tarama o blogu yakalamamisti ve 7 kayit tarihsiz kaldi.
#   * Vakif sayfalari "Kampanya Gecerlilik Tarihi" diyor; ilk denetim
#     kalibi bu yazimi bilmedigi icin VK-009, VK-010 ve TF-005 gozden
#     kacti - TF-005'in notunda "bitis tarihi sayfada belirtilmemis"
#     yaziyordu, oysa yaziyordu.
#
# Ders: "kaynakta yok" bir IDDIADIR ve kaynaga sorulabilir. Bu kontrol
# tam da onu yapar - tarih alanlari BOS olan bir kayitta, kaynak metinde
# hem tarih hem de donem ifadesi varsa uyarir.
#
# HATA DEGIL UYARI URETIR: cerez politikasi metinlerinde de tarih gecer
# (olculdu: DK-001 ve DK-004'te "17/08/2026" cerez aciklamasindan
# geliyor). Karar yine insanindir; kod yalnizca bakilacak yeri gosterir.
_DONEM_IFADESI = re.compile(
    r"kampanya\s+d[oö]nemi|kampanya\s+tarihleri|tarihleri\s+aras[iı]nda"
    r"|tarihine\s+kadar|ge[çc]erlilik\s+tarihi|kampanya\s+s[uü]resi",
    re.IGNORECASE,
)


# Cerez/gizlilik metinlerinde de tarih gecer ama kampanyayla ilgisi
# yoktur. Olculdu: Dunya Katilim sayfalarinda "17/08/2026" tarihi
# "cerez ... sona erme tarihine kadar" aciklamasindan geliyor ve
# DK-001 ile DK-004'te KALICI yanlis alarm uretiyordu. Surekli uyaran
# bir kontrol okunmaz hale gelir - gercek uyari da gorulmez.
_CEREZ_BAGLAMI = re.compile(
    r"[çc]erez|cookie|taray[iı]c[iı]|gizlilik politikas|kvkk", re.IGNORECASE)


def _tarih_izi(metin: str) -> list[str]:
    """Metindeki tarihler - CEREZ metnindekiler haric."""
    from extraction.normalizer import TR_AY_ADLARI

    kalip = re.compile(
        r"\d{1,2}[-./]\d{1,2}[-./]\d{4}"
        r"|\d{1,2}\s+(?:" + "|".join(TR_AY_ADLARI) + r")\s+\d{4}",
        re.IGNORECASE,
    )
    bulunan = set()
    for m in kalip.finditer(metin):
        # Tarihin yakin cevresi cerez metniyse sayma.
        cevre = metin[max(0, m.start() - 220):m.end() + 220]
        if _CEREZ_BAGLAMI.search(cevre):
            continue
        bulunan.add(m.group(0).strip())
    return sorted(bulunan)


def tarih_bekcisi(kayitlar: list[dict]) -> list[str]:
    """Tarihi bos kayitlarin kaynaginda tarih var mi?"""
    # SESSIZ BASARISIZLIK TUZAGI (olculdu): bu betik
    # `python gold_dataset/excel_to_json.py` seklinde calistirildiginda
    # sys.path[0] repo koku DEGIL, gold_dataset/ klasoru olur ve
    # `gold_dataset.sprint_is_listesi` importu ImportError verir. Ilk
    # surum bunu sessizce yutuyordu - kontrol hic calismiyor ama cikti
    # "Uyari yok" diyordu, yani her sey yolunda GORUNUYORDU.
    #
    # Cozum iki parcali: kokU path'e ekle, ve yine de basarisiz olursa
    # SESSIZ KALMA - kontrolun atlandigini SOYLE.
    kok = str(Path(__file__).resolve().parent.parent)
    if kok not in sys.path:
        sys.path.insert(0, kok)

    try:
        from gold_dataset.sprint_is_listesi import _ham_kampanyalar, _slug
    except ImportError as hata:
        return [f"[tarih bekcisi] KONTROL ATLANDI - modul yuklenemedi: {hata}"]

    try:
        ham = _ham_kampanyalar()
    except Exception as hata:  # noqa: BLE001
        return [f"[tarih bekcisi] KONTROL ATLANDI - korpus okunamadi: "
                f"{type(hata).__name__}"]
    if not ham:
        return ["[tarih bekcisi] KONTROL ATLANDI - scraper korpusu bos"]

    uyarilar = []
    for k in kayitlar:
        # IMZASIZ SATIR HENUZ OKUNMADI: tarihinin bos olmasi bir karar
        # degil, sadece siranin ona gelmemis olmasidir. Uyarmak, kuyrukta
        # bekleyen her taslak icin bir satir gurultu uretir ve GERCEK
        # uyarilari gorunmez kilar (olculdu: 200 taslak -> 150 uyari).
        if not (k.get("giren_kisi") or "").strip():
            continue
        if k.get("kampanya_baslangic") or k.get("kampanya_bitis"):
            continue
        kaynak = ham.get(_slug(k.get("kaynak_url") or ""))
        if not kaynak:
            continue
        metin = kaynak.get("normalize_metin") or ""
        if not _DONEM_IFADESI.search(metin):
            continue
        tarihler = _tarih_izi(metin)
        if tarihler:
            uyarilar.append(
                f"[{k['kayit_id']}] kampanya tarihi BOS ama kaynakta tarih var: "
                f"{', '.join(tarihler[:4])} - sayfayi kontrol et "
                "(cerez metninden geliyorsa bos dogru)"
            )
    return uyarilar


def _kaydi_dogrula(kayit: dict) -> list[str]:
    """Mantiksal tutarlilik kontrolleri. Hata degil, UYARI listesi doner."""
    uyarilar = []
    kid = kayit.get("kayit_id", "?")

    oran = kayit.get("kar_payi_orani")
    periyot = kayit.get("oran_periyodu")

    if oran is not None and not periyot:
        uyarilar.append(
            f"[{kid}] Oran girilmis ama oran_periyodu bos. "
            "Aylik mi yillik mi belirtilmeli (bilinmiyorsa 'belirsiz')."
        )

    if periyot and periyot not in GECERLI_PERIYOTLAR:
        uyarilar.append(
            f"[{kid}] oran_periyodu gecersiz: {periyot!r}. "
            f"Gecerli: {', '.join(sorted(GECERLI_PERIYOTLAR))}"
        )

    # Aylik oran cok yuksekse muhtemelen yillik oran aylik sanilmis
    if oran is not None and periyot == "aylik" and oran > 20:
        uyarilar.append(
            f"[{kid}] Aylik oran %{oran} olamaz - bu muhtemelen YILLIK bir orandir "
            "(ya da mevduat orani). Kaynak sayfayi tekrar kontrol et."
        )

    if kayit.get("odul_miktari") is not None and not kayit.get("odul_birimi"):
        uyarilar.append(f"[{kid}] odul_miktari var ama odul_birimi bos (Mil/Gram/TL...)")

    # Ters tutarsizlik: birim yazilmis ama miktar "kaynakta yok" sayilmis.
    # Ikisi birlikte olamaz - turetilmis bayrak (bkz. donustur) bu durumda
    # devreye GIRMEZ, yani sessiz kalmak yerine etiketleyici uyarilmali.
    if kayit.get("odul_birimi") and kayit.get("odul_miktari") is None:
        uyarilar.append(
            f"[{kid}] odul_birimi ({kayit['odul_birimi']}) yazilmis ama "
            "odul_miktari bos - miktar gercekten kaynakta yok mu?"
        )

    bas, bit = kayit.get("kampanya_baslangic"), kayit.get("kampanya_bitis")
    if bas and bit and bas > bit:
        uyarilar.append(f"[{kid}] kampanya_baslangic ({bas}) bitisten ({bit}) sonra")

    if not kayit.get("kaynak_url"):
        uyarilar.append(f"[{kid}] kaynak_url bos - provenance icin zorunlu")

    uyarilar.extend(_taksit_vade_karisikligi(kayit, kid))

    return uyarilar


# Kampanya adindaki "3 Taksit" / "5 Aya Varan Taksit" kalibi.
_ADDA_TAKSIT = re.compile(r"(\d{1,2})\s*(?:aya varan\s*)?taksit", re.IGNORECASE)


def _taksit_vade_karisikligi(kayit: dict, kid: str) -> list[str]:
    """taksit_sayisi ile vade_ay ayni seyi ifade ETMEZ - ama altin sette
    karismislar.

    OLCULEN DURUM: "MTV Odemelerinde Vade Farksiz 3 Taksit" kampanyasi
    VK-001'de vade_ay=3 olarak, ayni cumleye sahip AL-002'de ise
    taksit_sayisi=3 olarak yazilmis. Ikisi de dogru olamaz.

    NEDEN ONEMLI: vade_ay OLCULEN bir sutundur. Taksit sayisi oraya
    yazildiginda motor ne uretirse uretsin kayitlarin bir kismi yanlis
    sayilir - yani olcum, motorun hatasini degil ETIKETLEYICILERIN
    ANLASMAZLIGINI olcer. Bu, en pahali hata turudur: sebep motorda
    aranir, orada yoktur.

    DOGRU AYRIM: taksit sayisi bir ADETTIR (3 taksit = 3 odeme);
    vade ise finansmanin SURESIDIR (12 ay vade). MTV/vergi/alisveris
    odemesinde "vade" kavrami yoktur - oralarda deger taksit_sayisi'dir.

    BURASI HATA DEGIL UYARI URETIR: dokunulan kayitlar baskasinin
    etiketidir ve bu projede altin kayit, insan dogrulamasi + ekran
    goruntusuyle degistirilir. Kod yalnizca GORUNUR kilar; duzeltmeyi
    kaydi giren kisi kendi kaynagina bakarak yapar.
    """
    ad = kayit.get("kampanya_adi") or ""
    eslesme = _ADDA_TAKSIT.search(ad)
    if not eslesme:
        return []
    sayi = int(eslesme.group(1))
    if kayit.get("vade_ay") == sayi and kayit.get("taksit_sayisi") is None:
        return [
            f"[{kid}] kampanya adi '{eslesme.group(0)}' diyor ama deger "
            f"vade_ay={sayi} olarak yazilmis; taksit_sayisi bos. Taksit "
            "ADEDI ile finansman SURESI ayni alan degildir - kaynagi kontrol et."
        ]
    return []


def donustur(excel_yolu: Path = EXCEL) -> tuple[list[dict], list[str]]:
    wb = openpyxl.load_workbook(excel_yolu, data_only=True)
    if SAYFA not in wb.sheetnames:
        raise DogrulamaHatasi(f"'{SAYFA}' sayfasi bulunamadi. Sayfalar: {wb.sheetnames}")

    ws = wb[SAYFA]
    basliklar = [h.value for h in ws[1]]

    kayitlar: list[dict] = []
    tum_uyarilar: list[str] = []
    gorulen_idler: set[str] = set()

    for satir in ws.iter_rows(min_row=VERI_BASLANGIC_SATIRI, values_only=True):
        ham = dict(zip(basliklar, satir))

        kayit_id = (ham.get("kayit_id") or "").strip() if ham.get("kayit_id") else ""
        if not kayit_id:
            continue  # bos satir

        if kayit_id in gorulen_idler:
            tum_uyarilar.append(f"[{kayit_id}] Ayni kayit_id birden fazla satirda")
        gorulen_idler.add(kayit_id)

        kayit: dict = {}
        for alan, deger in ham.items():
            if alan is None:
                continue
            if alan == SPAN_ALANI:
                kayit[alan] = _spanlari_ayristir(deger, kayit_id, tum_uyarilar)
            elif alan in SAYISAL_ALANLAR:
                kayit[alan] = _sayiya_cevir(deger, kayit_id, alan)
            elif alan in TARIH_ALANLARI:
                kayit[alan] = _tarihe_cevir(deger, kayit_id, alan)
            else:
                kayit[alan] = str(deger).strip() if deger is not None else None

        # Seffaflik bayragi: YALNIZCA incelenmis sutunlarda bos hucre
        # "kaynakta belirtilmemis" sayilir (bkz. modul docstring'i).
        #
        # IMZASIZ KAYIT HICBIR IDDIA TASIMAZ: giren_kisi bos ise o satira
        # kimse bakmamistir; bos hucreleri "kaynakta yok" saymak, motorun
        # o alanlarda hicbir sey uretmemesini DOGRU sayardi - yani bos
        # birakilmis her taslak satir bedava puan kapisi olurdu.
        # Etiketleme sprintinde kuyruktan yuzlerce taslak satir aciliyor;
        # imza gelene kadar bu satirlar olcumun disindadir.
        imzali = bool((kayit.get("giren_kisi") or "").strip())
        kayit["alan_belirtilmemis"] = {
            a: True for a in INCELENMIS_ALANLAR if kayit.get(a) is None
        } if imzali else {}

        # TURETILMIS BAYRAK - odul_birimi, odul_miktari'na BAGLIDIR:
        # olmayan bir odulun birimi de olamaz. Bu YENI bir etiketleme
        # karari degil, 28 Temmuz oturumunda zaten verilmis "odul_miktari
        # kaynakta belirtilmemis" kararinin mantiksal sonucudur.
        # Dogrulandi (9 Agustos): odul_birimi'nin bos oldugu 28 kayit ile
        # odul_miktari'nin bayrakli oldugu 28 kayit BIREBIR ayni kume.
        if (
            kayit["alan_belirtilmemis"].get("odul_miktari")
            and kayit.get("odul_birimi") is None
        ):
            kayit["alan_belirtilmemis"]["odul_birimi"] = True

        tum_uyarilar.extend(_kaydi_dogrula(kayit))
        kayitlar.append(kayit)

    # Kaynak korpusa BIR KEZ bakan kontrol (kayit basina degil).
    tum_uyarilar.extend(tarih_bekcisi(kayitlar))

    return kayitlar, tum_uyarilar


def main() -> int:
    if not EXCEL.exists():
        print(f"HATA: {EXCEL} bulunamadi")
        return 1

    try:
        kayitlar, uyarilar = donustur()
    except DogrulamaHatasi as e:
        print(f"\nDUZELTILMESI GEREKEN HATA:\n  {e}\n")
        return 1

    ornek = [k for k in kayitlar if k.get("giren_kisi") == "ORNEK"]
    gercek = [k for k in kayitlar if k.get("giren_kisi") != "ORNEK"]
    # IMZALI olan altin settir; imzasiz satir kuyrukta bekleyen taslaktir
    # ve hicbir olcume girmez. Ikisi TEK SAYIDA birlestirilmez - "303
    # kayitlik altin set" demek, 200 bos satiri veri saymak olurdu.
    imzali = [k for k in gercek if (k.get("giren_kisi") or "").strip()]
    taslak = [k for k in gercek if not (k.get("giren_kisi") or "").strip()]

    with open(JSON_CIKTI, "w", encoding="utf-8") as f:
        json.dump(kayitlar, f, ensure_ascii=False, indent=2)

    print(f"Yazildi: {JSON_CIKTI}")
    print(f"  Toplam satir      : {len(kayitlar)}")
    print(f"  Ornek (ORNEK)     : {len(ornek)}")
    print(f"  ALTIN SET (imzali): {len(imzali)}   <- olculen kayitlar")
    print(f"  Taslak (imzasiz)  : {len(taslak)}   <- kuyrukta, olcum disi")

    bankalar: dict[str, int] = {}
    for k in imzali:
        bankalar[k.get("banka") or "?"] = bankalar.get(k.get("banka") or "?", 0) + 1
    if bankalar:
        print("\n  Banka basina IMZALI kayit:")
        for b, n in sorted(bankalar.items()):
            durum = "OK" if n >= 5 else "yetersiz (hedef 5-8)"
            print(f"    {b:24} {n:2}  {durum}")

    # Olcum kapsami: yanlis pozitif YALNIZCA incelenmis sutunlarda
    # olculebilir (bkz. modul docstring'i).
    # Payda IMZALI kayit sayisidir: imzasiz taslaklar hicbir alanda olcume
    # girmez, paydaya katilirlarsa kapsam oldugundan dusuk gorunur.
    print("\n  Yanlis pozitif olcum kapsami (imzali kayitlar uzerinden):")
    for alan in INCELENMIS_ALANLAR:
        bayrakli = sum(1 for k in imzali if k["alan_belirtilmemis"].get(alan) is True)
        print(f"    {alan:20} olculebilir={bayrakli:2}/{len(imzali)}  (incelendi)")
    turetilmis = sum(1 for k in imzali if k["alan_belirtilmemis"].get("odul_birimi"))
    if turetilmis:
        print(
            f"    {'odul_birimi':20} olculebilir={turetilmis:2}/{len(imzali)}  "
            "(TURETILDI - odul_miktari bayragindan)"
        )
    for alan in INCELENMEMIS_ALANLAR:
        dolu = sum(1 for k in imzali if k.get(alan) is not None)
        print(
            f"    {alan:20} olculebilir= 0/{len(imzali)}  "
            f"(OLCUM DISI - {dolu} kayitta deger var, bos kalanlar incelenmedi)"
        )
    if INCELENMEMIS_ALANLAR:
        print(
            "\n    Bir sutunun etiketlemesi bitince adini excel_to_json.py'deki\n"
            "    INCELENMIS_ALANLAR listesine tasi - yanlis pozitif o an olculur\n"
            "    hale gelir. Yardimci: python gold_dataset/etiketleme_yardimcisi.py"
        )

    if uyarilar:
        print(f"\n  UYARILAR ({len(uyarilar)}):")
        for u in uyarilar:
            print(f"    - {u}")
    else:
        print("\n  Uyari yok.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

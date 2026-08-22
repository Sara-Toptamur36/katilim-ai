"""Etiketleme sprinti is listesi (gold_dataset/sprint_is_listesi.py).

Bu liste, insan etiketleyicinin ONUNE konan is emridir. Yanlis bir liste
gunlerce bosa emek demektir: liste sayfasina gonderilen etiketleyici ya
zaman kaybeder ya da UYDURMA bir altin kayit uretir. Bu yuzden listenin
kendisi test edilir.
"""

import json
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
GOLD = KOK / "gold_dataset" / "altin_veri_seti.json"

SAHTE_ONEKLER = ("A-", "B-", "C-", "D-")


@pytest.fixture(scope="module")
def rapor():
    from gold_dataset.sprint_is_listesi import is_listesi_uret

    return is_listesi_uret(hedef=200, kota=30)


@pytest.fixture(scope="module")
def etiketli_sluglar():
    with open(GOLD, encoding="utf-8") as f:
        return {
            k["kaynak_url"].rstrip("/").split("/")[-1]
            for k in json.load(f)
            if not k["kayit_id"].startswith(SAHTE_ONEKLER) and k.get("kaynak_url")
        }


def test_zaten_etiketli_kampanya_listeye_GIRMEZ(rapor, etiketli_sluglar):
    """Ayni kampanyayi iki kez etiketlemek hem emek kaybi hem de altin
    sette cift kayit riskidir."""
    tekrarlar = [k["slug"] for k in rapor["liste"] if k["slug"] in etiketli_sluglar]
    assert not tekrarlar, f"zaten etiketli kampanyalar listede: {tekrarlar[:5]}"


def test_kontrol_gerekenler_ana_listeye_KARISMAZ(rapor):
    """Kategori sayfalari ana listeye karismamali - ama ATILMAZLAR da,
    ayri bolumde insan kontrolune sunulurlar (bkz. bir sonraki test)."""
    from gold_dataset.sprint_is_listesi import KONTROL_GEREK_KALIBI

    sizanlar = [k["slug"] for k in rapor["liste"] if KONTROL_GEREK_KALIBI.search(k["slug"])]
    assert not sizanlar, f"liste sayfasi is listesine sizmis: {sizanlar}"


def test_kontrol_gerekenler_ATILMAZ_raporlanir(rapor):
    """ILK SURUM BUNLARI OTOMATIK ELIYORDU - yanlisti.

    Altin veri setinin kendisi karsi ornegi tasiyor: T.O.M. Katilim'in
    UC kaydi (TOM-001/002/003) TEK bir "kampanyalar.html" sayfasindan
    cikarilmis. Yani kategori kalibina uyan bir sayfa pekala coklu
    kampanya sayfasi olabilir. Karar insanindir; kod yalnizca siraya
    sokar.

    DENETIM BULGUSU (22 Agustos 2026): Bu test onceden "kontrol_gerek
    listesi BOS OLAMAZ" diye sabit veriye guveniyordu - 22 Agustos'ta
    korpusta gercekten bulunan 20 sahte "kampanya" (Kuveyt Turk/Turkiye
    Finans/Ziraat'in saf navigasyon/kategori sayfalari, icerikleri
    incelenip dogrulandi) temizlenince bu sabit varsayim kirildi. Liste
    bos olmak ZORUNDA degil - korpus temizse bos olmasi DOGRU sonuctur.
    Asil test edilmesi gereken, gercek veriye bagli olmayan MEKANIZMANIN
    kendisi: kalip bilinen kategori-benzeri sluglari yakaliyor mu, ve
    korpusta o kalibla eslesen HERHANGI bir slug varsa mutlaka
    kontrol_gerek'e giriyor mu (sessizce kaybolmuyor mu)."""
    from gold_dataset.sprint_is_listesi import KONTROL_GEREK_KALIBI, _ham_kampanyalar

    assert "kontrol_gerek" in rapor
    for x in rapor["kontrol_gerek"]:
        assert x.get("url"), "kontrol icin URL sart - sayfa acilamazsa bakilamaz"

    # Mekanizma dogru calisiyor mu (korpus durumundan BAGIMSIZ): bilinen
    # kategori-benzeri sluglar yakalanmali, gercek kampanya sluglari
    # yakalanmamali.
    assert KONTROL_GEREK_KALIBI.search("kart-kampanyalari"), "kalip artik kategori sluglarini yakalamiyor"
    assert KONTROL_GEREK_KALIBI.search("finansman-kampanyalari.aspx"), "kalip .aspx uzantili kategori sluglarini yakalamiyor"
    assert not KONTROL_GEREK_KALIBI.search("12-aya-varan-taksit-firsati"), "kalip gercek bir kampanya sluguna yanlislikla uyuyor"

    # Tamlik: korpusta kalipla eslesen bir slug VARSA, kontrol_gerek'te
    # gorunmeli - sessizce ana listeye ya da hic bir yere girmemis olmasin.
    kontrol_sluglar = {x["slug"] for x in rapor["kontrol_gerek"]}
    korpustaki_kalip_eslesenler = {
        slug for slug in _ham_kampanyalar() if KONTROL_GEREK_KALIBI.search(slug)
    }
    assert korpustaki_kalip_eslesenler == kontrol_sluglar, (
        "korpustaki kalip eslesen sluglar ile kontrol_gerek listesi tutarsiz"
    )


def test_kota_asilmaz(rapor):
    """Kotanin isi, setin tek bankaya kaymasini engellemek."""
    asanlar = {b: n for b, n in rapor["banka_basina_secilen"].items() if n > 30}
    assert not asanlar, f"kota asilmis: {asanlar}"


def test_liste_tekrarsiz(rapor):
    sluglar = [k["slug"] for k in rapor["liste"]]
    assert len(sluglar) == len(set(sluglar)), "listede tekrar eden kampanya var"


def test_her_kayitta_url_var(rapor):
    """URL olmadan etiketleyici sayfayi acamaz."""
    eksik = [k["slug"] for k in rapor["liste"] if not k.get("url")]
    assert not eksik, f"URL'si olmayan kayitlar: {eksik[:5]}"


def test_liste_deterministik():
    """Ayni girdiyle ayni liste: iki kisi ayni siradan calisabilmeli."""
    from gold_dataset.sprint_is_listesi import is_listesi_uret

    a = [k["slug"] for k in is_listesi_uret(50, 30)["liste"]]
    b = [k["slug"] for k in is_listesi_uret(50, 30)["liste"]]
    assert a == b


def test_baslik_banka_adinin_kendisi_DEGIL(rapor):
    """Ilk surumde baslik olarak "Türkiye Emlak Katilim Bankasi" gibi
    gezinti satirlari seciliyordu - liste okunamaz hale geliyordu."""
    kotu = [
        k["slug"] for k in rapor["liste"]
        if k["baslik"].strip().lower().startswith((k["banka"] or "").lower())
    ]
    assert not kotu, f"baslik banka adiyla basliyor: {kotu[:5]}"


def test_hedef_karsilaniyorsa_bu_GIZLENMEZ(rapor):
    """Rapor, hedefe ulasilip ulasilamadigini sayilarla gostermeli ki
    plan gercege gore yapilsin - "liste uretildi" deyip sessiz kalmak
    yanlis guven verirdi.

    NOT (22 Agustos 2026): Bu test onceden tam tersini kontrol eden bir
    "tripwire" idi - "bugunku korpusta 200 hedefine ulasilamiyor, korpus
    buyudugunde bu test kirilsin ki fark edilsin" diye yazilmisti. 21
    Agustos'taki sitemap.xml taramasi 4 bankada +198 kampanya bulunca
    tam olarak bu oldu: tripwire kirildi, is gordu. Artik korpus hedefi
    karsiliyor (bkz. asagidaki assert) - bu test o yeni gercegi kilitler.
    Ayni desen: bir sonraki buyuk kesif korpusu daraltirsa (banka sitesi
    degisir, kampanyalar kaldirilir vb.) bu test yine kirilir."""
    assert rapor["listelenen"] <= rapor["hedef_yeni_kayit"]
    assert "ulasilabilir_toplam" in rapor
    assert rapor["ulasilabilir_toplam"] >= rapor["hedef_yeni_kayit"], (
        "Korpus beklenenden kucuk - hedefe ulasilamiyor olabilir. "
        "gold_dataset/sprint_is_listesi.py'deki 'DENGE ILE HACIM CATISIYOR' "
        "bolumunu ve README'deki kapsam sayilarini kontrol edin."
    )

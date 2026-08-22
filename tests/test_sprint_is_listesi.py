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
    sokar."""
    assert "kontrol_gerek" in rapor
    assert rapor["kontrol_gerek"], "kontrol listesi bos - kalip calisiyor mu?"
    for x in rapor["kontrol_gerek"]:
        assert x.get("url"), "kontrol icin URL sart - sayfa acilamazsa bakilamaz"


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


def test_hedefe_ulasilamiyorsa_bu_GIZLENMEZ(rapor):
    """Korpus dengesizligi yuzunden 200 hedefine ulasilamiyor. Rapor
    bunu sayilarla gostermeli ki plan gercege gore yapilsin - "liste
    uretildi" deyip sessiz kalmak yanlis guven verirdi."""
    assert rapor["listelenen"] <= rapor["hedef_yeni_kayit"]
    assert "ulasilabilir_toplam" in rapor
    # Bugunku korpusta hedefe ulasilamiyor; ulasilabilir hale geldiginde
    # bu test kirilir ve durumun degistigi FARK EDILIR.
    assert rapor["ulasilabilir_toplam"] < 200, (
        "Korpus buyumus olabilir - is listesi artik 200 hedefini karsiliyor. "
        "docs/ ve README'deki 'denge ile hacim catisiyor' notu guncellenmeli."
    )


def test_ayni_kampanya_farkli_adresle_ISARETLENIR(rapor):
    """Slug esitligi yetmiyor - olculmus iki durum var:

      - Dunya Katilim "Altin Kesem": altin sette `/altin-kesem`,
        ham korpusta `/altin-kesemTicari` (DK-003 ile ayni kampanya)
      - T.O.M.: `kampanyalar.html#...` parcalari, altin setteki
        TOM-001/002/003'un tam karsiligi

    Ikisi de slug esitligini gecip listeye giriyordu. Isaret konmazsa
    etiketleyici ayni kampanyayi tekrar yazar ve o kampanya olcumde
    CIFT agirlik alir.
    """
    isaretli = {k["slug"]: k["muhtemel_kopya"] for k in rapor["liste"] if k.get("muhtemel_kopya")}
    assert "altin-kesemTicari" in isaretli, "DK-003 kopyasi isaretlenmedi"
    parcalar = [s for s in isaretli if "kampanyalar.html#" in s]
    assert parcalar, "etiketli sayfanin URL parcalari isaretlenmedi"


def test_kopya_isareti_ELEMEZ_yalnizca_isaretler(rapor):
    """Kontrol gerek listesindeki dersle ayni: karar insanindir.
    "bridgestoneda-5-taksit" ile "bridgestoneda-5-taksit-2" pekala iki
    ayri kampanya olabilir - isaretli kayit listede KALIR."""
    assert any(k.get("muhtemel_kopya") for k in rapor["liste"])
    assert all("muhtemel_kopya" in k for k in rapor["liste"]), (
        "alan her kayitta bulunmali; yoklugu 'bakilmadi' ile 'temiz'i karistirir"
    )


def test_kopya_suphesi_kendini_isaretlemez():
    """Etiketli bir slug'in KENDISI zaten listeye girmez; ama fonksiyon
    yanlislikla cagrilirsa "kendisiyle onek iliskisi" demesin."""
    from gold_dataset.sprint_is_listesi import _kopya_suphesi

    assert _kopya_suphesi("altin-kesem", "Altın Kesem", {"altin-kesem"}, set()) is None


def test_slug_sonundaki_surum_rakamlari_kopyayi_GIZLEMEZ():
    """Olculmus durum: AL-005 altin sette
    "...-6-taksit-kampanyasi-1_1", ham korpusta ayni kampanya
    "...-6-taksit-kampanyasi1-2". Sadelestirilmis halleri ayni
    UZUNLUKTA oldugu icin onek kurali calismiyordu ve kayit temiz
    gorunuyordu - ta ki elle okunana kadar."""
    from gold_dataset.sprint_is_listesi import _kopya_suphesi

    s = _kopya_suphesi(
        "saglik-harcamalarina-vade-farksiz-6-taksit-kampanyasi1-2", "",
        {"saglik-harcamalarina-vade-farksiz-6-taksit-kampanyasi-1_1"}, set(),
    )
    assert s and "sondaki rakamlar" in s


def test_ORTADAKI_rakam_farki_kopya_SAYILMAZ():
    """"...-300-tl-parafpara" ile "...-400-tl-parafpara" iki AYRI
    kampanyadir. Sondaki rakamlari atma kurali ortaya bulasirsa iki
    gercek kampanya tek sayilir - liste sessizce eksilir."""
    from gold_dataset.sprint_is_listesi import _kopya_suphesi

    assert _kopya_suphesi(
        "akaryakit-harcamalariniza-400-tl-parafpara", "",
        {"akaryakit-harcamalariniza-300-tl-parafpara"}, set(),
    ) is None


def test_ay_varyanti_kopya_olarak_ISARETLENIR():
    """Albaraka'nin ayni fatura kampanyasi hem "temmuz-ayina-ozel-..."
    hem "agustos-ayina-ozel-..." adresiyle duruyor: ayni davet kodu
    (OFT2026), ayni odul (2.000 TL Worldpuan), yalnizca ay farkli.
    Metinler neredeyse ayni oldugu icin biri train'e digeri test'e
    duserse sizinti olur."""
    from gold_dataset.sprint_is_listesi import _kopya_suphesi

    s = _kopya_suphesi("temmuz-ayina-ozel-fatura-kampanyasi", "",
                       {"agustos-ayina-ozel-fatura-kampanyasi"}, set())
    assert s and "AY ADINDA" in s


def test_ay_normallestirmesi_farkli_kampanyalari_BIRLESTIRMEZ():
    """Ay adlarini atmak, adinda ay gecen iki AYRI kampanyayi tek
    sayacak kadar ileri gitmemeli."""
    from gold_dataset.sprint_is_listesi import _kopya_suphesi

    assert _kopya_suphesi("temmuz-ayina-ozel-fatura-kampanyasi", "",
                          {"agustos-ayina-ozel-akaryakit-kampanyasi"}, set()) is None


def test_bosluklu_adres_ana_listeye_GIRMEZ(rapor):
    """Emlak Katilim'in bosluk iceren kampanya adresi kampanya sayfasi
    yerine bankanin ANA SAYFASINI donduruyor - etiketlenecek tek cumle
    yok. Etiketleyici oraya gonderilmemeli; ama sayfa yeniden taranirsa
    gecerli hale gelebilecegi icin ATILMAZ, kontrole gider."""
    assert not [k["slug"] for k in rapor["liste"] if " " in k["slug"]]
    assert [x for x in rapor["kontrol_gerek"] if " " in x["slug"]], (
        "bosluklu adres kontrol listesinde de yok - tamamen kaybolmus"
    )


def test_cok_benzer_alani_HER_kayitta_var(rapor):
    """Alanin yoklugu "bakilmadi" ile "temiz"i karistirir."""
    assert all("cok_benzer" in k for k in rapor["liste"])


def test_cok_benzer_esigin_altini_ISARETLEMEZ(rapor):
    for k in rapor["liste"]:
        if k["cok_benzer"]:
            from gold_dataset.sprint_is_listesi import COK_BENZER_ESIGI

            assert k["cok_benzer"][1] >= COK_BENZER_ESIGI


def test_benzerlik_slug_kurallarini_BAGIMSIZ_dogruluyor(rapor):
    """Iki isaret birbirinden bagimsiz uretiliyor: biri slug'a, digeri
    METNE bakiyor. Slug kurallarinin yakaladigi kayitlarin metin
    benzerligi de yuksek cikmali - cikmiyorsa esik ya da kurallardan
    biri yanlistir.

    NOT: muhtemel_kopya isaretli kayitlarin bir kisminin kaynak sayfasi
    ham veride yok (TOM'un kampanyalar.html'i gibi) - onlar icin metin
    karsilastirmasi YAPILAMAZ, bu yuzden kesisim aranir, esitlik degil.
    """
    kopya = {k["slug"] for k in rapor["liste"] if k.get("muhtemel_kopya")}
    benzer = {k["slug"] for k in rapor["liste"] if k.get("cok_benzer")}
    assert kopya & benzer, "iki isaret hic ortusmuyor - biri bozuk olabilir"


def test_ikiz_ayni_bankadan(rapor):
    """Kalip metni bankaya ozeldir; farkli bankadan ikiz gosterilmesi
    olcumun yanlis kurulduguna isarettir."""
    import json as _json
    from pathlib import Path

    kok = Path(__file__).resolve().parent.parent
    with open(kok / "gold_dataset" / "altin_veri_seti.json", encoding="utf-8") as f:
        banka = {k["kayit_id"]: k.get("banka") for k in _json.load(f)}
    for k in rapor["liste"]:
        if k["cok_benzer"]:
            assert banka[k["cok_benzer"][0]] == k["banka"]

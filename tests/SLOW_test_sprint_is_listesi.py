"""Etiketleme sprinti is listesi (gold_dataset/sprint_is_listesi.py).

Bu liste, insan etiketleyicinin ONUNE konan is emridir. Yanlis bir liste
gunlerce bosa emek demektir: liste sayfasina gonderilen etiketleyici ya
zaman kaybeder ya da UYDURMA bir altin kayit uretir. Bu yuzden listenin
kendisi test edilir.

NOT (24 Agustos 2026): Bu test YAVAS - is_listesi_uret() tum korpusu
okur, kumeleme ve benzerlik hesaplamasi yapar (3+ dakika). Rutin CI'da
skip edilir, yalnizca sprint is listesi degistiginde manuel calistirilir.

MANUEL CALISTIRMA:
    PYTEST_SLOW_TESTS=1 pytest tests/test_sprint_is_listesi.py -v
"""

import json
import os
from pathlib import Path

import pytest

# TUM modul skip - ortam degiskeni ile override
pytestmark = pytest.mark.skipif(
    os.environ.get("PYTEST_SLOW_TESTS") != "1",
    reason="Slow test (3+ min) - set PYTEST_SLOW_TESTS=1 to run"
)

KOK = Path(__file__).resolve().parent.parent
GOLD = KOK / "gold_dataset" / "altin_veri_seti.json"

SAHTE_ONEKLER = ("A-", "B-", "C-", "D-")
_GOLD_DOSYASI = GOLD


@pytest.fixture(scope="module")
def rapor():
    from gold_dataset.sprint_is_listesi import is_listesi_uret

    # KOTA YOK: korpus zaten iki bankaya agir bastigi icin kota,
    # ulasilabilir kayit sayisini 200'un altinda tutuyordu. Denge
    # bedeli raporda acikca gorunur.
    return is_listesi_uret(hedef=200, kota=None)


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
    # KONTROL LISTESINE IKI SEBEPLE GIRILIR, esitlik testi birini
    # biliyordu ve digeri "tutarsizlik" gibi gorunuyordu:
    #   (a) kategori kalibina uyan slug ("default.aspx"),
    #   (b) ADRESINDE BOSLUK olan slug - Emlak Katilim'in
    #       ".../kampanya/Paraf ile Hepsiburada'da ... Firsati!" adresi
    #       kampanya sayfasi yerine bankanin ANA SAYFASINI donduruyor.
    # Ikisi de "insan baksin" demek; ikisi de listede olmali.
    kontrol_sluglar = {x["slug"] for x in rapor["kontrol_gerek"]}
    gecerli_sebepler = {
        slug for slug in _ham_kampanyalar()
        if KONTROL_GEREK_KALIBI.search(slug) or " " in slug
    }
    # (i) Listede GECERSIZ bir sey olmamali.
    assert kontrol_sluglar <= gecerli_sebepler, (
        "kontrol_gerek'te ne kalip ne bosluk sebebi olan slug var: "
        f"{sorted(kontrol_sluglar - gecerli_sebepler)[:5]}"
    )
    # (ii) Sebebi olan hicbir sayfa SESSIZCE kaybolmamali. Tek istisna:
    # kumesi zaten etiketli olanlar - onlar icin yapilacak is kalmadi.
    etiketli = {
        (k.get("kaynak_url") or "").rstrip("/").split("/")[-1]
        for k in json.load(open(GOLD, encoding="utf-8"))
    }
    kaybolanlar = gecerli_sebepler - kontrol_sluglar - etiketli
    assert not kaybolanlar, (
        f"kontrol sebebi olan sayfalar listeye girmemis: {sorted(kaybolanlar)[:5]}"
    )


def test_kota_asilmaz(rapor):
    """Kotanin isi, setin tek bankaya kaymasini engellemek."""
    kota = rapor["banka_basina_kota"]
    if kota is None:
        # Kota kaldirildiginda sinir yoktur; sinanacak olan, kotanin
        # VERILDIGINDE calistigidir.
        from gold_dataset.sprint_is_listesi import is_listesi_uret

        kotali = is_listesi_uret(hedef=200, kota=5)
        asanlar = {b: n for b, n in kotali["banka_basina_secilen"].items() if n > 5}
        assert not asanlar, f"kota asilmis: {asanlar}"
        return
    asanlar = {b: n for b, n in rapor["banka_basina_secilen"].items() if n > kota}
    assert not asanlar, f"kota asilmis (kota={kota}): {asanlar}"


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
    # HEDEF ARTIK KARSILANIYOR. Iki bagimsiz gelisme ayni sonuca goturdu:
    # (1) kota kaldirildi ve kaynak sayfalar JS ile yeniden tarandi -
    #     tazelenmis metinler daha dolu oldugu icin kumeleme, eskiden ayni
    #     gorunen sayfalari ayirt edebiliyor;
    # (2) sitemap taramasiyla korpusa yeni kampanyalar eklendi.
    #
    # Sart TERSINE cevrildi: bundan sonra hedefin ALTINA dusmek fark
    # edilmeli. Karsilastirma SABIT 200 degil, hedef parametresi uzerinden
    # yapilir - hedef degisirse test onunla birlikte hareket eder.
    assert rapor["ulasilabilir_toplam"] >= rapor["hedef_yeni_kayit"], (
        f"Ulasilabilir toplam hedefin ALTINA dustu: "
        f"{rapor['ulasilabilir_toplam']} < {rapor['hedef_yeni_kayit']} "
        f"(mevcut {rapor['mevcut_altin_kayit']} + kuyruk {rapor['listelenen']}). "
        "Kayit silinmis ya da kumeleme fazla eliyor olabilir."
    )


def test_ayni_kampanya_farkli_adresle_LISTEYE_GIRMEZ(rapor):
    """Olculmus iki durum:

      - Dunya Katilim "Altin Kesem": altin sette `/altin-kesem`,
        ham korpusta `/altin-kesemTicari` (DK-003 ile ayni kampanya)
      - T.O.M.: `kampanyalar.html#...` parcalari, altin setteki
        TOM-001/002/003'un tam karsiligi

    ONCEKI SURUM BUNLARI ISARETLIYORDU ama listede birakiyordu.
    Kume tabanli secimde artik LISTEYE HIC GIRMIYORLAR: bir uyesi
    etiketli olan kume tumuyle duser. Isaretleme emniyet agi olarak
    duruyor (bkz. test_emniyet_agi_calisiyor)."""
    sluglar = {k["slug"] for k in rapor["liste"]}
    assert "altin-kesemTicari" not in sluglar
    assert not [s for s in sluglar if "kampanyalar.html#" in s], (
        "etiketli sayfanin URL parcalari hala listede"
    )


def test_ADRES_benzerligi_tek_basina_ELEMEZ(rapor):
    """Iki farkli kanit, iki farkli yetki.

    SLUG kurallari (muhtemel_kopya) yalnizca ISARETLER: adres benzerligi
    zayif bir kanittir, "...-300-tl-parafpara" ile "...-400-tl-parafpara"
    pekala iki ayri kampanyadir. Bunlari elemek gercek kampanya kaybi olur.

    METIN+PROFIL eslesmesi ise ELER (bkz. bir sonraki test): orada iki
    sayfanin hem sozleri hem tasidigi degerler aynidir.
    """
    assert all("muhtemel_kopya" in k for k in rapor["liste"]), (
        "alan her kayitta bulunmali; yoklugu 'bakilmadi' ile 'temiz'i karistirir"
    )
    # ASIL DEGISMEZ: hicbir kayit YALNIZCA adres benzerligi yuzunden
    # elenmis olmamali. Elenen her kaydin metin benzerligi olcusu var.
    #
    # NOT: "listede isaretli kayit KALMALI" diye bir sart KOYULMUYOR.
    # Korpus temizlendikce isaretli kayit sayisi sifira inebilir ve o
    # zaman boyle bir sart, testi kendiliginden kirardi - sinanan sey
    # kural degil, o gunku verinin hali olurdu.
    for x in rapor["benzer_atlanan"]:
        assert "oran" in x, f"{x['slug']} adres benzerligiyle elenmis olabilir"


def test_metin_ve_profil_ayni_olan_LISTEYE_GIRMEZ(rapor):
    """Kumeleme tek gecislidir ve kacirir: bir aday, kendi kumesinin
    temsilcisine benzemeyip BASKA bir etiketli sayfaya benzeyebilir.
    Olculdu: "mobilya-...-4000-tlye-varan-parafpara" temsilciye
    takilmiyordu ama TEK-009 ile hem metni hem profili ayniydi.

    Bu yuzden son kontrol secim aninda yapilir ve ELER."""
    sizanlar = [k for k in rapor["liste"] if k.get("cok_benzer")]
    assert not sizanlar, (
        "altin setteki bir kayitla hem metni hem profili ayni olan sayfa listede: "
        + ", ".join(f"{k['slug']} <-> {k['cok_benzer'][0]}" for k in sizanlar[:5])
    )


def test_elenen_kayit_ATILMAZ_gerekcesiyle_raporlanir(rapor):
    """Sessiz eleme denetlenemez. Elenen her sayfa, hangi altin kayda
    hangi oranla benzedigiyle birlikte raporda durmali."""
    for x in rapor["benzer_atlanan"]:
        assert x["slug"] and x["ikiz"] and x["url"]
        assert x["oran"] >= 0.85
        assert "profil" in x["gerekce"]


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


# ---------------------------------------------------------------------------
# KUME TABANLI SECIM
# ---------------------------------------------------------------------------


def test_kapsanan_kume_listeye_GIRMEZ(rapor, etiketli_sluglar):
    """Bir uyesi zaten etiketli olan kume tumuyle duser. Onceki surumde
    yalnizca ETIKETLI SAYFANIN KENDISI eleniyordu; kumedeki diger
    kopyalar listede kaliyor ve ayni kalip ikinci kez etiketleniyordu."""
    import json as _json

    with open(KOK / "gold_dataset" / "sprint_is_listesi.json", encoding="utf-8") as f:
        _json.load(f)  # dosya gecerli JSON olmali
    for k in rapor["liste"]:
        uyeler = set(k["kume_uyeleri"]) | {k["slug"]}
        assert not (uyeler & etiketli_sluglar), (
            f"{k['slug']} kumesinde zaten etiketli sayfa var: "
            f"{sorted(uyeler & etiketli_sluglar)}"
        )


def test_her_kumeden_TEK_temsilci(rapor):
    """Ayni kume iki kez listelenirse kota bosa harcanir."""
    gorulen: set[str] = set()
    for k in rapor["liste"]:
        uyeler = set(k["kume_uyeleri"]) | {k["slug"]}
        assert not (uyeler & gorulen), f"{k['slug']} kumesi ikinci kez listelenmis"
        gorulen |= uyeler


def test_kayit_kendi_kume_uyesi_olarak_TEKRARLANMAZ(rapor):
    for k in rapor["liste"]:
        assert k["slug"] not in k["kume_uyeleri"]


def test_her_kaydin_secim_gerekcesi_VAR(rapor):
    """Liste bir is emridir; "neden bu sayfa" sorusunun cevabi listede
    durmali, kodun icinde degil."""
    for k in rapor["liste"]:
        assert k.get("banka"), f"{k['slug']} icin banka yok"
        assert k.get("secim_gerekcesi"), f"{k['slug']} icin gerekce yok"
        assert len(k["secim_gerekcesi"]) > 20, (
            f"{k['slug']} gerekcesi bilgi tasimiyor: {k['secim_gerekcesi']!r}"
        )


def test_ilk_secimler_YENI_ozellik_getirir(rapor):
    """Siralamanin isi cesitliligi one almak. Yapisal ozellik uzayi
    kucuktur ve hizla doyar - ama listenin BASINDA yeni ozellik getiren
    kayitlar olmali, yoksa siralama hic calismiyor demektir."""
    ilk = rapor["liste"][:5]
    assert any(k["yeni_ozellikler"] for k in ilk), (
        "ilk bes kayittan hicbiri yeni yapisal ozellik getirmiyor"
    )


def test_ozellik_kapsami_BUYUR(rapor):
    k = rapor["ozellik_kapsami"]
    assert k["bitis"] >= k["baslangic"]


def test_rapor_kume_sayilarini_TASIR(rapor):
    """Raporlama sarti: toplam, banka dagilimi ve kalan benzersiz kume."""
    assert rapor["toplam_kume"] == sum(o["kume"] for o in rapor["banka_ozeti"])
    assert rapor["kapsanan_kume"] == sum(o["kapsanan_kume"] for o in rapor["banka_ozeti"])
    assert rapor["aday_kume"] == sum(o["aday_kume"] for o in rapor["banka_ozeti"])
    # Her aday kume UC yoldan birine gider: listeye girer, benzer
    # oldugu icin elenir, ya da kotaya takilip bekler. Toplam tutmali -
    # tutmuyorsa bir kume sessizce kaybolmus demektir.
    assert (rapor["listelenen"] + len(rapor["benzer_atlanan"])
            + sum(rapor["kalan_kume"].values())) == rapor["aday_kume"]
    assert rapor["benzerlik_esigi"] == 0.85


def test_benzerlik_esigi_SABIT():
    """Esik %85 olarak sabitlendi (olculdu: 63 aday x 57 etiketli sayfada
    ortanca benzerlik %42; %85 acik bir aykiri bolge). Degistirmek altin
    setin bilesimini degistirir - kazara olmamali."""
    from gold_dataset.sprint_is_listesi import COK_BENZER_ESIGI

    assert COK_BENZER_ESIGI == 0.85


def test_kalan_kume_kotadan_dolayi_BEKLETILENLERDIR(rapor):
    """Kotaya takilip listeye giremeyen kumeler GIZLENMEZ - hacim
    gerekirse nereden gelecegi gorunur olmali."""
    for banka, sayi in rapor["kalan_kume"].items():
        # KOTA DISINDA IKINCI BIR SEBEP VAR: hedef dolmus olabilir.
        # Korpus sitemap taramasiyla buyudukten sonra aday sayisi hedefi
        # (200) astı; kota olmadan da kume beklemede kalabiliyor. Ilk
        # surum bunu "havuzun tamami listeye girmeliydi" diye hata
        # sayiyordu.
        if rapor["banka_basina_kota"] is None:
            assert rapor["listelenen"] >= rapor["hedef_yeni_kayit"], (
                f"kota YOK ve hedef dolmamisken {banka} icin {sayi} kume "
                "beklemede kalmis - havuzun tamami listeye girmeliydi"
            )
            continue
        assert rapor["banka_basina_secilen"].get(banka, 0) == rapor["banka_basina_kota"], (
            f"{banka} kotasi dolmadigi halde {sayi} kume beklemede"
        )


def test_altin_setin_KENDI_kopyalari_raporlanir(rapor, capsys):
    """Bu test hicbir sey DOGRULAMAZ; mevcut altin setin kendi icindeki
    kopyalari gorunur kilar.

    Benzerlik korumasi is listesine SONRADAN eklendi. Ondan once
    etiketlenmis kayitlarin bir kismi ayni kumede duruyor - ornegin
    Emlak'in akaryakit ParafPara surumleri. Bunlar olcumde o teklife
    fazladan agirlik verir; ayiklanip ayiklanmayacagi INSAN kararidir,
    bu yuzden test kirilmaz, yalnizca sayiyi yazar."""
    import collections
    import json as _json

    from gold_dataset.sprint_is_listesi import (_ham_kampanyalar, _kumeleri_al,
                                            _yapisal_belirtecler)

    ham = _ham_kampanyalar()
    with open(_GOLD_DOSYASI, encoding="utf-8") as f:
        gold = [k for k in _json.load(f) if not k["kayit_id"].startswith(SAHTE_ONEKLER)]

    slug_kayit = collections.defaultdict(list)
    for k in gold:
        slug_kayit[(k.get("kaynak_url") or "").rstrip("/").split("/")[-1]].append(k["kayit_id"])

    # KUME UYELIGI YETMEZ: kumeleme yalnizca METNE bakar. Ziraat'in
    # "2 taksit" ve "6 taksit" sayfalari ayni kumededir ama FARKLI DEGER
    # tasirlar - onlar kopya degildir. Gercek kopya, metni de yapisal
    # profili de ayni olan cifttir (bkz. _profile_gore_bol).
    catisan = []
    for kumeler in _kumeleri_al(ham).values():
        for kume in kumeler:
            gruplar = {}
            for u in kume["uyeler"]:
                anahtar = frozenset(_yapisal_belirtecler(u.get("normalize_metin") or ""))
                gruplar.setdefault(anahtar, []).extend(slug_kayit.get(u["_slug"], []))
            for idler in gruplar.values():
                if len(idler) > 1:
                    catisan.append(sorted(idler))

    kaynaksiz = sum(1 for k in gold
                    if (k.get("kaynak_url") or "").rstrip("/").split("/")[-1] not in ham)
    with capsys.disabled():
        print(f"\n  Altin set: {len(gold)} kayit | kaynak sayfasi ham veride "
              f"olmayan {kaynaksiz} (kumelenemez)")
        if catisan:
            fazla = sum(len(i) - 1 for i in catisan)
            print(f"  AYNI KUMEDE BIRDEN FAZLA ALTIN KAYIT: {len(catisan)} kume, "
                  f"{fazla} fazla kayit")
            for idler in catisan:
                print(f"    {', '.join(idler)}")


def test_baslik_CUMLE_PARCASI_olmaz(rapor):
    """Baslik turetmesi gelistirme sirasinda IKI KEZ bozuldu; her seferinde
    liste okunamaz hale geldi. Olculmus kotu ornekler:

        "10 Temmuz 2026 - 7 Agustos 2026"                (tarih araligi)
        "Bankkart Lira kazanabilirsiniz."                (cumle kuyrugu)
        "Kampanyaya Trendyol Dolap uygulamasindan..."    (kosul cumlesi)
        "Saat&Saat Magazalarindan ve"                    (cumle parcasi)

    Etiketleyici listede kampanyayi TANIYAMAZSA sira ise yaramaz.
    """
    import re

    kotu = []
    for k in rapor["liste"]:
        b = k["baslik"].strip()
        if not b:
            kotu.append((k["sira"], b, "bos"))
        elif b[0].islower():
            kotu.append((k["sira"], b, "kucuk harfle basliyor - cumle ortasi"))
        elif re.fullmatch(r"[\d\s.\-–—/]+", b):
            kotu.append((k["sira"], b, "yalnizca sayi/tarih"))
        elif b.endswith((" ve", " ile", " veya", ",")):
            kotu.append((k["sira"], b, "yarim kalmis"))
    assert not kotu, "cumle parcasi baslik: " + "; ".join(
        f"{s}. {b!r} ({n})" for s, b, n in kotu[:5])


def test_baslik_slug_ile_ILGILI(rapor):
    """Baslik ya sayfanin slug'ini tanitan bir satiridir ya da slug'in
    kendisinden turetilmistir. Ikisi de degilse baslik BASKA bir
    kampanyayi gosteriyor olabilir - listenin en tehlikeli hatasi budur.
    """
    from extraction.normalizer import turkce_ascii_kucult
    import re

    kopuk = []
    for k in rapor["liste"]:
        slug_kok = {w[:6] for w in re.split(r"[^a-z0-9]+",
                                            turkce_ascii_kucult(k["slug"])) if len(w) >= 4}
        baslik_kok = {w[:6] for w in re.split(r"[^a-z0-9]+",
                                              turkce_ascii_kucult(k["baslik"])) if len(w) >= 4}
        if slug_kok and not (slug_kok & baslik_kok):
            kopuk.append(f"{k['sira']}. {k['baslik'][:40]!r} <-> {k['slug'][:40]}")
    assert not kopuk, "baslik slug ile hic ortusmuyor: " + "; ".join(kopuk[:5])

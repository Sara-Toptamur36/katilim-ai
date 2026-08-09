"""Verifier: cikarim/ajan katmaninin urettigi sayisal iddialarin kaynak
metinde GERCEKTEN GECIP GECMEDIGINI dogrular (README "Henuz kurulmayanlar"
notundaki eksik katman).

NEDEN SADECE "SAYI METINDE VAR MI" YETMEZ (bulgu, gercek veriyle dogrulandi):
KT-006 kaydinda LLM, kaynakta OLMAYAN `odul_miktari` alanina 50000 degerini
uydurdu (bkz. docs/extraction_accuracy_raporu.md, yanlis pozitif listesi).
Naif bir "50000 metinde geciyor mu" kontrolu bunu YANLISLIKLA DOGRULARDI -
cunku "50.000 TL" gercekten metinde geciyor, ama `finansman_tutari` (azami
taksit tutari) olarak, `odul_miktari` degil. Ayni sekilde ayni kayitta
uydurulan `kar_payi_orani_percent=0.0` da naif kontrolden gecerdi - "0"
rakami neredeyse her metinde (tarih, telefon, vb.) bulunur.

TASARIM: Bu yuzden dogrulama SAYI + BAGLAM birlikte arar - extraction/
regex_extractor.py'nin zaten kullandigi pencere-tabanli yaklasimla (bkz.
o dosyadaki _ucret_baglaminda_mi) AYNI ilke: sayinin kendisi yetmez,
iddia edilen ALANLA ilgili bir anahtar kelime sayinin yakininda gecmeli.
Bu, KT-006'nin IKI hallusinasyonunu da (once test_verifier.py'de gercek
veriyle) yakalar.

OLCUM (9 Agustos 2026, guncel): hibrit_extraction_accuracy.py'nin uretttigi
6 gercek yanlis pozitifin **6/6'si (%100) dogru sekilde reddedildi** ve
canli Altin Veri Seti'ndeki 41 gercek (halusinasyon OLMAYAN) iddianin
**37/41'i (%90,2) dogru sekilde onaylandi**. (Onceki bir olcumde 7.
"yanlis pozitif" TOM-002'ydi - ama arastirilinca bunun LLM hallusinasyonu
DEGIL, gold_eslesme.py'deki bir eslestirme hatasi oldugu ortaya cikti:
"ozel" kelimesi baska bir kampanyada tesadufen gectigi icin TOM-002
yanlis metinle karsilastiriliyordu - duzeltme sonrasi TOM-002 hic
yanlis pozitif uretmiyor, bkz. o commit.)

Yol boyunca eklenen format varyantlari (gercek veriyle bulundu):
"X TL - Y TL **arasi**" ve "X TL'ye **kadar**" ifadeleri (finansman_tutari
icin, literal "tutar"/"finansman" kelimesi hic gecirmeden tutar bildirir)
ve "250 **bin** TL" gibi kelime-bazli buyukluk eki (binlik ayiracli
"250.000" YAZILMAYAN kayitlar icin).

DENENDI VE BILEREK DUZELTILMEDI: TOM-002'yi yakalamak icin "sayinin
yaninda sinirli/maksimum/azami/en fazla geçerse reddet" kurali denendi.
TUM canli Altin Veri Seti odul_miktari kayitlarina (23 kayit) karsi test
edildi: TOM-002'yi dogru yakaladi AMA 6 GERCEK DOGRU kaydi (ZK-005,
ZK-007, DK-003, HF-001, HF-004, TOM-001) yanlislikla reddetti - cunku
"en fazla X TL kazanabilirsiniz" katilim bankasi metinlerinde
odul_miktari'nin EN YAYGIN ifade bicimi. Carpici bulgu: TOM-001'in gold
kaydinda BIREBIR AYNI cumle kalibi ("...ile sinirlidir") DOGRU kabul
edilmis - insan etiketleyicinin kendisi bile bu kalip icin tutarli
degil. Kural NET ZARARLI cikti (6 kirilma / 1 duzeltme) ve GERI ALINDI.

Bu denemenin YAN URUNU olarak farkli, gercek bir hata bulunup duzeltildi:
cumle siniri hesabi baslangicta tek satir sonunu (\\n) da sinir sayiyordu
- ama scraper'in ham metni HER html blok elemani arasina \\n koydugu icin
("en fazla 1.500 tl\\nkazanabilecektir." gibi AYNI cumle iki satira
bolunuyor) bu, ZK-005/DK-002 gibi GERCEK dogru degerleri yanlislikla
reddediyordu. \\n sinir olmaktan cikarilinca (yalnizca ., !, ? kaliyor)
tum alan turlerinde canli dogrulama orani %82,9'a (34/41) cikti, halbuki
yanlis pozitif yakalama orani (6/7) DEGISMEDI - net kazanc.

DENENDI VE BILEREK GERI ALINDI (2): kar_payi_orani_percent=0 icin, metinde
literal "0" olmadan "vade farksiz"/"kar paysiz" gecerse dogrudan dogrulayan
bir kisayol denendi (AL-002/005/006 icin dogru sonuc verdi, genis oran
%97,6'ya cikti) AMA KT-006 ve TF-001'in GERCEK hallusinasyonlarini
(kar_payi_orani_percent=0.0 uydurmasi) yanlislikla dogruladi -
hallusinasyon yakalama oranini %100'den %67'ye dusurdu. TF-001'de somut
kanit: "kar paysiz 2.500 TL'ye kadar yedek hesap finansman destegi" -
bu, kampanyanin GENEL oranini degil, BASKA bir alt urunun ozelligini
anlatiyor. Modulun ASIL amaci hallusinasyon yakalamak oldugu icin (dogru
deger bulma degil), bu kisayol GERI ALINDI - ayni "insan etiketleyici
bile tutarli degil" kategorisi (TOM-001/TOM-002 gibi).

BILINEN SINIR (durustluk notu, guncel): Bu, tam bir NLP/varlik-iliski
cikarimi DEGILDIR - sadece "sayi + ilgili kelime yakinda mi" sezgiselidir.
Kalan 4 dogrulanamayan gercek kayit (AL-002, AL-005, AL-006, TOM-002 -
hepsi kar_payi_orani_percent=0) TEK bir kok nedene iniyor: "vade farksiz"
gibi RAKAMSIZ ifadelerle ima edilen sifir degerler, literal "0" yazilmadigi
icin dogrulanamiyor - VE bu ifadeyi kosulsuz guvenmek yukaridaki (2)
numarali denemenin gosterdigi gibi gercek hallusinasyonlari maskeler.
Amac halusinasyonu SIFIRLAMAK degil, agirlikli cogunlugunu (ozellikle
"kaynakta hic olmayan sayi" turunu) YAKALAMAKTIR - olculen %100 (6/6)
bu hedefi destekliyor.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Her alan icin, sayinin YAKININDA gecmesi beklenen baglam kelimeleri.
# extraction/regex_extractor.py'deki ayni domain sozlugune sadik kalinir
# (ör. kar payi icin "kar pay"/"kar oran", ucret baglami disi tutuluk).
_ALAN_BAGLAM_KELIMELERI: dict[str, list[str]] = {
    "kar_payi_orani_percent": ["kâr pay", "kar pay", "kâr oran", "kar oran", "vade farksız", "vade farksiz", "kar payı", "kârsız", "karsiz"],
    # "arası": "30.000 TL- 500.000 TL arası okul odemelerinize..." gibi
    # ARALIK ifadeleri, "tutar"/"finansman" kelimesi hic gecirmeden
    # finansman_tutari veriyor (olculdu, AL-006) - "arasi" bu ifadenin
    # ayirt edici isaretidir.
    "finansman_tutari": ["finansman", "kredi tutar", "azami tutar", "maksimum tutar", "üst limit", "ust limit", "tutar", "arası", "arasi", "kadar"],
    "odul_miktari": ["ödül", "odul", "hediye", "bonus", "kazan", "iade", "bankkart lira", "parafpara", "worldpuan", "mil", "puan", "çek", "cek"],
    "vade_ay": ["vade", "ay"],
    "taksit_sayisi": ["taksit"],
    "erteleme_suresi_ay": ["erteleme", "ödemesiz", "odemesiz"],
    "tahsis_ucreti": ["tahsis"],
}

# Bu alan turleri TAM SAYI olarak metinde gecer (ör. "5 ay", "12 taksit") -
# ondalikli varyant uretmeye gerek yok.
_TAMSAYI_ALANLAR = {"vade_ay", "taksit_sayisi", "erteleme_suresi_ay"}

# DENENDI VE GERI ALINDI (9 Agustos 2026): Bazi kayitlarda kar_payi_orani=0
# iken kaynak metin literal "0" rakami YAZMAZ - deger "vade farksiz"/"kar
# paysiz" gibi deyimsel bir ifadeden turetilir. Bu ifadeler metinde
# gecerse dogrudan dogrulamayi deneyen bir kisayol eklendi (AL-002/005/006
# icin dogru sonuc verdi) AMA genis testte 2 GERCEK hallusinasyonu
# (KT-006, TF-001 kar_payi_orani_percent=0.0) YANLISLIKLA dogruladi -
# cunku "vade farksiz X taksit" (belirli bir taksit plani icin) ile "kar
# paysiz" (KT-006/TF-001'de baska bir alt urun/limit icin) ayni yuzeysel
# ifadeyi kullaniyor ama kampanyanin GENEL kar payi oranini ifade etmiyor.
# TF-001 somut ornek: "kar paysiz 2.500 TL'ye kadar yedek hesap finansman
# destegi" - bu, kampanyanin degil, belirli bir alt urunun ozelligi.
# Modulun ASIL amaci hallusinasyon yakalamaktir (bkz. dosya basi
# docstring); bu kisayol o amaci 6/6 (%100) -> 4/6 (%67) dusurdu - dogru
# deger bulma oranindaki kazanctan (%85,4 -> %97,6) daha agir bastigi
# icin GERI ALINDI. Bu, TOM-002/TOM-001 "ile sinirlidir" bulgusuyla AYNI
# kategori: insan etiketleyicinin kendisi bile bu yuzeysel kaliplar icin
# tutarli degil, basit anahtar-kelime esleme bunu guvenilir cozemez.

_BAGLAM_PENCERESI_KARAKTER = 60
# NOT: tek satir sonu (\n) SINIR SAYILMAZ. Scraper'in ham metin cikarimi
# (statik_scraper.py: get_text("\n", strip=True)) HER html blok elemani
# arasina \n koyar - bu, gercek cumle/nokta bitisi DEGIL, yalnizca HTML
# yapisidir (ör. "en fazla 1.500 tl\nkazanabilecektir." - ayni cumle iki
# satira bolunmus). \n'i sinir saymak, ZK-005/DK-002 gibi GERCEK dogru
# degerleri yanlislikla reddediyordu (olculdu, 9 Agustos 2026) - kaldirildi.

# DENENDI VE GERI ALINDI (9 Agustos 2026): TOM-002'deki "...kazanilabilecek
# iade 2.500 TL ile SINIRLIDIR" yanlis pozitifini yakalamak icin, sayinin
# yaninda "sinirli/maksimum/azami/en fazla" gecerse o gecisi gecersiz
# sayan bir kural denendi. TUM canli Altin Veri Seti odul_miktari
# kayitlarina (23 kayit) karsi test edildi: TOM-002'yi dogru yakaladi AMA
# 6 GERCEK DOGRU kaydi (ZK-005, ZK-007, DK-003, HF-001, HF-004, TOM-001)
# yanlislikla reddetti - cunku "en fazla X TL kazanabilirsiniz" gercek
# katilim bankasi metinlerinde odul_miktari'nin EN YAYGIN ifade bicimi.
# Carpici bir bulgu: TOM-001'in gold kaydinda BIREBIR AYNI cumle kalibi
# ("...ile sinirlidir") DOGRU kabul edilmis - yani insan etiketleyicinin
# kendisi de bu kalip icin TUTARLI degil (TOM-002'yi yanlis, TOM-001'i
# dogru saymis). Bu, basit bir kelime-dislama kuralinin bu ayrimi
# guvenilir sekilde yakalayamayacaginin kaniti - kural NET ZARARLI
# cikti (6 kirilma / 1 duzeltme) ve GERI ALINDI. TOM-002 durumu
# validation/verifier.py docstring'inde "bilinen sinir" olarak belgeli
# kalmaya devam ediyor.


def _cumle_penceresi(metin_kucuk: str, baslangic: int, bitis: int) -> str:
    """Sayinin etrafindaki baglam penceresini doner - ham karakter
    sayisiyla SINIRLI degil, ayrica en yakin cumle sinirinda (., !, ?)
    KIRPILIR. Tek satir sonu (\\n) sinir SAYILMAZ (bkz. yukaridaki sabit
    yorumu) - yalnizca gercek noktalama.

    NEDEN GEREKLI (gercek veriyle bulundu): '...taksit sayisinin 0
    olmasi gerekmektedir. Islemin vade farksiz...' - burada '0' ve
    'vade farksiz' ham karakter mesafesi olarak birbirine yakin ama IKI
    AYRI, ilgisiz cumlede (nokta ile ayrilmis). Sadece karakter penceresi
    bunu yanlislikla 'ayni baglamda' sayardi; cumle siniri bu tesadufi
    yakinligi keser."""
    onceki_sinir = max(
        (metin_kucuk.rfind(c, 0, baslangic) for c in ".!?"), default=-1
    )
    sonraki_adaylar = [metin_kucuk.find(c, bitis) for c in ".!?"]
    sonraki_adaylar = [k for k in sonraki_adaylar if k != -1]
    sonraki_sinir = min(sonraki_adaylar) if sonraki_adaylar else len(metin_kucuk)

    pencere_baslangic = max(onceki_sinir + 1, baslangic - _BAGLAM_PENCERESI_KARAKTER)
    pencere_bitis = min(sonraki_sinir, bitis + _BAGLAM_PENCERESI_KARAKTER)
    return metin_kucuk[pencere_baslangic:pencere_bitis]


@dataclass(frozen=True)
class DogrulamaSonucu:
    """Tek bir sayisal iddianin dogrulama sonucu."""

    alan_adi: str
    deger: float
    dogrulandi: bool
    # Sayi metinde hic gecmediyse bos; geciyorsa ama baglam kelimesi
    # yakininda YOKSA bu, "muhtemelen yanlis alana atanmis" sinyalidir
    # (bkz. modul docstring'i, KT-006 odul_miktari ornegi).
    sayi_metinde_bulundu_mu: bool
    denenen_varyantlar: list[str] = field(default_factory=list)


def _ondalikli_varyantlar(deger: float) -> set[str]:
    """1.89 -> {'1.89', '1,89', '1.9', '1,9', '2'} gibi virgul/nokta
    ondalik ve yuvarlama varyantlari uretir - Turkce kaynaklar virgul
    kullanir, bazi kaynaklar nokta kullanabilir."""
    varyantlar: set[str] = set()
    for basamak in (4, 2, 1, 0):
        yuvarlanmis = round(deger, basamak)
        s = f"{yuvarlanmis:g}"
        varyantlar.add(s)
        varyantlar.add(s.replace(".", ","))
    return varyantlar


def _tamsayi_varyantlari(deger: float) -> set[str]:
    """40000 -> {'40000', '40.000', '40,000'} - TR binlik ayiraci nokta,
    bazi kaynaklarda virgul olabilir."""
    n = int(round(deger))
    varyantlar = {str(n)}
    if abs(n) >= 1000:
        varyantlar.add(f"{n:,}".replace(",", "."))
        varyantlar.add(f"{n:,}")
    return varyantlar


def _buyukluk_ekli_varyantlar(deger: float) -> set[str]:
    """250000 -> {'250 bin'} - bazi kaynaklar binlik ayiracli rakam yerine
    kelime bazli buyukluk eki kullanir (ör. TOM-002: '250 Bin TL' -
    '250.000 TL' DEGIL). Yalnizca 1000'in TAM KATI olan degerler icin
    anlamli bir varyant uretilebilir (250500 icin '250,5 bin' gibi
    kesirli bir varyant uretmek karmasikligi hak etmiyor - bu depoda
    boyle bir gercek veri ornegi gorulmedi)."""
    n = int(round(deger))
    if n != 0 and n % 1000 == 0:
        return {f"{n // 1000} bin"}
    return set()


def sayisal_iddiayi_dogrula(alan_adi: str, deger: float, kaynak_metin: str) -> DogrulamaSonucu:
    """Bir cikarim alaninin (ör. kar_payi_orani_percent=1.89) kaynak
    metinde hem sayisal olarak hem de dogru BAGLAMDA gectigini dogrular.

    `alan_adi`, api/schemas.py::CampaignRecord'daki alan adiyla ayni
    olmalidir (baglam kelime sozlugu bu isimle eslestirilir). Bilinmeyen
    bir alan adi icin baglam kontrolu atlanir, yalnizca sayi aranir -
    sessizce yanlis "dogrulanamadi" DONMEZ (bu da bir tur veri
    gizleme/yaniltma olurdu)."""
    tam_sayi_mi = alan_adi in _TAMSAYI_ALANLAR
    varyantlar = sorted(
        (_tamsayi_varyantlari(deger) if tam_sayi_mi else (_ondalikli_varyantlar(deger) | _tamsayi_varyantlari(deger)))
        | _buyukluk_ekli_varyantlar(deger)
    )

    baglam_kelimeleri = _ALAN_BAGLAM_KELIMELERI.get(alan_adi)
    metin_kucuk = kaynak_metin.lower()

    sayi_bulundu = False
    baglamda_dogrulandi = False
    for varyant in varyantlar:
        # KELIME SINIRI SART: substring kontrolu ("0" in metin) tek
        # haneli/kucuk sayilarda neredeyse HER metinde tesadufen eslesir
        # (tarih, telefon, sayfa numarasi vb. icindeki rakamlar). \b ile
        # sayinin BAGIMSIZ bir token oldugu garanti edilir.
        desen = re.compile(r"(?<![\w.,])" + re.escape(varyant.lower()) + r"(?![\w.,])")
        # TUM gecisler kontrol edilir, yalnizca ILK degil - ayni sayi
        # metinde birden fazla yerde (farkli baglamlarda) gecebilir (bkz.
        # KT-006: "50.000" hem taksit ust siniri hem finansman tutari
        # cumlesinde geciyor, yalnizca ikincisi dogru baglami tasiyor).
        for eslesme in desen.finditer(metin_kucuk):
            sayi_bulundu = True
            if baglam_kelimeleri is None:
                # Alan icin baglam sozlugu tanimlanmamis - sayinin varligi
                # tek basina yeterli sayilir (bilinmeyen alanda daha katı
                # bir kural uydurmak keyfi olurdu).
                baglamda_dogrulandi = True
                break
            pencere = _cumle_penceresi(metin_kucuk, eslesme.start(), eslesme.end())
            if not any(kelime.lower() in pencere for kelime in baglam_kelimeleri):
                continue
            baglamda_dogrulandi = True
            break
        if baglamda_dogrulandi:
            break

    return DogrulamaSonucu(
        alan_adi=alan_adi,
        deger=deger,
        dogrulandi=baglamda_dogrulandi,
        sayi_metinde_bulundu_mu=sayi_bulundu,
        denenen_varyantlar=varyantlar,
    )


def kaydi_dogrula(alanlar: dict, kaynak_metin: str) -> dict[str, DogrulamaSonucu]:
    """Bir cikarim kaydindaki (regex/NER/LLM ciktisi ya da CampaignRecord)
    TUM bilinen sayisal alanlarini kaynak metne karsi dogrular.

    Deger None olan alanlar atlanir - "belirtilmemis" zaten dogrulanacak
    bir iddia tasimiyor (bkz. rapor Bolum 15 - eksik veri gizlenmez
    ilkesi, bu fonksiyon o ilkeyi BOZMAZ, yalnizca VAR OLAN iddialari
    dogrular)."""
    sonuclar: dict[str, DogrulamaSonucu] = {}
    for alan_adi in _ALAN_BAGLAM_KELIMELERI:
        deger = alanlar.get(alan_adi)
        if deger is None:
            continue
        sonuclar[alan_adi] = sayisal_iddiayi_dogrula(alan_adi, float(deger), kaynak_metin)
    return sonuclar

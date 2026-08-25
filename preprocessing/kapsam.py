"""Kampanya govdesini sayfa artiklarindan ayirir (kapsam kirlenmesi).

SORUN (olculdu, gercek veri): Bir kampanya sayfasinin metni yalnizca O
kampanyayi anlatmiyor - bazi bankalar sayfanin altina BASKA kampanyalarin
tanitim bloklarini ekliyor. Albaraka'nin "Vade Farksiz Kampanyasi"
sayfasinda (AL-001) sayfa sonunda su blok var:

    Kredi kartina vade farksiz taksit kampanyalari hakkinda detayli
    bilgi almak icin:
    Saglik Kampanyasi | Albaraka Turk
    "... 1.000 TL- 100.000 TL arasi saglik harcamalariniza ..."
    Egitim Kampanyasi | Albaraka Turk
    "... Egitim Harcamalarina Vade Farksiz 6 Taksit ..."

Bu blok BASKA kampanyalarin (AL-005/AL-006) tutarlarini iceriyor ve
cikarim motoru onlari BU kampanyanin tutari sanabiliyor. Olculdu:
AL-001'in finansman_tutari'ni 40.000 yerine 100.000 yapiyordu - ve
100.000 aslinda AL-005'in tutari.

IKINCI KALIP (T.O.M. Bank Hadi, 25 Agustos 2026 ile eklendi): "İlginizi
Çekebilir" basligiyla baslayan ve her biri "<Kampanya Basligi>" satirini
"Kampanya Detayı" satirinin izledigi bir liste. Ilk kalibin aksine bu
DAR KAPSAMLI DEGIL - 10/10 tombankhadi sayfasinda ayni sablon blok
(1500 TL hos geldin hediyesi, 12 taksit, %30 indirim gibi BASKA
kampanyalarin degerleri) tekrar ediyor; bankalar.json'daki eski "dar
kapsamli, ertelendi" notu bu olcumle GECERSIZ hale geldi (bkz. TOM-001/
007/008/010 yanlis pozitifleri, scraper/scripts/extraction_accuracy.py).

KAPSAM (durustluk notu): Ilk kalip (Albaraka) 234 belgenin yalnizca
1'inde var - sistemik degil. Ikinci kalip (tombankhadi) ise TUM
belgelerde var - sistemik. Ikisi de site sablonundan geldigi icin yeni
taramalarda tekrar cikar, bu yuzden kalici olarak ele alinir.

TASARIM - NEDEN DAR TUTULDU: Metin uzerinde "sayfa artigi" temizligi
kaygan bir zemindir; fazla genis bir kural gercek kampanya kosullarini
da siler. Bu yuzden yalnizca AKIS TETIKLEYICISI acik olan kaliplar ele
alinir: bilinen bir tetikleyici ifadeden SONRA gelen ve capraz kampanya
basligiyla devam eden blok. Baska hicbir sey silinmez.

DEGERLENDIRILDI, EKLENMEDI (25 Agustos 2026): Sayfa BASINDAKI breadcrumb/
menu satirlari ("Ana Sayfa", "Kampanyalar", kategori adi gibi kisa
satirlarin gercek basliktan once art arda gelmesi - bkz. KT-018,
DK-016, TOM-* sayfa baslari) da bir kapsam kirlenmesi bicimi. Ancak bu
metin BASLIK TESPITINE (kampanya_adi) zarar veriyor gibi gorunuyor,
sayisal alanlara degil: breadcrumb metninde tutar/oran/taksit sayisi
GECMIYOR, dolayisiyla extraction_accuracy.py'nin olctugu alanlarda
olcumu degistirmiyor (kampanya_adi zaten ALAN_ESLEME'de yok). Kisa
satirlari genel bir "N kisa satir + tekrar" kuraliyla kirpmak, bu
modulun kendi tasarim ilkesini (dar tetikleyici, tahmine dayali silme
yok) ihlal eder ve baska bankalarda gercek kisa giris cumlelerini
(ör. "Kampanya Detayları:") yanlislikla silme riski tasir - bu yuzden
simdilik EKLENMEDI. Olcumle desteklenen somut bir zarar (ör. kampanya_adi
alani da olcume girdiginde) bulunursa yeniden degerlendirilmeli.
"""

from __future__ import annotations

import re

# Her tetikleyici ifade, kampanyanin KENDI kosullarinin bittigini ve
# baska kampanyalara yonlendirmenin/tanitimin basladigini isaret eder.
# Tetikleyiciden sonraki birkac satirda DOGRULAYICI kalip da bulunmazsa
# (yani gercekten capraz kampanya listesi degilse) hicbir sey silinmez -
# bkz. modul docstring'i "TASARIM - NEDEN DAR TUTULDU".
_YONLENDIRME_KALIPLARI: list[tuple[re.Pattern[str], re.Pattern[str]]] = [
    (
        # "Kredi kartina ... kampanyalari hakkinda detayli bilgi almak icin:"
        re.compile(
            r"^[^\n]{0,120}?hakk[ıi]nda\s+detayl[ıi]\s+bilgi\s+almak\s+i[çc]in\s*:?\s*$",
            re.IGNORECASE,
        ),
        # "Saglik Kampanyasi | Albaraka Turk" - capraz kampanya baglantisi.
        re.compile(r"^[^|\n]{3,80}\|[^|\n]{3,40}$"),
    ),
    (
        # T.O.M. Bank Hadi "ilgili kampanyalar" widget basligi.
        re.compile(r"^İlginizi\s+[Çç]ekebilir$", re.IGNORECASE),
        # Widget'taki her capraz kampanya "Kampanya Detayı" satiriyla biter.
        re.compile(r"^Kampanya\s+Detay[ıi]$", re.IGNORECASE),
    ),
]

# Tetikleyici ifadenin ardindan dogrulayici kalibi ararken bakilacak
# satir sayisi. Gercek veride dogrulayici kalip birkac satir icinde
# geliyor; blogun tamami taranmaz.
_DOGRULAYICI_ARAMA_PENCERESI = 3


def kampanya_govdesini_ayikla(ham_metin: str) -> str:
    """Sayfa sonundaki "ilgili kampanyalar" tanitim blogunu kirpar.

    Blok bulunamazsa metin OLDUGU GIBI doner - bu fonksiyon hicbir
    kosulda "temizlik" adina icerik tahmin etmez.
    """
    if not ham_metin:
        return ham_metin

    satirlar = ham_metin.split("\n")

    for i, satir in enumerate(satirlar):
        temiz_satir = satir.strip()
        for tetikleyici, dogrulayici in _YONLENDIRME_KALIPLARI:
            if not tetikleyici.fullmatch(temiz_satir):
                continue

            # Tetikleyicinin ardindan gercekten capraz kampanya isareti
            # geliyor mu? Gelmiyorsa bu, kampanyanin kendi metninde gecen
            # masum bir cumledir - KESILMEZ.
            sonrasi = [
                s.strip()
                for s in satirlar[i + 1 : i + 1 + _DOGRULAYICI_ARAMA_PENCERESI]
                if s.strip()
            ]
            if any(dogrulayici.fullmatch(s) for s in sonrasi):
                return "\n".join(satirlar[:i]).rstrip()

    return ham_metin

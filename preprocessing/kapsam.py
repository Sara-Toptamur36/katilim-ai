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

KAPSAM (durustluk notu): 234 belgenin YALNIZCA 1'inde bu blok var. Yani
bu sistemik bir sorun DEGIL; yine de site sablonundan geldigi icin yeni
taramalarda tekrar cikacaktir, bu yuzden kalici olarak ele alinir.

TASARIM - NEDEN DAR TUTULDU: Metin uzerinde "sayfa artigi" temizligi
kaygan bir zemindir; fazla genis bir kural gercek kampanya kosullarini
da siler. Bu yuzden yalnizca AKIS TETIKLEYICISI acik olan tek bir kalip
ele alinir: "... hakkinda detayli bilgi almak icin:" ifadesinden SONRA
gelen ve capraz kampanya basligiyla ("Kampanya Adi | Banka Adi")
devam eden blok. Baska hicbir sey silinmez.
"""

from __future__ import annotations

import re

# "Kredi kartina ... kampanyalari hakkinda detayli bilgi almak icin:"
# Bu ifade, kampanyanin KENDI kosullarinin bittigini ve baska
# kampanyalara yonlendirmenin basladigini isaret eder.
_YONLENDIRME_BASLANGICI = re.compile(
    r"^[^\n]{0,120}?hakk[ıi]nda\s+detayl[ıi]\s+bilgi\s+almak\s+i[çc]in\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# "Saglik Kampanyasi | Albaraka Turk" - capraz kampanya baglantisi.
# Yonlendirme ifadesinden sonra bu bicimde EN AZ BIR satir gelmelidir;
# gelmiyorsa blok "ilgili kampanya listesi" degildir ve dokunulmaz.
_CAPRAZ_KAMPANYA_BASLIGI = re.compile(r"^[^|\n]{3,80}\|[^|\n]{3,40}$")

# Yonlendirme ifadesinden sonra capraz basligi ararken bakilacak satir
# sayisi. Gercek veride baslik hemen bir sonraki satirda geliyor; birkac
# satir pay birakilir ama blogun tamami taranmaz.
_BASLIK_ARAMA_PENCERESI = 3


def kampanya_govdesini_ayikla(ham_metin: str) -> str:
    """Sayfa sonundaki "ilgili kampanyalar" tanitim blogunu kirpar.

    Blok bulunamazsa metin OLDUGU GIBI doner - bu fonksiyon hicbir
    kosulda "temizlik" adina icerik tahmin etmez.
    """
    if not ham_metin:
        return ham_metin

    satirlar = ham_metin.split("\n")

    for i, satir in enumerate(satirlar):
        if not _YONLENDIRME_BASLANGICI.fullmatch(satir.strip()):
            continue

        # Yonlendirme ifadesinin ardindan gercekten capraz kampanya
        # basligi geliyor mu? Gelmiyorsa bu, kampanyanin kendi metninde
        # gecen masum bir cumledir - KESILMEZ.
        sonrasi = [s.strip() for s in satirlar[i + 1 : i + 1 + _BASLIK_ARAMA_PENCERESI] if s.strip()]
        if any(_CAPRAZ_KAMPANYA_BASLIGI.fullmatch(s) for s in sonrasi):
            return "\n".join(satirlar[:i]).rstrip()

    return ham_metin

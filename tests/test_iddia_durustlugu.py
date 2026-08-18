"""Iddia durustlugu bekcisi: "fine-tune ettik" demeyi engeller.

NEDEN TEST: Bu bir uslup tercihi degil, olculmus her seyin guvenilirligini
koruyan bir kural. "Qwen'i fine-tune ettik" cumlesi soylendigi anda juri
egitim verisini, train/val/test ayrimini, loss egrisini ve baseline
karsilastirmasini sorar - bu depoda hicbirinin cevabi yoktur, cunku
fine-tuning YAPILMADI (bkz. docs/kapsam_ve_veri_ayrimi.md).

NEDEN INSAN HATIRLATMASI YETMEZ: Video, sunum ve Md. 6 dokumanini dort
kisi ayri ayri yazacak. Planlama belgesindeki "dikkat edelim" notunu
kimse ikinci kez okumaz; CI okur.

KELIME DEGIL IDDIA ARANIYOR: "fine-tune" kelimesi depoda MESRU sekilde
geciyor - ornegin ner_extractor.py "bu checkpoint NER icin hic fine-tune
edilmemis" diyor. Bunlar dogruyu soyleyen OLUMSUZ cumlelerdir ve
serbesttir. Test yalnizca OLUMLU iddia kaliplarini yakalar.
"""

import os
import re
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent

# Taranan dosyalar: insanin yazdigi ve juriye giden her sey. Uretilen
# ciktilar (htmlcov, node_modules) ve ham veri disarida.
TARANAN_UZANTILAR = (".md", ".py")

# Nokta ile baslayan dizinlerin TAMAMI atlanir (arac/onbellek dizinleri).
# Tek tek adlandirmak yerine kural koymak, ileride eklenen bir arac
# dizininin sessizce taramaya girmesini de onler.
HARIC_DIZINLER = {
    "node_modules", "__pycache__", "htmlcov", "raw_data", "dist", "alembic",
}

# Olumlu iddia kaliplari.
#
# TASARIM: Desenler fiilin BIRINCI COGUL GECMIS ekini ("-dik/-tik") arar,
# yalin kokunu degil. Boylece "biz yaptik" iddiasi ile ucuncu bir modeli
# anlatan notr cumle ayrisir - ornegin ner_extractor.py'deki "model
# kisi/yer/kurum icin egitilmis" bir baskasinin modelini tarif eder,
# bizim iddiamiz degildir ve yanlis alarm uretmemelidir.
#
# BILINEN SINIR: Failin belirsiz oldugu edilgen cumleler ("model egitildi")
# BILEREK yakalanmaz. Ayni kalip hem bizim iddiamiz hem baska bir modelin
# tarifi olabildigi icin, otomatik ayirmak yanlis alarm uretirdi. Edilgen
# yazim zaten teslim metinlerinde kacinilmasi gereken bir uslup.
#
# Turkce eklerin hem sapkali hem duz yazimi kabul edilir ("yaptık"/"yaptik").
_BIZ_YAPTIK = r"(?:ettik|yaptık|yaptik|uyguladık|uyguladik|gerçekleştirdik|gerceklestirdik)"
_BIZ_URETTIK = (
    r"(?:eğittik|egittik|çıkardık|cikardik|ürettik|urettik|geliştirdik|gelistirdik)"
)

_IDDIA_DESENLERI = [
    # "fine-tune ettik", "fine-tuning yaptik", "finetune de uyguladik"
    rf"fine[\s\-]?tun\w*\s+(?:\S+\s+){{0,2}}?{_BIZ_YAPTIK}",
    # "fine-tuned modelimiz", "fine-tune edilmis modelimiz"
    r"fine[\s\-]?tun\w*\s+(?:\S+\s+){0,2}?model\w*(?:imiz|ımız)",
    # "modeli egittik", "modeli kendi verimizle egittik"
    r"model\w*\s+(?:\S+\s+){0,3}?(?:eğittik|egittik)",
    # "ince ayar yaptik/ettik"
    rf"ince\s+ayar\w*\s+(?:\S+\s+){{0,2}}?{_BIZ_YAPTIK}",
    # "kendi modelimizi egittik", "kendi NER modelimizi cikardik"
    rf"kendi\s+(?:\S+\s+){{0,3}}?model\w*\s+(?:\S+\s+){{0,2}}?{_BIZ_URETTIK}",
    # "egittigimiz model"
    r"(?:eğitt|egitt)(?:iğ|ig)imiz\s+model",
]

# Belge bu kurali ANLATTIGI icin kaliplari ornek olarak icerir; kendisini
# ihlal sayamayiz. Bekciyi test eden dosya da ayni durumda.
MUAF_DOSYALAR = {
    "docs/nasil_anlatiyoruz.md",
    "tests/test_iddia_durustlugu.py",
}

_DERLENMIS = [re.compile(d, re.IGNORECASE) for d in _IDDIA_DESENLERI]


def _taranacak_dosyalar() -> list[Path]:
    """Haric dizinleri GEZMEDEN dolasir.

    rglob("*") ile once dolasip sonra elemek, node_modules'un on binlerce
    dosyasina da girdigi icin bu testi tek basina 5 dakikaya cikariyordu.
    os.walk, dirnames'i yerinde budamaya izin verir.
    """
    dosyalar = []
    for kok, dizinler, adlar in os.walk(KOK):
        dizinler[:] = [
            d for d in dizinler
            if d not in HARIC_DIZINLER and not d.startswith(".")
        ]
        for ad in adlar:
            if not ad.endswith(TARANAN_UZANTILAR):
                continue
            yol = Path(kok) / ad
            if yol.relative_to(KOK).as_posix() in MUAF_DOSYALAR:
                continue
            dosyalar.append(yol)
    return dosyalar


def test_fine_tuning_iddiasi_hicbir_yerde_gecmiyor():
    """Depoda "fine-tune ettik" tarzi OLUMLU bir iddia bulunmamali."""
    bulgular: list[str] = []

    for yol in _taranacak_dosyalar():
        metin = yol.read_text(encoding="utf-8", errors="ignore")
        for desen in _DERLENMIS:
            for eslesme in desen.finditer(metin):
                satir_no = metin.count("\n", 0, eslesme.start()) + 1
                bulgular.append(
                    f"{yol.relative_to(KOK).as_posix()}:{satir_no} -> "
                    f"{eslesme.group(0).strip()!r}"
                )

    assert not bulgular, (
        "Egitim yapmadigimiz halde egitim iddia eden ifade(ler) bulundu.\n"
        "Dogru karsiligi icin: docs/nasil_anlatiyoruz.md, Bolum 4.\n"
        + "\n".join(bulgular)
    )


def test_bekci_gercek_iddiayi_yakaliyor():
    """Bekcinin kendisi calisiyor mu? Yakalamayan bir bekci, yesil
    gorunup hicbir sey korumaz - o yuzden yakaladigi kanitlanir."""
    ihlaller = [
        "Qwen'i fine-tune ettik ve sonuclari olctuk.",
        "Modeli kendi altin verimizle egittik.",
        "Bu turda ince ayar yaptik.",
        "Kendi NER modelimizi cikardik.",
        "Fine-tuned modelimiz baseline'i geciyor.",
        "Egittigimiz model canlida calisiyor.",
    ]
    for cumle in ihlaller:
        assert any(d.search(cumle) for d in _DERLENMIS), f"yakalanmadi: {cumle}"


@pytest.mark.parametrize(
    "cumle",
    [
        # Depoda GERCEKTEN gecen olumsuz ifadeler - yanlis alarm vermemeli.
        "bu checkpoint NER icin hic fine-tune edilmemis",
        "Bu depoda fine-tuning yoktur.",
        "Fine-tuning bilincli olarak yapilmadi.",
        "Gercek bir NER fine-tune'u denendiginde klasik varliklari buluyor",
        "model kisi/yer/kurum icin egitilmis, finansal alan icin degil",
    ],
)
def test_olumsuz_ifadeler_yanlis_alarm_vermiyor(cumle):
    """"Fine-tuning yapmadik" demek serbesttir - dogruyu soyler.
    Bekci kelimeyi degil IDDIAYI aradigi icin bunlar temiz gecmeli."""
    assert not any(d.search(cumle) for d in _DERLENMIS), f"yanlis alarm: {cumle}"

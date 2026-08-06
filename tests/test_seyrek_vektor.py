"""chunking/seyrek_vektor.py testleri (hibrit aramanin kelime tarafi).

Saf mantik - Qdrant/model GEREKTIRMEZ, CI'da her zaman calisir.
"""

import subprocess
import sys

from chunking.seyrek_vektor import (
    metni_tokenlara_ayir,
    seyrek_vektor_uret,
    terim_kimligi,
)


def test_turkce_buyuk_i_tokenlari_bozmaz():
    """'İ'.lower() bozuk karakter uretir - projede daha once uc ayri
    yerde bulunan hata."""
    assert "indirim" in metni_tokenlara_ayir("İNDİRİM fırsatı")


def test_etkisiz_kelimeler_elenir():
    tokenlar = metni_tokenlara_ayir("bu kampanya ve bir fırsat için")
    assert "ve" not in tokenlar
    assert "bir" not in tokenlar
    assert "kampanya" in tokenlar


def test_ayirt_edici_urun_adlari_korunur():
    """Worldpuan/ParafPara gibi banka-ozel terimler lexical aramanin
    en degerli sinyalleri - bozulmadan token olmali."""
    tokenlar = metni_tokenlara_ayir("Worldpuan ve ParafPara kazanın")
    assert "worldpuan" in tokenlar
    assert "parafpara" in tokenlar


def test_sayisal_bicimler_tek_token_kalir():
    """'%1,99' ve '98/2' ayirt edici terimlerdir - parcalanirsa
    ayirt ediciligini kaybeder."""
    tokenlar = metni_tokenlara_ayir("%1,99 oranla ve 98/2 paylaşım")
    assert "1,99" in tokenlar
    assert "98/2" in tokenlar


def test_terim_kimligi_ayni_surecte_kararli():
    assert terim_kimligi("kampanya") == terim_kimligi("kampanya")
    assert terim_kimligi("kampanya") != terim_kimligi("finansman")


def test_terim_kimligi_SURECLER_ARASI_kararli():
    """KRITIK: indeksleme ve sorgulama FARKLI sureclerde calisir.
    Python'un yerlesik hash()'i string'ler icin surecler arasi degisir
    (PYTHONHASHSEED) - bu kullanilsaydi indekslenen terim, sorguda
    baska bir kimlik alir ve lexical arama sessizce HIC eslesmezdi."""
    kod = (
        "import sys; sys.path.insert(0, '.');"
        "from chunking.seyrek_vektor import terim_kimligi;"
        "print(terim_kimligi('worldpuan'))"
    )
    ciktilar = set()
    for tohum in ("0", "1", "12345"):
        sonuc = subprocess.run(
            [sys.executable, "-c", kod],
            capture_output=True,
            text=True,
            env={"PYTHONHASHSEED": tohum, "PATH": ""},
        )
        ciktilar.add(sonuc.stdout.strip())

    assert len(ciktilar) == 1, f"Terim kimligi surecler arasi degisti: {ciktilar}"


def test_seyrek_vektor_indeks_ve_deger_sayisi_esit():
    indeksler, degerler = seyrek_vektor_uret("kampanya kapsamında finansman sağlanır")
    assert len(indeksler) == len(degerler)
    assert all(d > 0 for d in degerler)


def test_bos_metin_bos_vektor_uretir():
    assert seyrek_vektor_uret("") == ([], [])
    assert seyrek_vektor_uret("ve bir bu") == ([], [])


def test_tekrar_eden_terim_agirligi_artirir():
    _, tek = seyrek_vektor_uret("finansman")
    _, cok = seyrek_vektor_uret("finansman finansman finansman")
    assert max(cok) > max(tek)


def test_ekli_bicimler_ortak_govde_uzerinden_eslesir():
    """Turkce eklemeli: 'kampanyadan' ve 'kampanyaya' ayni koke ait.
    Govde oneki sayesinde ortak bir terim kimligi paylasmalilar."""
    i1, _ = seyrek_vektor_uret("kampanyadan")
    i2, _ = seyrek_vektor_uret("kampanyaya")
    assert set(i1) & set(i2), "Ekli bicimler hicbir terimi paylasmiyor"

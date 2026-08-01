"""ortak._encoding_duzelt testi.

Gercek senaryo (T.O.M. Katilim, Sprint 3): sunucu Content-Type basliginda
charset belirtmiyor ("text/html", "charset=..." yok). `requests`, HTTP
spesifikasyonu geregi boyle durumda ISO-8859-1'e duser - sayfa gercekte
UTF-8 olsa bile. Sonuc: Turkce karakterler sessizce bozulur
(ör. "Katılım" -> "KatÄ±lÄ±m"), rapor Bolum 23.1'deki "okurken olusan
bozulma" ornegi.

NOT: Bu testte konsola YAZDIRMA/print ile dogrulama YAPILMAZ - bu ortamda
Windows konsolunun kod sayfasi (cp1254) dogru UTF-8 metni bile yanlis
gosterebiliyor (bu proje boyunca birkac kez rastlandi). Yalnizca string
esitligi (==) ile, programatik olarak dogrulanir.
"""

import requests

from scraper.scripts.ortak import _encoding_duzelt

ORIJINAL_METIN = "Katılım Bankası kampanyası %1,89 oran ile 12 ay vade"


def _sahte_yanit(content_type: str, encoding: str | None) -> requests.Response:
    yanit = requests.models.Response()
    yanit._content = ORIJINAL_METIN.encode("utf-8")
    yanit.headers["Content-Type"] = content_type
    yanit.encoding = encoding
    return yanit


def test_charset_belirtilmemis_ise_encoding_duzeltilir():
    """T.O.M. senaryosu: Content-Type'ta charset yok, requests ISO-8859-1'e
    dusmus (bu, requests'in gercek HTTP fetch sirasinda yaptigi varsayilan
    atamadir - bkz. modul docstring)."""
    yanit = _sahte_yanit("text/html", "ISO-8859-1")

    assert yanit.text != ORIJINAL_METIN, "test kurulumu hatali: bozulma yoksa test anlamsiz"

    _encoding_duzelt(yanit)

    assert yanit.text == ORIJINAL_METIN


def test_charset_dogru_belirtilmisse_dokunulmaz():
    """Sunucu zaten dogru charset veriyorsa (cogunluk banka sayfasi gibi)
    _encoding_duzelt hicbir sey degistirmemeli."""
    yanit = _sahte_yanit("text/html; charset=utf-8", "utf-8")

    _encoding_duzelt(yanit)

    assert yanit.encoding == "utf-8"
    assert yanit.text == ORIJINAL_METIN


def test_content_type_hic_yoksa_da_calisir():
    yanit = _sahte_yanit("", "ISO-8859-1")
    yanit.headers.pop("Content-Type", None)

    _encoding_duzelt(yanit)

    assert yanit.text == ORIJINAL_METIN

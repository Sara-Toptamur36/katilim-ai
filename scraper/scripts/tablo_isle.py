"""HTML tablolarini yapilandirilmis veriye cevirir.

Rehber Bolum 18. Bankalar "Kâr Payı Oranları" ve "Ücret/Komisyon
Tarifeleri"ni cogunlukla <table> icinde verir. soup.get_text() bu
tabloyu duz metne cevirip hangi sayinin hangi urune ait oldugunu
kaybeder - bu modul tabloyu SUTUN/SATIR yapisini koruyarak JSON'a cevirir.
"""

from __future__ import annotations

from io import StringIO

import pandas as pd


def sayfadaki_tablolari_al(html_metni: str) -> list[pd.DataFrame]:
    """Sayfadaki tum HTML tablolarini pandas DataFrame listesine cevirir.
    Sayfada hic <table> yoksa bos liste doner (hata firlatmaz)."""
    try:
        return pd.read_html(StringIO(html_metni))
    except ValueError:
        return []


def _basligi_duzelt(tablo: pd.DataFrame) -> pd.DataFrame:
    """pd.read_html, sayfada <th> etiketi olmayan tablolarda sutun adlarini
    0,1,2... olarak numaralandirir - gercek baslik ilk SATIRA duser.
    Sutun adlarinin TAMAMI sayisalsa, ilk satiri baslik olarak yukselt."""
    if all(str(k).strip().isdigit() for k in tablo.columns) and len(tablo) > 1:
        yeni_baslik = [str(v).strip() for v in tablo.iloc[0]]
        tablo = tablo.iloc[1:].reset_index(drop=True)
        tablo.columns = yeni_baslik
    return tablo


def tablolari_json_yap(tablolar: list[pd.DataFrame]) -> list[dict]:
    """DataFrame listesini ham kayda eklenebilecek JSON-uyumlu bir yapiya
    cevirir. Tamamen bos satirlar atilir, sutun adlari metne cevrilir."""
    cikti: list[dict] = []
    for i, tablo in enumerate(tablolar):
        tablo = tablo.dropna(how="all")
        tablo.columns = [str(k).strip() for k in tablo.columns]
        tablo = _basligi_duzelt(tablo)
        cikti.append(
            {
                "tablo_index": i,
                "sutunlar": list(tablo.columns),
                "satirlar": tablo.to_dict(orient="records"),
            }
        )
    return cikti

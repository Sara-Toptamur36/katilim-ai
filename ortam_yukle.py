"""`.env` dosyasini process ortamina yukler - repodaki HER giris noktasinin
EN BASINDA import edilmesi gereken tek modul.

NEDEN GEREKLI (denetim bulgusu, 24 Agustos 2026): Depoda `python-dotenv`
hic kullanilmiyordu - ne `conftest.py` ne bir baslatma betigi `.env`
dosyasini okuyordu. `.env.ornek`'in kendisi "bu dosyayi .env olarak
kopyalayip duzenleyin" diyordu ama hicbir kod onu process ortamina
tasimiyordu; yani `.env`'e yazilan HER deger (KATILIMAI_PROFIL,
LLM_ZAMAN_ASIMI, EVREN_API_KEY, ...) sessizce goz ardi ediliyordu -
degisken gercekten set edilmeden `os.environ.get()` her zaman
varsayilana duserdi. Bu, rapor Bolum 5.6'nin tam uyardigi turden bir
sessiz basarisizlikti: hata firlamiyor, yalnizca .env'deki deger hicbir
zaman uygulanmiyordu.

KULLANIM - HER GIRIS NOKTASININ EN USTUNDE, BASKA HICBIR PROJE IMPORT'UNDAN
ONCE:
    import ortam_yukle  # noqa: F401 - side effect: .env process ortamina yuklenir
    import donanim
    ...

SIRALAMA NEDEN KRITIK: chunking/embedding.py, chunking/qdrant_baglanti.py
ve evren_istemci.py gibi modullerin bir kismi ortam degiskenlerini MODUL
IMPORT ANINDA okuyor (dosya basinda `X = os.environ.get(...)` seklinde,
fonksiyon icinde degil). Bu modul, onlar import edilmeden ONCE
cagirilmazsa, `.env`'deki degerler artik process ortamina yuklenmis olsa
bile o modullerin sabitleri eski (varsayilan) degerle donmus olur.

VARSAYILAN DEGERLERI EZMEZ: `override=False` (varsayilan) - process
ortaminda zaten set edilmis bir degisken (ornegin CI'daki GitHub Actions
Secret) `.env` dosyasindaki ayni isimli degerle SESSIZCE ezilmez.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

_ENV_YOLU = Path(__file__).resolve().parent / ".env"

# .env yoksa (CI'da, ya da henuz .env.ornek'ten kopyalanmadiysa) sessizce
# atlanir - load_dotenv() dosya bulunamadiginda hata firlatmaz, False doner.
load_dotenv(dotenv_path=_ENV_YOLU, override=False)

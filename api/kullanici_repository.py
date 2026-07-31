"""Kullanicilar tablosu icin veritabani erisim katmani.

api/kampanya_repository.py ile ayni ayrim ilkesi: DB sorgulari burada,
sifre dogrulama mantigi api/auth.py'de, HTTP/endpoint mantigi api/main.py'de.
"""

from sqlalchemy.orm import Session

from api.auth import sifre_dogrula, sifre_hashle
from api.models import Kullanici


def kullanici_getir(oturum: Session, kullanici_adi: str) -> Kullanici | None:
    return (
        oturum.query(Kullanici)
        .filter(Kullanici.kullanici_adi == kullanici_adi)
        .first()
    )


def kullanici_dogrula(oturum: Session, kullanici_adi: str, duz_sifre: str) -> Kullanici | None:
    """Kullanici adi/parola dogrularsa Kullanici kaydini, aksi halde None doner.

    GUVENLIK: Kullanici bulunamasa bile ayni "None" sonucu donulur -
    "kullanici yok" ile "parola yanlis" ayrimi disariya sizdirilmaz
    (kullanici adi enumeration saldirisini onler).
    """
    kullanici = kullanici_getir(oturum, kullanici_adi)
    if kullanici is None or not kullanici.aktif:
        return None
    if not sifre_dogrula(duz_sifre, kullanici.sifre_hash):
        return None
    return kullanici


def kullanici_olustur(
    oturum: Session, kullanici_adi: str, duz_sifre: str, rol: str = "banka_calisani"
) -> Kullanici:
    yeni = Kullanici(
        kullanici_adi=kullanici_adi,
        sifre_hash=sifre_hashle(duz_sifre),
        rol=rol,
    )
    oturum.add(yeni)
    oturum.commit()
    oturum.refresh(yeni)
    return yeni

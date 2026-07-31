"""Yeni kullanici olusturur (GERCEK_JWT_AKTIF=true oldugunda /token icin).

Kullanim:
    python -m api.scripts.kullanici_ekle

Parola terminalde GORUNMEZ (getpass) ve hicbir yerde duz metin olarak
saklanmaz - yalnizca bcrypt hash'i veritabanina yazilir.
"""

import getpass
import sys

from api.db import OturumYerel
from api.kullanici_repository import kullanici_getir, kullanici_olustur

GECERLI_ROLLER = ["banka_calisani", "denetleyici", "yonetici"]


def calistir() -> None:
    kullanici_adi = input("Kullanici adi: ").strip()
    if not kullanici_adi:
        print("Kullanici adi bos olamaz.")
        sys.exit(1)

    sifre = getpass.getpass("Parola: ")
    sifre_tekrar = getpass.getpass("Parola (tekrar): ")
    if sifre != sifre_tekrar:
        print("Parolalar eslesmedi.")
        sys.exit(1)
    if len(sifre) < 8:
        print("Parola en az 8 karakter olmali.")
        sys.exit(1)

    rol = input(f"Rol ({'/'.join(GECERLI_ROLLER)}) [banka_calisani]: ").strip() or "banka_calisani"
    if rol not in GECERLI_ROLLER:
        print(f"Gecersiz rol. Gecerli roller: {', '.join(GECERLI_ROLLER)}")
        sys.exit(1)

    oturum = OturumYerel()
    try:
        if kullanici_getir(oturum, kullanici_adi) is not None:
            print(f"'{kullanici_adi}' adinda bir kullanici zaten var.")
            sys.exit(1)
        kullanici_olustur(oturum, kullanici_adi, sifre, rol)
        print(f"Kullanici olusturuldu: {kullanici_adi} ({rol})")
    finally:
        oturum.close()


if __name__ == "__main__":
    calistir()

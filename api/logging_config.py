"""Merkezi loglama yapilandirmasi.

Kurumsal/on-premise bir sistemde print() kullanilmaz: cikti sunucu kapaninca
kaybolur, seviyesi ve zaman damgasi yoktur. Bu modul, hem dosyaya hem konsola
yazan seviyeli bir logger saglar.

GUVENLIK: Log dosyalarina asla token, parola, JWT gizli anahtari veya kisisel
veri yazilmaz. Loglar genelde daha az korunan yerlerde saklanir.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_KLASORU = "logs"
LOG_DOSYASI = os.path.join(LOG_KLASORU, "api.log")

_BICIM = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def logger_kur(isim: str = "katilimai") -> logging.Logger:
    """Verilen isimde, dosya + konsol yazan bir logger dondurur."""
    logger = logging.getLogger(isim)
    if logger.handlers:  # ayni logger iki kez kurulmasin
        return logger

    logger.setLevel(logging.INFO)
    bicim = logging.Formatter(_BICIM)

    os.makedirs(LOG_KLASORU, exist_ok=True)

    # 5 MB'i asinca yeni dosyaya gecer, son 5 dosyayi saklar
    dosya = RotatingFileHandler(
        LOG_DOSYASI, maxBytes=5_000_000, backupCount=5, encoding="utf-8"
    )
    dosya.setFormatter(bicim)
    logger.addHandler(dosya)

    konsol = logging.StreamHandler()
    konsol.setFormatter(bicim)
    logger.addHandler(konsol)

    return logger


log = logger_kur()

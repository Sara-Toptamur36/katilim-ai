"""Merkezi loglama yapilandirmasi.

Kurumsal/on-premise bir sistemde print() kullanilmaz: cikti sunucu kapaninca
kaybolur, seviyesi ve zaman damgasi yoktur. Bu modul, hem dosyaya hem konsola
yazan seviyeli bir logger saglar.

GUVENLIK: Log dosyalarina asla token, parola, JWT gizli anahtari veya kisisel
veri yazilmaz. Loglar genelde daha az korunan yerlerde saklanir.
"""

import json
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

LOG_KLASORU = "logs"
LOG_DOSYASI = os.path.join(LOG_KLASORU, "api.log")

class JsonFormatter(logging.Formatter):
    """Loglari yapilandirilmis JSON formatinda ciktilar."""
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        
        # Ek (extra) metrikler varsa JSON'a dahil et
        for key, value in record.__dict__.items():
            if key not in ["args", "asctime", "created", "exc_info", "exc_text", "filename",
                           "funcName", "id", "levelname", "levelno", "lineno", "module",
                           "msecs", "message", "msg", "name", "pathname", "process",
                           "processName", "relativeCreated", "stack_info", "thread", "threadName"]:
                log_record[key] = value

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)

def logger_kur(isim: str = "katilimai") -> logging.Logger:
    """Verilen isimde, dosya + konsol yazan yapilandirilmis (JSON) logger dondurur."""
    logger = logging.getLogger(isim)
    if logger.handlers:  # ayni logger iki kez kurulmasin
        return logger

    logger.setLevel(logging.INFO)
    bicim = JsonFormatter()

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

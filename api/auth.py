"""Kimlik dogrulama.

SPRINT 1-3 (su an): Mock dogrulama. Authorization header ZORUNLU ama icerigi
kontrol edilmez. Amac, Havin'in arayuzu ilk gunden dogru header formatiyla
kurmasi; boylece Sprint 4'te gercek JWT'ye gecerken arayuzde HICBIR degisiklik
gerekmez - yalnizca token'in degeri degisir.

SPRINT 4: Asagidaki `GERCEK_JWT_AKTIF` True yapilir; gizli anahtar ortam
degiskeninden okunur (KODA YAZILMAZ).
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Header, HTTPException

from api.logging_config import log

_BCRYPT_MAX_BAYT = 72  # bcrypt'in kendi siniri - daha uzun parolalar kesilir

# Sprint 4'te True yapilacak
GERCEK_JWT_AKTIF = os.environ.get("JWT_AKTIF", "false").lower() == "true"

ALGORITMA = "HS256"
TOKEN_OMRU_SAAT = 8


def _gizli_anahtar() -> str:
    """Gizli anahtar ASLA koda yazilmaz, ortam degiskeninden okunur."""
    anahtar = os.environ.get("JWT_SECRET")
    if not anahtar:
        raise RuntimeError(
            "JWT_SECRET ortam degiskeni tanimli degil. "
            "Gercek JWT icin bu deger zorunludur ve koda yazilmaz."
        )
    return anahtar


def sifre_hashle(duz_sifre: str) -> str:
    """Parolayi bcrypt ile hash'ler. Duz metin ASLA saklanmaz."""
    ham = duz_sifre.encode("utf-8")[:_BCRYPT_MAX_BAYT]
    return bcrypt.hashpw(ham, bcrypt.gensalt()).decode("utf-8")


def sifre_dogrula(duz_sifre: str, hash_deger: str) -> bool:
    """Girilen parolanin saklanan hash ile eslesip eslesmedigini kontrol eder."""
    ham = duz_sifre.encode("utf-8")[:_BCRYPT_MAX_BAYT]
    try:
        return bcrypt.checkpw(ham, hash_deger.encode("utf-8"))
    except ValueError:
        # Bozuk/gecersiz hash formati - guvenlik icin sessizce False
        return False


def token_uret(kullanici_adi: str, rol: str = "banka_calisani") -> str:
    """Sprint 4'te kullanilacak. Simdilik yalnizca test/hazirlik amacli."""
    from jose import jwt  # yerel import: mock modda bagimlilik gerekmesin

    veri = {
        "sub": kullanici_adi,
        "rol": rol,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_OMRU_SAAT),
    }
    return jwt.encode(veri, _gizli_anahtar(), algorithm=ALGORITMA)


def token_dogrula(authorization: str | None = Header(None)) -> dict:
    """FastAPI bagimliligi olarak kullanilir: Depends(token_dogrula).

    Donen sozluk: {"kullanici": ..., "rol": ...}
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header gerekli. Format: 'Bearer <token>'",
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Token bos olamaz")

    if not GERCEK_JWT_AKTIF:
        # --- MOCK MOD (Sprint 1-3) ---
        return {"kullanici": "mock_kullanici", "rol": "banka_calisani", "mock": True}

    # --- GERCEK MOD (Sprint 4) ---
    from jose import JWTError, jwt

    try:
        veri = jwt.decode(token, _gizli_anahtar(), algorithms=[ALGORITMA])
    except JWTError:
        log.warning("Gecersiz veya suresi dolmus token ile istek geldi")
        raise HTTPException(status_code=401, detail="Gecersiz veya suresi dolmus token")

    return {"kullanici": veri.get("sub"), "rol": veri.get("rol"), "mock": False}


def rol_gerekli(izinli_roller: list[str]):
    """RBAC (rapor Bolum 11). Ornek kullanim:

        @app.get("/audit/detay")
        def detay(k=Depends(rol_gerekli(["denetleyici", "yonetici"]))):
            ...
    """

    def kontrol(authorization: str | None = Header(None)) -> dict:
        kullanici = token_dogrula(authorization)
        if not GERCEK_JWT_AKTIF:
            return kullanici  # mock modda rol kontrolu yapilmaz
        if kullanici.get("rol") not in izinli_roller:
            raise HTTPException(status_code=403, detail="Bu islem icin yetkiniz yok")
        return kullanici

    return kontrol

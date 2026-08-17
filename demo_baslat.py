"""Tek komutla demo baslatma (E4).

AMAC: README'deki "Kurulum ve Calistirma" adimlari (docker compose up,
alembic upgrade, uvicorn) ayri ayri elle calistiriliyordu - jüri demosunda
ADIM ATLAMA veya SIRAYI KARISTIRMA riski vardi. Bu script backend
tarafini (arayuz haric - dashboard/Havin'in alani, ayri kalir) TEK
komutla, dogru sirayla, her adimin gercekten hazir oldugunu bekleyerek
ayaga kaldirir.

Kullanim:
    python demo_baslat.py              # gercek veriyle (GERCEK_VERI_AKTIF=true)
    python demo_baslat.py --mock       # mock veriyle, Docker/DB GEREKMEZ

Sonra ayrica (bu script tarafindan baslatilmaz - farkli runtime/ekip alani):
    cd dashboard && npm run dev
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

_BEKLEME_ZAMAN_ASIMI_SN = 60


def _adim(metin: str) -> None:
    print(f"\n==> {metin}")


def _docker_compose_ayaga_kaldir() -> bool:
    _adim("Docker servisleri baslatiliyor (postgres, qdrant, ollama)...")
    try:
        subprocess.run(["docker", "compose", "up", "-d"], check=True, timeout=120)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"HATA: docker compose up -d basarisiz ({type(e).__name__}: {e})")
        print("Docker Desktop acik mi? 'docker compose up -d' elle deneyin.")
        return False
    return True


def _servisin_hazir_olmasini_bekle(ad: str, kontrol_fonksiyonu) -> bool:
    baslangic = time.monotonic()
    while time.monotonic() - baslangic < _BEKLEME_ZAMAN_ASIMI_SN:
        try:
            if kontrol_fonksiyonu():
                print(f"  {ad}: HAZIR ({time.monotonic() - baslangic:.0f} sn)")
                return True
        except Exception:  # noqa: BLE001 - servis henuz ayakta degilken beklenen durum
            pass
        time.sleep(2)
    print(f"  {ad}: {_BEKLEME_ZAMAN_ASIMI_SN} sn icinde hazir olmadi")
    return False


def _servisleri_bekle() -> bool:
    _adim("Servislerin hazir olmasi bekleniyor...")

    from chunking.qdrant_baglanti import qdrant_hazir_mi

    def postgres_hazir_mi() -> bool:
        from api.db import engine
        with engine.connect():
            return True

    hepsi = [
        _servisin_hazir_olmasini_bekle("PostgreSQL", postgres_hazir_mi),
        _servisin_hazir_olmasini_bekle("Qdrant", qdrant_hazir_mi),
    ]
    return all(hepsi)


def _sema_guncelle() -> bool:
    _adim("Veritabani semasi guncelleniyor (alembic upgrade head)...")
    try:
        subprocess.run(["alembic", "upgrade", "head"], check=True, timeout=60)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"HATA: alembic upgrade head basarisiz ({type(e).__name__}: {e})")
        return False
    return True


def _api_baslat() -> None:
    # Gomme modelini acilista yukle (api/main.py::yasam_dongusu). Olculdu
    # (17 Agu): isitma olmadan surecin ILK /chat sorusu modeli yuklemek icin
    # 81 sn bekliyor ve arayuz zaman asimina ugruyordu - yani demoda ilk
    # soruyu soran juri uyesi hata goruyordu. Isitma bu bekleyisi buraya,
    # kimsenin beklemedigi acilisa tasir.
    os.environ["KATILIMAI_MODEL_ISIT"] = "true"

    _adim("API baslatiliyor -> http://localhost:8000/docs")
    print("Gomme modeli acilista yukleniyor (~1-1,5 dk); 'Application startup")
    print("complete' YAZANA KADAR soru sormayin.")
    print("(Durdurmak icin Ctrl+C. Arayuz icin AYRI bir terminalde: cd dashboard && npm run dev)\n")
    subprocess.run([sys.executable, "-m", "uvicorn", "api.main:app", "--reload"])


def main() -> None:
    ayristirici = argparse.ArgumentParser(description="KatilimAI backend'ini tek komutla baslatir")
    ayristirici.add_argument(
        "--mock", action="store_true",
        help="Mock veriyle calistir - Docker/PostgreSQL/Qdrant GEREKMEZ",
    )
    argumanlar = ayristirici.parse_args()

    if argumanlar.mock:
        print("Mock modu: Docker/DB adimlari atlaniyor, GERCEK_VERI_AKTIF ayarlanmiyor.")
        _api_baslat()
        return

    os.environ["GERCEK_VERI_AKTIF"] = "true"

    if not _docker_compose_ayaga_kaldir():
        sys.exit(1)
    if not _servisleri_bekle():
        print("\nBazi servisler zamaninda hazir olmadi - 'docker compose ps' ile kontrol edin.")
        sys.exit(1)
    if not _sema_guncelle():
        sys.exit(1)

    _api_baslat()


if __name__ == "__main__":
    main()

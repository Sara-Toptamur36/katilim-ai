"""EVREN cikarim altyapisina (TEKNOFEST 2026, evren-llmapi.ssyz.org.tr) OpenAI
uyumlu istemci sarmalayicisi.

NEDEN AYRI MODUL: extraction/llm_extractor.py (su ana kadar Ollama) ve
chunking/embedding.py (su ana kadar yerel sentence-transformers) ikisi de
EVREN'in sirasiyla llm-fast ve bge-m3-embed alias'ini kullanacagi icin
baglanti/hazirlik mantigi tek yerde toplanir - donanim.py'nin GPU/CPU
ayrimiyla AYNI gerekce: iki cagiran taraf ayni kodu kopyalamasin.

SAGLAYICI ANAHTARI (opsiyonel, EVREN_API_KEY yoksa hicbir sey degismez):
EVREN_API_KEY ortam degiskeni set EDILMEDIYSE bu modulun tum fonksiyonlari
aktif_mi()/hazir_mi() False doner ve cagiran taraf (llm_extractor.py /
embedding.py) YEREL yola (Ollama / sentence-transformers) duser - demonun
"internet gerekmiyor" ozelligi boylece korunur (bkz. docs/adr/0002).
EVREN'i ACIKCA istemek icin: EVREN_API_KEY (takima verilen sk-evren-teamNN-...
tokeni) .env dosyasina yazilir.

MODEL SECIMI (bkz. docs/adr/0002-evren-cikarim-entegrasyonu.md, olcumler
dokumantasyon.pdf'in kendi ozetledigi sonuclardan):
  - llm-fast: cikarim icin - JSON uretimi/siniflandirma/arac cagirma gibi
    "bicim agirlikli" gorevlerde llm-large ile olculmus fark YOK (5/5 gorev,
    1,000=1,000), medyan gecikme 0,91 sn (16 esdeger istekte 771,7 tok/s).
    llm-large'in one ciktigi yerler (kulturel/tarihi bilgi, video) bu
    projede yok.
  - bge-m3-embed: getirme icin - dokumantasyonun kendi olcumunde EN YUKSEK
    R@1 (0,95) bu sistemde bu modelde. Cikti boyutu SABIT 1024 - yerel
    multilingual-e5-base'in 768 boyutundan FARKLI, bu yuzden saglayici
    degistiginde Qdrant koleksiyonunun yeniden olusturulmasi gerekir
    (bkz. chunking/embedding.py, .env.ornek).
  - THINKING PARAMETRESI HIC GONDERILMEZ: varsayilan zaten kapali
    (dokumantasyon SS3.2 - acilmasi maliyet/kalite acisindan onerilmiyor,
    ayrica dusuk max_tokens ile SESSIZCE bos yanit donme riski tasiyor).
  - Hibrit getirme ve rerank BU ISTEMCIDEN CAGRILMAZ: dokumanin kendi
    olcumunde ikisi de saf yogun getirmenin altinda kaliyor (hibrit 0,85,
    rerank 0,55 vs 0,95 saf yogun) - bkz. ADR.

ZAMAN ASIMI: Sistem yigininin HER katmani (kenar/ag gecidi/model servisi)
1800 sn kullaniyor (dokumantasyon SS Mimari); istemci varsayilani (OpenAI
Python istemcisinde 600 sn) bu yuzden ACIKCA ezilir - aksi halde istemci
sunucudan once baglantiyi keser, istek sunucu tarafinda islenmeye devam
eder ama sonuc hic gorulmez (dokumantasyon Sorun Giderme SS "İstek takılı
görünüyor").
"""

from __future__ import annotations

import os
import time
from typing import Any, Optional

_BASE_URL = os.environ.get("EVREN_BASE_URL", "https://evren-llmapi.ssyz.org.tr/v1")
_API_KEY = os.environ.get("EVREN_API_KEY", "").strip()
_ZAMAN_ASIMI_SN = int(os.environ.get("EVREN_ZAMAN_ASIMI", "1800"))

# Alias adlari dogrudan dokumantasyondaki gibi - GET /v1/models ile
# dogrulanabilir. Bilinmeyen/bos bir alias sistem tarafinda SESSIZCE
# llm-fast'e yonlendiriliyor (dokumantasyon SS Model Kartlari), bu yuzden
# burada da varsayilan degerler ayni isimle sabitlendi.
LLM_MODELI = os.environ.get("EVREN_LLM_MODELI", "llm-fast")
EMBED_MODELI = os.environ.get("EVREN_EMBED_MODELI", "bge-m3-embed")
EMBED_BOYUTU = 1024  # bge-m3-embed sabit cikti boyutu (dokumantasyon Model Kartlari)

_istemci = None
_DURUM_CACHE: dict[str, Any] = {}
_DURUM_CACHE_SURESI_SN = 30.0


def aktif_mi() -> bool:
    """EVREN_API_KEY set edilmis mi?

    Servise gercekten ulasilabildigini SOYLEMEZ (onun icin hazir_mi()).
    Cagiran taraf (llm_extractor.py / embedding.py) bu fonksiyonu, takimin
    EVREN'i ACIKCA istedigini anlamak icin kullanir - anahtar yoksa yerel
    yola sessizce dusulur, EVREN opsiyoneldir ve bu bir hata durumu degildir.
    """
    return bool(_API_KEY)


def _istemciyi_al():
    global _istemci
    if _istemci is None:
        from openai import OpenAI

        _istemci = OpenAI(
            base_url=_BASE_URL,
            api_key=_API_KEY,
            timeout=_ZAMAN_ASIMI_SN,
            max_retries=0,  # yeniden deneme cagiran katmanda (kademeli fallback) yonetilir
        )
    return _istemci


def hazir_mi() -> bool:
    """EVREN servisine gercekten ulasilabiliyor mu (anahtar dogru mu, ag
    erisimi var mi)? extraction/llm_extractor.py::_ollama_hazir_mi ve
    chunking/qdrant_baglanti.py::qdrant_hazir_mi ile AYNI onbellek deseni -
    servis kapaliyken/anahtar yanlisken her cagrida ayri baglanti-hatasi
    beklemesi odenmesin diye 30 sn cache'lenir.
    """
    if not aktif_mi():
        return False
    simdi = time.monotonic()
    son = _DURUM_CACHE.get("zaman")
    if son is not None and (simdi - son) < _DURUM_CACHE_SURESI_SN:
        return bool(_DURUM_CACHE["hazir"])
    try:
        _istemciyi_al().models.list()
        hazir = True
    except Exception:  # noqa: BLE001 - herhangi bir baglanti/kimlik hatasinda yerel yola dus
        hazir = False
    _DURUM_CACHE["hazir"] = hazir
    _DURUM_CACHE["zaman"] = simdi
    return hazir


def sohbet_ile_sor(
    prompt: str,
    *,
    model: str = LLM_MODELI,
    max_tokens: int = 1024,
    response_format: Optional[dict] = None,
) -> Optional[str]:
    """Tek-turlu sohbet cagrisi, temperature=0 / top_p=1 (tekrarlanabilirlik
    icin - dokumantasyon SS13: kisa ve sema-kisitli ciktida bu ayarla
    olculen tekrarlanabilirlik %100).

    Baglanti/zaman asimi/kimlik hatasinda None doner - extraction/
    llm_extractor.py::llm_ile_sor() ile AYNI kademeli-fallback sozlesmesi:
    cagiran taraf None'i "bu katman sonuc vermedi" sayip bir onceki
    katmanla (regex/NER) veya yerel Ollama ile yetinir.

    `response_format` verilirse (ornegin {"type": "json_schema", ...,
    "strict": True}) cikti belirtilen semaya zorlanir - dokumantasyonun
    kendi ölçümünde bu, ayristirma hatasi riskini ortadan kaldiriyor
    (SS9/SS23). enable_thinking parametresi KESINLIKLE gonderilmez.
    """
    if not hazir_mi():
        return None
    try:
        kwargs: dict[str, Any] = dict(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.0,
            top_p=1.0,
        )
        if response_format is not None:
            kwargs["response_format"] = response_format
        yanit = _istemciyi_al().chat.completions.create(**kwargs)
        return yanit.choices[0].message.content
    except Exception:  # noqa: BLE001 - kademeli fallback: hata firlatilmaz
        return None


def gomme_al(metinler: list[str], *, model: str = EMBED_MODELI) -> Optional[list[list[float]]]:
    """Yogun gomme vektorleri (bge-m3-embed varsayilan, cikti boyutu sabit
    1024). Baglanti/kimlik hatasinda None doner - chunking/embedding.py
    cagiran taraf bunu "EVREN yolu basarisiz, yerel modele dus" sinyali
    olarak kullanir; boylelikle embedding hicbir zaman sessizce durmaz.
    """
    if not hazir_mi():
        return None
    try:
        yanit = _istemciyi_al().embeddings.create(model=model, input=metinler)
        return [d.embedding for d in yanit.data]
    except Exception:  # noqa: BLE001
        return None


def ozet() -> str:
    """Tanilama ciktisi - donanim_testi.py'nin cikardigi ozetle ayni ruhta:
    hangi saglayicinin aktif oldugu tek bakista gorulsun."""
    if not aktif_mi():
        return "EVREN            : pasif (EVREN_API_KEY tanimli degil, yerel yol kullanilacak)"
    durum = "erisilebilir" if hazir_mi() else "ANAHTAR VAR AMA ERISILEMIYOR (ag/anahtar kontrol edin)"
    return (
        f"EVREN            : aktif ({durum})\n"
        f"  base_url       : {_BASE_URL}\n"
        f"  llm modeli     : {LLM_MODELI}\n"
        f"  embed modeli   : {EMBED_MODELI} ({EMBED_BOYUTU} boyut)"
    )


if __name__ == "__main__":
    print(ozet())

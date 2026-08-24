"""EVREN istemci iskeleti - TEKNOFEST'in sagladigi paylasimli bulut
cikarim altyapisina (evren-llmapi.ssyz.org.tr / evren-vektor.ssyz.org.tr)
baglanti katmani.

KAPSAM SINIRI - BUNU OKUMADAN KULLANMAYIN:
Bu modul hicbir production yoluna (extraction/, chunking/, agent/, api/)
BAGLI DEGILDIR ve baglanmamalidir. Sartname Md. 5.9 (on-premise) projenin
%20 agirlikli bir degerlendirme kriteri ve mevcut mimari (Ollama + yerel
Qdrant + GLiNER) bilerek internetsiz calisacak sekilde kurulmustur (bkz.
README "Tasarim Ilkeleri" ve extraction/llm_extractor.py'deki tokenizer
notu). EVREN, TEKNOFEST'in ekibe verdigi ek bir arac; on-premise motorun
yerini almaz. Bu dosya yalnizca iskelettir - hangi is akislarinda (varsa)
kullanilacagi ayri bir karar ve ayri bir degisiklikle netlestirilecektir.

Dogrulanmis (dokumantasyon.pdf) davranis notlari - kod bunlara gore yazildi:
  - Istemci zaman asimi 1800 sn olmali; OpenAI istemcisinin varsayilani
    (600 sn) sunucudan once baglantiyi keser, istek sunucuda islenmeye
    devam eder ama sonuc goruntulenemez.
  - Bilinmeyen/bos model adi hata DONDURMEZ, sessizce llm-fast'e yonlenir
    - bu yuzden model adi GET /v1/models'e karsi dogrulanmadan
    guvenilmemeli.
  - Qdrant istemcisinde port=443 ACIKCA verilmezse istemci kendi
    varsayilan portuna yonelir ve "Connection refused" alinir; prefix
    (takim kodu) verilmezse 404 alinir. Ikisi de bu dosyada sabitlenmistir.
  - rerank servisi olcumde getirme kalitesini dusurmustur (R@1 0,95 -> 0,55)
    - kullanilacaksa bilerek ve ayrica degerlendirilerek kullanilmalidir.

Kurulum:
    pip install -r requirements.txt   # openai artik icinde
    export EVREN_API_KEY="sk-evren-teamNN-..."
    export EVREN_QDRANT_KEY="qdr-teamNN-..."
    export EVREN_TEAM="teamNN"
"""

from __future__ import annotations

import os

# --- Sabit adresler (dokumantasyon.pdf SS2 "Kimlik dogrulama") ---
LLM_BASE_URL = "https://evren-llmapi.ssyz.org.tr/v1"
QDRANT_URL = "https://evren-vektor.ssyz.org.tr"
QDRANT_PORT = 443  # ZORUNLU - qdrant-client bunu URL'den cikaramaz.

# Sistemin her katmani (kenar/ag gecidi/model servisi) bu degeri kullanir;
# istemci tarafinda daha kisa bir sure baglantiyi modelden once keser.
ISTEK_ZAMAN_ASIMI_SN = 1800

# --- Model aliaslari (Model Kartlari sayfasi) ---
# Kullanim onerileri dokumantasyondaki olculmus sonuclara dayanir; tahmin
# degildir. 2. Senaryo (katilim bankaciligi) icin onerilenler: LLM_FAST
# (sema kisitli cikarim) ve BGE_M3_EMBED (getirme).
LLM_FAST = "llm-fast"      # belge okuma, siniflandirma, JSON, arac cagirma
LLM_LARGE = "llm-large"    # kulturel/tarihsel bilgi, uzun akil yurutme
VLM = "vlm"                # yalnizca video, goruntu kabul etmez (400 doner)
ROUTER = "router"          # hafif siniflandirma / yonlendirme
GUARD = "guard"            # icerik guvenligi siniflandirmasi
EMBED = "embed"            # yogun gomme, 2560 boyut, R@3=1.00
BGE_M3_EMBED = "bge-m3-embed"    # yogun gomme, 1024 boyut, R@1=0.95 (en yuksek ilk-isabet)
BGE_M3_SPARSE = "bge-m3-sparse"  # yalnizca /pooling, FlagEmbedding'den FARKLI cikti sekli
BGE_M3_COLBERT = "bge-m3-colbert"  # yalnizca /pooling, cok-vektor
# ONERILMEZ: olcumde yogun getirmenin uzerine eklendiginde R@1 0.95 -> 0.55
# dusurmustur (Model Rehberi SS10). Bilerek ve ayrica dogrulanmadan
# kullanilmamalidir.
RERANK = "rerank"


def api_anahtari_var_mi() -> bool:
    """EVREN_API_KEY ortam degiskeni tanimli mi? Baglanti denemeden once
    hizli bir on kontrol - Ollama/Qdrant'taki hazir_mi() desenlerinden
    farkli olarak burada bir servise HTTP istegi ATILMAZ (EVREN kota
    uygulamiyor ama paylasimli kuyruk var; gereksiz bir "durum" cagrisi
    kuyruga bosuna yuk bindirir)."""
    return bool(os.environ.get("EVREN_API_KEY", "").strip())


_istemci = None


def istemci_al():
    """OpenAI-uyumlu EVREN istemcisini (tembel, tek ornek) doner.

    EVREN_API_KEY tanimli degilse RuntimeError firlatir - bu, Ollama
    icin kullanilan "sessizce None don" desenden BILEREK farklidir:
    EVREN, production'daki bir kademeli-fallback zinciri degil, bilerek
    cagrilan yardimci bir arac; eksik kimlik bilgisiyle sessizce
    calismamis olmak, hangi katmanin cevap verdigini belirsizlestirir.
    """
    global _istemci
    if _istemci is None:
        anahtar = os.environ.get("EVREN_API_KEY", "").strip()
        if not anahtar:
            raise RuntimeError(
                "EVREN_API_KEY tanimli degil. export EVREN_API_KEY=\"sk-evren-teamNN-...\""
            )
        from openai import OpenAI

        _istemci = OpenAI(
            base_url=LLM_BASE_URL,
            api_key=anahtar,
            timeout=ISTEK_ZAMAN_ASIMI_SN,
            max_retries=0,  # yeniden deneme cagiran tarafta yonetilmeli (gecici/kalici hata ayrimi icin)
        )
    return _istemci


_qdrant_istemci = None


def qdrant_istemci_al():
    """Takima izole EVREN Qdrant ornegine (tembel, tek ornek) baglanir.

    port=443 ve prefix (takim kodu) ACIKCA verilir - dokumantasyonda
    belirtildigi gibi ikisi de atlanirsa sirasiyla "Connection refused"
    ve 404 ile sonuclanir, hata mesaji kok nedeni belirtmez.
    """
    global _qdrant_istemci
    if _qdrant_istemci is None:
        qdr_anahtar = os.environ.get("EVREN_QDRANT_KEY", "").strip()
        takim = os.environ.get("EVREN_TEAM", "").strip()
        if not qdr_anahtar or not takim:
            raise RuntimeError(
                "EVREN_QDRANT_KEY ve EVREN_TEAM tanimli olmali. "
                'export EVREN_QDRANT_KEY="qdr-teamNN-..." ve export EVREN_TEAM="teamNN"'
            )
        from qdrant_client import QdrantClient

        _qdrant_istemci = QdrantClient(
            url=QDRANT_URL,
            port=QDRANT_PORT,
            prefix=takim,
            api_key=qdr_anahtar,
            timeout=600,
            prefer_grpc=False,  # gRPC bu kurulumda desteklenmiyor (yol oneki yonlendirmesi)
        )
    return _qdrant_istemci

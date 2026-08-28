"""Metinleri vektore ceviren embedding katmani (RAG icin ilk adim).

IKI SAGLAYICI (bkz. docs/adr/0002-evren-cikarim-entegrasyonu.md):
  - Yerel intfloat/multilingual-e5-base - VARSAYILAN yol, 768 boyutlu
    vektor uretir. EVREN_API_KEY tanimli olsa BILE (ornegin yalnizca
    llm-fast icin eklenmis olabilir) embedding burada KALIR.
  - EVREN (evren_istemci.py, bge-m3-embed alias) - yalnizca
    evren_istemci.gomme_aktif_mi() True ise (EVREN_API_KEY VE ACIKCA
    EVREN_EMBED_KULLAN=true) devreye girer; cikti boyutu SABIT 1024.
    GUNCELLEME (25 Agustos 2026, gercek anahtarla olculdu - bkz. docs/
    rag_tasarim_ve_olcum.md Bulgu 14): dokumantasyonun genel test
    setindeki R@1=0,95 bu projenin Turkce korpusuna GENELLENMEDI - gercek
    olcumde bge-m3-embed yerel e5-base'in ALTINDA kaldi (Genel Recall@5
    %87,60 -> %83,72). Bu yuzden aktif_mi() (EVREN_API_KEY VAR MI) ile
    gomme_aktif_mi() (EMBEDDING FIILEN EVREN Mİ) artik BILINCLI OLARAK
    AYRI sorular - ilki extraction/llm_extractor.py'nin cevapladigi soru,
    ikincisi bu dosyanin.

KRITIK - VEKTOR BOYUTU SAGLAYICIYA GORE DEGISIR: EVREN (1024) ve yerel
model (768) AYNI Qdrant koleksiyonuna yazilamaz - boyut degistiginde
koleksiyonun `sifirla=True` ile yeniden olusturulup TUM korpusun yeniden
indekslenmesi gerekir (bkz. chunking/qdrant_baglanti.py::koleksiyon_hazirla,
.env.ornek). VEKTOR_BOYUTU bu yuzden gomme_aktif_mi() true ise otomatik
1024 secilir - EMBEDDING_BOYUTU ortam degiskeni yine de ELLE EZEBILIR.

MODEL SECIMI - yerel yol icin intfloat/multilingual-e5-base:
  - Cok dilli, Turkce destegi guclu; 768 boyutlu vektor uretir.
  - ~1.1 GB - bge-m3'e (~2.3 GB) gore juri demo makinesinde cok daha hafif.
  - Model adi ORTAM DEGISKENIYLE degistirilebilir (EMBEDDING_MODELI), boylece
    NLP tarafi (Yagmur) baska bir modele gecmek isterse kod degismez;
    yalnizca VEKTOR_BOYUTU'nun yeni modelle uyusmasi gerekir.

E5 MODELLERININ ONEK KURALI (kritik, YALNIZCA yerel yolda gecerli):
  e5 ailesi, egitim sirasinda her metnin basina bir gorev oneki almistir:
  aranan metin "query: ", indekslenen belge "passage: " ile baslar. Bu onek
  ATLANIRSA model calismaya devam eder ama benzerlik skorlari belirgin
  sekilde bozulur - sessiz bir kalite kaybidir. Bu yuzden onek burada
  ZORUNLU tutuldu: `belgeleri_vektore_cevir` ve `sorguyu_vektore_cevir`
  ayri fonksiyonlardir, cagiran tarafin oneki hatirlamasi gerekmez.
  bge-m3-embed (EVREN) boyle bir onek beklemez, bu yuzden EVREN yolunda
  onek hic eklenmez.

PERFORMANS (bu depoda olculdu, GPU'suz makine, yerel yol):
  ilk model yuklemesi ~12 sn (tek seferlik), 20 metnin toplu encode'u
  ~0.9 sn. Yani embedding, LLM cikarimindan (bkz. extraction/llm_extractor.py
  zaman asimi notu: 150-300+ sn) COK daha ucuzdur ve RAG icin darbogaz
  degildir.
"""

from __future__ import annotations

import os
from typing import Optional

import evren_istemci

MODEL_ADI = os.environ.get("EMBEDDING_MODELI", "intfloat/multilingual-e5-base")
_VARSAYILAN_BOYUT = evren_istemci.EMBED_BOYUTU if evren_istemci.gomme_aktif_mi() else 768
VEKTOR_BOYUTU = int(os.environ.get("EMBEDDING_BOYUTU", str(_VARSAYILAN_BOYUT)))

_model = None


def modeli_yukle():
    """Modeli ILK cagrida yukler (tembel yukleme).

    ner_extractor.py ile ayni gerekce: modul import edildigi anda ~1 GB'lik
    bir model yuklemek, embedding'e hic dokunmayan testleri/servisleri de
    yavaslatirdi.
    """
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_ADI, model_kwargs={"use_safetensors": False})
    return _model


def _vektore_cevir(metinler: list[str], onek: str) -> list[list[float]]:
    if evren_istemci.gomme_aktif_mi():
        # EVREN aktifken yerel modele SESSIZCE dusulmez: bge-m3-embed 1024,
        # yerel e5-base 768 boyutlu vektor uretir - ayni koleksiyona karisik
        # boyutta vektor yazmak indeksi bozar (bkz. modul basi dokstring).
        # Boyle bir hata "belge bulunamadi" gibi sessiz bir RAG basarisizligi
        # olarak degil, acikca firlatilir (rapor 5.6: en tehlikeli hata turu
        # sessiz basarisizliktir).
        vektorler = evren_istemci.gomme_al(metinler)
        if vektorler is None:
            raise RuntimeError(
                "EVREN_API_KEY tanimli ama bge-m3-embed'e ulasilamadi "
                "(agi/anahtari kontrol edin). Yerel modele otomatik "
                "dusulmuyor - boyut uyumsuzlugu Qdrant indeksini bozar."
            )
        return vektorler
    model = modeli_yukle()
    onekli = [f"{onek}{m}" for m in metinler]
    vektorler = model.encode(onekli, normalize_embeddings=True)
    return [v.tolist() for v in vektorler]


def belgeleri_vektore_cevir(metinler: list[str]) -> list[list[float]]:
    """Indekslenecek belge parcalari icin ('passage: ' oneki)."""
    return _vektore_cevir(metinler, "passage: ")


def sorguyu_vektore_cevir(sorgu: str) -> list[float]:
    """Kullanici sorusu icin ('query: ' oneki)."""
    return _vektore_cevir([sorgu], "query: ")[0]


def model_hazir_mi() -> Optional[str]:
    """Embedding kaynagi hazir mi? Hazirsa None, aksi halde hata metni
    doner (test/spike'larin anlamli sekilde atlanabilmesi icin - ornegin
    yerel model hic indirilmemisse ve internet yoksa, ya da EVREN aktifse
    ama erisilemiyorsa)."""
    if evren_istemci.gomme_aktif_mi():
        if evren_istemci.hazir_mi():
            return None
        return "EVREN_API_KEY tanimli ama evren-llmapi.ssyz.org.tr'a ulasilamadi"
    try:
        modeli_yukle()
        return None
    except Exception as e:  # noqa: BLE001 - hata TURU degil, mesaji onemli
        return f"{type(e).__name__}: {e}"

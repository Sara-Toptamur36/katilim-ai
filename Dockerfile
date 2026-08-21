# KatilimAI API imaji.
#
# --------------------------------------------------------------------------
# NEDEN COK ASAMALI
# --------------------------------------------------------------------------
# torch + transformers + gliner derlenirken derleyici/gelistirme basliklari
# gerekiyor ama CALISMA zamaninda gerekmiyor. Tek asamali bir imaj bu
# araclari da tasirdi - gereksiz yuz megabaytlar ve gereksiz saldiri yuzeyi.
#
# --------------------------------------------------------------------------
# SURUM SABITLEME
# --------------------------------------------------------------------------
# Taban imaj DIGEST ile sabitlenir, etiketle degil: "python:3.12-slim"
# etiketi zamanla BASKA bir imaji gosterir ve ayni Dockerfile farkli
# sonuc uretir. Yeniden uretilebilirlik, requirements.txt'teki `==`
# disiplinin imaj tarafindaki karsiligidir.
#
# --------------------------------------------------------------------------
# MODELLER IMAJA GOMULMEZ
# --------------------------------------------------------------------------
# Gomme modeli (~1 GB) ve GLiNER imaja KONULMAZ; calisma aninda indirilip
# HF_HOME hacminde onbelleklenir. Sebep: imaji 3 GB'a cikarirlar ve model
# surumu degistiginde imajin tamami yeniden uretilmek zorunda kalir.
# CEVRIMDISI DEMO icin modeller onceden indirilmis bir hacim baglanir
# (bkz. README "Cevrimdisi hazirlik kontrolu").

FROM python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a AS derleme

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# psycopg[binary] tekerlekli gelir ama bazi bagimliliklar kaynak derliyor.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /derleme
COPY requirements.txt .

# TORCH ONCE, CPU DEPOSUNDAN.
#
# OLCULDU (21 Agustos, ilk imaj denemesi): varsayilan PyPI deposu torch'un
# CUDA surumunu getiriyor - 532 MB torch + 366 MB nvidia_cudnn + diger
# NVIDIA paketleri, toplam ~2 GB. API konteynerinde GPU YOKTUR; bu
# kutuphaneler hic calistirilmaz, yalnizca imaji sisirir ve indirme
# suresini dakikalarca uzatir.
#
# Torch'u CPU deposundan ONCE kurmak, sonraki `-r requirements.txt`
# adiminda pip'in onu "zaten karsilanmis" saymasini saglar - surum yine
# requirements.txt'teki `==` ile ayni kalir, yalnizca yapisi CPU olur.
#
# BU KARAR GPU CALISMASINI ENGELLEMEZ. Degistirilen yer YALNIZCA bu imaj;
# requirements.txt'e DOKUNULMADI. GPU'lu makinede `pip install -r
# requirements.txt` yine CUDA surumunu getirir ve agir isler (ablation
# kosusu, toplu indeksleme) orada DOGRUDAN calistirilir - bu imaj
# uzerinden degil. Ollama'nin GPU erisimi ayri bir dosyadadir:
# docker-compose.gpu.yml.
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install --index-url https://download.pytorch.org/whl/cpu \
        "torch==$(grep -oP '^torch==\K.*' requirements.txt)" \
    && /opt/venv/bin/pip install -r requirements.txt


# --------------------------------------------------------------------------
FROM python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a AS calisma

# ROOT DEGIL: konteyner kacisi durumunda ayricalik kazanimini sinirlar.
RUN useradd --create-home --uid 10001 katilimai

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/onbellek/hf

COPY --from=derleme /opt/venv /opt/venv

WORKDIR /uygulama
COPY --chown=katilimai:katilimai . .

# Model onbellegi HACIM olarak baglanir - imaja yazilmaz (bkz. dosya basi).
#
# `logs/` DIZINI DE BURADA ACILIR. Ilk imaj denemesinde konteyner
# `PermissionError: [Errno 13] Permission denied: 'logs'` ile aciliste
# COKTU: api/logging_config.py import aninda `os.makedirs("logs")`
# cagiriyor, ama (1) .dockerignore `logs` dizinini imaja almiyor,
# (2) WORKDIR'i Docker root olarak yaratiyor - `COPY --chown` yalnizca
# KOPYALANAN dosyalarin sahibini degistirir, dizinin kendisininkini
# degil. Dolayisiyla katilimai kullanicisi orada klasor acamiyordu.
RUN mkdir -p /onbellek/hf /uygulama/logs \
    && chown -R katilimai:katilimai /onbellek /uygulama

USER katilimai
EXPOSE 8000

# Saglik kontrolu, uygulamanin KENDI ucunu kullanir - "surec ayakta mi"
# degil "istegi cevapliyor mu" olculur. Gomme modeli isitmasi acikken
# acilis ~1,5 dk surdugu icin start-period genis tutuldu (olculdu:
# 81 sn, bkz. api/main.py::yasam_dongusu).
HEALTHCHECK --interval=30s --timeout=5s --start-period=150s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/saglik', timeout=4).status==200 else 1)"

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

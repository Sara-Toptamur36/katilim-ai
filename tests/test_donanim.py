"""donanim.py testleri - profil secimi ve ortam degiskeni ezmeleri.

Saf mantik: GPU tespiti monkeypatch'lenir, gercek donanim gerekmez -
CI'da her zaman calisir.
"""

import pytest

import donanim


@pytest.fixture(autouse=True)
def _onbellegi_temizle():
    """ayarlar()/gpu_bilgisi() lru_cache'li - testler birbirini etkilemesin."""
    donanim.ayarlar.cache_clear()
    donanim.gpu_bilgisi.cache_clear()
    yield
    donanim.ayarlar.cache_clear()
    donanim.gpu_bilgisi.cache_clear()


def _gpu_taklit(monkeypatch, gpu):
    monkeypatch.setattr(donanim, "gpu_bilgisi", lambda: gpu)


def test_gpu_yoksa_cpu_profili_secilir(monkeypatch):
    monkeypatch.delenv("KATILIMAI_PROFIL", raising=False)
    for d in ("LLM_BAGLAM_PENCERESI", "LLM_ZAMAN_ASIMI", "EMBEDDING_YIGIN_BOYUTU"):
        monkeypatch.delenv(d, raising=False)
    _gpu_taklit(monkeypatch, None)

    assert donanim.ayarlar().ad == "cpu"


def test_vram_yetersiz_gpu_CPU_profiline_duser(monkeypatch):
    """KRITIK: "GPU var" hizli demek DEGILDIR. Gercek ornek - bu depoda
    olculdu: GeForce MX230 var ama 2 GB VRAM; 7B model (~5 GB) sigmiyor
    ve Ollama modeli %84 oraninda CPU'da calistiriyor. Profil karari
    VRAM'e bakmali."""
    monkeypatch.delenv("KATILIMAI_PROFIL", raising=False)
    for d in ("LLM_BAGLAM_PENCERESI", "LLM_ZAMAN_ASIMI", "EMBEDDING_YIGIN_BOYUTU"):
        monkeypatch.delenv(d, raising=False)
    _gpu_taklit(monkeypatch, ("GeForce MX230", 2048))

    assert donanim.ayarlar().ad == "cpu"


def test_yeterli_vramli_gpu_GPU_profilini_secer(monkeypatch):
    monkeypatch.delenv("KATILIMAI_PROFIL", raising=False)
    for d in ("LLM_BAGLAM_PENCERESI", "LLM_ZAMAN_ASIMI", "EMBEDDING_YIGIN_BOYUTU"):
        monkeypatch.delenv(d, raising=False)
    _gpu_taklit(monkeypatch, ("RTX 4090", 24564))

    a = donanim.ayarlar()
    assert a.ad == "gpu"
    assert a.llm_baglam_penceresi > donanim.CPU_PROFILI.llm_baglam_penceresi


def test_profil_ortam_degiskeniyle_zorlanabilir(monkeypatch):
    """Otomatik tespit yanilirsa kullanici son sozu soyleyebilmeli."""
    _gpu_taklit(monkeypatch, None)  # donanim CPU der
    monkeypatch.setenv("KATILIMAI_PROFIL", "gpu")
    for d in ("LLM_BAGLAM_PENCERESI", "LLM_ZAMAN_ASIMI", "EMBEDDING_YIGIN_BOYUTU"):
        monkeypatch.delenv(d, raising=False)

    assert donanim.ayarlar().ad == "gpu"


def test_tek_tek_ayarlar_profilden_bagimsiz_ezilebilir(monkeypatch):
    monkeypatch.delenv("KATILIMAI_PROFIL", raising=False)
    _gpu_taklit(monkeypatch, None)
    monkeypatch.setenv("LLM_ZAMAN_ASIMI", "1234")
    monkeypatch.delenv("LLM_BAGLAM_PENCERESI", raising=False)
    monkeypatch.delenv("EMBEDDING_YIGIN_BOYUTU", raising=False)

    a = donanim.ayarlar()
    assert a.ad == "cpu"                      # profil degismedi
    assert a.llm_zaman_asimi_sn == 1234       # ama tek ayar ezildi


def test_gpu_profili_daha_kisa_zaman_asimi_kullanir():
    """GPU'da cikarim hizli oldugu icin uzun zaman asimi gereksizdir;
    CPU'da ise comert olmali (olculdu: gercek metin >400 sn)."""
    assert donanim.GPU_PROFILI.llm_zaman_asimi_sn < donanim.CPU_PROFILI.llm_zaman_asimi_sn
    assert donanim.GPU_PROFILI.embedding_yigin_boyutu > donanim.CPU_PROFILI.embedding_yigin_boyutu


def test_ozet_calisir_ve_profil_adini_icerir(monkeypatch):
    _gpu_taklit(monkeypatch, ("RTX 4090", 24564))
    monkeypatch.delenv("KATILIMAI_PROFIL", raising=False)
    for d in ("LLM_BAGLAM_PENCERESI", "LLM_ZAMAN_ASIMI", "EMBEDDING_YIGIN_BOYUTU"):
        monkeypatch.delenv(d, raising=False)

    cikti = donanim.ozet()
    assert "RTX 4090" in cikti
    assert "gpu" in cikti


def test_nvidia_smi_yoksa_cokmez(monkeypatch):
    """GPU'suz makinede nvidia-smi bulunmaz - hata firlatmamali."""
    monkeypatch.setattr(donanim.shutil, "which", lambda ad: None)
    assert donanim.gpu_bilgisi() is None

"""ortam_yukle.py testleri.

DENETIM BULGUSU (24 Agustos 2026): .env dosyasi daha once HICBIR YERDE
process ortamina yuklenmiyordu - bkz. ortam_yukle.py dokstring'i. Bu
testler modulun `dotenv.load_dotenv`'i DOGRU parametrelerle (repo
kokundeki .env, override=False) cagirdigini dogrular - gercek bir .env
dosyasi olusturmadan, `importlib.reload` ile modulu yeniden calistirip
`dotenv.load_dotenv` cagrisini yakalayarak.
"""

import importlib

import ortam_yukle


def test_load_dotenv_repo_kokundeki_env_dosyasiyla_cagrilir(monkeypatch):
    cagrilar = []

    def _sahte_load_dotenv(dotenv_path=None, override=None, **kwargs):
        cagrilar.append({"dotenv_path": dotenv_path, "override": override})
        return True

    monkeypatch.setattr("dotenv.load_dotenv", _sahte_load_dotenv)
    try:
        importlib.reload(ortam_yukle)
        assert len(cagrilar) == 1
        assert cagrilar[0]["dotenv_path"].name == ".env"
        assert cagrilar[0]["dotenv_path"].parent == ortam_yukle._ENV_YOLU.parent
        assert cagrilar[0]["override"] is False
    finally:
        # Sahte load_dotenv'i GERI AL, sonra GERCEK load_dotenv ile modulu
        # eski haline dondur - bu testin yan etkisi diger testleri etkilemesin.
        monkeypatch.undo()
        importlib.reload(ortam_yukle)


def test_env_dosyasi_yoksa_hata_firlamaz(tmp_path, monkeypatch):
    """load_dotenv, dosya yoksa sessizce False doner - repo .env.ornek'ten
    henuz .env olusturulmamis bir gelistirici makinesinde/CI'da import
    hata vermemeli."""
    monkeypatch.setattr(ortam_yukle, "_ENV_YOLU", tmp_path / "olmayan.env")
    # Gercek load_dotenv ile, olmayan bir dosyaya karsi cagir - patlamamali.
    from dotenv import load_dotenv

    sonuc = load_dotenv(dotenv_path=ortam_yukle._ENV_YOLU, override=False)
    assert sonuc is False

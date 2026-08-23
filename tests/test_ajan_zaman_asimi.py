"""Ajan Orkestratoru zaman asimi fallback testi.

FAZ 1 tamamlama: agent/orchestrator.py::_arac_cagir_zaman_asimi fonksiyonunun
beklenenden uzun suren arac cagrilarini sessiz kilitlenme olmadan durdurabildigini
dogrular.
"""

import pytest
from unittest.mock import MagicMock, patch
import time


def _mock_gecikme(sure_sn: float):
    """Verilen sure kadar uyuyan ve basarili=True donen mock arac."""
    def _ic(*_args, **_kwargs):
        time.sleep(sure_sn)
        return {"basarili": True, "cevap": "test"}
    return _ic


def test_arac_zaman_asimi_kisa_sureli_basarili():
    """Kisa sureli arac cagrilari normal sekilde doner."""
    from agent.orchestrator import _arac_cagir_zaman_asimi

    sonuc = _arac_cagir_zaman_asimi(
        _mock_gecikme(0.01),
        zaman_asimi_sn=5.0,
    )
    assert sonuc["basarili"] is True
    assert sonuc["cevap"] == "test"


def test_arac_zaman_asimi_tetiklenir():
    """Esigi asan arac cagrisi zaman asimi mesaji doner."""
    from agent.orchestrator import _arac_cagir_zaman_asimi

    sonuc = _arac_cagir_zaman_asimi(
        _mock_gecikme(2.0),
        zaman_asimi_sn=0.1,
    )
    assert sonuc["basarili"] is False
    assert sonuc["sebep"] == "zaman_asimi"
    assert "zaman asimina ugradi" in sonuc["cevap"]


def test_arac_zaman_asimi_hata_iletilir():
    """Arac hata firlatirsa _arac_cagir_zaman_asimi o hatayi iletir."""
    from agent.orchestrator import _arac_cagir_zaman_asimi

    def _hata_firlatir(*_args):
        raise ValueError("test hatasi")

    with pytest.raises(ValueError, match="test hatasi"):
        _arac_cagir_zaman_asimi(_hata_firlatir, zaman_asimi_sn=5.0)


def test_soru_isle_zaman_asimi_fallback_donduruyor():
    """soru_isle: arac zaman asimina ugrarsa fallback=True doner.

    AKIS: hesaplama_aracini_cagir zaman asimina ugrar -> sonuc basarili=False,
    sebep='zaman_asimi'. Kademeli geri cekilme (orchestrator.py satirlari 171+)
    bu durumda RAG'e gider. Test ortaminda Qdrant kapali oldugu icin RAG da
    basarisiz olur - son yanit fallback=True ve Qdrant hata mesaji tasir.
    Bu beklenen ve DOGRU davranisin testi: sessiz kilitlenme YOKTUR,
    sistem acikca hata bildirir.
    """
    from agent.orchestrator import soru_isle

    with patch("agent.orchestrator._VARSAYILAN_ZAMAN_ASIMI_SN", 0.05):
        with patch("agent.orchestrator.hesaplama_aracini_cagir", _mock_gecikme(0.5)):
            with patch("agent.intent.niyet_tespit_et") as mock_niyet:
                from agent.intent import Niyet
                mock_niyet.return_value = (Niyet.HESAPLAMA, 0.9)

                mock_kayit = MagicMock()
                mock_kayit.return_value = []

                sonuc = soru_isle("500000 TL 12 ay", mock_kayit)

    # Fallback olmali - sessiz kilitlenme yok
    assert sonuc["fallback"] is True
    # Yanit bos olmamali - kullaniciya acik mesaj gitmeli
    assert len(sonuc["cevap"]) > 0


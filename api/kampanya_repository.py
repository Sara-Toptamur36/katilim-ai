"""Gercek veritabanindan (PostgreSQL) kampanya okuma katmani.

api/mock_data.py'nin gercek veri karsiligi. Ayni CampaignRecord seklini
(api/schemas.py) doner, boylece api/main.py hangi kaynagi kullandigini
Havin'in arayuzune hic yansitmadan degistirebilir (bkz. GERCEK_VERI_AKTIF
bayragi, api/main.py).
"""

from sqlalchemy.orm import Session

from api.models import Kampanya
from api.schemas import CampaignRecord


def _kayda_cevir(satir: Kampanya) -> CampaignRecord:
    """SQLAlchemy satirini CampaignRecord'a cevirir.

    ONEMLI: mock_data.id_ile_getir() de ayni sekilde Pydantic CampaignRecord
    doner (duz dict DEGIL) - comparison/compare_engine.py attribute erisimi
    (kayit.durum.value, getattr(kayit, alan, None) vb.) kullanir. Duz dict
    donmek karsilastirma motorunu GERCEK_VERI_AKTIF=true iken kirar.
    """
    return CampaignRecord(**{
        "id": satir.id,
        "banka": satir.banka,
        "kampanya_adi": satir.kampanya_adi,
        "kampanya_turu": satir.kampanya_turu or "Belirlenemedi",
        "kar_payi_orani_percent": satir.kar_payi_orani_percent,
        "kar_payi_orani_decimal": satir.kar_payi_orani_decimal,
        "kar_payi_tablosu": satir.kar_payi_tablosu,
        "vade_ay": satir.vade_ay,
        "finansman_tutari": satir.finansman_tutari,
        "taksit_sayisi": satir.taksit_sayisi,
        "erteleme_suresi_ay": satir.erteleme_suresi_ay,
        "odul_miktari": satir.odul_miktari,
        "odul_birimi": satir.odul_birimi,
        "kampanya_avantaji": satir.kampanya_avantaji,
        "masraf_durumu": satir.masraf_durumu,
        "tahsis_ucreti": satir.tahsis_ucreti,
        "kampanya_baslangic": satir.kampanya_baslangic,
        "kampanya_bitis": satir.kampanya_bitis,
        "durum": satir.durum or "BILINMIYOR",
        "hedef_kitle": satir.hedef_kitle,
        "kaynak_url": satir.kaynak_url,
        "belge_tarihi": satir.belge_tarihi,
        "confidence": satir.confidence or 0.0,
        "cikarim_yontemi": satir.cikarim_yontemi,
        "alan_belirtilmemis": satir.alan_belirtilmemis or {},
        # DENETIM BULGUSU: bu alan sema/model/migration/regex_ile_zenginlestir.py
        # ile DB'ye yaziliyordu ama burada hic aktarilmiyordu - Verifier
        # gercekten calisip DB'ye kaydetse bile API bunu sessizce {} donuyordu,
        # ki sema kendi aciklamasinda bos = "Verifier hic calismadi" diyor.
        # terminoloji_tutarli'nin daha once yasadigi ayni API-siniri hatasi.
        "dogrulanan_alanlar": satir.dogrulanan_alanlar or {},
    })


def kampanyalari_getir_db(
    oturum: Session, banka: str | None = None, kampanya_turu: str | None = None
) -> list[CampaignRecord]:
    sorgu = oturum.query(Kampanya)
    if banka:
        sorgu = sorgu.filter(Kampanya.banka == banka)
    if kampanya_turu:
        sorgu = sorgu.filter(Kampanya.kampanya_turu == kampanya_turu)
    return [_kayda_cevir(s) for s in sorgu.order_by(Kampanya.id).all()]


def id_ile_getir_db(oturum: Session, kampanya_id: int) -> CampaignRecord | None:
    satir = oturum.get(Kampanya, kampanya_id)
    return _kayda_cevir(satir) if satir else None

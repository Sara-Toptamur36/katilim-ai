"""Sprint 1 mock verileri.

KAYNAK: Sartname Md. 5, "Ornek Temsili Senaryo-1" - A/B/C Bankasi konut
finansmani ornegi ve beklenen cikti tablosu birebir buradan alinmistir.

NEDEN BU ORNEK: Sartnamenin kendi ornegini cozdugumuzu somut gosterir; ayrica
Havin gercekci bir arayuz kurabilir ve karsilastirma motorunun ciktisi
sartnamedeki tabloyla dogrudan karsilastirilabilir.

Bu veriler Sprint 2'de Zeynep+Yagmur'un gercek verisiyle degistirilecektir.
"""

from datetime import date

from api.schemas import CampaignRecord, CikarimYontemi, KampanyaTuru, YasamDongusu

MOCK_KAMPANYALAR: list[CampaignRecord] = [
    CampaignRecord(
        id=1,
        banka="A Bankasi",
        kampanya_adi="Konut Finansmani Kampanyasi",
        kampanya_turu=KampanyaTuru.KONUT,
        kar_payi_orani_percent=1.89,
        kar_payi_orani_decimal=0.0189,
        vade_ay=120,
        kampanya_avantaji="50.000 TL'ye kadar masraf alinmiyor",
        masraf_durumu="Dosya masrafi yok",
        kampanya_baslangic=date(2026, 7, 1),
        kampanya_bitis=date(2026, 12, 31),
        durum=YasamDongusu.ACTIVE,
        hedef_kitle="Yeni ev sahibi olmak isteyen musteriler",
        kaynak_url="https://ornek-a-bankasi.com.tr/konut-finansmani",
        belge_tarihi=date(2026, 7, 27),
        confidence=0.98,
        cikarim_yontemi=CikarimYontemi.REGEX,
        alan_belirtilmemis={"odul_miktari": True, "tahsis_ucreti": True},
    ),
    CampaignRecord(
        id=2,
        banka="B Bankasi",
        kampanya_adi="Konut Finansmaninda Avantajli Odeme",
        kampanya_turu=KampanyaTuru.KONUT,
        kar_payi_orani_percent=1.95,
        kar_payi_orani_decimal=0.0195,
        vade_ay=120,
        kampanya_avantaji="Ekspertiz ucreti banka tarafindan karsilaniyor",
        masraf_durumu="Ekspertiz ucretsiz",
        # Sartnamede kampanya suresi "Belirtilmemis" -> alan bos, GIZLENMEZ
        kampanya_baslangic=None,
        kampanya_bitis=None,
        durum=YasamDongusu.ACTIVE,
        kaynak_url="https://ornek-b-bankasi.com.tr/konut-finansmani",
        belge_tarihi=date(2026, 7, 27),
        confidence=0.95,
        cikarim_yontemi=CikarimYontemi.REGEX,
        alan_belirtilmemis={
            "kampanya_bitis": True,
            "odul_miktari": True,
            "hedef_kitle": True,
        },
    ),
    CampaignRecord(
        id=3,
        banka="C Bankasi",
        kampanya_adi="Yeni Konut Alimlarina Ozel Finansman",
        kampanya_turu=KampanyaTuru.KONUT,
        kar_payi_orani_percent=1.87,
        kar_payi_orani_decimal=0.0187,
        vade_ay=96,
        odul_miktari=5000.0,
        odul_birimi="TL",
        kampanya_avantaji="5.000 TL degerinde alisveris ceki",
        masraf_durumu="Belirtilmemis",
        kampanya_baslangic=None,
        kampanya_bitis=None,
        durum=YasamDongusu.ACTIVE,
        hedef_kitle="Yeni konut alimi yapanlar",
        kaynak_url="https://ornek-c-bankasi.com.tr/konut-finansmani",
        belge_tarihi=date(2026, 7, 27),
        confidence=0.96,
        cikarim_yontemi=CikarimYontemi.REGEX,
        alan_belirtilmemis={"kampanya_bitis": True, "masraf_durumu": True},
    ),
    # Farkli odul birimi ornegi (rapor Bolum 3: Mil/Gram/Puan cesitliligi)
    CampaignRecord(
        id=4,
        banka="D Bankasi",
        kampanya_adi="Kart Harcamalarina Mil Hediyesi",
        kampanya_turu=KampanyaTuru.KART,
        kar_payi_orani_percent=None,  # kart kampanyasinda oran YOK - gizlenmez
        kar_payi_orani_decimal=None,
        vade_ay=None,
        odul_miktari=10000.0,
        odul_birimi="Mil",
        kampanya_avantaji="10.000 Mil'e varan hediye",
        masraf_durumu="Belirtilmemis",
        kampanya_baslangic=date(2026, 7, 1),
        kampanya_bitis=date(2026, 8, 31),
        durum=YasamDongusu.ACTIVE,
        hedef_kitle="Yeni kart musterileri",
        kaynak_url="https://ornek-d-bankasi.com.tr/kart-kampanyasi",
        belge_tarihi=date(2026, 7, 27),
        confidence=0.91,
        cikarim_yontemi=CikarimYontemi.REGEX,
        alan_belirtilmemis={
            "kar_payi_orani_percent": True,
            "vade_ay": True,
            "masraf_durumu": True,
        },
    ),
]


def kampanyalari_getir(
    banka: str | None = None, kampanya_turu: str | None = None
) -> list[CampaignRecord]:
    """Mock filtreleme. Sprint 2'de gercek PostgreSQL sorgusuyla degisecek."""
    sonuc = MOCK_KAMPANYALAR
    if banka:
        sonuc = [k for k in sonuc if k.banka.lower() == banka.lower()]
    if kampanya_turu:
        sonuc = [k for k in sonuc if k.kampanya_turu.value == kampanya_turu]
    return sonuc


def id_ile_getir(kampanya_id: int) -> CampaignRecord | None:
    for k in MOCK_KAMPANYALAR:
        if k.id == kampanya_id:
            return k
    return None

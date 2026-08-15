"""API sozlesmesi testleri.

AMAC: Havin'in arayuzu bu alan adlarina gore kuruldugu icin, buradaki
alanlarin adi/varligi sessizce degisirse onun kodu bozulur. Bu testler
sozlesmeyi kilitler - CI her push'ta calistirir.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

GECERLI_BASLIK = {"Authorization": "Bearer mock-token-test"}


# ---------------------------------------------------------------------------
# Kimlik dogrulama
# ---------------------------------------------------------------------------


def test_kok_uc_noktasi_kimlik_gerektirmez():
    yanit = client.get("/")
    assert yanit.status_code == 200
    assert yanit.json()["durum"] == "calisiyor"


def test_saglik_kontrolu_calisiyor():
    yanit = client.get("/saglik")
    assert yanit.status_code == 200
    assert yanit.json()["durum"] == "saglikli"


def test_token_ucnoktasi_mock_modda_400_doner():
    """Varsayilan (JWT_AKTIF ayarli degil) modda /token gereksizdir -
    herhangi bir Bearer token zaten kabul edilir (bkz. api/auth.py)."""
    yanit = client.post("/token", data={"username": "test", "password": "test"})
    assert yanit.status_code == 400


@pytest.mark.parametrize(
    "yol,metot,govde",
    [
        ("/kampanyalar", "get", None),
        ("/karsilastir", "post", {"ids": [1, 2]}),
        ("/chat", "post", {"soru": "test"}),
    ],
)
def test_authorization_header_olmadan_401_doner(yol, metot, govde):
    """Havin'in Gun 1'den dogru header formatini kullanmasini garanti eder."""
    yanit = getattr(client, metot)(yol, json=govde) if govde else client.get(yol)
    assert yanit.status_code == 401


def test_bozuk_authorization_formati_401_doner():
    yanit = client.get("/kampanyalar", headers={"Authorization": "mock-token"})
    assert yanit.status_code == 401


# ---------------------------------------------------------------------------
# /kampanyalar
# ---------------------------------------------------------------------------


def test_kampanyalar_liste_doner():
    yanit = client.get("/kampanyalar", headers=GECERLI_BASLIK)
    assert yanit.status_code == 200
    veri = yanit.json()
    assert isinstance(veri, list)
    assert len(veri) >= 3


def test_kampanya_kaydinda_zorunlu_alanlar_var():
    """CampaignRecord sozlesmesi (rapor Bolum 15)."""
    veri = client.get("/kampanyalar", headers=GECERLI_BASLIK).json()
    kayit = veri[0]

    zorunlu = [
        "banka",
        "kampanya_adi",
        "kampanya_turu",
        "kar_payi_orani_percent",
        "kar_payi_orani_decimal",
        "vade_ay",
        "odul_miktari",
        "odul_birimi",
        "kampanya_baslangic",
        "kampanya_bitis",
        "durum",
        "hedef_kitle",
        "kaynak_url",
        "confidence",
        "alan_belirtilmemis",
    ]
    for alan in zorunlu:
        assert alan in kayit, f"Sozlesme alani eksik: {alan}"


def test_eksik_veri_gizlenmez_isaretlenir():
    """Seffaflik ilkesi (rapor Bolum 5.7/15): eksik alan None kalir ve
    alan_belirtilmemis icinde True olarak bayraklanir."""
    veri = client.get("/kampanyalar", headers=GECERLI_BASLIK).json()

    # D Bankasi kart kampanyasinda kar payi orani YOK ama kayit gizlenmiyor
    kart = [k for k in veri if k["banka"] == "D Bankasi"][0]
    assert kart["kar_payi_orani_percent"] is None
    assert kart["alan_belirtilmemis"].get("kar_payi_orani_percent") is True


def test_banka_filtresi_calisir():
    yanit = client.get("/kampanyalar?banka=A Bankasi", headers=GECERLI_BASLIK)
    assert yanit.status_code == 200
    veri = yanit.json()
    assert len(veri) == 1
    assert veri[0]["banka"] == "A Bankasi"


def test_olmayan_kampanya_404_doner():
    yanit = client.get("/kampanyalar/9999", headers=GECERLI_BASLIK)
    assert yanit.status_code == 404


# ---------------------------------------------------------------------------
# /terminoloji (Md. 5.5) - DENETIM BULGUSU: bu uc nokta yokken arayuz
# terminolojiMock.js'te sozlugun AYRI bir kopyasini tutuyordu ve kopya
# gercek sozlukten sapmisti. Bu testler tek kaynagi kilitler.
# ---------------------------------------------------------------------------


def test_terminoloji_sozlugu_doner():
    yanit = client.get("/terminoloji", headers=GECERLI_BASLIK)
    assert yanit.status_code == 200
    veri = yanit.json()
    assert isinstance(veri, list)
    assert len(veri) > 0


def test_terminoloji_kimlik_dogrulama_ister():
    assert client.get("/terminoloji").status_code == 401


def test_terminoloji_kartinda_zorunlu_alanlar_var():
    """Arayuz (TerminolojiSozlugu.jsx) bu alan adlarina gore kuruldu."""
    veri = client.get("/terminoloji", headers=GECERLI_BASLIK).json()
    for kart in veri:
        for alan in ("anahtar", "standart_terim", "gelenek_karsilik", "aciklama", "kaynak"):
            assert kart.get(alan), f"{kart.get('anahtar')} kaydinda '{alan}' bos"


def test_terminoloji_sartname_kavramlarini_icerir():
    """Sartname Md. 5.5'in ornek kavram tablosundaki bes kavram."""
    veri = client.get("/terminoloji", headers=GECERLI_BASLIK).json()
    anahtarlar = {k["anahtar"] for k in veri}
    assert {
        "kar_payi_orani",
        "finansman_maliyeti",
        "katilim_fonu",
        "masrafsiz_finansman",
        "avantajli_finansman",
    } <= anahtarlar


def test_terminoloji_sozlukle_birebir_ayni_sayida_kavram_doner():
    """Uc nokta sozlugu SUZMEZ - arayuzde eksik kavram gorunmesin."""
    from terminology.sozluk import sozluk_yukle

    veri = client.get("/terminoloji", headers=GECERLI_BASLIK).json()
    assert len(veri) == len(sozluk_yukle())


# ---------------------------------------------------------------------------
# /rakip-analizi (Md. 5.7) - tum kriterleri tek tabloda gosterir
# ---------------------------------------------------------------------------


def test_rakip_analizi_kimlik_dogrulama_ister():
    assert client.get("/rakip-analizi").status_code == 401


def test_rakip_analizi_matris_doner():
    yanit = client.get("/rakip-analizi", headers=GECERLI_BASLIK)
    assert yanit.status_code == 200
    veri = yanit.json()
    for alan in ("eksenler", "satirlar", "kayit_sayisi", "banka_sayisi"):
        assert alan in veri


def test_rakip_analizi_her_satirda_tum_eksenler_var():
    """Arayuz tabloyu bu anahtarlara gore kuruyor - eksik sutun olmamali."""
    veri = client.get("/rakip-analizi", headers=GECERLI_BASLIK).json()
    eksen_adlari = {e["kriter"] for e in veri["eksenler"]}
    for satir in veri["satirlar"]:
        assert set(satir["degerler"]) == eksen_adlari


def test_rakip_analizi_kaynak_url_tasir():
    """Her hucre bir kaynaga baglanabilmeli (provenance ilkesi)."""
    veri = client.get("/rakip-analizi", headers=GECERLI_BASLIK).json()
    for satir in veri["satirlar"]:
        assert satir["kaynak_url"]


def test_rakip_analizi_tur_suzgeci_calisir():
    veri = client.get(
        "/rakip-analizi",
        params={"kampanya_turu": "Kart Kampanyasi", "yalnizca_aktif": False},
        headers=GECERLI_BASLIK,
    ).json()
    assert veri["kampanya_turu"] == "Kart Kampanyasi"


# ---------------------------------------------------------------------------
# /karsilastir
# ---------------------------------------------------------------------------


def test_karsilastirma_en_dusuk_orani_basa_koyar():
    """Sartname Md. 5.7 ornegi: C Bankasi (%1,87) en avantajli orandir."""
    yanit = client.post(
        "/karsilastir",
        json={"ids": [1, 2, 3], "kriter": "en_dusuk_kar_payi"},
        headers=GECERLI_BASLIK,
    )
    assert yanit.status_code == 200
    sonuclar = yanit.json()["sonuclar"]
    assert sonuclar[0]["banka"] == "C Bankasi"
    assert sonuclar[0]["kar_payi_orani_percent"] == 1.87


def test_karsilastirmada_null_degerler_en_sona_gider():
    """NULLS LAST: orani olmayan kayit listenin BASINA gelmemeli."""
    yanit = client.post(
        "/karsilastir",
        json={"ids": [1, 4], "kriter": "en_dusuk_kar_payi"},
        headers=GECERLI_BASLIK,
    )
    sonuclar = yanit.json()["sonuclar"]
    assert sonuclar[-1]["kar_payi_orani_percent"] is None


def test_tek_kampanya_ile_karsilastirma_reddedilir():
    yanit = client.post(
        "/karsilastir", json={"ids": [1]}, headers=GECERLI_BASLIK
    )
    assert yanit.status_code == 422  # Pydantic: min_length=2


def test_karsilastirma_terminoloji_kontrolu_uctan_uca_calisir():
    """DENETIM BULGUSU (11 Agu): terminoloji_tutarli yalnizca /chat'te
    hesaplaniyordu; AuditBilgisi'nin kendi tasarim ilkesi "Hesaplama/
    Karsilastirma'da gercek True/False" diyordu ama /karsilastir'in
    dogrudan cagrisinda (dashboard'un kendi sayfasi, chatbot'tan
    BAGIMSIZ) alan hep None donuyordu. Karsilastirma metni sabit,
    katilim-bankaciligi terminolojisine uygun sablonlardan uretildigi
    icin True donmesi beklenir."""
    yanit = client.post(
        "/karsilastir",
        json={"ids": [1, 3], "kriter": "en_avantajli"},
        headers=GECERLI_BASLIK,
    ).json()
    assert yanit["audit"]["terminoloji_tutarli"] is True
    assert yanit["audit"]["terminoloji_sorunlari"] == []


def test_hesaplama_terminoloji_kontrolu_uctan_uca_calisir():
    """Ayni bulgu, /hesapla icin - ozet metni katilim terminolojisine
    (kar payi) uygun oldugundan True donmeli."""
    yanit = client.post(
        "/hesapla",
        json={"anapara": 100000, "aylik_oran_percent": 1.89, "vade_ay": 12},
        headers=GECERLI_BASLIK,
    ).json()
    assert yanit["audit"]["terminoloji_tutarli"] is True
    assert yanit["audit"]["terminoloji_sorunlari"] == []


def test_en_avantajli_kompozit_kriteri_uctan_uca_calisir():
    """D1 bulgusu: Sartname Md. 5.7'nin kompozit kriteri gercek API
    uzerinden de calismali (bkz. comparison/compare_engine.py, A/C
    Bankasi = Ornek Temsili Senaryo-2)."""
    yanit = client.post(
        "/karsilastir",
        json={"ids": [1, 3], "kriter": "en_avantajli"},
        headers=GECERLI_BASLIK,
    )
    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["kriter"] == "en_avantajli"
    assert govde["calistirilan_sql"] is not None
    assert "ORDER BY" not in govde["calistirilan_sql"]
    assert "kar payi" in govde["audit"]["sebep"].lower()


# ---------------------------------------------------------------------------
# /chat  -  audit blogu sozlesmesi
# ---------------------------------------------------------------------------


def test_chat_yanit_verir():
    yanit = client.post(
        "/chat", json={"soru": "A Bankasi'nin konut orani ne?"}, headers=GECERLI_BASLIK
    )
    assert yanit.status_code == 200
    assert "cevap" in yanit.json()


def test_chat_audit_blogu_tum_alanlari_icerir():
    """KRITIK: Havin'in Juri Audit Paneli bu alan adlarina gore kurulur
    (rapor Bolum 10.2). Alanlar Sprint 1'de bos olabilir ama VAR olmalidir."""
    yanit = client.post("/chat", json={"soru": "test"}, headers=GECERLI_BASLIK)
    audit = yanit.json()["audit"]

    beklenen = [
        "intent",
        "intent_confidence",
        "cagrilan_arac",
        "sql_sorgusu",
        "retriever_sonuclari",
        "extraction_confidence",
        "response_confidence",
        "regex_basari_orani",
        "latency_ms",
        "cache_hit",
        "model",
        "temperature",
        "terminoloji_tutarli",
        "terminoloji_sorunlari",
    ]
    for alan in beklenen:
        assert alan in audit, f"Audit paneli alani eksik: {alan}"


def test_chat_terminoloji_bilgisi_uctan_uca_iletilir():
    """DENETIM BULGUSU: agent/orchestrator.py::soru_isle terminoloji
    kontrolunu dogru hesapliyordu ama api/schemas.py::AuditBilgisi'nde
    karsilik gelen alan hic yoktu - deger sessizce API sinirinda
    kayboluyordu. Sozluk sorusu, Md. 5.5'in kendi kavramini (Faiz
    Orani'na karsilik gelir) acikladigi icin gercekten bir gelenek terim
    icerir - bilgi notu (terminoloji_tutarli=None) API'ye kadar ulasmali."""
    yanit = client.post(
        "/chat", json={"soru": "Kâr payı oranı nedir?"}, headers=GECERLI_BASLIK
    ).json()
    audit = yanit["audit"]
    assert audit["cagrilan_arac"] == "dictionary"
    assert audit["terminoloji_tutarli"] is None
    assert audit["terminoloji_sorunlari"]


def test_chat_yanitinda_kaynak_ve_confidence_alanlari_var():
    """Provenance sozlesmesi (rapor Bolum 9)."""
    yanit = client.post("/chat", json={"soru": "test"}, headers=GECERLI_BASLIK).json()
    assert "kaynaklar" in yanit
    assert isinstance(yanit["kaynaklar"], list)
    assert "confidence" in yanit
    assert "fallback" in yanit


def test_cok_uzun_soru_reddedilir():
    yanit = client.post(
        "/chat", json={"soru": "a" * 600}, headers=GECERLI_BASLIK
    )
    assert yanit.status_code == 422


def test_bos_soru_reddedilir():
    yanit = client.post("/chat", json={"soru": ""}, headers=GECERLI_BASLIK)
    assert yanit.status_code == 422


# ---------------------------------------------------------------------------
# Audit kaydi (Md. 11) - DENETIM BULGUSU: AuditKayit tablosu tanimli ve
# migrate edilmisti ama hicbir yer ona satir yazmiyordu.
# ---------------------------------------------------------------------------


def test_audit_kaydet_mock_modda_veritabanina_hic_dokunmaz(monkeypatch):
    """Mock mod BILEREK Docker/Postgres gerektirmez (dosya basi aciklamasi,
    VERI KAYNAGI) - audit yazimi bu garantiyi bozmamali. oturum_al'i
    cagrilirsa patlayacak sekilde degistirip, mock modda GERCEKTEN hic
    cagrilmadigini kanitlar."""
    import api.main as main_modulu

    def _cagrilirsa_patlat():
        raise AssertionError("mock modda oturum_al hic cagrilmamali")

    monkeypatch.setattr(main_modulu, "GERCEK_VERI_AKTIF", False)
    monkeypatch.setattr(main_modulu, "oturum_al", _cagrilirsa_patlat)

    main_modulu._audit_kaydet({"kullanici": "test", "rol": "test"}, "chat", 10)


def test_audit_kaydet_gercek_modda_db_hatasi_asil_istegi_bozmaz(monkeypatch):
    """GERCEK_VERI_AKTIF=true iken audit yazimi denenir, ama Postgres
    erisilemezse (bu makinede oldugu gibi) sessizce loglanir - kullanicinin
    asil istegi (chat/hesapla/karsilastir cevabi) BU YUZDEN ASLA
    basarisiz olmamali; audit ikincil bir kayittir."""
    import api.main as main_modulu

    monkeypatch.setattr(main_modulu, "GERCEK_VERI_AKTIF", True)
    # DB gercekten erisilemez oldugu icin (bu test ortaminda) istisna
    # ATILMAMASI beklenir - _audit_kaydet kendi icinde yakalayip loglar.
    main_modulu._audit_kaydet({"kullanici": "test", "rol": "test"}, "chat", 10)

"""POST /cikar testleri - serbest metinden yapilandirilmis cikti.

NEDEN VAR: Sartname Md. 6, demo videosunda "metin girdisi verilmesi,
modelin urettigi yapilandirilmis cikti" gosterilmesini ZORUNLU kiliyor.
Cikarim motoru vardi ama yalnizca toplu script'ten erisilebiliyordu;
bu uc nokta onu tek metin icin acar.

Kilitlenen davranislar:
  1. Alanlar TEK BASINA donmez - kanit (kaynak_span), katman ve
     dogrulama izi hep yanindadir
  2. Bulunamayan alan sifir DEGIL, `bos_alanlar` icinde ADIYLA listelenir
  3. Hibrit VARSAYILAN OLARAK KAPALI (LLM CPU'da 150-300 sn/kayit)
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

GECERLI_BASLIK = {"Authorization": "Bearer mock-token-test"}

# Gercek kampanya metinlerinin yapisini taklit eden ornek - regex
# katmaninin birden fazla alani doldurabilecegi kadar zengin.
ORNEK_METIN = (
    "Konut finansmaninda aylik %1,89 kar payi orani ile 120 aya varan vade "
    "firsati! Dosya masrafi alinmaz. Kampanya 31.12.2026 tarihine kadar "
    "gecerlidir. Yeni musterilerimize ozeldir."
)


def _cikar(metin: str = ORNEK_METIN, **govde):
    return client.post(
        "/cikar", json={"metin": metin, **govde}, headers=GECERLI_BASLIK
    )


# ---------------------------------------------------------------------------
# Sozlesme
# ---------------------------------------------------------------------------


def test_kimlik_dogrulama_ister():
    assert client.post("/cikar", json={"metin": ORNEK_METIN}).status_code == 401


def test_metinden_alan_cikarir():
    yanit = _cikar()
    assert yanit.status_code == 200
    veri = yanit.json()
    assert veri["alanlar"]["kar_payi_orani_percent"] == 1.89
    assert veri["alanlar"]["vade_ay"] == 120


def test_yanitta_tum_sozlesme_alanlari_var():
    """Arayuz (MetinAnalizi ekrani) bu anahtarlara gore kurulacak."""
    veri = _cikar().json()
    for alan in (
        "alanlar",
        "izler",
        "catismalar",
        "bos_alanlar",
        "genel_guven",
        "hibrit_kullanildi",
        "sure_ms",
    ):
        assert alan in veri


# ---------------------------------------------------------------------------
# Kanit / denetim izi - alanlar tek basina donmez
# ---------------------------------------------------------------------------


def test_her_dolu_alan_kanitiyla_birlikte_doner():
    """Bir degeri gosterip nereden geldigini gizlemek, projenin
    "her kayit kaynagini tasir" ilkesine aykiri olurdu."""
    veri = _cikar().json()
    assert veri["izler"], "Hicbir iz donmedi"

    for iz in veri["izler"]:
        assert iz["alan"]
        assert iz["katman"] in ("regex", "ner", "llm")
        assert iz["kaynak_span"], f"{iz['alan']} icin metindeki kanit bos"


def test_span_kaniti_metinde_gercekten_gecer():
    """kaynak_span uydurulmaz - girdinin icinden gelir.

    YALNIZCA kanit_turu="span" olan alanlar icin gecerli. kampanya_turu
    anahtar kelimeyle SINIFLANDIRILIR; onun "kanit"i bir etikettir ve
    metinde aynen gecmez - bu ayrim yapilmazsa arayuz kullaniciya metinde
    bulunmayan bir ifadeyi "kanit" diye gosterir."""
    veri = _cikar().json()
    span_izleri = [i for i in veri["izler"] if i["kanit_turu"] == "span"]
    assert span_izleri, "Hicbir span kaniti donmedi"

    for iz in span_izleri:
        assert iz["kaynak_span"] in ORNEK_METIN, (
            f"{iz['alan']}: '{iz['kaynak_span']}' girdi metninde yok"
        )


# hedef_kitle de kampanya_turu gibi anahtar kelimeyle ETIKETE
# siniflandirilir ("Yeni müşteri"), metinden span kesilmez. 17 Agustos'a
# kadar bu gozden kacmisti: regex_extractor diyakritiksiz metinde
# hedef_kitle'yi hic bulamadigi icin (katlama hatasi) ORNEK_METIN uzerinde
# alan bos donuyor, dolayisiyla yanlis isaretleme de hic gorunmuyordu.
@pytest.mark.parametrize("alan", ["kampanya_turu", "hedef_kitle"])
def test_siniflandirma_alani_span_diye_isaretlenmez(alan):
    veri = _cikar().json()
    iz = next((i for i in veri["izler"] if i["alan"] == alan), None)
    if iz is not None:
        assert iz["kanit_turu"] == "siniflandirma"


def test_turetilmis_alanlar_ayrica_isaretlenir():
    """kampanya_avantaji digger alanlardan DERLENIR, metinden cikarilmaz -
    izi yoktur. Arayuz bunu "metinde bulundu" gibi gostermemeli."""
    veri = _cikar().json()
    assert "kampanya_avantaji" in veri["turetilmis_alanlar"]

    izli_alanlar = {i["alan"] for i in veri["izler"]}
    for alan in veri["turetilmis_alanlar"]:
        assert veri["alanlar"][alan] is not None, f"{alan} turetilmis ama degeri yok"
        assert alan not in izli_alanlar, f"{alan} hem turetilmis hem izli olamaz"


def test_sayisal_alanlar_verifier_sonucu_tasir():
    veri = _cikar().json()
    kar_payi = next(i for i in veri["izler"] if i["alan"] == "kar_payi_orani_percent")
    assert kar_payi["dogrulandi"] is not None


def test_genel_guven_bulunan_alanlardan_hesaplanir():
    veri = _cikar().json()
    assert 0.0 < veri["genel_guven"] <= 1.0


# ---------------------------------------------------------------------------
# Bos alan sifir DEGILDIR
# ---------------------------------------------------------------------------


def test_bulunamayan_alan_adiyla_listelenir():
    """Ornek metinde odul yok - bu "odul sifir" degil "kaynakta
    belirtilmemis" demektir (README tasarim ilkesi 1)."""
    veri = _cikar().json()
    assert "odul_miktari" in veri["bos_alanlar"]
    assert veri["alanlar"]["odul_miktari"] is None


def test_bos_alanlar_ile_alanlar_tutarli():
    veri = _cikar().json()
    for alan in veri["bos_alanlar"]:
        assert veri["alanlar"][alan] is None


def test_hicbir_sey_bulunamayan_metin_hata_vermez():
    """Alakasiz metin -> bos sonuc, ama 200 ve acik bir cikti."""
    veri = _cikar("Bu metin bankacilikla tamamen alakasiz bir paragraftir ve "
                  "icinde hicbir finansal deger bulunmamaktadir.").json()
    assert veri["genel_guven"] == 0.0
    assert veri["izler"] == []
    assert len(veri["bos_alanlar"]) > 0


# ---------------------------------------------------------------------------
# Hibrit varsayilan olarak KAPALI
#
# NOT: hibrit=true ile calisan testler `slow` isaretlidir - GLiNER modelini
# gercekten yukler (ilk cagride dakikalar surebilir) ve Ollama'ya istek
# atar. tests/test_ner_extractor.py da ayni sebeple tumuyle slow.
# Haric tutmak icin: pytest -m "not slow"
# ---------------------------------------------------------------------------


def test_hibrit_varsayilan_olarak_kapalidir():
    """LLM GPU'suz makinede kayit basina 150-300 sn - canli demo bunu
    bekleyemez, bu yuzden acikca istenmedikce calismaz. Bu testin HIZLI
    kalmasi, varsayilanin gercekten kapali oldugunun da kanitidir: acik
    olsaydi bu test de dakikalarca surerdi."""
    assert _cikar().json()["hibrit_kullanildi"] is False


@pytest.mark.slow
def test_hibrit_bayragi_yanitta_gorunur():
    veri = _cikar(hibrit=True).json()
    assert veri["hibrit_kullanildi"] is True


@pytest.mark.slow
def test_hibrit_istenip_katman_gelmezse_acikca_bildirilir():
    """Ollama kapaliyken sessizce regex sonucu donup "hibrit calisti"
    izlenimi vermek yaniltici olurdu."""
    veri = _cikar(hibrit=True).json()
    katmanlar = {iz["katman"] for iz in veri["izler"]}
    if not (katmanlar & {"ner", "llm"}):
        assert veri["not"], "Hibrit calismadi ama kullaniciya bildirilmedi"


# ---------------------------------------------------------------------------
# Girdi dogrulama
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "govde",
    [
        {"metin": "kisa"},                  # min_length alti
        {"metin": "x" * 20001},             # max_length ustu
        {},                                 # metin yok
    ],
)
def test_gecersiz_girdi_422_doner(govde):
    assert client.post("/cikar", json=govde, headers=GECERLI_BASLIK).status_code == 422


def test_cok_uzun_metin_sunucuyu_mesgul_etmez():
    """Sinir olmadan gonderilen dev metin, cikarim motorunu gereksiz
    yere calistirirdi."""
    yanit = client.post(
        "/cikar", json={"metin": "a" * 50000}, headers=GECERLI_BASLIK
    )
    assert yanit.status_code == 422

"""Musteri Sesi (Complaint Insight) - kural tabanli tema siniflandirici.

FAZ 1 T8 (PeacewAI_Faz_Plani_ve_Is_Bolumu.docx): mentorun 3.7'de onerdigi
"en dusuk riskli yol" - duygu analizi modeli (Faz 2) yerine, Faz 1'de
KURAL TABANLI siniflandirma. Gercek Sikayetvar/musteri verisi ancak
kurumsal/hukuki (KVKK) izin surecinden sonra Faz 2'de ingest edilecek;
bu modul o zamana kadar YALNIZCA sentetik ornek uzerinde calisir (bkz.
tests/veri/kapsam_disi/sentetik_musteri_sesi.json).

NEDEN KURAL TABANLI (ve neden simdilik yeterli): hizli, aciklanabilir -
"neden bu temaya girdi?" sorusuna, hangi ifadenin eslestigini gostererek
cevap verilebilir. Juri "kural mi model mi?" derse durust cevap budur.

TASARIM ILKESI (rapor Bolum 5.7/15 ile ayni): hicbir ifade eslesmezse
tema UYDURULMAZ - None doner. Kismi/belirsiz bir metni zorla bir temaya
sokmak, extraction katmanindaki "kaynakta olmayan deger uretme" hatasinin
sikayet tarafindaki karsiligi olurdu.

ESLESME BICIMI: tek kelime degil, COK KELIMELI ifadeler kullanilir (ör.
"aktivasyon" tek basina degil "aktivasyon yapmadim" gibi) - tek kelimeli
anahtar kelimeler farkli temalar arasinda capraz eslesme (yanlis pozitif)
uretiyordu, olculdu (bkz. tests/test_sentetik_musteri_sesi.py ozgulluk
olcumu, terminology/tutarlilik_kontrolu.py'deki ayni derste).
"""

from __future__ import annotations

from extraction.normalizer import turkce_ascii_kucult

# Her tema icin COK KELIMELI ifadeler - tek kelime degil (capraz eslesme
# riski). Ifadeler turkce_ascii_kucult ile katlanmis halde yazilir (asagida
# _katla_liste ile hem burada hem aranan metinde ayni katlama uygulanir).
_TEMA_IFADELERI: dict[str, list[str]] = {
    "REWARD_NOT_CREDITED": [
        "odul yatmadi", "odul gecmedi", "puan yatmadi", "puan gecmedi",
        "hesabima gecmedi", "hesabima yatmadi", "worldpuan", "bankkart lira",
        "parafpara", "odul tutari",
    ],
    "ELIGIBILITY_MISMATCH": [
        "uygun degilmisim", "uygun degil", "kapsaminda degil", "kapsam disinda",
        "yararlanamiyorum", "yararlanamadim", "segment", "musteri olmam",
    ],
    "INSTALLMENT_MATURITY": [
        "taksit secenegi", "taksit sayisi", "odemesiz donem", "erteleme",
        "taksit tahsil", "vade",
    ],
    "MERCHANT_MCC_SCOPE": [
        "isyeri kampanyaya dahil", "isyeri degil", "anlasmali degil",
        "istasyon anlasmali", "market alisveris", "kampanya kapsaminda oldugunu",
    ],
    "ACTIVATION_REGISTRATION": [
        "aktivasyon yapmam", "aktivasyon yapmadim", "aktivasyon basarisiz",
        "aktivasyon butonu", "aktive",
    ],
    "DATE_EXPIRY": [
        "suresinin doldugunu", "bitis tarihi", "son gun basvuru",
        "bir gun once bitti", "kampanyanin suresi",
    ],
    "CARD_PRODUCT_MISMATCH": [
        "kart turu", "farkli bir urun", "kredi kartimla degil",
        "banka kartimla", "kart uyusmuyor",
    ],
    "FEE_CHARGE": [
        "tahsis ucreti", "beklenmedik komisyon", "ucret kesildi",
        "masrafsiz sanirken", "komisyon kesildi",
    ],
    "COMMUNICATION_AMBIGUITY": [
        "metni karisik", "net degildi", "anlayamadim", "yaziliyordu ama",
        "hicbir yerde yazmiyordu",
    ],
    "SERVICE_RESOLUTION": [
        "cagri merkezini aradim", "sorunum cozulmedi", "farkli temsilciler",
        "subeye gittim", "cagri merkezine yonlendirdiler",
    ],
}


def _katla_liste(ifadeler: list[str]) -> list[str]:
    return [turkce_ascii_kucult(i) for i in ifadeler]


_TEMA_IFADELERI_KATLANMIS = {
    tema: _katla_liste(ifadeler) for tema, ifadeler in _TEMA_IFADELERI.items()
}


def tema_siniflandir(metin: str) -> dict:
    """Serbest metni 10 temali taksonomiye (mentor 3.3) gore siniflandirir.

    Donen sozluk: {"tema": str|None, "guven": float, "eslesen_ifadeler": list[str]}.
    Hicbir tema esik degerini gecemezse tema None doner - UYDURULMAZ.

    Guven, en cok eslesen temanin eslesme sayisinin normalize edilmis
    halidir (basit ama aciklanabilir - "kac ifade eslesti" gosterilebilir).
    """
    katlanmis = turkce_ascii_kucult(metin)

    en_iyi_tema: str | None = None
    en_iyi_eslesenler: list[str] = []

    for tema, ifadeler_katlanmis in _TEMA_IFADELERI_KATLANMIS.items():
        eslesenler = [
            ham for ham, kat in zip(_TEMA_IFADELERI[tema], ifadeler_katlanmis)
            if kat in katlanmis
        ]
        if len(eslesenler) > len(en_iyi_eslesenler):
            en_iyi_tema = tema
            en_iyi_eslesenler = eslesenler

    if not en_iyi_eslesenler:
        return {"tema": None, "guven": 0.0, "eslesen_ifadeler": []}

    # Guven: 1 eslesme 0.6, 2+ eslesme 0.85 - regex_extractor.py'deki
    # "baglam eslesmeli desen" (0.85-0.9) / "genel fallback" (0.6) ayrimiyla
    # AYNI mantik: birden fazla bagimsiz ifadenin ayni temaya isaret etmesi
    # tek bir ifadeden daha guvenilirdir.
    guven = 0.6 if len(en_iyi_eslesenler) == 1 else 0.85

    return {"tema": en_iyi_tema, "guven": guven, "eslesen_ifadeler": en_iyi_eslesenler}

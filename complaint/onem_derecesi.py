"""Sikayetin ONEM DERECESI (severity) - kural tabanli, kanitli.

NEDEN FORMUL/PUAN DEGIL KATEGORI: comparison/etki_skoru.py ve
complaint/kampanya_eslestirme.py'deki AYNI ilke - "0.4 x X + 0.3 x Y"
gibi agirlikli bir sayi UYDURMAK yerine, GOZLENEBILIR sinyallere
dayanan bir kategori ve o kategoriyi ACIKLAYAN bir gerekce uretilir.
Juri "neden 0.7 degil 0.6?" diye sorarsa cevap yoktur; "neden YUKSEK?"
diye sorarsa gerekce sozlugu cevabi verir.

--------------------------------------------------------------------------
UC SEVIYE, VARSAYILAN EN DUSUK DEGIL
--------------------------------------------------------------------------
    YUKSEK - parasal kayip/tahsilat temasi (FEE_CHARGE, REWARD_NOT_CREDITED)
             VEYA tekrarlanan magduriyet ifadesi (defalarca, haftalardir)
             VEYA metinde somut bir TL/₺ tutari gecmesi (DUSUK temalar
             haric - asagi bak)
    ORTA   - varsayilan. "Yuksek sinyali gorulmedi" demektir, "onemsiz"
             degil - yukaridaki sinyallerin hicbiri yoksa buraya duser
    DUSUK  - yalnizca COMMUNICATION_AMBIGUITY: bilgi eksikligi/belirsizlik,
             henuz somut bir zarar bildirilmemis

Varsayilan ORTA'dir, DUSUK degil - kirmizi cizgi (tema_siniflandirici.py,
kampanya_eslestirici.py ile AYNI): kanit yoksa en dusuk ya da en yuksek
iddia degil, "ayirt edici sinyal yok" durumu uretilir.

--------------------------------------------------------------------------
NEDEN 3. SINYAL (TUTAR BAHSI) EKLENDI - 27 Agustos 2026
--------------------------------------------------------------------------
Ilk surumde YUKSEK yalnizca IKI temaya (FEE_CHARGE, REWARD_NOT_CREDITED)
BAGLIYDI - yani 10 temanin 8'i, metnin ICERIGINDEN BAGIMSIZ olarak HER
ZAMAN ORTA doneceginden, "onem derecesi" fiilen temanin gizli bir
yeniden-etiketlenmesiydi. Somut bir TL/₺ tutari gecmesi, TEMADAN
BAGIMSIZ, olculebilir bir sinyaldir - "500 TL kaybettim" ile "kampanya
metni net degildi" arasindaki fark parayla ilgilidir, temayla degil.
DUSUK temalar (COMMUNICATION_AMBIGUITY) bu sinyalden BILEREK MUAF
TUTULUR: "500 TL'lik odul hakkinda net bilgi bulamadim" hala bir bilgi
eksikligidir, dogrulanmis bir kayip degil - tutar gecmesi onu YUKSEK'e
YUKSELTMEZ (bkz. kontrol sirasi asagida).

--------------------------------------------------------------------------
TEMA-BAZLI ESLEME NEDEN KABUL EDILEBILIR
--------------------------------------------------------------------------
Tema kendisi zaten complaint/tema_siniflandirici.py::TEMA_SURUMU ile
denetlenebilir, kanitli bir siniflandirmadir (eslesen_ifadeler). Onem
derecesini temaya baglamak, ayri bir kanitsiz siniflandirici eklemek
yerine ZATEN KANITLANMIS bir sinyali yeniden kullanmaktir - ayni ilke
comparison/etki_skoru.py'nin "eksen yuzdeligi" tercihiyle ayni: var olan
gozlemi kullan, yeni bir tahmin uydurma.
"""

from __future__ import annotations

import re

from extraction.normalizer import turkce_ascii_kucult

YUKSEK = "YUKSEK"
ORTA = "ORTA"
DUSUK = "DUSUK"

# Parasal kayip/tahsilat bildiren temalar - somut, olculebilir zarar.
_YUKSEK_TEMALAR = {"FEE_CHARGE", "REWARD_NOT_CREDITED"}

# Yalnizca bilgi/iletisim belirsizligi - henuz somut zarar yok. Bu temalar
# tutar bahsi sinyalinden de MUAFTIR (bkz. modul basligi).
_DUSUK_TEMALAR = {"COMMUNICATION_AMBIGUITY"}

# Tekrarlanan magduriyet ifadeleri - tek seferlik degil, sureklilik sinyali.
_TEKRAR_IFADELERI = [
    "defalarca", "tekrar tekrar", "haftalardir", "aylardir",
    "bir cok kez", "surekli", "her seferinde",
]

# Somut bir TL/₺ tutari gecmesi - deger CIKARILMAZ (bu extraction/'in isi),
# yalnizca VAR MI YOK MU sorulur. extraction/regex_extractor.py'deki tutar
# desenlerinden BILEREK AYRI: buradaki amac degeri dogru ayristirmak degil,
# "parayla ilgili somut bir iddia var mi" sorusuna hizli cevap vermek.
_TUTAR_BAHSI = re.compile(r"\d[\d.,]*\s*(?:tl|₺)", re.IGNORECASE)


def onem_derecesi_belirle(temiz_metin: str, tema: str | None) -> dict:
    """Sikayetin onem derecesini ve gerekcesini doner.

    Donen sozluk: {"onem_derecesi": str, "gerekce": dict}. `gerekce`
    hangi sinyalin karari verdirdigini ACIKCA gosterir - kampanya_esle
    tarzinda, sayi tek basina kalmasin diye.

    KONTROL SIRASI ONEMLI: parasal tema → tekrar ifadesi → DUSUK tema
    (mutlak, tutar bahsi bile onu YUKSELTMEZ) → tutar bahsi → varsayilan.
    """
    katlanmis = turkce_ascii_kucult(temiz_metin or "")

    tekrar_eslesen = next(
        (ifade for ifade in _TEKRAR_IFADELERI if ifade in katlanmis), None
    )

    if tema in _YUKSEK_TEMALAR:
        return {
            "onem_derecesi": YUKSEK,
            "gerekce": {"sebep": "parasal_kayip_temasi", "tema": tema},
        }
    if tekrar_eslesen:
        return {
            "onem_derecesi": YUKSEK,
            "gerekce": {"sebep": "tekrarlanan_magduriyet_ifadesi", "ifade": tekrar_eslesen},
        }
    if tema in _DUSUK_TEMALAR:
        return {
            "onem_derecesi": DUSUK,
            "gerekce": {"sebep": "yalnizca_bilgi_belirsizligi", "tema": tema},
        }
    tutar_eslesme = _TUTAR_BAHSI.search(temiz_metin or "")
    if tutar_eslesme:
        return {
            "onem_derecesi": YUKSEK,
            "gerekce": {"sebep": "somut_tutar_bahsi", "eslesen": tutar_eslesme.group(0)},
        }
    return {
        "onem_derecesi": ORTA,
        "gerekce": {"sebep": "yuksek_veya_dusuk_sinyal_gorulmedi_varsayilan"},
    }

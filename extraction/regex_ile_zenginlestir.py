"""Kampanyalar tablosundaki bos finansal alanlari hibrit cikarim motoruyla
doldurur (regex -> NER -> LLM, bkz. extraction/hybrid_pipeline.py).

scraper/scripts/postgrese_yukle.py'nin ikinci adimi: o script yalnizca
kaynak/izlenebilirlik alanlarini yazip finansal alanlari NULL birakiyordu
(bkz. o dosyanin HENUZ_CIKARILMAMIS_ALANLAR listesi). Bu script, ayni
scraper/raw_data/*/json/*.json ham metinlerini kaydi_hibrit_cikar() ile
isleyip SADECE HALA NULL olan alanlari doldurur.

DENETIM BULGUSU (mentor denetimi): Bu script eskiden yalnizca
regex_extractor.kaydi_cikar()'i (regex-only) cagiriyordu - hibrit boru
hatti (NER+LLM) yazildiktan SONRA bile veritabanini dolduran gercek
kod hala regex-only kalmisti. Yani README'nin "hibrit cikarim" iddiasi
ile veritabanini gercekte dolduran kod arasinda bir fark vardi. Artik
kaydi_hibrit_cikar() cagriliyor.

PERFORMANS UYARISI: Hibrit cagri, regex'in bos biraktigi her alan icin
NER (ilk cagrida GLiNER modelini yukler, ~birkac saniye tek seferlik) ve
gerekirse LLM (Ollama'ya HTTP istegi, basarili bir cagri GPU'suz
makinede 150-300+ sn surebilir - bkz. extraction/llm_extractor.py) cagirir.
Cok sayida kayit uzerinde calistirmak saf regex'ten (kayit basina <1sn)
COK daha uzun surebilir; Ollama kapaliysa LLM adimi hizlica (onbellekli
kontrol sayesinde) None doner, ilerlemeyi durdurmaz (bkz.
extraction/llm_extractor.py::_ollama_hazir_mi).

IDEMPOTENT VE GUVENLI GUNCELLEME: Bir alan zaten dolu ise (manuel duzeltme
veya onceki bir calistirmayla) UZERINE YAZILMAZ - her alan tek tek
kontrol edilir. Boylece elle yapilan duzeltmeler bu script tekrar
calistirildiginda SILINMEZ. (Hibrit boru hattinin KENDI ic guven-esikli
devralma mantigi - bkz. hybrid_pipeline.py KILITLEME_GUVEN_ESIGI - bu
disaridan-asla-ezme kuralindan AYRIDIR: o, TEK bir kaydi_hibrit_cikar()
cagrisi icindeki regex/NER/LLM katmanlari arasindaki uzlasmadir; burasi,
veritabaninda ONCEDEN VAR olan bir degerin bu script tarafindan hic
ezilmemesidir.)

Kullanim:
    python -m extraction.regex_ile_zenginlestir
"""

import json
from pathlib import Path

from api.db import OturumYerel
from api.logging_config import log
from api.models import Kampanya
from extraction.hybrid_pipeline import kaydi_hibrit_cikar
from extraction.regex_extractor import genel_guven_hesapla, kampanya_avantajini_olustur
from extraction.tablo_extractor import oran_tablolarini_sec
from validation.verifier import kaydi_dogrula

RAW_DATA_KOK = Path(__file__).resolve().parent.parent / "scraper" / "raw_data"

# CampaignRecord alan adi -> Kampanya ORM kolon adi ayni, dogrudan setattr edilir.
CIKARILABILEN_ALANLAR = [
    "kar_payi_orani_percent",
    "kar_payi_orani_decimal",
    "vade_ay",
    "taksit_sayisi",
    "erteleme_suresi_ay",
    "finansman_tutari",
    "odul_miktari",
    "odul_birimi",
    "masraf_durumu",
    "tahsis_ucreti",
    "kampanya_avantaji",
    "kampanya_baslangic",
    "kampanya_bitis",
    "kampanya_turu",
    "hedef_kitle",
]


def _ham_metinleri_url_ile_esle() -> dict[str, dict]:
    """kaynak_url -> {"ham_metin": ..., "tablolar": ...} sozlugu.
    postgrese_yukle.py'deki _json_kayitlarini_bul ile ayni tarama mantigi."""
    esleme = {}
    for dosya in RAW_DATA_KOK.glob("*/json/*.json"):
        try:
            with open(dosya, encoding="utf-8") as f:
                kayit = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        url = kayit.get("url")
        metin = kayit.get("ham_metin") or kayit.get("normalize_metin")
        if url and metin:
            esleme[url] = {"ham_metin": metin, "tablolar": kayit.get("tablolar")}
    return esleme


def _tablo_varsa_kar_payi_bastir(cikan: dict, secilen_tablo: list[dict] | None) -> dict:
    """Sayfada bir oran TABLOSU varsa, hibrit boru hattinin duz metinden
    urettigi TEK sayilik `kar_payi_orani_percent`/`_decimal` adayini
    (ve ondan derlenen `kampanya_avantaji` ozetini) siler.

    OLCULDU - sayfada bir oran TABLOSU varken duz metin tahmini HER GUVEN
    SEVIYESINDE yaniliyor, iki farkli mekanizmayla:
      1) dusuk guvenli "ilk bulunan %X" fallback (guven 0.6, Turkiye Finans
         banka-/kamu-calisanlarina-ozel-ihtiyac-finansmani sayfalari) -
         get_text()'in duzlestirdigi YANLIS sutundan (ör. "Aylık Toplam
         Maliyet") geliyordu.
      2) "confident" ifade eslesmesi (guven 0.8, Albaraka dijital-
         musterilere-ozel-pratik-finansman-kart) - sayfa "vade farksiz
         VEYA ozel oranli" diyor (kosullu secim, TUM kampanya DEGIL) ve
         tablo bunu dogruluyor: sadece EN KUCUK tutar diliminde (250-
         40.000 TL) %0, digerlerinde %3,95/3,90/3,85.
    Yani "tablo varsa duz metne guvenme" esigi guven SEVIYESINE gore degil,
    TABLO VARLIGINA gore konuldu - 3/3 olculen tablolu sayfada duz metin
    tahmini yanildi, sifir karsi-ornek yok. Gercek (vadeye/tutara gore
    degisen) oranlar zaten kar_payi_tablosu'nda dogru duruyor.
    """
    if secilen_tablo is None:
        return cikan
    cikan["kar_payi_orani_percent"] = None
    cikan["kar_payi_orani_decimal"] = None
    # kampanya_avantaji DERLEME'dir (bkz. regex_extractor.
    # kampanya_avantajini_olustur docstring'i) - kaydi_hibrit_cikar() onu
    # YUKARIDAKI bastirmadan ONCEKI (henuz bastirilmamis, hatali)
    # kar_payi_orani_percent ile derlemisti; bastirmadan SONRA yeniden
    # derlenmezse ozet metin alanin kendisiyle (None) CELISIR - OLCULDU.
    cikan["kampanya_avantaji"] = kampanya_avantajini_olustur(cikan)
    return cikan


def zenginlestir() -> dict:
    """Donen ozet: {"guncellendi": N, "atlandi": M, "ham_metin_yok": K,
    "dogrulanamayan": L, "tablo_eklendi": T}.

    "dogrulanamayan": bu calistirmada YENI yazilan sayisal alanlardan,
    validation/verifier.py'nin kaynak metinde (deger + baglam) DOGRULAYAMADIGI
    sayisi - bkz. asagida "Verifier" bolumu.
    "tablo_eklendi": kar_payi_tablosu bu calistirmada YENI dolduruldu -
    "guncellendi" ile AYRI sayilir cunku CIKARILABILEN_ALANLAR akisina
    (confidence/cikarim_yontemi/Verifier) dahil degildir."""
    ozet = {
        "guncellendi": 0, "atlandi": 0, "ham_metin_yok": 0,
        "dogrulanamayan": 0, "tablo_eklendi": 0,
    }
    url_veri = _ham_metinleri_url_ile_esle()
    oturum = OturumYerel()

    try:
        satirlar = oturum.query(Kampanya).all()
        for satir in satirlar:
            veri = url_veri.get(satir.kaynak_url)
            ham_metin = veri.get("ham_metin") if veri else None
            if not ham_metin:
                ozet["ham_metin_yok"] += 1
                continue

            # Kar payi tablosu (Rehber Bolum 18): idempotent, TEK sayiya
            # indirgenmez, alan_belirtilmemis/confidence/cikarim_yontemi
            # akisina dahil edilmez - bkz. extraction/tablo_extractor.py
            # docstring'i (neden ayri tutuldugu).
            secilen_tablo = oran_tablolarini_sec(veri.get("tablolar"))
            if secilen_tablo is not None and satir.kar_payi_tablosu is None:
                satir.kar_payi_tablosu = secilen_tablo
                ozet["tablo_eklendi"] += 1

            cikan = kaydi_hibrit_cikar(ham_metin)
            izler = cikan.pop("_izler")
            kaynaklar = cikan.pop("_kaynaklar")
            cikan.pop("_adaylar", None)
            cikan.pop("_catismalar", None)

            cikan = _tablo_varsa_kar_payi_bastir(cikan, secilen_tablo)

            alan_belirtilmemis = dict(satir.alan_belirtilmemis or {})
            degisti = False
            kullanilan_katmanlar: set[str] = set()
            guncellenen_alanlar: list[str] = []

            for alan in CIKARILABILEN_ALANLAR:
                mevcut_deger = getattr(satir, alan, None)
                yeni_deger = cikan.get(alan)
                if mevcut_deger is None and yeni_deger is not None:
                    setattr(satir, alan, yeni_deger)
                    alan_belirtilmemis[alan] = False
                    degisti = True
                    kullanilan_katmanlar.add(kaynaklar.get(alan, "regex"))
                    guncellenen_alanlar.append(alan)

            if degisti:
                satir.alan_belirtilmemis = alan_belirtilmemis
                satir.confidence = genel_guven_hesapla(izler)
                # Kayit gercekten NER/LLM katkisi aldiysa "hibrit", tum
                # doldurulan alanlar regex'ten geldiyse durustce "regex"
                # (bkz. rapor Bolum 5.7/15 - hangi yontemin kullanildigi
                # uydurulmaz/abartilmaz).
                satir.cikarim_yontemi = (
                    "hibrit" if kullanilan_katmanlar - {"regex"} else "regex"
                )
                ozet["guncellendi"] += 1

                # Verifier (validation/verifier.py) - YENI yazilan sayisal
                # alanlarin kaynak metinde (deger + baglam) gercekten gecip
                # gecmedigini kontrol eder. BILEREK SILMEZ/GERI ALMAZ: Verifier
                # kendi olcumunde bile gercek-dogru degerlerin bir kismini
                # (bilinen sinir: "vade farksiz" gibi literal "0" icermeyen
                # ifadeler) yanlislikla dogrulayamiyor - otomatik silmek
                # DOGRU veriyi de kaybettirirdi. Amac gorunurluk/denetim izidir
                # (rapor Bolum 5.7/15/9), veri BUDANMAZ. Sonuc `dogrulanan_
                # alanlar` sutununda KALICI olarak saklanir (onceden yalnizca
                # log dosyasina yaziliyordu, API/dashboard'dan hic erisilemezdi).
                dogrulama = kaydi_dogrula(
                    {a: getattr(satir, a) for a in guncellenen_alanlar}, ham_metin
                )
                # DENETIM BULGUSU: Verifier sonucu ONCEDEN yalnizca log
                # dosyasina yaziliyordu - goruntulenemez, API'den donmez,
                # dashboard hicbir zaman "bu deger dogrulandi mi" gosteremezdi.
                # Artik kalici (dogrulanan_alanlar sutunu) - mevcut satirdaki
                # ONCEKI calistirmalardan kalan degerler KORUNUR (yalnizca bu
                # calistirmada guncellenen alanlar icin anahtar eklenir/degisir).
                dogrulanan_alanlar = dict(satir.dogrulanan_alanlar or {})
                for alan, sonuc in dogrulama.items():
                    dogrulanan_alanlar[alan] = sonuc.dogrulandi
                    if not sonuc.dogrulandi:
                        ozet["dogrulanamayan"] += 1
                        log.warning(
                            "Verifier: kampanya id=%s (%s) - %s=%s kaynak metinde "
                            "dogrulanamadi (sayi_metinde_bulundu_mu=%s)",
                            satir.id, satir.kaynak_url, alan, sonuc.deger,
                            sonuc.sayi_metinde_bulundu_mu,
                        )
                satir.dogrulanan_alanlar = dogrulanan_alanlar
            else:
                ozet["atlandi"] += 1

        oturum.commit()
    finally:
        oturum.close()

    return ozet


if __name__ == "__main__":
    sonuc = zenginlestir()
    print(
        f"Zenginlestirildi: {sonuc['guncellendi']} guncellendi, "
        f"{sonuc['atlandi']} zaten doluydu/degismedi, "
        f"{sonuc['ham_metin_yok']} icin ham metin bulunamadi, "
        f"{sonuc['dogrulanamayan']} yeni alan Verifier'dan gecemedi "
        "(silinmedi, bkz. logs/api.log), "
        f"{sonuc['tablo_eklendi']} kayda kar_payi_tablosu eklendi"
    )

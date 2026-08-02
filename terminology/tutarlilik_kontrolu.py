"""Terminoloji Tutarlılık Kontrolü (Şartname Md. 5.5, rapor Bölüm 5.3'teki
"Terminology Check" adımı).

Ajanın ürettiği doğal dil yanıtında geleneksel bankacılık teriminin
(Faiz, Mevduat, Kredi) sızıp sızmadığını denetler. Bu kontrol, bilerek
terminology/sozluk.json'daki 12 kavramdan OTOMATIK türetilmez — çünkü
o kavramların gelenek_karsilik alanlarının ilk kelimesini almak yanıltıcı
sonuçlar üretir (örnek: "Vadeli Mevduat"tan "Vadeli" çıkarmak, "vadeli
taksit" gibi tamamen masum ifadelerde yanlış alarm verir; "Kampanya
Hediyesi" veya "Grace Period" gibi karşılıkların flaglenecek anlamlı
tek bir kelimesi yoktur). Bunun yerine, özenle seçilmiş, ayrı bir
gelenek-terim listesi kullanılır.

İki ayrı gerçek veri kaynağına karşı doğrulandı:
1. Altın Veri Seti (62 kayıt): "faizsiz" (faiz kökünü içerir ama doğru
   ifade) ve "kredi kartı" (17/62 kayıtta meşru ürün adı) istisnaları.
2. Zeynep'in tam scraper verisi (129 gerçek kayıt, 9 banka): "kredi
   skoru/notu/politikası" (sektör-standart terimler, katılım bankaları
   da kullanıyor) ve "açık kredi"/"veresiye kredi" (kredi'den ÖNCE gelen
   meşru bileşikler - önceki istisna mantığı yalnızca SONRASINA
   bakıyordu) istisnaları bu taramada ortaya çıktı.
"""

import re

# Her giris: kok (yakalanacak kelime govdesi), standart_terim (onerilecek
# katilim bankaciligi karsiligi), guvenli_ek_onekleri (kok+bu onekle
# baslayan kelimeler meşru sayilir, ornek: faiz+siz="faizsiz"),
# guvenli_sonraki_kelime_onekleri (kokten hemen sonraki kelime bu onekle
# basliyorsa meşru sayilir, ornek: "kredi" + "kart..."),
# guvenli_onceki_kelimeler (kokten hemen ONCEKI kelime tam olarak buysa
# meşru sayilir, ornek: "acik" + "kredi")
GELENEK_TERIM_ESLESTIRMELERI = [
    {
        "kok": "faiz",
        "standart_terim": "Kâr Payı",
        "guvenli_ek_onekleri": ["siz"],
        "guvenli_sonraki_kelime_onekleri": [],
        "guvenli_onceki_kelimeler": [],
    },
    {
        "kok": "mevduat",
        "standart_terim": "Katılım Fonu",
        "guvenli_ek_onekleri": [],
        "guvenli_sonraki_kelime_onekleri": [],
        "guvenli_onceki_kelimeler": [],
    },
    {
        "kok": "kredi",
        "standart_terim": "Finansman",
        "guvenli_ek_onekleri": [],
        # "kredi karti/kartiyla" (urun adi), "kredi bakiyesi/limiti" (kart
        # ekosisteminde yerlesik jargon - Altin Veri Seti TOM-002), "kredi
        # skoru/notu" ve "kredi politikasi" (sektor-standart, katilim
        # bankalari da kullanir - Zeynep'in 129 kayitlik verisinde
        # Albaraka/Vakif Katilim/Turkiye Finans sayfalarinda gorulmustur).
        "guvenli_sonraki_kelime_onekleri": ["kart", "bakiye", "limit", "skor", "not", "politika"],
        # "acik kredi" ve "veresiye kredi" T.O.M. Bank sayfasinda gorulen,
        # kredi'den ONCE gelen mesru bileşik terimler.
        "guvenli_onceki_kelimeler": ["açık", "veresiye"],
    },
]


def turkce_kucult(metin: str) -> str:
    """str.lower() Turkce noktali buyuk 'İ' harfini duz 'i' degil, gorunmez
    bir birlesik nokta karakteriyle kucultur - bu yuzden once manuel
    degistirilir. Ayni duzeltme terminology/genisletme.py ve
    extraction/normalizer.py'de de var (bagimsiz olarak bulundu)."""
    return metin.replace("İ", "i").lower()


def _kelime_temizle(parca: str) -> str:
    """Kelime sinirindaki noktalama isaretlerini (parantez, virgul vb.)
    temizler - ornek: 'Kredi) bakiyesinin' metninde ')' karakteri
    'bakiye' onek kontrolunu bozmasin diye."""
    return parca.strip(" \t\n)(\"'”’,.;:!?-")


def terminoloji_tutarliligini_kontrol_et(yanit_metni: str) -> dict:
    """Yanıt metninde geleneksel bankacılık teriminin sızıp sızmadığını
    denetler. Meşru bileşik kullanımlar (ör. "faizsiz", "kredi kartı",
    "açık kredi") istisna tutulur.

    Döner: {"tutarli": bool, "bulunan_sorunlar": [{"gelenek_terim", "onerilen"}]}
    """
    sorunlar = []
    for eslesme_kurali in GELENEK_TERIM_ESLESTIRMELERI:
        kok = eslesme_kurali["kok"]
        for m in re.finditer(rf"\b{re.escape(kok)}\w*", yanit_metni, re.IGNORECASE):
            kelime = m.group()
            ek = kelime[len(kok):].lower()
            if any(
                ek.startswith(guvenli)
                for guvenli in eslesme_kurali["guvenli_ek_onekleri"]
            ):
                continue  # ornek: "faizsiz" -> mesru, atla

            # 30 karakterlik pencere: "kredi kartı" gibi bitisik bilesikleri
            # de "kredi ve tahsis politikaları" gibi arada 1-2 kelime olan
            # bicimleri de (Albaraka/Vakif Katilim - kredi skoru/politikasi
            # aciklama cumlesi) kapsar.
            sonraki_pencere = turkce_kucult(yanit_metni[m.end():m.end() + 30])
            if any(
                guvenli in sonraki_pencere
                for guvenli in eslesme_kurali["guvenli_sonraki_kelime_onekleri"]
            ):
                continue  # ornek: "kredi kartı" / "kredi ... politikaları" -> mesru, atla

            onceki_kelime = _kelime_temizle(yanit_metni[max(0, m.start() - 20):m.start()]).split()
            onceki_kelime = onceki_kelime[-1].lower() if onceki_kelime else ""
            if onceki_kelime in eslesme_kurali["guvenli_onceki_kelimeler"]:
                continue  # ornek: "açık kredi" -> mesru bilesik terim, atla

            sorunlar.append({
                "gelenek_terim": kelime,
                "onerilen": eslesme_kurali["standart_terim"],
            })

    return {"tutarli": len(sorunlar) == 0, "bulunan_sorunlar": sorunlar}

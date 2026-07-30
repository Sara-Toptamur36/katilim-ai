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

Altın Veri Seti'ndeki (62 gerçek kayıt) analiz iki somut istisna ortaya
çıkardı:
- "faizsiz" kelimesi "faiz" kökünü içerir ama aslında doğru/istenen bir
  ifadedir (bkz. sifir_oran_ifadesi kavramı) - flaglenmemeli.
- "kredi kartı" 62 kayıttan 17'sinde meşru bir ürün adı olarak geçiyor
  (katılım bankaları da kart ürünlerini "kredi kartı" diye pazarlıyor,
  "finansman kartı" demiyorlar) - flaglenmemeli.
"""

import re

# Her giris: kok (yakalanacak kelime govdesi), standart_terim (onerilecek
# katilim bankaciligi karsiligi), guvenli_ek_onekleri (kok+bu onekle
# baslayan kelimeler meşru sayilir, ornek: faiz+siz="faizsiz"),
# guvenli_sonraki_kelime_onekleri (kokten hemen sonraki kelime bu onekle
# basliyorsa meşru sayilir, ornek: "kredi" + "kart...")
GELENEK_TERIM_ESLESTIRMELERI = [
    {
        "kok": "faiz",
        "standart_terim": "Kâr Payı",
        "guvenli_ek_onekleri": ["siz"],
        "guvenli_sonraki_kelime_onekleri": [],
    },
    {
        "kok": "mevduat",
        "standart_terim": "Katılım Fonu",
        "guvenli_ek_onekleri": [],
        "guvenli_sonraki_kelime_onekleri": [],
    },
    {
        "kok": "kredi",
        "standart_terim": "Finansman",
        "guvenli_ek_onekleri": [],
        # "kredi karti/kartiyla" (urun adi) ve "kredi bakiyesi/limiti"
        # (kart ekosisteminde katilim bankalarinin da kullandigi yerlesik
        # jargon) mesru sayilir - Altin Veri Seti TOM-002'de gorulen
        # "kredi bakiyesi" ornegiyle dogrulandi.
        "guvenli_sonraki_kelime_onekleri": ["kart", "bakiye", "limit"],
    },
]


def terminoloji_tutarliligini_kontrol_et(yanit_metni: str) -> dict:
    """Yanıt metninde geleneksel bankacılık teriminin sızıp sızmadığını
    denetler. Meşru bileşik kullanımlar (ör. "faizsiz", "kredi kartı")
    istisna tutulur.

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

            sonraki_kelime = yanit_metni[m.end():m.end() + 20].lstrip()
            if any(
                sonraki_kelime.lower().startswith(guvenli)
                for guvenli in eslesme_kurali["guvenli_sonraki_kelime_onekleri"]
            ):
                continue  # ornek: "kredi kartı" -> mesru urun adi, atla

            sorunlar.append({
                "gelenek_terim": kelime,
                "onerilen": eslesme_kurali["standart_terim"],
            })

    return {"tutarli": len(sorunlar) == 0, "bulunan_sorunlar": sorunlar}

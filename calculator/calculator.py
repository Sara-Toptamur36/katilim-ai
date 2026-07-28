"""Hesap Makinesi Araci (Calculator Tool).

TASARIM ILKESI (rapor Bolum 5.3 / 8): Hesaplamalar LLM'e BIRAKILMAZ.
LLM aritmetikte hata yapabilir ve yaptigi hatayi fark etmez. Finansal bir
hesapta bu kabul edilemez. Bu yuzden tum hesaplar saf Python fonksiyonlariyla
deterministik olarak yapilir; LLM yalnizca sonucu cumleye doker.

Ajan Orkestratoru (Sprint 3), "hesaplama" niyeti tespit ettiginde bu modulu
cagirir -- LLM'e "su hesabi yap" demez.

ORAN BIRIMI: Katilim bankaciligi kampanyalarinda kar payi orani AYLIK verilir
(ornek: "%1,89 kar payi orani" = ayda %1,89). Bu modulun tum fonksiyonlari
aylik oran bekler. CampaignRecord'daki `kar_payi_orani_decimal` alani zaten
aylik ondalik degeri tasir (0.0189), dogrudan kullanilabilir.
"""

from dataclasses import dataclass, field

# Girdi sinirlari - anlamsiz degerlerle hesap yapilmasini onler
MAKS_VADE_AY = 480          # 40 yil; gercek kampanyalarda 120 ay tipik ust sinir
MAKS_ANAPARA = 100_000_000  # 100 milyon TL
MAKS_AYLIK_ORAN = 0.20      # aylik %20 - bunun ustu veri hatasi demektir


class HesapGirdiHatasi(ValueError):
    """Hesaplama icin gecersiz girdi verildi."""


@dataclass(frozen=True)
class TaksitSonucu:
    """Bir finansman hesabinin sonucu.

    frozen=True: sonuc uretildikten sonra degistirilemez -- yanlislikla
    uzerine yazilip yanlis sayi gosterilmesini onler.
    """

    anapara: float
    aylik_oran: float
    vade_ay: int
    aylik_taksit: float
    toplam_odeme: float
    toplam_kar_payi: float
    yontem: str = "deterministik_python"

    def ozet_metni(self) -> str:
        """Insan okunur ozet. LLM tarafindan degil, dogrudan sayilardan
        uretilir -- bu yuzden halusinasyon icermez."""
        return (
            f"{self.anapara:,.0f} TL tutarinda finansman, "
            f"aylik %{self.aylik_oran * 100:.2f} kar payi orani ve "
            f"{self.vade_ay} ay vade ile: "
            f"aylik taksit {self.aylik_taksit:,.2f} TL, "
            f"toplam geri odeme {self.toplam_odeme:,.2f} TL "
            f"(toplam kar payi {self.toplam_kar_payi:,.2f} TL)."
        )


def _girdileri_dogrula(anapara: float, aylik_oran: float, vade_ay: int) -> None:
    """Hesaba girmeden once anlamsiz degerleri reddeder.

    Sessizce yanlis sonuc uretmektense hata vermek dogrudur: kullaniciya
    yanlis bir taksit tutari gostermek, hic gostermemekten kotudur.
    """
    if anapara <= 0:
        raise HesapGirdiHatasi("Anapara pozitif olmalidir")
    if anapara > MAKS_ANAPARA:
        raise HesapGirdiHatasi(f"Anapara cok buyuk (maks {MAKS_ANAPARA:,} TL)")
    if vade_ay <= 0:
        raise HesapGirdiHatasi("Vade pozitif olmalidir")
    if vade_ay > MAKS_VADE_AY:
        raise HesapGirdiHatasi(f"Vade cok uzun (maks {MAKS_VADE_AY} ay)")
    if aylik_oran < 0:
        raise HesapGirdiHatasi("Kar payi orani negatif olamaz")
    if aylik_oran > MAKS_AYLIK_ORAN:
        raise HesapGirdiHatasi(
            f"Aylik oran cok yuksek ({aylik_oran:.4f}). "
            "Yillik oran girilmis olabilir -- bu modul AYLIK oran bekler."
        )


def aylik_taksit_hesapla(
    anapara: float, aylik_oran: float, vade_ay: int
) -> TaksitSonucu:
    """Esit taksitli (anuite) finansman hesabi.

    Formul:  taksit = P * (r * (1+r)^n) / ((1+r)^n - 1)
      P = anapara, r = aylik kar payi orani (ondalik), n = vade (ay)

    Ornek:
        >>> s = aylik_taksit_hesapla(500_000, 0.0189, 120)
        >>> round(s.aylik_taksit, 2)
        10567.32
    """
    _girdileri_dogrula(anapara, aylik_oran, vade_ay)

    if aylik_oran == 0:
        # Sifir oranli kampanya (rapor Bolum 3: "Kar payi yok" ornegi).
        # Formul 0'a bolme verirdi; bu durum ayri ele alinir.
        aylik_taksit = anapara / vade_ay
    else:
        carpan = (1 + aylik_oran) ** vade_ay
        aylik_taksit = anapara * (aylik_oran * carpan) / (carpan - 1)

    # ONEMLI: Toplam, YUVARLANMIS taksit uzerinden hesaplanir.
    # Ham (yuvarlanmamis) taksitle carpsaydik, kullaniciya gosterilen
    # "aylik taksit x vade" carpimi gosterilen "toplam odeme"yi tutmazdi --
    # kullanici bunu carpip farki gorur ve sisteme guvenmez.
    # Gercekte de musteri her ay yuvarlanmis tutari oder.
    aylik_taksit = round(aylik_taksit, 2)
    toplam_odeme = round(aylik_taksit * vade_ay, 2)

    return TaksitSonucu(
        anapara=anapara,
        aylik_oran=aylik_oran,
        vade_ay=vade_ay,
        aylik_taksit=aylik_taksit,
        toplam_odeme=toplam_odeme,
        toplam_kar_payi=round(toplam_odeme - anapara, 2),
    )


@dataclass(frozen=True)
class OdemeSatiri:
    """Odeme planinin tek bir ayi."""

    ay: int
    taksit: float
    kar_payi_kismi: float
    anapara_kismi: float
    kalan_bakiye: float


def odeme_plani_uret(
    anapara: float, aylik_oran: float, vade_ay: int
) -> list[OdemeSatiri]:
    """Ay ay odeme plani (amortisman tablosu) uretir.

    Her ay: kalan bakiyenin kar payi hesaplanir, taksitin geri kalani
    anaparadan duser. Son ayda kalan bakiye 0 olmalidir.

    Kullanim: chatbot "odeme plani goster" dedigi zaman, ve hesabin
    dogrulugunu capraz kontrol etmek icin (bkz. testler).
    """
    sonuc = aylik_taksit_hesapla(anapara, aylik_oran, vade_ay)
    taksit = sonuc.aylik_taksit

    plan: list[OdemeSatiri] = []
    kalan = float(anapara)

    for ay in range(1, vade_ay + 1):
        kar_payi_kismi = kalan * aylik_oran
        anapara_kismi = taksit - kar_payi_kismi

        if ay == vade_ay:
            # Son ayda yuvarlama farkini kapat: kalan ne ise onu ode.
            # Boylece plan her zaman tam 0 ile biter.
            anapara_kismi = kalan
            taksit_bu_ay = round(anapara_kismi + kar_payi_kismi, 2)
        else:
            taksit_bu_ay = taksit

        kalan -= anapara_kismi

        plan.append(
            OdemeSatiri(
                ay=ay,
                taksit=round(taksit_bu_ay, 2),
                kar_payi_kismi=round(kar_payi_kismi, 2),
                anapara_kismi=round(anapara_kismi, 2),
                kalan_bakiye=round(max(kalan, 0.0), 2),
            )
        )

    return plan


def maksimum_finansman_hesapla(
    aylik_butce: float, aylik_oran: float, vade_ay: int
) -> float:
    """Ters hesap: "Aylik X TL odeyebiliyorum, ne kadar finansman alabilirim?"

    Anuite formulunun anapara icin cozulmus hali:
      P = taksit * ((1+r)^n - 1) / (r * (1+r)^n)
    """
    if aylik_butce <= 0:
        raise HesapGirdiHatasi("Aylik butce pozitif olmalidir")
    _girdileri_dogrula(1, aylik_oran, vade_ay)  # oran/vade dogrulamasi

    if aylik_oran == 0:
        return round(aylik_butce * vade_ay, 2)

    carpan = (1 + aylik_oran) ** vade_ay
    anapara = aylik_butce * (carpan - 1) / (aylik_oran * carpan)
    return round(anapara, 2)


@dataclass
class KarsilastirmaSonucu:
    """Iki kampanyanin toplam maliyet karsilastirmasi."""

    secenekler: list[dict] = field(default_factory=list)
    en_dusuk_toplam_maliyet: dict | None = None
    aciklama: str = ""


def toplam_maliyet_karsilastir(secenekler: list[dict]) -> KarsilastirmaSonucu:
    """Ayni anapara icin farkli kampanyalarin toplam maliyetini karsilastirir.

    Girdi: [{"banka": "A Bankasi", "anapara": 500000,
             "aylik_oran": 0.0189, "vade_ay": 120}, ...]

    NEDEN GEREKLI: Dusuk oran her zaman ucuz demek DEGILDIR -- daha uzun
    vade, dusuk oranli bir kampanyayi toplamda daha pahali yapabilir.
    Bu fonksiyon, kullaniciya bu tuzagi somut sayilarla gosterir.
    """
    hesaplananlar = []

    for s in secenekler:
        sonuc = aylik_taksit_hesapla(
            s["anapara"], s["aylik_oran"], s["vade_ay"]
        )
        hesaplananlar.append(
            {
                "banka": s.get("banka", "?"),
                "kampanya_adi": s.get("kampanya_adi"),
                "aylik_oran_percent": round(s["aylik_oran"] * 100, 4),
                "vade_ay": s["vade_ay"],
                "aylik_taksit": sonuc.aylik_taksit,
                "toplam_odeme": sonuc.toplam_odeme,
                "toplam_kar_payi": sonuc.toplam_kar_payi,
            }
        )

    if not hesaplananlar:
        return KarsilastirmaSonucu(aciklama="Karsilastirilacak secenek yok.")

    en_ucuz = min(hesaplananlar, key=lambda h: h["toplam_odeme"])
    en_dusuk_taksit = min(hesaplananlar, key=lambda h: h["aylik_taksit"])

    aciklama = (
        f"Toplam maliyet acisindan en avantajli secenek {en_ucuz['banka']} "
        f"({en_ucuz['toplam_odeme']:,.2f} TL toplam geri odeme)."
    )
    if en_dusuk_taksit["banka"] != en_ucuz["banka"]:
        aciklama += (
            f" Ancak en dusuk AYLIK taksit {en_dusuk_taksit['banka']}'nda "
            f"({en_dusuk_taksit['aylik_taksit']:,.2f} TL) -- daha uzun vade "
            "aylik yuku azaltir ama toplam maliyeti artirir."
        )

    return KarsilastirmaSonucu(
        secenekler=sorted(hesaplananlar, key=lambda h: h["toplam_odeme"]),
        en_dusuk_toplam_maliyet=en_ucuz,
        aciklama=aciklama,
    )

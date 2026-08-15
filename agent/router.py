"""Tool Router - tespit edilen niyete gore dogru deterministik araci cagirir.

Mimari (rapor Bolum 8): Intent Detection -> TOOL ROUTER -> SQL/Calculator/
Dictionary/RAG/Fallback. Bu dosya ortadaki katmandir.

RAG: Belirli bir araca (hesaplama/sozluk/karsilastirma) uymayan serbest
bilgi sorulari `rag_aracini_cagir` ile kaynakli olarak yanitlanir. Kaynak
bulunamazsa cevap UYDURULMAZ - durum acikca bildirilir (rapor Bolum
5.7/15). Bu karar retriever katmaninda verilir
(chunking/retriever.py, abstention kurali).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from agent.intent import turkce_ascii_katla
from agent.parametre_cikar import eksik_parametreler, hesaplama_parametrelerini_cikar
from calculator.calculator import (
    HesapGirdiHatasi,
    aylik_taksit_hesapla,
    toplam_maliyet_karsilastir,
)
from comparison.compare_engine import BilinmeyenKriter, aciklama_uret, karsilastir_bellekte
from terminology.genisletme import benzer_terim_bul, gelenek_terimden_bul
from terminology.sozluk import gelenek_karsiligi_bul, sozluk_yukle

BANKALAR_JSON = Path(__file__).resolve().parents[1] / "scraper" / "config" / "bankalar.json"

_SOZLUK_SORU_KALIPLARI = ["ne demek", "nedir", "anlamina gelir", "aciklar misin", "ne anlama", "tanimi ne"]

_KRITER_ANAHTAR_KELIMELERI = {
    "en_yuksek_odul": ["en yuksek odul", "en cok odul", "en yuksek hediye"],
    "en_uzun_vade": ["en uzun vade"],
    "en_dusuk_masraf": ["en dusuk masraf", "en az masraf"],
    # "avantajli" kelimesi Sartname Md. 5.7'nin KENDI terimi ("En Avantajli
    # Kampanya") - bu yuzden HER ZAMAN kompozit kritere yonlendirilir, tek bir
    # alt kritere (ör. en dusuk oran) ozgu sayilmaz. Bu sozluk sirali okundugu
    # icin en_dusuk_kar_payi'nin "oran" temelli anahtar kelimeleriyle CAKISMAZ.
    "en_avantajli": [
        "en avantajli kampanya",
        "en avantajli",
        "hangisi daha avantajli",
        "hangi kampanya daha avantajli",
        "daha avantajli",
    ],
    "en_dusuk_kar_payi": ["en dusuk oran", "en dusuk kar payi"],
}


def _bilinen_bankalari_yukle() -> list[str]:
    """scraper/config/bankalar.json'daki kisa banka adlarini (DB'deki
    `banka` sutunuyla ayni format) doner. Zeynep yeni banka ekledikce
    bu liste otomatik buyur - burada AYRICA hardcode edilmez."""
    if not BANKALAR_JSON.exists():
        return []
    with open(BANKALAR_JSON, encoding="utf-8") as f:
        veri = json.load(f)
    return [banka["ad"] for banka in veri.values()]


def _sorudaki_kriteri_tespit_et(soru: str) -> str:
    # Katlama: anahtar kelimeler ASCII yazili ("en dusuk"), gercek soru ise
    # dogal Turkce ("en düşük") - katlama olmadan hicbir zaman eslesmez
    # (bkz. agent/intent.py'deki ayni bulgu).
    s = turkce_ascii_katla(soru)
    for kriter, kelimeler in _KRITER_ANAHTAR_KELIMELERI.items():
        if any(k in s for k in kelimeler):
            return kriter
    return "en_dusuk_kar_payi"  # varsayilan (sartname Md. 5.7 ornegi)


def _sozluk_terimini_cikar(soru: str) -> str:
    """'Kâr payı oranı ne demek?' -> 'kar payi orani'.

    NOT: Kalip cikarma ASCII katlanmis metin uzerinde yapilir (yukaridaki
    kriter tespitiyle ayni gerekce), bu yuzden donen terim de katlanmis
    olur. terminology/genisletme.py'nin benzer_terim_bul() fonksiyonu
    zaten kendi Turkce-guvenli kucultmesini yapip bulanik eslesme
    kullandigi icin (bkz. o dosyanin testleri), diyakritiksiz bir terim de
    dogru sozluk girdisini bulur."""
    s = turkce_ascii_katla(soru.strip().rstrip("?!."))
    for kalip in _SOZLUK_SORU_KALIPLARI:
        s = s.replace(kalip, "")
    return s.strip()


def hesaplama_aracini_cagir(soru: str) -> dict[str, Any]:
    """Calculator Tool: sorudan anapara/oran/vade cikarip taksit hesaplar."""
    parametreler = hesaplama_parametrelerini_cikar(soru)
    eksikler = eksik_parametreler(parametreler)
    if eksikler:
        return {
            "basarili": False,
            "cevap": (
                "Hesaplama icin şu bilgiler eksik: "
                + ", ".join(eksikler)
                + ". Ornek: '500.000 TL, %1,99 oranla 24 ay vadeyle taksitim ne kadar olur?'"
            ),
            "sebep": f"Eksik parametre(ler): {', '.join(eksikler)}",
        }
    try:
        sonuc = aylik_taksit_hesapla(
            parametreler["anapara"],
            parametreler["aylik_oran_percent"] / 100,
            parametreler["vade_ay"],
        )
    except HesapGirdiHatasi as e:
        return {"basarili": False, "cevap": f"Girdi hatasi: {e}", "sebep": str(e)}

    return {
        "basarili": True,
        "cevap": sonuc.ozet_metni(),
        "veri": {
            "anapara": sonuc.anapara,
            "aylik_taksit": sonuc.aylik_taksit,
            "toplam_odeme": sonuc.toplam_odeme,
            "toplam_kar_payi": sonuc.toplam_kar_payi,
        },
    }


def sozluk_aracini_cagir(soru: str) -> dict[str, Any]:
    """Dictionary Tool: terminoloji sozlugunde birebir/benzer terim arar.

    IKI YONLU ARAR (Md. 5.5 - kavramlarin dogru siniflandirilmasi):
      1) Ileri  - kullanici KATILIM terimini sorar ("kar payi orani nedir?")
      2) Ters   - kullanici GELENEK terimini sorar ("faiz orani nedir?")

    Ters arama olculerek eklendi: onceden "Faiz orani nedir?" sorusuna
    sistem "'faiz orani' terimini sozlugumde bulamadim" diyordu. Bu,
    Md. 5.5'in tam olarak ogretilmesini istedigi ayrimda sessiz kalmakti -
    kullanicinin bildigi terim genelde gelenek terimdir. Artik ceviri
    yonu acikca ogretiliyor.
    """
    terim = _sozluk_terimini_cikar(soru)
    if not terim:
        return {
            "basarili": False,
            "cevap": "Hangi terimi sormak istediginizi anlayamadim.",
            "sebep": "Sozluk sorgusu icin terim cikarilamadi",
        }

    sozluk = sozluk_yukle()
    anahtar, skor = benzer_terim_bul(terim, sozluk)
    if anahtar is not None:
        gelenek = gelenek_karsiligi_bul(anahtar, sozluk)
        standart = sozluk[anahtar]["standart_terim"]
        cevap = f"{standart}, geleneksel bankacilikta '{gelenek}' kavramina karsilik gelir."
        return {
            "basarili": True,
            "cevap": _aciklama_ekle(cevap, sozluk[anahtar]),
            "veri": {"anahtar": anahtar, "eslesme_skoru": round(skor, 2), "yon": "ileri"},
        }

    ters_anahtar, ters_skor = gelenek_terimden_bul(terim, sozluk)
    if ters_anahtar is not None:
        standart = sozluk[ters_anahtar]["standart_terim"]
        gelenek = gelenek_karsiligi_bul(ters_anahtar, sozluk)
        cevap = (
            f"'{gelenek}' geleneksel bankacilik terimidir. "
            f"Katilim bankaciligindaki karsiligi: {standart}."
        )
        return {
            "basarili": True,
            "cevap": _aciklama_ekle(cevap, sozluk[ters_anahtar]),
            "veri": {
                "anahtar": ters_anahtar,
                "eslesme_skoru": round(ters_skor, 2),
                "yon": "ters",
            },
        }

    return {
        "basarili": False,
        "cevap": f"'{terim}' terimini sozlugumde bulamadim.",
        "sebep": (
            f"Ne katilim terimi ne gelenek karsiligi esige ulasti "
            f"(ileri={skor:.2f}, ters={ters_skor:.2f})"
        ),
    }


def _aciklama_ekle(cevap: str, kavram: dict) -> str:
    """Sozluk yanitina kavramin tanimini ve tanim kaynagini ekler.

    Kaynak bilerek yaziliyor: Md. 5.5 kavramlarin dogru yorumlanmasini
    istiyor, jüri de "bu tanim nereden geliyor?" diye soracaktir. Kaynak
    sozlukte zaten var (terminology/sozluk.json `kaynak` alani), yanitta
    gosterilmemesi icin bir sebep yok.
    """
    parcalar = [cevap]
    if kavram.get("aciklama"):
        parcalar.append(kavram["aciklama"])
    if kavram.get("kaynak"):
        parcalar.append(f"(Kaynak: {kavram['kaynak']})")
    return " ".join(parcalar)


def karsilastirma_aracini_cagir(soru: str, kayit_getirici) -> dict[str, Any]:
    """SQL/Karsilastirma Tool: sorudaki banka adlarini tespit edip
    karsilastirir.

    kayit_getirici: banka adi -> CampaignRecord listesi doner fonksiyon.
    GERCEK_VERI_AKTIF durumuna gore api/main.py bunu mock ya da DB
    kaynagina baglar (bkz. agent/orchestrator.py).
    """
    # Katlama iki yonlu de yapilir: kullanici diyakritiksiz yazsa bile
    # ("Kuveyt Turk") banka adi "Kuveyt Türk" ile eslesmeli.
    s = turkce_ascii_katla(soru)
    bilinen_bankalar = _bilinen_bankalari_yukle()
    bulunan_bankalar = [
        b for b in bilinen_bankalar if turkce_ascii_katla(b) in s
    ]

    if len(bulunan_bankalar) < 2:
        return {
            "basarili": False,
            "cevap": (
                "Karsilastirma icin en az 2 banka adi gerekiyor. "
                "Şu an taninan bankalar: " + ", ".join(bilinen_bankalar)
            ),
            "sebep": f"Soruda yalnizca {len(bulunan_bankalar)} banka tespit edildi",
        }

    kayitlar = []
    for banka in bulunan_bankalar:
        kayitlar.extend(kayit_getirici(banka))

    if len(kayitlar) < 2:
        return {
            "basarili": False,
            "cevap": "Tespit edilen bankalar icin karsilastirilacak yeterli kampanya bulunamadi.",
            "sebep": "Kayit sayisi < 2",
        }

    kriter = _sorudaki_kriteri_tespit_et(soru)
    try:
        sonuc = karsilastir_bellekte(kayitlar, kriter=kriter)
    except BilinmeyenKriter as e:
        return {"basarili": False, "cevap": str(e), "sebep": str(e)}

    return {
        "basarili": True,
        "cevap": aciklama_uret(sonuc),
        "veri": {
            "kriter": kriter,
            "sonuc_sayisi": len(sonuc["sonuclar"]),
            "extraction_confidence": _ortalama_confidence(kayitlar),
            "regex_basari_orani": _regex_basari_orani(kayitlar),
        },
    }


def toplam_maliyet_aracini_cagir(soru: str, kayit_getirici) -> dict[str, Any]:
    """Toplam Maliyet Karsilastirma Tool: birden fazla bankanin AYNI anapara
    icin toplam geri odeme maliyetini karsilastirir (calculator/calculator.py::
    toplam_maliyet_karsilastir). karsilastirma_aracini_cagir'dan FARKI: o ham
    alanlari (oran/vade/masraf) tek tek siralar, bu ise GERCEK bir amortisman
    hesabi yapar - "dusuk oran = ucuz demek degildir" tuzagini somut TL ile
    gosterir (rapor Bolum 8).

    Her bankanin kar_payi_orani_decimal ve vade_ay'i KENDI kampanya
    verisinden gelir; kullanicidan yalnizca ortak bir anapara istenir.
    """
    s = turkce_ascii_katla(soru)
    bilinen_bankalar = _bilinen_bankalari_yukle()
    bulunan_bankalar = [b for b in bilinen_bankalar if turkce_ascii_katla(b) in s]

    if len(bulunan_bankalar) < 2:
        return {
            "basarili": False,
            "cevap": (
                "Toplam maliyet karsilastirmasi icin en az 2 banka adi gerekiyor. "
                "Şu an taninan bankalar: " + ", ".join(bilinen_bankalar)
            ),
            "sebep": f"Soruda yalnizca {len(bulunan_bankalar)} banka tespit edildi",
        }

    anapara = hesaplama_parametrelerini_cikar(soru)["anapara"]
    if anapara is None:
        return {
            "basarili": False,
            "cevap": (
                "Toplam maliyet karsilastirmasi icin bir anapara tutari belirtmelisiniz "
                "(ornek: '500.000 TL icin A Bankasi ile C Bankasi'nin toplam maliyetini karsilastir')."
            ),
            "sebep": "anapara sorudan cikarilamadi",
        }

    secenekler = []
    veri_eksik_bankalar = []
    for banka in bulunan_bankalar:
        kayitlar = kayit_getirici(banka)
        # Bankanin kar_payi_orani_decimal VE vade_ay'i dolu olan ILK kaydi
        # kullan - amortisman hesabi ikisi de olmadan yapilamaz.
        uygun = next(
            (
                k
                for k in kayitlar
                if getattr(k, "kar_payi_orani_decimal", None) is not None
                and getattr(k, "vade_ay", None) is not None
            ),
            None,
        )
        if uygun is None:
            veri_eksik_bankalar.append(banka)
            continue
        secenekler.append(
            {
                "banka": banka,
                "kampanya_adi": uygun.kampanya_adi,
                "anapara": anapara,
                "aylik_oran": uygun.kar_payi_orani_decimal,
                "vade_ay": uygun.vade_ay,
            }
        )

    if len(secenekler) < 2:
        return {
            "basarili": False,
            "cevap": (
                "Toplam maliyet hesabi icin gereken kar payi orani/vade bilgisi "
                f"eksik: {', '.join(veri_eksik_bankalar)}."
            ),
            "sebep": "Yeterli sayida bankada kar_payi_orani_decimal/vade_ay dolu degil",
        }

    try:
        sonuc = toplam_maliyet_karsilastir(secenekler)
    except HesapGirdiHatasi as e:
        return {"basarili": False, "cevap": str(e), "sebep": str(e)}

    return {
        "basarili": True,
        "cevap": sonuc.aciklama,
        "veri": {
            "anapara": anapara,
            "secenekler": sonuc.secenekler,
            "en_dusuk_toplam_maliyet": sonuc.en_dusuk_toplam_maliyet,
            "veri_eksik_bankalar": veri_eksik_bankalar,
        },
    }


def _erisim_zamanini_tarihe_cevir(erisim_zamani: str | None) -> str | None:
    """Chunk ustverisindeki ISO datetime string'ini ('2026-08-01T13:25:39...')
    Kaynak.belge_tarihi'nin bekledigi tarihe cevirir. Format bozuksa None
    doner - uydurma bir tarih GOSTERILMEZ."""
    if not erisim_zamani:
        return None
    try:
        return datetime.fromisoformat(erisim_zamani).date().isoformat()
    except ValueError:
        return None


def rag_aracini_cagir(soru: str) -> dict[str, Any]:
    """RAG Tool: soruyu indekslenmis banka belgelerinde arar ve KAYNAKLI
    yanit uretir.

    TEMBEL IMPORT: chunking.retriever, sentence_transformers'i cekiyor
    (olculdu: yalnizca import ~55 sn). Modul basinda import edilseydi,
    RAG'e hic dokunmayan her API acilisi ve her test bu bedeli oderdi.

    LLM KULLANILMIYOR: Bu katman, bulunan kaynak parcalarini dogrudan
    dondurur - uzerine serbest metin URETMEZ. Boylece halusinasyon
    yapisal olarak imkansizdir: kullaniciya gosterilen her cumle bir
    kaynak belgeden birebir gelir. (LLM ile ozetleme sonraki adimdir ve
    ancak Verifier ile birlikte guvenli olur.)
    """
    from chunking.retriever import getir

    sonuc = getir(soru, limit=3)

    if not sonuc.yeterli_kaynak_var:
        return {
            "basarili": False,
            "cevap": (
                "Bu soruyu yanitlayacak yeterli kaynak bulamadim. "
                "Elimdeki banka kampanya belgelerinde sorunuzla eslesen "
                "bir icerik yok; yanlis bilgi vermektense cevap vermemeyi "
                "tercih ediyorum."
            ),
            "sebep": sonuc.sebep or "Yeterli kaynak bulunamadi",
            "veri": {"terim_ortusmesi": sonuc.terim_ortusmesi},
        }

    kaynaklar = []
    satirlar = []
    for i, parca in enumerate(sonuc.parcalar, 1):
        ustveri = parca.get("ustveri") or {}
        satirlar.append(f"{i}. {ustveri.get('metin', '')}")
        kaynaklar.append(
            {
                "banka": ustveri.get("banka"),
                "kampanya_adi": ustveri.get("kampanya_adi"),
                "kaynak_url": ustveri.get("kaynak_url"),
                # DENETIM BULGUSU (11 Agu): bu iki alan Kaynak semasinda vardi
                # ama burada hic set edilmiyordu, Pydantic sessizce None
                # birakiyordu - audit panelindeki retriever_sonuclari (ayni
                # veriden, agent/orchestrator.py) doluyken ana kaynaklar
                # listesi bos gorunuyordu. chunk_id icin ayri bir Qdrant point
                # ID'si tutulmuyor, retriever_sonuclari ile AYNI konvansiyonla
                # kaynak_url kullanilir (bkz. orchestrator.py).
                "chunk_id": ustveri.get("kaynak_url"),
                "belge_tarihi": _erisim_zamanini_tarihe_cevir(ustveri.get("erisim_zamani")),
                "similarity_score": round(parca.get("skor", 0.0), 4),
                "metin": ustveri.get("metin", ""),
            }
        )

    return {
        "basarili": True,
        "cevap": "Kaynaklarda bulduklarim:\n" + "\n".join(satirlar),
        "kaynaklar": kaynaklar,
        "veri": {
            "terim_ortusmesi": sonuc.terim_ortusmesi,
            "eslesen_terimler": sonuc.eslesen_terimler,
            "parca_sayisi": len(sonuc.parcalar),
        },
    }


def _ortalama_confidence(kayitlar: list) -> float | None:
    """Karsilastirmada kullanilan kayitlarin cikarim guven skorlarinin
    ortalamasi - Juri Audit Paneli'nin extraction_confidence alani icin
    (rapor Bolum 10.2). Hicbir kayitta confidence yoksa None doner."""
    degerler = [k.confidence for k in kayitlar if k.confidence is not None]
    return round(sum(degerler) / len(degerler), 4) if degerler else None


def _regex_basari_orani(kayitlar: list) -> float | None:
    """Karsilastirmada kullanilan kayitlarin ne kadarinin regex motoruyla
    (extraction/regex_extractor.py) zenginlestirildigini gosterir - hala
    ham/cikarim yapilmamis kayitlarin oranini seffaf sekilde ortaya koyar."""
    if not kayitlar:
        return None
    regex_ile = sum(1 for k in kayitlar if k.cikarim_yontemi and k.cikarim_yontemi.value == "regex")
    return round(regex_ile / len(kayitlar), 4)

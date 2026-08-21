"""RAG degerlendirme soru setini uretir (gorev 22: 100-200 soru).

--------------------------------------------------------------------------
NEDEN SADECE "DAHA COK SORU" DEGIL
--------------------------------------------------------------------------
Onceki olcum, her kampanyanin ADINI sorgu olarak kullaniyordu:

    sorgu  = "Egitim Harcamalarinizda 5 Taksit Firsati"
    belge  = "Egitim Harcamalarinizda 5 Taksit Firsati ..."

Yani sorgu, belgenin BASLIGININ TA KENDISIYDI. Bu mumkun olan EN KOLAY
gorevdir ve gercek kullaniciyi temsil etmez - kimse kampanya basligini
birebir yazmaz. Olculen %93,75'lik Recall, gercek dunyada beklenecek
degerin ustunde bir tahmindir.

Bu yuzden set yalnizca buyutulmedi, ZORLASTIRILDI ve KATEGORILERE
ayrildi. Deger, tek bir ortalama sayida degil kategoriler ARASINDAKI
FARKTADIR: "tam ad" ile "dogal soru" arasindaki dusus, retrieval'in
gercek zayifligini gosterir.

--------------------------------------------------------------------------
KATEGORILER
--------------------------------------------------------------------------
    tam_ad          Kampanya adinin birebir kendisi (eski davranis, taban)
    kismi_ad        Adin yalnizca ilk anlamli kelimeleri
    banka_ve_konu   "Kuveyt Turk tasit finansmani" - ad hic gecmez
    dogal_soru      Elle yazilmis, kullanicinin soracagi bicimde
    alan_disi       Bankacilikla ilgisiz - dogru cevap CEKIMSERLIK
    alan_ici_kapsam_disi   Katilim bankaciligi sorusu ama korpusta yok

--------------------------------------------------------------------------
COKLU DOGRU CEVAP
--------------------------------------------------------------------------
Turetilmis sorgularin BIRDEN FAZLA dogru cevabi olabilir: "Kuveyt Turk
tasit finansmani" o bankanin tum tasit kampanyalarina uyar. Bu yuzden
her kayitta `beklenen_sluglar` bir LISTEDIR. Tek dogru cevap varsaymak,
dogru getirilen bir belgeyi "kacirildi" diye sayardi - yani olcumu
haksiz yere dusururdu.

--------------------------------------------------------------------------
YER GERCEGI UYDURULMUYOR
--------------------------------------------------------------------------
Turetilmis sorularin cevabi, sorunun turetildigi ALTIN KAYITTIR - elle
dogrulanmis veriden gelir. Elle yazilan sorular (`dogal_soru`) ise
altin kaydin ayirt edici ozelligine baglanir ve `kaynak: "elle"` diye
isaretlenir ki hangi kismin insan eliyle yazildigi denetlenebilsin.

Kullanim:
    python -m scraper.scripts.rag_soru_seti_uret
"""

from __future__ import annotations

import json
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent.parent
GOLD = KOK / "gold_dataset" / "altin_veri_seti.json"
CIKTI = KOK / "gold_dataset" / "rag_soru_seti.json"

_SAHTE_ONEKLER = ("A-", "B-", "C-", "D-")

# Ad kisaltilirken atilan, ayirt edici olmayan kelimeler.
_ETKISIZ = {
    "ve", "ile", "icin", "ozel", "yeni", "firsati", "firsat", "kampanyasi",
    "kampanya", "kampanyalari", "avantajli", "avantaj", "da", "de", "bir",
}

# --------------------------------------------------------------------------
# ELLE YAZILAN SORULAR
# --------------------------------------------------------------------------
# Her biri BELIRLI bir altin kayda baglanir (kayit_id). Kullanicinin
# soracagi bicimde yazilmislardir; kampanya adini icermezler.
_ELLE_DOGAL_SORULAR: list[tuple[str, str]] = [
    # DIKKAT: Her soru, bagli oldugu altin kaydin GERCEK icerigine gore
    # yazilmistir. Ilk taslakta 10 sorunun 6'si yanlis kayda baglanmisti
    # (ör. ZK-001 "saglik taksiti" sanilmisti, oysa Bankkart Lira
    # kampanyasi) - yanlis yer gercegi, olcumu sessizce bozar. Yeni soru
    # eklerken kampanya adi MUTLAKA dogrulanmali.
    ("KT-002", "Kuveyt Türk'te TOGG almak için finansman var mı?"),
    ("KT-004", "Umre için vade farksız taksit yapan banka var mı?"),
    ("KT-003", "Çiftçilere yönelik finansman desteği hangi bankada var?"),
    ("KT-005", "Mobilden müşteri olursam mil kazanabilir miyim?"),
    ("AL-003", "Yurt dışı çıkış harcı öderken Worldpuan kazanabilir miyim?"),
    ("AL-005", "Sağlık harcamalarıma vade farksız taksit yapan katılım bankası hangisi?"),
    ("VK-004", "Otel rezervasyonunda indirim sağlayan kampanya var mı?"),
    ("VK-007", "Hisse senedi işlemlerinde komisyon indirimi veren banka hangisi?"),
    ("TF-002", "Emekliyim, promosyon veren katılım bankası var mı?"),
    ("TF-007", "Hesap işletim ücreti almayan katılım bankası hangisi?"),
    ("ZK-004", "Okul ödemelerine ek taksit yapan banka hangisi?"),
    ("ZK-008", "Elektrikli araç şarjında puan kazandıran kampanya var mı?"),
    ("TEK-005", "İlk kart harcamamın yarısını iade eden kampanya hangisinde?"),
    ("TEK-007", "Emeklilere özel ayrıcalık sunan katılım bankası var mı?"),
    ("DK-003", "Alışveriş yaparken altın biriktirebileceğim bir ürün var mı?"),
    ("DK-006", "Hepsiburada'da peşin fiyatına taksit imkânı hangi bankada?"),
    ("HF-002", "Dijital üyelik ödemelerinde nakit iade veren kart hangisi?"),
    ("HF-003", "Gümüş alım satımında makas avantajı sunan banka var mı?"),
    ("TOM-002", "Özel okul ödemesini vade farksız taksitlendirebilir miyim?"),
    ("TOM-003", "Market alışverişlerinde iade veren katılım bankası hangisi?"),
]

# --------------------------------------------------------------------------
# ALAN DISI - dogru cevap CEKIMSERLIKTIR
# --------------------------------------------------------------------------
_ALAN_DISI = [
    "Uzay istasyonunda yerçekimi nasıl ölçülür?",
    "Mercimek çorbası tarifi nedir?",
    "Dünyanın en yüksek dağı hangisidir?",
    "Python'da liste nasıl sıralanır?",
    "Yarın hava durumu nasıl olacak?",
    "Fotosentez hangi organelde gerçekleşir?",
    "İstanbul'dan Ankara'ya tren kaç saat sürer?",
    "Bir futbol maçı kaç dakikadır?",
    "Kedilerin ortalama ömrü ne kadardır?",
    "Piyanoda do notası nerededir?",
    "Roman türünün özellikleri nelerdir?",
    "Çamaşır makinesi nasıl temizlenir?",
    "Güneş sistemindeki gezegen sayısı kaçtır?",
    "Matematikte türev nasıl alınır?",
    "Antik Yunan'da demokrasi ne zaman başladı?",
]

# --------------------------------------------------------------------------
# ALAN ICI AMA KAPSAM DISI - daha ZOR cekimserlik vakalari
# --------------------------------------------------------------------------
# Bunlar gercek katilim bankaciligi sorularidir; sistem alan icinde
# oldugu icin "yakin" parcalar bulabilir ve cevap uretmeye EGILIMLIDIR.
# Dogru cevap yine cekimserliktir.
#
# SECIM GEREKCESI (tahmin degil, korpusun YAPISAL ozelligi): korpus
# yalnizca KAMPANYA sayfalarindan olusur (scraper/raw_data/*/json).
# Urun sartnameleri, hesap acilis prosedurleri, sube bilgileri, mevzuat
# metinleri hic toplanmadi - dolayisiyla bu sorularin cevabi korpusta
# BULUNAMAZ. Kampanya sayfasi olmayan konular bilerek secildi.
_ALAN_ICI_KAPSAM_DISI = [
    "Katılım bankasında altın hesabı nasıl açılır?",
    "Katılım bankacılığında danışma kurulu kimlerden oluşur?",
    "Kâr payı dağıtımı hangi sıklıkta yapılır?",
    "Katılım bankasında hesap açmak için hangi belgeler gerekir?",
    "En yakın şubenin adresi nedir?",
    "İnternet bankacılığı şifremi unuttum, nasıl yenilerim?",
    "Katılım bankaları TMSF güvencesi kapsamında mıdır?",
    "Mudârabe ile muşâraka arasındaki fark nedir?",
    "Yatırım hesabımdaki bakiyeyi nasıl öğrenirim?",
    "Kredi kartı limitimi nasıl artırabilirim?",
]


def _gercek_kayitlar() -> list[dict]:
    with open(GOLD, encoding="utf-8") as f:
        kayitlar = json.load(f)
    return [
        k for k in kayitlar
        if not k["kayit_id"].startswith(_SAHTE_ONEKLER) and k.get("kaynak_url")
    ]


def _slug(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def _anlamli_kelimeler(ad: str) -> list[str]:
    return [k for k in ad.split() if k.lower().strip("'’!,.") not in _ETKISIZ]


def _kismi_ad(ad: str) -> str | None:
    """Adin ilk 3 anlamli kelimesi. Ad zaten kisaysa None - kisaltilmamis
    bir ad 'kismi' kategorisine girmez, tam_ad'in kopyasi olurdu."""
    kelimeler = _anlamli_kelimeler(ad)
    if len(kelimeler) <= 3:
        return None
    return " ".join(kelimeler[:3])


def _tur_metni(kampanya_turu: str | None) -> str | None:
    """"Tasit Finansmani Kampanyasi" -> "tasit finansmani"."""
    if not kampanya_turu or kampanya_turu == "Belirlenemedi":
        return None
    kelimeler = [k for k in kampanya_turu.split() if k.lower() != "kampanyasi"]
    return " ".join(kelimeler).lower() if kelimeler else None


def soru_seti_uret() -> list[dict]:
    kayitlar = _gercek_kayitlar()
    sorular: list[dict] = []

    # --- tam_ad + kismi_ad (kayit basina) ---
    for k in kayitlar:
        ad = (k.get("kampanya_adi") or "").strip()
        if not ad:
            continue
        slug = _slug(k["kaynak_url"])

        sorular.append({
            "soru": ad,
            "kategori": "tam_ad",
            "beklenen_sluglar": [slug],
            "kayit_id": k["kayit_id"],
            "kaynak": "turetilmis",
        })

        kisa = _kismi_ad(ad)
        if kisa:
            sorular.append({
                "soru": kisa,
                "kategori": "kismi_ad",
                "beklenen_sluglar": [slug],
                "kayit_id": k["kayit_id"],
                "kaynak": "turetilmis",
            })

    # --- banka_ve_konu (COKLU dogru cevap) ---
    # Ayni banka+tur birden fazla kampanyaya sahipse hepsi gecerli cevaptir.
    kumeler: dict[tuple[str, str], list[dict]] = {}
    for k in kayitlar:
        tur = _tur_metni(k.get("kampanya_turu"))
        banka = k.get("banka")
        if not tur or not banka:
            continue
        kumeler.setdefault((banka, tur), []).append(k)

    for (banka, tur), grup in sorted(kumeler.items()):
        sorular.append({
            "soru": f"{banka} {tur}",
            "kategori": "banka_ve_konu",
            "beklenen_sluglar": sorted({_slug(g["kaynak_url"]) for g in grup}),
            "kayit_id": grup[0]["kayit_id"],
            "kaynak": "turetilmis",
            "not": f"{len(grup)} kampanya gecerli cevaptir",
        })

    # --- dogal_soru (elle) ---
    id_ile = {k["kayit_id"]: k for k in kayitlar}
    for kayit_id, soru in _ELLE_DOGAL_SORULAR:
        kayit = id_ile.get(kayit_id)
        if kayit is None:
            # Altin kayit degismis/silinmis olabilir - SESSIZCE atlanmaz.
            print(f"  UYARI: {kayit_id} altin veri setinde yok, soru atlandi: {soru}")
            continue
        sorular.append({
            "soru": soru,
            "kategori": "dogal_soru",
            "beklenen_sluglar": [_slug(kayit["kaynak_url"])],
            "kayit_id": kayit_id,
            "kaynak": "elle",
        })

    # --- cekimserlik beklenen sorular (beklenen slug YOK) ---
    for soru in _ALAN_DISI:
        sorular.append({
            "soru": soru,
            "kategori": "alan_disi",
            "beklenen_sluglar": [],
            "kayit_id": None,
            "kaynak": "elle",
        })

    for soru in _ALAN_ICI_KAPSAM_DISI:
        sorular.append({
            "soru": soru,
            "kategori": "alan_ici_kapsam_disi",
            "beklenen_sluglar": [],
            "kayit_id": None,
            "kaynak": "elle",
        })

    return _tekillestir(sorular)


def _tekillestir(sorular: list[dict]) -> list[dict]:
    """Ayni (kategori, soru) ciftini BIRLESTIRIR, beklenenleri birlestirir.

    BULGU: iki FARKLI kampanyanin ilk uc anlamli kelimesi ayni olabiliyor -
    Ziraat Katilim ve Emlak Katilim'in "Elektrikli Arac Sarj" kampanyalari
    gibi. Bu sorgunun IKI dogru cevabi vardir.

    Tekrar birakmak iki hataya yol acardi: (1) o sorgu olcumde iki kat
    agirlik alirdi, (2) her kopya tek bir slug bekledigi icin dogru
    getirilen belge yarisinda "kacirildi" sayilirdi.
    """
    birlesik: dict[tuple[str, str], dict] = {}
    for s in sorular:
        anahtar = (s["kategori"], s["soru"].strip().lower())
        if anahtar in birlesik:
            mevcut = birlesik[anahtar]
            mevcut["beklenen_sluglar"] = sorted(
                set(mevcut["beklenen_sluglar"]) | set(s["beklenen_sluglar"])
            )
            mevcut["not"] = (
                f"{len(mevcut['beklenen_sluglar'])} kampanya gecerli cevaptir"
            )
        else:
            birlesik[anahtar] = dict(s)
    return list(birlesik.values())


def main() -> None:
    sorular = soru_seti_uret()

    dagilim: dict[str, int] = {}
    for s in sorular:
        dagilim[s["kategori"]] = dagilim.get(s["kategori"], 0) + 1

    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(sorular, f, ensure_ascii=False, indent=2)

    print(f"Soru seti yazildi: {CIKTI.relative_to(KOK)}")
    print(f"Toplam: {len(sorular)} soru\n")
    for kategori, adet in sorted(dagilim.items(), key=lambda x: -x[1]):
        print(f"  {kategori:24} {adet:>4}")


if __name__ == "__main__":
    main()

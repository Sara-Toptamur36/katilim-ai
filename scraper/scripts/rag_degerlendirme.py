"""RAG retrieval degerlendirmesi - Recall@k ve abstention dogrulugu.

NEDEN: "RAG kurduk" demek yeterli degildir; jurinin gormesi gereken sey
retrieval'in OLCULMUS kalitesidir. Bu script iki soruyu cevaplar:

  1. RECALL@k - Bir kampanya hakkinda soru sorulunca, O kampanyanin
     belgesi ilk k sonuc icinde geliyor mu?

  2. ABSTENTION DOGRULUGU - Cevabi kaynaklarda OLMAYAN bir soruda sistem
     dogru bicimde "bilmiyorum" diyor mu? (rapor Bolum 5.7/15)

SORU SETI (gorev 22): gold_dataset/rag_soru_seti.json - 186 soru, ALTI
KATEGORIDE. Onceki olcum yalnizca kampanya ADLARINI sorgu yapiyordu;
yani sorgu, belgenin BASLIGININ TA KENDISIYDI - mumkun olan en kolay
gorev. Yeni set bunu bir TABAN kategorisi olarak korur ama yaninda
kismi ad, banka+konu ve elle yazilmis DOGAL SORULAR da olcer.

Sonuclar KATEGORI BAZINDA raporlanir. Tek bir ortalama vermek, kolay
kategorinin arkasina zor kategoriyi gizlerdi; degerli bilgi kategoriler
ARASINDAKI FARKTIR.

YER GERCEGI uydurulmaz: turetilmis sorularin cevabi, sorunun turetildigi
elle dogrulanmis altin kayittir. Elle yazilan sorular da belirli bir
altin kayda baglidir (bkz. scraper/scripts/rag_soru_seti_uret.py).

Kullanim:
    docker compose up -d qdrant
    python -m chunking.indeksleyici          # once indeks kurulmali
    python -m scraper.scripts.rag_degerlendirme
"""

from __future__ import annotations

import json
from pathlib import Path

GOLD = Path(__file__).resolve().parent.parent.parent / "gold_dataset" / "altin_veri_seti.json"
SORU_SETI = Path(__file__).resolve().parent.parent.parent / "gold_dataset" / "rag_soru_seti.json"

# Cevabi kaynaklarda olmayan kategoriler - dogru cevap CEKIMSERLIKTIR.
# Ikisi AYRI raporlanir: "alan_disi" (uzay, yemek tarifi) kolaydir;
# "alan_ici_kapsam_disi" ise gercek bir katilim bankaciligi sorusudur ve
# sistem yakin parcalar bulup cevap uretmeye EGILIMLIDIR - asil sinav odur.
CEKIMSERLIK_KATEGORILERI = ("alan_disi", "alan_ici_kapsam_disi")


def soru_setini_yukle() -> list[dict]:
    """Kategorili degerlendirme setini okur (scraper/scripts/
    rag_soru_seti_uret.py uretir). Dosya yoksa acikca soyler - sessizce
    eski/dar sete dusmek olcumu yaniltirdi."""
    if not SORU_SETI.exists():
        raise FileNotFoundError(
            f"Soru seti bulunamadi: {SORU_SETI} - "
            "once uretin: python -m scraper.scripts.rag_soru_seti_uret"
        )
    with open(SORU_SETI, encoding="utf-8") as f:
        return json.load(f)


# Sahte (A/B/C/D Bankasi) kayitlar gercek scraper verisinde yok
_SAHTE_ONEKLER = ("A-", "B-", "C-", "D-")


def _gercek_altin_kayitlar() -> list[dict]:
    with open(GOLD, encoding="utf-8") as f:
        kayitlar = json.load(f)
    return [
        k
        for k in kayitlar
        if not k["kayit_id"].startswith(_SAHTE_ONEKLER) and k.get("kaynak_url")
    ]


def _url_eslesiyor_mu(beklenen: str, bulunan: str | None) -> bool:
    """URL'ler protokol/www farkiyla yazilabildigi icin son parca
    (kampanya slug'i) uzerinden karsilastirilir."""
    if not bulunan:
        return False
    return beklenen.rstrip("/").split("/")[-1] == bulunan.rstrip("/").split("/")[-1]


def _indekste_olan_sluglar() -> set[str]:
    """Scraper verisinde (dolayisiyla indekste) gercekten bulunan kampanya
    slug'lari."""
    import glob

    kok = Path(__file__).resolve().parent.parent / "raw_data"
    sluglar = set()
    for dosya in glob.glob(str(kok / "*" / "json" / "*.json")):
        try:
            with open(dosya, encoding="utf-8") as f:
                kayit = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        slug = (kayit.get("url") or "").rstrip("/").split("/")[-1]
        if slug:
            sluglar.add(slug)
    return sluglar


def kategori_bazli_recall_olc(k: int = 5) -> dict:
    """Her KATEGORI icin ayri Recall@k.

    Tek bir ortalama sayi vermek yaniltici olurdu: kategoriler farkli
    zorluktadir ve degerli bilgi aralarindaki FARKTIR. "tam_ad" ile
    "dogal_soru" arasindaki dusus, retrieval'in gercek zayifligidir.

    OLCUM KAPSAMI: yalnizca beklenen belgesi GERCEKTEN INDEKSTE OLAN
    sorular olculur (bkz. asagidaki `mevcut` suzgeci). Altin Veri Seti
    28-29 Temmuz'da toplandi; bazi kampanyalar o gunlerde bankanin
    sitesinden kaldirildi. Indekste olmayan bir belgeyi "bulunamadi"
    saymak retrieval'i degil VERI ESKIMESINI olcerdi.

    COKLU DOGRU CEVAP: `beklenen_sluglar` bir listedir; ilk k sonuctan
    HERHANGI BIRI listede varsa isabet sayilir.
    """
    from chunking.retriever import getir

    sorular = soru_setini_yukle()
    mevcut = _indekste_olan_sluglar()

    kategoriler: dict[str, dict] = {}
    kacirilanlar: list[dict] = []
    kapsam_disi_eskimis = 0

    for kayit in sorular:
        kategori = kayit["kategori"]
        if kategori in CEKIMSERLIK_KATEGORILERI:
            continue  # bunlarin dogru cevabi cekimserlik, recall'a girmez

        beklenen = [s_ for s_ in kayit["beklenen_sluglar"] if s_ in mevcut]
        if not beklenen:
            kapsam_disi_eskimis += 1
            continue

        ozet = kategoriler.setdefault(kategori, {"isabet": 0, "toplam": 0})
        ozet["toplam"] += 1

        sonuc = getir(kayit["soru"], limit=k)
        bulunan = {
            (p.get("ustveri") or {}).get("kaynak_url", "").rstrip("/").split("/")[-1]
            for p in sonuc.parcalar
        }
        if bulunan & set(beklenen):
            ozet["isabet"] += 1
        else:
            kacirilanlar.append({
                "kategori": kategori,
                "soru": kayit["soru"][:70],
                "kayit_id": kayit.get("kayit_id"),
            })

    for ozet in kategoriler.values():
        ozet["recall"] = (
            round(ozet["isabet"] / ozet["toplam"] * 100, 2) if ozet["toplam"] else 0.0
        )

    toplam_isabet = sum(o["isabet"] for o in kategoriler.values())
    toplam_sorgu = sum(o["toplam"] for o in kategoriler.values())

    return {
        "k": k,
        "kategoriler": kategoriler,
        "genel_recall": (
            round(toplam_isabet / toplam_sorgu * 100, 2) if toplam_sorgu else 0.0
        ),
        "toplam_sorgu": toplam_sorgu,
        "kacirilan": kacirilanlar,
        "kapsam_disi_eskimis": kapsam_disi_eskimis,
    }


def abstention_olc() -> dict:
    """Cevabi kaynaklarda OLMAYAN sorularda sistem cekimser kaliyor mu?

    Iki kategori AYRI raporlanir - ortalamak, zor vakayi kolay vakanin
    arkasina gizlerdi (bkz. CEKIMSERLIK_KATEGORILERI).
    """
    from chunking.retriever import getir

    sorular = soru_setini_yukle()
    sonuclar: dict[str, dict] = {}

    for kategori in CEKIMSERLIK_KATEGORILERI:
        kume = [s_ for s_ in sorular if s_["kategori"] == kategori]
        dogru = 0
        yanlis: list[dict] = []

        for kayit in kume:
            sonuc = getir(kayit["soru"], limit=3)
            if sonuc.yeterli_kaynak_var:
                yanlis.append({
                    "soru": kayit["soru"],
                    "terim_ortusmesi": sonuc.terim_ortusmesi,
                    "eslesen_terimler": sonuc.eslesen_terimler,
                })
            else:
                dogru += 1

        sonuclar[kategori] = {
            "toplam": len(kume),
            "dogru_cekimser": dogru,
            "abstention_dogrulugu": (
                round(dogru / len(kume) * 100, 2) if kume else 0.0
            ),
            "yanlis_cevaplananlar": yanlis,
        }

    return sonuclar


if __name__ == "__main__":
    print("=== RAG Retrieval Degerlendirmesi ===" + chr(10))

    sorular = soru_setini_yukle()
    print(f"Soru seti: {len(sorular)} soru" + chr(10))

    for k in (1, 3, 5):
        son = kategori_bazli_recall_olc(k=k)
        print(f"--- Recall@{k}  (genel %{son['genel_recall']}, "
              f"{son['toplam_sorgu']} sorgu) ---")
        for kategori, ozet in sorted(
            son["kategoriler"].items(), key=lambda x: -x[1]["recall"]
        ):
            print(f"  {kategori:16} %{ozet['recall']:>6}  "
                  f"({ozet['isabet']}/{ozet['toplam']})")
        print()

    if son["kapsam_disi_eskimis"]:
        print(f"  Not: {son['kapsam_disi_eskimis']} soru olcum disi - beklenen belgesi")
        print("  indekste yok (kampanya rotasyonu). Bunlari 'bulunamadi' saymak")
        print("  retrieval'i degil veri eskimesini olcerdi." + chr(10))

    print("--- Cekimserlik (dogru cevap: cevap VERMEMEK) ---")
    for kategori, a in abstention_olc().items():
        print(f"  {kategori:22} %{a['abstention_dogrulugu']:>6}  "
              f"({a['dogru_cekimser']}/{a['toplam']})")
        for y in a["yanlis_cevaplananlar"][:5]:
            print(f"      cevap uretildi: {y['soru'][:56]} "
                  f"(ortusme={y['terim_ortusmesi']})")

    if son["kacirilan"]:
        print(chr(10) + f"--- Recall@5'te kacirilan {len(son['kacirilan'])} sorgu ---")
        for x in son["kacirilan"][:12]:
            print(f"  [{x['kategori']:14}] {x['soru']}")

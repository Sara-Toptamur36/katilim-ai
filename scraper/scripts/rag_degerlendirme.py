"""RAG retrieval degerlendirmesi - Recall@k ve abstention dogrulugu.

NEDEN: "RAG kurduk" demek yeterli degildir; jurinin gormesi gereken sey
retrieval'in OLCULMUS kalitesidir. Bu script iki soruyu cevaplar:

  1. RECALL@k - Bir kampanya hakkinda soru sorulunca, O kampanyanin
     belgesi ilk k sonuc icinde geliyor mu?

  2. ABSTENTION DOGRULUGU - Cevabi kaynaklarda OLMAYAN bir soruda sistem
     dogru bicimde "bilmiyorum" diyor mu? (rapor Bolum 5.7/15)

YER GERCEGI (ground truth) NEREDEN GELIYOR: Altin Veri Seti'ndeki
(gold_dataset/altin_veri_seti.json) elle dogrulanmis kampanyalar
kullanilir. Her kampanyanin adi bir SORGU, kaynak_url'i ise BEKLENEN
sonuctur. Boylece yer gercegi uydurulmaz - zaten elle dogrulanmis
veriden turetilir.

ABSTENTION TEST SORULARI bilerek alan disidir (uzay, yemek tarifi vb.);
bunlarin kaynaklarda karsiligi OLMADIGI kesin oldugu icin sistemin
"bilmiyorum" demesi DOGRU cevaptir.

Kullanim:
    docker compose up -d qdrant
    python -m chunking.indeksleyici          # once indeks kurulmali
    python -m scraper.scripts.rag_degerlendirme
"""

from __future__ import annotations

import json
from pathlib import Path

GOLD = Path(__file__).resolve().parent.parent.parent / "gold_dataset" / "altin_veri_seti.json"

# Kaynaklarda karsiligi KESINLIKLE olmayan sorular - sistem bunlara
# "bilmiyorum" demeli. Dogru cevap = abstention.
ALAN_DISI_SORULAR = [
    "Uzay istasyonunda yerçekimi nasıl ölçülür?",
    "Mercimek çorbası tarifi nedir?",
    "Dünyanın en yüksek dağı hangisidir?",
    "Python'da liste nasıl sıralanır?",
    "Yarın hava durumu nasıl olacak?",
]

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


def recall_olc(k: int = 5, azami_sorgu: int | None = None) -> dict:
    """Her altin kampanyanin adini sorgu yapip, o kampanyanin belgesinin
    ilk k sonuc icinde gelip gelmedigini olcer.

    OLCUM KAPSAMI (kritik): Yalnizca belgesi GERCEKTEN INDEKSTE OLAN
    kampanyalar olculur. Altin Veri Seti 28-29 Temmuz'da toplandi ve o
    kayitlarin bir kismi gunler icinde bankalarin sitesinden kaldirildi
    (kampanya rotasyonu - bkz. tests/test_scraper_regresyon.py). Indekste
    hic bulunmayan bir belgeyi "bulunamadi" diye saymak retrieval'i
    olcmez, VERI ESKIMESINI olcer ve dogrulugu haksiz yere dusuk
    gosterir. Ilk olcumde 58 kayittan 26'si bu durumdaydi.
    """
    from chunking.retriever import getir

    tum_kayitlar = _gercek_altin_kayitlar()
    mevcut_sluglar = _indekste_olan_sluglar()

    kayitlar = [
        k_
        for k_ in tum_kayitlar
        if k_["kaynak_url"].rstrip("/").split("/")[-1] in mevcut_sluglar
    ]
    kapsam_disi = len(tum_kayitlar) - len(kayitlar)

    if azami_sorgu:
        kayitlar = kayitlar[:azami_sorgu]

    isabet = 0
    kacirilan: list[dict] = []

    for kayit in kayitlar:
        sorgu = kayit.get("kampanya_adi") or ""
        if not sorgu.strip():
            continue
        sonuc = getir(sorgu, limit=k)
        bulundu = any(
            _url_eslesiyor_mu(kayit["kaynak_url"], (p.get("ustveri") or {}).get("kaynak_url"))
            for p in sonuc.parcalar
        )
        if bulundu:
            isabet += 1
        else:
            kacirilan.append(
                {
                    "kayit_id": kayit["kayit_id"],
                    "sorgu": sorgu[:70],
                    "beklenen_url": kayit["kaynak_url"],
                }
            )

    toplam = isabet + len(kacirilan)
    return {
        "k": k,
        "toplam_sorgu": toplam,
        "isabet": isabet,
        "recall": round(isabet / toplam * 100, 2) if toplam else 0.0,
        "kacirilan": kacirilan,
        # Seffaflik: kac altin kayit "sitede artik yok" oldugu icin
        # olcum disinda kaldi (rapor Bolum 5.7/15 - durum gizlenmez)
        "kapsam_disi_eskimis": kapsam_disi,
    }


def abstention_olc() -> dict:
    """Alan disi sorularda sistem dogru bicimde cevap vermiyor mu?"""
    from chunking.retriever import getir

    dogru_cekimser = 0
    yanlis_cevaplananlar: list[dict] = []

    for soru in ALAN_DISI_SORULAR:
        sonuc = getir(soru, limit=3)
        if sonuc.yeterli_kaynak_var:
            yanlis_cevaplananlar.append(
                {
                    "soru": soru,
                    "terim_ortusmesi": sonuc.terim_ortusmesi,
                    "eslesen_terimler": sonuc.eslesen_terimler,
                }
            )
        else:
            dogru_cekimser += 1

    toplam = len(ALAN_DISI_SORULAR)
    return {
        "toplam": toplam,
        "dogru_cekimser": dogru_cekimser,
        "abstention_dogrulugu": round(dogru_cekimser / toplam * 100, 2) if toplam else 0.0,
        "yanlis_cevaplananlar": yanlis_cevaplananlar,
    }


if __name__ == "__main__":
    print("=== RAG Retrieval Degerlendirmesi ===\n")

    son = None
    for k in (1, 3, 5):
        son = recall_olc(k=k)
        print(f"Recall@{k}: %{son['recall']}  ({son['isabet']}/{son['toplam_sorgu']} kampanya)")

    if son and son["kapsam_disi_eskimis"]:
        print(
            f"\n  Not: {son['kapsam_disi_eskimis']} altin kayit olcum disi birakildi - "
            "kampanyalari bankanin sitesinden kaldirilmis (rotasyon), belgeleri\n"
            "  indekste yok. Bunlari 'bulunamadi' saymak retrieval'i degil veri\n"
            "  eskimesini olcerdi (bkz. tests/test_scraper_regresyon.py)."
        )

    print()
    a = abstention_olc()
    print(
        f"Abstention dogrulugu: %{a['abstention_dogrulugu']} "
        f"({a['dogru_cekimser']}/{a['toplam']} alan disi soruda dogru sekilde cevap verilmedi)"
    )
    if a["yanlis_cevaplananlar"]:
        print("\n  UYARI - alan disi soruya cevap uretildi:")
        for y in a["yanlis_cevaplananlar"]:
            print(f"    {y['soru']} (ortusme={y['terim_ortusmesi']}, {y['eslesen_terimler']})")

    if son and son["kacirilan"]:
        print(f"\n  Recall@5'te kacirilan {len(son['kacirilan'])} kampanya:")
        for x in son["kacirilan"][:10]:
            print(f"    [{x['kayit_id']}] {x['sorgu']}")

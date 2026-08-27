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

# DENETIM BULGUSU (27.08.2026): bu betik `chunking/indeksleyici.py` ile AYNI
# hatayi tasiyordu - ortam_yukle hic import edilmiyordu. Sonuc: .env'deki
# QDRANT_YEREL_YOL okunmuyor, chunking/qdrant_baglanti.py varsayilan Docker
# sunucusuna (bos "kampanya_parcalari" koleksiyonu, 0 kayit) dusuyor ve TUM
# kategoriler sessizce %0 Recall veriyordu - retrieval degil, ortam
# yuklemesi kirikti. `import ortam_yukle` diger tum giris noktalariyla
# AYNI zorunlu kalibi izler (bkz. ortam_yukle.py docstring'i).
import ortam_yukle  # noqa: F401 - side effect: .env process ortamina yuklenir

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


def kategori_bazli_recall_olc(
    k: int = 5,
    banka_otomatik: bool | None = None,
    yeniden_sirala: bool | None = None,
    exact: bool = True,
) -> dict:
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

    `exact` VARSAYILAN TRUE (bkz. docs/rag_tasarim_ve_olcum.md, Bulgu 1 -
    "Recall@1 tek bir sayi olarak raporlanamaz" bulgusu ve orada verilen
    oneri): Qdrant'in varsayilan HNSW yaklasik aramasi Recall@1'i kosudan
    kosuya oynatiyordu (olculdu: 29/30/29, yalnizca en yakin skorlu 1.
    sirada). Bu script bir BENCHMARK'tir - tekrar uretilebilirlik dogruluk
    kadar onemlidir; uretim yolunda (agent/router.py) hizli yanit onemli
    oldugu icin `exact=False` (yaklasik) kalmaya devam eder, bu ikisi
    KASITLI olarak farkli varsayilanlar kullanir.
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

        sonuc = getir(
            kayit["soru"],
            limit=k,
            banka_otomatik=banka_otomatik,
            yeniden_sirala=yeniden_sirala,
            exact=exact,
        )
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


def abstention_olc(
    banka_otomatik: bool | None = None,
    yeniden_sirala: bool | None = None,
    exact: bool = True,
) -> dict:
    """Cevabi kaynaklarda OLMAYAN sorularda sistem cekimser kaliyor mu?

    Iki kategori AYRI raporlanir - ortalamak, zor vakayi kolay vakanin
    arkasina gizlerdi (bkz. CEKIMSERLIK_KATEGORILERI).

    `exact` VARSAYILAN TRUE - bkz. kategori_bazli_recall_olc'daki AYNI
    gerekce (Bulgu 1, HNSW yaklasik aramanin kosu-arasi oynakligi).
    """
    from chunking.retriever import getir

    sorular = soru_setini_yukle()
    sonuclar: dict[str, dict] = {}

    for kategori in CEKIMSERLIK_KATEGORILERI:
        kume = [s_ for s_ in sorular if s_["kategori"] == kategori]
        dogru = 0
        yanlis: list[dict] = []

        for kayit in kume:
            sonuc = getir(
                kayit["soru"],
                limit=3,
                banka_otomatik=banka_otomatik,
                yeniden_sirala=yeniden_sirala,
                exact=exact,
            )
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


def abstention_uctan_uca_olc() -> dict:
    """`abstention_olc`'un AYNISI ama `chunking.retriever.getir`'i degil
    `agent.orchestrator.soru_isle`'i cagirir.

    NEDEN GEREKLI (bkz. docs/rag_tasarim_ve_olcum.md, Bulgu 8'in sonundaki
    "Olcum metodolojisi notu", 23 Agustos 2026'dan beri acik bir bosluk):
    `alan_ici_kapsam_disi` sorularinin bir kismi ("hesap nasil acilir" gibi)
    `agent/intent.py::Niyet.KAPSAM_DISI` ile RAG'e HIC SORULMADAN, sabit
    durust bir cevapla kapaniyor - ama bu duzeltmenin gercek etkisi hic
    olculmedi, cunku `abstention_olc()` doguran `chunking.retriever.getir`
    niyet katmanini tamamen atlar. Bu fonksiyon, kullanicinin GORECEGI
    gercek yolu (niyet tespiti -> arac secimi -> gerekirse RAG) olcer.

    DOGRU CEKIMSER SAYILAN IKI DURUM: (1) `arac == "kapsam_disi"` -
    KAPSAM_DISI niyeti dogru tespit edildi, RAG'e hic gidilmedi; (2)
    `arac in ("rag", "fallback") and not basarili` - RAG'e gidildi ama
    kaynak bulunamadigi icin durustce cekimser kalindi. YANLIS sayilan
    tek durum: sistem bir CEVAP URETTI (`basarili=True` ve `arac` RAG/
    hesaplama/vb. - yani "bilmiyorum" DEGIL bir sey iddia etti).

    `kayit_getirici` bos liste doner: bu olcum yalnizca CEKIMSERLIK
    dogrulugunu kontrol ediyor, kaynaklara kampanya_id eklenip
    eklenmedigini degil - gercek bir DB/mock baglantisi gerekmez.

    NOT - `exact` PARAMETRESI YOK: `agent/router.py::rag_aracini_cagir`
    `chunking.retriever.getir`'i sabit varsayilanlarla (yaklasik/ANN
    arama) cagirir, uctan uca yolda bu ezilemez. Bulgu 1'deki oynaklik
    yalnizca SIRALAMAYI (Recall@1) etkiliyordu; burada olculen sey bir
    ESIK KARARI (cekimser mi degil mi), rank-hassasiyeti çok daha
    dusuktur - yine de kucuk bir gurultu payi olabilecegi kabul edilir.
    """
    from agent.orchestrator import soru_isle

    def _bos_kayit_getirici(banka: str) -> list:
        return []

    sorular = soru_setini_yukle()
    sonuclar: dict[str, dict] = {}

    for kategori in CEKIMSERLIK_KATEGORILERI:
        kume = [s_ for s_ in sorular if s_["kategori"] == kategori]
        dogru = 0
        yanlis: list[dict] = []

        for kayit in kume:
            sonuc = soru_isle(kayit["soru"], _bos_kayit_getirici)
            # soru_isle "basarili" DEGIL "fallback" doner (basarili'nin
            # tersi) - bkz. agent/orchestrator.py::soru_isle donus semasi.
            basarisiz = sonuc.get("fallback", True)
            arac = (sonuc.get("audit_ekstra") or {}).get("cagrilan_arac")
            cekimser = (arac == "kapsam_disi") or basarisiz
            if cekimser:
                dogru += 1
            else:
                yanlis.append({
                    "soru": kayit["soru"],
                    "arac": arac,
                    "cevap": (sonuc.get("cevap") or "")[:120],
                })

        sonuclar[kategori] = {
            "toplam": len(kume),
            "dogru_cekimser": dogru,
            "abstention_dogrulugu": (
                round(dogru / len(kume) * 100, 2) if kume else 0.0
            ),
            "yanlis_cevaplananlar": yanlis,
        }

    return sonuclar


# ---------------------------------------------------------------------------
# banka_ve_konu BELIRSIZLIK AYRISIMI (Bulgu 14)
# ---------------------------------------------------------------------------
# Bu kategorinin recall'u TEK BIR SAYI OLARAK YANILTICIDIR: sorular
# "banka + tur" formatinda oldugu icin korpustaki ONLARCA esdeger kampanya
# meshru cevaptir, ama `beklenen_sluglar` yalnizca ALTIN SETTE etiketlenmis
# olanlari icerir. Olculdu (25.08.2026): 28 sorunun gold'da 55 dogru cevabi
# var, korpusta esdegeri 344 - kapsama %16.
#
# YER GERCEGI GENISLETILMEZ (dairesellik): korpustaki kampanya_turu makine
# tarafindan uretilir; onu dogru cevap listesine koymak, RAG olcumunu
# cikarim motorunun kendi ciktisina bagimli kilardi. Bkz. docs/
# rag_tasarim_ve_olcum.md Bulgu 14.
#
# Bunun yerine: sorular korpustaki esdeger sayisina gore GRUPLANIR ve iki
# grubun recall'u ayri yazdirilir. Gruplama makine turunu kullanir ama
# YALNIZCA raporlama icin - dogru cevap listesi degismez.
_BELIRSIZLIK_ESIGI = 5

# Soru metnindeki tur ifadesi -> api/schemas.py KampanyaTuru degeri
_TUR_ESLEME = {
    "kart": "Kart Kampanyasi",
    "ihtiyac finansmani": "Ihtiyac Finansmani Kampanyasi",
    "yeni musteri": "Yeni Musteri Kampanyasi",
    "alisveris puani": "Alisveris Puani Kampanyasi",
    "yatirim urunu": "Yatirim Urunu Kampanyasi",
    "finansman": "Finansman Kampanyasi",
    "konut finansmani": "Konut Finansmani Kampanyasi",
    "tasit finansmani": "Tasit Finansmani Kampanyasi",
}


def _korpus_banka_tur_sayimi() -> dict[tuple[str, str], int]:
    """(banka, tur) -> korpustaki kampanya sayisi. DB yoksa bos doner."""
    try:
        from collections import Counter

        from api.db import OturumYerel
        from api.models import Kampanya
    except Exception:  # noqa: BLE001 - DB yoksa ayrisim atlanir
        return {}
    try:
        oturum = OturumYerel()
    except Exception:  # noqa: BLE001
        return {}
    try:
        return dict(
            Counter(
                (k.banka, k.kampanya_turu)
                for k in oturum.query(Kampanya).all()
                if k.kampanya_turu
            )
        )
    except Exception:  # noqa: BLE001
        return {}
    finally:
        oturum.close()


def banka_ve_konu_belirsizlik_ayrisimi(k: int = 5, exact: bool = True) -> dict | None:
    """banka_ve_konu recall'unu korpus belirsizligine gore ikiye ayirir.

    Hipotez (Bulgu 14): dusuk recall retrieval zayifligi degil, gold
    kapsamasi. Dogruysa AZ esdegerli sorularda recall yuksek, COK
    esdegerli sorularda dusuk olmalidir.

    DB erisilemezse None doner - ayrisim raporlanmaz, ana olcum etkilenmez.
    """
    sayim = _korpus_banka_tur_sayimi()
    if not sayim:
        return None

    # Gomme modeli yalnizca gercekten olcum yapilacaksa yuklensin -
    # bu dosyadaki diger olcum fonksiyonlariyla ayni desen.
    from chunking.retriever import getir

    bankalar = {b for b, _ in sayim}
    mevcut = _indekste_olan_sluglar()
    gruplar = {
        "az esdegerli": {"isabet": 0, "toplam": 0},
        "cok esdegerli": {"isabet": 0, "toplam": 0},
    }
    en_belirsizler: list[tuple[str, int, bool]] = []

    for kayit in soru_setini_yukle():
        if kayit.get("kategori") != "banka_ve_konu":
            continue
        beklenen = [s_ for s_ in kayit["beklenen_sluglar"] if s_ in mevcut]
        if not beklenen:
            continue  # indekste yok - ana olcumle AYNI kural

        soru = kayit["soru"]
        banka = next((b for b in bankalar if soru.startswith(b)), None)
        tur = next(
            (v for anahtar, v in sorted(_TUR_ESLEME.items(), key=lambda x: -len(x[0]))
             if soru.lower().endswith(anahtar)),
            None,
        )
        esdeger = sayim.get((banka, tur), 0) if banka and tur else 0

        sonuc = getir(soru, limit=k, exact=exact)
        bulunan = {
            (p.get("ustveri") or {}).get("kaynak_url", "").rstrip("/").split("/")[-1]
            for p in sonuc.parcalar
        }
        isabet = bool(bulunan & set(beklenen))

        grup = "cok esdegerli" if esdeger > _BELIRSIZLIK_ESIGI else "az esdegerli"
        gruplar[grup]["toplam"] += 1
        gruplar[grup]["isabet"] += int(isabet)
        en_belirsizler.append((soru, esdeger, isabet))

    for ozet in gruplar.values():
        ozet["recall"] = (
            round(ozet["isabet"] / ozet["toplam"] * 100, 2) if ozet["toplam"] else 0.0
        )
    en_belirsizler.sort(key=lambda x: -x[1])
    return {"gruplar": gruplar, "en_belirsiz": en_belirsizler[:3]}


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

    ayrisim = banka_ve_konu_belirsizlik_ayrisimi()
    if ayrisim:
        print("--- banka_ve_konu: belirsizlige gore ayrisim (Bulgu 14) ---")
        print("  Bu kategorinin recall'u TEK SAYI olarak yaniltici - korpusta")
        print(f"  {_BELIRSIZLIK_ESIGI}'ten fazla esdeger kampanya varsa sorgu")
        print("  ayirt edici bilgi tasimiyor demektir.")
        for ad, ozet in ayrisim["gruplar"].items():
            print(f"  {ad:16} %{ozet['recall']:>6}  "
                  f"({ozet['isabet']}/{ozet['toplam']})")
        print("  En belirsiz uc soru:")
        for soru, esdeger, isabet in ayrisim["en_belirsiz"]:
            print(f"    {soru[:34]:<36}{esdeger:>4} esdeger  "
                  f"{'isabet' if isabet else 'KACIRMA'}")
        print()

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

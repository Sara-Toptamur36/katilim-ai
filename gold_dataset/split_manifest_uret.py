"""Gold veri seti icin banka-katmanli, kampanya-sizintisiz train/test split.

NEDEN GEREKLI: Mentorluk raporu II (Bolum 5.4) "banka bazli ve zaman bazli
split kullanin: ayni kampanyanin farkli snapshot'lari train ve test arasinda
sizmamali" diyor. Bugun gold_dataset/altin_veri_seti.json'da her kampanyanin
tek bir zaman noktasi etiketli (henuz coklu-snapshot etiketleme yok), ama
split MANTIGI simdiden dogru kurulmali: gruplama daima kaynak_url uzerinden
yapilir, boylece ileride ayni kampanyanin ikinci bir zaman noktasi
etiketlendiginde otomatik olarak aynı tarafta (train VEYA test, ikisi
birden degil) kalir - split scripti tekrar yazilmasi gerekmez.

NEDEN training/ DEGIL gold_dataset/ ALTINDA: docs/kapsam_ve_veri_ayrimi.md
Bolum 4'teki karar - bos bir training/ dizini acmak, egitim yapmadigimiz
halde egitim yapiyormus izlenimi verir. Bu script bir split URETIR, egitim
YAPMAZ; dolayisiyla zaten var olan gold_dataset/ altinda kalir.

NEDEN ORNEK KAYITLAR (giren_kisi=ORNEK) HARIC TUTULUR: A/B/C/D Bankasi
kayitlari sartname Md. 5 ornek tablosundan kopyalanmis referans kayitlardir,
gercek banka verisi degildir (bkz. dosyanin kendi notlari alani). Split'e
girerlerse hem train hem test setini gercek olmayan veriyle kirletir.

NEDEN ATAMALAR DONDURULUR: onceki surum her calistirmada butun URL listesini
bastan karistiriyordu. Tohum sabit olsa da shuffle'in sonucu LISTE ICERIGINE
baglidir - etiketleme sprintinde 3 yeni kayit eklemek mevcut 103 kaydin
19'unu taraf degistiriyordu (olculdu). Bunun bedeli agirdir: test setinde
olculmus bir kayit sonraki koşuda train'e gecerse, o olcum artik bagimsiz
degildir ve "test setimize hic dokunmadik" denemez.

Bu yuzden bir URL bir kez taraf aldiktan sonra ORADA KALIR. Yalnizca daha
once gorulmemis URL'ler atanir. Etiketleme sprinti boyunca test seti
buyuyebilir ama icindekiler yer degistirmez.

Kullanim:
    python -m gold_dataset.split_manifest_uret
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

KOK = Path(__file__).resolve().parent
GOLD_DOSYASI = KOK / "altin_veri_seti.json"
CIKTI_DOSYASI = KOK / "split_manifest_v1.json"
KUME_HARITASI_DOSYASI = KOK / "kume_haritasi.json"

TEST_ORANI = 0.2


def _gercek_kayitlari_yukle() -> list[dict]:
    """Split'e girecek kayitlar: ornek OLMAYAN ve IMZALI olanlar.

    IMZASIZ KAYIT SPLIT'E GIRMEZ: etiketleme kuyrugundan acilan taslak
    satirlarin butun olculen alanlari bostur ve olcumun disindadir
    (bkz. excel_to_json, "IMZASIZ KAYIT HICBIR IDDIA TASIMAZ"). Bunlari
    split'e almak test setini olculemeyen satirlarla doldurur - 200
    taslak acildiginda test setinin buyuk bolumu hakkinda hicbir sey
    soylenemeyen kayitlardan olusurdu.

    Satir imzalandiginda kendiliginden split'e girer; atamasi
    dondurulmus oldugu icin de o andan sonra taraf degistirmez."""
    with open(GOLD_DOSYASI, encoding="utf-8") as f:
        kayitlar = json.load(f)
    return [k for k in kayitlar
            if k.get("giren_kisi") != "ORNEK" and (k.get("giren_kisi") or "").strip()]


def _kaynak_url_gruplari(kayitlar: list[dict]) -> dict[str, list[dict]]:
    """kaynak_url'ye gore gruplar - ayni kampanyanin (ileride eklenecek)
    birden fazla zaman noktasi etiketi hep AYNI grupta kalir."""
    gruplar: dict[str, list[dict]] = defaultdict(list)
    for kayit in kayitlar:
        gruplar[kayit["kaynak_url"]].append(kayit)
    return dict(gruplar)


_KUME_ANAHTAR_ONBELLEK: dict[tuple[str, ...], tuple[dict[str, str], str | None]] = {}
_SLUG_KUME_ONBELLEK: list[dict[str, str] | None] = []


def _korpus_imzasi(ham: dict) -> str:
    """Korpusun kimligi - icerik degistiyse imza da degisir."""
    return f"{len(ham)}:{max((k.get('erisim_zamani') or '') for k in ham.values())}"


def _slug_kume_haritasi() -> tuple[dict[str, str], str | None]:
    """slug -> kume anahtari.

    DISK ONBELLEGI NEDEN VAR: kumeleme banka icinde O(n^2) metin
    karsilastirmasidir ve olculdu - 424 sayfa icin 409 saniye. Testler
    split_uret'i defalarca cagirdigi icin CI'a her kosuda ~7 dakika
    ekliyordu.

    BAYAT ONBELLEK SESSIZCE KULLANILMAZ: dosyada korpus imzasi da durur.
    Korpus degistiyse onbellek yok sayilir ve kumeleme yeniden yapilir -
    aksi halde yeni kampanyalar hic kumelenmemis gorunur ve sablon
    sizintisi fark edilmeden geri gelir."""
    if _SLUG_KUME_ONBELLEK:
        harita, sorun = _SLUG_KUME_ONBELLEK[0], _SLUG_KUME_ONBELLEK[1]
        return harita or {}, sorun  # type: ignore[return-value]

    def _sakla(harita: dict[str, str] | None, sorun: str | None):
        _SLUG_KUME_ONBELLEK.extend([harita, sorun])  # type: ignore[arg-type]
        return harita or {}, sorun

    try:
        from gold_dataset.sprint_is_listesi import _ham_kampanyalar, _kumeleri_al
    except ImportError as hata:
        return _sakla(None, f"modul yuklenemedi: {hata}")

    try:
        ham = _ham_kampanyalar()
    except Exception as hata:  # noqa: BLE001
        return _sakla(None, f"korpus okunamadi: {type(hata).__name__}")
    if not ham:
        return _sakla(None, "scraper korpusu bos")

    imza = _korpus_imzasi(ham)
    if KUME_HARITASI_DOSYASI.exists():
        try:
            with open(KUME_HARITASI_DOSYASI, encoding="utf-8") as f:
                kayitli = json.load(f)
            if kayitli.get("korpus_imzasi") == imza:
                return _sakla(kayitli["harita"], None)
        except (json.JSONDecodeError, KeyError, OSError):
            pass  # bozuk onbellek yok sayilir, asagida yeniden uretilir

    slug_kume: dict[str, str] = {}
    for banka, kumeler in _kumeleri_al(ham).items():
        for sira, kume in enumerate(kumeler):
            for uye in kume["uyeler"]:
                slug_kume[uye["_slug"]] = f"{banka}#kume{sira:03d}"

    with open(KUME_HARITASI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump({"korpus_imzasi": imza,
                   "uretim": "gold_dataset/split_manifest_uret.py",
                   "harita": slug_kume}, f, ensure_ascii=False, indent=2)
    return _sakla(slug_kume, None)


def _url_kume_anahtarlari(urller: list[str]) -> tuple[dict[str, str], str | None]:
    """url -> kume anahtari. Kumelenemezse url'nin kendisi anahtardir.

    NEDEN URL YETMIYOR: olculdu - iki AYRI kampanya URL'si neredeyse ayni
    sablon metni tasiyabiliyor. "Akaryakit Harcamalariniza 300 TL
    ParafPara" (TEK-003, train) ile "Ucak Bileti Harcamalariniza 2.000 TL
    ParafPara" (TEK-006, test) ayni kalibin iki ornegi. URL bazli split
    bunlari farkli taraflara koyuyordu; motor kalibi train'de gorup
    test'te taniyacagi icin olcum siserdi.

    Ikinci deger: kumeleme yapilamadiysa SEBEBI. Sessiz kalinmaz -
    kumeleme calismadan uretilen split sizintisiz GORUNUR ama degildir.

    ONBELLEK: korpusu okumak 511 dosya, kumeleme banka icinde O(n^2).
    Testler split_uret'i defalarca cagirir; onbelleksiz test dosyasi tek
    basina 7 dakika suruyordu."""
    onbellek_anahtari = tuple(sorted(urller))
    if onbellek_anahtari in _KUME_ANAHTAR_ONBELLEK:
        return _KUME_ANAHTAR_ONBELLEK[onbellek_anahtari]

    slug_kume, sorun = _slug_kume_haritasi()
    if sorun:
        sonuc = ({u: u for u in urller}, sorun)
    else:
        from gold_dataset.sprint_is_listesi import _slug

        sonuc = ({u: slug_kume.get(_slug(u), u) for u in urller}, None)

    _KUME_ANAHTAR_ONBELLEK[onbellek_anahtari] = sonuc
    return sonuc


def _onceki_atamalar() -> dict[str, str]:
    """Daha once yazilmis manifest'ten url -> 'train'/'test' haritasi.

    Manifest kayit_id tutar, ama bolme birimi URL'dir; eslemeyi gold
    dosyasindan kurariz. Manifest yoksa (ilk uretim) bos doner."""
    if not CIKTI_DOSYASI.exists():
        return {}
    with open(CIKTI_DOSYASI, encoding="utf-8") as f:
        onceki = json.load(f)
    with open(GOLD_DOSYASI, encoding="utf-8") as f:
        kayit_url = {k["kayit_id"]: k["kaynak_url"] for k in json.load(f)}

    atamalar: dict[str, str] = {}
    for taraf in ("train", "test"):
        for kayit_id in onceki.get(taraf, []):
            url = kayit_url.get(kayit_id)
            if url:  # silinmis kayit varsa atlanir
                atamalar[url] = taraf
    return atamalar


def _sira_anahtari(url: str) -> str:
    """URL'nin kendi hash'i - atama sirasi listenin icerigine degil,
    URL'nin kendisine bagli olsun diye. Ayni URL her zaman ayni yerde."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def split_uret() -> dict:
    """Banka-katmanli, ATAMASI DONDURULMUS split.

    Daha once taraf almis her URL tarafinda kalir; yalnizca yeni URL'ler
    atanir. Yeni URL'ler banka bazinda, o bankanin test orani hedefin
    altinda kaldigi surece test'e gider - boylece set buyudukce oran
    hedefe yaklasir ama eski atamalar hic bozulmaz."""
    kayitlar = _gercek_kayitlari_yukle()
    url_gruplari = _kaynak_url_gruplari(kayitlar)
    onceki = _onceki_atamalar()
    kume_anahtari, kumeleme_sorunu = _url_kume_anahtarlari(list(url_gruplari))

    # Bolme birimi KUME'dir; ayni sablonu tasiyan URL'ler tek grup sayilir.
    kume_urlleri: dict[str, list[str]] = defaultdict(list)
    for url in url_gruplari:
        kume_urlleri[kume_anahtari[url]].append(url)

    banka_bazinda_kumeler: dict[str, list[str]] = defaultdict(list)
    for kume, urller in kume_urlleri.items():
        banka = url_gruplari[urller[0]][0]["banka"]
        banka_bazinda_kumeler[banka].append(kume)

    # Bir kume icinde daha once train'e girmis tek bir URL bile varsa
    # KUMENIN TAMAMI train'dir: o sablon gelistirirken zaten gorulmustur,
    # kardesini test'te olcmek sisirilmis puan uretir. Ters yon (hepsini
    # test'e almak) daha risklidir - train'de gorulmus bir sablonu test'e
    # tasimak olur.
    kume_onceki: dict[str, str] = {}
    for kume, urller in kume_urlleri.items():
        taraflar = {onceki[u] for u in urller if u in onceki}
        if not taraflar:
            continue
        kume_onceki[kume] = "train" if "train" in taraflar else "test"

    train_kumeler: list[str] = []
    test_kumeler: list[str] = []
    korunan = 0

    for _banka, kumeler in sorted(banka_bazinda_kumeler.items()):
        eski_test = [k for k in kumeler if kume_onceki.get(k) == "test"]
        eski_train = [k for k in kumeler if kume_onceki.get(k) == "train"]
        yeni = sorted((k for k in kumeler if k not in kume_onceki), key=_sira_anahtari)
        korunan += len(eski_test) + len(eski_train)

        test_kumeler.extend(eski_test)
        train_kumeler.extend(eski_train)

        hedef_test = max(1, round(len(kumeler) * TEST_ORANI)) if len(kumeler) >= 3 else 0
        acik = max(0, hedef_test - len(eski_test))

        test_kumeler.extend(yeni[:acik])
        train_kumeler.extend(yeni[acik:])

    train_urller = [u for k in train_kumeler for u in kume_urlleri[k]]
    test_urller = [u for k in test_kumeler for u in kume_urlleri[k]]

    def _kayit_idler(urller: list[str]) -> list[str]:
        idler = []
        for url in urller:
            idler.extend(k["kayit_id"] for k in url_gruplari[url])
        return sorted(idler)

    test_kumesi = set(test_urller)
    test_kume_kumesi = set(test_kumeler)
    manifest = {
        "surum": "v1",
        "olusturulma_yontemi": (
            "banka-katmanli, benzerlik-kumesi gruplu, atamasi dondurulmus split "
            "(gold_dataset/split_manifest_uret.py)"
        ),
        "test_orani_hedef": TEST_ORANI,
        "kumeleme": ("uygulandi" if not kumeleme_sorunu
                     else f"UYGULANAMADI - {kumeleme_sorunu}"),
        "toplam_kume": len(kume_urlleri),
        "onceki_surumden_korunan_kume": korunan,
        "yeni_atanan_kume": len(kume_urlleri) - korunan,
        "toplam_kayit": len(kayitlar),
        "toplam_kampanya_url": len(url_gruplari),
        "train": _kayit_idler(train_urller),
        "test": _kayit_idler(test_urller),
        "banka_bazinda_ozet": {
            banka: {
                "toplam_kume": len(kumeler),
                "test_kume": sum(1 for k in kumeler if k in test_kume_kumesi),
                "toplam_url": sum(len(kume_urlleri[k]) for k in kumeler),
                "test_url": sum(1 for k in kumeler for u in kume_urlleri[k]
                                if u in test_kumesi),
            }
            for banka, kumeler in sorted(banka_bazinda_kumeler.items())
        },
    }
    return manifest


def kaydet() -> Path:
    manifest = split_uret()
    with open(CIKTI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return CIKTI_DOSYASI


if __name__ == "__main__":
    yol = kaydet()
    manifest = split_uret()
    print(f"Manifest yazildi: {yol}")
    print(f"Train: {len(manifest['train'])} kayit, Test: {len(manifest['test'])} kayit")

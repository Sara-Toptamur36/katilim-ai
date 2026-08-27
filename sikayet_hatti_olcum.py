# -*- coding: utf-8 -*-
"""Sikayet boru hattinin sentetik veri seti uzerindeki olcum raporunu uretir.

CALISTIRMA:
    python sikayet_hatti_olcum.py

CIKTI:
    sikayet_hatti_olcum_raporu.json

NE OLCER: complaint/toplama.py::hazirla hattinin adimlarini
tests/veri/kapsam_disi/sentetik_musteri_sesi.json (v1.1) uzerinde.
Her olcum IKI YONLUDUR (hassasiyet + ozgulluk) - tek yon olcmek
yaniltici olurdu (bkz. docs/kapsam_ve_veri_ayrimi.md).

NE YAPMAZ:
  - Gercek veri TOPLAMAZ. Ag baglantisi kurmaz, hicbir siteye istek atmaz.
  - VERITABANINA YAZMAZ. complaint/toplama.py::kaydet HIC cagrilmaz;
    `sikayetler` tablosuna tek satir bile eklenmez. Veri setinin kendi
    sozlesmesi bunu sart kosuyor: "icerigi veritabanina, altin veri
    setine ve RAG indeksine ASLA girmez".
  - IZIN KAPISINI ACMAZ. logs/sikayet_izin_durumu.json olusturulmaz;
    hat `izin_zorunlu=False` ile kosar - bu bayrak complaint/toplama.py
    docstring'inde sentetik olcum icin tanimlidir.

Testle iliskisi: tests/test_sikayet_hatti_sentetik.py ayni olcumleri
CI'da kilitler; bu betik ayni sayilari juri/mentor icin raporlanabilir
bir artefakta cevirir.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from complaint.pii_temizleme import temizle
from complaint.tema_siniflandirici import TEMA_SURUMU
from complaint.toplama import hazirla, yogunluk_ozeti

KOK = Path(__file__).resolve().parent
VERI_YOLU = KOK / "tests" / "veri" / "kapsam_disi" / "sentetik_musteri_sesi.json"
RAPOR_YOLU = KOK / "sikayet_hatti_olcum_raporu.json"

KAYNAK = "sentetik_musteri_sesi"


def _hazirla(metin: str, **kw):
    return hazirla(metin, kaynak=KAYNAK, izin_zorunlu=False, **kw)


def _pii_olcumu(veri: dict) -> dict:
    hassasiyet, ozgulluk = [], []

    for k in veri["pii_ornekleri"]:
        sonuc = temizle(k["metin"])
        hassasiyet.append({
            "id": k["id"],
            "aciklama": k["aciklama"],
            "beklenen": k["beklenen_maskeler"],
            "bulunan": sonuc.bulunanlar,
            "gecti": sonuc.bulunanlar == k["beklenen_maskeler"],
            "temiz_metin": sonuc.metin,
        })

    for k in veri["pii_karsi_ornekleri"]:
        sonuc = temizle(k["metin"])
        ozgulluk.append({
            "id": k["id"],
            "aciklama": k["aciklama"],
            "bulunan": sonuc.bulunanlar,
            "metin_degismedi": sonuc.metin == k["metin"],
            "gecti": sonuc.bulunanlar == {} and sonuc.metin == k["metin"],
        })

    return {
        "_ne_olcer": (
            "Hassasiyet: maskelenmesi gerekeni maskeledi mi. Ozgulluk: musteri "
            "numarasi, referans no, tutar ve tarih gibi KISISEL OLMAYAN degerleri "
            "rahat birakti mi. Ozgulluk olculmeseydi 'her rakam dizisini sil' diyen "
            "bir kontrol tam puan alir, sikayetin finansal icerigi yok olurdu."
        ),
        "hassasiyet": {
            "gecen": sum(1 for h in hassasiyet if h["gecti"]),
            "toplam": len(hassasiyet),
            "kayitlar": hassasiyet,
        },
        "ozgulluk": {
            "gecen": sum(1 for o in ozgulluk if o["gecti"]),
            "toplam": len(ozgulluk),
            "kayitlar": ozgulluk,
        },
    }


def _yineleme_olcumu(veri: dict) -> dict:
    ciftler, karsi = [], []

    for c in veri["yineleme_ciftleri"]:
        ilk = _hazirla(c["metin_a"])
        ikinci = _hazirla(c["metin_b"], bilinen_icerik_hashleri=[ilk.icerik_hash])
        ciftler.append({
            "id": c["id"],
            "aciklama": c["aciklama"],
            "ayni_hash": ilk.icerik_hash == ikinci.icerik_hash,
            "yineleme_supheli_isaretlendi": ikinci.yineleme_supheli,
            "kayit_durdu": bool(ikinci.temiz_metin),
            "gecti": (
                ilk.icerik_hash == ikinci.icerik_hash
                and ikinci.yineleme_supheli
                and bool(ikinci.temiz_metin)
            ),
        })

    for c in veri["yineleme_karsi_ciftleri"]:
        a = _hazirla(c["metin_a"]).icerik_hash
        b = _hazirla(c["metin_b"]).icerik_hash
        karsi.append({
            "id": c["id"],
            "aciklama": c["aciklama"],
            "farkli_hash": a != b,
            "gecti": a != b,
        })

    return {
        "_ne_olcer": (
            "Yakalama: noktalama/harf/bosluk farkiyla yazilmis AYNI sikayet ayni "
            "anahtara dusuyor mu. Ozgulluk: FARKLI sikayetler cakismiyor mu. "
            "KIRMIZI CIZGI: sonuc her iki durumda da ENGELLEME degil ISARETLEMEDIR - "
            "yineleme supheli kayit silinmez, insan incelemesine bayraklanir "
            "(kayit_durdu alani bunu dogrular)."
        ),
        "yakalama": {
            "gecen": sum(1 for c in ciftler if c["gecti"]),
            "toplam": len(ciftler),
            "kayitlar": ciftler,
        },
        "ozgulluk": {
            "gecen": sum(1 for c in karsi if c["gecti"]),
            "toplam": len(karsi),
            "kayitlar": karsi,
        },
    }


def _tema_olcumu(veri: dict) -> dict:
    from complaint.tema_siniflandirici import tema_siniflandir

    temel = [
        {"id": o["id"], "beklenen": o["tema"],
         "bulunan": tema_siniflandir(o["metin"])["tema"]}
        for o in veri["ornekler"]
    ]
    alan_disi = [
        {"id": o["id"], "bulunan": tema_siniflandir(o["metin"])["tema"]}
        for o in veri["alan_disi_ornekler"]
    ]
    # PII maskelemesinden SONRA tema hala dogru mu?
    maskeli = [
        {"id": k["id"], "beklenen": k["beklenen_tema"],
         "bulunan": _hazirla(k["metin"]).tema}
        for k in veri["pii_ornekleri"] + veri["pii_karsi_ornekleri"]
    ]

    return {
        "_ne_olcer": (
            "Temel siniflandirma dogrulugu, alan disi metinlerde UYDURMA TEMA "
            "uretilmemesi ve PII maskelemesinden SONRA temanin korunmasi. "
            "Sonuncusu, maske etiketlerinin turu koruma tasarimini dogrular "
            "(complaint/pii_temizleme.py::ETIKET)."
        ),
        "tema_surumu": TEMA_SURUMU,
        "temel_dogruluk": {
            "gecen": sum(1 for t in temel if t["beklenen"] == t["bulunan"]),
            "toplam": len(temel),
        },
        "alan_disi_ozgulluk": {
            "gecen": sum(1 for a in alan_disi if a["bulunan"] is None),
            "toplam": len(alan_disi),
        },
        "maskeleme_sonrasi": {
            "gecen": sum(1 for m in maskeli if m["beklenen"] == m["bulunan"]),
            "toplam": len(maskeli),
            "kayitlar": maskeli,
        },
    }


def _onem_olcumu(veri: dict) -> dict:
    kayitlar = [
        {"id": k["id"], "beklenen": k["beklenen_onem_derecesi"],
         "bulunan": (r := _hazirla(k["metin"])).onem_derecesi,
         "gerekce": r.onem_gerekce}
        for k in veri["onem_ornekleri"]
    ]
    return {
        "_ne_olcer": (
            "complaint/onem_derecesi.py - YUKSEK (parasal kayip temasi VEYA "
            "tekrarlanan magduriyet ifadesi) / ORTA (varsayilan) / DUSUK "
            "(yalnizca bilgi belirsizligi). Kanit yoksa en olumsuz/en yuksek "
            "iddia UYDURULMAZ, ORTA varsayilandir."
        ),
        "gecen": sum(1 for k in kayitlar if k["beklenen"] == k["bulunan"]),
        "toplam": len(kayitlar),
        "kayitlar": kayitlar,
    }


def _cozum_olcumu(veri: dict) -> dict:
    kayitlar = [
        {"id": k["id"], "beklenen": k["beklenen_cozum_durumu"],
         "bulunan": (r := _hazirla(k["metin"])).cozum_durumu,
         "gerekce": r.cozum_gerekce}
        for k in veri["cozum_ornekleri"]
    ]
    return {
        "_ne_olcer": (
            "complaint/cozum_tespiti.py - musterinin KENDI ifadesinden "
            "cozuldu/kismen/cozulmedi/bilinmiyor tespiti. CRM/destek bileti "
            "entegrasyonu DEGILDIR (Faz 2). Sinyal yoksa 'bilinmiyor' - "
            "'cozulmedi' gibi bir iddia UYDURULMAZ."
        ),
        "gecen": sum(1 for k in kayitlar if k["beklenen"] == k["bulunan"]),
        "toplam": len(kayitlar),
        "kayitlar": kayitlar,
    }


def _dusuk_bilgi_olcumu(veri: dict) -> dict:
    yakalama = [
        {"id": k["id"], "dusuk_bilgi_supheli": _hazirla(k["metin"]).dusuk_bilgi_supheli}
        for k in veri["dusuk_bilgi_ornekleri"]
    ]
    ozgulluk = [
        {"id": k["id"], "dusuk_bilgi_supheli": _hazirla(k["metin"]).dusuk_bilgi_supheli}
        for k in veri["dusuk_bilgi_karsi_ornekleri"]
    ]
    return {
        "_ne_olcer": (
            "complaint/toplama.py::_dusuk_bilgi_supheli_mi - 4 kelimenin "
            "ALTINDAKI metinler ISARETLENIR (SILINMEZ). Yakalama: cok kisa "
            "metinler isaretlendi mi. Ozgulluk: esikte/uzerinde gercek "
            "icerikli kisa sikayetler YANLIS ALARM almadi mi."
        ),
        "yakalama": {
            "gecen": sum(1 for k in yakalama if k["dusuk_bilgi_supheli"]),
            "toplam": len(yakalama),
        },
        "ozgulluk": {
            "gecen": sum(1 for k in ozgulluk if not k["dusuk_bilgi_supheli"]),
            "toplam": len(ozgulluk),
        },
    }


class _SentetikKampanya:
    """Gercek api/models.py::Kampanya yerine minimal nesne - kampanya_esle
    yalnizca getattr ile alan okur (bkz. tests/test_sikayet_hatti_sentetik.py
    ile AYNI yardimci sinif - iki dosya arasinda TEK FARKLILIK budur, veri
    kaynagi ARTIK ikisinde de veri_seti['entity_resolution_ornekleri'])."""

    def __init__(self, id, banka, kampanya_adi, kampanya_turu, odul_birimi=None):
        self.id = id
        self.banka = banka
        self.kampanya_adi = kampanya_adi
        self.kampanya_turu = kampanya_turu
        self.odul_birimi = odul_birimi
        self.kampanya_baslangic = None
        self.kampanya_bitis = None


def _entity_resolution_olcumu(veri: dict) -> dict:
    """Uc seviyeli entity resolution - mentor geri bildirimindeki 'kampanya
    eslestirmeyi zorunlu degil opsiyonel yapin' onerisinin sonucu.

    27 Agustos 2026: artik veri_seti['entity_resolution_ornekleri']'nden
    okunur - onceki surumde bu sozluk KOD ICINE GOMULUYDU (dashboard'daki
    statik kartla ve rapordaki sayilarla senkron kalmasi elle takip
    gerektiriyordu). Tek kaynak, iki tuketici (bu betik + testler)."""
    from complaint.kampanya_eslestirme import kampanya_esle

    senaryolar = []
    for k in veri["entity_resolution_ornekleri"]:
        sonuc = kampanya_esle(k["metin"], [_SentetikKampanya(**k["kampanya"])])
        senaryolar.append({
            "id": k["id"],
            "aciklama": k["aciklama"],
            "metin": k["metin"],
            "seviye_1_banka_eslesti": sonuc.banka_eslesti,
            "seviye_2_urun_turu_guven": sonuc.urun_turu_guven,
            "seviye_3_kampanya_id": sonuc.kampanya_id,
            "seviye_3_guven": sonuc.guven,
            "beklenenle_uyumlu": (
                sonuc.banka_eslesti == k["beklenen"]["banka_eslesti"]
                and (sonuc.urun_turu_guven > 0.0) == k["beklenen"]["urun_turu_guven_pozitif"]
                and (sonuc.kampanya_id is not None) == k["beklenen"]["kampanya_esti"]
            ),
        })

    return {
        "_ne_olcer": (
            "Seviye 1 (banka) ve Seviye 2 (urun turu) sinyalleri, Seviye 3'ten "
            "(kampanya) BAGIMSIZ hesaplanir - kampanya esik altinda kalsa bile "
            "kaybolmazlar. SM-ER1 tipik durumu (kampanya adi gecmiyor), SM-ER2 "
            "kontrol grubunu (adi da gecince Seviye 3 de esigi asiyor) gosterir."
        ),
        "gecen": sum(1 for s in senaryolar if s["beklenenle_uyumlu"]),
        "toplam": len(senaryolar),
        "senaryolar": senaryolar,
    }


def _yogunluk_gosterimi(veri: dict) -> dict:
    """Tema bazli GOZLENEN YOGUNLUK - oran DEGIL, adet."""
    hazirlar = [_hazirla(o["metin"]) for o in veri["ornekler"]]
    ozet = yogunluk_ozeti(hazirlar, izin_var=False)
    ozet["_not"] = (
        "Bu ozet SENTETIK ornekler uzerinde hesaplanmistir ve gercek musteri "
        "yogunlugunu TEMSIL ETMEZ. Uretimdeki GET /musteri-sesi/yogunluk-ozeti "
        "ucnoktasi gercek `sikayetler` tablosunu okur; o tablo bostur ve "
        "kapsam_durumu 'izin_yok' doner. Bu betik o tabloya YAZMAZ."
    )
    return ozet


def olcum_yap() -> dict:
    veri = json.loads(VERI_YOLU.read_text(encoding="utf-8"))

    rapor = {
        "_baslik": "Sikayet boru hatti - sentetik veri olcumu",
        "_uretim_tarihi": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "_veri_seti": {
            "yol": str(VERI_YOLU.relative_to(KOK)).replace("\\", "/"),
            "surum": veri["_surum"],
            "uretim_yontemi": veri["_uretim_yontemi"],
            "pii_uretim_yontemi": veri["_uretim_yontemi_pii"],
        },
        "_kapsam_beyani": {
            "gercek_veri_toplandi_mi": False,
            "veritabanina_yazildi_mi": False,
            "izin_kaydi_olusturuldu_mu": False,
            "aciklama": (
                "Bu olcum yalnizca elle yazilmis sentetik metinler uzerinde "
                "yapilmistir. Hicbir siteye istek atilmamis, complaint/toplama.py"
                "::kaydet cagrilmamis ve logs/sikayet_izin_durumu.json "
                "olusturulmamistir. Izin kapisi (complaint/izin_kapisi.py) "
                "degistirilmemistir."
            ),
        },
        "pii_temizleme": _pii_olcumu(veri),
        "yineleme": _yineleme_olcumu(veri),
        "tema_siniflandirma": _tema_olcumu(veri),
        "onem_derecesi": _onem_olcumu(veri),
        "cozum_durumu": _cozum_olcumu(veri),
        "dusuk_bilgi_spam": _dusuk_bilgi_olcumu(veri),
        "entity_resolution_3_seviye": _entity_resolution_olcumu(veri),
        "gozlenen_yogunluk": _yogunluk_gosterimi(veri),
        "bilinen_sinirlamalar": [
            {
                "id": s["id"],
                "baslik": s["baslik"],
                "neden_duzeltilmedi": s["neden_duzeltilmedi"],
                "etki_alani": s["etki_alani"],
            }
            for s in veri["bilinen_sinirlamalar"]
        ],
    }
    return rapor


def _ozet_yazdir(rapor: dict) -> None:
    def _satir(ad, blok):
        print(f"  {ad:<26} {blok['gecen']}/{blok['toplam']}")

    print("\nSIKAYET HATTI - SENTETIK OLCUM")
    print(f"  Veri seti surumu           {rapor['_veri_seti']['surum']}")
    _satir("PII hassasiyet", rapor["pii_temizleme"]["hassasiyet"])
    _satir("PII ozgulluk", rapor["pii_temizleme"]["ozgulluk"])
    _satir("Yineleme yakalama", rapor["yineleme"]["yakalama"])
    _satir("Yineleme ozgulluk", rapor["yineleme"]["ozgulluk"])
    _satir("Tema temel dogruluk", rapor["tema_siniflandirma"]["temel_dogruluk"])
    _satir("Tema alan disi ozgulluk", rapor["tema_siniflandirma"]["alan_disi_ozgulluk"])
    _satir("Maskeleme sonrasi tema", rapor["tema_siniflandirma"]["maskeleme_sonrasi"])
    _satir("Onem derecesi (severity)", rapor["onem_derecesi"])
    _satir("Cozum durumu (resolution)", rapor["cozum_durumu"])
    _satir("Dusuk-bilgi yakalama", rapor["dusuk_bilgi_spam"]["yakalama"])
    _satir("Dusuk-bilgi ozgulluk", rapor["dusuk_bilgi_spam"]["ozgulluk"])
    _satir("Entity resolution (3 sv.)", rapor["entity_resolution_3_seviye"])
    print(f"  Bilinen sinirlama          {len(rapor['bilinen_sinirlamalar'])} (dondurulmus)")
    print("\n  Gercek veri toplandi mi?   HAYIR")
    print("  Veritabanina yazildi mi?   HAYIR")
    print("  Izin kaydi olusturuldu mu? HAYIR")


if __name__ == "__main__":
    rapor = olcum_yap()
    RAPOR_YOLU.write_text(
        json.dumps(rapor, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _ozet_yazdir(rapor)
    print(f"\nDetayli rapor: {RAPOR_YOLU.name}")

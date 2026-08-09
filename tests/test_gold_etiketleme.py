"""Altin Veri Seti etiketleme boru hattinin testleri.

KILITLENEN DAVRANIS: bos bir hucrenin anlamini SUTUN belirler.
Incelenmis bir sutunda bos = "kaynakta belirtilmemis" (yanlis pozitif
olculebilir); henuz incelenmemis bir sutunda bos = "kimse bakmadi"
(olcum disi). Karistirilirsa, hic etiketlenmemis bir sutun "hepsi bos,
demek ki motor hic uydurmuyor" diye bedava yuksek puan uretir.

Excel'in "1. Nasil Doldurulur" sayfasindaki kural ("'-', 'yok', '0'
YAZMA, BOS birak") KORUNUR - burada ona ek bir hucre isareti YOKTUR.
"""

import openpyxl
import pytest

from gold_dataset.excel_to_json import (
    INCELENMEMIS_ALANLAR,
    INCELENMIS_ALANLAR,
    donustur,
)

BASLIKLAR = [
    "kayit_id", "banka", "kampanya_adi", "kaynak_url", "kar_payi_orani",
    "oran_periyodu", "vade_ay", "finansman_tutari", "odul_miktari",
    "odul_birimi", "masraf_durumu", "kampanya_bitis", "hedef_kitle",
    "taksit_sayisi", "erteleme_suresi_ay", "giren_kisi",
]


def _excel_yaz(tmp_path, satirlar: list[dict]):
    """Test icin gecici bir Altin Veri Seti Excel'i uretir."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "2. Altin Veri Seti"
    ws.append(BASLIKLAR)
    ws.append(["aciklama"] * len(BASLIKLAR))  # 2. satir: aciklama
    for satir in satirlar:
        ws.append([satir.get(b) for b in BASLIKLAR])
    yol = tmp_path / "altin.xlsx"
    wb.save(yol)
    return yol


def _temel_kayit(**ekstra) -> dict:
    return {
        "kayit_id": "KT-001",
        "banka": "Kuveyt Türk",
        "kampanya_adi": "Test",
        "kaynak_url": "https://ornek.com/k",
        "giren_kisi": "Test",
        **ekstra,
    }


# ---------------------------------------------------------------------------
# Bos hucrenin anlami sutuna gore degisir
# ---------------------------------------------------------------------------


def test_incelenmemis_sutunda_bos_hucre_BAYRAKLANMAZ(tmp_path):
    """EN KRITIK TEST: sutun 9 Agustos'ta eklendi, hicbir kayit icin
    incelenmedi. Bayraklansaydi 58 kaydin tamami yanlis pozitif olcumune
    girer ve motor, hicbir sey kanitlamadan %100 alirdi."""
    yol = _excel_yaz(tmp_path, [_temel_kayit(taksit_sayisi=None)])
    kayit = donustur(yol)[0][0]
    assert kayit["taksit_sayisi"] is None
    assert "taksit_sayisi" not in kayit["alan_belirtilmemis"]


def test_incelenmis_sutunda_bos_hucre_bayraklanir(tmp_path):
    """Mevcut davranis KORUNMALI: bu alanlar 28 Temmuz oturumunda tek tek
    incelendi, bos olmalari bilincli bir karardir."""
    yol = _excel_yaz(tmp_path, [_temel_kayit(vade_ay=None, hedef_kitle=None)])
    kayit = donustur(yol)[0][0]
    assert kayit["alan_belirtilmemis"]["vade_ay"] is True
    assert kayit["alan_belirtilmemis"]["hedef_kitle"] is True


def test_iki_liste_kesismez():
    """Bir sutun hem incelenmis hem incelenmemis olamaz."""
    assert not set(INCELENMIS_ALANLAR) & set(INCELENMEMIS_ALANLAR)


def test_yok_yazmak_sayisal_alanda_hata_verir(tmp_path):
    """Excel rehberi (1. Nasil Doldurulur, satir 34) '-', 'yok', '0'
    yazmayi ACIKCA yasaklar. Yazilirsa sessizce yutulmamali, etiketleyici
    uyarilmali."""
    from gold_dataset.excel_to_json import DogrulamaHatasi

    yol = _excel_yaz(tmp_path, [_temel_kayit(taksit_sayisi="yok")])
    with pytest.raises(DogrulamaHatasi, match="taksit_sayisi"):
        donustur(yol)


# ---------------------------------------------------------------------------
# Yeni sayisal alanlar
# ---------------------------------------------------------------------------


def test_taksit_ve_erteleme_sayiya_cevrilir(tmp_path):
    yol = _excel_yaz(tmp_path, [_temel_kayit(taksit_sayisi=12, erteleme_suresi_ay=3)])
    kayit = donustur(yol)[0][0]
    assert kayit["taksit_sayisi"] == 12
    assert kayit["erteleme_suresi_ay"] == 3


def test_taksit_sayisina_birim_yazilirsa_acik_hata_verir(tmp_path):
    """Sessizce duzeltmek yerine etiketleyiciye hatayi soyle."""
    from gold_dataset.excel_to_json import DogrulamaHatasi

    yol = _excel_yaz(tmp_path, [_temel_kayit(taksit_sayisi="12 taksit")])
    with pytest.raises(DogrulamaHatasi, match="taksit_sayisi"):
        donustur(yol)


def test_dolu_deger_bayraklanmaz(tmp_path):
    yol = _excel_yaz(tmp_path, [_temel_kayit(taksit_sayisi=6)])
    kayit = donustur(yol)[0][0]
    assert "taksit_sayisi" not in kayit["alan_belirtilmemis"]


# ---------------------------------------------------------------------------
# Etiketleme yardimcisi
# ---------------------------------------------------------------------------


def test_yardimci_kanit_cumlesini_bulur():
    from gold_dataset.etiketleme_yardimcisi import ALANLAR, _kanit_cumleleri

    desen = ALANLAR["erteleme_suresi_ay"][0]
    metin = "Kampanya sartlari asagidadir. 3 ay ertelemeli odeme imkani. Basvurun."
    kanitlar = _kanit_cumleleri(metin, desen)
    assert len(kanitlar) == 1
    assert "3 ay ertelemeli" in kanitlar[0]


def test_yardimci_kavram_gecmiyorsa_bos_doner():
    from gold_dataset.etiketleme_yardimcisi import ALANLAR, _kanit_cumleleri

    desen = ALANLAR["taksit_sayisi"][0]
    assert _kanit_cumleleri("Konut finansmaninda 120 ay vade firsati.", desen) == []


def test_yardimci_yasakli_yok_yazimini_ONERMEZ(capsys):
    """REGRESYON: yardimci bir ara surumde '[1] ... Excel'de `yok` yaz'
    diyordu. Excel rehberi bunu yasakliyor ve excel_to_json.py sayisal
    alanda 'yok' gorunce DogrulamaHatasi firlatiyor - yani talimati
    uygulayan etiketleyicinin isi patlardi."""
    from gold_dataset.etiketleme_yardimcisi import rapor_yazdir

    rapor_yazdir(
        {
            "alan": "taksit_sayisi",
            "hatirlatma": "test",
            "yok": ["KT-001"],
            "karar_gerek": [],
            "kaynaksiz": [],
        }
    )
    cikti = capsys.readouterr().out
    assert "BOS BIRAK" in cikti
    assert "`yok` yaz" not in cikti


def test_yardimci_cikarim_motorunu_CAGIRMAZ():
    """DAIRESELLIK KORUMASI: Altin Veri Seti, motorun olculdugu
    referanstir. Yardimci motorun ciktisini onerirse olcum kendi kendini
    dogrular ve dogruluk tanim geregi %100 cikar.

    Kontrol AST uzerinden yapilir - duz metin aramasi, dosyanin kendi
    aciklamasindaki 'regex_extractor.py'yi CAGIRMAZ' cumlesine takilirdi."""
    import ast
    from pathlib import Path

    agac = ast.parse(
        (Path(__file__).parent.parent / "gold_dataset" / "etiketleme_yardimcisi.py")
        .read_text(encoding="utf-8")
    )

    ithal_edilenler: set[str] = set()
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.Import):
            ithal_edilenler.update(a.name for a in dugum.names)
        elif isinstance(dugum, ast.ImportFrom) and dugum.module:
            ithal_edilenler.add(dugum.module)

    yasakli = {"extraction", "extraction.regex_extractor", "extraction.hybrid_pipeline"}
    ihlal = {m for m in ithal_edilenler if m in yasakli or m.startswith("extraction.")}
    assert not ihlal, f"Etiketleme yardimcisi cikarim motorunu ithal ediyor: {ihlal}"

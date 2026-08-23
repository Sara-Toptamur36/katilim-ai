"""Taslak kayitlar icin insan dogrulama sayfasi uretir.

--------------------------------------------------------------------------
NEDEN
--------------------------------------------------------------------------
Altin sette bir kayit, `giren_kisi` alani doldurulana kadar TASLAKTIR.
O alana isim yazmak "ben baktim ve dogru" demektir - olcum bu imzaya
guvenir.

Bu betik imzayi KOLAYLASTIRIR, gereksiz kilmaz: makinenin kontrol
edebilecegi ne varsa onceden kontrol eder ve geriye yalnizca GOZLE
yargi gerektiren kismi birakir. Her kayit icin ekran goruntusunu,
girilmis degerleri ve kanit cumlelerini yan yana koyar.

--------------------------------------------------------------------------
OTOMATIK KONTROLLER
--------------------------------------------------------------------------
  * kanit spani kaynak metinde birebir geciyor mu
  * sayisal degerler kaynak metinde gorunuyor mu
  * odul_miktari / odul_birimi birlikte mi
  * baslangic <= bitis mi
  * ekran goruntusu var mi

Bunlarin hicbiri "deger DOGRU" demez - yalnizca "kendi icinde tutarli"
der. Degerin dogrulugu sayfaya bakmakla anlasilir; sayfa da yaninda.

Kullanim:
    python gold_dataset/dogrulama_sayfasi.py
    # -> gold_dataset/dogrulama.html  (tarayicida ac)
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

GOLD = KOK / "gold_dataset" / "altin_veri_seti.json"
CIKTI = KOK / "gold_dataset" / "dogrulama.html"

GOSTERILEN = ("banka", "kampanya_turu", "kar_payi_orani", "oran_periyodu",
              "vade_ay", "taksit_sayisi", "erteleme_suresi_ay",
              "finansman_tutari", "odul_miktari", "odul_birimi",
              "masraf_durumu", "kampanya_baslangic", "kampanya_bitis",
              "hedef_kitle", "kampanya_avantaji")
SAYISAL = ("kar_payi_orani", "vade_ay", "taksit_sayisi", "erteleme_suresi_ay",
           "finansman_tutari", "odul_miktari")


def _sayi_bicimleri(deger) -> list[str]:
    if isinstance(deger, float) and deger.is_integer():
        deger = int(deger)
    b = {str(deger)}
    if isinstance(deger, int):
        b.add(f"{deger:,}".replace(",", "."))
        if deger >= 1000 and deger % 1000 == 0:
            b.add(f"{deger // 1000} bin")
    if isinstance(deger, float):
        b.add(str(deger).replace(".", ","))
    return sorted(b)


def kontroller(kayit: dict, metin: str | None) -> list[dict]:
    from gold_dataset.excel_to_json import span_metinde_var

    sonuc: list[dict] = []

    def ekle(durum, mesaj):
        sonuc.append({"durum": durum, "mesaj": mesaj})

    # ekran goruntusu
    ss = KOK / "gold_dataset" / "ekran_goruntuleri" / f"{kayit['kayit_id']}.png"
    ekle("iyi" if ss.exists() else "kotu",
         "ekran görüntüsü var" if ss.exists() else "EKRAN GÖRÜNTÜSÜ YOK")

    # kanit spanlari
    # KANITLANACAK DEGER YOKSA "kanit yok" UYARISI YANLIS ALARMDIR.
    # Olculdu: HF-007, VK-009 ve VK-010'da sayfa hicbir sayisal deger
    # vermiyor ve tum olculen alanlar BILEREK bos; kanit spani yalnizca
    # DOLU alanlara verilir. Bunlari uyari saymak, gercek uyarilari
    # gurultuye bogar.
    from gold_dataset.excel_to_json import SPAN_VERILEBILIR_ALANLAR

    spanlar = kayit.get("kanit_spanlari") or {}
    kanitlanabilir = [a for a in SPAN_VERILEBILIR_ALANLAR
                      if kayit.get(a) not in (None, "", [])]
    if not kanitlanabilir:
        ekle("iyi", "kanıtlanacak dolu alan yok — tüm ölçülen alanlar bilerek boş")
    elif not spanlar:
        ekle("uyari", f"kanıt cümlesi girilmemiş ({len(kanitlanabilir)} dolu alan var)")
    elif metin is None:
        ekle("uyari", f"{len(spanlar)} kanıt cümlesi var, kaynak sayfa yok — doğrulanamadı")
    else:
        kirik = [a for a, c in spanlar.items() if c and not span_metinde_var(c, metin)]
        ekle("kotu" if kirik else "iyi",
             f"kanıt cümleleri kaynakta bulunamadı: {', '.join(kirik)}" if kirik
             else f"{len(spanlar)} kanıt cümlesi kaynakta birebir geçiyor")

    # sayisal degerler metinde goruluyor mu
    if metin:
        gorunmeyen = []
        for alan in SAYISAL:
            d = kayit.get(alan)
            if d in (None, "", []):
                continue
            if not any(b in metin for b in _sayi_bicimleri(d)):
                gorunmeyen.append(f"{alan}={d}")
        ekle("uyari" if gorunmeyen else "iyi",
             f"değer metinde birebir görünmüyor (türetilmiş olabilir): {', '.join(gorunmeyen)}"
             if gorunmeyen else "sayısal değerlerin hepsi metinde görünüyor")
    else:
        ekle("uyari", "kaynak sayfa ham veride yok — yalnızca görüntüden bakılabilir")

    # odul ikilisi
    om, ob = kayit.get("odul_miktari"), kayit.get("odul_birimi")
    if (om is None) != (ob in (None, "")):
        ekle("kotu", "ödül miktarı ve birimi uyumsuz")

    # tarih mantigi
    b, s = kayit.get("kampanya_baslangic"), kayit.get("kampanya_bitis")
    if b and s and b > s:
        ekle("kotu", "başlangıç bitişten sonra")

    return sonuc


def uret() -> str:
    from gold_dataset.sprint_is_listesi import _ham_kampanyalar, _slug

    ham = _ham_kampanyalar()
    with open(GOLD, encoding="utf-8") as f:
        kayitlar = json.load(f)
    taslak = [k for k in kayitlar
              if not k["kayit_id"].startswith(("A-", "B-", "C-", "D-"))
              and not k.get("giren_kisi")]

    kartlar = []
    for k in sorted(taslak, key=lambda x: (x["banka"], x["kayit_id"])):
        kaynak = ham.get(_slug(k.get("kaynak_url") or ""))
        metin = (kaynak or {}).get("normalize_metin")
        kont = kontroller(k, metin)

        alanlar = "".join(
            f'<tr><td class="a">{html.escape(a)}</td>'
            f'<td class="d">{html.escape(str(k.get(a)))}</td></tr>'
            for a in GOSTERILEN if k.get(a) not in (None, "", []))
        bos = [a for a in GOSTERILEN if k.get(a) in (None, "", [])]
        spanlar = "".join(
            f'<div class="sp"><span class="spa">{html.escape(a)}</span>'
            f'<span class="spc">{html.escape(c)}</span></div>'
            for a, c in (k.get("kanit_spanlari") or {}).items())
        kontrol_html = "".join(
            f'<li class="k-{c["durum"]}">{html.escape(c["mesaj"])}</li>' for c in kont)
        en_kotu = ("kotu" if any(c["durum"] == "kotu" for c in kont)
                   else "uyari" if any(c["durum"] == "uyari" for c in kont) else "iyi")

        kartlar.append(f'''
<article class="kart" id="{html.escape(k['kayit_id'])}" data-durum="{en_kotu}">
  <header class="kh">
    <span class="kid">{html.escape(k['kayit_id'])}</span>
    <h2>{html.escape(k.get('kampanya_adi') or '')}</h2>
    <a class="url" href="https://{html.escape((k.get('kaynak_url') or '').lstrip('/'))}"
       target="_blank" rel="noopener noreferrer">kaynağı aç ↗</a>
  </header>
  <div class="gövde">
    <div class="sol">
      <img loading="lazy" src="ekran_goruntuleri/{html.escape(k['kayit_id'])}.png"
           alt="{html.escape(k['kayit_id'])} ekran görüntüsü">
    </div>
    <div class="sag">
      <table class="alanlar">{alanlar}</table>
      <p class="bos"><strong>Boş bırakılan:</strong> {html.escape(', '.join(bos)) or '—'}</p>
      {'<div class="spanlar"><div class="baslik">Kanıt cümleleri</div>' + spanlar + '</div>' if spanlar else ''}
      <ul class="kontrol">{kontrol_html}</ul>
      <p class="not">{html.escape((k.get('notlar') or '')[:400])}</p>
    </div>
  </div>
</article>''')

    return SABLON.replace("__KARTLAR__", "\n".join(kartlar)) \
                 .replace("__SAYI__", str(len(taslak)))


SABLON = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Taslak Kayıt Doğrulama</title>
<style>
:root{--g:#f4f6f4;--s:#fff;--s2:#eaefec;--i:#111d1b;--i2:#44514e;--i3:#6c7a76;
 --l:#dbe2df;--a:#0f6b62;--iyi:#1d6b3a;--uyari:#8a5a0b;--kotu:#8a2e1f;
 --iyi-s:#dcecdf;--uyari-s:#f5e9d4;--kotu-s:#f7e3df}
@media(prefers-color-scheme:dark){:root{--g:#0c1312;--s:#131d1b;--s2:#1a2624;
 --i:#e7edea;--i2:#a9b8b4;--i3:#7d8d89;--l:#233230;--a:#54b8aa;
 --iyi:#77c78f;--uyari:#d3a259;--kotu:#e0806e;
 --iyi-s:#16301f;--uyari-s:#33260f;--kotu-s:#3a1e18}}
*{box-sizing:border-box}
body{margin:0;background:var(--g);color:var(--i);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
.üst{position:sticky;top:0;background:var(--g);border-bottom:1px solid var(--l);
 padding:14px 22px;z-index:9;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
h1{font-size:1.15rem;margin:0}
.sayac{color:var(--i3);font-size:.86rem}
.cip{font:inherit;font-size:.83rem;padding:5px 12px;border-radius:100px;cursor:pointer;
 border:1px solid var(--l);background:var(--s);color:var(--i2)}
.cip[aria-pressed=true]{background:var(--a);border-color:var(--a);color:var(--g)}
.sarma{max-width:1240px;margin:0 auto;padding:20px 22px 70px}
.uyarı{background:var(--uyari-s);border-left:3px solid var(--uyari);padding:13px 17px;
 border-radius:0 6px 6px 0;margin-bottom:22px;color:var(--i2);font-size:.9rem}
.uyarı b{color:var(--i)}
.kart{background:var(--s);border:1px solid var(--l);border-radius:8px;margin-bottom:22px;overflow:hidden}
.kh{display:flex;gap:12px;align-items:baseline;padding:13px 18px;background:var(--s2);
 border-bottom:1px solid var(--l);flex-wrap:wrap}
.kid{font-family:ui-monospace,monospace;font-weight:600;color:var(--a)}
.kh h2{font-size:1rem;margin:0;flex:1;font-weight:600}
.url{font-size:.8rem;color:var(--i3);text-decoration:none}
.url:hover{color:var(--a)}
.gövde{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:0}
.sol{border-right:1px solid var(--l);max-height:560px;overflow:auto;background:var(--s2)}
.sol img{width:100%;display:block}
.sag{padding:16px 18px;min-width:0}
table.alanlar{width:100%;border-collapse:collapse;font-size:.87rem;margin-bottom:10px}
.alanlar td{padding:4px 8px;border-bottom:1px solid var(--l);vertical-align:top}
.alanlar .a{color:var(--i3);white-space:nowrap;width:11rem;font-family:ui-monospace,monospace;font-size:.8rem}
.alanlar .d{font-weight:500}
.bos{font-size:.82rem;color:var(--i3);margin:8px 0}
.spanlar{background:var(--s2);border-radius:6px;padding:10px 12px;margin:10px 0}
.baslik{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--i3);margin-bottom:6px}
.sp{font-size:.82rem;margin-bottom:5px;display:flex;gap:8px}
.spa{font-family:ui-monospace,monospace;color:var(--a);white-space:nowrap}
.spc{color:var(--i2)}
ul.kontrol{list-style:none;padding:0;margin:10px 0;font-size:.82rem}
ul.kontrol li{padding:3px 9px;border-radius:4px;margin-bottom:3px}
.k-iyi{background:var(--iyi-s);color:var(--iyi)}
.k-uyari{background:var(--uyari-s);color:var(--uyari)}
.k-kotu{background:var(--kotu-s);color:var(--kotu)}
.not{font-size:.8rem;color:var(--i3);margin:8px 0 0}
@media(max-width:900px){.gövde{grid-template-columns:1fr}.sol{border-right:none;border-bottom:1px solid var(--l)}}
</style></head><body>
<div class="üst">
  <h1>Taslak Kayıt Doğrulama</h1>
  <span class="sayac" id="sayac"></span>
  <button class="cip" data-f="*" aria-pressed="true">Tümü</button>
  <button class="cip" data-f="uyari">Bakılacaklar</button>
  <button class="cip" data-f="kotu">Sorunlu</button>
</div>
<div class="sarma">
<p class="uyarı"><b>Bu sayfa imzayı kolaylaştırır, gereksiz kılmaz.</b>
Yeşil satırlar makinenin kontrol edebildikleri — kanıt cümlesi kaynakta geçiyor mu,
değerler kendi içinde tutarlı mı. Hiçbiri "değer doğru" demez. Değerin doğruluğu
soldaki ekran görüntüsüne bakmakla anlaşılır. Onayladığınız kayıtların
<code>giren_kisi</code> alanını Excel'de doldurun.</p>
__KARTLAR__
</div>
<script>
const kartlar=[...document.querySelectorAll('.kart')],sayac=document.getElementById('sayac');
function ciz(f){let n=0;kartlar.forEach(k=>{const g=f==='*'||k.dataset.durum===f;
 k.style.display=g?'':'none';if(g)n++});sayac.textContent=n+' / '+kartlar.length+' kayıt';}
document.querySelectorAll('.cip').forEach(b=>b.addEventListener('click',()=>{
 document.querySelectorAll('.cip').forEach(o=>o.setAttribute('aria-pressed',String(o===b)));
 ciz(b.dataset.f);}));
ciz('*');
</script></body></html>"""


if __name__ == "__main__":
    CIKTI.write_text(uret(), encoding="utf-8")
    print(f"  yazildi: {CIKTI.relative_to(KOK)}")
    print("  Tarayicida acin; onayladiginiz kayitlarin giren_kisi alanini Excel'de doldurun.")

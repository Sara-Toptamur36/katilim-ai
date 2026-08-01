"""Kampanya yaşam döngüsü (ACTIVE / EXPIRED / BILINMIYOR) hesaplama.

Zeynep Veri Toplama Rehberi, Sprint 2 Gün 4. Rapor Bölüm 15: kampanya
başlangıç/bitiş tarihleri, durum alanının hesaplanmasında kullanılır;
api/schemas.py'deki YasamDongusu enum'u ile birebir eşleşir.
"""

from __future__ import annotations

from datetime import date


def durum_hesapla(
    baslangic: date | None, bitis: date | None, bugun: date | None = None
) -> str:
    """Kampanyanın güncel olup olmadığını belirler.

    Tarih bilgisi YOKSA 'BILINMIYOR' döner - EXPIRED denmez. Bilgi
    eksikliğini "süresi dolmuş" saymak, şeffaflık ilkesine aykırıdır
    (rapor Bölüm 5.7/15) ve kampanyayı haksız yere gizler.

    `bugun` parametresi test edilebilirlik içindir; verilmezse
    `date.today()` kullanılır.
    """
    bugun = bugun if bugun is not None else date.today()

    if bitis and bitis < bugun:
        return "EXPIRED"
    if baslangic and baslangic > bugun:
        return "BILINMIYOR"  # henüz başlamamış
    if bitis and bitis >= bugun:
        return "ACTIVE"
    if baslangic and not bitis:
        return "ACTIVE"  # başlamış, bitiş belirtilmemiş
    return "BILINMIYOR"  # hiçbir tarih yok

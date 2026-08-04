"""Hibrit boru hattinin (regex + NER + LLM) Extraction Accuracy olcumu.

scraper/scripts/extraction_accuracy.py'deki genellenmis
extraction_accuracy_hesapla() fonksiyonunu extraction/hybrid_pipeline.py
kaydi_hibrit_cikar() ile calistirir - boylece NER/LLM katmanlarinin
eklenmesinin regex'in tek basina dogrulugu (mevcut olcum: %84.38) ile
kiyaslandiginda GERCEKTEN bir iyilesme saglayip saglamadigi olculur.

NER icin GLiNER modeli ilk cagrida yuklenir (agir), LLM icin regex+NER'in
bos biraktigi her alan grubu icin Ollama'ya gercek bir HTTP istegi atilir
- bu yuzden regex-only olcumden COK daha yavas calisir (gold_dataset
boyutuna gore birkaç dakika surebilir). Ollama servisi kapaliysa hatalar
FIRLATILMAZ (llm_ile_cikar zaten kademeli fallback ilkesiyle None doner),
ama olculen dogruluk yalnizca regex+NER'i yansitir - gercek sayi icin
`ollama serve` calisir durumda olmali.

Kullanim:
    python -m scraper.scripts.hibrit_extraction_accuracy
"""

from __future__ import annotations

from extraction.hybrid_pipeline import kaydi_hibrit_cikar
from scraper.scripts.extraction_accuracy import extraction_accuracy_hesapla

if __name__ == "__main__":
    sonuc = extraction_accuracy_hesapla(kaydi_hibrit_cikar)
    print(f"Hibrit Extraction Accuracy: %{sonuc['accuracy']} ({sonuc['dogru_alan']}/{sonuc['toplam_alan']} alan)")
    print(f"Olcume dahil edilen canli kayit sayisi: {sonuc['canli_kayit_sayisi']}")
    if sonuc["hatalar"]:
        print(f"\nHatalar ({len(sonuc['hatalar'])}):")
        for h in sonuc["hatalar"]:
            print(f"  [{h['kayit_id']}] {h['alan']}: beklenen={h['beklenen']!r} bulunan={h['bulunan']!r}")

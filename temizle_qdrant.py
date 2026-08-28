import os
import sys

# Qdrant local path must be set before chunking.qdrant_baglanti is imported
os.environ["QDRANT_YEREL_YOL"] = ".qdrant_yerel"

from qdrant_client import QdrantClient
from chunking.qdrant_baglanti import VARSAYILAN_KOLEKSIYON
from chunking.parcalayici import _gurultu_mu

def temizle():
    client = QdrantClient(path=".qdrant_yerel")
    
    offset = None
    points_to_delete = []
    
    print(f"Taraniyor: {VARSAYILAN_KOLEKSIYON}")
    while True:
        records, next_offset = client.scroll(
            collection_name=VARSAYILAN_KOLEKSIYON,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        
        for record in records:
            payload = record.payload or {}
            metin = payload.get("metin", "")
            # Parca baslik icerebilir, ornegin "Albaraka - dis ticaret"
            # Biz sadece "dis ticaret" falan varsa secmek istiyoruz
            satirlar = metin.split("\n")
            for satir in satirlar:
                sade = satir.split(" — ")[-1].strip() # Basligi ayir
                if _gurultu_mu(sade):
                    points_to_delete.append(record.id)
                    break
                
        offset = next_offset
        if offset is None:
            break
            
    print(f"Toplam silinecek gurultulu parca sayisi: {len(points_to_delete)}")
    
    if points_to_delete:
        client.delete(
            collection_name=VARSAYILAN_KOLEKSIYON,
            points_selector=points_to_delete
        )
        print("Silme islemi tamamlandi.")
    else:
        print("Gurultulu parca bulunamadi.")

if __name__ == "__main__":
    temizle()

import json
import random
from collections import defaultdict
import os

def main():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    RAG_SORU_SETI_PATH = os.path.join(BASE_DIR, "rag_soru_seti.json")
    VALIDATION_SETI_PATH = os.path.join(BASE_DIR, "validation_seti.json")
    
    if not os.path.exists(RAG_SORU_SETI_PATH):
        print(f"HATA: {RAG_SORU_SETI_PATH} bulunamadi.")
        return

    with open(RAG_SORU_SETI_PATH, "r", encoding="utf-8") as f:
        tum_sorular = json.load(f)
        
    # Kategorilere gore grupla
    kategori_gruplari = defaultdict(list)
    for soru in tum_sorular:
        kategori = soru.get("kategori", "diger")
        kategori_gruplari[kategori].append(soru)
        
    # Sabit seed ile tekrarlanabilirlik
    random.seed(42)
    
    validation_seti = []
    kalan_test_seti = []
    
    # Her kategoriden yaklasik %20 sec
    print("Stratified Sampling Raporu:")
    print("-" * 50)
    for kategori, sorular in kategori_gruplari.items():
        toplam = len(sorular)
        ayrilacak = max(1, round(toplam * 0.20)) # En az 1 tane alalim
        
        # Karistir ve bol
        random.shuffle(sorular)
        val_secilen = sorular[:ayrilacak]
        test_kalan = sorular[ayrilacak:]
        
        validation_seti.extend(val_secilen)
        kalan_test_seti.extend(test_kalan)
        
        print(f"Kategori: {kategori:25} | Toplam: {toplam:3} | Val: {ayrilacak:2} | Test: {len(test_kalan):3}")
        
    print("-" * 50)
    print(f"TOPLAM Validation: {len(validation_seti)}")
    print(f"TOPLAM Test (Kalan Altin Set): {len(kalan_test_seti)}")
    print("-" * 50)
    
    # Orijinal dosyayi yedekle (guvenlik amacli)
    RAG_YEDEK = RAG_SORU_SETI_PATH + ".bak"
    if not os.path.exists(RAG_YEDEK):
        import shutil
        shutil.copy2(RAG_SORU_SETI_PATH, RAG_YEDEK)
        print(f"Orijinal dosya yedeklendi: {RAG_YEDEK}")
        
    # Dosyalari yaz
    with open(VALIDATION_SETI_PATH, "w", encoding="utf-8") as f:
        json.dump(validation_seti, f, ensure_ascii=False, indent=2)
        
    with open(RAG_SORU_SETI_PATH, "w", encoding="utf-8") as f:
        json.dump(kalan_test_seti, f, ensure_ascii=False, indent=2)
        
    print("Dosyalar basariyla olusturuldu.")

if __name__ == "__main__":
    main()

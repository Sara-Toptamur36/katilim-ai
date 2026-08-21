# Sürüm yayınlama ve geri alma

Bu belge tek bir soruya cevap verir: **"Şu an ne çalışıyor ve bozulursa
nasıl geri dönerim?"**

---

## 1. Neden etiket değil, digest

Bir imaj etiketi (`v1.0.0`) **taşınabilir**: aynı etiket bugün bir imajı,
yarın başkasını gösterebilir. Geri almak için gereken şey değişmeyecek bir
adrestir — yani **digest**.

```
ghcr.io/sara-toptamur36/katilim-ai-api@sha256:abc123...   ← değişmez
ghcr.io/sara-toptamur36/katilim-ai-api:v1.0.0             ← taşınabilir
```

Bu yüzden sürüm künyesi digest'i kaydeder ve geri alma **her zaman**
digest ile yapılır.

---

## 2. Sürüm künyesi

Etiket atıldığında `.github/workflows/release.yml` bir künye üretir ve
artefakt olarak saklar (90 gün):

```json
{
  "surum": "v0.1.0",
  "git_sha": "...",
  "imaj_digest": "sha256:...",
  "alembic_surumu": "c9d2e4a17b30",
  "modeller": {
    "llm": "qwen2.5:7b-instruct-q4_K_M",
    "gomme": "intfloat/multilingual-e5-base",
    "ner": "urchade/gliner_multi-v2.1"
  }
}
```

**Neden hepsi tek dosyada:** bir sorun çıktığında "hangi kod, hangi şema,
hangi model" sorularının cevabı aynı yerde olmalı. Bunları ayrı ayrı
hatırlamaya çalışmak, gece yarısı yapılan en pahalı hatadır.

---

## 3. Yayınlama

```bash
git tag v0.1.0
git push origin v0.1.0
```

Sonrası otomatik: imaj üretilir, GHCR'a yayınlanır, künye çıkarılır ve
**hazırlık doğrulaması** çalışır — yayınlanan imaj gerçekten ayağa kalkıp
`/saglik` ucuna cevap veriyor mu? "Build geçti" demek yetmez; çalışmayan
bir imaj da başarıyla üretilebilir.

---

## 4. Geri alma

### 4.1 Yalnızca kod bozulduysa (şema değişmedi)

En basit ve en sık durum. Önceki künyeden digest'i alıp onu çalıştırın:

```bash
docker pull ghcr.io/sara-toptamur36/katilim-ai-api@sha256:ONCEKI_DIGEST
docker stop katilimai-api && docker rm katilimai-api
docker run -d --name katilimai-api -p 8000:8000 \
  -e GERCEK_VERI_AKTIF=true \
  ghcr.io/sara-toptamur36/katilim-ai-api@sha256:ONCEKI_DIGEST
```

Şema değişmediyse burada durun. Veritabanına **dokunmayın**.

### 4.2 Şema da değiştiyse

**Önce kodu geri alın, sonra şemayı.** Ters sırada yaparsanız yeni kod
eski şemayla çalışmaya çalışır ve daha çok şey bozar.

```bash
# 1) Eski imaja dön (yukarıdaki adım)
# 2) Şemayı o sürümün alembic revizyonuna indir
alembic downgrade <onceki_kunyedeki_alembic_surumu>
```

Migration'ların geri alınabilirliği CI'da her PR'da sınanıyor
(`entegrasyon` job'ındaki "Migration gidiş-dönüş" adımı) — yani
`downgrade` yolunun çalıştığı önceden biliniyor, kriz anında öğrenilmiyor.

> **Veri kaybı uyarısı:** `downgrade`, o migration'ın eklediği sütunları
> **siler**. Sütunda veri varsa gider. Şema geri alması gereken bir
> durumda önce yedek alın:
> `docker exec katilimai-postgres pg_dump -U katilim katilimai > yedek.sql`

### 4.3 Model sürümü değiştiyse

Modeller imaja gömülü değildir (bkz. `Dockerfile`), çalışma anında
indirilip `HF_HOME` hacminde önbelleklenir. Model sürümü değiştiyse
künyedeki model adlarını `EMBEDDING_MODELI` ortam değişkeniyle geri
alabilirsiniz; önbellek hacmi silinmediği sürece yeniden indirme olmaz.

---

## 5. Bu kurulumun bilinçli sınırları

**Otomatik dağıtım yok.** `release.yml` imajı üretir ve doğrular; bir
sunucuya **kendiliğinden kurmaz**. Sebep: elimizde çalışan bir üretim
ortamı yok ve olmayan bir ortama dağıtım yapıyormuş gibi görünen bir
boru hattı yazmak, en baştan yanlış olurdu.

**Hazırlık ortamı kalıcı değil.** `hazirlik_dogrulama` job'ı imajı
GitHub Actions makinesinde geçici olarak ayağa kaldırıp saniyeler içinde
kapatır. Bu bir *doğrulama adımıdır*, sürekli çalışan bir staging
ortamı değildir.

**İmaj hâlâ gereğinden büyük.** `requirements.txt` test ve scraper
bağımlılıklarını da içeriyor (playwright, pytest, pandas, openpyxl);
bunlar API çalışma zamanında kullanılmıyor. Ayırmak `requirements.txt`
dosyasını ikiye bölmeyi gerektirir ve bu, ekibin ortak dosyası olduğu
için tek başına yapılmadı.

Buna karşılık **CUDA sürümü ayıklandı**: ilk denemede torch'un GPU
sürümü geliyordu (532 MB torch + 366 MB `nvidia_cudnn` + diğerleri,
~2 GB). API konteynerinde GPU yok, bu kütüphaneler hiç çalıştırılmıyordu.
Dockerfile artık torch'u CPU deposundan kuruyor — sürüm aynı, yapı farklı.

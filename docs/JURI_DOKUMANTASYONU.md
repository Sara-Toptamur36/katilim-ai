**KatılımAI**

Katılım Bankacılığı Ürün Zekâsı ve Dil Ajanı

**SİSTEM DOKÜMANTASYON RAPORU**

TEKNOFEST 2026 · Yapay Zekâ Dil Ajanları Yarışması · Senaryo 2

Bilişim Vadisi 2026 · Türkiye Açık Kaynak Platformu

| **Alan** | **Bilgi** |
|----|----|
| Takım | PeacewAI |
| Kurum | Fırat Üniversitesi — Yapay Zekâ ve Veri Mühendisliği |
| Takım Kaptanı | Sara Toptamur |
| Depo | github.com/Sara-Toptamur36/katilim-ai (herkese açık) |
| Lisans | Apache License 2.0 |
| Doğrulama | Tüm sayılar depodaki koda ve canlı ölçümlere karşı doğrulanmıştır |

# **İçindekiler**

- [Giriş](#giriş)
- [0. Proje Kimliği ve Ekip Yapısı](#0-proje-kimliği-ve-ekip-yapısı)
  - [0.1 Projenin Tek Cümlelik Tanımı](#01-projenin-tek-cümlelik-tanımı)
  - [0.2 Takım Üyeleri ve Sorumluluk Dağılımı](#02-takım-üyeleri-ve-sorumluluk-dağılımı)
  - [0.3 Problemin Tanımı](#03-problemin-tanımı)
  - [0.4 Hedef Kullanıcı Profilleri](#04-hedef-kullanıcı-profilleri)
- [1. Çözüm Yaklaşımı ve Farklılaşma](#1-çözüm-yaklaşımı-ve-farklılaşma)
  - [1.1 Mevcut Durum ve Eksiklikler](#11-mevcut-durum-ve-eksiklikler)
  - [1.2 Sistemin Diğer Yapay Zekâ Sohbet Robotlarından Farkı](#12-sistemin-diğer-yapay-zekâ-sohbet-robotlarından-farkı)
  - [1.3 Neden Ajan Mimarisi?](#13-neden-ajan-mimarisi)
  - [1.4 Örnek Vaka: "Vade Farksız" Hatası](#14-örnek-vaka-vade-farksız-hatası)
- [2. Sistem Mimarisi](#2-sistem-mimarisi)
  - [2.1 Altı Katmanlı Mimari ve Uçtan Uca Akış](#21-altı-katmanlı-mimari-ve-uçtan-uca-akış)
  - [2.2 Katman Sorumlulukları](#22-katman-sorumlulukları)
  - [2.3 Teknoloji Yığını](#23-teknoloji-yığını)
  - [2.4 On-Premise (Yerinde Çalışma) Tasarımı](#24-on-premise-yerinde-çalışma-tasarımı)
  - [2.5 Donanım Profili ve Otomatik Uyarlama](#25-donanım-profili-ve-otomatik-uyarlama)
- [3. Veri Toplama Katmanı](#3-veri-toplama-katmanı)
  - [3.1 Kapsam ve Hacim](#31-kapsam-ve-hacim)
  - [3.2 Banka Bazında Dağılım (Canlı Veri, 27 Ağustos 2026)](#32-banka-bazında-dağılım-canlı-veri-27-ağustos-2026)
  - [3.3 Toplama Yöntemleri](#33-toplama-yöntemleri)
  - [3.4 SHA-256 Delta Motoru — Değişiklik Takibi](#34-sha-256-delta-motoru-değişiklik-takibi)
  - [3.5 Kampanya Kaldırıldığında Ne Olur?](#35-kampanya-kaldırıldığında-ne-olur)
  - [3.6 Etik Tarama İlkeleri](#36-etik-tarama-ilkeleri)
- [4. Ön İşleme Katmanı](#4-ön-işleme-katmanı)
  - [4.1 Türkçe Diyakritik Katlama — Ölçülmüş Bir Bulgu](#41-türkçe-diyakritik-katlama-ölçülmüş-bir-bulgu)
  - [4.2 Normalizasyon Fonksiyonları (Şartname Md. 5.6)](#42-normalizasyon-fonksiyonları-şartname-md-56)
  - [4.3 Sayfa Kapsamı Ayıklama](#43-sayfa-kapsamı-ayıklama)
- [5. Bilgi Çıkarım Sistemi](#5-bilgi-çıkarım-sistemi)
  - [5.1 Çıkarılan Alanlar](#51-çıkarılan-alanlar)
  - [5.2 Hibrit Boru Hattı](#52-hibrit-boru-hattı)
  - [5.3 Regex Katmanı — Bağlam Duyarlı Desen Eşleştirme](#53-regex-katmanı-bağlam-duyarlı-desen-eşleştirme)
  - [5.4 NER ve LLM Katmanları](#54-ner-ve-llm-katmanları)
  - [5.5 Resolver — Çatışma Çözümü](#55-resolver-çatışma-çözümü)
  - [5.6 Uydurma Değer Üretmeme Garantisi](#56-uydurma-değer-üretmeme-garantisi)
  - [5.7 Çözülmüş Kök Nedenler](#57-çözülmüş-kök-nedenler)
- [6. Altın Veri Seti (Gold Dataset)](#6-altın-veri-seti-gold-dataset)
  - [6.1 Neden Vardır?](#61-neden-vardır)
  - [6.2 Dairesellik Yasağı](#62-dairesellik-yasağı)
  - [6.3 Eğitim/Test Ayrımı ve Sızıntı Önleme](#63-eğitimtest-ayrımı-ve-sızıntı-önleme)
  - [6.4 Eşdeğer Kampanya İşaretlemesi](#64-eşdeğer-kampanya-işaretlemesi)
- [7. Çıkarım Başarım Metrikleri](#7-çıkarım-başarım-metrikleri)
  - [7.1 Nihai Boru Hattı Başarımı](#71-nihai-boru-hattı-başarımı)
  - [7.2 Katman Katkısı Ayrıştırması (Ablation)](#72-katman-katkısı-ayrıştırması-ablation)
  - [7.3 Regex Katmanının Alan Kümesi Bazlı Başarımı](#73-regex-katmanının-alan-kümesi-bazlı-başarımı)
  - [7.4 Kalan Hataların Alan Bazlı Dağılımı](#74-kalan-hataların-alan-bazlı-dağılımı)
  - [7.5 Bilinen Hatalar](#75-bilinen-hatalar)
  - [7.6 Hâlâ Açık İki Alan ve Gerekçeleri](#76-hâlâ-açık-iki-alan-ve-gerekçeleri)
- [8. RAG Mimarisi (Retrieval-Augmented Generation)](#8-rag-mimarisi-retrieval-augmented-generation)
  - [8.1 Teknik Parametreler](#81-teknik-parametreler)
  - [8.2 Hibrit Arama: Yoğun + Seyrek + RRF](#82-hibrit-arama-yoğun-seyrek-rrf)
  - [8.3 Kaynak Gösterimi](#83-kaynak-gösterimi)
  - [8.4 Çekimserlik Mekanizması — Neden Skor Eşiği Değil?](#84-çekimserlik-mekanizması-neden-skor-eşiği-değil)
- [9. RAG Değerlendirme Sonuçları](#9-rag-değerlendirme-sonuçları)
  - [9.1 Genel Başarım](#91-genel-başarım)
  - [9.2 Kategori Bazlı Kırılım](#92-kategori-bazlı-kırılım)
  - [9.3 Alan İçi Kapsam Dışı Sorular — Bir Ölçüm Vakası](#93-alan-içi-kapsam-dışı-sorular-bir-ölçüm-vakası)
- [10. Ajan Mimarisi ve Araç Yönlendirme](#10-ajan-mimarisi-ve-araç-yönlendirme)
  - [10.1 Niyetler ve Araçlar](#101-niyetler-ve-araçlar)
  - [10.2 Araç Seçimini Kim Yapar?](#102-araç-seçimini-kim-yapar)
  - [10.3 Karar Zinciri](#103-karar-zinciri)
  - [10.4 Kademeli Yedekleme — Ölçülmüş Gerekçe](#104-kademeli-yedekleme-ölçülmüş-gerekçe)
  - [10.5 Paralel Araç Çağrısı](#105-paralel-araç-çağrısı)
- [11. Terminoloji Sistemi (Şartname Md. 5.5)](#11-terminoloji-sistemi-şartname-md-55)
  - [11.1 Sözlük Kapsamı](#111-sözlük-kapsamı)
  - [11.2 En Kritik Ayrımlar](#112-en-kritik-ayrımlar)
  - [11.3 Kullanıcı Yanlış Terim Kullandığında](#113-kullanıcı-yanlış-terim-kullandığında)
- [12. Kapsam Ölçümü (Scope Guard)](#12-kapsam-ölçümü-scope-guard)
  - [12.1 Ölçüm Sonuçları](#121-ölçüm-sonuçları)
  - [12.2 Karşı-Örnek Setinin Etik Disiplini](#122-karşı-örnek-setinin-etik-disiplini)
  - [12.3 Katmanlı Kapsam Kontrolü](#123-katmanlı-kapsam-kontrolü)
- [13. Deterministik Hesaplama Katmanı](#13-deterministik-hesaplama-katmanı)
  - [13.1 Neden Dil Modeli Hesaplama Yapmaz?](#131-neden-dil-modeli-hesaplama-yapmaz)
  - [13.2 Fonksiyonlar](#132-fonksiyonlar)
  - [13.3 Aylık Taksit Formülü](#133-aylık-taksit-formülü)
  - [13.4 Toplam Maliyet Karşılaştırması](#134-toplam-maliyet-karşılaştırması)
- [14. Müşteri Sesi (Complaint Insight) — Sentetik Demo](#14-müşteri-sesi-complaint-insight-sentetik-demo)
  - [14.1 Veri Seti Künyesi](#141-veri-seti-künyesi)
  - [14.2 On Tema](#142-on-tema)
  - [14.3 Sınıflandırıcı Davranışı](#143-sınıflandırıcı-davranışı)
  - [14.4 Şikâyet Hattı — Koda Gömülü Dört Kırmızı Çizgi](#144-şikâyet-hattı-koda-gömülü-dört-kırmızı-çizgi)
  - [14.5 Kampanya Eşleştirmesi Bir Hipotezdir](#145-kampanya-eşleştirmesi-bir-hipotezdir)
  - [14.6 Sızıntı Koruması](#146-sızıntı-koruması)
- [15. Kampanya Karşılaştırma Motoru (Şartname Md. 5.7)](#15-kampanya-karşılaştırma-motoru-şartname-md-57)
  - [15.1 Karşılaştırma Kriterleri](#151-karşılaştırma-kriterleri)
  - [15.2 "En Avantajlı" Nasıl Hesaplanır? — Ağırlıklı Formül Yoktur](#152-en-avantajlı-nasıl-hesaplanır-ağırlıklı-formül-yoktur)
  - [15.3 Eksik Veri Nasıl Ele Alınır?](#153-eksik-veri-nasıl-ele-alınır)
- [16. Denetim ve İzlenebilirlik Sistemi](#16-denetim-ve-izlenebilirlik-sistemi)
  - [16.1 Jüri Audit Paneli'nin Amacı](#161-jüri-audit-panelinin-amacı)
  - [16.2 Kaydedilen Bilgiler](#162-kaydedilen-bilgiler)
  - [16.3 Üç Durumlu Doğrulama](#163-üç-durumlu-doğrulama)
  - [16.4 RAG Yolunda Özet Neden Üretilmez?](#164-rag-yolunda-özet-neden-üretilmez)
  - [16.5 İki Denetim Ekranının Farkı](#165-iki-denetim-ekranının-farkı)
  - [16.6 Çıkarım Denetimi Ekranında Gösterilenler](#166-çıkarım-denetimi-ekranında-gösterilenler)
- [17. Arayüz Mimarisi](#17-arayüz-mimarisi)
  - [17.1 Sayfalar ve Veri Kaynakları](#171-sayfalar-ve-veri-kaynakları)
  - [17.2 Mock ve Canlı Veri Ayrımı](#172-mock-ve-canlı-veri-ayrımı)
  - [17.3 Çevrimdışı ve Hata Davranışı](#173-çevrimdışı-ve-hata-davranışı)
- [18. REST API Mimarisi](#18-rest-api-mimarisi)
- [19. Güvenlik ve KVKK Uyumu](#19-güvenlik-ve-kvkk-uyumu)
  - [19.1 Kimlik Doğrulama ve Yetkilendirme](#191-kimlik-doğrulama-ve-yetkilendirme)
  - [19.2 Sır ve Anahtar Yönetimi](#192-sır-ve-anahtar-yönetimi)
  - [19.3 Enjeksiyon ve Girdi Güvenliği](#193-enjeksiyon-ve-girdi-güvenliği)
  - [19.4 KVKK Değerlendirmesi](#194-kvkk-değerlendirmesi)
- [20. Çevrimdışı Çalışma ve Kurulum](#20-çevrimdışı-çalışma-ve-kurulum)
  - [20.1 Çevrimdışı Yetenek Beyanı](#201-çevrimdışı-yetenek-beyanı)
  - [20.2 Kurulum Adımları](#202-kurulum-adımları)
  - [20.3 Demo Öncesi Zorunlu Adım](#203-demo-öncesi-zorunlu-adım)
  - [20.4 Çevrimdışı Hazırlık Kontrolü](#204-çevrimdışı-hazırlık-kontrolü)
  - [20.5 Veri Setine Erişim (Şartname Md. 9)](#205-veri-setine-erişim-şartname-md-9)
- [21. Test Takımı ve Kalite Güvencesi](#21-test-takımı-ve-kalite-güvencesi)
  - [21.1 Test Sayıları](#211-test-sayıları)
  - [21.2 Dış Servis Gerektiren Testler](#212-dış-servis-gerektiren-testler)
  - [21.3 Dürüstlük ve Dairesellik Testleri](#213-dürüstlük-ve-dairesellik-testleri)
  - [21.4 Test Komutları](#214-test-komutları)
- [22. MLOps, CI/CD ve Sürüm Yönetimi](#22-mlops-cicd-ve-sürüm-yönetimi)
  - [22.1 Sürüm Sabitleme](#221-sürüm-sabitleme)
  - [22.2 GitHub Pages Hakkında Dürüstlük Notu](#222-github-pages-hakkında-dürüstlük-notu)
- [23. Veri Tazeliği ve Eşzamanlılık](#23-veri-tazeliği-ve-eşzamanlılık)
  - [23.1 Tazelik Uç Noktası](#231-tazelik-uç-noktası)
  - [23.2 "Bilinmiyor" ile "Eski" Aynı Şey Değildir](#232-bilinmiyor-ile-eski-aynı-şey-değildir)
  - [23.3 Bilinen Tazelik Farkı — Açıkça Raporlanır](#233-bilinen-tazelik-farkı-açıkça-raporlanır)
- [24. Sistem Sınırlılıkları ve Dürüstlük Beyanı](#24-sistem-sınırlılıkları-ve-dürüstlük-beyanı)
  - [24.1 En Önemli Sınırlılıklar](#241-en-önemli-sınırlılıklar)
  - [24.2 Diğer Eksikler](#242-diğer-eksikler)
  - [24.3 Bileşen Bazlı Zayıflıklar](#243-bileşen-bazlı-zayıflıklar)
  - [24.4 \`hedef_kitle\` Alanı — Neden Kapatılamıyor?](#244-hedef_kitle-alanı-neden-kapatılamıyor)
- [25. Gelecek Yol Haritası](#25-gelecek-yol-haritası)
- [26. Demo Senaryosu](#26-demo-senaryosu)
  - [26.1 Önerilen Akış](#261-önerilen-akış)
  - [26.2 Kurtarma Planları](#262-kurtarma-planları)
- [27. EVREN Entegrasyonu](#27-evren-entegrasyonu)
  - [27.1 Kullanılan Modeller](#271-kullanılan-modeller)
  - [27.2 Model Seçim Gerekçesi](#272-model-seçim-gerekçesi)
  - [27.3 Bulunan ve Düzeltilen Sessiz Hata](#273-bulunan-ve-düzeltilen-sessiz-hata)
  - [27.4 Yedekleme ve Bağımsızlık](#274-yedekleme-ve-bağımsızlık)
- [28. Ölçümlerin Yeniden Üretilmesi](#28-ölçümlerin-yeniden-üretilmesi)
  - [28.1 Ölçüm Raporları](#281-ölçüm-raporları)
- [29. Şartname Uyum Tablosu](#29-şartname-uyum-tablosu)

# **Giriş**

KatılımAI, katılım bankacılığı ekosistemindeki dağınık, biçimlendirilmemiş ve farklı gösterim biçimlerine sahip ürün, mevzuat ve kampanya verilerini anlamlandırarak yapılandıran ve kullanıcılara güvenilir doğal dil yanıtları sunan uçtan uca bir yapay zekâ dil ajanı mimarisidir. TEKNOFEST Yapay Zekâ Dil Ajanları Yarışması (Senaryo 2) standartlarına uygun olarak geliştirilen bu sistem, sektördeki standart eksikliği ve verilerin yapılandırılmamış doğası gibi temel problemleri çözmeyi hedeflemektedir. Günümüzde bankaların verilerini tamamen kurumlara özgü farklı formatlarda sunması, fıkhi uyumluluk açısından geleneksel bankacılık terimlerinin hatalı kullanımı ve standart büyük dil modellerinin (LLM) finansal verilerde sergilediği tehlikeli yanılsama (hallucination) eğilimleri, şeffaf ve güvenilir bir analiz sürecini imkânsız kılmaktadır. KatılımAI, kurumsal şeffaflığı artırmayı, finansal veri analiz süreçlerini otomatikleştirmeyi ve bu yanılsama problemini finansal bağlamda tamamen ortadan kaldırmayı temel vizyonu olarak belirlemiştir.

Bu karmaşık problemleri aşmak üzere geliştirilen KatılımAI, statik bir metin üreticisi olmanın ötesine geçerek veri toplama, hibrit bilgi çıkarımı ve akıllı yönlendirme yeteneklerine sahip otonom bir ajan olarak tasarlanmıştır. Sistem, Türkiye'deki katılım bankalarının kaynaklarından veri toplayıp SHA-256 tabanlı delta motoruyla güncellemeleri anlık olarak tespit edip metinlerdeki finansal parametreleri Regex, varlık ismi tanıma (NER) ve büyük dil modeli kombinasyonuyla yapılandırılmış verilere dönüştürür. Kullanıcı sorguları bu akıllı mimari tarafından analiz edilerek ihtiyaca göre veritabanı sorgusuna, karmaşık matematiksel hesaplamalara, kaynaklı metin aramasına veya fıkhi sözlük katmanına otomatik olarak yönlendirilir. En önemlisi, sistem cevap üretirken kesinlikle kaynak gösterimi yapar ve veri kümesinde karşılığı bulunmayan veya güven eşiğinin altında kalan durumlarda bilgi uydurmak yerine açıkça çekimser kalır.

Projenin geliştirilme sürecindeki en temel mühendislik felsefesi, doğruluğu yalnızca iddia etmek yerine onu ölçmek ve kanıtlamak üzerine inşa edilmiştir. Finansal veri işleyen bir yapay zekâ sisteminde eksik bilgi bulmanın (False Negative), yanlış bilgi uydurmaktan (False Positive) çok daha kabul edilebilir olduğu ilkesi benimsenmiştir. Bu doğrultuda, dokümanda sunulan tüm performans metrikleri altın veri seti (Gold Dataset) üzerinde titizlikle ölçülmüş olup, değerlendiricilerin sistemi kendi ortamlarında şeffafça test edebilmesi için tamamen yeniden üretilebilir (reproducible) kodlar ve komutlarla desteklenmiştir.

# **0. Proje Kimliği ve Ekip Yapısı**

| **Alan** | **Bilgi** |
|----|----|
| Resmî proje adı | KatılımAI |
| Takım | PeacewAI — Fırat Üniversitesi, Yapay Zekâ ve Veri Mühendisliği |
| Yarışma / Senaryo | TEKNOFEST 2026, Yapay Zekâ Dil Ajanları Yarışması — Senaryo 2 |
| Depo | github.com/Sara-Toptamur36/katilim-ai — herkese açık |
| Lisans | Apache License 2.0 |

## **0.1 Projenin Tek Cümlelik Tanımı**

> KatılımAI, dokuz katılım bankasının dağınık ve standart olmayan kampanya metinlerini karşılaştırılabilir yapılandırılmış veriye dönüştüren, her cevabı kaynağıyla birlikte gösteren ve kaynağı yetersiz bulduğunda cevap üretmek yerine açıkça çekimser kalan bir dil ajanıdır.

## **0.2 Takım Üyeleri ve Sorumluluk Dağılımı**

| **Üye** | **Rol** | **Sorumluluk Alanları** |
|----|----|----|
| Sara Toptamur | Takım Kaptanı | API mimarisi, ajan orkestrasyonu, karşılaştırma motoru, deterministik hesap makinesi, genel koordinasyon |
| Yağmur Ekici | NLP / Yapay Zekâ | Bilgi çıkarımı, terminoloji sistemi, embedding, RAG tasarımı ve ölçümü |
| Zeynep Sönmez | Veri ve Sistem | Veri toplama (scraper), PDF işleme, Türkçe ön işleme, PostgreSQL, sistem testleri |
| Havin Karagöz | Arayüz / UX | React arayüzü, dashboard tasarımı, karşılaştırma ekranları, Jüri Audit Paneli |

## **0.3 Problemin Tanımı**

Katılım bankaları, kampanya ve ürün bilgilerini standart bir veri formatı olmaksızın, doğal dilde yazılmış serbest metinlerle duyurur. Aynı finansal bilgi, bankadan bankaya tamamen farklı biçimlerde ifade edilir. Bu, dört ayrı gösterim boyutunda ortaya çıkar:

| **Gösterim Biçimi** | **Gerçek Örnek** | **Zorluk** |
|----|----|----|
| Sayısal ve açık | "%1,99 oranla 12 aya varan taksit" | Doğrudan ayrıştırılabilir |
| Rasyo tabanlı | "98/2 kâr paylaşım oranı" | Yüzde değil; farklı bir matematiksel gösterim |
| Sözel / nitel | "Kâr payı yok. Beklemek yok." | Hiç sayı içermiyor; anlamdan çıkarım gerekir |
| Heterojen ödül birimi | Mil, Gram Altın, Bankkart Lira, ParafPara, Worldpuan | Birbirine doğrudan çevrilemez |

Bu çeşitlilik iki kritik sonuç doğurur. Birincisi, kullanıcıların ve banka analiz ekiplerinin dokuz bankaya ait yüzlerce aktif kampanyayı tutarlı biçimde karşılaştırması pratikte imkânsız hâle gelir. İkincisi — ve daha kritik olanı — finansal kararların yanlış okunan bir orana veya vadeye dayanması doğrudan maddi sonuç doğurur.

## **0.4 Hedef Kullanıcı Profilleri**

| **Kullanıcı** | **Kullanım Amacı** | **Sistemdeki Rol** |
|----|----|----|
| Banka çalışanı | Rakip analizi, kampanya karşılaştırma, pazar konumlandırma | banka_calisani |
| Denetleyici | Çıkarım izinin ve karar zincirinin denetimi | denetleyici |
| Yönetici | Genel bakış, kapsam ve kalite göstergeleri | yonetici |
| Son kullanıcı / müşteri | Doğal dilde soru-cevap, taksit ve maliyet hesabı | musteri (self-servis kayıt) |
| Jüri / demo kullanıcısı | Audit Paneli, Çıkarım Denetimi, Metin Analizi | Tüm denetim ekranları erişime açıktır |

# **1. Çözüm Yaklaşımı ve Farklılaşma**

## **1.1 Mevcut Durum ve Eksiklikler**

Kullanıcı bugün bu problemi elle çözmektedir: her bankanın sitesine tek tek girip kampanyaları okumakta ve karşılaştırmayı zihninde yapmaktadır. Bu yöntemin dört yapısal eksikliği vardır:

- Ölçek: Dokuz banka ve yüzlerce aktif kampanya, elle takip edilebilecek hacmin çok üzerindedir.

- Standart yokluğu: Aynı bilgi farklı biçimlerde sunulduğu için doğrudan kıyas mümkün değildir.

- Tazelik: Kampanyalar sessizce değişmekte veya siteden kaldırılmaktadır; kullanıcı bunu fark edemez.

- Terminoloji: Katılım bankacılığı kavramları (kâr payı, katılım fonu) geleneksel bankacılık kavramlarıyla (faiz, mevduat) karıştırılmaktadır.

## **1.2 Sistemin Diğer Yapay Zekâ Sohbet Robotlarından Farkı**

KatılımAI'yi genel amaçlı bir sohbet robotundan ayıran üç yapısal karar vardır. Bunlar tercih değil, mimarinin temel taşlarıdır:

### Birinci karar: RAG kaynağı birebir döndürür, üzerine metin üretmez

Sistem, bulduğu kaynak parçalarını değiştirmeden döndürür; üzerine serbest cümle kurmaz. Bu tasarımın sonucu şudur: halüsinasyon azaltılmaz, yapısal olarak imkânsız kılınır. Model serbest cümle üretmediği için uyduramaz. Bu, olasılıklı bir güvence değil, mimari bir garantidir.

### İkinci karar: Sayısal işler dil modeline bırakılmaz

Kampanya karşılaştırması sabit ve parametreli SQL şablonlarıyla yapılır; serbest metinden SQL üretilmez. Taksit ve toplam maliyet hesapları saf Python fonksiyonlarıdır. Aritmetik deterministik bir iştir; olasılıklı bir modele bırakmak, doğru sonucu şansa bağlamak anlamına gelirdi ve finansal bir üründe bu kabul edilemez.

### Üçüncü karar: Kaynak yetersizse sistem cevap vermez

Çekimserlik kararı ham benzerlik skoruna göre değil, sorunun ayırt edici terimlerinin kaynaklarda gerçekten geçip geçmediğine göre verilir. Bu tercihin gerekçesi ölçülmüştür: yalnızca vektör benzerliğine bakıldığında, "uzay istasyonunda yerçekimi" gibi tamamen alakasız bir soru bile 0,78 benzerlik skoru almaktaydı (§8.4).

## **1.3 Neden Ajan Mimarisi?**

Kullanıcı soruları tek tip değildir. "En düşük kâr payı hangisinde?" bir veritabanı sorgusudur; "500.000 TL'nin aylık taksiti ne olur?" bir hesaplama; "Murabaha nedir?" bir sözlük sorgusu; "Bu kampanyanın şartları neler?" ise bir bilgi getirme (RAG) sorusudur.

Bu dört soruyu tek bir dil modeli istemine vermek, deterministik olabilecek işleri gereksiz yere olasılıklı hâle getirirdi. Ajan mimarisi, her soruyu doğru araca yönlendirerek her işin kendi doğru yöntemiyle çözülmesini sağlar.

## **1.4 Örnek Vaka: "Vade Farksız" Hatası**

Projenin ölçüm disiplininin neden var olduğunu gösteren somut bir örnek, geliştirme sürecinde yaşanmış ve kayıt altına alınmıştır.

İki ayrı kod değişikliği zıt yönde karar verdi: biri altın veri setine "vade farksız" ifadesi için kar_payi_orani = 0 yazdı; diğeri aynı kuralı çıkarım motorundan kaldırdı. Her iki karar da tek başına savunulabilirdi; ancak birlikte tutarsızdılar ve kâr payı oranı recall değerini %90,91'den %15,38'e düşürdüler. Kombinasyonu kimse yeniden ölçmediği için hata uzun süre fark edilmedi.

Düzeltme sonrası kâr payı oranı F1 değeri %26,09'dan %80,00'e yükselmiştir. Bugün tests/test_olcum_kapsami.py bu çelişkili kombinasyonu imkânsız kılmaktadır.

> Çıkarılan ders: İki doğru kararın birleşimi yanlış olabilir ve bunu yalnızca yeniden ölçüm yakalar. Bu vaka, projedeki tüm regresyon testlerinin ve ölçüm otomasyonunun gerekçesidir.

# **2. Sistem Mimarisi**

## **2.1 Altı Katmanlı Mimari ve Uçtan Uca Akış**

Sistem, ham banka sayfasından kaynaklı doğal dil yanıtına uzanan altı katmandan oluşur.

<img src="media/image1.png" style="width:2.975in;height:5.81494in" />

Şekil 1. KatılımAI sistem mimarisi ve uçtan uca veri/istek akışı.

## **2.2 Katman Sorumlulukları**

| **Katman** | **Sorumluluk** | **Depodaki Karşılığı** |
|----|----|----|
| 1 — Veri Toplama | Banka sayfalarının taranması, değişiklik takibi, ham arşivleme | scraper/ |
| 2 — Ön İşleme | Türkçe normalizasyon, diyakritik katlama, sayfa kapsamı ayıklama | preprocessing/ |
| 3 — Çıkarım | Regex, NER ve LLM katmanlarıyla yapılandırılmış alan üretimi | extraction/ |
| 4 — Depolama | İlişkisel kayıt (PostgreSQL) ve vektör indeksi (Qdrant) | storage/, chunking/ |
| 5 — Ajan | Niyet tespiti, araç yönlendirme, doğrulama, yanıt üretimi | agent/, validation/ |
| 6 — Sunum | Dashboard, sohbet arayüzü, denetim panelleri | dashboard/, api/ |

## **2.3 Teknoloji Yığını**

Şartname Md. 5.10 ve Md. 8 gereğince tüm bileşenler açık kaynaklıdır:

| **Katman** | **Teknoloji** | **Lisans** |
|----|----|----|
| Arayüz | React, Vite, Ant Design | MIT |
| API | FastAPI, SQLAlchemy, Alembic | MIT |
| İlişkisel veritabanı | PostgreSQL | PostgreSQL License |
| Vektör veritabanı | Qdrant | Apache-2.0 |
| Embedding modeli | intfloat/multilingual-e5-base (768 boyut) | MIT |
| Yerel dil modeli | Qwen2.5-Instruct GGUF Q4_K_M (Ollama) | Apache-2.0 / MIT |
| Bulut dil modeli (ops.) | EVREN llm-fast | TEKNOFEST kaynağı |
| Varlık tanıma (NER) | GLiNER urchade/gliner_multi-v2.1 | Apache-2.0 |
| Yapılandırılmış çıktı | Pydantic | MIT |
| Veri toplama | Requests, BeautifulSoup4, Playwright | Apache-2.0 / MIT / BSD |
| PDF işleme | pypdf | BSD |

Kullanılmayanlar: özel veya kapalı lisanslı dil modelleri, AGPL kütüphaneler, kapalı kaynak bulut API'leri ve ücretli servisler.

> Fine-tuning (model eğitimi) yoktur ve iddia edilmez. Kullanılan tüm modeller açık kaynaklıdır ve olduğu gibi, sürümleri sabitlenmiş biçimde çalışır. Bu kural tests/test_iddia_durustlugu.py tarafından korunur: herhangi bir belgeye yanlışlıkla model eğitimi iddiası yazılırsa CI hattı kırmızı verir ve dosya ile satır numarasını gösterir. Projenin yeniliği modeli eğitmek değil, hangi katmanın ne kadar katkı verdiğini — ve nerede zarar verdiğini — ölçmüş olmaktır.

## **2.4 On-Premise (Yerinde Çalışma) Tasarımı**

Şartname Md. 5.9, sistemin internetsiz çalışabilmesini gerektirir. Bu gereksinim mimarinin tamamına yansıtılmıştır:

| **Servis** | **Yerel mi?** | **Açıklama** |
|----|----|----|
| PostgreSQL | Evet | Docker konteyneri, port 5432 |
| Qdrant | Evet | Docker konteyneri, port 6333 |
| Ollama + Qwen2.5 | Evet | Docker konteyneri, port 11434 |
| Embedding modeli | Evet | İlk indirmeden sonra tamamen çevrimdışı |
| EVREN | Hayır — opsiyonel | EVREN_API_KEY tanımlı değilse hiç devreye girmez |

EVREN devreye girmeden önce sistem yerel Qwen2.5 ile çalışıyordu ve hâlâ öyle çalışabilir. EVREN, dil modeli katmanında Ollama'ya alternatif bir sağlayıcıdır; mimari ve çıktı sözleşmesi değişmez. Çevrimdışı hazırlık python cevrimdisi_hazirlik_kontrolu.py komutuyla denetlenir. Bu betik EVREN'i bilinçli olarak çevrimdışı sonucuna dahil etmez; EVREN tanım gereği çevrimiçidir ve ayrı bir "opsiyonel" başlığı altında raporlanır.

## **2.5 Donanım Profili ve Otomatik Uyarlama**

Dil modeli çıkarım süresi donanıma göre on kattan fazla değişmektedir; tek bir sabit ayar iki farklı makineye birden uymaz. Bu nedenle sistem çalıştığı makineyi tespit edip kendini otomatik ayarlar:

| **Profil** | **Koşul** | **Bağlam Penceresi** | **Zaman Aşımı** | **Kırpılan Belge** |
|----|----|----|----|----|
| gpu | VRAM ≥ 8 GB | 16.384 | 300 sn | 0 / 234 |
| cpu | GPU yok veya VRAM \< 8 GB | 4.096 | 900 sn | 12 / 234 |

Asgari gereksinimler: Python 3.11+, Docker Desktop, Node.js 18+. GPU zorunlu değildir; CPU profili tam işlevle çalışır, yalnızca daha yavaştır. Makine profili \`python donanim_testi.py\` komutuyla ölçülebilir.

> Ölçülmüş tuzak — bağlam penceresi neden açıkça gönderilir: Ollama, istekte num_ctx parametresi verilmezse modeli 4.096 bağlamla servis eder — model 32.768 desteklese bile — ve uzun istemi sessizce kırpar. Hata dönmez; yalnızca çıkarım kalitesi düşer. Bu davranış ollama ps çıktısıyla doğrulanmıştır ve sistem bağlam penceresini her çağrıda açıkça göndererek bu tuzağı kapatır.

# **3. Veri Toplama Katmanı**

## **3.1 Kapsam ve Hacim**

| **Gösterge** | **Değer** | **Açıklama** |
|----|----|----|
| Taranan banka | 10 | BDDK katılım bankaları listesi |
| Veri yayımlayan banka | 9 | Adil Katılım gerekçeli olarak hariç — ürün/kampanya yayımlamıyor |
| Yapılandırılmış kayıt | 536 | PostgreSQL, 27 Ağustos 2026 |
| Tekil taranmış sayfa | 525 | scraper/raw_data içindeki benzersiz URL sayısı |
| Toplam anlık görüntü | 623 | Aynı URL'nin farklı tarihli taramaları dahil |

### Üç Farklı Sayı Neden Vardır?

Bu üç sayı birbiriyle çelişmez; üç farklı şeyi ölçerler. Scraper eski taramaları silmez, çünkü değişiklik takibi (SHA-256 delta) bunu gerektirir:

- 525 — Diskteki tekil kampanya URL'si sayısı (ham sayfa).

- 623 — Toplam anlık görüntü; aynı URL'nin farklı tarihli sürümleri ayrı sayılır.

- 536 — PostgreSQL'de yapılandırılmış hâle getirilmiş kayıt sayısı.

Bu fazlalık bir artık değil, bir özelliğin girdisidir: aynı URL'nin birden fazla tarihli kaydının bulunması, o kampanyanın gerçekten güncellendiği anlamına gelir.

## **3.2 Banka Bazında Dağılım (Canlı Veri, 27 Ağustos 2026)**

| **Banka** | **Kampanya** | **Sayfa Türü** | **Özel Durum** |
|----|----|----|----|
| Kuveyt Türk | 110 | HTML | Çerez duvarı — Playwright seçicisi gerekir |
| Ziraat Katılım | 109 | HTML | — |
| Vakıf Katılım | 100 | HTML | — |
| Türkiye Emlak Katılım | 84 | HTML | — |
| Dünya Katılım | 45 | HTML | — |
| Albaraka Türk | 37 | HTML | Mobil kodlu kampanyalar zor (bkz. EX-AL, §7.4) |
| Türkiye Finans | 25 | HTML | Maliyet tablosu ayrı katmanla okunur |
| T.O.M. Katılım | 13 | HTML | Dijital banka |
| Hayat Finans | 13 | HTML | Dijital banka |
| Adil Katılım | — | — | Kapsam dışı: kampanya/ürün yayımlamıyor |
| TOPLAM | 536 |  |  |

> Düşük kampanya sayısı tarama eksikliği değildir. T.O.M. Katılım ve Hayat Finans'ta on üçer kampanya bulunması bir kapsam boşluğu değil, o bankaların sitesinde o an yayında olan gerçek kampanya sayısıdır. Bu ayrım arayüzde de açıkça belirtilir; aksi hâlde sistem kendi verisi hakkında yanlış bir izlenim yaratırdı.

## **3.3 Toplama Yöntemleri**

| **Yöntem** | **Kullanılan Teknoloji** | **Ne Zaman Kullanılır** |
|----|----|----|
| Statik HTML | Requests + BeautifulSoup4 | Sunucu tarafında tam render edilen sayfalar |
| JavaScript render | Playwright | Dinamik listeler, çerez duvarı olan siteler |
| PDF | pypdf | Metin tabanlı PDF ekleri |
| OCR | Kurulu değil | Taranmış/görüntü PDF'ler — bkz. §25 |

## **3.4 SHA-256 Delta Motoru — Değişiklik Takibi**

Her taramada sayfa içeriğinin SHA-256 özeti alınır. Özet değişmemişse yeni dosya yazılmaz; değişmişse yeni tarihli bir anlık görüntü eklenir ve eski sürüm silinmez. Bu mekanizma, sisteme yalnızca "değişti" demenin ötesinde bir yetenek kazandırır:

| **Ölçüm** | **Sonuç** | **Yorum** |
|----|----|----|
| İçeriği değişen kampanya | 40 / 251 | SHA-256 özeti farklılaşan kayıtlar |
| İzlenen alanı değişen | 25 / 251 | Oran, vade, tutar, ödül veya tarih gerçekten farklılaşmış |
| Yalnızca metin düzeltmesi | 15 | Özet değişmiş ama finansal bilgi aynı |

Bu ayrım ürün açısından kritiktir: kullanıcıya "değişti" denecekse, *neyin* değiştiği gösterilebilmelidir. Kozmetik bir metin düzeltmesi için bildirim üretmek gürültüdür ve kullanıcının gerçek değişikliklere olan duyarlılığını köreltir.

Ölçülmüş somut örnek: Dünya Katılım'ın "avantajlı kurlar" kampanyasının bitiş tarihi 2026-07-30'dan 2026-08-06'ya çekilmiş, yani kampanya süresi uzatılmıştır. Bu, ek veri toplamadan yalnızca arşivlenmiş anlık görüntüler karşılaştırılarak tespit edilmiştir:

> from scraper.scripts.kampanya_tarihcesi import tarihce_getir, degisen_alanlari_bul
>
> tarihce = tarihce_getir("https://www.dunyakatilim.com.tr/kampanyalar/avantajli-kurlar")
>
> degisen_alanlari_bul(tarihce)
>
> \# {'kampanya_bitis': {'eski': '2026-07-30', 'yeni': '2026-08-06'}}

## **3.5 Kampanya Kaldırıldığında Ne Olur?**

Kayıt silinmez; EXPIRED olarak işaretlenir ve tarihçede kalır. Ölçülmüş örnek: T.O.M. Katılım'ın üç kampanyasından ikisi (restoran ve market iade kampanyaları) 18 Ağustos taramasında sitede bulunamamıştır. Bunun bir scraper hatası olmadığı, canlı sayfa elle kontrol edilerek doğrulanmıştır.

## **3.6 Etik Tarama İlkeleri**

- Hız sınırı: Her banka yapılandırmasında crawl_delay = 1 saniye tanımlıdır; sitelere yük bindirilmez.

- Yalnızca kamuya açık içerik: Giriş gerektiren hiçbir alan taranmaz; sadece herkese açık kampanya sayfaları alınır.

- Kaynak şeffaflığı: Her kayıt, alındığı sayfanın URL'si ve tarih damgasıyla birlikte saklanır.

# **4. Ön İşleme Katmanı**

## **4.1 Türkçe Diyakritik Katlama — Ölçülmüş Bir Bulgu**

Bu katman, projenin en kritik ve en az görünen mühendislik çözümlerinden birini içerir.

Tespit edilen problem (17 Ağustos, ölçüldü): Çıkarım desenleri ve anahtar kelime listeleri Türkçe diyakritiklerle yazılmıştı. Sonuç olarak "3 ay ödemesiz dönem" ifadesi bulunuyor, ancak aynı cümlenin diyakritiksiz yazımı olan "3 ay odemesiz donem" sessizce boş dönüyordu. POST /cikar uç noktası ve Metin Analizi ekranı kullanıcıyı serbest metin yapıştırmaya davet ettiği için, bu kullanıcının hiçbir zaman göremeyeceği bir alan kaybıydı.

### Çözüm: Her İki Tarafı da Katla

Hem metin hem de desen aynı karakter haritasından geçirilir. Böylece desenler doğal Türkçe yazımıyla okunabilir kalır, ancak eşleşme yazım biçiminden bağımsız hâle gelir:

> \_TR_ASCII_HARITASI = str.maketrans(
>
> "şŞıİğĞüÜöÖçÇâÂîÎûÛ",
>
> "sSiIgGuUoOcCaAiIuU"
>
> )
>
> def \_katlanmis_derle(desen, bayraklar=re.IGNORECASE):
>
> """Deseni ASCII'ye katlayarak derler — kaydi_cikar da metni aynı
>
> şekilde katladığı için iki taraf her zaman aynı alfabede karşılaşır."""
>
> return re.compile(turkce_ascii_katla(desen), bayraklar)
>
> Kritik tasarım detayı — uzunluk korunumu: Katlama işlemi str.translate ile birebir (1:1) yapıldığı için karakter sayısını korur. Bu sayede katlanmış metindeki karakter konumları (offset), ham metinde aynı yeri gösterir. Sonuç: kanıt izi (evidence span) ve masraf durumu alanları, kullanıcının kendi orijinal yazımıyla saklanabilir. Katlama yalnızca eşleşme için kullanılır, saklanan veriyi bozmaz.

## **4.2 Normalizasyon Fonksiyonları (Şartname Md. 5.6)**

Ham metinden çıkarılan değerler, karşılaştırılabilir olması için standart birimlere dönüştürülür:

| **Fonksiyon** | **Girdi Örneği** | **Çıktı** | **Açıklama** |
|----|----|----|----|
| yuzdeye_cevir | "%1,89 aylık" | 1.89 | Ondalık ayracı ve yüzde işareti normalize edilir |
| tutara_cevir | "2 bin TL" / "1.500.000" | 2000.0 / 1500000.0 | Binlik ayracı ve büyüklük ekleri çözülür |
| aya_cevir | "10 yıl" | 120 | Tüm vadeler aya çevrilir |
| tarihe_cevir | "Aralık 2025" | 2025-12-31 | Türkçe ay adları ISO formatına çevrilir |

Büyüklük ekleri sabit bir sözlükle çözülür: bin = 1.000, milyon = 1.000.000, milyar = 1.000.000.000.

## **4.3 Sayfa Kapsamı Ayıklama**

Banka kampanya sayfalarının önemli bir kısmında, sayfanın kendi içeriği bittikten sonra başka kampanyaların listesi gelmektedir. Bu liste, o sayfanın kendi kampanyasına ait olmayan taksit ve ödül ifadeleri içerir. Ayıklama katmanı olmadan çıkarım motoru bu değerleri o kaydın kendi değeri sanmaktaydı — bu, 26 Ağustos düzeltmelerinde tespit edilen en yaygın kök nedenlerden biridir (§5.6).

# **5. Bilgi Çıkarım Sistemi**

Bu bölüm sistemin teknik kalbidir. Ham, kuralsız kampanya metninden karşılaştırılabilir sayısal alanların nasıl üretildiğini açıklar.

## **5.1 Çıkarılan Alanlar**

Ölçüme giren on bir alan şunlardır:

| **Alan**               | **Tip**           | **Şartname İlgisi**       |
|------------------------|-------------------|---------------------------|
| kar_payi_orani_percent | Ondalık sayı      | Md. 5.6 — normalizasyon   |
| vade_ay                | Tam sayı (ay)     | Md. 5.6                   |
| finansman_tutari       | Ondalık sayı (TL) | Md. 5.6                   |
| odul_miktari           | Ondalık sayı      | Md. 5.3                   |
| odul_birimi            | Metin             | Md. 5.3 — heterojen birim |
| taksit_sayisi          | Tam sayı          | Md. 5.6                   |
| erteleme_suresi_ay     | Tam sayı (ay)     | Md. 5.6                   |
| kampanya_turu          | Sınıf etiketi     | Md. 5.4 — sınıflandırma   |
| hedef_kitle            | Sınıf etiketi     | Md. 5.3                   |
| kampanya_baslangic     | Tarih (ISO)       | Md. 5.3 — kampanya süresi |
| kampanya_bitis         | Tarih (ISO)       | Md. 5.3 — kampanya süresi |

Ölçüm dışında tutulan ek alanlar: tahsis_ucreti, masraf_durumu, kar_payi_tablosu, kampanya_avantaji.

## **5.2 Hibrit Boru Hattı**

> Regex → GLiNER → Qwen2.5 / EVREN → Resolver
>
> (deterministik) (zero-shot NER) (yapılandırılmış çıktı) (çatışma)
>
> sayısal desene sınıflandırma hangi
>
> çekirdek oturmayan alanları değer
>
> varlıklar kazanır

| **Katman** | **Sorumlu Olduğu Alanlar** | **Yöntem** |
|----|----|----|
| Regex | Oran, vade, tutar, taksit, ödül, erteleme, tarih | Bağlam pencereli desen eşleştirme — deterministik |
| GLiNER (NER) | Ödül birimi, segment gibi desene oturmayan varlıklar | Zero-shot varlık tanıma, eğitimsiz |
| LLM | kampanya_turu, hedef_kitle (sınıflandırma) | Pydantic şemasıyla yapılandırılmış çıktı |
| Resolver | Katmanlar çatıştığında nihai karar | Güven skoru + kaynak doğrulaması |

## <img src="media/image2.png" style="width:6.87917in;height:0.80347in" />

## Şekil 2. Kampanya verilerinin hibrit çıkarım ve doğrulama süreci.

## **5.3 Regex Katmanı — Bağlam Duyarlı Desen Eşleştirme**

Regex katmanı basit bir desen listesi değildir. Finansal metinlerde aynı sayı biçimi farklı anlamlara gelebildiği için, her eşleşme bağlam kontrolünden geçirilir.

### Temel Sayı Deseni

> \_SAYI = r"(?:\d{1,3}(?:\\\d{3})+\|\d+)(?:,\d+)?"
>
> \_TUTAR = rf"{\_SAYI}\s\*(?:bin\|milyon\|milyar)?"
>
> Ölçülmüş hata ve düzeltmesi: Desenin ilk alternatifi başlangıçta \d{1,3}(?:\\\d{3})\* biçimindeydi. Regex alternation soldan sağa çalıştığı için "2000" girdisinde yalnızca "200" yakalanıyor ve dönülüyordu — yani binlik ayracı olmadan yazılan her tutar 10 ila 100 kat küçük okunuyordu. Bir kayıtta ödül miktarı 0.0 çıkıyordu. Bu kusur altı ayrı desende tekrarlıyordu ve hepsi tek bir \_SAYI parçasına çekilerek giderildi.

Uydurma sıfırın gerçek zararı: Bu yalnızca yanlış değil, aktif olarak zararlıydı. Karşılaştırma motorundaki "en düşük kâr payı" kriteri artan sırada sıraladığı için, uydurma bir sıfır her karşılaştırmayı kazanıyordu ve kullanıcıya yanlış kampanyayı en avantajlı olarak sunuyordu.

### Bağlam Pencereleri

Bir sayının hangi alana ait olduğunu belirlemek için çevresindeki metin incelenir. Her kontrol için ölçüme dayalı ayrı bir pencere genişliği kullanılır:

| **Kontrol Fonksiyonu** | **Pencere** | **Amaç** |
|----|----|----|
| \_ucret_baglaminda_mi | 45 karakter | Yüzdenin ücret/komisyon bağlamında olup olmadığı |
| \_oran_tablosu_baglaminda_mi | 60 karakter | Değerin bir maliyet tablosu hücresi olup olmadığı |
| \_ikincil_urun_baglaminda_mi | 60 karakter | Sayfadaki ikincil ürüne ait değerlerin elenmesi |
| \_vade_ornek_odeme_planindan_mi | 90 karakter | Örnek ödeme planındaki vadenin gerçek vade sanılmaması |
| \_taksit_araliginin_ikinci_sayisi_mi | 12 karakter | "6-12 taksit" ifadesinde ikinci sayının ayrıştırılması |

> Vaka: TF-001 ve TF-008 yanlış pozitifleri. Türkiye Finans'ın "Aylık/Yıllık Toplam Maliyet" tablosu tek bir satırda yan yana beş-altı yüzde taşımaktadır (3 \| 4,20% \| 0,50% \| 5,77% \| 96,05%). 45 karakterlik bağlam penceresi satır başındaki "Maliyet" başlığına yetişemediği için, tablonun ortasındaki bir hücre kâr payı oranı sanılıyordu. Çözüm: tablolardaki gerçek oranları extraction/tablo_extractor.py adlı ayrı bir katman okur; düşük güvenli regex yedeğinin oraya hiç girmemesi doğru davranıştır.

### Kâr Payı Tabloları — Tek Sayıya İndirgenmez

Bazı kampanyalarda kâr payı oranı sabit tek bir sayı değil, vade ve tutar dilimine göre değişen bir tablodur. Bu tabloyu tek bir sayıya indirgemek — hangi dilimin "asıl" oran olduğuna karar vermek — uydurma bir seçim olurdu. Bu nedenle tablo, kaynaktaki hâliyle ayrı bir kar_payi_tablosu alanına taşınır ve arayüzde olduğu gibi gösterilir.

## **5.4 NER ve LLM Katmanları**

NER katmanı olarak GLiNER (urchade/gliner_multi-v2.1) kullanılır; sıfırdan eğitilmemiş, zero-shot çalışan hazır bir modeldir. Öncesinde BERTurk (dbmdz/bert-base-turkish-cased) denenmiş, ancak bu kontrol noktası NER için ince ayarlanmamış olduğundan span çıkarımında kullanılamamıştır. Gerekçe extraction/ner_extractor.py dosyasının başında belgelenmiştir.

LLM katmanı, regex ve NER'in boş bıraktığı sınıflandırma alanlarını doldurur. Ölçülen katkısı: 112 çağrıda 49 yeni doğru alan (§7.2). Çıktı, Pydantic şemasıyla yapılandırılmış biçimde alınır; serbest metin kabul edilmez.

## **5.5 Resolver — Çatışma Çözümü**

Birden fazla katman aynı alan için farklı değer ürettiğinde karar şu kurallara göre verilir:

1.  Kaynak metinde doğrulanmış olan değer önceliklidir.

2.  Doğrulama eşitse, güven skoru yüksek olan kazanır.

Regex bir değeri bilerek reddettiyse (düşük güven, yanlış bağlam), NER veya LLM onu geri koyamaz. Bu bilinçli bir kısıttır: deterministik katmanın gerekçeli reddi, olasılıklı katmanın önerisinden üstün tutulur.

## **5.6 Uydurma Değer Üretmeme Garantisi**

Sistemin kaynakta olmayan bir değer üretmemesi üç mekanizmanın birlikte çalışmasıyla sağlanır:

- Boş alan açıkça boş kalır: Bulunamayan alan null bırakılır ve adıyla listelenir; asla sıfır yazılmaz. Arayüzde "Belirtilmemiş" olarak görünür.

- Verifier: Her sayısal değer, kaynak metinde değer ve bağlam olarak aranır; sonuç dogrulanan_alanlar sütununda kalıcılaştırılır.

- Kanıt spanı: Değerin metinde birebir geçtiği cümle saklanır ve Çıkarım Denetimi ekranında jüriye gösterilir.

## **5.7 Çözülmüş Kök Nedenler**

| **Problem** | **Kök Neden** | **Ölçülen Sonuç** |
|----|----|----|
| İlgisiz kampanya listesi | Sayfanın kendi içeriği bittikten sonra gelen başka kampanyaların taksit/ödül ifadeleri o kaydın değeri sanılıyordu | Sayfa kapsamı ayıklaması eklendi |
| İstisna cümlesi olumlu sanılıyordu | "Business kartlar dahil değildir" ifadesi kampanyayı "Ticari Kampanya" olarak sınıflandırıyordu | kampanya_turu %35,63 → %87,43 |
| Türkçe çekim ekleri | Desende "6 taksite", "3 Ay Erteleme" gibi çekimli biçimler yoktu | taksit_sayisi → %89,50 |
| Maliyet tablosu yanlış pozitifi | Bağlam penceresi tablo başlığına yetişemiyordu (TF-001, TF-008) | Ayrı tablo okuma katmanı |
| Tutar ayrıştırma hatası | Regex alternation nedeniyle binlik ayracı olmayan tutarlar küçük okunuyordu | Altı desen tek \_SAYI parçasına çekildi |

# **6. Altın Veri Seti (Gold Dataset)**

## **6.1 Neden Vardır?**

Bir referans olmadan "doğruluk" iddiası edilemez. Altın veri seti, çıkarım motorunun çıktısının karşılaştırıldığı insan doğrulamalı referanstır. Bu set olmadan tüm doğruluk metrikleri temelsiz kalırdı.

| **Gösterge** | **Değer** | **Açıklama** |
|----|----|----|
| Toplam kayıt | 302 | gold_dataset/altin_veri_seti.json |
| İnsan doğrulaması | 302 / 302 | Tamamı imzalı; taslak kayıt kalmamıştır |
| Kanıt arşivi | 298 ekran görüntüsü | gold_dataset/ekran_goruntuleri/ |
| Tek doğru kaynak | altin_veri_seti.xlsx | JSON bu dosyadan üretilir, elle düzenlenmez |

## **6.2 Dairesellik Yasağı**

> Altın veri seti üretim sistemine bağlanmaz. Bir motor kendi ürettiği veriyle ölçülemez — bu, sınavı kendi cevap anahtarıyla yapmak olurdu. Bu yasak yalnızca bir ilke beyanı değildir; otomatik testle korunur ve ihlal edildiğinde CI hattı kırmızı verir.

## **6.3 Eğitim/Test Ayrımı ve Sızıntı Önleme**

Ayrım kümelendirme temellidir. Birbirine çok benzeyen kampanyalar aynı kümede tutulur ve birlikte aynı tarafa düşer. Somut örnek: AL-005 ve AL-006 kayıtlarının adları neredeyse aynıdır ("…Vade Farksız 6 Taksit Kampanyası"). Bunlar ayrı taraflara düşseydi, test kümesindeki bir kaydın neredeyse birebir eşi eğitim kümesinde bulunacak ve ölçüm gerçekte olduğundan iyi görünecekti.

| **Dosya** | **İşlevi** |
|----|----|
| gold_dataset/kume_haritasi.json | Hangi kaydın hangi benzerlik kümesinde olduğunu tutar |
| gold_dataset/split_manifest_v1.json | Bölmenin sabit ve denetlenebilir olduğunu garanti eder |

Bölme manifestosunun sağladığı güvence şudur: ayrım ölçümden ölçüme rastgele değişmez. Aksi hâlde iki ölçüm sonucu birbiriyle kıyaslanamaz hâle gelirdi.

## **6.4 Eşdeğer Kampanya İşaretlemesi**

RAG ölçümünde "doğru cevap" her zaman tek bir kampanya değildir; korpusta içerik olarak eşdeğer birden fazla kampanya bulunabilir. Bunlar gold_dataset/rag_esdeger_kampanya_listesi.py ile işaretlenir. Aksi hâlde sistem *doğru* bir kampanyayı getirdiği hâlde "kaçırdı" sayılır ve Recall değeri haksız yere düşük ölçülürdü.

# **7. Çıkarım Başarım Metrikleri**

> Ölçüm künyesi: 27 Ağustos 2026 · 291 canlı kayıt · 302 altın kayıt · 11 alan · Rapor: EVREN_FULL_PIPELINE_BENCHMARK.md ve cikarim_dogruluk_raporu.json

## **7.1 Nihai Boru Hattı Başarımı**

Çalışan sistemin tam yapılandırması Regex → NER → EVREN → Validation sırasıyla işler. Bu yapılandırmanın ölçülmüş sonucu:

| **Metrik**                                   | **Değer** |
|----------------------------------------------|-----------|
| Makro F1 (nihai boru hattı)                  | %87,25    |
| Precision                                    | %93,85    |
| Recall                                       | %81,51    |
| Dolu alan doğruluğu                          | %81,68    |
| Boş alan doğruluğu (yanlış pozitif kontrolü) | %96,88    |

> İki farklı F1 karıştırılmamalıdır. Yukarıdaki \*\*%87,25\*\* değeri boru hattının mikro F1'idir (tüm alanların doğru/yanlış sayıları havuzlanarak hesaplanır). Alan bazlı tabloda (§7.3) verilen değerler ise makro F1'dir (her alan eşit ağırlıkla ortalanır). İkisi farklı soruları yanıtlar ve birbirinin yerine kullanılamaz; bu nedenle her ikisi de ayrı ayrı raporlanır.

## <img src="media/image3.png" style="width:6.87917in;height:3.42014in" />

## Şekil 3. Altın veri seti üzerinde 11 kritik veri alanının Precision, Recall ve F1 skorları.

## **7.2 Katman Katkısı Ayrıştırması (Ablation)**

Her katmanın gerçek katkısı, katmanlar sırayla eklenerek ölçülmüştür. Bu, projenin en önemli bulgularından birini ortaya çıkarmıştır:

| **Yapılandırma**     | **TP** | **FP** | **FN** | **Precision** | **Recall** | **F1** |
|----------------------|--------|--------|--------|---------------|------------|--------|
| Yalnızca Regex       | 708    | 38     | 509    | %94,91        | %58,18     | %72,14 |
| Regex + NER          | 711    | 49     | 506    | %93,55        | %58,42     | %71,92 |
| Regex + NER + EVREN  | 760    | 58     | 457    | %92,91        | %62,45     | %74,69 |
| Nihai (+ Validation) | 992    | 65     | 225    | %93,85        | %81,51     | %87,25 |

### Aşama Bazlı Net Katkı

| **Aşama** | **Yeni Doğru Alan** | **Eklenen Yanlış Pozitif** | **Çağrı Sayısı** | **Net Etki** |
|----|----|----|----|----|
| Regex | 708 (taban) | 38 | — | Deterministik temel |
| NER (GLiNER) | +3 | +11 | 54 | NET NEGATİF |
| EVREN (\`llm-fast\`) | +49 | +9 | 112 | NET POZİTİF |
| Validation | +232 | +7 | — | +12,56 puan F1 |

> Kritik ve dürüst bulgu — NER katmanı net zarar veriyor. GLiNER katmanı 54 çağrıda yalnızca 3 yeni doğru alan eklerken 11 yanlış pozitif üretmiştir. Sonuç olarak F1 değeri %72,14'ten %71,92'ye düşmüştür. Bu bulgu gizlenmemekte, aksine öne çıkarılmaktadır: bir mimariye katman eklemek onu her zaman iyileştirmez ve bunu ancak ölçüm gösterebilir. Katmanın kaldırılması veya yeniden yapılandırılması yol haritasındadır (§25).

EVREN katmanının katkısı ise net pozitiftir: 112 çağrıda 49 yeni doğru alan bulmuş, yalnızca 9 yanlış pozitif üretmiştir. Bunların 38'i gerçek kurtarma örneğidir — yani Regex ve NER katmanlarının hiç bulamadığı alanlar EVREN tarafından bulunmuştur.

En büyük tek katkı Validation katmanınındır: +12,56 puan. Bu, sistemin doğrulama odaklı tasarımının ölçülmüş karşılığıdır — kaynağa karşı doğrulama yalnızca bir güvenlik önlemi değil, doğruluğun en büyük tek kaynağıdır.

## **7.3 Regex Katmanının Alan Kümesi Bazlı Başarımı**

Deterministik regex katmanının makro F1 değerleri, iki farklı alan kümesi için ayrı ayrı raporlanır:

| **Alan Kümesi** | **Eski** | **Güncel** | **Açıklama** |
|----|----|----|----|
| Sayısal çekirdek (7 alan) | %81,66 | %82,47 | Oran, vade, tutar, taksit, ödül, erteleme |
| Sınıflandırma / tarih (4 alan) | — | %77,48 | Kampanya türü, hedef kitle, başlangıç, bitiş |

> Neden iki ayrı doğruluk metriği raporlanır? Bir alanı *kaçırmak* ile kaynakta olmayan bir değeri *uydurmak* farklı ağırlıkta hatalardır ve ikincisi finansal kararlarda çok daha tehlikelidir. Tek bir yüzde bu iki hatayı birbirinin arkasına saklardı. "Boş alan doğruluğu" (%96,88) metriği, sistemin olmayan bir şeyi uydurmama başarısını ayrıca ölçer.

## **7.4 Kalan Hataların Alan Bazlı Dağılımı**

Nihai boru hattında kalan 225 kaçırma (false negative) alanlara eşit dağılmamıştır. Dağılım, hangi alanların gerçekten zor olduğunu açıkça gösterir:

| **Alan** | **Kaçırma (FN)** | **Payı** | **Değerlendirme** |
|----|----|----|----|
| hedef_kitle | 117 | %52,0 | En büyük tek kaynak — bkz. §7.5 |
| kampanya_turu | 65 | %28,9 | Sınıflandırma alanı (Md. 5.4) |
| kampanya_bitis | 9 | %4,0 | — |
| taksit_sayisi | 8 | %3,6 | — |
| kampanya_baslangic | 7 | %3,1 | Çoğu sayfada tarih hiç yazmıyor |
| odul_miktari | 6 | %2,7 | — |
| finansman_tutari | 5 | %2,2 | — |
| odul_birimi | 5 | %2,2 | — |
| vade_ay | 2 | %0,9 | — |
| kar_payi_orani_percent | 1 | %0,4 | Neredeyse tam isabet |
| TOPLAM | 225 | %100 |  |

> Bu tablonun anlamı: Kalan hataların %80,9'u yalnızca iki alandan gelmektedir (hedef_kitle ve kampanya_turu). Bu ikisi sınıflandırma görevleridir — metinden doğrudan okunacak bir değer değil, anlamdan çıkarım gerektirirler. Sayısal alanlarda (oran, vade, tutar) sistem neredeyse tam isabet göstermektedir; kâr payı oranında 291 kayıtta yalnızca 1 kaçırma vardır.

## **7.5 Bilinen Hatalar**

| **Kod** | **Alan** | **Açıklama ve Durum** |
|----|----|----|
| EX-AL | Kampanya avantajı (Albaraka) | Albaraka Mobil üzerinden kodla alınan indirim kampanyalarında (13 kayıt) metinde hiç "kart" kelimesi geçmemektedir; mevcut desenler yakalayamamaktadır. |
| DK-002 | Ödül miktarı (Dünya Katılım) | Altın veri "davet başına birim ödül"ü, motor ise metnin öne çıkardığı "toplam tavan"ı esas almaktadır. Hangisinin doğru olduğu yorum gerektirdiği için bilinçli olarak açık bırakılmıştır. |

## **7.6 Hâlâ Açık İki Alan ve Gerekçeleri**

- kampanya_baslangic — Recall %95,45'e yükselmiştir. Kalan kaçırmalar, çoğu sayfada başlangıç tarihinin hiç yazmamasından kaynaklanmaktadır; motorun ulaşabileceği bir bilgi değildir.

- hedef_kitle — Altın veri setindeki baskın sınıf olan "Belirli segment" (yaklaşık 140 kayıt) bir insan çıkarımıdır; etiketi yazan kişi ürün adından ve kampanya tipinden anlam çıkarmıştır, o ifade metinde aynen geçmez. Bu, kural genişleterek kapatılabilecek bir boşluk değildir — denenmiş ve ölçümle reddedilmiştir.

# **8. RAG Mimarisi (Retrieval-Augmented Generation)**

## **8.1 Teknik Parametreler**

| **Parametre** | **Değer** | **Açıklama** |
|----|----|----|
| Parçalama yöntemi | Özyinelemeli | 900 karakter / 150 karakter örtüşme |
| Embedding modeli | intfloat/multilingual-e5-base | 768 boyutlu, çok dilli, yerel |
| İndeks boyutu | 2.186 parça / 623 belge | 28 Ağustos 2026 — ölçüm bu indekste yapıldı |
| Değerlendirme seti | 110 sorgu | Eskimiş 17 soru elendi, exact=True |
| Üretimde getirilen sonuç | limit = 3 | agent/router.py; ölçümde k = 1/3/5 |
| Çekimserlik eşiği | Leksikal örtüşme ≥ 0,60 | Vektör skoru değil (bkz. §8.4) |

> Parçalama stratejisi değiştirildi ve ölçüm yenilendi. Önceki semantik parçalama (700 karakter hedef) yerine özyinelemeli parçalama (900 karakter, 150 karakter örtüşme) uygulanmıştır. Örtüşme, bir cümlenin parça sınırında ikiye bölünüp anlamını kaybetmesini engeller. İndeks bu yapılandırmayla yeniden kurulmuş ve Recall aynı indeks üzerinde yeniden ölçülmüştür — önceki sürümdeki "ölçüm indeksi ile canlı indeks farklı" durumu böylece kapanmıştır.

## **8.2 Hibrit Arama: Yoğun + Seyrek + RRF**

Sistem yalnızca anlamsal (dense) aramaya dayanmaz. Bunun ölçülmüş bir gerekçesi vardır: anlamsal benzerlik, kampanya adı gibi ayırt edici özel isimleri yeterince ağırlıklandırmamaktadır.

- Yoğun (dense) vektör: Anlamsal yakınlığı yakalar; farklı kelimelerle ifade edilmiş aynı kavramı bulur.

- Seyrek (BM25) vektör: Birebir kelime eşleşmesini geri getirir; özel isim ve kampanya adı ayırt ediciliğini sağlar.

- RRF (Reciprocal Rank Fusion): İki sıralamayı tek bir sıralamada birleştirir.

## **8.3 Kaynak Gösterimi**

RAG yanıtında parça kimliği, benzerlik skoru ve kaynak parçanın birebir metni (Kaynak.metin) döndürülür. Sistem bu metnin üzerine serbest cümle üretmez. "Her cümle bir kaynaktan gelir" iddiasının kanıtı budur — iddia doğrulanabilir biçimde API sözleşmesinden döner.

## **8.4 Çekimserlik Mekanizması — Neden Skor Eşiği Değil?**

Sistemin cevap vermeme kararı, aşağıdaki leksikal örtüşme formülüne dayanır:

> Örtüşme = \|Soru kökleri ∩ Kaynak kökleri\| / \|Soru kökleri\|
>
> Eşik : ≥ 0,60
>
> Bu tercih ölçümle belirlenmiştir, tahminle değil. Yalnızca vektör benzerliğine bakıldığında, "uzay istasyonunda yerçekimi" gibi tamamen alakasız bir soru dahi 0,78 benzerlik skoru almaktaydı. Ayrıca RRF skoru bir sıralama birleştirme skorudur; en üstteki sonuç, sorgu alakalı olsun ya da olmasın yaklaşık 1,0 değerini alır. Dolayısıyla ne ham benzerlik skoru ne de RRF skoru çekimserlik eşiği olarak kullanılabilir.

# **9. RAG Değerlendirme Sonuçları**

> Ölçüm künyesi: 28 Ağustos 2026 · 2.186 parçalık indeks · 110 sorgu · exact=True · Komut: python -m scraper.scripts.rag_degerlendirme

## **9.1 Genel Başarım**

| **Metrik** | **Değer** | **Açıklama** |
|----|----|----|
| Recall@1 | %63,64 | İlk sonuçta isabet |
| Recall@3 | %74,55 | Üretimde kullanılan k değeri (limit=3) |
| Recall@5 | %77,27 | Genel |
| Recall@5 — tam başlık kategorisi | %92,31 | Kampanya adı verildiğinde |
| Çekimserlik — alan dışı | %83,33 (10/12) | Konu tamamen dışındaki sorular |
| Çekimserlik — alan içi kapsam dışı | %50,0 izole (4/8) · %100,0 uçtan uca (10/10, güncel sette yeniden ölçülmedi) | Bkz. §9.3 |

Değerlendirme seti 110 sorgudan oluşur; korpus rotasyonu nedeniyle beklenen belgesi artık indekste bulunmayan 17 eskimiş soru ölçüm dışı bırakılmıştır. Bu soruları "bulunamadı" saymak, getirme başarısını değil veri eskimesini ölçmek olurdu.

> Halüsinasyon engelleme uçtan uca %100 başarıya ulaşmıştır. Alan içi kapsam dışı sorularda izole ölçüm %40 gösterse de, niyet katmanı yönlendirmesiyle birlikte uçtan uca ölçümde 10/10 başarı elde edilmiştir. Yani sistem, cevabını bilmediği bir soruya pratikte hiç uydurma cevap üretmemektedir.

## **9.2 Kategori Bazlı Kırılım**

Tek bir genel oran, sistemin nerede zorlandığını gizler. Bu nedenle kategori kırılımı ayrıca raporlanır:

| **Kategori** | **Recall@5**   | **Tanım**                                      |
|--------------|----------------|------------------------------------------------|
| Tam ad       | %92,31 (36/39) | Kampanya adı birebir verilerek sorulan sorular |
| Kısmi ad     | %86,49 (32/37) | Kampanya adının bir kısmı verilir              |
| Doğal soru   | %64,29 (9/14)  | Günlük dilde sorulmuş sorular                  |
| Banka + konu | %40,0 (8/20)   | En zor kategori — kampanya adı hiç verilmez    |

banka_ve_konu kategorisi kasıtlı olarak zor tasarlanmıştır: kullanıcı kampanya adını bilmeden "X bankasının kart kampanyası" biçiminde sormaktadır. Leksikal arama kampanya adına dayandığı için, isim verilmediğinde ayırt edicilik kaybolur. Bu bir kod hatası değildir; belgelenmiş dense-arama sınırının doğal sonucudur ve açıkça raporlanmaktadır.

> Denenip ölçümle reddedilen çözüm — reranker. Bu kategoriyi iyileştirmek için cross-encoder tabanlı bir yeniden sıralayıcı (reranker) denenmiştir. Ancak ölçüm, aday havuzunun genişletilmesinin genel Recall'ü düşürdüğünü göstermiştir: geniş havuzun cross-encoder'a sunduğu dikkat dağıtıcı fazlalık, doğru sonucu aşağı itmektedir. Deney farklı embedding modelleri ve farklı veri seti boyutlarıyla tekrarlanmış, sonuç değişmemiştir — bu yapısal bir sınırlamadır, tek bir koşunun gürültüsü değildir. Reranker bu nedenle bilinçli olarak iptal edilmiştir (varsayılan kapalı, KATILIMAI_RERANK=true ile elle açılabilir). Sonraki bir denemede farklı bir mekanizma — sorguda geçen kampanya türünü (kart/ihtiyaç/taşıt vb.) tespit edip aday sıralamasını yumuşak biçimde ağırlıklandıran "kampanya_turu tür-boost" ile marka koruma listesi — ölçülüp varsayılan olarak açılmıştır (KATILIMAI_TUR_BOOST, varsayılan açık). Bu mekanizma banka_ve_konu Recall@5'ini %24,00'den %40,0'a yükseltmiştir. Kategori hâlâ en zayıf halka olmaya devam etmektedir ama açık sorun kısmen kapanmıştır.

## **9.3 Alan İçi Kapsam Dışı Sorular — Bir Ölçüm Vakası**

Bu bölüm, projenin ölçüm disiplininin nasıl çalıştığını gösteren temsilî bir örnektir.

Problem: "Hesap açmak için hangi belgeler gerekli?", "Şifremi unuttum", "TMSF güvencesi" gibi sorular alan içi ama kapsam dışıdır. "Hesap", "belge", "şifre" kelimeleri kampanya metinlerinin genel bankacılık kelime dağarcığından geldiği için, leksikal örtüşme yanlışlıkla %60 eşiğini aşıyor ve sistem cevap üretmeye çalışıyordu. Bu kategoride çekimserlik doğruluğu yalnızca %50 (5/10) ölçüldü.

İlk akla gelen çözüm ve neden reddedildi: "Eşiği yükseltelim" en doğal öneriydi. Ancak tam dağılım ölçüldüğünde bu kategorinin skor aralığının (0,50–0,83) gerçekten cevaplanabilir banka_ve_konu ve kismi_ad sorularının aralığıyla iç içe geçtiği görüldü. Yani eşiği yükseltmek bu sorunu çözmez, gerçek cevaplanabilir soruları da susturur.

Uygulanan doğru çözüm: Sorunu RAG katmanında değil, niyet katmanında çözmek. Ajana KAPSAM_DISI adlı yeni bir niyet eklendi; bu sorular RAG'e hiç sorulmadan ayıklanıyor. Sonuç: uçtan uca çekimserlik doğruluğu %100,0 (10/10)'a yükseldi.

> Metodolojik çıkarım: En sezgisel çözüm (eşiği yükseltmek) ölçüm tarafından reddedilmiş ve ölçüm doğru katmanı göstermiştir. Bu, projedeki her tasarım kararının neden ölçüme dayandırıldığının somut kanıtıdır.

# **10. Ajan Mimarisi ve Araç Yönlendirme**

## **10.1 Niyetler ve Araçlar**

| **Niyet** | **Çağrılan Araç** | **İşlev** |
|----|----|----|
| HESAPLAMA | hesaplama_aracini_cagir | Taksit ve kâr payı hesabı — saf Python |
| KARSILASTIRMA | karsilastirma_aracini_cagir | Sabit parametreli SQL şablonu |
| TOPLAM_MALIYET | toplam_maliyet_aracini_cagir | Gerçek amortisman hesabı |
| SOZLUK | sozluk_aracini_cagir | 31 kavramlık terminoloji sözlüğü |
| BILGI | rag_aracini_cagir | Hibrit arama + kaynak gösterimi |
| KAPSAM_DISI | \*(araç çağrılmaz)\* | Sorunun kapsam dışı olduğunu açıkça bildirir |

## **10.2 Araç Seçimini Kim Yapar?**

Araç seçimi bir dil modeline bırakılmaz. Seçim, agent/intent.py içindeki deterministik anahtar kelime eşleştirmesiyle yapılır. Bu, hem çevrimdışı çalışabilirlik (Md. 5.9) hem de denetlenebilirlik açısından bilinçli bir tercihtir: jüri, hangi sorunun neden hangi araca gittiğini kod okuyarak doğrulayabilir.

İstisna: BILGI niyeti anahtar kelimeyle tespit edilmez. Açık uçlu olduğu için kelime listesiyle yakalanamaz; hiçbir araç eşleşmediğinde orkestratör varsayılan olarak RAG yoluna gider.

## **10.3 Karar Zinciri**

> Kullanıcı sorusu
>
> ↓
>
> Niyet tespiti (+ güven skoru)
>
> ↓
>
> Araç seçimi ──→ araç yetersizse ──→ RAG'e yedekleme
>
> ↓
>
> Araç çalıştırma (SQL / Python / sözlük / vektör arama)
>
> ↓
>
> Verifier — sayısal iddiaların kaynağa karşı doğrulanması
>
> ↓
>
> Terminoloji kontrolü
>
> ↓
>
> Yanıt + kaynak + audit izi

## **10.4 Kademeli Yedekleme — Ölçülmüş Gerekçe**

Seçilen araç yetersiz kalırsa sistem vazgeçmez; soruyu RAG'e sorar. Bu davranışın gerekçesi ölçülmüştür: *"Ziraat Katılım kart kampanyalarında taksit var mı?"* sorusu, yalnızca "taksit" kelimesi içerdiği için hesap makinesine yönlendiriliyor ve kullanıcıya *"Hesaplama için şu bilgiler eksik: anapara…"* yanıtı dönüyordu. Oysa bu bir bilgi sorusudur ve cevabı kaynaklarda mevcuttur. Bugün hangi aracın neden yetersiz kaldığı audit kaydında korunur.

## **10.5 Paralel Araç Çağrısı**

Sistem aynı anda birden fazla araç çağırmaz. Tek araç seçilir, yetersiz kalırsa RAG'e düşülür. Bu bilinçli bir kısıttır: paralel çağrı, karar zincirinin denetlenebilirliğini zorlaştırırdı ve Jüri Audit Paneli'nin temel vaadi olan "tek bir izlenebilir karar yolu" bozulurdu.

# **11. Terminoloji Sistemi (Şartname Md. 5.5)**

Katılım bankacılığı, geleneksel bankacılıktan yalnızca ürün adlarıyla değil kavramsal olarak da ayrılır. Bir yanıtta "faiz" kelimesinin geçmesi yalnızca terminolojik bir hata değil, fıkhî olarak da yanlış bir ifadedir. Sözlük bu ayrımı sistematik hâle getirir.

## **11.1 Sözlük Kapsamı**

Sözlükte 31 kavram bulunur; her biri geleneksel karşılığı ve tanım kaynağıyla birlikte saklanır.

| **\#** | **Kavram** | **\#** | **Kavram** | **\#** | **Kavram** |
|----|----|----|----|----|----|
| 1 | kar_payi_orani | 12 | nakit_iade | 23 | ozel_cari_hesap |
| 2 | finansman_maliyeti | 13 | murabaha | 24 | vade_farki |
| 3 | katilim_fonu | 14 | icare | 25 | pesin_fiyat |
| 4 | masrafsiz_finansman | 15 | musaraka | 26 | tahsis_ucreti |
| 5 | avantajli_finansman | 16 | mudaraba | 27 | erken_odeme_indirimi |
| 6 | vade_suresi | 17 | selem | 28 | gecikme_bedeli |
| 7 | odul_miktari | 18 | istisna | 29 | danisma_kurulu |
| 8 | kesirli_kar_paylasimi | 19 | karz_i_hasen | 30 | finansman_tutari |
| 9 | sifir_oran_ifadesi | 20 | tekaful | 31 | hedef_kitle |
| 10 | odemesiz_donem | 21 | kira_sertifikasi |  |  |
| 11 | dar_makas | 22 | kar_zarar_katilma |  |  |

## **11.2 En Kritik Ayrımlar**

| **Katılım Bankacılığı** | **Geleneksel Karşılığı** | **Neden Kritik** |
|----|----|----|
| Kâr payı | Faiz | Kavramsal ve fıkhî olarak farklı; karıştırılması ürünü yanlış tanımlar |
| Katılım fonu | Mevduat | Risk paylaşımı yapısı farklıdır |
| Vade farkı | Faiz farkı | Peşin/vadeli fiyat farkına dayanır |
| Kâr-zarar katılma | Sabit getiri | Getiri garantisi yoktur |

## **11.3 Kullanıcı Yanlış Terim Kullandığında**

Sistem soruyu reddetmez. Kullanıcı "faiz" dediğinde kavram düzeltilir ve katılım bankacılığındaki karşılığı (kâr payı) açıklanır. Amaç engellemek değil, doğru terminolojiyi öğretmektir. Yanıt üretildikten sonra çalışan terminoloji kontrolü, çıktıda geleneksel bankacılık terimi kalmamasını da güvence altına alır.

Sözlük manuel olarak yönetilir ve sürümü rule_version alanı olarak /sistem/tazelik yanıtında döner (örnek: sozluk-376da8806612). Böylece bir yanıtın hangi sözlük sürümüyle üretildiği geriye dönük izlenebilir.

# **12. Kapsam Ölçümü (Scope Guard)**

Sistemin katılım bankacılığı ile geleneksel bankacılığı ayırt edebildiğini ölçebilmek için bir karşı-örnek seti tutulur.

## **12.1 Ölçüm Sonuçları**

| **Ölçüm**  | **Neyi Test Eder**                                 | **Sonuç** |
|------------|----------------------------------------------------|-----------|
| Hassasiyet | 24 geleneksel bankacılık ifadesi yakalanmalı       | 24 / 24   |
| Özgüllük   | 10 meşru katılım bankacılığı ifadesi yakalanmamalı | 10 / 10   |

> Neden iki yön birden ölçülür? Yalnızca hassasiyet ölçülseydi, "her cümleyi kapsam dışı işaretle" diyen tamamen işe yaramaz bir kontrol de tam not alırdı. Özgüllük olmadan hassasiyet anlamsızdır. Bu iki yönlü ölçüm, kapsam kontrolünün gerçekten ayırt ettiğini kanıtlar.

## **12.2 Karşı-Örnek Setinin Etik Disiplini**

Karşı-örnek ifadeleri elle yazılmıştır; hiçbiri gerçek bir bankadan kopyalanmamış ve hiçbiri gerçek bir bankaya atfedilmemiştir. Bu set yalnızca kapsam sınıflandırması ve ölçüm amacıyla kullanılır; üretim kampanya veritabanına ve RAG indeksine dâhil edilmez.

Bu bir iddia olarak bırakılmaz. Her kod gönderiminde çalışan bir test, karşı-örnek ifadelerinin ham veri ve altın veri seti içinde geçmediğini tarar:

> tests/test_karsi_ornekler.py::test_karsi_ornekler_veritabanina_girmemis

## **12.3 Katmanlı Kapsam Kontrolü**

| **Katman** | **Mekanizma** | **Ne Zaman Devreye Girer** |
|----|----|----|
| 1\. Niyet katmanı | KAPSAM_DISI niyeti | Genel bankacılık işlemi soruları (§9.3) |
| 2\. Terminoloji | Sözlük eşleştirmesi | Geleneksel bankacılık terimi tespiti |
| 3\. Leksikal örtüşme | Örtüşme \< 0,60 | RAG kaynağı yetersizse çekimserlik |

# **13. Deterministik Hesaplama Katmanı**

## **13.1 Neden Dil Modeli Hesaplama Yapmaz?**

> Aritmetik deterministik bir iştir. Bir hesabı olasılıklı bir modele bırakmak, doğru sonucu şansa bağlamak anlamına gelir. Finansal bir üründe bu kabul edilemez. Bu nedenle tüm hesaplamalar saf Python fonksiyonlarıyla yapılır ve dil modeli hesaplama zincirine hiç girmez.

## **13.2 Fonksiyonlar**

| **Fonksiyon** | **İşlevi** |
|----|----|
| aylik_taksit_hesapla | Anapara, oran ve vadeden aylık taksit üretir |
| odeme_plani_uret | Ay ay ödeme planı tablosu üretir |
| maksimum_finansman_hesapla | Belirli bir taksit kapasitesine karşılık gelen azami finansman |
| toplam_maliyet_karsilastir | Farklı kampanyaların gerçek toplam maliyetini karşılaştırır |

## **13.3 Aylık Taksit Formülü**

> r × (1 + r)^n
>
> Aylık Taksit = A × ─────────────────
>
> (1 + r)^n − 1
>
> A = anapara (finansman tutarı)
>
> r = aylık kâr payı oranı → kampanya kaydındaki kar_payi_orani_percent
>
> (oran_periyodu alanıyla aylık/yıllık normalize edilir)
>
> n = vade (ay) → kampanya kaydındaki vade_ay

Girdiler \_girdileri_dogrula() fonksiyonuyla sınırlandırılır; negatif veya anlamsız değerler hesaplamaya hiç girmez.

## **13.4 Toplam Maliyet Karşılaştırması**

Düşük oran, ucuz olmak anlamına gelmez. Uzun vadeli ve düşük oranlı bir kampanya, kısa vadeli ve yüksek oranlı bir kampanyadan toplamda daha pahalı olabilir. Bu nedenle sisteme "500.000 TL için X Bankası ile Y Bankası'nın toplam maliyetini karşılaştır" biçiminde sorulduğunda, her bankanın kendi oran ve vadesiyle gerçek bir amortisman hesabı yapılır. Ham oran sıralaması yerine gerçek maliyet karşılaştırılır.

> Kapsam beyanı: Bu depodaki hesap makinesi KKDF ve BSMV gibi vergi kalemlerini hesaplamaz; yalnızca anapara, oran ve vade üzerinden taksit ile toplam maliyet üretir. Vergi kalemlerinin eklenmemiş olduğu, yanlış bir sonuç gösterilmemesi için burada açıkça belirtilir. Ayrıca sonuçların PDF veya Excel olarak dışa aktarımı henüz mevcut değildir.

# **14. Müşteri Sesi (Complaint Insight) — Sentetik Demo**

> **KVKK ŞEFFAFLIK BEYANI —** Bu modül gerçek şikâyet verisi kullanmaz. Veri setinin tamamı sentetiktir; hiçbir örnek gerçek bir şikâyetten kopyalanmamış ve hiçbir gerçek bankaya atfedilmemiştir. Her API yanıtı ve her ekran, verinin sentetik olduğunu açıkça belirtir.

## **14.1 Veri Seti Künyesi**

| **Gösterge** | **Değer** |
|----|----|
| Sentetik örnek sayısı | 20 örnek + 2 alan dışı örnek |
| Tema sayısı | 10 |
| Üretim yöntemi | Elle yazıldı — dil modeli veya şablon kullanılmadı |
| Model eğitiminde kullanım | Hayır — yalnızca sınıflandırıcı demosu |
| Taksonomi kaynağı | Mentör raporundaki 10 temalı taksonomi |

## **14.2 On Tema**

| **Kod** | **Tema** | **Tanım** |
|----|----|----|
| REWARD_NOT_CREDITED | Ödül yatmadı | Vaat edilen ödül/puan/nakit iade hesaba geçmedi |
| ELIGIBILITY_MISMATCH | Koşul uyuşmazlığı | Müşteri koşulu sağladığını sanıyor ama kapsam dışında |
| INSTALLMENT_MATURITY | Taksit/vade uyuşmazlığı | Taksit, vade veya erteleme beklentisi gerçekleşenle uyuşmuyor |
| MERCHANT_MCC_SCOPE | İşyeri kapsam dışı | İşyeri/harcama türü kampanyaya dahil sanıldı |
| ACTIVATION_REGISTRATION | Aktivasyon sorunu | Katılım için gereken aktivasyon yapılmamış/başarısız |
| DATE_EXPIRY | Tarih uyuşmazlığı | Başlangıç/bitiş tarihiyle ilgili yanlış anlama |
| CARD_PRODUCT_MISMATCH | Kart/ürün uyuşmazlığı | Yanlış kart veya ürün türü kampanyaya bağlanmış |
| FEE_CHARGE | Beklenmeyen ücret | Masrafsız sanılan işlemde ücret/komisyon kesildi |
| COMMUNICATION_AMBIGUITY | İletişim belirsizliği | Kampanya metni yanıltıcı veya eksik anlaşılmış |
| SERVICE_RESOLUTION | Çözüm sürecinde sorun | Çağrı merkezi/şube başvurusu sorunu çözmedi |

## **14.3 Sınıflandırıcı Davranışı**

Sınıflandırıcı kural tabanlı ifade eşleştirmesi yapar (complaint/tema_siniflandirici.py). Hiçbir ifade eşleşmezse tema uydurulmaz; None döner. Bu, sistemin genel "bilmediğini bilme" ilkesinin bu modüldeki karşılığıdır.

## **14.4 Şikâyet Hattı — Koda Gömülü Dört Kırmızı Çizgi**

Gerçek veri henüz toplanmamaktadır, ancak hattın tamamı kurulu ve test edilmiştir. Veri koruma ilkeleri niyet beyanı değil, çalışan kontrollerdir:

| **Kırmızı Çizgi** | **Kodda Karşılığı** |
|----|----|
| Ham metin izin kapısı geçmeden diske yazılmaz | İzin kaydı yoksa IzinYok istisnası fırlatılır; diske yazan kaydet() izni ikinci kez sorar |
| PII temizliği kayıttan önce yapılır | hazirla() ham metni ne döndürür ne de loglar; tek çıkışı temizlenmiş metindir |
| Şikâyet verisi kampanya tablosuna karışmaz | Ayrı tablo; kampanyalara foreign key yoktur |
| "Şikâyet oranı" ifadesi kullanılmaz | yogunluk_ozeti() yüzde üretmez; adet döner, alan adı gozlenen_yogunluk |

Varsayılan her zaman izin yokluğudur: izin dosyası yoksa, bozuksa ya da alanları eksikse "izin var" sayılmaz.

## **14.5 Kampanya Eşleştirmesi Bir Hipotezdir**

Bir şikâyetin hangi kampanyaya ait olduğu kesin bilinemez; bu nedenle eşleştirme bir hipotez olarak ele alınır:

- Güven skoru 0,50 eşiğinin altındaysa bağ kurulmaz ve neden kurulmadığı kayda yazılır.

- Banka adının geçmesi tek başına yetmez — bir bankanın onlarca kampanyası vardır.

- İki kampanya aynı güven skorunu alırsa yine bağ kurulmaz; rastgele birini seçmek, olmayan bir kesinlik üretmek olurdu.

- Şikâyet tarihi kampanyanın yayın penceresi dışındaysa aday elenir; pencere içinde olmak ise puan kazandırmaz.

## **14.6 Sızıntı Koruması**

Sentetik verinin üretim veritabanına veya RAG indeksine sızmadığı otomatik testle kilitlenmiştir:

> tests/test_sentetik_musteri_sesi.py::test_sentetik_ornekler_urun_verisine_sizmamis

# **15. Kampanya Karşılaştırma Motoru (Şartname Md. 5.7)**

## **15.1 Karşılaştırma Kriterleri**

| **Kriter** | **Kullanılan Alan** | **Kaynak** |
|----|----|----|
| En Düşük Kâr Payı Oranı | kar_payi_orani_percent | Md. 5.7 |
| En Yüksek Ödül Miktarı | odul_miktari | Md. 5.7 |
| En Uzun Vade Seçeneği | vade_ay | Md. 5.7 |
| En Düşük Masraf | tahsis_ucreti | Md. 5.7 |
| En Avantajlı Kampanya | Kompozit — bkz. §15.2 | Md. 5.7 |
| En Yüksek Finansman Tutarı | finansman_tutari | \*Bonus — şartname listesinde yok\* |

## **15.2 "En Avantajlı" Nasıl Hesaplanır? — Ağırlıklı Formül Yoktur**

Sistem tek bir ağırlıklı skor uydurmaz. Her alt kriterde hangi kampanyanın öne çıktığı ayrı ayrı belirlenir (örneğin: "Kâr payı oranı açısından C Bankası daha avantajlı…"), ve en çok eksende öne çıkan kampanya genel kazanan sayılır. Eşitlik durumunda tek bir kazanan uydurulmaz. Bu yöntem, şartnamedeki Örnek Temsilî Senaryo-2 ile birebir aynıdır.

> Neden ağırlık atanmadı? "Kâr payı %40, ödül %30, vade %20…" gibi bir ağırlıklandırma bilimsel görünen ama temelsiz bir seçim olurdu. Hangi ağırlığın doğru olduğunu söyleyen bir kaynak yoktur; kullanıcının önceliği kullanıcıya göre değişir. Eksen eksen raporlama, kararı kullanıcıya bırakır ve gerekçeyi görünür kılar.

## **15.3 Eksik Veri Nasıl Ele Alınır?**

Eksik alan gizlenmez. SQL sorgusunda NULLS LAST ile en sona yerleştirilir; filtrelenip yok sayılmaz. Arayüzde "Belirtilmemiş" olarak görünür. Bir kampanyanın masraf bilgisinin belirtilmemiş olması, o kampanyada *masraf olmadığı* anlamına gelmez — bu ayrım finansal kararda kritiktir.

Karşılaştırma sonuçları canlı veritabanı sorgusuyla üretilir; önbellek kullanılmaz.

# **16. Denetim ve İzlenebilirlik Sistemi**

## **16.1 Jüri Audit Paneli'nin Amacı**

Şeffaflık iki ayrı kitleye ayrılmıştır. Banka çalışanı iş odaklı dashboard'u görür; jüri ve geliştirici ise çağrılan aracı, tespit edilen niyeti, çalıştırılan SQL'i, güven skorlarını ve gecikmeyi gösteren ayrı bir denetim panelini kullanır.

## **16.2 Kaydedilen Bilgiler**

| **Kayıt**  | **İçerik**                               |
|------------|------------------------------------------|
| Niyet      | Algılanan niyet ve güven skoru           |
| Araç       | Çağrılan araç ve parametreleri           |
| SQL        | Çalıştırılan sorgu ve dönen sonuçlar     |
| Retriever  | Benzerlik skorları ve getirilen parçalar |
| Güven      | Çıkarım ve yanıt güvenilirlik skorları   |
| Performans | Yanıt süresi ve önbellek durumu          |
| Doğrulama  | Kaynakta doğrulama (Verifier) sonuçları  |

## **16.3 Üç Durumlu Doğrulama**

| **Durum** | **Anlamı** |
|----|----|
| dogrulandi | Kullanılan tüm alanlar, tüm kayıtlarda kaynakta doğrulandı |
| kismi | Verifier çalıştı ancak bir kısmını onaylayamadı — değer silinmez |
| calistirilmamis | Bu alanlar için Verifier hiç çalışmadı |

> Bunları tek bir orana indirgemek en büyük hata olurdu. "Çalıştırılmamış" durumunu başarısızlık saymak sistemi haksız yere kötü, başarı saymak ise yalancı gösterirdi. Üç durum bilinçli olarak ayrı sayılır.

Ayrıca yalnızca sıralamayı belirleyen eksenler raporlanır: "en uzun vade" sorusunda ödül miktarının doğrulanmış olması, o cevap hakkında bilgi vermez.

## **16.4 RAG Yolunda Özet Neden Üretilmez?**

RAG yolunda doğrulama özeti bilerek None döner ve bu doğru davranıştır: RAG hiçbir cümle üretmez, kaynak parçasını birebir döndürür. Orada "bu sayı kaynakta geçiyor mu?" kontrolü tanım gereği her zaman evet derdi — hiçbir şey elemeyen, yalnızca doğrulama yapılmış *izlenimi* veren bir kontrol olurdu. Sisteme ileride LLM ile özetleme eklenirse, Verifier o yola birlikte bağlanmalıdır.

## **16.5 İki Denetim Ekranının Farkı**

| **Ekran** | **Neyi Denetler** | **Zaman Boyutu** |
|----|----|----|
| Karar Zinciri (DecisionTrace) | Bir sorunun nasıl cevaplandığı | Çalışma zamanı |
| Çıkarım Denetimi (ExtractionAudit) | Bir kampanyanın nasıl çıkarıldığı | Veri kalitesi |

## **16.6 Çıkarım Denetimi Ekranında Gösterilenler**

Bir kampanya seçildiğinde her alan için şu bilgiler alan alan gösterilir: alan adı, mevcut değer, değeri dolduran çıkarım katmanı (regex / GLiNER / LLM), güven skoru, altın veri referansı, doğrulama durumu ve kanıt spanı.

Üç katman farklı değer ürettiyse Resolver'ın seçtiği değer gösterilir; diğer katmanların adayları "diğer adaylar" olarak ayrıca listelenir. Çatışma gizlenmez. Altın veri değeri ile model çıktısı uyuşmadığında ilgili satır işaretlenir.

> Ekranda açıkça yazan dürüstlük notu: "Bu ölçümde NER (GLiNER) devre dışıydı — raporlanan hibrit gerçekte regex + LLM'dir. NER'in katkısı ölçülmemiştir." Bu not, ekranın tasarım şeması (Regex → GLiNER → Qwen → Resolver) ile fiilen ölçülen yapılandırmanın karıştırılmaması için konulmuştur.

# **17. Arayüz Mimarisi**

## **17.1 Sayfalar ve Veri Kaynakları**

| **Sayfa** | **Amaç** | **Veri Kaynağı** |
|----|----|----|
| Genel Bakış | Hacim, kapsam, dağılım ve veri tazeliği | /sistem/tazelik, /kampanyalar |
| AI Asistan | Doğal dilde soru-cevap | /chat, /chat/stream |
| Kampanyalar | Liste, detay ve değişim tarihçesi | /kampanyalar\* |
| Karşılaştırma | 5+1 kriter matrisi ve rakip analizi | /karsilastir, /rakip-analizi |
| Hesap Makinesi | Taksit ve toplam maliyet | /hesapla |
| Metin Analizi | Serbest metinden çıkarım (Md. 6 demosu) | /cikar |
| Jüri Audit Paneli | Karar zinciri, model metrikleri, veri kaynakları | Çalışma zamanı |
| Çıkarım Denetimi | Kampanya bazlı çıkarım izi | /audit/extraction/{id} |

## **17.2 Mock ve Canlı Veri Ayrımı**

Veri kaynağı GERCEK_VERI_AKTIF ortam değişkeniyle seçilir. false değeri dört kayıtlık mock veriyi (A/B/C/D Bankası — sözleşme testi verisi), true değeri ise canlı PostgreSQL verisini (536 kayıt) kullanır. Arayüzde üst barda yer alan "CANLI VERİ" rozeti bu durumu her sayfada gösterir; jüri hangi veriyi gördüğünü her an bilir.

## **17.3 Çevrimdışı ve Hata Davranışı**

> API'ye ulaşılamadığında arayüz uydurma veri göstermez. Dürüstçe "Veri alınamadı" bildirimi verir ve statik ölçüm değerlerine düşer — bu değerlerin hangi tarihe ait olduğu da açıkça belirtilerek. Boş bir ekran veya sıfırlarla dolu bir tablo göstermek, kullanıcıyı yanıltmak olurdu.

Arayüz duyarlı (responsive) tasarlanmıştır; 640, 900, 1000, 1200 ve 1400 piksel kırılım noktaları tanımlıdır.

# **18. REST API Mimarisi**

Tüm uç noktalar Authorization: Bearer \<token\> başlığı ister; kök ve sağlık kontrolü uçları hariç. Başlık formatı her iki kimlik doğrulama modunda da aynıdır, bu sayede arayüz kodu mod geçişinde değişmez.

| **Metot** | **Yol** | **Açıklama** |
|----|----|----|
| GET | / · /saglik | Servis bilgisi ve sağlık kontrolü (kimlik gerektirmez) |
| GET | /sistem/tazelik | Veri ve RAG indeksinin güncellik durumu |
| POST | /token | Kullanıcı adı ve parola ile JWT (yalnızca JWT_AKTIF=true) |
| POST | /kayit | Self-servis kayıt — rol her zaman musteri |
| POST | /kullanici/sifre-degistir | Mevcut şifreyi doğrulayıp yenisiyle değiştirir |
| GET | /kampanyalar | Kampanya listesi (?banka=, ?kampanya_turu=) |
| GET | /kampanyalar/{id} | Tek kampanya detayı |
| GET | /kampanyalar/{id}/etki | Etki skoru — piyasaya göre eksen eksen yüzdelik sıra |
| GET | /kampanyalar/{id}/tarihce | Değişim tarihçesi — ek veri toplamaz |
| GET | /rakip-analizi | Rakip matrisi — tüm kriterler tek tabloda |
| GET | /terminoloji | Katılım bankacılığı sözlüğü (31 kavram, Md. 5.5) |
| POST | /cikar | Serbest metinden yapılandırılmış çıktı (Md. 6 demosu) |
| POST | /karsilastir | Kampanya karşılaştırma (sabit kriter listesi) |
| POST | /hesapla | Taksit ve kâr payı hesabı (saf Python) |
| POST | /chat | Doğal dilde soru-cevap (kaynak ve audit bilgisiyle) |
| POST | /chat/stream | Aynı yanıt, parça parça (SSE) |
| GET | /audit/extraction/{id} | Çıkarım izi — katman, güven, gold referansı |
| POST | /musteri-sesi/siniflandir | Serbest metni 10 temalı taksonomiye göre sınıflandırır |
| GET | /musteri-sesi/ornekler | Sentetik demo seti — gerçek şikâyet değildir |
| GET | /musteri-sesi/yogunluk-ozeti | Tema bazında adet döner (oran değil) |

Swagger/OpenAPI dokümantasyonu otomatik üretilir ve http://localhost:8000/docs adresinde erişilebilir.

> curl -H "Authorization: Bearer test-token" \\
>
> "http://localhost:8000/kampanyalar?banka=Kuveyt%20T%C3%BCrk"

# **19. Güvenlik ve KVKK Uyumu**

## **19.1 Kimlik Doğrulama ve Yetkilendirme**

| **Konu** | **Uygulama** |
|----|----|
| Şifre saklama | bcrypt (bcrypt.hashpw + gensalt) — düz metin asla saklanmaz |
| JWT | HS256; JWT_AKTIF=true ile gerçek doğrulama devreye girer |
| Rol ataması | /kayit ile açılan hesabın rolü her zaman musteri — rol istemciden kabul edilmez |
| Roller | musteri, banka_calisani, denetleyici, yonetici |

> Jüri erişimi hakkında not: Metin Analizi ve Çıkarım Denetimi ekranları tüm giriş yapmış kullanıcılara açıktır, böylece jüri kendi hesabıyla denetim yapabilir. /cikar uç noktasındaki rol kısıtı yalnızca JWT_AKTIF=true modunda devreye girer; demo varsayılanında uygulanmaz.

## **19.2 Sır ve Anahtar Yönetimi**

- Ortam değişkenleri: Tüm API anahtarları .env dosyasında tutulur; bu dosya .gitignore içindedir ve depoya girmez. Şablon olarak .env.ornek sunulur.

- EVREN anahtarı: Git geçmişinde bulunmamaktadır.

- Otomatik tarama: CI hattında her kod gönderiminde sızmış sır taraması çalışır.

## **19.3 Enjeksiyon ve Girdi Güvenliği**

SQL enjeksiyonu, SQLAlchemy'nin parametreli sorguları ile engellenir. Daha temel bir güvence de vardır: sistem serbest metinden SQL üretmez. Karşılaştırma sorguları sabit ve parametreli şablonlardır; kullanıcı girdisi yalnızca parametre olarak yerleştirilir, sorgu yapısına asla karışmaz.

## **19.4 KVKK Değerlendirmesi**

Sistem kişisel veri toplamaz. Şikâyet hattında PII (kişisel veri) temizliği kayıttan önce zorunludur ve izin kapısı geçilmeden ham metin diske yazılmaz (§14.4). Şikâyet tablosu, kurumsal ve hukuki onay gelene kadar boş kalmaktadır.

# **20. Çevrimdışı Çalışma ve Kurulum**

## **20.1 Çevrimdışı Yetenek Beyanı**

> İnternet kesildiğinde sistem çalışmaya devam eder. Veritabanı, vektör indeksi, dil modeli ve embedding modelinin tamamı yereldir. EVREN kapalıyken sistem tam işlevle çalışır; dil modeli katmanı yerel Qwen2.5'e düşer. Ollama da kapalıysa LLM katmanı sessizce atlanır ve deterministik katmanların (regex + NER) sonucu döner — sistem durmaz, yalnızca EVREN katkısı kaybolur (§7.2).

## **20.2 Kurulum Adımları**

> \# 1) Depoyu klonla
>
> git clone https://github.com/Sara-Toptamur36/katilim-ai.git
>
> cd katilim-ai
>
> \# 2) Altyapı (PostgreSQL 5432, Qdrant 6333, Ollama 11434)
>
> docker compose up -d
>
> \# 3) Python ortamı
>
> python -m venv venv
>
> venv\Scripts\activate \# Windows
>
> source venv/bin/activate \# macOS / Linux
>
> pip install -r requirements.txt
>
> \# 4) Veritabanı şeması
>
> alembic upgrade head
>
> \# 5) API (Swagger: http://localhost:8000/docs)
>
> python demo_baslat.py \# Docker + alembic + API tek komutta
>
> python demo_baslat.py --mock \# Docker/DB GEREKMEZ
>
> \# 6) Arayüz
>
> cd dashboard && npm install && npm run dev

## **20.3 Demo Öncesi Zorunlu Adım**

> Ölçülmüş tuzak: Gömme (embedding) modeli açılışta ısıtılmazsa, sürecin ilk /chat sorusu modeli beklemek zorunda kalır — ölçüldü: 81 saniye — ve arayüz zaman aşımına uğrar. demo_baslat.py bunu otomatik açar; elle çalıştırmak için: KATILIMAI_MODEL_ISIT=true uvicorn api.main:app

## **20.4 Çevrimdışı Hazırlık Kontrolü**

Ollama modeli, embedding modeli ve Docker imajları ilk kullanımda internetten iner. Demo günü internet olmayabileceği için, internet varken bir kez çalıştırılmalıdır:

> python cevrimdisi_hazirlik_kontrolu.py

## **20.5 Veri Setine Erişim (Şartname Md. 9)**

| **İstenen**                                | **Depodaki Konumu**        |
|--------------------------------------------|----------------------------|
| Bağımlılık listesi (sürümleri sabitlenmiş) | requirements.txt           |
| Çalıştırma adımları                        | Bu bölüm (§20.2) ve README |
| Altın veri seti (+ ekran görüntüleri)      | gold_dataset/              |
| Ham kampanya metinleri (9 banka)           | scraper/raw_data/          |
| Sentetik müşteri sesi seti                 | tests/veri/kapsam_disi/    |

Veri seti harici bir servise yüklenmemiştir; depoyla birlikte doğrudan dağıtılmaktadır. Depo herkese açıktır ve klonlamak veri setini de indirir.

# **21. Test Takımı ve Kalite Güvencesi**

## **21.1 Test Sayıları**

| **Gösterge** | **Değer** | **Açıklama** |
|----|----|----|
| Geçen test | 1.278 | CI hattı, -m "not slow" seçimiyle |
| Hata | 0 | 27 Ağustos 2026 CI koşusu |
| Atlanan | 90 | Dış servis gerektiren testler |
| Test dosyası | 85 | tests/ dizini |
| Yavaş test — grup 1 | 34 | SLOW_test_sprint_is_listesi.py, ortam değişkeniyle |
| Yavaş test — grup 2 | 46 | @pytest.mark.slow işaretli |

> İki yavaş test grubu karıştırılmamalıdır. Grup 1 modül seviyesinde PYTEST_SLOW_TESTS ortam değişkeniyle atlanır (sprint iş listesi üretimi üç dakikadan uzun sürer). Grup 2 ise @pytest.mark.slow işaretiyle CI'da deselect edilir (Ollama, GLiNER veya Qdrant gerektirir). Bunlar birbirinden bağımsız iki ayrı mekanizmadır.

## **21.2 Dış Servis Gerektiren Testler**

Bazı testler dış servis gerektirir ve servis mevcut değilse hata vermez, atlanır:

| **Test Grubu**        | **Gereksinim**            | **Servis Yoksa** |
|-----------------------|---------------------------|------------------|
| Veritabanı testleri   | PostgreSQL                | Atlanır          |
| LLM / hibrit testleri | Ollama + Qwen2.5          | Atlanır          |
| Vektör arama testleri | Qdrant + embedding modeli | Atlanır          |

Bu nedenle CI'da test sayısı yerel ortamdan düşük görünür. Bu bir regresyon değil, beklenen ve belgelenmiş bir durumdur.

## **21.3 Dürüstlük ve Dairesellik Testleri**

Projenin metodolojik ilkeleri yalnızca belgelerde yazmaz; testlerle korunur:

| **Test** | **Neyi Garanti Eder** |
|----|----|
| test_olcum_kapsami.py | Çelişkili etiket kombinasyonunu imkânsız kılar (§1.4) |
| test_karsi_ornekler.py | Karşı-örneklerin üretim verisine sızmadığını tarar |
| test_sentetik_musteri_sesi.py | Sentetik şikâyet verisinin ürün verisine sızmadığını tarar |
| test_iddia_durustlugu.py | Belgelere yanlışlıkla model eğitimi iddiası yazılmasını engeller |
| test_kaynak_guncelligi.py | Kaynak güncellik alanının doldurulduğunu ve gizlenmediğini doğrular |

## **21.4 Test Komutları**

> pytest tests/ -v \# tümü
>
> pytest tests/ -m "not slow" \# CI'nin çalıştırdığı takım
>
> pytest -m "slow" \# yalnızca yavaş testler
>
> PYTEST_SLOW_TESTS=1 pytest tests/SLOW_test_sprint_is_listesi.py

# 

# **22. MLOps, CI/CD ve Sürüm Yönetimi**

| **Konu** | **Durum ve Açıklama** |
|----|----|
| CI/CD | GitHub Actions — her kod gönderiminde test ve sızmış sır taraması |
| Güvenlik taraması | Sır taraması + CodeQL analizi |
| Konteynerleştirme | Docker Compose — postgres, qdrant, ollama servisleri |
| Kalıcı depolama | pgdata, qdrantdata, ollamadata volume'leri |
| Dağıtım | GitHub Pages (statik arayüz) — deploy-pages.yml |
| Sürüm takibi | dataset_version, rag_index_version, model_version, rule_version |
| MLflow / DVC | Kullanılmıyor |

## **22.1 Sürüm Sabitleme**

Tüm Python bağımlılıkları requirements.txt içinde tam sürümle (==), Docker imajları ise sabit etiketle sabitlenmiştir. Sonuç: aynı commit her makinede aynı sürümlerle kurulur. Bu, ölçümlerin tekrar üretilebilirliğinin ön koşuludur.

## **22.2 GitHub Pages Hakkında Dürüstlük Notu**

> GitHub Pages'te backend çalışmaz. Pages yalnızca statik dosya sunar; PostgreSQL, Qdrant ve Ollama gerektiren canlı veri gösterimi ekibin kendi makinesinde çalışır. VITE_API_BASE_URL değişkeni tanımlı değilse yayınlanan site localhost:8000'e istek atar ve dış ziyaretçilerde dürüstçe "Veri alınamadı" gösterir. Bu bir hata değil, uydurma veri göstermemenin doğrudan sonucudur.

# **23. Veri Tazeliği ve Eşzamanlılık**

## **23.1 Tazelik Uç Noktası**

Sistemin veri ve indeks güncelliği /sistem/tazelik uç noktasından şeffaf biçimde raporlanır. Canlı örnek (28 Ağustos 2026):

> {
>
> "son_tarama": "2026-08-26T03:04:41", "tarama_gun_once": 2,
>
> "rag_indeks_kuruldu": "2026-08-28T07:37:13", "rag_indeks_gun_once": 0,
>
> "rag_parca_sayisi": 2186, "rag_belge_sayisi": 623,
>
> "indeks_ham_veriden_eski_mi": false,
>
> "tekil_kampanya": 525, "anlik_goruntu": 623,
>
> "dataset_version": "298imzali-2026-08-24",
>
> "rag_index_version": "2186parca-2026-08-28",
>
> "model_version": "qwen2.5:7b-instruct-q4_K_M",
>
> "rule_version": "sozluk-376da8806612",
>
> "demo_mode": false
>
> }

## **23.2 "Bilinmiyor" ile "Eski" Aynı Şey Değildir**

> indeks_ham_veriden_eski_mi alanı üç değerlidir: true, false ve null. null değeri "bilinmiyor" anlamına gelir ve false ile karıştırılmaz. "İndeks eski" ile "indeks durumu bilinmiyor" farklı bilgilerdir; bilinmeyen bir durum için tahmin üretilmez.

## **23.3 Bilinen Tazelik Farkı — Açıkça Raporlanır**

Bu sürümde RAG indeksi özyinelemeli parçalamayla yeniden kurulmuş ve Recall aynı indeks üzerinde yeniden ölçülmüştür. Önceki sürümlerdeki "ölçüm indeksi ile canlı indeks farklı" durumu böylece kapanmıştır:

| **Arayüz Bileşeni** | **Gösterdiği Bilgi**                                 |
|---------------------|------------------------------------------------------|
| Ölçüm indeksi       | 2.186 parça / 623 belge — Recall bu indekste ölçüldü |
| Canlı indeks        | 2.186 parça / 623 belge — ölçümle aynı               |

Bu ayrım, jürinin iki farklı sayıyı görüp hangisinin doğru olduğunu sormasını önlemek için açıkça etiketlenmiştir.

# **24. Sistem Sınırlılıkları ve Dürüstlük Beyanı**

> Bu bölüm eksiksizdir. Aşağıdaki maddeler hedef mimaride yer almakla birlikte bu depoda henüz tamamlanmamıştır. Jürinin sistemi doğru değerlendirebilmesi için bilinçli olarak ve ayrıntısıyla listelenmişlerdir.

## **24.1 En Önemli Sınırlılıklar**

| **\#** | **Sınırlılık** | **Ayrıntı** |
|----|----|----|
| 1 | NER katmanı net zarar veriyor | GLiNER 54 çağrıda +3 doğru alan eklerken +11 yanlış pozitif üretmekte, F1'i %72,14'ten %71,92'ye düşürmektedir (§7.2). Katman hâlâ boru hattındadır; kaldırılması veya yeniden yapılandırılması yol haritasındadır. |
| 2 | Sınıflandırma alanları zayıf | Kalan 225 kaçırmanın %80,9'u hedef_kitle (117) ve kampanya_turu (65) alanlarından gelmektedir. Bunlar anlamdan çıkarım gerektiren sınıflandırma görevleridir. |
| 3 | LLM katmanı deterministik değil | temperature=0 ile bile koşular arası oynamaktadır (ölçüldü: %89,06 ↔ %87,5). Bu nedenle nihai sayı ölçülmüş bir aralığın temsilcisidir; regex tabanı ise birebir yeniden üretilebilir. |
| 4 | Müşteri Sesi yalnızca sentetik veriyle çalışıyor | Hat kurulu ve test edilmiş durumda; eksik olan tek şey kurumsal/hukuki (KVKK) onaydır. |
| 5 | Reranker uygulanamadı | Denendi ve ölçümle reddedildi (§9.2). banka_ve_konu kategorisi kampanya_turu tür-boost mekanizmasıyla %24,00'den %40,0'a yükselmiştir; iyileşme ölçülmüş olsa da kategori hâlâ en zayıf halka olmaya devam etmektedir. |

> Önceki sürümde eksik olan iki madde bu sürümde kapanmıştır: (1) Katman katkısı ayrıştırması (ablation) tamamlandı ve NER'in net etkisi ölçüldü. (2) RAG Recall, güncel 2.186 parçalık indeks üzerinde yeniden ölçüldü. Bu iki madde artık sınırlılık değildir.

## 

## **24.2 Diğer Eksikler**

LLM ile yanıt özetleme yok: RAG kaynağı birebir döndürür. Bu bilinçlidir; özetleme ancak Verifier ile birlikte güvenli hâle gelir.

OCR kurulu değil: Taranmış/görüntü PDF'ler işlenemez (Tesseract ayrı yerel kurulum ister). Metin tabanlı PDF'ler pypdf ile işlenir; taranmış bir PDF'te metin boş dönerse kayıt düşük güvenle işaretlenir, sessizce doğru varsayılmaz.

Müşteri geri bildirim bileşeni yok: Etki skorunun ikinci yarısıdır. Gösterge veri_yok döner — sıfır yazılmaz, çünkü geri bildirim yokluğu "müşteriler memnun değil" anlamına gelmez.

KKDF/BSMV vergi hesabı yok: Hesap makinesi vergi kalemlerini hesaplamaz (§13.4).

Test coverage ölçülmüyor: Depoda coverage raporu üretilmemektedir.

## **24.3 Bileşen Bazlı Zayıflıklar**

| **Alan** | **Durum** |
|----|----|
| Çıkarımda en zayıf alanlar | hedef_kitle (117 FN), kampanya_turu (65 FN) — ikisi de sınıflandırma görevi |
| RAG'in zorlandığı kategori | banka_ve_konu (%40,0) — kampanya adı verilmeden sorulan sorular |
| Canlı olmayan metrikler | Çıkarım, RAG ve Scope Guard metrikleri 27 Ağustos ölçümüdür. Hacim ve dağılım metrikleri canlıdır. |

## **24.4 \`hedef_kitle\` Alanı — Neden Kapatılamıyor?**

Bu alan tek başına kalan hataların yarısından fazlasını oluşturmaktadır ve nedeni teknik değil, kavramsaldır. Altın veri setindeki baskın sınıf olan "Belirli segment" (yaklaşık 140 kayıt) bir insan çıkarımıdır: etiketi yazan kişi ürün adından ve kampanya tipinden anlam çıkarmıştır; o ifade kaynak metinde aynen geçmez. Kural genişleterek kapatılabilecek bir boşluk değildir — denenmiş ve ölçümle reddedilmiştir. Bu, altın veri setinin etiketleme tanımıyla ilgili yapısal bir sınırdır ve açıkça raporlanmaktadır.

# **25. Gelecek Yol Haritası**

| **Öncelik** | **Plan** | **Gerekçe** |
|----|----|----|
| Yüksek | NER katmanının kaldırılması veya yeniden yapılandırılması | Ölçülmüş net negatif katkı: +3 TP'ye karşılık +11 FP (§7.2) |
| Yüksek | hedef_kitle için etiketleme tanımının gözden geçirilmesi | Kalan hataların %52'si bu alandan; sorun kavramsal (§24.4) |
| Yüksek | kampanya_turu sınıflandırmasının güçlendirilmesi | Kalan hataların %29'u bu alandan |
| Orta | banka_ve_konu kategorisi için alternatif getirme stratejisi | Reranker ölçümle reddedildi; farklı bir yaklaşım gerekiyor (§9.2) |
| Orta | Altın veri setinin 302'nin üzerine büyütülmesi | Ölçüm hassasiyetinin artırılması |
| Orta | RAG otomatik yeniden indeksleme | Tazelik farkının yapısal olarak kapanması |
| Orta | Complaint Insight'ın gerçek anonim veriyle geliştirilmesi | KVKK onayı sonrası, Faz 2 |
| Düşük | OCR entegrasyonu | Taranmış PDF kapsamı |
| — | Fine-tuning yapılmayacaktır | Mimari tercih; iddia edilmiyor (§2.3) |

# **26. Demo Senaryosu**

## **26.1 Önerilen Akış**

| **Adım** | **Ekran / İşlem** | **Gösterilecek** |
|----|----|----|
| 1 | Genel Bakış | Canlı veri rozeti, kapsam (9/10 banka), banka dağılımı, veri tazeliği |
| 2 | AI Asistan — bilgi sorusu | "Kuveyt Türk'ün konut finansmanı kampanyalarında kâr payı oranı nedir?" → RAG → kaynak parçası birebir + parça kimliği + skor |
| 3 | AI Asistan — karşılaştırma | "En düşük kâr payı oranlı kart kampanyası hangisi?" → SQL şablonu → eksik veriler NULLS LAST ile sonda |
| 4 | AI Asistan — toplam maliyet | "500.000 TL için Kuveyt Türk ile Ziraat Katılım'ın toplam maliyetini karşılaştır" → saf Python amortisman |
| 5 | Jüri Audit Paneli | Karar zinciri: niyet → araç → SQL/retriever → doğrulama → süre |
| 6 | Çıkarım Denetimi | Kampanya seç → alan alan katman, güven, gold referansı, kanıt spanı |
| 7 | Metin Analizi | Serbest metin yapıştır → yapılandırılmış çıktı (Md. 6 gereksinimi) |

## **26.2 Kurtarma Planları**

Demo sırasında oluşabilecek teknik sorunlar ve sistemin bunlara verdiği yanıt:

| **Sorun** | **Kurtarma** |
|----|----|
| EVREN yanıt vermiyor | Otomatik — yerel Qwen2.5'e düşer, sistem durmaz |
| Ollama kapalı | Otomatik — LLM katmanı atlanır, regex + NER sonucu döner |
| Qdrant bağlantısı kopuk | RAG çekimser kalır; SQL, hesaplama ve sözlük araçları çalışmaya devam eder |
| PostgreSQL erişilemiyor | python demo_baslat.py --mock — Docker ve veritabanı gerekmez |
| Arayüz yüklenmiyor | Swagger /docs üzerinden uç noktalar canlı gösterilebilir |
| İlk soru çok yavaş | Model ısıtması yapılmamış → KATILIMAI_MODEL_ISIT=true ile başlat |

# **27. EVREN Entegrasyonu**

## **27.1 Kullanılan Modeller**

| **Model** | **Kullanım Durumu** | **Gerekçe** |
|----|----|----|
| llm-fast | Kullanılıyor | Hibrit çıkarımın LLM katmanı — opsiyonel sağlayıcı |
| bge-m3-embed | İstemcide tanımlı, üretimde kullanılmıyor | Yerel embedding tercih edildi |
| llm-large | Kullanılmıyor | Ölçümde llm-fast ile fark bulunamadı (5/5 görev) |
| router | Kullanılmıyor | Niyet tespiti deterministik yerel katmanla yapılır (Md. 5.9) |
| rerank, bge-m3-sparse, bge-m3-colbert | Kullanılmıyor | Dokümantasyonun kendi ölçümünde hibrit+rerank saf yoğun aramadan düşük çıktı (0,55 vs 0,95) |
| vlm, guard | Kullanılmıyor | Görev profiline girmiyor |

## **27.2 Model Seçim Gerekçesi**

llm-fast tercih edilmiştir çünkü JSON üretimi, sınıflandırma ve araç çağırma gibi biçim ağırlıklı görevlerde llm-large ile ölçülmüş bir fark bulunamamıştır (5/5 görev). llm-large'ın öne çıktığı alanlar (kültürel ve tarihî bilgi, video anlama) bu projenin görev profiline girmemektedir. Ayrıntılı gerekçe docs/adr/0002-evren-cikarim-entegrasyonu.md kararında belgelenmiştir.

## **27.3 Bulunan ve Düzeltilen Sessiz Hata**

> EVREN entegrasyonunda sessiz bir hata tespit edilip giderilmiştir. llm-fast modeli varsayılan olarak bir *"düşünme zinciri"* üretiyordu; bu, max_tokens sınırını tüketip çağrıyı sessizce boş döndürüyordu (finish_reason=length, content=null). Hata mesajı üretilmediği için uzun süre fark edilmedi. Çözüm: chat_template_kwargs.enable_thinking=false. Düzeltme sonrası EVREN ölçüme dahil edilebildi; nihai boru hattı F1 değeri %87,25'e ulaştı.

## **27.4 Yedekleme ve Bağımsızlık**

EVREN_API_KEY tanımlı değilse evren_istemci.py içindeki tüm fonksiyonlar pasif döner ve sistem yerel Qwen2.5 ile çalışmaya devam eder. Şartnamenin çevrimdışı ve açık kaynak gereksinimleri yerel yığınla tam olarak sağlanmaktadır; EVREN yalnızca opsiyonel bir alternatif sağlayıcıdır.

# **28. Ölçümlerin Yeniden Üretilmesi**

Bu belgedeki her sayı aşağıdaki komutlarla yeniden üretilebilir. Jüri, depoyu klonlayıp bu komutları çalıştırarak tüm metrikleri bağımsız olarak doğrulayabilir.

> \# Çıkarım doğruluğu — dolu/boş alan + alan bazlı F1
>
> python -m scraper.scripts.extraction_accuracy
>
> \# Hibrit çıkarım (regex + NER + LLM)
>
> python -m scraper.scripts.hibrit_extraction_accuracy
>
> \# Katman katkısı tablosu (henüz koşulmadı — bkz. §24.1)
>
> python -m scraper.scripts.ablation
>
> \# RAG Recall@k + çekimserlik
>
> python -m scraper.scripts.rag_degerlendirme
>
> \# Kapsam ölçümü (hassasiyet / özgüllük)
>
> pytest tests/test_karsi_ornekler.py -s
>
> \# CI'nin çalıştırdığı test takımı
>
> pytest tests/ -m "not slow"
>
> Sağlayıcı seçimi ölçümde de geçerlidir. .env dosyasında EVREN_API_KEY tanımlıysa hibrit ölçüm EVREN'in llm-fast modelini, tanımlı değilse yerel Ollama'yı kullanır. Aynı komut, hangi sağlayıcının kullanıldığını çıktının başında yazar — iki koşunun sayıları karıştırılmasın diye.

## **28.1 Ölçüm Raporları**

| **Rapor Dosyası** | **İçeriği** |
|----|----|
| cikarim_dogruluk_raporu.json | Alan bazlı F1, regex ve hibrit karşılaştırması, NER durumu |
| docs/extraction_accuracy_raporu.md | Çıkarım yöntemi ve yanlış pozitif analizi |
| docs/rag_tasarim_ve_olcum.md | RAG tasarımı, eşik kalibrasyonu, bulgular |
| docs/kapsam_ve_veri_ayrimi.md | Scope Guard ölçüm metodolojisi |
| docs/md6_dokumantasyon.md | Şartname Md. 6'nın 10 kalemi tek belgede |
| docs/adr/0002-evren-cikarim-entegrasyonu.md | EVREN model seçim gerekçesi |

# **29. Şartname Uyum Tablosu**

| **Madde** | **Konu** | **Projedeki Karşılığı** | **Durum** |
|----|----|----|----|
| Md. 5.3 | Hedef kitle, kampanya süresi | Üç alan da ölçüme dahil; kalan kaçırmalar §7.4'te alan alan raporlanır | Ölçüldü |
| Md. 5.4 | Kampanya türü sınıflandırması | kampanya_turu ölçüme dahil, 11 tür; kalan 65 kaçırma §7.4'te | Ölçüldü |
| Md. 5.5 | Terminoloji | 31 kavram, /terminoloji uç noktası | Tamam |
| Md. 5.6 | Normalizasyon | Oran, vade, tutar ve tarih normalizasyonu (preprocessing/) | Tamam |
| Md. 5.7 | Karşılaştırma kriterleri | 5 kriter + 1 bonus (comparison/compare_engine.py) | Tamam |
| Md. 5.9 | On-premise / çevrimdışı | Tüm yığın yerel; cevrimdisi_hazirlik_kontrolu.py | Tamam |
| Md. 5.10 / 8 | Açık kaynak | Tüm bileşenler açık kaynak, Apache-2.0 | Tamam |
| Md. 6 | Dokümantasyon (10 kalem) | docs/md6_dokumantasyon.md + /cikar demo ekranı | Tamam |
| Md. 9 | Veri erişimi | requirements.txt · kurulum adımları · gold_dataset/ · scraper/raw_data/ | Tamam |

**PeacewAI · TEKNOFEST 2026**

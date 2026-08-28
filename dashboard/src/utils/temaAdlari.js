// Tema kodunun Turkce karsiligi - yalnizca GORUNUM icindir.
//
// complaint/tema_siniflandirici.py::TEMA_ADLARI ile BILEREK AYNI degerler
// (backend'deki ayni sozlugun frontend karsiligi - gercek `sikayetler`
// tablosunu okuyan uc noktalar /musteri-sesi/istatistikler ve
// /kampanyalar/{id}/musteri-sesi-ozeti ham KOD doner, MusteriSesi.jsx'teki
// gibi {kod, ad} cifti tasiyan bir sentetik-ornek endpoint'i yok - bu
// yuzden bu iki widget (MusteriSesiWidget, KampanyaMusteriSesiWidget)
// kendi haritasina ihtiyac duyar). `tema` ALANI hala koddur, bu sozluk
// yalnizca gorunen metni uretir.
export const TEMA_ADLARI = {
  REWARD_NOT_CREDITED: "Ödül yatmadı",
  ELIGIBILITY_MISMATCH: "Koşul uyuşmazlığı",
  INSTALLMENT_MATURITY: "Taksit/vade uyuşmazlığı",
  MERCHANT_MCC_SCOPE: "İşyeri kapsam dışı",
  ACTIVATION_REGISTRATION: "Aktivasyon sorunu",
  DATE_EXPIRY: "Tarih uyuşmazlığı",
  CARD_PRODUCT_MISMATCH: "Kart/ürün uyuşmazlığı",
  FEE_CHARGE: "Beklenmeyen ücret",
  COMMUNICATION_AMBIGUITY: "İletişim belirsizliği",
  SERVICE_RESOLUTION: "Çözüm sürecinde sorun",
};

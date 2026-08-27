// SONUÇ basligi - cevabin en ustunde, ham paragraftan once gosterilen
// kisa ozet satiri. Amac: kullanicinin uzun bir blok yerine once TEK
// cumlelik sonucu gormesi (bkz. sohbet arayuzu yeniden tasarimi).
export default function SonucBaslik({ kisaSonuc, aciklama }) {
  if (!kisaSonuc) return null;

  return (
    <div className="sonuc-baslik-blok">
      <div className="sonuc-baslik-etiket">SONUÇ</div>
      <div className="sonuc-baslik-metin">{kisaSonuc}</div>
      {aciklama && <div className="sonuc-baslik-aciklama">{aciklama}</div>}
    </div>
  );
}

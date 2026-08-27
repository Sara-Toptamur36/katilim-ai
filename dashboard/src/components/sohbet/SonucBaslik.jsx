// SONUÇ basligi - cevabin en ustunde, ham paragraftan once gosterilen
// kisa ozet satiri. Amac: kullanicinin uzun bir blok yerine once TEK
// cumlelik sonucu gormesi (bkz. sohbet arayuzu yeniden tasarimi).
//
// durumRozetesi / sure: audit'te ZATEN var olan, ama daha once yalniz
// Karar Zinciri modalinda gorunen iki alanin (dogrulama.durum, latency_ms)
// ana goruntude de yuzeye cikarilmis hali - yeni bir olcum degil, mevcut
// verinin ust seviyede gosterimi.
export default function SonucBaslik({ kisaSonuc, aciklama, durumRozetesi, sure }) {
  if (!kisaSonuc) return null;

  return (
    <div className="sonuc-baslik-blok">
      <div className="sonuc-baslik-ust-satir">
        <div className="sonuc-baslik-etiket">SONUÇ</div>
        <div className="sonuc-baslik-ust-satir-sag">
          {sure && <span className="sonuc-baslik-sure">Yanıt süresi: {sure}</span>}
          {durumRozetesi && (
            <span className={`sonuc-baslik-durum-rozeti ${durumRozetesi.renk}`}>
              {durumRozetesi.etiket}
            </span>
          )}
        </div>
      </div>
      <div className="sonuc-baslik-metin">{kisaSonuc}</div>
      {aciklama && <div className="sonuc-baslik-aciklama">{aciklama}</div>}
    </div>
  );
}

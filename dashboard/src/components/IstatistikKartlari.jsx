import { Card, Row, Col, Tooltip } from "antd";
import {
  DatabaseOutlined,
  CheckCircleOutlined,
  BankOutlined,
  PercentageOutlined,
} from "@ant-design/icons";

// DUZELTILEN YANLIS ETIKET (24.08.2026): kart basligi "Aktif Banka Sayisi"
// diyordu ama hesap TUM bankalari sayiyordu - durum alani o tarihte
// veritabaninda hep BILINMIYOR oldugu icin "aktif" diye bir ayrim zaten
// yapilamiyordu. Yasam dongusu hesabi duzeltilince (bkz.
// api/kampanya_repository._durum_coz) ayrim gercekten mumkun oldu:
// baslik durustlestirildi ve AYRI bir "Aktif Kampanya" karti eklendi.
export default function IstatistikKartlari({ kampanyalar = [] }) {
  // HATA 2: Toplam Kayıt ve kaynak_url bazlı tekil kampanya sayısı
  const toplamKayitSayisi = kampanyalar.length;
  const tekilKampanyaSayisi = new Set(
    kampanyalar.map((k) => k.kaynak_url).filter(Boolean)
  ).size;

  // Aktif Kampanya ve Banka Sayısı
  const aktifSayisi = kampanyalar.filter((k) => k.durum === "ACTIVE").length;
  const bankaSayisi = new Set(kampanyalar.map((k) => k.banka).filter(Boolean)).size;

  // HATA 1: Kâr Payı Oranı Analizi (%0 olanlar vade farksız / kâr payı alınmıyor)
  const karPayiOlanlar = kampanyalar.filter((k) => k.kar_payi_orani_percent != null);
  const sifirKarPayiSayisi = kampanyalar.filter((k) => k.kar_payi_orani_percent === 0).length;
  const pozitifKarPaylari = karPayiOlanlar.filter((k) => k.kar_payi_orani_percent > 0);
  const enDusukPozitifKarPayi =
    pozitifKarPaylari.length > 0
      ? Math.min(...pozitifKarPaylari.map((k) => k.kar_payi_orani_percent))
      : null;

  return (
    <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
      {/* 1. Toplam Kayıt Kartı */}
      <Col xs={24} sm={12} lg={6}>
        <Tooltip title="Bir kampanyanın birden çok tarihli anlık görüntüsü olabilir; toplam kayıt bu görüntüleri de sayar.">
          <Card className="istatistik-karti aksam-yesil">
            <div>
              <div className="istatistik-ust-satir">
                <span className="istatistik-baslik">Toplam Kayıt</span>
                <DatabaseOutlined className="istatistik-ikon yesil" />
              </div>
              <div className="istatistik-deger">{toplamKayitSayisi}</div>
            </div>
            <div className="istatistik-alt-not">
              {tekilKampanyaSayisi} tekil kampanya
            </div>
          </Card>
        </Tooltip>
      </Col>

      {/* 2. Aktif Kampanya Kartı */}
      <Col xs={24} sm={12} lg={6}>
        <Tooltip title="Bitiş tarihi bugünden ileride olan kampanyalar. Tarihi belirtilmemiş kayıtlar 'bilinmiyor' sayılır, aktif sayılmaz.">
          <Card className="istatistik-karti aksam-yesil">
            <div>
              <div className="istatistik-ust-satir">
                <span className="istatistik-baslik">Aktif Kampanya</span>
                <CheckCircleOutlined className="istatistik-ikon yesil" />
              </div>
              <div className="istatistik-deger">{aktifSayisi}</div>
            </div>
            <div className="istatistik-alt-not">
              {aktifSayisi} / {toplamKayitSayisi} kayıt yayında
            </div>
          </Card>
        </Tooltip>
      </Col>

      {/* 3. Banka Sayısı Kartı */}
      <Col xs={24} sm={12} lg={6}>
        <Tooltip title="Veritabanında kampanyası bulunan katılım bankası sayısı.">
          <Card className="istatistik-karti aksam-altin">
            <div>
              <div className="istatistik-ust-satir">
                <span className="istatistik-baslik">Banka Sayısı</span>
                <BankOutlined className="istatistik-ikon altin" />
              </div>
              <div className="istatistik-deger">{bankaSayisi}</div>
            </div>
            <div className="istatistik-alt-not">
              Tüm katılım bankaları dahil
            </div>
          </Card>
        </Tooltip>
      </Col>

      {/* 4. En Düşük Kâr Payı Kartı */}
      <Col xs={24} sm={12} lg={6}>
        <Tooltip title="Sıfırdan büyük en düşük aylık kâr payı oranı. %0 olanlar kâr payı alınmayan (vade farksız) işlemleri temsil eder.">
          <Card className="istatistik-karti aksam-altin">
            <div>
              <div className="istatistik-ust-satir">
                <span className="istatistik-baslik">En Düşük Kâr Payı</span>
                <PercentageOutlined className="istatistik-ikon altin" />
              </div>
              <div className="istatistik-deger">
                {enDusukPozitifKarPayi != null
                  ? `%${enDusukPozitifKarPayi.toLocaleString("tr-TR")}`
                  : "Belirtilmemiş"}
              </div>
            </div>
            <div className="istatistik-alt-not">
              {sifirKarPayiSayisi > 0 ? `${sifirKarPayiSayisi} kampanyada %0 (vade farksız) · ` : ""}
              {karPayiOlanlar.length} / {toplamKayitSayisi} kayıtta ölçülebilir
            </div>
          </Card>
        </Tooltip>
      </Col>
    </Row>
  );
}

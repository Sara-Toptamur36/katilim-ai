import { Collapse } from "antd";
import { MOCK_TERIMLER } from "../api/terminolojiMock";

// TODO(Sara): /terminoloji endpoint'i eklenince MOCK_TERIMLER yerine
// api/client.js'deki gercek fonksiyon cagrilacak (bkz. terminolojiMock.js).
export default function TerminolojiSozlugu() {
  return (
    <Collapse
      items={MOCK_TERIMLER.map((t, i) => ({
        key: i,
        label: t.standart_terim,
        children: (
          <>
            <p>
              <strong>Geleneksel bankaciliktaki karsiligi:</strong> {t.gelenek_karsilik}
            </p>
            <p>
              <strong>Aciklama:</strong> {t.aciklama}
            </p>
          </>
        ),
      }))}
    />
  );
}

import { Button, message } from "antd";
import { CopyOutlined } from "@ant-design/icons";

export default function KopyalaButonu({ metin }) {
  const kopyala = async () => {
    try {
      await navigator.clipboard.writeText(metin);
      message.success("Panoya kopyalandi");
    } catch {
      message.error("Kopyalanamadi");
    }
  };

  return (
    <Button size="small" icon={<CopyOutlined />} onClick={kopyala}>
      Kopyala
    </Button>
  );
}

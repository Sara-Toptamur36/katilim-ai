import axios from "axios";

// Sara'nin FastAPI'sinin adresi (Sprint 1: lokal calisir)
const API_TABANI = "http://localhost:8000";

const TOKEN_ANAHTARI = "katilimai_token";

export const tokenKaydet = (token) => {
  localStorage.setItem(TOKEN_ANAHTARI, token);
};

export const tokenAl = () => {
  // Sprint 1-3: mock modda deger kontrol edilmiyor, herhangi bir metin yeter
  return localStorage.getItem(TOKEN_ANAHTARI) || "mock-token-havin";
};

export const tokenSil = () => {
  localStorage.removeItem(TOKEN_ANAHTARI);
};

const client = axios.create({
  baseURL: API_TABANI,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 10000,
});

// Her istekte guncel token'i otomatik ekler (Sprint 4'te gercek JWT'ye
// gecildiginde bu dosyada baska hicbir sey degismeyecek)
client.interceptors.request.use((config) => {
  config.headers["Authorization"] = `Bearer ${tokenAl()}`;
  return config;
});

client.interceptors.response.use(
  (yanit) => yanit,
  (hata) => {
    if (hata.response?.status === 401) {
      tokenSil();
    }
    return Promise.reject(hata);
  }
);

// GET /kampanyalar?banka=...&kampanya_turu=...
export const kampanyalariGetir = async (filtreler = {}) => {
  const yanit = await client.get("/kampanyalar", { params: filtreler });
  return yanit.data;
};

// GET /kampanyalar/{id}
export const kampanyaDetay = async (id) => {
  const yanit = await client.get(`/kampanyalar/${id}`);
  return yanit.data;
};

// POST /karsilastir  { ids, kriter }
export const karsilastir = async (
  idListesi,
  kriter = "en_dusuk_kar_payi"
) => {
  const yanit = await client.post("/karsilastir", { ids: idListesi, kriter });
  return yanit.data;
};

// POST /hesapla  { anapara, aylik_oran_percent, vade_ay, odeme_plani_istiyor }
export const hesapla = async (girdi) => {
  const yanit = await client.post("/hesapla", girdi);
  return yanit.data;
};

// POST /chat  { soru }
export const chatGonder = async (soru) => {
  const yanit = await client.post("/chat", { soru });
  return yanit.data;
};

export default client;

import { createContext, useContext, useEffect, useState } from "react";

// Chatbot ve Jüri Audit Paneli farkli sayfalar (route) oldugu icin, /chat
// yanitindaki audit blogunu ikisi arasinda paylasmak icin bir Context
// kullaniliyor. sessionStorage'a da yazilir ki sayfa yenilenince kaybolmasin
// (sohbet gecmisiyle ayni mantik, bkz. Chatbot.jsx).
const AuditContext = createContext(null);

const GECMIS_ANAHTARI = "katilimai_audit_gecmisi";
const MAKS_GECMIS = 20;

export function AuditProvider({ children }) {
  const [auditGecmisi, setAuditGecmisi] = useState(() => {
    const kayitli = sessionStorage.getItem(GECMIS_ANAHTARI);
    return kayitli ? JSON.parse(kayitli) : [];
  });

  useEffect(() => {
    sessionStorage.setItem(GECMIS_ANAHTARI, JSON.stringify(auditGecmisi));
  }, [auditGecmisi]);

  const auditEkle = (audit, soru) => {
    if (!audit) return;
    setAuditGecmisi((onceki) =>
      [{ ...audit, soru, zaman: new Date().toISOString() }, ...onceki].slice(0, MAKS_GECMIS)
    );
  };

  const sonAudit = auditGecmisi[0] ?? null;

  return (
    <AuditContext.Provider value={{ sonAudit, auditGecmisi, auditEkle }}>
      {children}
    </AuditContext.Provider>
  );
}

export function useAudit() {
  const ctx = useContext(AuditContext);
  if (!ctx) throw new Error("useAudit, AuditProvider icinde kullanilmali");
  return ctx;
}

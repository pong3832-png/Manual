import { useEffect } from "react";
import { publicEnv } from "../../../shared/config/publicEnv.js";

const ADSENSE_SCRIPT_ID = "adsense-auto-script";
const ADSENSE_HOST = "pagead2.googlesyndication.com";

function normalizeAdSenseClientId(value = "") {
  const clientId = String(value || "").trim();
  if (clientId.startsWith("ca-pub-")) return clientId;
  if (clientId.startsWith("pub-")) return `ca-${clientId}`;
  return clientId;
}

function canLoadAdSense() {
  if (typeof window === "undefined") return false;
  if (publicEnv.adsenseEnableLocal === "1") return true;
  if (!publicEnv.isProduction) return false;

  return !["localhost", "127.0.0.1"].includes(window.location.hostname);
}

function AdSenseLoader() {
  useEffect(() => {
    const clientId = normalizeAdSenseClientId(publicEnv.adsenseClient);
    if (!clientId || !/^ca-pub-\d+$/.test(clientId) || !canLoadAdSense()) return;
    if (document.getElementById(ADSENSE_SCRIPT_ID)) return;

    const script = document.createElement("script");
    script.id = ADSENSE_SCRIPT_ID;
    script.async = true;
    script.crossOrigin = "anonymous";
    script.src = `https://${ADSENSE_HOST}/pagead/js/adsbygoogle.js?client=${encodeURIComponent(clientId)}`;
    document.head.appendChild(script);
  }, []);

  return null;
}

export default AdSenseLoader;

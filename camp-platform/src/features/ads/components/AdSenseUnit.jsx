import { useEffect, useMemo, useRef, useState } from "react";
import { trackAdEvent } from "../lib/ads";
import { publicEnv } from "../../../shared/config/publicEnv.js";

function normalizeAdSenseClientId(value = "") {
  const clientId = String(value || "").trim();
  if (clientId.startsWith("ca-pub-")) return clientId;
  if (clientId.startsWith("pub-")) return `ca-${clientId}`;
  return clientId;
}

function canRenderAdSense() {
  if (typeof window === "undefined") return false;
  if (publicEnv.adsenseEnableLocal === "1") return true;
  if (!publicEnv.isProduction) return false;
  return !["localhost", "127.0.0.1"].includes(window.location.hostname);
}

function isAdSenseFilled(slotNode) {
  const adNode = slotNode?.querySelector(".adsbygoogle");
  if (!adNode) return false;
  if (adNode.getAttribute("data-ad-status") === "filled") return true;
  if (adNode.getAttribute("data-ad-status") === "unfilled") return false;
  return Boolean(adNode.querySelector("iframe"));
}

function AdSenseUnit({ slotId, placementId, context = {}, variant = "default", channel = "", fallback = null }) {
  const clientId = normalizeAdSenseClientId(publicEnv.adsenseClient);
  const normalizedSlotId = String(slotId || "").trim();
  const logicalSlotId = String(placementId || normalizedSlotId);
  const slotRef = useRef(null);
  const impressedRef = useRef("");
  const [fallbackState, setFallbackState] = useState({ key: "", visible: false });
  const canRender = canRenderAdSense()
    && /^ca-pub-\d+$/.test(clientId)
    && /^\d+$/.test(normalizedSlotId);

  const key = useMemo(
    () => `${clientId}:${normalizedSlotId}:${channel || "default"}`,
    [channel, clientId, normalizedSlotId],
  );
  const showFallback = fallbackState.key === key && fallbackState.visible;

  useEffect(() => {
    if (!canRender) return;

    try {
      window.adsbygoogle = window.adsbygoogle || [];
      window.adsbygoogle.push({});
    } catch {
      // AdSense can throw while navigating in a client-rendered app; leave the slot empty.
    }
  }, [canRender, key]);

  useEffect(() => {
    if (!canRender) return undefined;

    const timeout = window.setTimeout(() => {
      if (!isAdSenseFilled(slotRef.current)) {
        setFallbackState({ key, visible: true });
      }
    }, 3500);

    return () => window.clearTimeout(timeout);
  }, [canRender, key]);

  useEffect(() => {
    if (!canRender || !slotRef.current || impressedRef.current === key) return undefined;

    const syntheticAd = {
      id: `adsense_${logicalSlotId}_${normalizedSlotId}`,
      provider: "adsense",
      targetUrl: "",
    };
    const node = slotRef.current;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        if (!isAdSenseFilled(node)) return;
        impressedRef.current = key;
        trackAdEvent(syntheticAd, logicalSlotId, "impression", {
          context,
          variant,
          adSenseSlotId: normalizedSlotId,
          channel,
        });
        observer.disconnect();
      },
      { threshold: 0.35 },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [canRender, channel, context, key, logicalSlotId, normalizedSlotId, variant]);

  if (!canRender || showFallback) return fallback;

  return (
    <aside ref={slotRef} className={`adsense-slot adsense-slot--${variant}`} aria-label="광고">
      <ins
        key={key}
        className="adsbygoogle"
        style={{ display: "block" }}
        data-ad-client={clientId}
        data-ad-slot={normalizedSlotId}
        data-ad-format="auto"
        data-full-width-responsive="true"
        {...(channel ? { "data-ad-channel": channel } : {})}
      />
    </aside>
  );
}

export default AdSenseUnit;

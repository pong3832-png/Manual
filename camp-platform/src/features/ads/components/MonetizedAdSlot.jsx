import AdBanner from "./AdBanner";
import AdSenseUnit from "./AdSenseUnit";
import { publicEnv } from "../../../shared/config/publicEnv.js";

const ADSENSE_SLOT_IDS = {
  home_top: publicEnv.adsenseSlots.home_top,
  explore_inline: publicEnv.adsenseSlots.explore_inline,
  map_bottom: publicEnv.adsenseSlots.map_bottom,
};

const ADSENSE_CHANNEL_IDS = {
  home_top: publicEnv.adsenseChannels.home_top,
  explore_inline: publicEnv.adsenseChannels.explore_inline,
  map_bottom: publicEnv.adsenseChannels.map_bottom,
};

function canRenderAdSenseSlot() {
  if (typeof window === "undefined") return false;
  if (publicEnv.adsenseEnableLocal === "1") return true;
  if (!publicEnv.isProduction) return false;
  return !["localhost", "127.0.0.1"].includes(window.location.hostname);
}

function MonetizedAdSlot({ slotId, context = {}, variant = "default" }) {
  const adSenseSlotId = String(ADSENSE_SLOT_IDS[slotId] || "").trim();
  const adSenseChannel = String(ADSENSE_CHANNEL_IDS[slotId] || "").trim();
  const fallback = <AdBanner slotId={slotId} context={context} variant={variant} />;

  if (adSenseSlotId && canRenderAdSenseSlot()) {
    return (
      <AdSenseUnit
        slotId={adSenseSlotId}
        placementId={slotId}
        context={context}
        variant={variant}
        channel={adSenseChannel}
        fallback={fallback}
      />
    );
  }

  return fallback;
}

export default MonetizedAdSlot;

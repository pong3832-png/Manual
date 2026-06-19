import { useEffect, useState } from "react";
import { collapseDuplicateCampaigns, enrichCampaign, fetchCampaignsFromSupabase, isCampaignOpen } from "../lib/campaigns";
import { mergeCampaignPointsFromSnapshot } from "../lib/campaignPointMerge.js";
import { shouldUseSupabaseCampaignSource } from "../lib/campaignSourcePolicy.js";
import { isSupabaseConfigured } from "../../../shared/api/supabase";
import { publicEnv } from "../../../shared/config/publicEnv.js";

const CAMPAIGN_REFRESH_MS = 5 * 60 * 1000;

async function fetchCampaignsFromLocalSnapshot() {
  const response = await fetch("/campaigns.json", { cache: "no-cache" });
  if (!response.ok) {
    throw new Error(`최근 공개 데이터를 불러오지 못했습니다. (${response.status})`);
  }

  const payload = await response.json();
  const localCampaigns = (payload?.campaigns || [])
    .map((campaign) => enrichCampaign(campaign))
    .filter(isCampaignOpen);

  return collapseDuplicateCampaigns(localCampaigns);
}

export default function useCampaigns() {
  const [campaigns, setCampaigns] = useState([]);
  const [campaignLoadError, setCampaignLoadError] = useState("");
  const [loading, setLoading] = useState(true);
  const shouldUseSupabaseCampaigns = shouldUseSupabaseCampaignSource({
    isSupabaseConfigured,
    env: publicEnv.raw,
  });
  const shouldBackgroundRefresh = shouldUseSupabaseCampaigns;

  useEffect(() => {
    let active = true;
    let inFlight = false;

    const loadCampaigns = async ({ isBackground = false } = {}) => {
      if (inFlight) return;
      inFlight = true;

      if (!isBackground && active) {
        setLoading(true);
      }

      try {
        if (!shouldUseSupabaseCampaigns) {
          const localCampaigns = await fetchCampaignsFromLocalSnapshot();

          if (!active) return;

          setCampaigns(localCampaigns);
          setCampaignLoadError("");
          return;
        }

        const dbCampaigns = await fetchCampaignsFromSupabase();
        if (!active) return;

        if (dbCampaigns.length > 0) {
          let mergedCampaigns = dbCampaigns.filter(isCampaignOpen);
          try {
            const localCampaigns = await fetchCampaignsFromLocalSnapshot();
            mergedCampaigns = mergeCampaignPointsFromSnapshot(mergedCampaigns, localCampaigns).filter(isCampaignOpen);
          } catch {
            // Keep DB results when the static snapshot is temporarily unavailable.
          }

          setCampaigns(mergedCampaigns);
          setCampaignLoadError("");
          return;
        }

        const localCampaigns = await fetchCampaignsFromLocalSnapshot();
        if (!active) return;

        setCampaigns(localCampaigns);
        setCampaignLoadError("");
      } catch (error) {
        if (!isBackground) {
          try {
            const localCampaigns = await fetchCampaignsFromLocalSnapshot();
            if (!active) return;

            setCampaigns(localCampaigns);
            setCampaignLoadError("");
          } catch {
            if (!active) return;

            setCampaigns([]);
            setCampaignLoadError(error?.message || "캠페인 데이터를 불러오지 못했습니다.");
          }
        }
      } finally {
        if (active) setLoading(false);
        inFlight = false;
      }
    };

    loadCampaigns();

    const intervalId = shouldBackgroundRefresh
      ? window.setInterval(() => {
        loadCampaigns({ isBackground: true });
      }, CAMPAIGN_REFRESH_MS)
      : null;

    const handleVisibilityChange = () => {
      if (shouldBackgroundRefresh && document.visibilityState === "visible") {
        loadCampaigns({ isBackground: true });
      }
    };

    const handleWindowFocus = () => {
      if (shouldBackgroundRefresh) {
        loadCampaigns({ isBackground: true });
      }
    };

    if (shouldBackgroundRefresh) {
      window.addEventListener("focus", handleWindowFocus);
      document.addEventListener("visibilitychange", handleVisibilityChange);
    }

    return () => {
      active = false;
      if (intervalId) window.clearInterval(intervalId);
      if (shouldBackgroundRefresh) {
        window.removeEventListener("focus", handleWindowFocus);
        document.removeEventListener("visibilitychange", handleVisibilityChange);
      }
    };
  }, [shouldBackgroundRefresh, shouldUseSupabaseCampaigns]);

  return { campaigns, campaignLoadError, loading };
}

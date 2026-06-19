import { useEffect, useState } from "react";
import { rememberAdContext, selectAdForSlot } from "../lib/ads";

const EMPTY_ADS = [];

function useAds(slotId, context = {}) {
  const [ads, setAds] = useState(EMPTY_ADS);
  const contextCategory = context.category;
  const contextCity = context.city;
  const contextPage = context.page;
  const contextProvince = context.province;
  const contextRegion = context.region;

  useEffect(() => {
    let cancelled = false;

    async function loadAds() {
      try {
        const response = await fetch("/ads.json", { cache: "no-store" });
        if (!response.ok) throw new Error(`ads.json ${response.status}`);
        const payload = await response.json();
        if (!cancelled) setAds(Array.isArray(payload?.ads) ? payload.ads : EMPTY_ADS);
      } catch {
        if (!cancelled) setAds(EMPTY_ADS);
      }
    }

    loadAds();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    rememberAdContext({
      category: contextCategory,
      city: contextCity,
      page: contextPage,
      province: contextProvince,
      region: contextRegion,
    });
  }, [contextCategory, contextCity, contextPage, contextProvince, contextRegion]);

  return selectAdForSlot(ads, slotId, context);
}

export default useAds;

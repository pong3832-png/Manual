const processEnv = typeof process !== "undefined" && process.env ? process.env : {};
const viteEnv = typeof import.meta !== "undefined" && import.meta.env ? import.meta.env : {};

function firstValue(...values) {
  return values.map((value) => String(value || "").trim()).find(Boolean) || "";
}

const raw = {
  VITE_SUPABASE_URL: firstValue(processEnv.NEXT_PUBLIC_SUPABASE_URL, processEnv.VITE_SUPABASE_URL, viteEnv.VITE_SUPABASE_URL),
  VITE_SUPABASE_ANON_KEY: firstValue(
    processEnv.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    processEnv.VITE_SUPABASE_ANON_KEY,
    viteEnv.VITE_SUPABASE_ANON_KEY,
  ),
  VITE_CAMPAIGN_DB_REFRESH_ENABLED: firstValue(
    processEnv.NEXT_PUBLIC_CAMPAIGN_DB_REFRESH_ENABLED,
    processEnv.VITE_CAMPAIGN_DB_REFRESH_ENABLED,
    viteEnv.VITE_CAMPAIGN_DB_REFRESH_ENABLED,
  ),
  VITE_KAKAO_MAP_APP_KEY: firstValue(
    processEnv.NEXT_PUBLIC_KAKAO_MAP_APP_KEY,
    processEnv.VITE_KAKAO_MAP_APP_KEY,
    viteEnv.VITE_KAKAO_MAP_APP_KEY,
  ),
  VITE_PUBLIC_SITE_NAME: firstValue(
    processEnv.NEXT_PUBLIC_PUBLIC_SITE_NAME,
    processEnv.VITE_PUBLIC_SITE_NAME,
    viteEnv.VITE_PUBLIC_SITE_NAME,
  ),
  VITE_PUBLIC_SITE_URL: firstValue(
    processEnv.NEXT_PUBLIC_PUBLIC_SITE_URL,
    processEnv.VITE_PUBLIC_SITE_URL,
    viteEnv.VITE_PUBLIC_SITE_URL,
  ),
  VITE_PUBLIC_CONTACT_EMAIL: firstValue(
    processEnv.NEXT_PUBLIC_PUBLIC_CONTACT_EMAIL,
    processEnv.VITE_PUBLIC_CONTACT_EMAIL,
    viteEnv.VITE_PUBLIC_CONTACT_EMAIL,
  ),
  VITE_PUBLIC_OPERATOR_NAME: firstValue(
    processEnv.NEXT_PUBLIC_PUBLIC_OPERATOR_NAME,
    processEnv.VITE_PUBLIC_OPERATOR_NAME,
    viteEnv.VITE_PUBLIC_OPERATOR_NAME,
  ),
  VITE_ADSENSE_CLIENT: firstValue(processEnv.NEXT_PUBLIC_ADSENSE_CLIENT, processEnv.VITE_ADSENSE_CLIENT, viteEnv.VITE_ADSENSE_CLIENT),
  VITE_ADSENSE_ENABLE_LOCAL: firstValue(
    processEnv.NEXT_PUBLIC_ADSENSE_ENABLE_LOCAL,
    processEnv.VITE_ADSENSE_ENABLE_LOCAL,
    viteEnv.VITE_ADSENSE_ENABLE_LOCAL,
  ),
  VITE_ADSENSE_HOME_TOP_SLOT: firstValue(
    processEnv.NEXT_PUBLIC_ADSENSE_HOME_TOP_SLOT,
    processEnv.VITE_ADSENSE_HOME_TOP_SLOT,
    viteEnv.VITE_ADSENSE_HOME_TOP_SLOT,
  ),
  VITE_ADSENSE_EXPLORE_INLINE_SLOT: firstValue(
    processEnv.NEXT_PUBLIC_ADSENSE_EXPLORE_INLINE_SLOT,
    processEnv.VITE_ADSENSE_EXPLORE_INLINE_SLOT,
    viteEnv.VITE_ADSENSE_EXPLORE_INLINE_SLOT,
  ),
  VITE_ADSENSE_MAP_BOTTOM_SLOT: firstValue(
    processEnv.NEXT_PUBLIC_ADSENSE_MAP_BOTTOM_SLOT,
    processEnv.VITE_ADSENSE_MAP_BOTTOM_SLOT,
    viteEnv.VITE_ADSENSE_MAP_BOTTOM_SLOT,
  ),
  VITE_ADSENSE_HOME_TOP_CHANNEL: firstValue(
    processEnv.NEXT_PUBLIC_ADSENSE_HOME_TOP_CHANNEL,
    processEnv.VITE_ADSENSE_HOME_TOP_CHANNEL,
    viteEnv.VITE_ADSENSE_HOME_TOP_CHANNEL,
  ),
  VITE_ADSENSE_EXPLORE_INLINE_CHANNEL: firstValue(
    processEnv.NEXT_PUBLIC_ADSENSE_EXPLORE_INLINE_CHANNEL,
    processEnv.VITE_ADSENSE_EXPLORE_INLINE_CHANNEL,
    viteEnv.VITE_ADSENSE_EXPLORE_INLINE_CHANNEL,
  ),
  VITE_ADSENSE_MAP_BOTTOM_CHANNEL: firstValue(
    processEnv.NEXT_PUBLIC_ADSENSE_MAP_BOTTOM_CHANNEL,
    processEnv.VITE_ADSENSE_MAP_BOTTOM_CHANNEL,
    viteEnv.VITE_ADSENSE_MAP_BOTTOM_CHANNEL,
  ),
};

export const publicEnv = {
  raw,
  isProduction: processEnv.NODE_ENV === "production" || viteEnv.PROD === true,
  supabaseUrl: raw.VITE_SUPABASE_URL,
  supabaseAnonKey: raw.VITE_SUPABASE_ANON_KEY,
  campaignDbRefreshEnabled: raw.VITE_CAMPAIGN_DB_REFRESH_ENABLED,
  kakaoMapAppKey: raw.VITE_KAKAO_MAP_APP_KEY,
  publicSiteName: raw.VITE_PUBLIC_SITE_NAME,
  publicSiteUrl: raw.VITE_PUBLIC_SITE_URL,
  publicContactEmail: raw.VITE_PUBLIC_CONTACT_EMAIL,
  publicOperatorName: raw.VITE_PUBLIC_OPERATOR_NAME,
  adsenseClient: raw.VITE_ADSENSE_CLIENT,
  adsenseEnableLocal: raw.VITE_ADSENSE_ENABLE_LOCAL,
  adsenseSlots: {
    home_top: raw.VITE_ADSENSE_HOME_TOP_SLOT,
    explore_inline: raw.VITE_ADSENSE_EXPLORE_INLINE_SLOT,
    map_bottom: raw.VITE_ADSENSE_MAP_BOTTOM_SLOT,
  },
  adsenseChannels: {
    home_top: raw.VITE_ADSENSE_HOME_TOP_CHANNEL,
    explore_inline: raw.VITE_ADSENSE_EXPLORE_INLINE_CHANNEL,
    map_bottom: raw.VITE_ADSENSE_MAP_BOTTOM_CHANNEL,
  },
};

import assert from "node:assert/strict";

process.env.NEXT_PUBLIC_SUPABASE_URL = "https://next-ref.supabase.co";
process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "next-anon";
process.env.NEXT_PUBLIC_CAMPAIGN_DB_REFRESH_ENABLED = "0";
process.env.NEXT_PUBLIC_PUBLIC_SITE_NAME = "CheheomMoa";
process.env.NEXT_PUBLIC_PUBLIC_SITE_URL = "https://cheheommoa.com";
process.env.NEXT_PUBLIC_KAKAO_MAP_APP_KEY = "next-kakao";
process.env.NEXT_PUBLIC_ADSENSE_CLIENT = "ca-pub-next";
process.env.NEXT_PUBLIC_ADSENSE_ENABLE_LOCAL = "1";
process.env.NEXT_PUBLIC_ADSENSE_HOME_TOP_SLOT = "home";
process.env.NEXT_PUBLIC_ADSENSE_EXPLORE_INLINE_SLOT = "explore";
process.env.NEXT_PUBLIC_ADSENSE_MAP_BOTTOM_SLOT = "map";

const { publicEnv } = await import("../../src/shared/config/publicEnv.js");

assert.equal(publicEnv.supabaseUrl, "https://next-ref.supabase.co");
assert.equal(publicEnv.supabaseAnonKey, "next-anon");
assert.equal(publicEnv.campaignDbRefreshEnabled, "0");
assert.equal(publicEnv.publicSiteUrl, "https://cheheommoa.com");
assert.equal(publicEnv.kakaoMapAppKey, "next-kakao");
assert.equal(publicEnv.adsenseClient, "ca-pub-next");
assert.equal(publicEnv.adsenseEnableLocal, "1");
assert.equal(publicEnv.adsenseSlots.home_top, "home");
assert.equal(publicEnv.raw.VITE_CAMPAIGN_DB_REFRESH_ENABLED, "0");

console.log(JSON.stringify({ ok: true }));

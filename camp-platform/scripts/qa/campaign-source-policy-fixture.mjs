import assert from "node:assert/strict";

const {
  shouldUseSupabaseCampaignSource,
} = await import("../../src/features/campaigns/lib/campaignSourcePolicy.js");

assert.equal(typeof shouldUseSupabaseCampaignSource, "function");

assert.equal(
  shouldUseSupabaseCampaignSource({
    isSupabaseConfigured: true,
    env: {},
  }),
  false,
  "Supabase campaign reads must stay off by default to avoid free-tier egress drain",
);

assert.equal(
  shouldUseSupabaseCampaignSource({
    isSupabaseConfigured: true,
    env: { VITE_CAMPAIGN_DB_REFRESH_ENABLED: "1" },
  }),
  true,
  "Supabase campaign reads can be explicitly enabled for DB-backed operation",
);

assert.equal(
  shouldUseSupabaseCampaignSource({
    isSupabaseConfigured: true,
    env: { VITE_CAMPAIGN_DB_REFRESH_ENABLED: "true" },
  }),
  true,
  "Boolean-like env values should also enable DB-backed campaign reads",
);

assert.equal(
  shouldUseSupabaseCampaignSource({
    isSupabaseConfigured: false,
    env: { VITE_CAMPAIGN_DB_REFRESH_ENABLED: "1" },
  }),
  false,
  "Missing Supabase config must keep DB-backed campaign reads disabled",
);

console.log(JSON.stringify({ ok: true }, null, 2));

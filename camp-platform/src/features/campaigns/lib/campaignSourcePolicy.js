function isEnabledFlag(value) {
  return ["1", "true", "yes", "on"].includes(String(value || "").trim().toLowerCase());
}

function shouldUseSupabaseCampaignSource({ isSupabaseConfigured = false, env = {} } = {}) {
  return Boolean(isSupabaseConfigured && isEnabledFlag(env.VITE_CAMPAIGN_DB_REFRESH_ENABLED));
}

export {
  shouldUseSupabaseCampaignSource,
};

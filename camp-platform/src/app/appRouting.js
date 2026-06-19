const APP_TABS = ["home", "map", "explore", "status", "profile"];

function normalizeAppTab(value = "", { showOps = false } = {}) {
  const normalized = String(value || "").trim().toLowerCase();
  const allowedTabs = showOps ? [...APP_TABS, "ops"] : APP_TABS;
  return allowedTabs.includes(normalized) ? normalized : "home";
}

export { APP_TABS, normalizeAppTab };

const fs = require("fs");
const path = require("path");
const axios = require("axios");
const cheerio = require("cheerio");
const { createClient } = require("@supabase/supabase-js");

process.env.CRAWLER_TEST_EXPORTS = "1";
const { extractDinnerqueenProvisionFromDetail } = require("./crawl.cjs");

const PROJECT_ROOT = path.resolve(__dirname, "..", "..");
const PUBLIC_CAMPAIGNS_PATH = path.join(PROJECT_ROOT, "public", "campaigns.json");
const DEFAULT_USER_AGENT =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36";

function loadDotEnv() {
  const envPath = path.join(PROJECT_ROOT, ".env");
  if (!fs.existsSync(envPath)) return;

  const lines = fs.readFileSync(envPath, "utf8").split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const match = trimmed.match(/^([^=]+)=(.*)$/);
    if (!match) continue;

    const key = match[1].trim();
    if (process.env[key] !== undefined) continue;
    const value = match[2].trim().replace(/^["']|["']$/g, "");
    process.env[key] = value;
  }
}

function hasArg(name) {
  return process.argv.includes(name);
}

function envFlag(name) {
  return ["1", "true", "yes", "on"].includes(String(process.env[name] || "").trim().toLowerCase());
}

function envNumber(name, fallback) {
  const value = Number(process.env[name]);
  return Number.isFinite(value) ? value : fallback;
}

function cleanText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function writeJsonAtomic(filePath, payload) {
  const tempPath = `${filePath}.tmp`;
  fs.writeFileSync(tempPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  fs.renameSync(tempPath, filePath);
}

async function fetchProvision(campaign, timeoutMs) {
  const response = await axios.get(campaign.url, {
    timeout: timeoutMs,
    responseType: "text",
    headers: {
      "User-Agent": process.env.DINNERQUEEN_USER_AGENT || DEFAULT_USER_AGENT,
      Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      Referer: "https://dinnerqueen.net/taste",
      ...(process.env.DINNERQUEEN_COOKIE ? { Cookie: process.env.DINNERQUEEN_COOKIE } : {}),
    },
    validateStatus: (status) => status >= 200 && status < 400,
  });

  const $ = cheerio.load(response.data);
  return cleanText(extractDinnerqueenProvisionFromDetail($));
}

function isBackfillClosedCampaign(campaign) {
  const dDay = Number(campaign?.dDay);
  if (Number.isFinite(dDay) && dDay < 0) return true;

  const status = cleanText(campaign?.status).toLowerCase();
  return status === "closed" || status === "ended" || status === "expired" || status.includes("마감");
}

function compareBackfillCandidates(left, right) {
  const leftClosed = isBackfillClosedCampaign(left) ? 1 : 0;
  const rightClosed = isBackfillClosedCampaign(right) ? 1 : 0;
  if (leftClosed !== rightClosed) return leftClosed - rightClosed;

  const leftHasPoint = cleanText(left?.point) ? 1 : 0;
  const rightHasPoint = cleanText(right?.point) ? 1 : 0;
  if (leftHasPoint !== rightHasPoint) return leftHasPoint - rightHasPoint;

  const leftDDay = Number(left?.dDay);
  const rightDDay = Number(right?.dDay);
  const normalizedLeftDDay = Number.isFinite(leftDDay) && leftDDay >= 0 ? leftDDay : 999;
  const normalizedRightDDay = Number.isFinite(rightDDay) && rightDDay >= 0 ? rightDDay : 999;
  if (normalizedLeftDDay !== normalizedRightDDay) return normalizedLeftDDay - normalizedRightDDay;

  return Number(left?.applyCount || 0) - Number(right?.applyCount || 0);
}

function selectCampaigns(snapshot, { recheckAll, limit }) {
  const campaigns = Array.isArray(snapshot.campaigns) ? snapshot.campaigns : [];
  const candidates = campaigns
    .filter((campaign) => campaign.platformId === "dinner")
    .filter((campaign) => recheckAll || !cleanText(campaign.point))
    .filter((campaign) => cleanText(campaign.url))
    .sort(compareBackfillCandidates);

  return limit > 0 ? candidates.slice(0, limit) : candidates;
}

function buildDinnerqueenProvisionBackfillPlan(snapshot, { recheckAll = false, limit = 25 } = {}) {
  const campaigns = Array.isArray(snapshot.campaigns) ? snapshot.campaigns : [];
  const dinnerCampaigns = campaigns.filter((campaign) => campaign.platformId === "dinner");
  const pointFilled = dinnerCampaigns.filter((campaign) => cleanText(campaign.point)).length;
  const selectable = selectCampaigns(snapshot, { recheckAll, limit: 0 }).length;
  const selected = selectCampaigns(snapshot, { recheckAll, limit }).length;

  return {
    totalDinner: dinnerCampaigns.length,
    pointFilled,
    pointEmpty: dinnerCampaigns.length - pointFilled,
    withUrl: dinnerCampaigns.filter((campaign) => cleanText(campaign.url)).length,
    selectable,
    selected,
    limit,
    recheckAll,
  };
}
function buildExistingDinnerqueenPointUpdates(snapshot, { limit = 0 } = {}) {
  const campaigns = Array.isArray(snapshot.campaigns) ? snapshot.campaigns : [];
  const updates = campaigns
    .filter((campaign) => campaign.platformId === "dinner")
    .filter((campaign) => cleanText(campaign.id) && cleanText(campaign.point) && cleanText(campaign.url))
    .sort(compareBackfillCandidates)
    .map((campaign) => ({
      id: campaign.id,
      campaign,
      point: cleanText(campaign.point),
    }));

  return limit > 0 ? updates.slice(0, limit) : updates;
}

function applyPublicUpdates(snapshot, updates) {
  const byId = new Map(updates.map((update) => [update.id, update.point]));
  let changed = 0;

  snapshot.campaigns = (snapshot.campaigns || []).map((campaign) => {
    if (campaign.platformId !== "dinner" || !byId.has(campaign.id)) return campaign;
    const point = byId.get(campaign.id);
    if (cleanText(campaign.point) === point) return campaign;
    changed += 1;
    return { ...campaign, point };
  });

  if (changed > 0) {
    snapshot.updatedAt = new Date().toISOString();
  }

  return changed;
}

function mapForSupabase(update) {
  const { campaign, point } = update;
  return {
    platform_id: "dinner",
    external_id: campaign.id,
    source_url: campaign.url,
    title: campaign.title,
    campaign_type: campaign.type || "visit",
    category: campaign.category || null,
    reward_text: point,
    apply_count: campaign.applyCount || 0,
    selected_count: campaign.selectedCount || 0,
    d_day: campaign.dDay ?? 99,
    status: campaign.status || "open",
    crawled_at: campaign.crawledAt || new Date().toISOString(),
  };
}

async function syncSupabase(updates, batchSize) {
  const supabaseUrl = process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!supabaseUrl || !serviceRoleKey) {
    throw new Error("SUPABASE_URL/VITE_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for Supabase sync.");
  }

  const supabase = createClient(supabaseUrl, serviceRoleKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });

  let synced = 0;
  for (let index = 0; index < updates.length; index += batchSize) {
    const batch = updates.slice(index, index + batchSize).map(mapForSupabase);
    const { error } = await supabase
      .from("campaigns")
      .upsert(batch, { onConflict: "platform_id,external_id" });
    if (error) throw error;
    synced += batch.length;
    console.log(`  - supabase synced ${synced}/${updates.length}`);
  }

  return synced;
}

async function main() {
  loadDotEnv();

  const writePublic = hasArg("--write-public") || envFlag("DINNERQUEEN_PROVISION_BACKFILL_WRITE_PUBLIC");
  const syncDb = hasArg("--sync-supabase") || envFlag("DINNERQUEEN_PROVISION_BACKFILL_SYNC_SUPABASE");
  const syncExistingPublic = hasArg("--sync-existing-public") || envFlag("DINNERQUEEN_PROVISION_BACKFILL_SYNC_EXISTING_PUBLIC");
  const recheckAll = hasArg("--recheck-all") || envFlag("DINNERQUEEN_PROVISION_BACKFILL_RECHECK_ALL");
  const planOnly = hasArg("--plan-only") || envFlag("DINNERQUEEN_PROVISION_BACKFILL_PLAN_ONLY");
  const limit = Math.max(0, envNumber("DINNERQUEEN_PROVISION_BACKFILL_LIMIT", 25));
  const concurrency = Math.max(1, envNumber("DINNERQUEEN_PROVISION_BACKFILL_CONCURRENCY", 4));
  const timeoutMs = Math.max(5000, envNumber("DINNERQUEEN_PROVISION_BACKFILL_TIMEOUT_MS", 15000));
  const batchDelayMs = Math.max(0, envNumber("DINNERQUEEN_PROVISION_BACKFILL_BATCH_DELAY_MS", 500));
  const saveEvery = Math.max(1, envNumber("DINNERQUEEN_PROVISION_BACKFILL_SAVE_EVERY", 50));
  const supabaseBatchSize = Math.max(1, envNumber("SUPABASE_BATCH_SIZE", 100));

  const snapshot = readJson(PUBLIC_CAMPAIGNS_PATH);
  const selected = selectCampaigns(snapshot, { recheckAll, limit });
  const plan = buildDinnerqueenProvisionBackfillPlan(snapshot, { recheckAll, limit });
  const updates = [];
  const failures = [];
  let appliedUpdateCount = 0;
  let publicChanged = 0;

  console.log(JSON.stringify({
    mode: writePublic || syncDb ? "write-enabled" : "dry-run",
    selected: selected.length,
    limit,
    concurrency,
    timeoutMs,
    writePublic,
    syncSupabase: syncDb,
    syncExistingPublic,
    recheckAll,
    planOnly,
    plan,
  }, null, 2));

  if (planOnly) {
    console.log(JSON.stringify({ ok: true, planOnly: true, ...plan }, null, 2));
    return;
  }

  if (syncExistingPublic) {
    const existingUpdates = buildExistingDinnerqueenPointUpdates(snapshot, { limit });
    const synced = syncDb && existingUpdates.length > 0
      ? await syncSupabase(existingUpdates, supabaseBatchSize)
      : 0;
    console.log(JSON.stringify({
      ok: true,
      syncExistingPublic: true,
      selected: existingUpdates.length,
      extracted: existingUpdates.length,
      failed: 0,
      publicChanged: 0,
      supabaseSynced: synced,
      failures: [],
    }, null, 2));
    return;
  }

  for (let index = 0; index < selected.length; index += concurrency) {
    const batch = selected.slice(index, index + concurrency);
    const results = await Promise.all(batch.map(async (campaign) => {
      try {
        const point = await fetchProvision(campaign, timeoutMs);
        return { ok: true, campaign, point };
      } catch (error) {
        return { ok: false, campaign, error: error.message || String(error) };
      }
    }));

    for (const result of results) {
      if (!result.ok) {
        failures.push({ id: result.campaign.id, url: result.campaign.url, error: result.error });
        continue;
      }
      if (!result.point) continue;

      const update = { id: result.campaign.id, campaign: result.campaign, point: result.point };
      updates.push(update);
      console.log(`  - ${result.campaign.id}: ${result.point}`);
    }

    if (writePublic) {
      const pendingUpdates = updates.slice(appliedUpdateCount);
      if (pendingUpdates.length >= saveEvery) {
        const changed = applyPublicUpdates(snapshot, pendingUpdates);
        appliedUpdateCount = updates.length;
        publicChanged += changed;
        writeJsonAtomic(PUBLIC_CAMPAIGNS_PATH, snapshot);
        console.log(`  - public snapshot checkpoint saved (${publicChanged} updates)`);
      }
    }

    console.log(`  - checked ${Math.min(index + concurrency, selected.length)}/${selected.length}`);
    if (batchDelayMs > 0 && index + concurrency < selected.length) {
      await sleep(batchDelayMs);
    }
  }

  if (writePublic) {
    const changed = applyPublicUpdates(snapshot, updates.slice(appliedUpdateCount));
    publicChanged += changed;
    if (changed > 0) {
      writeJsonAtomic(PUBLIC_CAMPAIGNS_PATH, snapshot);
    }
  }

  const synced = syncDb && updates.length > 0
    ? await syncSupabase(updates, supabaseBatchSize)
    : 0;

  console.log(JSON.stringify({
    ok: true,
    selected: selected.length,
    extracted: updates.length,
    failed: failures.length,
    publicChanged,
    supabaseSynced: synced,
    failures: failures.slice(0, 10),
  }, null, 2));
}

if (process.env.DINNERQUEEN_BACKFILL_TEST_EXPORTS === "1") {
  module.exports = {
    buildDinnerqueenProvisionBackfillPlan,
    buildExistingDinnerqueenPointUpdates,
    selectCampaigns,
  };
} else {
  main().catch((error) => {
    console.error(error.message || error);
    process.exit(1);
  });
}

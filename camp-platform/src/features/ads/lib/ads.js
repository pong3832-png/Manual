import { isSupabaseConfigured, supabase } from "../../../shared/api/supabase";

const LEGACY_AD_EVENT_STORAGE_KEY = "cheommoa_ad_events";
const LEGACY_AD_ROTATION_SALT_STORAGE_KEY = "cheommoa_ad_rotation_salt";
const AD_EVENT_STORAGE_KEY = "cheheommoa_ad_events";
const AD_ROTATION_SALT_STORAGE_KEY = "cheheommoa_ad_rotation_salt";
const AD_INTEREST_STORAGE_KEY = "cheheommoa_ad_interests";
const MAX_LOCAL_EVENTS = 200;
const MAX_INTEREST_ITEMS = 12;
const AD_INTEREST_MAX_AGE_MS = 1000 * 60 * 60 * 24 * 30;
const RECENT_IMPRESSION_LIMIT = 6;
const ROTATION_BUCKET_MS = 1000 * 60 * 60 * 6;

function nowIso() {
  return new Date().toISOString();
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function getEventId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return `ad_evt_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function normalizeTarget(value) {
  const text = String(value || "").trim();
  return text || "전체";
}

function isAllTarget(value) {
  const text = normalizeTarget(value).toLowerCase();
  return ["전체", "all", "*", "any"].includes(text);
}

function normalizeInterestTarget(value) {
  const text = normalizeTarget(value);
  return isAllTarget(text) ? "" : text;
}

function matchesTarget(adValue, contextValue) {
  const adTarget = normalizeTarget(adValue);
  if (isAllTarget(adTarget)) return true;
  return adTarget === normalizeTarget(contextValue);
}

function isAdCurrentlyActive(ad, now = new Date()) {
  if (!ad?.enabled) return false;
  if (!ad.targetUrl) return false;

  const startsAt = ad.startAt ? Date.parse(ad.startAt) : null;
  const endsAt = ad.endAt ? Date.parse(ad.endAt) : null;
  const timestamp = now.getTime();

  if (Number.isFinite(startsAt) && timestamp < startsAt) return false;
  if (Number.isFinite(endsAt) && timestamp > endsAt) return false;
  return true;
}

function adMatchesContext(ad, context = {}) {
  return matchesTarget(ad.targetCategory, context.category)
    && matchesTarget(ad.targetRegion, context.province || context.region);
}

function isExactTarget(adValue, contextValue) {
  if (!contextValue) return false;
  const adTarget = normalizeTarget(adValue);
  return !isAllTarget(adTarget) && adTarget === normalizeTarget(contextValue);
}

function normalizeAd(ad) {
  return {
    id: String(ad.id || ""),
    slotId: String(ad.slotId || ""),
    provider: String(ad.provider || "direct"),
    enabled: Boolean(ad.enabled),
    label: String(ad.label || "광고"),
    sponsorName: String(ad.sponsorName || ""),
    title: String(ad.title || ""),
    description: String(ad.description || ""),
    cta: String(ad.cta || "자세히 보기"),
    targetUrl: String(ad.targetUrl || ""),
    imageUrl: String(ad.imageUrl || ""),
    disclosure: String(ad.disclosure || ""),
    startAt: ad.startAt || null,
    endAt: ad.endAt || null,
    priority: Number(ad.priority || 0),
    targetCategory: normalizeTarget(ad.targetCategory),
    targetRegion: normalizeTarget(ad.targetRegion),
  };
}

function stableHash(value) {
  let hash = 2166136261;
  const text = String(value);
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function getClientRotationSalt() {
  if (typeof localStorage === "undefined") return "default";

  try {
    const current = localStorage.getItem(AD_ROTATION_SALT_STORAGE_KEY);
    if (current) return current;

    const legacy = localStorage.getItem(LEGACY_AD_ROTATION_SALT_STORAGE_KEY);
    if (legacy) {
      localStorage.setItem(AD_ROTATION_SALT_STORAGE_KEY, legacy);
      return legacy;
    }

    const next = getEventId();
    localStorage.setItem(AD_ROTATION_SALT_STORAGE_KEY, next);
    return next;
  } catch {
    return "default";
  }
}

function getRotationBucket(now = Date.now()) {
  return Math.floor(now / ROTATION_BUCKET_MS);
}

function readAdInterestState() {
  if (typeof localStorage === "undefined") return { categories: {}, regions: {} };

  try {
    const parsed = JSON.parse(localStorage.getItem(AD_INTEREST_STORAGE_KEY) || "{}");
    return {
      categories: parsed?.categories && typeof parsed.categories === "object" ? parsed.categories : {},
      regions: parsed?.regions && typeof parsed.regions === "object" ? parsed.regions : {},
    };
  } catch {
    return { categories: {}, regions: {} };
  }
}

function pruneInterestBucket(bucket, nowMs = Date.now()) {
  return Object.fromEntries(
    Object.entries(bucket || {})
      .map(([value, item]) => [
        value,
        {
          score: Math.max(0, Number(item?.score || 0)),
          lastSeenAt: String(item?.lastSeenAt || ""),
        },
      ])
      .filter(([, item]) => {
        const timestamp = Date.parse(item.lastSeenAt);
        return Number.isFinite(timestamp) && nowMs - timestamp <= AD_INTEREST_MAX_AGE_MS;
      })
      .sort(([, left], [, right]) =>
        right.score - left.score || Date.parse(right.lastSeenAt) - Date.parse(left.lastSeenAt),
      )
      .slice(0, MAX_INTEREST_ITEMS),
  );
}

function writeAdInterestState(state) {
  if (typeof localStorage === "undefined") return;

  try {
    localStorage.setItem(AD_INTEREST_STORAGE_KEY, JSON.stringify({
      categories: pruneInterestBucket(state.categories),
      regions: pruneInterestBucket(state.regions),
      updatedAt: nowIso(),
    }));
  } catch {
    return;
  }
}

function bumpInterest(bucket, value, weight) {
  if (!value) return;
  const current = bucket[value] || { score: 0, lastSeenAt: "" };
  bucket[value] = {
    score: Math.min(100, Number(current.score || 0) + weight),
    lastSeenAt: nowIso(),
  };
}

function rememberAdContext(context = {}, weight = 1) {
  const category = normalizeInterestTarget(context.category);
  const region = normalizeInterestTarget(context.province || context.region);
  if (!category && !region) return;

  const state = readAdInterestState();
  bumpInterest(state.categories, category, weight);
  bumpInterest(state.regions, region, weight);
  writeAdInterestState(state);
}

function getTopInterest(bucket) {
  return Object.entries(pruneInterestBucket(bucket))
    .sort(([, left], [, right]) =>
      right.score - left.score || Date.parse(right.lastSeenAt) - Date.parse(left.lastSeenAt),
    )[0]?.[0] || "";
}

function getEffectiveAdContext(context = {}) {
  const state = readAdInterestState();
  const preferredCategory = getTopInterest(state.categories);
  const preferredRegion = getTopInterest(state.regions);
  const explicitCategory = normalizeInterestTarget(context.category);
  const explicitRegion = normalizeInterestTarget(context.province || context.region);

  return {
    ...context,
    category: explicitCategory || preferredCategory || context.category,
    province: explicitRegion || preferredRegion || context.province,
    region: explicitRegion || preferredRegion || context.region,
  };
}

function getContextSignature(context = {}) {
  return [
    context.page || "",
    normalizeTarget(context.category),
    normalizeTarget(context.province || context.region),
    normalizeTarget(context.city),
  ].join("|");
}

function getRecentImpressionIds(slotId) {
  return readLocalEvents()
    .filter((event) => event?.slot_id === slotId && event?.event_type === "impression")
    .map((event) => event.ad_id)
    .filter(Boolean)
    .slice(0, RECENT_IMPRESSION_LIMIT);
}

function getAdContextScore(ad, context = {}) {
  let score = ad.priority;
  if (isExactTarget(ad.targetCategory, context.category)) score += 30;
  if (isExactTarget(ad.targetRegion, context.province || context.region)) score += 20;
  return score;
}

function getRotationScore(ad, slotId, context = {}) {
  const seed = [
    getClientRotationSalt(),
    getRotationBucket(),
    slotId,
    getContextSignature(context),
    ad.id,
  ].join("|");
  return getAdContextScore(ad, context) + (stableHash(seed) / 0xffffffff);
}

function selectAdForSlot(ads, slotId, context = {}) {
  const effectiveContext = getEffectiveAdContext(context);
  const eligibleAds = safeArray(ads)
    .map(normalizeAd)
    .filter((ad) => ad.slotId === slotId)
    .filter((ad) => isAdCurrentlyActive(ad))
    .filter((ad) => adMatchesContext(ad, effectiveContext));

  if (eligibleAds.length <= 1) return eligibleAds[0] || null;

  const recentIds = new Set(getRecentImpressionIds(slotId));
  const rotationPool = eligibleAds.filter((ad) => !recentIds.has(ad.id));
  const candidates = rotationPool.length ? rotationPool : eligibleAds;

  return candidates
    .sort((left, right) =>
      getRotationScore(right, slotId, effectiveContext) - getRotationScore(left, slotId, effectiveContext)
      || left.id.localeCompare(right.id),
    )[0] || null;
}

function readLocalEvents() {
  try {
    const current = localStorage.getItem(AD_EVENT_STORAGE_KEY);
    if (current) return safeArray(JSON.parse(current));

    const legacy = localStorage.getItem(LEGACY_AD_EVENT_STORAGE_KEY);
    if (legacy) {
      localStorage.setItem(AD_EVENT_STORAGE_KEY, legacy);
      return safeArray(JSON.parse(legacy));
    }

    return [];
  } catch {
    return [];
  }
}

function summarizeAdEvents(events = readLocalEvents()) {
  const rowsBySlot = new Map();

  safeArray(events).forEach((event) => {
    const slotId = String(event?.slot_id || "unknown");
    const current = rowsBySlot.get(slotId) || {
      slotId,
      impressions: 0,
      clicks: 0,
      providers: new Set(),
      lastEventAt: "",
    };

    if (event.event_type === "impression") current.impressions += 1;
    if (event.event_type === "click") current.clicks += 1;
    if (event.provider) current.providers.add(event.provider);
    if (!current.lastEventAt || Date.parse(event.created_at) > Date.parse(current.lastEventAt)) {
      current.lastEventAt = event.created_at || "";
    }

    rowsBySlot.set(slotId, current);
  });

  const rows = [...rowsBySlot.values()]
    .map((row) => ({
      ...row,
      providers: [...row.providers].sort(),
      ctr: row.impressions > 0 ? row.clicks / row.impressions : 0,
    }))
    .sort((left, right) => right.impressions - left.impressions || left.slotId.localeCompare(right.slotId));

  return {
    totalEvents: safeArray(events).length,
    impressions: rows.reduce((sum, row) => sum + row.impressions, 0),
    clicks: rows.reduce((sum, row) => sum + row.clicks, 0),
    rows,
  };
}

function createEmptyAdSummary(extra = {}) {
  return {
    totalEvents: 0,
    impressions: 0,
    clicks: 0,
    rows: [],
    ...extra,
  };
}

function summarizeRemoteAdEventRows(rows = []) {
  const rowsBySlot = new Map();
  let totalEvents = 0;

  safeArray(rows).forEach((row) => {
    const slotId = String(row?.slot_id || "unknown");
    const provider = String(row?.provider || "unknown");
    const eventType = String(row?.event_type || "");
    const eventCount = Number(row?.event_count || 0);
    const current = rowsBySlot.get(slotId) || {
      slotId,
      impressions: 0,
      clicks: 0,
      providers: new Set(),
      lastEventAt: "",
    };

    totalEvents += eventCount;
    if (eventType === "impression") current.impressions += eventCount;
    if (eventType === "click") current.clicks += eventCount;
    current.providers.add(provider);
    if (!current.lastEventAt || Date.parse(row.last_event_at) > Date.parse(current.lastEventAt)) {
      current.lastEventAt = row.last_event_at || "";
    }

    rowsBySlot.set(slotId, current);
  });

  const summaryRows = [...rowsBySlot.values()]
    .map((row) => ({
      ...row,
      providers: [...row.providers].sort(),
      ctr: row.impressions > 0 ? row.clicks / row.impressions : 0,
    }))
    .sort((left, right) => right.impressions - left.impressions || left.slotId.localeCompare(right.slotId));

  return {
    totalEvents,
    impressions: summaryRows.reduce((sum, row) => sum + row.impressions, 0),
    clicks: summaryRows.reduce((sum, row) => sum + row.clicks, 0),
    rows: summaryRows,
  };
}

async function fetchRemoteAdEventSummary(lookbackDays = 30) {
  if (!isSupabaseConfigured) {
    return createEmptyAdSummary({ error: "Supabase 설정 없음" });
  }

  try {
    const { data, error } = await supabase.rpc("get_ad_event_summary", {
      lookback_days: lookbackDays,
    });

    if (error) throw error;
    return summarizeRemoteAdEventRows(data);
  } catch (error) {
    return createEmptyAdSummary({ error: error.message || "Supabase 광고 집계 조회 실패" });
  }
}

function writeLocalEvent(event) {
  if (typeof localStorage === "undefined") return;
  const events = [event, ...readLocalEvents()].slice(0, MAX_LOCAL_EVENTS);
  localStorage.setItem(AD_EVENT_STORAGE_KEY, JSON.stringify(events));
}

function createAdEvent(ad, slotId, eventType, metadata = {}) {
  return {
    id: getEventId(),
    ad_id: ad.id,
    slot_id: slotId,
    provider: ad.provider,
    event_type: eventType,
    page_path: `${window.location.pathname}${window.location.search}${window.location.hash}`,
    target_url: ad.targetUrl,
    metadata,
    created_at: nowIso(),
  };
}

function trackAdEvent(ad, slotId, eventType, metadata = {}) {
  if (!ad?.id || !slotId || !eventType) return;
  if (eventType === "click") {
    rememberAdContext(metadata.context, 3);
  }

  const event = createAdEvent(ad, slotId, eventType, metadata);
  writeLocalEvent(event);

  supabase
    .from("ad_events")
    .insert({
      id: event.id,
      ad_id: event.ad_id,
      slot_id: event.slot_id,
      provider: event.provider,
      event_type: event.event_type,
      page_path: event.page_path,
      target_url: event.target_url,
      metadata: event.metadata,
      created_at: event.created_at,
    })
    .then(() => null);
}

export {
  AD_EVENT_STORAGE_KEY,
  AD_ROTATION_SALT_STORAGE_KEY,
  fetchRemoteAdEventSummary,
  rememberAdContext,
  normalizeAd,
  selectAdForSlot,
  summarizeAdEvents,
  trackAdEvent,
};

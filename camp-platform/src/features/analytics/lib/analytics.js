import { isSupabaseConfigured, supabase } from "../../../shared/api/supabase.js";

const ANALYTICS_ANONYMOUS_ID_STORAGE_KEY = "cheheommoa_analytics_anonymous_id";
const ANALYTICS_SESSION_ID_STORAGE_KEY = "cheheommoa_analytics_session_id";
const ANALYTICS_OPT_OUT_STORAGE_KEY = "cheheommoa_analytics_opt_out";
const ANALYTICS_TRAFFIC_SOURCE_SESSION_KEY = "cheheommoa_analytics_traffic_source_session";
const MAX_METADATA_STRING_LENGTH = 120;
const REDACTED_METADATA_VALUE = "[redacted]";
const SAFE_SENSITIVE_KEY_METRICS = new Set([
  "hassearch",
  "searchlength",
  "previoushasreviewurl",
  "nexthasreviewurl",
]);
const SENSITIVE_METADATA_KEY_PATTERN = /(^|[_-])(?:q|query|keyword|password|pass|token|secret|cookie|authorization|email|phone|tel|url|href)(?:[_-]|$)|rawsearch|accesstoken|refreshtoken|idtoken|authtoken|reviewurl/i;

const ANALYTICS_EVENT_LABELS = {
  tab_view: "탭 보기",
  home_discovery_click: "홈 탐색 클릭",
  category_filter: "카테고리 필터",
  region_filter: "지역 필터",
  search_filter: "검색 사용",
  preset_filter: "빠른 탐색",
  sort_filter: "정렬 변경",
  filter_reset: "필터 초기화",
  campaign_impression: "캠페인 노출",
  campaign_open: "상세 열기",
  favorite_add: "즐겨찾기 추가",
  favorite_remove: "즐겨찾기 제거",
  apply_click: "신청 버튼",
  application_status_update: "지원 상태 변경",
  application_memo_update: "지원 메모 변경",
  application_review_url_update: "리뷰 URL 변경",
  map_filter: "지도 필터",
  map_pin_open: "지도 핀 열기",
  map_cluster_interaction: "지도 클러스터",
  traffic_source: "유입 출처",
  market_report_create: "리포트 생성",
  market_report_download: "리포트 다운로드",
  legal_open: "정책 열기",
  analytics_opt_out: "분석 끄기",
  analytics_opt_in: "분석 켜기",
};

const ANALYTICS_TAB_LABELS = {
  home: "홈",
  map: "지도",
  explore: "탐색",
  status: "현황",
  ops: "운영",
  profile: "마이",
  unknown: "알 수 없음",
};
const ALLOWED_EVENT_TYPES = new Set([
  "tab_view",
  "home_discovery_click",
  "category_filter",
  "region_filter",
  "search_filter",
  "preset_filter",
  "sort_filter",
  "filter_reset",
  "campaign_impression",
  "campaign_open",
  "favorite_add",
  "favorite_remove",
  "apply_click",
  "application_status_update",
  "application_memo_update",
  "application_review_url_update",
  "map_filter",
  "map_pin_open",
  "map_cluster_interaction",
  "traffic_source",
  "market_report_create",
  "market_report_download",
  "legal_open",
  "analytics_opt_out",
  "analytics_opt_in",
]);

function getAllowedAnalyticsEventTypes() {
  return Array.from(ALLOWED_EVENT_TYPES);
}

function formatAnalyticsSummaryKey(row = {}) {
  if (row.type === "event_type") return ANALYTICS_EVENT_LABELS[row.key] || row.key;
  if (row.type === "tab") return ANALYTICS_TAB_LABELS[row.key] || row.key;
  if (row.type === "identity") return row.key === "logged_in" ? "로그인" : "비로그인";
  return row.key;
}
function getEventId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return `evt_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function safeStorageGet(key) {
  if (typeof localStorage === "undefined") return "";
  try {
    return localStorage.getItem(key) || "";
  } catch {
    return "";
  }
}

function safeStorageSet(key, value) {
  if (typeof localStorage === "undefined") return;
  try {
    localStorage.setItem(key, value);
  } catch {
    return;
  }
}

function getOrCreateStoredId(key, prefix) {
  const current = safeStorageGet(key);
  if (current) return current;

  const next = `${prefix}_${getEventId()}`;
  safeStorageSet(key, next);
  return next;
}

function getAnonymousId() {
  return getOrCreateStoredId(ANALYTICS_ANONYMOUS_ID_STORAGE_KEY, "anon");
}

function getSessionId() {
  return getOrCreateStoredId(ANALYTICS_SESSION_ID_STORAGE_KEY, "sess");
}

function normalizeText(value, maxLength = 80) {
  const text = String(value || "").trim();
  return text ? text.slice(0, maxLength) : null;
}

function isSensitiveMetadataKey(key) {
  const normalizedKey = String(key || "").replace(/[^a-z0-9_-]/gi, "").toLowerCase();
  if (!normalizedKey || SAFE_SENSITIVE_KEY_METRICS.has(normalizedKey)) return false;
  return SENSITIVE_METADATA_KEY_PATTERN.test(normalizedKey);
}

function normalizeMetadataValue(value, key = "") {
  if (value === null || value === undefined) return null;
  if (isSensitiveMetadataKey(key)) {
    if (typeof value === "boolean" || typeof value === "number") return value;
    return REDACTED_METADATA_VALUE;
  }
  if (typeof value === "boolean" || typeof value === "number") return value;
  if (typeof value === "string") return value.slice(0, MAX_METADATA_STRING_LENGTH);
  if (Array.isArray(value)) return value.slice(0, 12).map((item) => normalizeMetadataValue(item, key));
  if (typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value)
        .slice(0, 24)
        .map(([nestedKey, item]) => {
          const normalizedKey = String(nestedKey).slice(0, 40);
          return [normalizedKey, normalizeMetadataValue(item, normalizedKey)];
        }),
    );
  }
  return String(value).slice(0, MAX_METADATA_STRING_LENGTH);
}

function normalizeMetadata(metadata = {}) {
  return Object.fromEntries(
    Object.entries(metadata || {})
      .filter(([, value]) => value !== undefined)
      .map(([key, value]) => {
        const normalizedKey = String(key).slice(0, 40);
        return [normalizedKey, normalizeMetadataValue(value, normalizedKey)];
      }),
  );
}

function getPagePath() {
  if (typeof window === "undefined") return "";
  try {
    const url = new URL(window.location.href);
    if (url.searchParams.has("q")) url.searchParams.set("q", "[search]");
    const safeHash = /access_token|refresh_token|id_token|code=/i.test(url.hash) ? "#auth" : url.hash;
    return `${url.pathname}${url.search}${safeHash}`.slice(0, 500);
  } catch {
    return String(window.location.pathname || "").slice(0, 500);
  }
}

function isAnalyticsOptedOut() {
  return safeStorageGet(ANALYTICS_OPT_OUT_STORAGE_KEY) === "1";
}

function setAnalyticsOptOut(isOptedOut) {
  safeStorageSet(ANALYTICS_OPT_OUT_STORAGE_KEY, isOptedOut ? "1" : "0");
}

function canTrackAnalyticsEvent(options = {}) {
  return !isAnalyticsOptedOut() || Boolean(options.ignoreOptOut);
}

function sanitizeSearchMetadata(search = "") {
  const text = String(search || "").trim();
  return {
    hasSearch: text.length > 0,
    searchLength: Math.min(text.length, 200),
  };
}

function sanitizeTrafficSourceMetadata() {
  if (typeof window === "undefined") return null;

  try {
    const url = new URL(window.location.href);
    const params = url.searchParams;
    const allowedParams = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "gclid", "fbclid"];
    const utm = Object.fromEntries(
      allowedParams
        .filter((key) => params.has(key))
        .map((key) => [key, String(params.get(key) || "").slice(0, 80)]),
    );
    const referrerHost = document.referrer ? new URL(document.referrer).host.slice(0, 120) : "";
    const hasExternalReferrer = Boolean(referrerHost && referrerHost !== url.host);

    if (!Object.keys(utm).length && !hasExternalReferrer) return null;

    return {
      hasUtm: Object.keys(utm).length > 0,
      utm,
      referrerHost: hasExternalReferrer ? referrerHost : "",
      landingPath: url.pathname.slice(0, 120),
    };
  } catch {
    return null;
  }
}

function trackTrafficSourceOnce(user = null) {
  const sessionId = getSessionId();
  if (safeStorageGet(ANALYTICS_TRAFFIC_SOURCE_SESSION_KEY) === sessionId) return;

  const metadata = sanitizeTrafficSourceMetadata();
  safeStorageSet(ANALYTICS_TRAFFIC_SOURCE_SESSION_KEY, sessionId);
  if (!metadata) return;

  trackAnalyticsEvent("traffic_source", { metadata }, user);
}

function createAnalyticsPayload(eventType, payload = {}, user = null) {
  if (!ALLOWED_EVENT_TYPES.has(eventType)) return null;

  return {
    id: getEventId(),
    event_type: eventType,
    user_id: user?.id || null,
    anonymous_id: getAnonymousId(),
    session_id: getSessionId(),
    page_path: getPagePath(),
    category: normalizeText(payload.category),
    region: normalizeText(payload.region || payload.province),
    city: normalizeText(payload.city),
    platform_id: normalizeText(payload.platformId || payload.platform_id),
    campaign_id: normalizeText(payload.campaignId || payload.campaign_id, 120),
    slot_id: normalizeText(payload.slotId || payload.slot_id, 80),
    metadata: normalizeMetadata(payload.metadata),
    created_at: new Date().toISOString(),
  };
}

function trackAnalyticsEvent(eventType, payload = {}, user = null, options = {}) {
  if (!isSupabaseConfigured) return;
  if (!canTrackAnalyticsEvent(options)) return;

  const eventPayload = createAnalyticsPayload(eventType, payload, user);
  if (!eventPayload) return;

  supabase
    .from("analytics_events")
    .insert(eventPayload)
    .then(() => null)
    .catch(() => null);
}

function createEmptyAnalyticsDashboardSummary(extra = {}) {
  return {
    totalEvents: 0,
    uniqueUsers: 0,
    uniqueBrowsers: 0,
    lastEventAt: "",
    eventRows: [],
    categoryRows: [],
    regionRows: [],
    platformRows: [],
    tabRows: [],
    identityRows: [],
    applyCampaignRows: [],
    openCampaignRows: [],
    error: "",
    ...extra,
  };
}

function normalizeSummaryRow(row = {}) {
  return {
    type: String(row.summary_type || ""),
    key: String(row.summary_key || "unknown"),
    eventType: String(row.event_type || "all"),
    count: Number(row.event_count || 0),
    uniqueUsers: Number(row.unique_users || 0),
    uniqueBrowsers: Number(row.unique_browsers || 0),
    lastEventAt: row.last_event_at || "",
  };
}

function rowsForType(rows, type, limit = 8) {
  return rows
    .filter((row) => row.type === type && row.key)
    .sort((left, right) => right.count - left.count || left.key.localeCompare(right.key))
    .slice(0, limit);
}

function summarizeAnalyticsDashboardRows(rows = []) {
  const normalizedRows = Array.isArray(rows) ? rows.map(normalizeSummaryRow) : [];
  const totalRow = normalizedRows.find((row) => row.type === "total") || {};

  return createEmptyAnalyticsDashboardSummary({
    totalEvents: Number(totalRow.count || 0),
    uniqueUsers: Number(totalRow.uniqueUsers || 0),
    uniqueBrowsers: Number(totalRow.uniqueBrowsers || 0),
    lastEventAt: totalRow.lastEventAt || "",
    eventRows: rowsForType(normalizedRows, "event_type", 12),
    categoryRows: rowsForType(normalizedRows, "category", 8),
    regionRows: rowsForType(normalizedRows, "region", 8),
    platformRows: rowsForType(normalizedRows, "platform", 8),
    tabRows: rowsForType(normalizedRows, "tab", 8),
    identityRows: rowsForType(normalizedRows, "identity", 4),
    applyCampaignRows: rowsForType(normalizedRows, "apply_campaign", 8),
    openCampaignRows: rowsForType(normalizedRows, "open_campaign", 8),
  });
}

const MARKET_REPORT_MIN_EVENTS = 20;
const MARKET_REPORT_MIN_BROWSERS = 5;
const MARKET_REPORT_ROW_GROUPS = [
  { key: "eventRows", label: "행동 유형" },
  { key: "categoryRows", label: "카테고리" },
  { key: "regionRows", label: "지역" },
  { key: "platformRows", label: "플랫폼" },
  { key: "tabRows", label: "탭" },
];

function getMarketReportCandidateRows(summary = {}, options = {}) {
  const formatKey = typeof options.formatKey === "function" ? options.formatKey : (row) => row.key;

  return MARKET_REPORT_ROW_GROUPS.flatMap((group) =>
    (summary[group.key] || []).map((row) => ({
      ...row,
      groupLabel: group.label,
      displayKey: formatKey(row),
    })),
  )
    .filter((row) =>
      Number(row.count || 0) >= MARKET_REPORT_MIN_EVENTS
      && Number(row.uniqueBrowsers || 0) >= MARKET_REPORT_MIN_BROWSERS,
    )
    .sort((left, right) => right.count - left.count || left.displayKey.localeCompare(right.displayKey))
    .slice(0, 10);
}

function getMarketReportReadiness(summary = {}, options = {}) {
  const candidateRows = getMarketReportCandidateRows(summary, options);
  const missingEvents = Math.max(0, MARKET_REPORT_MIN_EVENTS - Number(summary.totalEvents || 0));
  const missingBrowsers = Math.max(0, MARKET_REPORT_MIN_BROWSERS - Number(summary.uniqueBrowsers || 0));

  return {
    candidateRows,
    readySegmentCount: candidateRows.length,
    missingEvents,
    missingBrowsers,
    isReady: candidateRows.length > 0,
  };
}

function readMarketReportAuditNumber(value, fallback = 0) {
  if (value === null || value === undefined || value === "") return Number(fallback || 0);
  const nextValue = Number(value);
  return Number.isFinite(nextValue) ? nextValue : Number(fallback || 0);
}

function buildMarketReportBaseAuditMetadata(report = {}, options = {}) {
  return {
    reportId: String(report?.id || ""),
    reportStatus: String(report?.status || "empty"),
    rowCount: readMarketReportAuditNumber(report?.rowCount),
    totalEventCount: readMarketReportAuditNumber(report?.totalEventCount),
    totalUniqueBrowsers: readMarketReportAuditNumber(report?.totalUniqueBrowsers),
    lookbackDays: readMarketReportAuditNumber(report?.lookbackDays, options.lookbackDays),
    minEvents: readMarketReportAuditNumber(report?.minEvents, options.minEvents),
    minBrowsers: readMarketReportAuditNumber(report?.minBrowsers, options.minBrowsers),
  };
}

function buildMarketReportCreateAuditMetadata(report = {}, options = {}) {
  return {
    ...buildMarketReportBaseAuditMetadata(report, options),
    selectedItemCount: Array.isArray(options.selectedItems) ? options.selectedItems.length : 0,
  };
}

function buildMarketReportDownloadAuditMetadata(report = {}, items = []) {
  return {
    ...buildMarketReportBaseAuditMetadata(report),
    itemCount: Array.isArray(items) ? items.length : 0,
  };
}

function quoteMarketReportCsvValue(value) {
  const text = String(value ?? "");
  return `"${text.replace(/"/g, '""')}"`;
}

function buildMarketReportCsv(report, items = []) {
  const metadataRows = [
    ["report_id", report.id],
    ["title", report.title],
    ["status", report.status],
    ["generated_at", report.generatedAt],
    ["period_start", report.periodStart],
    ["period_end", report.periodEnd],
    ["lookback_days", report.lookbackDays],
    ["min_events", report.minEvents],
    ["min_browsers", report.minBrowsers],
    ["row_count", report.rowCount],
    ["total_event_count", report.totalEventCount],
    ["total_unique_browsers", report.totalUniqueBrowsers],
    ["export_policy_version", report.exportPolicyVersion],
  ];
  const itemHeader = [
    "rank",
    "report_type",
    "dimension_key",
    "metric_name",
    "metric_value",
    "event_count",
    "unique_browsers",
    "unique_users",
    "period_start",
    "period_end",
  ];
  const itemRows = items.map((item) => [
    item.rankPosition,
    item.reportType,
    item.dimensionKey,
    item.metricName,
    item.metricValue,
    item.eventCount,
    item.uniqueBrowsers,
    item.uniqueUsers,
    item.periodStart,
    item.periodEnd,
  ]);

  return [
    ...metadataRows,
    [],
    itemHeader,
    ...itemRows,
  ].map((row) => row.map(quoteMarketReportCsvValue).join(",")).join("\r\n");
}
function createEmptyAnalyticsMarketReportArchive(extra = {}) {
  return {
    reports: [],
    items: [],
    selectedReportId: "",
    error: "",
    ...extra,
  };
}

function normalizeMarketReport(row = {}) {
  return {
    id: String(row.id || ""),
    title: String(row.title || "Market report"),
    status: String(row.status || "empty"),
    lookbackDays: Number(row.lookback_days || 0),
    minEvents: Number(row.min_events || 0),
    minBrowsers: Number(row.min_browsers || 0),
    rowCount: Number(row.row_count || 0),
    totalEventCount: Number(row.total_event_count || 0),
    totalUniqueBrowsers: Number(row.total_unique_browsers || 0),
    periodStart: row.period_start || "",
    periodEnd: row.period_end || "",
    generatedAt: row.generated_at || "",
    generatedBy: row.generated_by || "",
    exportPolicyVersion: String(row.export_policy_version || ""),
    notes: String(row.notes || ""),
  };
}

function normalizeMarketReportItem(row = {}) {
  return {
    reportId: String(row.report_id || ""),
    reportType: String(row.report_type || ""),
    dimensionKey: String(row.dimension_key || ""),
    metricName: String(row.metric_name || ""),
    metricValue: Number(row.metric_value || 0),
    eventCount: Number(row.event_count || 0),
    uniqueBrowsers: Number(row.unique_browsers || 0),
    uniqueUsers: Number(row.unique_users || 0),
    periodStart: row.period_start || "",
    periodEnd: row.period_end || "",
    rankPosition: Number(row.rank_position || 0),
  };
}

function getMarketReportErrorMessage(error, fallback) {
  const message = error?.message || fallback;
  if (/admin access|required|permission|42501/i.test(message)) {
    return "시장 리포트 관리자 권한이 필요합니다. Supabase의 analytics_report_admins에 현재 사용자를 등록해야 합니다.";
  }
  return message;
}

async function fetchRemoteAnalyticsDashboardSummary(lookbackDays = 30, options = {}) {
  if (!isSupabaseConfigured) {
    return createEmptyAnalyticsDashboardSummary({ error: "Supabase 설정 없음" });
  }

  if (!options.user) {
    return createEmptyAnalyticsDashboardSummary({ error: "로그인 후 분석 요약을 볼 수 있습니다." });
  }

  try {
    const { data, error } = await supabase.rpc("get_analytics_dashboard_summary", {
      lookback_days: lookbackDays,
    });

    if (error) throw error;
    return summarizeAnalyticsDashboardRows(data);
  } catch (error) {
    return createEmptyAnalyticsDashboardSummary({
      error: error.message || "Supabase 분석 요약 조회 실패",
    });
  }
}

async function fetchRemoteAnalyticsMarketReportItems(reportId, options = {}) {
  if (!isSupabaseConfigured) {
    return { items: [], error: "Supabase 설정 없음" };
  }

  if (!options.user) {
    return { items: [], error: "로그인 후 저장된 리포트를 볼 수 있습니다." };
  }

  if (!reportId) return { items: [], error: "" };

  try {
    const { data, error } = await supabase.rpc("get_analytics_market_report_items", {
      target_report_id: reportId,
    });

    if (error) throw error;
    return { items: (data || []).map(normalizeMarketReportItem), error: "" };
  } catch (error) {
    return {
      items: [],
      error: getMarketReportErrorMessage(error, "저장된 시장 리포트 항목 조회 실패"),
    };
  }
}

async function fetchRemoteAnalyticsMarketReportArchive(options = {}) {
  if (!isSupabaseConfigured) {
    return createEmptyAnalyticsMarketReportArchive({ error: "Supabase 설정 없음" });
  }

  if (!options.user) {
    return createEmptyAnalyticsMarketReportArchive({ error: "로그인 후 저장된 리포트를 볼 수 있습니다." });
  }

  try {
    const { data, error } = await supabase.rpc("list_analytics_market_reports", {
      report_limit: options.limit || 8,
    });

    if (error) throw error;

    const reports = (data || []).map(normalizeMarketReport);
    const selectedReportId = reports[0]?.id || "";
    const itemsResult = selectedReportId
      ? await fetchRemoteAnalyticsMarketReportItems(selectedReportId, options)
      : { items: [], error: "" };

    return createEmptyAnalyticsMarketReportArchive({
      reports,
      items: itemsResult.items,
      selectedReportId,
      error: itemsResult.error,
    });
  } catch (error) {
    return createEmptyAnalyticsMarketReportArchive({
      error: getMarketReportErrorMessage(error, "저장된 시장 리포트 조회 실패"),
    });
  }
}

async function createRemoteAnalyticsMarketReport(options = {}) {
  if (!isSupabaseConfigured) {
    throw new Error("Supabase 설정 없음");
  }

  if (!options.user) {
    throw new Error("로그인 후 시장 리포트를 생성할 수 있습니다.");
  }

  try {
    const { data, error } = await supabase.rpc("create_analytics_market_report", {
      lookback_days: options.lookbackDays || 30,
      min_events: options.minEvents || 20,
      min_browsers: options.minBrowsers || 5,
      report_title: options.title || null,
      report_notes: options.notes || null,
    });

    if (error) throw error;

    const row = Array.isArray(data) ? data[0] : data;
    return {
      id: String(row?.report_id || ""),
      status: String(row?.report_status || "empty"),
      rowCount: Number(row?.report_row_count || 0),
      totalEventCount: Number(row?.total_event_count || 0),
      totalUniqueBrowsers: Number(row?.total_unique_browsers || 0),
      periodStart: row?.period_start || "",
      periodEnd: row?.period_end || "",
    };
  } catch (error) {
    throw new Error(getMarketReportErrorMessage(error, "시장 리포트 생성 실패"));
  }
}

export {
  ANALYTICS_EVENT_LABELS,
  ANALYTICS_OPT_OUT_STORAGE_KEY,
  MARKET_REPORT_MIN_BROWSERS,
  MARKET_REPORT_MIN_EVENTS,
  buildMarketReportCreateAuditMetadata,
  buildMarketReportCsv,
  buildMarketReportDownloadAuditMetadata,
  canTrackAnalyticsEvent,
  createAnalyticsPayload,
  createEmptyAnalyticsMarketReportArchive,
  createRemoteAnalyticsMarketReport,
  fetchRemoteAnalyticsDashboardSummary,
  fetchRemoteAnalyticsMarketReportArchive,
  fetchRemoteAnalyticsMarketReportItems,
  formatAnalyticsSummaryKey,
  getAllowedAnalyticsEventTypes,
  getMarketReportReadiness,
  isAnalyticsOptedOut,
  sanitizeSearchMetadata,
  setAnalyticsOptOut,
  summarizeAnalyticsDashboardRows,
  trackAnalyticsEvent,
  trackTrafficSourceOnce,
};

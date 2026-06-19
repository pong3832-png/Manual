const URL_FIELDS = [
  ["naverBlogUrl", "네이버 블로그"],
  ["instagramUrl", "인스타그램"],
  ["youtubeUrl", "유튜브"],
];

const METRIC_FIELDS = [
  ["naverBlogNeighborCount", "naver_blog_neighbor_count", "네이버 블로그 이웃수"],
  ["naverBlogDailyVisitorCount", "naver_blog_daily_visitor_count", "네이버 블로그 하루 방문자"],
  ["naverBlogTotalVisitorCount", "naver_blog_total_visitor_count", "네이버 블로그 총 방문자"],
  ["instagramFollowerCount", "instagram_follower_count", "인스타그램 팔로워"],
  ["youtubeSubscriberCount", "youtube_subscriber_count", "유튜브 구독자"],
];

function normalizeUrl(value) {
  const trimmed = String(value || "").trim();
  if (!trimmed) return "";
  return /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
}

function isValidUrl(value) {
  const normalized = normalizeUrl(value);
  if (!normalized) return true;
  try {
    const url = new URL(normalized);
    return Boolean(url.hostname.includes("."));
  } catch {
    return false;
  }
}

function parseMetric(value) {
  const trimmed = String(value ?? "").replaceAll(",", "").trim();
  if (!trimmed) return null;
  if (!/^\d+$/.test(trimmed)) return Number.NaN;
  const parsed = Number(trimmed);
  return Number.isSafeInteger(parsed) ? parsed : Number.NaN;
}

export function formatProfileMetric(value) {
  const parsed = parseMetric(value);
  return Number.isFinite(parsed) ? parsed.toLocaleString("ko-KR") : "";
}

export function buildProfileDraftFromProfile(profile = {}) {
  return {
    name: profile?.name || "",
    naverBlogUrl: profile?.blog_url || "",
    instagramUrl: profile?.instagram_url || "",
    youtubeUrl: profile?.youtube_url || "",
    applicationMessageTemplate: profile?.application_message_template || "",
    naverBlogNeighborCount: formatProfileMetric(profile?.naver_blog_neighbor_count),
    naverBlogDailyVisitorCount: formatProfileMetric(profile?.naver_blog_daily_visitor_count),
    naverBlogTotalVisitorCount: formatProfileMetric(profile?.naver_blog_total_visitor_count),
    instagramFollowerCount: formatProfileMetric(profile?.instagram_follower_count),
    youtubeSubscriberCount: formatProfileMetric(profile?.youtube_subscriber_count),
  };
}

export function buildProfilePayload(draft) {
  const payload = {
    name: String(draft.name || "").trim(),
    blog_url: normalizeUrl(draft.naverBlogUrl) || null,
    instagram_url: normalizeUrl(draft.instagramUrl) || null,
    youtube_url: normalizeUrl(draft.youtubeUrl) || null,
    application_message_template: String(draft.applicationMessageTemplate || "").trim() || null,
  };

  METRIC_FIELDS.forEach(([draftKey, column]) => {
    const parsed = parseMetric(draft[draftKey]);
    payload[column] = Number.isFinite(parsed) ? parsed : null;
  });

  return payload;
}

export function getProfileDraftValidation(draft) {
  return {
    invalidMetricLabels: METRIC_FIELDS
      .filter(([draftKey]) => Number.isNaN(parseMetric(draft[draftKey])))
      .map(([, , label]) => label),
    invalidUrlLabels: URL_FIELDS
      .filter(([draftKey]) => !isValidUrl(draft[draftKey]))
      .map(([, label]) => label),
  };
}

export function areProfileDraftsEqual(leftDraft, rightDraft) {
  const leftValidation = getProfileDraftValidation(leftDraft);
  const rightValidation = getProfileDraftValidation(rightDraft);
  if (
    leftValidation.invalidMetricLabels.length > 0
    || leftValidation.invalidUrlLabels.length > 0
    || rightValidation.invalidMetricLabels.length > 0
    || rightValidation.invalidUrlLabels.length > 0
  ) {
    return false;
  }

  const leftPayload = buildProfilePayload(leftDraft);
  const rightPayload = buildProfilePayload(rightDraft);
  return Object.keys(leftPayload).every((key) => leftPayload[key] === rightPayload[key]);
}

import assert from "node:assert/strict";

const storage = new Map();

globalThis.localStorage = {
  getItem(key) {
    return storage.get(String(key)) || null;
  },
  setItem(key, value) {
    storage.set(String(key), String(value));
  },
};

globalThis.window = {
  location: new URL("https://camp-platform-liart.vercel.app/explore?q=%EA%B0%95%EB%82%A8%20%EB%A7%9B%EC%A7%91&category=food#access_token=secret-token&id_token=secret-id"),
};

globalThis.document = {
  referrer: "https://search.example.test/?q=private-search",
};

const {
  canTrackAnalyticsEvent,
  createAnalyticsPayload,
  isAnalyticsOptedOut,
  sanitizeSearchMetadata,
  setAnalyticsOptOut,
} = await import("../../src/features/analytics/lib/analytics.js");

assert.equal(typeof createAnalyticsPayload, "function", "createAnalyticsPayload must be exported");
assert.equal(typeof canTrackAnalyticsEvent, "function", "canTrackAnalyticsEvent must be exported");

setAnalyticsOptOut(true);
assert.equal(isAnalyticsOptedOut(), true, "analytics opt-out flag should be stored");
assert.equal(canTrackAnalyticsEvent(), false, "ordinary analytics events must stop after opt-out");
assert.equal(
  canTrackAnalyticsEvent({ ignoreOptOut: true }),
  true,
  "analytics preference audit events may bypass opt-out",
);
setAnalyticsOptOut(false);
assert.equal(canTrackAnalyticsEvent(), true, "ordinary analytics events may resume after opt-in");

const searchMetadata = sanitizeSearchMetadata("강남 맛집 추천");
assert.deepEqual(
  searchMetadata,
  { hasSearch: true, searchLength: 8 },
  "search metadata must keep only search presence and length",
);

const payload = createAnalyticsPayload("search_filter", {
  category: "맛집",
  metadata: {
    rawSearch: "강남 맛집 추천",
    q: "강남 맛집 추천",
    accessToken: "secret-token",
    reviewUrl: "https://blog.example.test/private-review",
    nested: {
      password: "secret-password",
      safeMetric: 12,
    },
    longText: "x".repeat(200),
  },
}, { id: "user_1" });

assert.ok(payload, "allowed analytics event should create a payload");
assert.equal(payload.page_path, "/explore?q=%5Bsearch%5D&category=food#auth");
assert.equal(payload.metadata.rawSearch, "[redacted]");
assert.equal(payload.metadata.q, "[redacted]");
assert.equal(payload.metadata.accessToken, "[redacted]");
assert.equal(payload.metadata.reviewUrl, "[redacted]");
assert.equal(payload.metadata.nested.password, "[redacted]");
assert.equal(payload.metadata.nested.safeMetric, 12);
assert.equal(payload.metadata.longText.length, 120);

const serializedPayload = JSON.stringify(payload);
for (const forbidden of [
  "강남 맛집 추천",
  "secret-token",
  "secret-id",
  "secret-password",
  "private-review",
]) {
  assert.ok(!serializedPayload.includes(forbidden), `payload must not include sensitive value: ${forbidden}`);
}

assert.equal(
  createAnalyticsPayload("unknown_event", { metadata: { safeMetric: 1 } }),
  null,
  "unknown analytics event types must be ignored",
);

console.log(JSON.stringify({ ok: true }, null, 2));

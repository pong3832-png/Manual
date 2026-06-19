import assert from "node:assert/strict";

globalThis.localStorage = {
  getItem() {
    return null;
  },
  setItem() {},
};

globalThis.window = {
  location: new URL("https://camp-platform-liart.vercel.app/explore"),
};

globalThis.document = {
  referrer: "",
};

const {
  ANALYTICS_EVENT_LABELS,
  createAnalyticsPayload,
  formatAnalyticsSummaryKey,
  getAllowedAnalyticsEventTypes,
} = await import("../../src/features/analytics/lib/analytics.js");

assert.equal(typeof getAllowedAnalyticsEventTypes, "function", "getAllowedAnalyticsEventTypes must be exported");
assert.equal(typeof formatAnalyticsSummaryKey, "function", "formatAnalyticsSummaryKey must be exported");

const allowedEventTypes = getAllowedAnalyticsEventTypes();
assert.ok(Array.isArray(allowedEventTypes), "allowed event types must be an array");
assert.ok(allowedEventTypes.length >= 20, "analytics event catalog should include the current product event set");

for (const eventType of allowedEventTypes) {
  assert.ok(ANALYTICS_EVENT_LABELS[eventType], `missing analytics label for ${eventType}`);
  assert.ok(
    createAnalyticsPayload(eventType, { metadata: { safeMetric: 1 } }),
    `allowed event type should create payload: ${eventType}`,
  );
}

assert.equal(
  createAnalyticsPayload("unlisted_event", { metadata: { safeMetric: 1 } }),
  null,
  "unlisted events must not create analytics payloads",
);

assert.equal(
  formatAnalyticsSummaryKey({ type: "event_type", key: "apply_click" }),
  "신청 버튼",
);
assert.equal(
  formatAnalyticsSummaryKey({ type: "tab", key: "profile" }),
  "마이",
);
assert.equal(
  formatAnalyticsSummaryKey({ type: "identity", key: "logged_in" }),
  "로그인",
);
assert.equal(
  formatAnalyticsSummaryKey({ type: "identity", key: "anonymous" }),
  "비로그인",
);
assert.equal(
  formatAnalyticsSummaryKey({ type: "category", key: "맛집" }),
  "맛집",
);

console.log(JSON.stringify({
  ok: true,
  allowedEventTypes: allowedEventTypes.length,
}, null, 2));

import assert from "node:assert/strict";

globalThis.localStorage = {
  getItem() {
    return null;
  },
  setItem() {},
};

globalThis.window = {
  location: new URL("https://camp-platform-liart.vercel.app/?ops=1"),
};

globalThis.document = {
  referrer: "",
};

const {
  summarizeAnalyticsDashboardRows,
} = await import("../../src/features/analytics/lib/analytics.js");

assert.equal(typeof summarizeAnalyticsDashboardRows, "function", "summarizeAnalyticsDashboardRows must be exported");

const summary = summarizeAnalyticsDashboardRows([
  {
    summary_type: "event_type",
    summary_key: "campaign_open",
    event_type: "campaign_open",
    event_count: "12",
    unique_users: "3",
    unique_browsers: "6",
    last_event_at: "2026-05-26T00:01:00.000Z",
  },
  {
    summary_type: "event_type",
    summary_key: "apply_click",
    event_type: "apply_click",
    event_count: "30",
    unique_users: "2",
    unique_browsers: "8",
    last_event_at: "2026-05-26T00:02:00.000Z",
  },
  {
    summary_type: "total",
    summary_key: "all",
    event_type: "all",
    event_count: "42",
    unique_users: "4",
    unique_browsers: "9",
    last_event_at: "2026-05-26T00:03:00.000Z",
  },
  {
    summary_type: "category",
    summary_key: "맛집",
    event_type: "all",
    event_count: "21",
    unique_browsers: "7",
  },
  {
    summary_type: "identity",
    summary_key: "logged_in",
    event_type: "all",
    event_count: "10",
    unique_users: "4",
    unique_browsers: "4",
  },
  {
    summary_type: "apply_campaign",
    summary_key: "campaign_1",
    event_type: "apply_click",
    event_count: "9",
    unique_browsers: "5",
  },
]);

assert.equal(summary.totalEvents, 42);
assert.equal(summary.uniqueUsers, 4);
assert.equal(summary.uniqueBrowsers, 9);
assert.equal(summary.lastEventAt, "2026-05-26T00:03:00.000Z");

assert.deepEqual(
  summary.eventRows.map((row) => [row.key, row.count, row.uniqueBrowsers]),
  [
    ["apply_click", 30, 8],
    ["campaign_open", 12, 6],
  ],
);
assert.deepEqual(summary.categoryRows.map((row) => row.key), ["맛집"]);
assert.deepEqual(summary.identityRows.map((row) => row.key), ["logged_in"]);
assert.deepEqual(summary.applyCampaignRows.map((row) => row.key), ["campaign_1"]);
assert.deepEqual(summary.regionRows, []);
assert.deepEqual(summary.platformRows, []);
assert.deepEqual(summary.tabRows, []);
assert.equal(summary.error, "");

const emptySummary = summarizeAnalyticsDashboardRows(null);
assert.equal(emptySummary.totalEvents, 0);
assert.equal(emptySummary.uniqueUsers, 0);
assert.equal(emptySummary.uniqueBrowsers, 0);
assert.deepEqual(emptySummary.eventRows, []);

console.log(JSON.stringify({ ok: true }, null, 2));

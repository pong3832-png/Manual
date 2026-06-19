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
  buildMarketReportCsv,
  getMarketReportReadiness,
} = await import("../../src/features/analytics/lib/analytics.js");

assert.equal(typeof getMarketReportReadiness, "function", "getMarketReportReadiness must be exported");
assert.equal(typeof buildMarketReportCsv, "function", "buildMarketReportCsv must be exported");

const summary = {
  totalEvents: 42,
  uniqueBrowsers: 6,
  eventRows: [
    { type: "event_type", key: "apply_click", eventType: "apply_click", count: 28, uniqueBrowsers: 6 },
    { type: "event_type", key: "campaign_open", eventType: "campaign_open", count: 35, uniqueBrowsers: 4 },
  ],
  categoryRows: [
    { type: "category", key: "맛집", eventType: "all", count: 24, uniqueBrowsers: 5 },
  ],
  regionRows: [
    { type: "region", key: "서울", eventType: "all", count: 19, uniqueBrowsers: 5 },
  ],
  platformRows: [],
  tabRows: [],
};

const readiness = getMarketReportReadiness(summary, {
  formatKey(row) {
    return row.type === "event_type" && row.key === "apply_click" ? "신청 버튼" : row.key;
  },
});

assert.equal(readiness.isReady, true, "summary should be ready when at least one segment meets thresholds");
assert.equal(readiness.readySegmentCount, 2, "only rows meeting both event and browser thresholds should count");
assert.deepEqual(
  readiness.candidateRows.map((row) => row.displayKey),
  ["신청 버튼", "맛집"],
  "candidate rows should be sorted by count and use display labels",
);
assert.equal(readiness.missingEvents, 0);
assert.equal(readiness.missingBrowsers, 0);

const notReady = getMarketReportReadiness({
  totalEvents: 18,
  uniqueBrowsers: 3,
  eventRows: [],
});
assert.equal(notReady.isReady, false);
assert.equal(notReady.missingEvents, 2);
assert.equal(notReady.missingBrowsers, 2);

const csv = buildMarketReportCsv(
  {
    id: "report_1",
    title: "5월 시장 리포트",
    status: "ready",
    generatedAt: "2026-05-26T00:00:00.000Z",
    periodStart: "2026-05-01T00:00:00.000Z",
    periodEnd: "2026-05-26T00:00:00.000Z",
    lookbackDays: 30,
    minEvents: 20,
    minBrowsers: 5,
    rowCount: 1,
    totalEventCount: 42,
    totalUniqueBrowsers: 6,
    exportPolicyVersion: "market-report-v1",
  },
  [
    {
      rankPosition: 1,
      reportType: "category_interest",
      dimensionKey: "맛집",
      metricName: "event_count",
      metricValue: 24,
      eventCount: 24,
      uniqueBrowsers: 5,
      uniqueUsers: 2,
      periodStart: "2026-05-01T00:00:00.000Z",
      periodEnd: "2026-05-26T00:00:00.000Z",
      userId: "user_should_not_export",
      anonymousId: "anon_should_not_export",
      pagePath: "/explore?q=private",
      rawSearch: "강남 맛집",
    },
  ],
);

assert.ok(csv.includes("\"report_id\",\"report_1\""));
assert.ok(csv.includes("\"rank\",\"report_type\",\"dimension_key\""));
assert.ok(csv.includes("\"1\",\"category_interest\",\"맛집\""));

for (const forbidden of [
  "user_should_not_export",
  "anon_should_not_export",
  "/explore?q=private",
  "강남 맛집",
]) {
  assert.ok(!csv.includes(forbidden), `market report CSV must not include ${forbidden}`);
}

console.log(JSON.stringify({ ok: true }, null, 2));

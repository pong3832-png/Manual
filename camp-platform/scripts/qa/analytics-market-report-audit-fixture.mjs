import assert from "node:assert/strict";

globalThis.localStorage = {
  getItem() {
    return null;
  },
  setItem() {},
};

globalThis.window = {
  location: new URL("https://camp-platform-liart.vercel.app/ops?tab=reports"),
};

globalThis.document = {
  referrer: "",
};

const {
  buildMarketReportCreateAuditMetadata,
  buildMarketReportDownloadAuditMetadata,
  createAnalyticsPayload,
} = await import("../../src/features/analytics/lib/analytics.js");

assert.equal(typeof buildMarketReportCreateAuditMetadata, "function", "create audit metadata helper must be exported");
assert.equal(typeof buildMarketReportDownloadAuditMetadata, "function", "download audit metadata helper must be exported");

const sensitiveReport = {
  id: "report_20260526",
  status: "ready",
  rowCount: 3,
  totalEventCount: 84,
  totalUniqueBrowsers: 12,
  lookbackDays: 30,
  minEvents: 20,
  minBrowsers: 5,
  periodStart: "2026-04-26T00:00:00.000Z",
  periodEnd: "2026-05-26T00:00:00.000Z",
  title: "서울 맛집 원문 제목",
  notes: "검색어와 운영자 메모가 섞인 문장",
  generatedBy: "user_should_not_export",
  reviewUrl: "https://example.com/private-review",
  pagePath: "/explore?q=secret",
};

const sensitiveItems = [
  {
    reportType: "category_interest",
    dimensionKey: "맛집",
    eventCount: 45,
    uniqueBrowsers: 9,
    uniqueUsers: 3,
    userId: "user_should_not_export",
    anonymousId: "anon_should_not_export",
    rawSearch: "강남 맛집",
    sourceUrl: "https://example.com/private",
  },
];

const createMetadata = buildMarketReportCreateAuditMetadata(sensitiveReport, {
  lookbackDays: 30,
  minEvents: 20,
  minBrowsers: 5,
  selectedItems: sensitiveItems,
});
const downloadMetadata = buildMarketReportDownloadAuditMetadata(sensitiveReport, sensitiveItems);

assert.deepEqual(createMetadata, {
  reportId: "report_20260526",
  reportStatus: "ready",
  rowCount: 3,
  totalEventCount: 84,
  totalUniqueBrowsers: 12,
  lookbackDays: 30,
  minEvents: 20,
  minBrowsers: 5,
  selectedItemCount: 1,
});

assert.deepEqual(downloadMetadata, {
  reportId: "report_20260526",
  reportStatus: "ready",
  rowCount: 3,
  itemCount: 1,
  totalEventCount: 84,
  totalUniqueBrowsers: 12,
  lookbackDays: 30,
  minEvents: 20,
  minBrowsers: 5,
});

for (const metadata of [createMetadata, downloadMetadata]) {
  const serialized = JSON.stringify(metadata);
  for (const forbidden of [
    "서울 맛집 원문 제목",
    "검색어와 운영자 메모",
    "user_should_not_export",
    "anon_should_not_export",
    "private-review",
    "/explore?q=secret",
    "강남 맛집",
    "sourceUrl",
  ]) {
    assert.ok(!serialized.includes(forbidden), `audit metadata must not include ${forbidden}`);
  }
}

const payload = createAnalyticsPayload("market_report_download", { metadata: downloadMetadata });
assert.equal(payload.metadata.reportId, "report_20260526");
assert.equal(payload.metadata.itemCount, 1);
assert.ok(!JSON.stringify(payload.metadata).includes("user_should_not_export"));

console.log(JSON.stringify({ ok: true }, null, 2));

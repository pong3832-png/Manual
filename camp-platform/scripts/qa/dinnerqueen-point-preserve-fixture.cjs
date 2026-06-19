const assert = require("node:assert/strict");

process.env.CRAWLER_TEST_EXPORTS = "1";

const {
  buildCampaignSnapshotResult,
} = require("../crawler/crawl.cjs");

assert.equal(typeof buildCampaignSnapshotResult, "function");

const crawlStartedAt = "2026-05-26T00:00:00.000Z";
const previousCampaign = {
  id: "dq_keep_point",
  platformId: "dinner",
  platform: "dinnerqueen",
  title: "Dinner Queen preserved point sample",
  url: "https://dinnerqueen.net/taste/9999999",
  dDay: 3,
  status: "open",
  point: "40000 KRW meal voucher",
  type: "visit",
  category: "food",
  crawledAt: "2026-05-25T00:00:00.000Z",
  firstSeenAt: "2026-05-25T00:00:00.000Z",
  lastSeenAt: "2026-05-25T00:00:00.000Z",
};

const result = buildCampaignSnapshotResult(
  [
    {
      platformId: "dinner",
      label: "dinnerqueen",
      durationMs: 1,
      campaigns: [
        {
          ...previousCampaign,
          point: null,
          crawledAt: crawlStartedAt,
        },
      ],
    },
  ],
  [],
  {
    previousCampaigns: [previousCampaign],
    crawlStartedAt,
  },
);

const campaign = result.campaigns.find((item) => item.id === "dq_keep_point");
assert.ok(campaign, "fresh Dinnerqueen campaign should remain publishable");
assert.equal(campaign.point, previousCampaign.point);
assert.equal(campaign.dataState, "fresh");

console.log(JSON.stringify({ ok: true }, null, 2));
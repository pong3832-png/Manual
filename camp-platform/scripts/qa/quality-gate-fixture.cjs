const assert = require("assert");

process.env.CRAWLER_TEST_EXPORTS = "1";

const { evaluateQualityGate } = require("../crawler/crawl.cjs");

assert.equal(typeof evaluateQualityGate, "function", "evaluateQualityGate must be exported");

const freshCampaign = {
  id: "sample_1",
  title: "Sample campaign",
  url: "https://example.com/campaign/1",
  platformId: "sample",
  platform: "sample",
  dDay: 3,
  status: "open",
  coordinateSource: "unresolved",
};

const qualityGate = evaluateQualityGate({
  candidateCampaigns: [freshCampaign],
  freshCampaigns: [freshCampaign],
  previousCampaigns: [],
  successfulCrawls: [
    {
      platformId: "sample",
      label: "sample",
      campaigns: [freshCampaign],
      durationMs: 1,
    },
  ],
  failedCrawls: [
    {
      platformId: "reviewnote",
      label: "reviewnote",
      reason: "cooldown active after 403",
      durationMs: 1,
    },
  ],
  activeCrawlers: [
    { platformId: "sample", label: "sample" },
    { platformId: "reviewnote", label: "reviewnote" },
  ],
  crawlOnly: [],
});

const failedPreserveRule = qualityGate.rules.find((rule) => (
  rule.id === "failed_platform_preserved:reviewnote"
));

assert.ok(failedPreserveRule, "expected failed-platform preservation rule");
assert.equal(failedPreserveRule.passed, false, "failed platform without previous data must fail preservation rule");
assert.equal(qualityGate.canPublish, false, "quality gate must block publishing when failed platform cannot be preserved");
assert.equal(qualityGate.status, "blocked", "quality gate status must be blocked");

console.log(JSON.stringify({
  ok: true,
  status: qualityGate.status,
  canPublish: qualityGate.canPublish,
}, null, 2));

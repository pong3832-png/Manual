const assert = require("node:assert/strict");

process.env.CRAWLER_TEST_EXPORTS = "1";

const {
  selectDinnerqueenDetailTargets,
} = require("../crawler/crawl.cjs");

assert.equal(typeof selectDinnerqueenDetailTargets, "function");

const campaigns = [
  { id: "closed_with_point", platformId: "dinner", dDay: -1, status: "closed", point: "3만원 식사권", applyCount: 1 },
  { id: "closed_empty", platformId: "dinner", dDay: -1, status: "closed", point: "", applyCount: 0 },
  { id: "open_empty_later", platformId: "dinner", dDay: 7, status: "open", point: "", applyCount: 1 },
  { id: "open_filled_soon", platformId: "dinner", dDay: 0, status: "open", point: "이미 있음", applyCount: 1 },
  { id: "open_empty_soon", platformId: "dinner", dDay: 1, status: "open", point: "", applyCount: 9 },
  { id: "open_empty_soon_low_apply", platformId: "dinner", dDay: 1, status: "open", point: "", applyCount: 2 },
];

assert.deepEqual(
  selectDinnerqueenDetailTargets(campaigns, 4).map((campaign) => campaign.id),
  [
    "open_empty_soon_low_apply",
    "open_empty_soon",
    "open_empty_later",
    "open_filled_soon",
  ],
  "open campaigns with empty point should be enriched before closed or already-filled campaigns",
);

assert.deepEqual(
  selectDinnerqueenDetailTargets(campaigns, 0).map((campaign) => campaign.id),
  [
    "open_empty_soon_low_apply",
    "open_empty_soon",
    "open_empty_later",
    "open_filled_soon",
    "closed_empty",
    "closed_with_point",
  ],
  "limit 0 should keep every campaign while preserving priority order",
);

console.log(JSON.stringify({ ok: true }, null, 2));

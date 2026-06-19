const assert = require("node:assert/strict");

process.env.DINNERQUEEN_BACKFILL_TEST_EXPORTS = "1";

const {
  buildDinnerqueenProvisionBackfillPlan,
  buildExistingDinnerqueenPointUpdates,
  selectCampaigns,
} = require("../crawler/backfill-dinnerqueen-provisions.cjs");

assert.equal(typeof buildDinnerqueenProvisionBackfillPlan, "function");
assert.equal(typeof buildExistingDinnerqueenPointUpdates, "function");
assert.equal(typeof selectCampaigns, "function");

const snapshot = {
  campaigns: [
    {
      id: "dinner_soon",
      platformId: "dinner",
      url: "https://dinnerqueen.net/taste/1",
      point: "",
      dDay: 1,
      applyCount: 12,
    },
    {
      id: "dinner_later",
      platformId: "dinner",
      url: "https://dinnerqueen.net/taste/2",
      point: "",
      dDay: 8,
      applyCount: 2,
    },
    {
      id: "dinner_filled",
      platformId: "dinner",
      url: "https://dinnerqueen.net/taste/3",
      point: "식사권 제공",
      dDay: 2,
      applyCount: 3,
    },
    {
      id: "dinner_closed",
      platformId: "dinner",
      url: "https://dinnerqueen.net/taste/4",
      point: "",
      dDay: -1,
      status: "closed",
      applyCount: 1,
    },
    {
      id: "dinner_no_url",
      platformId: "dinner",
      url: "",
      point: "",
      dDay: 0,
    },
    {
      id: "mrblog_empty",
      platformId: "mrblog",
      url: "https://example.com",
      point: "",
    },
  ],
};

const selectedIds = selectCampaigns(snapshot, { recheckAll: false, limit: 10 }).map((campaign) => campaign.id);
assert.deepEqual(selectedIds, ["dinner_soon", "dinner_later", "dinner_closed"]);

const limitedPlan = buildDinnerqueenProvisionBackfillPlan(snapshot, { recheckAll: false, limit: 1 });
assert.deepEqual(limitedPlan, {
  totalDinner: 5,
  pointFilled: 1,
  pointEmpty: 4,
  withUrl: 4,
  selectable: 3,
  selected: 1,
  limit: 1,
  recheckAll: false,
});

const recheckPlan = buildDinnerqueenProvisionBackfillPlan(snapshot, { recheckAll: true, limit: 10 });
assert.equal(recheckPlan.selectable, 4);
assert.equal(recheckPlan.selected, 4);
assert.equal(recheckPlan.pointEmpty, 4);

assert.deepEqual(
  buildExistingDinnerqueenPointUpdates(snapshot, { limit: 10 }).map((update) => [update.id, update.point]),
  [["dinner_filled", "식사권 제공"]],
);
assert.deepEqual(buildExistingDinnerqueenPointUpdates(snapshot, { limit: 0 }).map((update) => update.id), ["dinner_filled"]);

console.log(JSON.stringify({ ok: true }, null, 2));

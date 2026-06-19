import assert from "node:assert/strict";

const {
  mergeCampaignPointsFromSnapshot,
} = await import("../../src/features/campaigns/lib/campaignPointMerge.js");

assert.equal(typeof mergeCampaignPointsFromSnapshot, "function");

const dbCampaigns = [
  { id: "dq_1", platformId: "dinner", point: null, title: "Dinner 1" },
  { id: "dq_2", platformId: "dinner", point: "DB point", title: "Dinner 2" },
  { id: "mr_1", platformId: "mrblog", point: null, title: "Mrblog" },
];
const localCampaigns = [
  { id: "dq_1", platformId: "dinner", point: "Local dinner point" },
  { id: "dq_2", platformId: "dinner", point: "Local should not overwrite" },
  { id: "mr_1", platformId: "mrblog", point: "Local mrblog point" },
];

const merged = mergeCampaignPointsFromSnapshot(dbCampaigns, localCampaigns);
assert.equal(merged[0].point, "Local dinner point");
assert.equal(merged[1].point, "DB point");
assert.equal(merged[2].point, null);
assert.notEqual(merged[0], dbCampaigns[0], "patched campaign should be copied");
assert.equal(merged[1], dbCampaigns[1], "unchanged campaign can keep identity");

console.log(JSON.stringify({ ok: true }, null, 2));
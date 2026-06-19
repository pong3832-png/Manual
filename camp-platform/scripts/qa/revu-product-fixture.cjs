const assert = require("node:assert/strict");

process.env.CRAWLER_TEST_EXPORTS = "1";

const {
  buildRevuCampaignFromApiItem,
  getRevuCategories,
  mapRevuType,
} = require("../crawler/crawl.cjs");

assert.equal(typeof buildRevuCampaignFromApiItem, "function");
assert.equal(typeof getRevuCategories, "function");
assert.equal(typeof mapRevuType, "function");

delete process.env.REVU_LIST_SCOPE;
assert.deepEqual(getRevuCategories(), ["지역", "제품"]);

process.env.REVU_LIST_SCOPE = "delivery";
assert.deepEqual(getRevuCategories(), ["제품"]);
delete process.env.REVU_LIST_SCOPE;

assert.equal(
  mapRevuType({
    media: "instagram",
    category: ["제품"],
    campaignOptions: {},
  }),
  "delivery",
);

assert.equal(
  mapRevuType({
    media: "blog",
    category: ["지역"],
    campaignOptions: {},
  }),
  "visit",
);

assert.equal(
  mapRevuType({
    media: "instagram",
    category: ["지역"],
    campaignOptions: {},
  }),
  "instagram",
);

const productCampaign = buildRevuCampaignFromApiItem({
  id: 1345843,
  item: "[동원] 건강은더하고부담은줄인슈퍼참치",
  media: "blog",
  category: ["제품"],
  byDeadline: 4,
  reviewerLimit: 50,
  thumbnail: "https://files.weble.net/campaign/data/1345843/thumb200.jpg?bust=1779958387047",
  campaignStats: {
    requestCount: 256,
  },
  campaignData: {
    reward: "동원 참치 8개",
  },
  campaignOptions: {},
});

assert.equal(productCampaign.id, "revu_1345843");
assert.equal(productCampaign.title, "[동원] 건강은더하고부담은줄인슈퍼참치");
assert.equal(productCampaign.url, "https://www.revu.net/campaign/1345843");
assert.equal(productCampaign.platformId, "revu");
assert.equal(productCampaign.type, "delivery");
assert.equal(productCampaign.dDay, 4);
assert.equal(productCampaign.applyCount, 256);
assert.equal(productCampaign.selectedCount, 50);
assert.equal(productCampaign.point, "동원 참치 8개");
assert.equal(
  productCampaign.imageUrl,
  "https://files.weble.net/campaign/data/1345843/thumb200.jpg?bust=1779958387047",
);
assert.equal(productCampaign.coordinateSource, "unresolved");
assert.equal(productCampaign.lat, undefined);
assert.equal(productCampaign.lng, undefined);

const regionInstagram = buildRevuCampaignFromApiItem({
  id: 1345875,
  item: "[리포데이] 올인원 데일리파이토",
  media: "instagram",
  category: ["지역"],
  byDeadline: 4,
  reviewerLimit: 15,
  campaignStats: {
    requestCount: 16,
  },
  campaignData: {
    reward: "데일리파이토 1개",
  },
  campaignOptions: {},
});

assert.equal(regionInstagram.type, "instagram");
assert.equal(regionInstagram.point, "데일리파이토 1개");

console.log(JSON.stringify({ ok: true }, null, 2));

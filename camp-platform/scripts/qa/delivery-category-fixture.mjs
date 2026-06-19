import assert from "node:assert/strict";
import { createServer } from "vite";

const server = await createServer({
  appType: "custom",
  logLevel: "error",
  server: { middlewareMode: true },
});

let CATEGORIES;
let CAMPAIGN_TYPE_FILTERS;
let campaignMatchesType;
let campaignTypeToSlug;
let categoryToSlug;
let enrichCampaign;
let normalizeCampaignCategory;
let slugToCampaignType;
let slugToCategory;

try {
  ({ CATEGORIES, CAMPAIGN_TYPE_FILTERS } = await server.ssrLoadModule("/src/shared/config/platforms.js"));
  ({
    campaignMatchesType,
    campaignTypeToSlug,
    categoryToSlug,
    enrichCampaign,
    normalizeCampaignCategory,
    slugToCampaignType,
    slugToCategory,
  } = await server.ssrLoadModule("/src/features/campaigns/lib/campaigns.js"));
} finally {
  await server.close();
}

assert.deepEqual(CAMPAIGN_TYPE_FILTERS, ["전체", "방문형", "배송형"]);
assert.equal(campaignTypeToSlug("배송형"), "delivery");
assert.equal(slugToCampaignType("delivery"), "배송형");
assert.equal(slugToCampaignType("visit"), "방문형");
assert.ok(!CATEGORIES.includes("배송형"), "배송형 must be a top-level type filter, not a campaign category");
assert.equal(categoryToSlug("배송형"), "all");
assert.equal(slugToCategory("delivery"), "전체");

assert.equal(
  normalizeCampaignCategory("맛집", "디너의여왕 배송 캠페인", "dinner", "delivery"),
  "맛집",
);
assert.equal(
  normalizeCampaignCategory("생활용품", "체험뷰 delivery campaign", "chvu", "delivery"),
  "생활용품",
);

for (const platformId of ["dinner", "gangnam", "chvu"]) {
  const campaign = enrichCampaign({
    id: `${platformId}_delivery_sample`,
    title: `${platformId} 배송형 샘플`,
    url: `https://example.com/${platformId}`,
    platformId,
    platform: platformId,
    type: "delivery",
    category: platformId === "chvu" ? "생활용품" : "맛집",
    dDay: 3,
    applyCount: 10,
    selectedCount: 3,
    point: "제품 제공",
  });

  assert.equal(campaign.campaignType, "delivery", `${platformId} delivery campaign must keep delivery type`);
  assert.equal(campaign.campaignMode, "배송형", `${platformId} delivery campaign must be in 배송형 mode`);
  assert.equal(campaign.category, platformId === "chvu" ? "생활용품" : "맛집");
  assert.equal(campaignMatchesType(campaign, "배송형"), true);
  assert.equal(campaignMatchesType(campaign, "방문형"), false);
}

const visitCampaign = enrichCampaign({
  id: "chvu_visit_sample",
  title: "체험뷰 방문형 샘플",
  url: "https://example.com/chvu-visit",
  platformId: "chvu",
  platform: "체험뷰",
  type: "visit",
  category: "맛집",
  dDay: 3,
  applyCount: 10,
  selectedCount: 3,
  point: "식사권",
});
assert.equal(visitCampaign.campaignType, "visit");
assert.equal(visitCampaign.campaignMode, "방문형");
assert.equal(visitCampaign.category, "맛집");
assert.equal(campaignMatchesType(visitCampaign, "방문형"), true);
assert.equal(campaignMatchesType(visitCampaign, "배송형"), false);

console.log(JSON.stringify({ ok: true }, null, 2));

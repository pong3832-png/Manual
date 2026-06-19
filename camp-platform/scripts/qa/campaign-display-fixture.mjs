import assert from "node:assert/strict";
import { createServer } from "vite";

const server = await createServer({
  appType: "custom",
  logLevel: "error",
  server: { middlewareMode: true },
});

let campaignModule;

try {
  campaignModule = await server.ssrLoadModule("/src/features/campaigns/lib/campaigns.js");
} finally {
  await server.close();
}

assert.equal(
  typeof campaignModule.getCampaignDisplayProfile,
  "function",
  "campaign display profile helper should be exported",
);
assert.equal(
  typeof campaignModule.formatCampaignDdayLabel,
  "function",
  "campaign deadline label helper should be exported",
);

assert.equal(
  campaignModule.getCampaignLocationLabel({
    title: "[광진] 제품 체험단",
    addressRaw: "서울특별시 광진구 천호대로 571 COPYRIGHT",
  }),
  "서울특별시 광진구 천호대로 571",
  "location labels should strip crawler footer noise",
);

assert.equal(campaignModule.formatCampaignDdayLabel(0), "오늘");
assert.equal(campaignModule.formatCampaignDdayLabel(1), "내일");
assert.equal(campaignModule.formatCampaignDdayLabel(3), "D-3");
assert.equal(campaignModule.formatCampaignDdayLabel(99), "마감일 확인");
assert.equal(campaignModule.formatCampaignDdayLabel(null), "마감일 확인");

const deliveryDisplay = campaignModule.getCampaignDisplayProfile({
  title: "상품 배송 체험단",
  type: "delivery",
  campaignType: "delivery",
  campaignMode: "배송형",
  category: "생활용품",
  locationRaw: "미정",
  dDay: 99,
});

assert.deepEqual(
  deliveryDisplay,
  {
    locationLabel: "배송형",
    snsLabel: "",
    modeLabel: "배송형",
    dDayLabel: "마감일 확인",
    isUrgent: false,
  },
  "delivery campaigns with unknown fields should show trustworthy fallback labels",
);

const deliveryWithAddressDisplay = campaignModule.getCampaignDisplayProfile({
  title: "[클립][닥터M] 미네랄워터",
  type: "delivery",
  campaignType: "delivery",
  campaignMode: "배송형",
  category: "생활용품",
  addressRaw: "서울특별시 광진구 천호대로 571",
  sourceType: "clip",
  dDay: 0,
});

assert.equal(
  deliveryWithAddressDisplay.locationLabel,
  "배송형",
  "delivery display should not expose visit-style addresses or title brackets as location",
);
assert.equal(deliveryWithAddressDisplay.snsLabel, "숏폼");
assert.equal(deliveryWithAddressDisplay.modeLabel, "배송형");
assert.equal(deliveryWithAddressDisplay.dDayLabel, "오늘");

const packagingDisplay = campaignModule.getCampaignDisplayProfile({
  title: "대단한탕후루 세종소담점",
  type: "delivery",
  campaignType: "delivery",
  campaignMode: "배송형",
  category: "맛집",
  point: "1만2천원 식사권 (포장체험)",
  dDay: 0,
});

assert.equal(packagingDisplay.locationLabel, "포장형");
assert.equal(packagingDisplay.modeLabel, "포장형");

const packagingUnavailableDisplay = campaignModule.getCampaignDisplayProfile({
  title: "민물장어구이전문점",
  type: "delivery",
  campaignType: "delivery",
  campaignMode: "배송형",
  category: "맛집",
  point: "점심체험 : 특장어덮밥 1인 + 덮밥류 중 택1 제공 / 포장불가",
  dDay: 0,
});

assert.equal(
  packagingUnavailableDisplay.locationLabel,
  "배송형",
  "delivery campaigns should not show packaging mode when benefit text says packaging is unavailable",
);
assert.equal(packagingUnavailableDisplay.modeLabel, "배송형");

assert.equal(
  campaignModule.getCampaignBenefitLabel({
    point: "카템 100w C to C 초고속 충전케이블 1.2m https://brand.naver.com/cartem/products/10120484162 * 본 체험단은 배송 후, 업체 자체의 [배송이벤트]에 중복 참여가 불가 합니다.",
  }),
  "카템 100w C to C 초고속 충전케이블 1.2m",
  "benefit display should remove URLs and long operational notes",
);

assert.equal(
  campaignModule.getCampaignBenefitLabel({
    point: "1인 기준 체험권자세한 상품은 가이드라인을 참고해주세요!",
  }),
  "1인 기준 체험권",
  "benefit display should remove attached guideline notes",
);

const blogVisitDisplay = campaignModule.getCampaignDisplayProfile({
  title: "[성수] 블로그 맛집 체험단",
  sourceType: "blog",
  campaignMode: "방문형",
  addressRaw: "서울특별시 성동구 성수이로 7",
  dDay: 1,
});

assert.equal(blogVisitDisplay.locationLabel, "서울특별시 성동구 성수이로 7");
assert.equal(blogVisitDisplay.snsLabel, "블로그");
assert.equal(blogVisitDisplay.modeLabel, "방문형");
assert.equal(blogVisitDisplay.dDayLabel, "내일");
assert.equal(blogVisitDisplay.isUrgent, true);

console.log(JSON.stringify({ ok: true }));

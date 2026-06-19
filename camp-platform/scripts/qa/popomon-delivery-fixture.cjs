const assert = require("assert");

process.env.CRAWLER_TEST_EXPORTS = "1";

const { getPopomonConfigs, parsePopomonListCampaigns } = require("../crawler/crawl.cjs");

const html = `
<a href="/next/campaign/252074">
  <li>
    <img src="/next/_next/image?url=https%3A%2F%2Fd17jwiodubhsh2.cloudfront.net%2FUPLOAD%2FCAMPAIGN_THUMB%2F20260513_112549_BiN1Jfp_ompanyinc.png&amp;w=3840&amp;q=75">
    <span>인스타</span><span>배송형</span>
    <h3>[뷰티/배송형]거노그롭</h3>
    <p><span>14일 남음</span>23만원 상당의 엑소좀 미스트, 크림, 마스크팩 세트</p>
    <span>신청 58/2</span>
  </li>
</a>
<a href="/next/campaign/259533">
  <li>
    <img src="/next/_next/image?url=https%3A%2F%2Fd17jwiodubhsh2.cloudfront.net%2FUPLOAD%2FCAMPAIGN_THUMB%2F20260529_091728_RxO7oDe_415033427.png&amp;w=3840&amp;q=75">
    <span>유튜브</span><span>배송형</span>
    <h3>[생활]모카리움</h3>
    <p><span>7일 남음</span>60만원 상당의 프리미엄 오가닉 침구 세트</p>
    <span>신청 0/5</span>
  </li>
</a>
<a href="/next/campaign/259486">
  <li>
    <img src="/next/_next/image?url=https%3A%2F%2Fd17jwiodubhsh2.cloudfront.net%2FUPLOAD%2FCAMPAIGN_THUMB%2F20260331_164615_GwY7iyF_qsOYRTH_Y.png&amp;w=3840&amp;q=75">
    <span>블로그</span><span>배송형</span>
    <h3>[식품]메타웰</h3>
    <p><span>5일 남음</span>6.9만원 상당의 메타웰 수족 냉증 영양제 포카포아</p>
    <span>신청 1/20</span>
  </li>
</a>
`;

process.env.POPOMON_LIST_SCOPE = "";
assert.ok(getPopomonConfigs().some((config) => config.label === "shipping"), "default configs include shipping");

process.env.POPOMON_LIST_SCOPE = "delivery";
assert.deepStrictEqual(
  getPopomonConfigs().map((config) => config.label),
  ["shipping"],
  "delivery scope only requests shipping campaigns",
);

const config = getPopomonConfigs()[0];
const parsed = parsePopomonListCampaigns(html, { config });
assert.strictEqual(parsed.parsedCount, 3);
assert.strictEqual(parsed.addedCount, 3);
assert.strictEqual(parsed.campaigns.length, 3);

const first = parsed.campaigns.find((campaign) => campaign.id === "pm_252074");
assert.ok(first, "first campaign parsed");
assert.strictEqual(first.title, "거노그롭");
assert.strictEqual(first.url, "https://popomon.com/next/campaign/252074");
assert.strictEqual(first.type, "delivery");
assert.strictEqual(first.dDay, 14);
assert.strictEqual(first.applyCount, 58);
assert.strictEqual(first.selectedCount, 2);
assert.strictEqual(first.point, "23만원 상당의 엑소좀 미스트, 크림, 마스크팩 세트");
assert.strictEqual(
  first.imageUrl,
  "https://d17jwiodubhsh2.cloudfront.net/UPLOAD/CAMPAIGN_THUMB/20260513_112549_BiN1Jfp_ompanyinc.png",
);

const second = parsed.campaigns.find((campaign) => campaign.id === "pm_259533");
assert.ok(second, "second campaign parsed");
assert.strictEqual(second.title, "모카리움");
assert.strictEqual(second.type, "delivery");
assert.strictEqual(second.dDay, 7);
assert.strictEqual(second.applyCount, 0);
assert.strictEqual(second.selectedCount, 5);
assert.ok(second.point.includes("침구 세트"), "provision text kept");

const third = parsed.campaigns.find((campaign) => campaign.id === "pm_259486");
assert.ok(third, "third campaign parsed");
assert.strictEqual(third.title, "메타웰");
assert.strictEqual(third.type, "delivery");
assert.strictEqual(third.dDay, 5);
assert.strictEqual(third.applyCount, 1);
assert.strictEqual(third.selectedCount, 20);

const seenIds = new Set(["pm_252074"]);
const deduped = parsePopomonListCampaigns(html, { config, seenIds });
assert.strictEqual(deduped.parsedCount, 3);
assert.strictEqual(deduped.addedCount, 2);
assert.ok(seenIds.has("pm_259533"), "new campaign id added to seen set");

console.log(JSON.stringify({ ok: true, parsedCount: parsed.parsedCount, addedCount: parsed.addedCount }, null, 2));

const assert = require("assert");

process.env.CRAWLER_TEST_EXPORTS = "1";

const { getMrblogConfigs, parseMrblogListCampaigns } = require("../crawler/crawl.cjs");

const html = `
<a href="https://www.mrblog.net/campaigns/1093486" class="campaign_item">
  <div class="thumb">
    <img src="http://storage.mrblog.net/new/files/campaigns/ibuki_01-1.jpg" alt="">
  </div>
  <div class="txt">
    <span class="area"><span class="sns_icon insta"></span> 배송</span>
    <strong class="subject">Lead Cycle 주식회사(일본)</strong>
    <p class="desc">이브키노미 영양제 30일분 1개</p>
    <div class="status">
      <span class="d_day">6일 남음</span>
      <div class="count"><span class="current">신청 <strong>1명</strong></span> / 모집 5명</div>
    </div>
  </div>
</a>
<a href="https://www.mrblog.net/campaigns/1093530" class="campaign_item">
  <div class="thumb">
    <img src="http://storage.mrblog.net/new/files/reports/53qQHZYTteygV61ioJs3JStisNPCxAdPppNQSJmE.png" alt="">
  </div>
  <div class="txt">
    <span class="area"><span class="sns_icon blog"></span> 배송</span>
    <strong class="subject">옹기종기땅콩빵 바사칸 고구마칩 (쿠팡)</strong>
    <p class="desc">
      옹기종기땅콩빵 바사칸 고구마칩 1봉지 (10,000원)
      쿠팡리뷰 작성 캠페인 (블로그X) / 선결제 후 페이백 진행됩니다
    </p>
    <div class="status">
      <span class="d_day">6일 남음</span>
      <div class="count"><span class="current">신청 <strong>4명</strong></span> / 모집 5명</div>
    </div>
  </div>
</a>
<a href="https://www.mrblog.net/campaigns/1091553" class="campaign_item">
  <div class="thumb">
    <img src="http://storage.mrblog.net/new/campaigns/1091553_4UiLK3cUQCuvvxxnqEj38BnouTgFJi8IcbaIZkHe.jpg" alt="">
  </div>
  <div class="txt">
    <span class="area"><span class="sns_icon blog"></span> 배송</span>
    <strong class="subject">강릉 무진장한과</strong>
    <p class="desc">강릉 무진장 한과 선물세트 (5만원 상당)</p>
    <div class="status">
      <span class="d_day">3일 남음</span>
      <div class="count"><span class="current">신청 <strong>149명</strong></span> / 모집 5명</div>
    </div>
  </div>
</a>
`;

process.env.MRBLOG_LIST_SCOPE = "";
assert.ok(getMrblogConfigs().some((config) => config.label === "delivery"), "default configs include delivery");

process.env.MRBLOG_LIST_SCOPE = "delivery";
assert.deepStrictEqual(
  getMrblogConfigs().map((config) => config.label),
  ["delivery"],
  "delivery scope only requests the delivery tab",
);

const seenIds = new Set(["mb_1091553"]);
const parsed = parseMrblogListCampaigns(html, { fallbackType: "delivery", seenIds });
assert.strictEqual(parsed.parsedCount, 3);
assert.strictEqual(parsed.addedCount, 2);
assert.strictEqual(parsed.campaigns.length, 2);

const first = parsed.campaigns.find((campaign) => campaign.id === "mb_1093486");
assert.ok(first, "first campaign parsed");
assert.strictEqual(first.title, "Lead Cycle 주식회사(일본)");
assert.strictEqual(first.url, "https://www.mrblog.net/campaigns/1093486");
assert.strictEqual(first.type, "delivery");
assert.strictEqual(first.dDay, 6);
assert.strictEqual(first.applyCount, 1);
assert.strictEqual(first.selectedCount, 5);
assert.strictEqual(first.point, "이브키노미 영양제 30일분 1개");
assert.strictEqual(first.imageUrl, "http://storage.mrblog.net/new/files/campaigns/ibuki_01-1.jpg");

const second = parsed.campaigns.find((campaign) => campaign.id === "mb_1093530");
assert.ok(second, "second campaign parsed");
assert.strictEqual(second.type, "delivery");
assert.strictEqual(second.dDay, 6);
assert.strictEqual(second.applyCount, 4);
assert.strictEqual(second.selectedCount, 5);
assert.ok(second.point.includes("선결제 후 페이백"), "description preserved as point");
assert.strictEqual(
  second.imageUrl,
  "http://storage.mrblog.net/new/files/reports/53qQHZYTteygV61ioJs3JStisNPCxAdPppNQSJmE.png",
);

assert.ok(seenIds.has("mb_1091553"), "pre-seen id stays marked");
assert.ok(seenIds.has("mb_1093486"), "new id added to seen set");

console.log(JSON.stringify({ ok: true, parsedCount: parsed.parsedCount, addedCount: parsed.addedCount }, null, 2));

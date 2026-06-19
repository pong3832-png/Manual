const assert = require("assert");

process.env.CRAWLER_TEST_EXPORTS = "1";

const { getReviewplaceCategories, parseReviewplaceListCampaigns } = require("../crawler/crawl.cjs");

const html = `
<div class="item">
  <a href="/pr/?id=289632">
    <div class="img">
      <img src="https://cdn.cdnreviewplace.co.kr/data/file/product/2026/05/29/thumb-289632_194cb2a746b8ea3fa15dcbdfd0acb3965fadba46_230x230.png" class="thumbimg">
    </div>
    <div class="item_info">
      <div class="txt_wrap">
        <p class="tit">[블로그/스스] 네이처그랜드 오메가3 꾸미</p>
        <p class="txt">네이처그랜드 오메가3 꾸미 / 1박스 * 1개(구매수량)</p>
      </div>
      <div class="date_wrap">
        <p class="date"><em class="d_ico">D</em> - 10</p>
        <div class="num"><p>신청 2<span> / 20명</span></p></div>
      </div>
      <div class="tag_wrap"><div class="txt_tag">17,900P</div></div>
    </div>
  </a>
</div>
<a href="/pr/?id=289624">
  <div class="img">
    <img src="https://cdn.cdnreviewplace.co.kr/data/file/product/2026/05/29/thumb-289624_ab624345975bc1da61b0b2a65899f7af5d9dbd69_230x230.jpg" class="thumbimg">
  </div>
  <div class="item_info">
    <div class="txt_wrap">
      <p class="tit">[릴스/회수형/30,000P] 자동 건조 케어온 제습기!</p>
      <p class="txt">[리뷰 후 제품 회수] 케어온제습기 1개 + 리뷰플레이스 30,000P</p>
    </div>
    <div class="date_wrap">
      <p class="date"><em class="d_ico">D</em> - 6</p>
      <div class="num"><p>신청 1<span> / 10명</span></p></div>
    </div>
    <div class="tag_wrap"><div class="txt_tag">+ 30,000P</div></div>
  </div>
</a>
<div class="item">
  <a href="/pr/?id=289622">
    <div class="img">
      <img src="https://cdn.cdnreviewplace.co.kr/data/file/product/2026/05/29/thumb-31400146_n4t6lcBv_275c0c01ac5f248cd482f2a452a3e2a9cd316561_230x230.png" class="thumbimg">
    </div>
    <div class="item_info">
      <div class="txt_wrap">
        <p class="tit">[인스타/릴스] 어메이즈핏 액티브3 프리미엄 GPS 스마트워치</p>
        <p class="txt">어메이즈핏 액티브3 프리미엄 GPS 스마트워치 * 1개</p>
      </div>
      <div class="date_wrap">
        <p class="date"><em class="d_ico">D</em> - 10</p>
        <div class="num"><p>신청 8<span> / 6명</span></p></div>
      </div>
      <div class="tag_wrap"></div>
    </div>
  </a>
</div>
`;

process.env.REVIEWPLACE_LIST_SCOPE = "";
assert.ok(getReviewplaceCategories().some((category) => category.label === "제품"), "default categories include product");

process.env.REVIEWPLACE_LIST_SCOPE = "delivery";
assert.deepStrictEqual(
  getReviewplaceCategories().map((category) => category.label),
  ["제품"],
  "delivery scope only requests the product tab",
);

const category = getReviewplaceCategories()[0];
const parsed = parseReviewplaceListCampaigns(html, { category });
assert.strictEqual(parsed.parsedCount, 3);
assert.strictEqual(parsed.addedCount, 3);
assert.strictEqual(parsed.campaigns.length, 3);

const first = parsed.campaigns.find((campaign) => campaign.id === "rp_289632");
assert.ok(first, "first campaign parsed");
assert.strictEqual(first.title, "[블로그/스스] 네이처그랜드 오메가3 꾸미");
assert.strictEqual(first.url, "https://www.reviewplace.co.kr/pr/?id=289632");
assert.strictEqual(first.type, "delivery");
assert.strictEqual(first.dDay, 10);
assert.strictEqual(first.applyCount, 2);
assert.strictEqual(first.selectedCount, 20);
assert.ok(first.point.includes("네이처그랜드 오메가3 꾸미"), "product provision is kept");
assert.strictEqual(
  first.imageUrl,
  "https://cdn.cdnreviewplace.co.kr/data/file/product/2026/05/29/thumb-289632_194cb2a746b8ea3fa15dcbdfd0acb3965fadba46_230x230.png",
);

const second = parsed.campaigns.find((campaign) => campaign.id === "rp_289624");
assert.ok(second, "second campaign parsed");
assert.strictEqual(second.type, "delivery");
assert.strictEqual(second.dDay, 6);
assert.strictEqual(second.applyCount, 1);
assert.strictEqual(second.selectedCount, 10);
assert.ok(second.point.includes("케어온제습기"), "recovery product provision is kept");

const third = parsed.campaigns.find((campaign) => campaign.id === "rp_289622");
assert.ok(third, "third campaign parsed");
assert.strictEqual(third.type, "delivery");
assert.strictEqual(third.applyCount, 8);
assert.strictEqual(third.selectedCount, 6);

const seenIds = new Set(["rp_289632"]);
const deduped = parseReviewplaceListCampaigns(html, { category, seenIds });
assert.strictEqual(deduped.parsedCount, 3);
assert.strictEqual(deduped.addedCount, 2);
assert.ok(seenIds.has("rp_289624"), "new campaign id added to seen set");

console.log(JSON.stringify({ ok: true, parsedCount: parsed.parsedCount, addedCount: parsed.addedCount }, null, 2));

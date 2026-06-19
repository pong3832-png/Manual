const assert = require("assert");

process.env.CRAWLER_TEST_EXPORTS = "1";

const { getPavloConfigs, parsePavloListCampaigns } = require("../crawler/crawl.cjs");

const html = `
<div class="box">
  <div class="thumb">
    <a href="review_campaign.php?cp_id=1779946581">
      <img src="./data/campaign/thumb/thumb-1889562815_1f6H7DC4_2_EC8AA4ED8AB8EB9EA9_EC8DB8_300x300.jpg" class="it_img">
    </a>
  </div>
  <a href="review_campaign.php?cp_id=1779946581">
    <div class="it_info">
      <div class="top_info">
        <div class="sns_info"><span class="sns blog">블로그</span></div>
        <div class="option2"><span>배송형</span></div>
      </div>
      <span class="it_name">[배송/생활] 디OO 창신</span>
      <span class="it_description">카메라 스트랩</span>
      <div class="option">
        <span><span>모집 <b class="txt_num">5</b></span></span>
        <span class="dday">상시모집</span>
      </div>
    </div>
  </a>
</div>
<div class="box">
  <div class="thumb">
    <a href="review_campaign.php?cp_id=1779353581">
      <img src="./data/campaign/thumb/thumb-1889562815_kNXRFzGn_EC95B0ED948C_300x300.jpg" class="it_img">
    </a>
  </div>
  <a href="review_campaign.php?cp_id=1779353581">
    <div class="it_info">
      <div class="top_info">
        <div class="sns_info"><span class="sns instagram_reels">인스타그램 릴스</span></div>
        <div class="option2"><span>배송형</span></div>
      </div>
      <span class="it_name">[배송/뷰티] 케O밈</span>
      <span class="it_description">율앰플 50ml</span>
      <div class="option">
        <span><span>모집 <b class="txt_num">18</b></span></span>
        <span class="dday">상시모집</span>
      </div>
    </div>
  </a>
</div>
<div class="box">
  <div class="thumb">
    <a href="review_campaign.php?cp_id=1778118339">
      <img src="./data/campaign/thumb/thumb-1889562815_3PaHudJp_11_300x300.jpg" class="it_img">
    </a>
  </div>
  <a href="review_campaign.php?cp_id=1778118339">
    <div class="it_info">
      <div class="top_info">
        <div class="sns_info"><span class="sns youtube_shorts">유튜브 쇼츠</span></div>
        <div class="option2"><span>배송형</span></div>
      </div>
      <span class="it_name">[쇼츠/배송/식품] 바OO렘</span>
      <span class="it_description">100%국산 청국장환 30포</span>
      <div class="option">
        <span><span>모집 <b class="txt_num">10</b></span></span>
        <span class="dday">상시모집</span>
      </div>
    </div>
  </a>
</div>
`;

process.env.PAVLO_LIST_SCOPE = "";
assert.ok(getPavloConfigs().some((config) => config.categoryId === "001A"), "default configs include delivery");

process.env.PAVLO_LIST_SCOPE = "delivery";
assert.deepStrictEqual(
  getPavloConfigs().map((config) => config.categoryId),
  ["001A"],
  "delivery scope only requests shipping category",
);

const config = getPavloConfigs()[0];
const parsed = parsePavloListCampaigns(html, { config });
assert.strictEqual(parsed.parsedCount, 3);
assert.strictEqual(parsed.addedCount, 3);
assert.strictEqual(parsed.campaigns.length, 3);

const first = parsed.campaigns.find((campaign) => campaign.id === "pv_1779946581");
assert.ok(first, "first campaign parsed");
assert.strictEqual(first.title, "[배송/생활] 디OO 창신");
assert.strictEqual(first.url, "https://pavlovu.com/review_campaign.php?cp_id=1779946581");
assert.strictEqual(first.type, "delivery");
assert.strictEqual(first.dDay, 99);
assert.strictEqual(first.applyCount, 0);
assert.strictEqual(first.selectedCount, 5);
assert.strictEqual(first.point, "카메라 스트랩");
assert.strictEqual(
  first.imageUrl,
  "https://pavlovu.com/data/campaign/thumb/thumb-1889562815_1f6H7DC4_2_EC8AA4ED8AB8EB9EA9_EC8DB8_300x300.jpg",
);

const second = parsed.campaigns.find((campaign) => campaign.id === "pv_1779353581");
assert.ok(second, "second campaign parsed");
assert.strictEqual(second.title, "[배송/뷰티] 케O밈");
assert.strictEqual(second.type, "delivery");
assert.strictEqual(second.selectedCount, 18);
assert.strictEqual(second.point, "율앰플 50ml");

const third = parsed.campaigns.find((campaign) => campaign.id === "pv_1778118339");
assert.ok(third, "third campaign parsed");
assert.strictEqual(third.title, "[쇼츠/배송/식품] 바OO렘");
assert.strictEqual(third.type, "delivery");
assert.strictEqual(third.selectedCount, 10);
assert.strictEqual(third.point, "100%국산 청국장환 30포");

const seenIds = new Set(["pv_1779946581"]);
const deduped = parsePavloListCampaigns(html, { config, seenIds });
assert.strictEqual(deduped.parsedCount, 3);
assert.strictEqual(deduped.addedCount, 2);
assert.ok(seenIds.has("pv_1779353581"), "new campaign id added to seen set");

console.log(JSON.stringify({ ok: true, parsedCount: parsed.parsedCount, addedCount: parsed.addedCount }, null, 2));

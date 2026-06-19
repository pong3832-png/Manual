const assert = require("assert");

process.env.CRAWLER_TEST_EXPORTS = "1";

const { getComeplayConfigs, parseComeplayListCampaigns } = require("../crawler/crawl.cjs");

const html = `
<li>
  <div class="thumb">
    <a href="item.php?it_id=1780027517&amp;category_id=002">
      <img src="./data/list/thumb/thumb-1780027602ECA784_270x270.jpg" alt="" class="it_img">
    </a>
  </div>
  <a href="item.php?it_id=1780027517&amp;category_id=002">
    <div class="it_info">
      <span class="it_name">[쇼핑몰] 어릴 적 분식집에서 즐겨먹던, 수제로 직접 빚어 만든 야끼만두 전문쇼핑몰</span>
      <span class="it_description">#에어프라이어만두 #야끼만두</span>
    </div>
    <div class="option_re">
      <span class="txt_num">D-day 5</span>
      <i class="blog"></i>
      <span class="peo_cnt">신청 <b class="txt_num point_color4">3</b> 명 / 모집 <b class="txt_num">10</b> 명</span>
    </div>
  </a>
</li>
<li>
  <div class="thumb">
    <a href="item.php?it_id=1780020122&amp;category_id=002">
      <img src="./data/list/thumb/thumb-1780020140AQH_00_270x270.png" alt="" class="it_img">
    </a>
  </div>
  <a href="item.php?it_id=1780020122&amp;category_id=002">
    <div class="it_info">
      <span class="it_name">[쇼핑몰] 소변기 노란 얼룩제거 및 악취제거에 탁월한 소변기탈취제 [올그린코리아]</span>
      <span class="it_description">#소변기탈취제 #요석제거제 #변기찌든때 #변기악취제거</span>
    </div>
    <div class="option_re">
      <span class="txt_num">D-day 9</span>
      <i class="blog"></i>
      <span class="peo_cnt">신청 <b class="txt_num point_color4">1</b> 명 / 모집 <b class="txt_num">5</b> 명</span>
    </div>
  </a>
</li>
<li>
  <div class="thumb">
    <a href="item.php?it_id=1780020082&amp;category_id=002">
      <img src="./data/list/thumb/thumb-1780020099ECA784_270x270.jpg" alt="" class="it_img">
    </a>
  </div>
  <a href="item.php?it_id=1780020082&amp;category_id=002">
    <div class="it_info">
      <span class="it_name">[쇼핑몰] 옥수수추출물로 청정세상! 세탁조클리너 쇼핑몰 [올그린코리아]</span>
      <span class="it_description">#세탁조클리너 #세탁기클리너 #드럼세탁기청소 #세탁조청소 #세탁기소독</span>
    </div>
    <div class="option_re">
      <span class="txt_num">D-day 9</span>
      <i class="blog"></i>
      <span class="peo_cnt">신청 <b class="txt_num point_color4">1</b> 명 / 모집 <b class="txt_num">10</b> 명</span>
    </div>
  </a>
</li>
`;

process.env.COMEPLAY_LIST_SCOPE = "";
assert.ok(getComeplayConfigs().some((config) => config.categoryId === "002"), "default configs include product");

process.env.COMEPLAY_LIST_SCOPE = "delivery";
assert.deepStrictEqual(
  getComeplayConfigs().map((config) => config.categoryId),
  ["002"],
  "delivery scope only requests product category",
);

const config = getComeplayConfigs()[0];
const parsed = parseComeplayListCampaigns(html, { config });
assert.strictEqual(parsed.parsedCount, 3);
assert.strictEqual(parsed.addedCount, 3);
assert.strictEqual(parsed.campaigns.length, 3);

const first = parsed.campaigns.find((campaign) => campaign.id === "cply_1780027517");
assert.ok(first, "first campaign parsed");
assert.strictEqual(first.title, "[쇼핑몰] 어릴 적 분식집에서 즐겨먹던, 수제로 직접 빚어 만든 야끼만두 전문쇼핑몰");
assert.strictEqual(first.url, "https://www.cometoplay.kr/item.php?it_id=1780027517&category_id=002");
assert.strictEqual(first.type, "delivery");
assert.strictEqual(first.dDay, 5);
assert.strictEqual(first.applyCount, 3);
assert.strictEqual(first.selectedCount, 10);
assert.strictEqual(first.point, null);
assert.strictEqual(first.imageUrl, "https://www.cometoplay.kr/data/list/thumb/thumb-1780027602ECA784_270x270.jpg");

const second = parsed.campaigns.find((campaign) => campaign.id === "cply_1780020122");
assert.ok(second, "second campaign parsed");
assert.strictEqual(second.type, "delivery");
assert.strictEqual(second.dDay, 9);
assert.strictEqual(second.applyCount, 1);
assert.strictEqual(second.selectedCount, 5);

const third = parsed.campaigns.find((campaign) => campaign.id === "cply_1780020082");
assert.ok(third, "third campaign parsed");
assert.strictEqual(third.type, "delivery");
assert.strictEqual(third.dDay, 9);
assert.strictEqual(third.applyCount, 1);
assert.strictEqual(third.selectedCount, 10);

const seenIds = new Set(["cply_1780027517"]);
const deduped = parseComeplayListCampaigns(html, { config, seenIds });
assert.strictEqual(deduped.parsedCount, 3);
assert.strictEqual(deduped.addedCount, 2);
assert.ok(seenIds.has("cply_1780020122"), "new campaign id added to seen set");

console.log(JSON.stringify({ ok: true, parsedCount: parsed.parsedCount, addedCount: parsed.addedCount }, null, 2));

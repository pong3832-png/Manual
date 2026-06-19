const assert = require("node:assert/strict");

process.env.CRAWLER_TEST_EXPORTS = "1";

const {
  buildDinnerqueenListRequest,
  getDinnerqueenListConfigs,
  normalizeCampaignTypeForLaunch,
  parseDinnerqueenListCampaigns,
  parseDinnerqueenListResponse,
  shouldContinueDinnerqueenListPage,
} = require("../crawler/crawl.cjs");

assert.equal(typeof buildDinnerqueenListRequest, "function");
assert.equal(typeof getDinnerqueenListConfigs, "function");
assert.equal(typeof normalizeCampaignTypeForLaunch, "function");
assert.equal(typeof parseDinnerqueenListCampaigns, "function");
assert.equal(typeof parseDinnerqueenListResponse, "function");
assert.equal(typeof shouldContinueDinnerqueenListPage, "function");

const previousScope = process.env.DINNERQUEEN_LIST_SCOPE;
try {
  delete process.env.DINNERQUEEN_LIST_SCOPE;
  assert.deepEqual(getDinnerqueenListConfigs().map((config) => config.label), ["all", "delivery"]);
  process.env.DINNERQUEEN_LIST_SCOPE = "delivery";
  assert.deepEqual(getDinnerqueenListConfigs().map((config) => config.label), ["delivery"]);
} finally {
  if (previousScope === undefined) {
    delete process.env.DINNERQUEEN_LIST_SCOPE;
  } else {
    process.env.DINNERQUEEN_LIST_SCOPE = previousScope;
  }
}

assert.equal(normalizeCampaignTypeForLaunch("방문형"), "visit");
assert.equal(normalizeCampaignTypeForLaunch("배송형"), "delivery");
assert.equal(normalizeCampaignTypeForLaunch("기자단"), "reporter");
assert.equal(normalizeCampaignTypeForLaunch("릴스"), "reels");

const deliveryRequest = buildDinnerqueenListRequest(
  { label: "delivery", ct: "\uBC30\uC1A1", fallbackType: "delivery" },
  3,
);
assert.deepEqual(deliveryRequest.params, {
  ct: "\uBC30\uC1A1",
  area1: "\uC804\uAD6D",
  area2: "\uC804\uCCB4",
  page: 3,
  ctype: "",
  query: "",
});
assert.equal("lpage" in deliveryRequest.params, false);
assert.equal("order" in deliveryRequest.params, false);
assert.equal("deal" in deliveryRequest.params, false);
assert.equal("cate" in deliveryRequest.params, false);
assert.equal("sns[]" in deliveryRequest.params, false);
assert.match(deliveryRequest.referer, /lpage=3/);
assert.match(deliveryRequest.referer, /query=&deal=&cate=&order=/);
assert.match(deliveryRequest.referer, /ctype=$/);

const html = `
  <div class="qz-col pc2 lt3 tb2 mb2 mr-b7 mb-mr-b5">
    <div class="qz-dq-card qz-button fluid hover">
      <a class="qz-dq-card__link" href="/taste/1375906" title="[랜덤픽] 마샬 액톤3 스피커 (블루투스) 신청하기">
        <div class="qz-dq-card__link__img">
          <img src="https://dq-files.gcdn.ntruss.com/posts/019e4e72-8a62-739d-9c16-9272b2c52730.webp" alt="[랜덤픽] 마샬 액톤3 스피커 (블루투스)">
        </div>
      </a>
      <div class="qz-dq-card__text">
        <div class="layer-primary"><p><strong>D-24</strong></p></div>
        <p><strong>배송</strong></p>
        <p><strong>랜덤픽</strong></p>
        <p class="qz-body2-kr--line ellipsis color-title">[랜덤픽] 마샬 액톤3 스피커 (블루투스)</p>
        <p class="apply_badge"><span>신청 675</span><span> / 모집 1</span></p>
      </div>
    </div>
  </div>
  <div class="qz-col pc2 lt3 tb2 mb2 mr-b7 mb-mr-b5">
    <div class="qz-dq-card qz-button fluid hover">
      <a class="qz-dq-card__link" href="/taste/1363565" title="[랜덤픽] 신세계 상품권 30만원권 신청하기">
        <img src="https://dq-files.gcdn.ntruss.com/posts/019e2a3c-dfc8-777a-9b88-862dcfa41ffd.webp" alt="[랜덤픽] 신세계 상품권 30만원권">
      </a>
      <div class="qz-dq-card__text">
        <p><strong>D-17</strong></p>
        <p><strong>배송</strong></p>
        <p class="apply_badge"><span>신청 405</span><span> / 모집 1</span></p>
      </div>
    </div>
  </div>
  <div class="qz-col pc2 lt3 tb2 mb2 mr-b7 mb-mr-b5">
    <div class="qz-dq-card qz-button fluid hover">
      <a class="qz-dq-card__link" href="/taste/1352337" title="[랜덤픽] 키크론 무선 키보드 (K10 PRO SE2) 신청하기">
        <img src="https://dq-files.gcdn.ntruss.com/posts/019e06e6-5598-77d0-9776-e6074bae4984.webp" alt="[랜덤픽] 키크론 무선 키보드 (K10 PRO SE2)">
      </a>
      <div class="qz-dq-card__text">
        <p><strong>D-10</strong></p>
        <p><strong>배송</strong></p>
        <p class="apply_badge"><span>신청 2,144</span><span> / 모집 1</span></p>
      </div>
    </div>
  </div>
`;

const parsed = parseDinnerqueenListCampaigns(html, { fallbackType: "delivery" });
assert.equal(parsed.parsedCount, 3);
assert.equal(parsed.addedCount, 3);
assert.equal(parsed.campaigns.length, 3);

const first = parsed.campaigns[0];
assert.equal(first.id, "dq_1375906");
assert.equal(first.title, "[랜덤픽] 마샬 액톤3 스피커 (블루투스)");
assert.equal(first.url, "https://dinnerqueen.net/taste/1375906");
assert.equal(first.type, "delivery");
assert.equal(first.dDay, 24);
assert.equal(first.applyCount, 675);
assert.equal(first.selectedCount, 1);
assert.equal(first.imageUrl, "https://dq-files.gcdn.ntruss.com/posts/019e4e72-8a62-739d-9c16-9272b2c52730.webp");

assert.equal(parsed.campaigns[1].applyCount, 405);
assert.equal(parsed.campaigns[1].selectedCount, 1);
assert.equal(parsed.campaigns[2].applyCount, 2144);
assert.equal(parsed.campaigns[2].selectedCount, 1);

const seenIds = new Set(["dq_1375906"]);
const deduped = parseDinnerqueenListCampaigns(html, { seenIds, fallbackType: "delivery" });
assert.equal(deduped.parsedCount, 3);
assert.equal(deduped.addedCount, 2);
assert.equal(deduped.campaigns[0].id, "dq_1363565");

const pageResult = parseDinnerqueenListResponse(JSON.stringify({ layout: html, has_next: true }));
assert.equal(pageResult.hasNext, true);
assert.equal(parseDinnerqueenListCampaigns(pageResult.layout, { fallbackType: "delivery" }).parsedCount, 3);

const terminalPageResult = parseDinnerqueenListResponse(JSON.stringify({ layout: "[]", has_next: false }));
assert.equal(terminalPageResult.layout, "[]");
assert.equal(terminalPageResult.hasNext, false);
assert.equal(parseDinnerqueenListCampaigns(terminalPageResult.layout, { fallbackType: "delivery" }).parsedCount, 0);

assert.equal(shouldContinueDinnerqueenListPage({ parsedCount: 3, addedOnPage: 3, hasNext: true }), true);
assert.equal(shouldContinueDinnerqueenListPage({ parsedCount: 3, addedOnPage: 3, hasNext: false }), false);
assert.equal(shouldContinueDinnerqueenListPage({ parsedCount: 3, addedOnPage: 0, hasNext: true }), true);
assert.equal(shouldContinueDinnerqueenListPage({ parsedCount: 3, addedOnPage: 0, hasNext: null }), false);
assert.equal(shouldContinueDinnerqueenListPage({ parsedCount: 0, addedOnPage: 0, hasNext: true }), false);

console.log(JSON.stringify({ ok: true, campaigns: parsed.campaigns.length }, null, 2));

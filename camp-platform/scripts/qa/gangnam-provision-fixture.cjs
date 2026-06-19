const assert = require("assert");
const cheerio = require("cheerio");

process.env.CRAWLER_TEST_EXPORTS = "1";

const {
  applyGangnamDetailLocationEnrichment,
  extractGangnamProvisionFromDetail,
  parseGangnamListCampaigns,
} = require("../crawler/crawl.cjs");

const samples = [
  {
    name: "voucher with guide note",
    html: `
      <p class="sub_tit">
        <a href="https://naver.me/50eZteBL" alt="업체 홈페이지 링크" target="_blank" style="font-size:15px; color:#000; margin-left:0px;">5만 원 체험권(2인기준)<br>자세한 상품은 가이드를 참고해주세요</a>
      </p>
    `,
    expectedIncludes: [
      "5만 원 체험권",
      "2인기준",
      "자세한 상품은 가이드를 참고해주세요",
    ],
  },
  {
    name: "single body correction voucher",
    html: `
      <p class="sub_tit">
        <a href="https://naver.me/IDbDcI5j" alt="업체 홈페이지 링크" target="_blank" style="font-size:15px; color:#000; margin-left:0px;">1회 체형교정 체험권 (1인 기준, 10만원 상당)</a>
      </p>
    `,
    expectedIncludes: [
      "1회 체형교정 체험권",
      "10만원 상당",
    ],
  },
];

assert.equal(
  typeof extractGangnamProvisionFromDetail,
  "function",
  "extractGangnamProvisionFromDetail must be exported",
);
assert.equal(
  typeof parseGangnamListCampaigns,
  "function",
  "parseGangnamListCampaigns must be exported",
);
assert.equal(
  typeof applyGangnamDetailLocationEnrichment,
  "function",
  "applyGangnamDetailLocationEnrichment must be exported",
);

const productListHtml = `
  <li class="list_item " data-ach="" data-product="2153098" data-no="2">
    <div>
      <div class="imgArea" style="height: 196px;">
        <a href="/cp/?id=2153098" ref="nosublink">
          <img src="//gangnam-review.net/data/file/cmp/2026/04/24/thumb-cmp_2153098-0ad8897f89a44dd0d2510c63b555b980435f398d_300x300.jpg" class="thumb_img" alt="캠페인">
        </a>
      </div>
      <div class="textArea">
        <dl>
          <span class="label"><em class="blog">Blog</em><em class="type">배송형</em><span class="dday"><em class="day_c">2일 남음</em></span></span>
          <dt class="tit"><a href="/cp/?id=2153098">롯데상품권</a></dt>
          <dd class="sub_tit">롯데상품권 (30만원)</dd>
        </dl>
        <div class="item_detail"><p class="item_info"><span class="numb"><b style="color:#000">신청 4,180</b> / 모집 1</span></p></div>
      </div>
    </div>
  </li>
  <li class="list_item " data-ach="" data-product="2189184" data-no="13">
    <div>
      <div class="imgArea" style="height: 196px;">
        <a href="/cp/?id=2189184" ref="nosublink">
          <img src="//gangnam-review.net/data/file/cmp/2026/05/27/thumb-cmp_2189184-9f2d6c590c04ed7f7de93297c878ef2dc5d56fb2_300x300.png" class="thumb_img" alt="캠페인">
        </a>
      </div>
      <div class="textArea">
        <dl>
          <span class="label"><em class="blog">Blog</em><em class="type">배송형</em><span class="dday"><em class="day_c">6일 남음</em></span></span>
          <dt class="tit"><a href="/cp/?id=2189184">마라도회식당</a></dt>
          <dd class="sub_tit">물회 밀키트 체험권</dd>
        </dl>
        <div class="item_detail"><p class="item_info"><span class="numb"><b style="color:#000">신청 56</b> / 모집 20</span></p></div>
      </div>
    </div>
  </li>
`;

const productCampaigns = parseGangnamListCampaigns(productListHtml, { category: "30" });
assert.equal(productCampaigns.length, 2);

assert.deepEqual(
  {
    id: productCampaigns[0].id,
    title: productCampaigns[0].title,
    url: productCampaigns[0].url,
    type: productCampaigns[0].type,
    dDay: productCampaigns[0].dDay,
    applyCount: productCampaigns[0].applyCount,
    selectedCount: productCampaigns[0].selectedCount,
    point: productCampaigns[0].point,
    imageUrl: productCampaigns[0].imageUrl,
    coordinateSource: productCampaigns[0].coordinateSource,
  },
  {
    id: "gn_2153098",
    title: "롯데상품권",
    url: "https://xn--939au0g4vj8sq.net/cp/?id=2153098",
    type: "delivery",
    dDay: 2,
    applyCount: 4180,
    selectedCount: 1,
    point: "롯데상품권 (30만원)",
    imageUrl: "https://gangnam-review.net/data/file/cmp/2026/04/24/thumb-cmp_2153098-0ad8897f89a44dd0d2510c63b555b980435f398d_300x300.jpg",
    coordinateSource: "unresolved",
  },
);

assert.equal(productCampaigns[1].id, "gn_2189184");
assert.equal(productCampaigns[1].type, "delivery");
assert.equal(productCampaigns[1].point, "물회 밀키트 체험권");
assert.equal(productCampaigns[1].selectedCount, 20);

const deliveryCampaign = { type: "delivery", coordinateSource: "unresolved" };
applyGangnamDetailLocationEnrichment(deliveryCampaign, {
  extractedAddress: "서울 강남구 테헤란로 1",
  coords: { lat: 37.5, lng: 127.1, coordinateSource: "html" },
});
assert.equal(deliveryCampaign.addressRaw, undefined);
assert.equal(deliveryCampaign.lat, undefined);
assert.equal(deliveryCampaign.coordinateSource, "unresolved");

const visitCampaign = { type: "visit", coordinateSource: "unresolved" };
applyGangnamDetailLocationEnrichment(visitCampaign, {
  extractedAddress: "서울 강남구 테헤란로 1",
  coords: { lat: 37.5, lng: 127.1, coordinateSource: "html" },
});
assert.equal(visitCampaign.addressRaw, "서울 강남구 테헤란로 1");
assert.equal(visitCampaign.lat, 37.5);
assert.equal(visitCampaign.coordinateSource, "html");

for (const sample of samples) {
  const $ = cheerio.load(sample.html);
  const actual = extractGangnamProvisionFromDetail($);
  assert.ok(actual, `${sample.name}: expected provision text`);
  for (const expected of sample.expectedIncludes) {
    assert.ok(actual.includes(expected), `${sample.name}: missing "${expected}" in "${actual}"`);
  }
}

console.log(JSON.stringify({ ok: true, samples: samples.length }, null, 2));

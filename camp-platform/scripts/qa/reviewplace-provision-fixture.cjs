const assert = require("assert");
const cheerio = require("cheerio");

process.env.CRAWLER_TEST_EXPORTS = "1";

const { extractReviewplaceProvisionFromDetail } = require("../crawler/crawl.cjs");

const samples = [
  {
    name: "sauna admission and extras",
    html: `
      <dd class="bstyle">
        보리사우나 입장권(최대 2인/10시간까지 이용가능) + 음료 및 간식, 내부식당 메뉴 중 선택 1가지 무료제공 + 추가서비스(방문인원 중 1인 한정)
      </dd>
    `,
    expectedIncludes: [
      "보리사우나 입장권",
      "음료 및 간식",
      "내부식당 메뉴 중 선택 1가지 무료제공",
      "추가서비스",
    ],
  },
  {
    name: "gym pass and pt",
    html: `
      <dd class="bstyle">
        헬스1개월권 + PT2회
      </dd>
    `,
    expectedIncludes: [
      "헬스1개월권",
      "PT2회",
    ],
  },
];

assert.equal(
  typeof extractReviewplaceProvisionFromDetail,
  "function",
  "extractReviewplaceProvisionFromDetail must be exported",
);

for (const sample of samples) {
  const $ = cheerio.load(sample.html);
  const actual = extractReviewplaceProvisionFromDetail($);
  assert.ok(actual, `${sample.name}: expected provision text`);
  for (const expected of sample.expectedIncludes) {
    assert.ok(actual.includes(expected), `${sample.name}: missing "${expected}" in "${actual}"`);
  }
}

console.log(JSON.stringify({ ok: true, samples: samples.length }, null, 2));

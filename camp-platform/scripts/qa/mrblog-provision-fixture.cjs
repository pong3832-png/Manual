const assert = require("assert");
const cheerio = require("cheerio");

process.env.CRAWLER_TEST_EXPORTS = "1";

const { extractMrblogProvisionFromDetail } = require("../crawler/crawl.cjs");

const samples = [
  {
    name: "single paragraph product block",
    html: `
      <div class="info_row">
        <dl>
          <dt>체험 상품</dt>
          <dd>
            <strong class="c_blue">
              <p>1인 - 프렌치토스트1개 + 음료1잔 + 진한 밀크아이스크림<br>
              2인 - 프렌치토스트1개 + 음료2잔 +&nbsp;진한 밀크아이스크림</p>
            </strong>
          </dd>
        </dl>
      </div>
    `,
    expectedIncludes: [
      "1인 - 프렌치토스트1개 + 음료1잔 + 진한 밀크아이스크림",
      "2인 - 프렌치토스트1개 + 음료2잔 + 진한 밀크아이스크림",
    ],
  },
  {
    name: "multi paragraph product block",
    html: `
      <div class="info_row">
        <dl>
          <dt>체험 상품</dt>
          <dd>
            <strong class="c_blue">
              <p>[블로그 체험]<br>
              저녁체험 : 이모카세 2인 10만원 할인권 (4만원 개인부담)<br>
              <br>
              ** 블로그리뷰1개+영수증리뷰1개 필수</p>
              <p>** 업체 인스타 팔로우 필수 !&nbsp;</p>
              <p>-&nbsp;https://www.instagram.com/4season_imokase</p>
            </strong>
          </dd>
        </dl>
      </div>
    `,
    expectedIncludes: [
      "[블로그 체험]",
      "이모카세 2인 10만원 할인권",
      "블로그리뷰1개+영수증리뷰1개 필수",
      "업체 인스타 팔로우 필수",
    ],
  },
];

for (const sample of samples) {
  const $ = cheerio.load(sample.html);
  const actual = extractMrblogProvisionFromDetail($);
  assert.ok(actual, `${sample.name}: expected provision text`);
  for (const expected of sample.expectedIncludes) {
    assert.ok(actual.includes(expected), `${sample.name}: missing "${expected}" in "${actual}"`);
  }
}

console.log(JSON.stringify({ ok: true, samples: samples.length }, null, 2));

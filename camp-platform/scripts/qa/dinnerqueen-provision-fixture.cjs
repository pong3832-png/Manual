const assert = require("assert");
const cheerio = require("cheerio");

process.env.CRAWLER_TEST_EXPORTS = "1";

const { extractDinnerqueenProvisionFromDetail } = require("../crawler/crawl.cjs");

const samples = [
  {
    name: "multi option provided items",
    html: `
      <p class="qz-body-kr mb-qz-body2-kr">
        <strong class="w-600">1번 2번 중 택1<br>
        1.키토3종(트러플키토마요+묵참키토마요+매운파김치삼겹키토)+보슬마늘떡볶이(1인분)+반반쌈밥(제육4p+차돌4p)<br>
        2.반반쌈밥(제육4p+차돌4p)+매운파김치삼겹김밥+묵은지참치말이</strong>
      </p>
    `,
    expectedIncludes: [
      "1번 2번 중 택1",
      "키토3종",
      "보슬마늘떡볶이",
      "매운파김치삼겹김밥",
    ],
  },
  {
    name: "single voucher provided item",
    html: `
      <p class="qz-body-kr mb-qz-body2-kr">
        <strong class="w-600">40,000원 이용권 제공  (치즈불고기 신메뉴 필수이용)</strong>
      </p>
    `,
    expectedIncludes: [
      "40,000원 이용권 제공",
      "치즈불고기 신메뉴 필수이용",
    ],
  },
  {
    name: "collapse section provided item",
    html: `
      <div class="qz-collapse qz-row mr-b6 tb-mr-b3">
        <div class="qz-col pc2 tb6 tb-mr-b1 mb-mr-b05">
          <h5 class="dis-inline-block font-0">
            <strong class="qz-h6-kr mb-qz-body-kr dis-inline-block ver-m mr-l05 pd-l05">제공 내역</strong>
          </h5>
        </div>
        <div class="qz-col pc5 pc-r5 tb6 tb-r0">
          <div class="qz-collapse__content tb-pd-l4">
            <p class="qz-body-kr mb-qz-body2-kr">
              <strong class="w-600">2인 기본 세팅 6만원 세트</strong>
            </p>
            <div class="qz-wrap qz-container layer-primary-dq-o mr-t2 pd-2 pd-t015 mb-pd-t1 mb-mr-t015">
              <p class="qz-body-kr"><strong>참여 전 필수 확인사항</strong></p>
              <p class="qz-body-kr mb-qz-body2-kr color-title">※ 추가 비용 발생 시 별도 지불 (음료/주류 포함)</p>
            </div>
          </div>
        </div>
      </div>
    `,
    expectedIncludes: [
      "2인 기본 세팅 6만원 세트",
    ],
    expectedExcludes: [
      "참여 전 필수 확인사항",
      "추가 비용 발생",
    ],
  },
  {
    name: "collapse section wins over unrelated strong text",
    html: `
      <p class="qz-body-kr mb-qz-body2-kr">
        <strong class="w-600">캠페인 안내 문구</strong>
      </p>
      <div class="qz-collapse qz-row mr-b6 tb-mr-b3">
        <div class="qz-col pc2 tb6 tb-mr-b1 mb-mr-b05">
          <h5>
            <strong class="qz-h6-kr mb-qz-body-kr">제공 내역</strong>
          </h5>
        </div>
        <div class="qz-col pc5 pc-r5 tb6 tb-r0">
          <div class="qz-collapse__content tb-pd-l4">
            <p class="qz-body-kr mb-qz-body2-kr">
              <strong class="w-600">2인 기본 세팅 6만원 세트</strong>
            </p>
          </div>
        </div>
      </div>
    `,
    expectedIncludes: [
      "2인 기본 세팅 6만원 세트",
    ],
    expectedExcludes: [
      "캠페인 안내 문구",
    ],
  },
];

assert.equal(
  typeof extractDinnerqueenProvisionFromDetail,
  "function",
  "extractDinnerqueenProvisionFromDetail must be exported",
);

for (const sample of samples) {
  const $ = cheerio.load(sample.html);
  const actual = extractDinnerqueenProvisionFromDetail($);
  assert.ok(actual, `${sample.name}: expected provision text`);
  for (const expected of sample.expectedIncludes) {
    assert.ok(actual.includes(expected), `${sample.name}: missing "${expected}" in "${actual}"`);
  }
  for (const excluded of sample.expectedExcludes || []) {
    assert.ok(!actual.includes(excluded), `${sample.name}: should not include "${excluded}" in "${actual}"`);
  }
}

console.log(JSON.stringify({ ok: true, samples: samples.length }, null, 2));

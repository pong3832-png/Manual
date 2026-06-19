const assert = require("node:assert/strict");

process.env.CRAWLER_TEST_EXPORTS = "1";

const {
  buildTqueensListRequest,
  extractTqueensProvisionFromDetail,
  parseTqueensListCampaigns,
  parseTqueensListResponse,
} = require("../crawler/crawl.cjs");

assert.equal(typeof buildTqueensListRequest, "function", "buildTqueensListRequest must be exported");
assert.equal(typeof extractTqueensProvisionFromDetail, "function", "extractTqueensProvisionFromDetail must be exported");
assert.equal(typeof parseTqueensListCampaigns, "function", "parseTqueensListCampaigns must be exported");
assert.equal(typeof parseTqueensListResponse, "function", "parseTqueensListResponse must be exported");

const request = buildTqueensListRequest(3);
assert.deepEqual(request.params, {
  area1: "",
  area2: "",
  cate: "",
  page: 3,
  query: "",
  deal: "",
});
assert.match(request.referer, /lpage=3/);
assert.match(request.referer, /query=&deal=&cate=&order=&area1=&area2=/);

const html = `
  <div class="qz-col pc3 lt3 tb2 mb2 mr-b6 mb-mr-b4 font-0">
    <div class="qz-dq-card qz-button fluid hover">
      <a class="qz-dq-card__link quarter" href="/taste/1384253" title="[\uB9B4\uC2A4][\uC7A1\uC2A4] \uBC14\uD034\uC0B4\uCDA9\uC81C \uCE90\uCE58\uB9E8 \uC7A1\uC2A4 \uC6B8\uD2B8\uB77C\uC5D0\uC5B4\uB85C\uC194 \uC2E0\uCCAD\uD558\uAE30">
        <div class="qz-dq-card__link__img">
          <img src="https://dq-files.gcdn.ntruss.com/sales/019e68f2-7357-77ae-8b4a-036effb86063.webp" alt="[\uB9B4\uC2A4][\uC7A1\uC2A4] \uBC14\uD034\uC0B4\uCDA9\uC81C \uCE90\uCE58\uB9E8 \uC7A1\uC2A4 \uC6B8\uD2B8\uB77C\uC5D0\uC5B4\uB85C\uC194">
        </div>
      </a>
      <div class="qz-dq-card__text">
        <div class="qz-wrap mr-t015">
          <p class="qz-badge m layer-primary mr-b005 ver-t"><strong>D-6</strong></p>
          <p class="qz-body2-kr color-primary-dq dis-none"><strong class="keep-a">\uBC30\uC1A1\uD615</strong></p>
        </div>
        <p class="qz-body-kr--line mb-qz-body2-kr--line ellipsis color-title mr-t1">
          <strong class="keep-a">[\uB9B4\uC2A4][\uC7A1\uC2A4] \uBC14\uD034\uC0B4\uCDA9\uC81C \uCE90\uCE58\uB9E8 \uC7A1\uC2A4 \uC6B8\uD2B8\uB77C\uC5D0\uC5B4\uB85C\uC194</strong>
        </p>
        <p class="qz-body2-kr--line mb-qz-caption-kr--line ellipsis color-placeholder mr-t1">
          \uCE90\uCE58\uB9E8 \uC7A1\uC2A4 \uC6B8\uD2B8\uB77C\uC5D0\uC5B4\uB85C\uC194 500ml
        </p>
      </div>
    </div>
  </div>
  <div class="qz-col pc3 lt3 tb2 mb2 mr-b6 mb-mr-b4 font-0">
    <div class="qz-dq-card qz-button fluid hover">
      <a class="qz-dq-card__link quarter" href="/taste/1385863" title="[\uB808\uB189\uD2F0] \uC2DC\uB108\uC5C5 \uCF5C\uB77C\uAC90 \uC2E0\uCCAD\uD558\uAE30">
        <div class="qz-dq-card__link__img">
          <img src="https://dq-files.gcdn.ntruss.com/sales/019e6d83-af98-732e-91f0-ac1a76f94fa3.webp" alt="[\uB808\uB189\uD2F0] \uC2DC\uB108\uC5C5 \uCF5C\uB77C\uAC90">
        </div>
      </a>
      <div class="qz-dq-card__text">
        <div class="qz-wrap mr-t015">
          <p class="qz-badge m layer-primary mr-b005 ver-t"><strong>D-6</strong></p>
          <p class="qz-body2-kr color-primary-dq dis-none"><strong class="keep-a">\uBC30\uC1A1\uD615</strong></p>
        </div>
        <p class="qz-body-kr--line mb-qz-body2-kr--line ellipsis color-title mr-t1">
          <strong class="keep-a">[\uB808\uB189\uD2F0] \uC2DC\uB108\uC5C5 \uCF5C\uB77C\uAC90</strong>
        </p>
        <p class="qz-body2-kr--line mb-qz-caption-kr--line ellipsis color-placeholder mr-t1">
          \uB808\uB189\uD2F0 \uC2DC\uB108\uC5C5 \uCF5C\uB77C\uAC90 14\uD3EC
        </p>
      </div>
    </div>
  </div>
`;

const parsed = parseTqueensListCampaigns(JSON.stringify({ layout: html, has_next: true }));
assert.equal(parsed.hasNext, true);
assert.equal(parsed.parsedCount, 2);
assert.equal(parsed.addedCount, 2);
assert.equal(parsed.campaigns.length, 2);

assert.deepEqual(
  {
    id: parsed.campaigns[0].id,
    title: parsed.campaigns[0].title,
    url: parsed.campaigns[0].url,
    type: parsed.campaigns[0].type,
    dDay: parsed.campaigns[0].dDay,
    point: parsed.campaigns[0].point,
    imageUrl: parsed.campaigns[0].imageUrl,
  },
  {
    id: "tq_1384253",
    title: "[\uB9B4\uC2A4][\uC7A1\uC2A4] \uBC14\uD034\uC0B4\uCDA9\uC81C \uCE90\uCE58\uB9E8 \uC7A1\uC2A4 \uC6B8\uD2B8\uB77C\uC5D0\uC5B4\uB85C\uC194",
    url: "https://tqueens.net/taste/1384253",
    type: "delivery",
    dDay: 6,
    point: "\uCE90\uCE58\uB9E8 \uC7A1\uC2A4 \uC6B8\uD2B8\uB77C\uC5D0\uC5B4\uB85C\uC194 500ml",
    imageUrl: "https://dq-files.gcdn.ntruss.com/sales/019e68f2-7357-77ae-8b4a-036effb86063.webp",
  },
);
assert.equal(parsed.campaigns[1].id, "tq_1385863");
assert.equal(parsed.campaigns[1].type, "delivery");

const deduped = parseTqueensListCampaigns(html, { seenIds: new Set(["tq_1384253"]) });
assert.equal(deduped.parsedCount, 2);
assert.equal(deduped.addedCount, 1);
assert.equal(deduped.campaigns[0].id, "tq_1385863");

const detailHtml = `
  <p class="qz-body-kr mb-qz-body2-kr">
    <strong class="w-600">\uC720\uAE30\uB18D \uD1A0\uB9C8\uD1A0 \uC5D1\uC2A4\uD2B8\uB77C\uBC84\uC9C4 \uC62C\uB9AC\uBE0C\uC624\uC77C \uC62C\uB9AC\uD1A0\uC0F7 14\uD3EC, 1\uAC1C</strong>
  </p>
`;
assert.equal(
  extractTqueensProvisionFromDetail(detailHtml),
  "\uC720\uAE30\uB18D \uD1A0\uB9C8\uD1A0 \uC5D1\uC2A4\uD2B8\uB77C\uBC84\uC9C4 \uC62C\uB9AC\uBE0C\uC624\uC77C \uC62C\uB9AC\uD1A0\uC0F7 14\uD3EC, 1\uAC1C",
);

assert.equal(parseTqueensListResponse(JSON.stringify({ layout: "[]", has_next: false })).hasNext, false);

console.log(JSON.stringify({ ok: true, campaigns: parsed.campaigns.length }, null, 2));

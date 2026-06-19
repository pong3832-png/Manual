const assert = require("node:assert/strict");
const cheerio = require("cheerio");

process.env.CRAWLER_TEST_EXPORTS = "1";

const {
  applyRingbleDetailEnrichment,
  extractRingbleProvisionFromDetail,
  getCampaignGeocodeQuery,
  isKnownBadMapCoordinate,
  normalizeKakaoGeocodeDocument,
  parseRingbleKoreanDateRange,
  parseRingbleListCampaigns,
} = require("../crawler/crawl.cjs");

assert.equal(typeof applyRingbleDetailEnrichment, "function");
assert.equal(typeof extractRingbleProvisionFromDetail, "function");
assert.equal(typeof getCampaignGeocodeQuery, "function");
assert.equal(typeof isKnownBadMapCoordinate, "function");
assert.equal(typeof normalizeKakaoGeocodeDocument, "function");
assert.equal(typeof parseRingbleKoreanDateRange, "function");
assert.equal(typeof parseRingbleListCampaigns, "function");

const listHtml = `
  <div class="campaigns">
    <a href="/detail.php?number=274969&category=832"><img src="/upload/274969.jpg" alt=""></a>
    <a class="list_title" href="/detail.php?number=274969&category=832">4일 남음</a>
    <a class="list_title" href="/detail.php?number=274969&category=832">[충남/서산시] 소뜰 (식사권)</a>
    <a class="list_title" href="/detail.php?number=275017&category=832">오늘 마감</a>
    <a class="list_title" href="/detail.php?number=275017&category=832">[서울/강남구] 테스트 카페</a>
  </div>
`;

const campaigns = parseRingbleListCampaigns(listHtml);
assert.equal(campaigns.length, 2);

const sample = campaigns.find((campaign) => campaign.id === "ringble_274969");
assert.ok(sample, "expected sample campaign");
assert.equal(sample.title, "[충남/서산시] 소뜰 (식사권)");
assert.equal(sample.url, "https://www.ringble.co.kr/detail.php?number=274969&category=832");
assert.equal(sample.dDay, 4);
assert.equal(sample.locationRaw, "충남 서산시 소뜰");
assert.equal(sample.placeName, "소뜰");
assert.equal(sample.imageUrl, "https://www.ringble.co.kr/upload/274969.jpg");

const todayClose = campaigns.find((campaign) => campaign.id === "ringble_275017");
assert.equal(todayClose.dDay, 0, "today-close should remain open with dDay 0");

const detailHtml = `
  <table>
    <tr>
      <td class="detail_page_title">[충남/서산시] 소뜰 (식사권)</td>
    </tr>
    <tr>
      <td class="bloger_process_title">모집 기간</td>
      <td id="10" class="bloger_process_title">26년 05월 26일(화) ~ 26년 06월 01일(월)</td>
    </tr>
    <tr>
      <td class="bloger_process_title">당첨자 발표일</td>
      <td id="20" class="bloger_process_title">26년 06월 02일(화)</td>
    </tr>
    <tr>
      <td class="bloger_process_title">리뷰 등록기간</td>
      <td id="30" class="bloger_process_title">26년 06월 03일(수) ~ 26년 06월 15일(월)</td>
    </tr>
    <tr>
      <td>제공내역</td>
      <td class="font11">
        [2인] 8만원 식사권 <br>
        (*주문 시 된장찌개 주문 필수)
        <br><font style="color:#0000FF;">+ 링블포인트 2,000점</font>
      </td>
    </tr>
    <tr>
      <td>주소</td>
      <td id="descURL"><a href="https://naver.me/5qRkthtp">https://naver.me/5qRkthtp</a></td>
    </tr>
  </table>
  <div class="detail_list_mem_total_wrap">신청 4 / 모집 21</div>
`;

const $ = cheerio.load(detailHtml);
const provision = extractRingbleProvisionFromDetail($);
assert.ok(provision.includes("8만원 식사권"), provision);
assert.ok(provision.includes("링블포인트 2,000점"), provision);
assert.ok(!provision.includes("모집 기간"), provision);
assert.ok(!provision.includes("리뷰어 신청하기"), provision);

const noisyDetailHtml = `
  <div class="font11">
    오늘 마감 신청 1 / 모집 1 [강원/평창군] 평창 위모텔 (캡슐룸)
    모집 기간 26년 05월 22일(금) ~ 26년 05월 28일(목)
    당첨자 발표일 26년 05월 29일(금)
    리뷰 등록 기간 26년 05월 30일(토) ~ 26년 06월 11일(목)
    리뷰어 신청하기
  </div>
  <table>
    <tr>
      <td>제공내역</td>
      <td class="font11">[1인] 객실 1박 숙박 + 링블포인트 1,000점</td>
    </tr>
  </table>
`;
const noisyProvision = extractRingbleProvisionFromDetail(cheerio.load(noisyDetailHtml));
assert.equal(noisyProvision, "[1인] 객실 1박 숙박 + 링블포인트 1,000점");

const range = parseRingbleKoreanDateRange(
  "26년 05월 26일(화) ~ 26년 06월 01일(월)",
  new Date("2026-05-28T00:00:00+09:00"),
);
assert.equal(range.sourceStartedAt, "2026-05-25T15:00:00.000Z");
assert.equal(range.sourceEndedAt, "2026-05-31T15:00:00.000Z");
assert.equal(range.dDay, 4);

applyRingbleDetailEnrichment(sample, detailHtml, new Date("2026-05-28T00:00:00+09:00"));
assert.equal(sample.applyCount, 4);
assert.equal(sample.selectedCount, 21);
assert.equal(sample.dDay, 4);
assert.equal(sample.point, provision);
assert.equal(sample.sourceLocationUrl, "https://naver.me/5qRkthtp");
assert.equal(sample.addressRaw || "", "");
assert.equal(
  getCampaignGeocodeQuery(sample),
  "",
  "Ringble campaigns with only title region hints and Naver map URLs should not be geocoded",
);

assert.equal(
  getCampaignGeocodeQuery({
    platformId: "ringble",
    title: "[경기/안양시] 오월메이크업",
    locationRaw: "경기 안양시 오월메이크업",
    addressRaw: "경기 안양시",
    placeName: "오월메이크업",
    sourceLocationUrl: "https://m.place.naver.com/place/1416918113",
  }),
  "",
  "Ringble campaigns with only title region text in addressRaw should not be geocoded",
);

assert.equal(
  getCampaignGeocodeQuery({
    platformId: "ringble",
    title: "[경기/안양시] 오월메이크업",
    locationRaw: "경기 안양시 오월메이크업",
    addressRaw: "경기 안양시 오월메이크업",
    placeName: "오월메이크업",
    sourceLocationUrl: "https://m.place.naver.com/place/1416918113",
  }),
  "",
  "Ringble campaigns with only title region and place text in addressRaw should not be geocoded",
);

assert.equal(
  getCampaignGeocodeQuery({
    platformId: "ringble",
    title: "[경기/오산시] 청수식당 오산시청점",
    locationRaw: "경기도 오산시 운암로 13-18 희영빌딩",
    addressRaw: "경기도 오산시 운암로 13-18 희영빌딩",
    placeName: "청수식당 오산시청점",
  }),
  "경기도 오산시 운암로 13-18 희영빌딩",
  "Ringble campaigns with extracted visit addresses should still be geocoded",
);

assert.equal(isKnownBadMapCoordinate(37.574703, 127.002749), true);
assert.equal(
  normalizeKakaoGeocodeDocument(
    { y: "37.574703", x: "127.002749" },
    "kakao_address",
  ),
  null,
  "Known Ringble/Kakao fallback coordinates should not be accepted",
);
assert.deepEqual(
  normalizeKakaoGeocodeDocument(
    { y: "37.1469356435343", x: "127.075244731746" },
    "kakao_address",
  ),
  {
    lat: 37.1469356435343,
    lng: 127.075244731746,
    coordinateSource: "kakao_address",
  },
);

console.log(JSON.stringify({ ok: true, campaigns: campaigns.length }, null, 2));

const assert = require("node:assert/strict");

process.env.CRAWLER_TEST_EXPORTS = "1";

const {
  getTbleConfigs,
  parseTbleListCampaigns,
} = require("../crawler/crawl.cjs");

assert.equal(typeof getTbleConfigs, "function", "getTbleConfigs must be exported");
assert.equal(typeof parseTbleListCampaigns, "function", "parseTbleListCampaigns must be exported");

const previousScope = process.env.TBLE_LIST_SCOPE;
try {
  delete process.env.TBLE_LIST_SCOPE;
  assert.deepEqual(getTbleConfigs().map((config) => config.categoryType), ["l", "p", "r", "c"]);

  process.env.TBLE_LIST_SCOPE = "delivery";
  assert.deepEqual(getTbleConfigs().map((config) => config.categoryType), ["p"]);
  assert.deepEqual(getTbleConfigs().map((config) => config.type), ["delivery"]);
} finally {
  if (previousScope === undefined) {
    delete process.env.TBLE_LIST_SCOPE;
  } else {
    process.env.TBLE_LIST_SCOPE = previousScope;
  }
}

const html = `
  <div class="item">
    <div class="img_in">
      <div class="img">
        <a href="./view.php?cp_id=411178" class="link" style="height: 190px;">
          <img src="https://tble.kr/data/campaign/3551702535_2M5XkWd0" alt="\uCEA0\uD398\uC778 \uC774\uBBF8\uC9C0">
        </a>
      </div>
      <div class="sns_img blog"><img src="/img/sns/sns_blog.png"></div>
    </div>
    <div class="info">
      <a href="./view.php?cp_id=411178" title="[\uBC30\uC1A1] \uBA54\uC774\uB4E0">
        <div class="t1"><span class="ps_remain">6\uC77C \uB0A8\uC74C</span></div>
        <div class="t2">[\uBC30\uC1A1] \uBA54\uC774\uB4E0</div>
        <div class="t3">\uBA54\uC774\uB4E0 \uCC29\uC999\uAE30 \uC2E4\uBC84</div>
        <div class="t4">\uC2E0\uCCAD <strong>620</strong>\uBA85 / <span class="lgray">\uBAA8\uC9D1 <strong>10</strong>\uBA85</span></div>
      </a>
    </div>
  </div>
  <div class="item">
    <div class="img_in">
      <div class="img">
        <a href="./view.php?cp_id=410841" class="link" style="height: 190px;">
          <img src="https://tble.kr/data/campaign/3551702535_kYQIXE4O" alt="\uCEA0\uD398\uC778 \uC774\uBBF8\uC9C0">
        </a>
      </div>
      <div class="sns_img blog"><img src="/img/sns/sns_blog.png"></div>
    </div>
    <div class="info">
      <a href="./view.php?cp_id=410841" title="[\uBC30\uC1A1] \uBE44\uD0C0\uD478\uB4DC\uBAB0">
        <div class="t1"><span class="ps_remain">3\uC77C \uB0A8\uC74C</span></div>
        <div class="t2">[\uBC30\uC1A1] \uBE44\uD0C0\uD478\uB4DC\uBAB0</div>
        <div class="t3">\uBE44\uD0C0\uD478\uB4DC \uB9AC\uD3EC\uC880 \uCCA0\uBD84 \uD4E8\uC5B4C 30\uD3EC</div>
        <div class="t4">\uC2E0\uCCAD <strong>175</strong>\uBA85 / <span class="lgray">\uBAA8\uC9D1 <strong>30</strong>\uBA85</span></div>
      </a>
    </div>
  </div>
`;

const parsed = parseTbleListCampaigns(html, {
  config: { categoryType: "p", type: "delivery" },
});

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
    applyCount: parsed.campaigns[0].applyCount,
    selectedCount: parsed.campaigns[0].selectedCount,
    point: parsed.campaigns[0].point,
    imageUrl: parsed.campaigns[0].imageUrl,
  },
  {
    id: "tble_411178",
    title: "[\uBC30\uC1A1] \uBA54\uC774\uB4E0",
    url: "https://tble.kr/view.php?cp_id=411178",
    type: "delivery",
    dDay: 6,
    applyCount: 620,
    selectedCount: 10,
    point: "\uBA54\uC774\uB4E0 \uCC29\uC999\uAE30 \uC2E4\uBC84",
    imageUrl: "https://tble.kr/data/campaign/3551702535_2M5XkWd0",
  },
);

assert.equal(parsed.campaigns[1].id, "tble_410841");
assert.equal(parsed.campaigns[1].type, "delivery");
assert.equal(parsed.campaigns[1].applyCount, 175);
assert.equal(parsed.campaigns[1].selectedCount, 30);

const deduped = parseTbleListCampaigns(html, {
  config: { categoryType: "p", type: "delivery" },
  seenIds: new Set(["tble_411178"]),
});
assert.equal(deduped.parsedCount, 2);
assert.equal(deduped.addedCount, 1);
assert.equal(deduped.campaigns[0].id, "tble_410841");

console.log(JSON.stringify({ ok: true, campaigns: parsed.campaigns.length }, null, 2));

const assert = require("node:assert/strict");

process.env.CRAWLER_TEST_EXPORTS = "1";

const {
  resolveActiveCrawlers,
} = require("../crawler/crawl.cjs");

assert.equal(typeof resolveActiveCrawlers, "function");

const crawlers = [
  { platformId: "reviewnote", label: "reviewnote" },
  { platformId: "mrblog", label: "mrblog" },
  { platformId: "dinner", label: "dinnerqueen" },
];

assert.deepEqual(
  resolveActiveCrawlers(crawlers).map((crawler) => crawler.platformId),
  ["mrblog", "dinner"],
  "reviewnote should be excluded from the default full crawl",
);

assert.deepEqual(
  resolveActiveCrawlers(crawlers, new Set(["reviewnote"])).map((crawler) => crawler.platformId),
  ["reviewnote"],
  "CRAWL_ONLY=reviewnote should still allow an explicit limited crawl",
);

assert.deepEqual(
  resolveActiveCrawlers(crawlers, new Set(["dinnerqueen"])).map((crawler) => crawler.platformId),
  ["dinner"],
  "CRAWL_ONLY should continue to match crawler labels",
);

console.log(JSON.stringify({ ok: true }, null, 2));

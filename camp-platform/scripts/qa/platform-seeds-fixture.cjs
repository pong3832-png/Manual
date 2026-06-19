const assert = require("node:assert/strict");

process.env.CRAWLER_TEST_EXPORTS = "1";

const { PLATFORM_SEEDS } = require("../crawler/crawl.cjs");

assert.ok(Array.isArray(PLATFORM_SEEDS), "PLATFORM_SEEDS must be exported for QA");

const crawlerPlatformIds = [
  "reviewnote",
  "mrblog",
  "reviewplace",
  "dinner",
  "tqueens",
  "pavlo",
  "seouloba",
  "revu",
  "gangnam",
  "popomon",
  "comeplay",
  "tble",
  "ringble",
  "chvu",
];

const seededPlatformIds = new Set(PLATFORM_SEEDS.map((platform) => platform.id));
const missingSeeds = crawlerPlatformIds.filter((platformId) => !seededPlatformIds.has(platformId));

assert.deepEqual(missingSeeds, [], "every crawler platform must have a Supabase platform seed");

console.log(JSON.stringify({ ok: true }, null, 2));

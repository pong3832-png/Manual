import assert from "node:assert/strict";
import fs from "node:fs";
import dynamicSitemap from "../../src/app/sitemap.js";
import dynamicRobots from "../../src/app/robots.js";
import { SEO_LANDING_PAGES, getLandingPage } from "../../src/seo/landingPages.js";
import { getCampaignsForLanding, getSnapshotUpdatedAt } from "../../src/seo/seoCampaignData.js";

delete process.env.NEXT_PUBLIC_PUBLIC_SITE_URL;
delete process.env.VITE_PUBLIC_SITE_URL;
const defaultSiteConfig = await import("../../src/seo/siteConfig.js?default");

const requiredSlugs = [
  "체험단",
  "블로그체험단",
  "인스타체험단",
  "맛집체험단",
  "서울-맛집-체험단",
  "오늘마감-체험단",
  "디너의여왕-체험단",
];

const newLandingSlugs = [
  "레뷰-체험단",
  "미블-체험단",
  "강남-맛집-체험단",
  "서울-블로그-체험단",
  "부산-카페-체험단",
  "뷰티-체험단-모집",
  "오늘마감-블로그-체험단",
  "배송형-체험단",
  "제품-체험단",
];

assert.equal(defaultSiteConfig.SEO_SITE_URL, "https://camp-platform-liart.vercel.app");
assert.equal(
  defaultSiteConfig.absoluteUrl("/체험단"),
  "https://camp-platform-liart.vercel.app/체험단",
);

process.env.NEXT_PUBLIC_PUBLIC_SITE_URL = "https://camp-platform-liart.vercel.app/";
const previewSiteConfig = await import("../../src/seo/siteConfig.js?preview");
assert.equal(previewSiteConfig.SEO_SITE_URL, "https://camp-platform-liart.vercel.app");
assert.equal(
  previewSiteConfig.absoluteUrl("/체험단"),
  "https://camp-platform-liart.vercel.app/체험단",
);
delete process.env.NEXT_PUBLIC_PUBLIC_SITE_URL;

for (const slug of requiredSlugs) {
  const page = getLandingPage(slug);
  assert.ok(page, `missing landing page: ${slug}`);
  assert.ok(page.title.includes("체험단"), `title should include 체험단: ${slug}`);
  assert.ok(page.description.length >= 20, `description too short: ${slug}`);
  assert.ok(page.h1.length >= 6, `h1 too short: ${slug}`);
}

for (const slug of newLandingSlugs) {
  const page = getLandingPage(slug);
  assert.ok(page, `missing new landing page: ${slug}`);
  const campaigns = getCampaignsForLanding(page, 5);
  assert.ok(campaigns.length > 0, `new landing should have campaigns: ${slug}`);
}

assert.equal(getLandingPage("리뷰노트-체험단"), null);

const duplicateSlugs = SEO_LANDING_PAGES
  .map((page) => page.slug)
  .filter((slug, index, slugs) => slugs.indexOf(slug) !== index);
assert.deepEqual(duplicateSlugs, []);

const robotsSource = fs.readFileSync(new URL("../../public/robots.txt", import.meta.url), "utf8");
const dynamicRobotsConfig = dynamicRobots();
assert.ok(
  robotsSource.includes(`Sitemap: ${defaultSiteConfig.SEO_SITE_URL}/sitemap.xml`),
  "robots.txt should point to the canonical sitemap URL",
);
assert.ok(
  robotsSource.includes(`Sitemap: ${defaultSiteConfig.SEO_SITE_URL}/sitemap-pages.xml`),
  "robots.txt should point to the alternate sitemap URL",
);
assert.deepEqual(
  dynamicRobotsConfig.sitemap,
  [
    `${defaultSiteConfig.SEO_SITE_URL}/sitemap.xml`,
    `${defaultSiteConfig.SEO_SITE_URL}/sitemap-pages.xml`,
  ],
  "dynamic robots route should expose both sitemap URLs",
);

const sitemapSource = fs.readFileSync(new URL("../../public/sitemap.xml", import.meta.url), "utf8");
const alternateSitemapSource = fs.readFileSync(new URL("../../public/sitemap-pages.xml", import.meta.url), "utf8");
assert.equal(alternateSitemapSource, sitemapSource, "alternate sitemap should mirror the static sitemap");
assert.ok(
  sitemapSource.includes(`<loc>${defaultSiteConfig.SEO_SITE_URL}/</loc>`),
  "sitemap should include the canonical home URL",
);
assert.ok(
  sitemapSource.includes(`<loc>${defaultSiteConfig.SEO_SITE_URL}/app</loc>`),
  "sitemap should include the app route",
);
for (const page of SEO_LANDING_PAGES) {
  assert.ok(
    sitemapSource.includes(`<loc>${encodeURI(`${defaultSiteConfig.SEO_SITE_URL}/${page.slug}`)}</loc>`),
    `sitemap should include landing page: ${page.slug}`,
  );
}

const dynamicSitemapEntries = dynamicSitemap();
assert.equal(
  dynamicSitemapEntries.length,
  SEO_LANDING_PAGES.length + 2,
  "dynamic sitemap should include home, app, and every landing page",
);
for (const entry of dynamicSitemapEntries) {
  assert.ok(!/[ㄱ-ㅎㅏ-ㅣ가-힣]/.test(entry.url), `dynamic sitemap URL should be encoded: ${entry.url}`);
}
for (const page of SEO_LANDING_PAGES) {
  assert.ok(
    dynamicSitemapEntries.some((entry) => entry.url === encodeURI(`${defaultSiteConfig.SEO_SITE_URL}/${page.slug}`)),
    `dynamic sitemap should include encoded landing page: ${page.slug}`,
  );
}

const dinnerqueenPage = getLandingPage("디너의여왕-체험단");
const dinnerqueenCampaigns = getCampaignsForLanding(dinnerqueenPage, 5);
assert.ok(dinnerqueenCampaigns.length > 0, "Dinnerqueen landing should have campaigns");
assert.ok(
  dinnerqueenCampaigns.some((campaign) => campaign.reward),
  "Dinnerqueen landing should include at least one reward text",
);

const updatedAt = getSnapshotUpdatedAt();
assert.ok(Date.parse(updatedAt) || updatedAt.length > 0, "snapshot updatedAt should be present");

const seoDataModule = await import("../../src/seo/seoCampaignData.js?home-display");
assert.equal(
  typeof seoDataModule.countCampaignsForLanding,
  "function",
  "home should use an uncapped campaign count helper",
);
assert.equal(
  typeof seoDataModule.formatSnapshotUpdatedAt,
  "function",
  "home should expose a readable snapshot date formatter",
);
assert.equal(
  seoDataModule.formatSnapshotUpdatedAt("2026-05-15T01:53:28.757Z"),
  "2026.05.15 10:53 KST",
);

const homePageSource = fs.readFileSync(new URL("../../src/app/page.jsx", import.meta.url), "utf8");
assert.ok(
  !homePageSource.includes("도메인 검증 단계"),
  "home page should not expose internal domain-validation wording",
);
assert.ok(
  !homePageSource.includes("운영 검증용 핵심 섹션"),
  "home page should not expose internal validation wording",
);
for (const expectedFragment of [
  "/app?tab=explore",
  "/배송형-체험단",
  "/제품-체험단",
  "/오늘마감-체험단",
  "/서울-맛집-체험단",
  "/디너의여왕-체험단",
  "/레뷰-체험단",
  "/미블-체험단",
  "/강남-맛집-체험단",
  "/부산-카페-체험단",
  "home-deadline",
  "home-platforms",
]) {
  assert.ok(
    homePageSource.includes(expectedFragment),
    `home page should include ${expectedFragment}`,
  );
}

console.log(JSON.stringify({
  ok: true,
  landingPages: SEO_LANDING_PAGES.length,
  dinnerqueenCampaigns: dinnerqueenCampaigns.length,
  updatedAt,
}));

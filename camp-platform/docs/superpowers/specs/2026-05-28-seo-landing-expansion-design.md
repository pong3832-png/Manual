# SEO Landing Expansion Design

## Goal

Add crawlable SEO landing pages for search terms that already have enough campaign data, so Google and Naver can discover more specific entry points than the generic `/체험단` page.

## Current Context

- The temporary SEO origin is `https://camp-platform-liart.vercel.app`.
- `src/seo/landingPages.js` defines static landing metadata and filters.
- `src/seo/seoCampaignData.js` reads `public/campaigns.json`, filters open campaigns, and renders campaign cards on landing pages.
- `src/app/sitemap.js` automatically includes every item in `SEO_LANDING_PAGES`.
- Google Search Console ownership is verified.
- Naver Search Advisor sitemap, robots.txt, and primary page collection requests are complete.

## Candidate Data Check

Use only landing pages with real campaign data. Current snapshot counts:

| Candidate | Count | Decision |
|---|---:|---|
| `/뷰티-체험단-모집` | 2,185 | Add |
| `/레뷰-체험단` | 1,670 | Add |
| `/미블-체험단` | 1,609 | Add |
| `/강남-맛집-체험단` | 347 | Add |
| `/서울-블로그-체험단` | 81 | Add |
| `/부산-카페-체험단` | 57 | Add |
| `/오늘마감-블로그-체험단` | 39 | Add |
| `/리뷰노트-체험단` | 0 | Do not add yet |

## Design

### Landing Definitions

Add seven entries to `SEO_LANDING_PAGES`:

- `레뷰-체험단`: platform-focused page for `platformId = "revu"`.
- `미블-체험단`: platform-focused page for `platformId = "mrblog"`.
- `강남-맛집-체험단`: region/category page using text matching for `강남` plus food terms.
- `서울-블로그-체험단`: region/channel page using text matching for `서울` and `블로그`.
- `부산-카페-체험단`: region/category page using text matching for `부산` plus cafe terms.
- `뷰티-체험단-모집`: category page using beauty-related terms.
- `오늘마감-블로그-체험단`: deadline/channel page using `maxDday: 1` plus blog terms.

Each page must include:

- `slug`
- `title`
- `description`
- `h1`
- `intro`
- `filters`
- `appQuery`
- `relatedSlugs`

### Filter Model

Extend `matchesLanding()` in `src/seo/seoCampaignData.js` with a `textKeywords` filter:

- `textKeywords` requires all listed keyword groups to match campaign search text.
- Each group can be either a string or an array of alternatives.
- Examples:
  - `["강남", ["맛집", "음식", "식품"]]`
  - `["서울", "블로그"]`
  - `["부산", ["카페", "디저트"]]`

Keep existing filters intact:

- `platformIds`
- `province`
- `maxDday`
- `categoryKeywords`
- `channelKeywords`

### Home Links

Update `SEARCH_ENTRY_LINKS` on `src/app/page.jsx` so the first screen links to a small set of high-value new pages without turning the home into a link farm.

Add:

- `레뷰 체험단`
- `미블 체험단`
- `강남 맛집 체험단`
- `부산 카페 체험단`

Do not add every possible page to the home. The sitemap and related links will expose the rest.

### Related Links

Connect related pages so crawlers can move through the cluster:

- Platform pages link to generic `/체험단`, `/오늘마감-체험단`, and relevant category pages.
- Region/category pages link to `/맛집체험단`, `/카페체험단`, `/서울-맛집-체험단`, or `/오늘마감-체험단` as appropriate.
- Deadline blog page links to `/오늘마감-체험단`, `/블로그체험단`, and `/체험단`.

### QA

Update `scripts/qa/seo-landing-fixture.mjs` to assert:

- The seven new slugs exist.
- `리뷰노트-체험단` does not exist yet.
- Each new page has at least one campaign in the current snapshot.
- Home source includes representative new links:
  - `/레뷰-체험단`
  - `/미블-체험단`
  - `/강남-맛집-체험단`
  - `/부산-카페-체험단`

Run:

```powershell
npm.cmd run qa:seo:landing
npm.cmd run qa:public-env
npm.cmd run build
git diff --check -- src/seo/landingPages.js src/seo/seoCampaignData.js src/app/page.jsx scripts/qa/seo-landing-fixture.mjs docs/work-log.md
```

## Deployment Notes

- Keep Google and Naver verification files in `public/`.
- Keep `NEXT_PUBLIC_PUBLIC_SITE_URL=https://camp-platform-liart.vercel.app` in Vercel Production while using the temporary Vercel domain for SEO.
- After deploy, recheck:
  - `/레뷰-체험단`
  - `/미블-체험단`
  - `/강남-맛집-체험단`
  - `/서울-블로그-체험단`
  - `/부산-카페-체험단`
  - `/뷰티-체험단-모집`
  - `/오늘마감-블로그-체험단`
  - `/sitemap.xml`

## Out Of Scope

- Do not add `/리뷰노트-체험단` until snapshot data has matching campaigns.
- Do not change campaign crawlers in this task.
- Do not change Supabase sync behavior in this task.
- Do not purchase or switch to `cheheommoa.com` in this task.

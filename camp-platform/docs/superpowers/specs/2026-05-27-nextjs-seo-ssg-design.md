# Next.js SEO SSG Design

Date: 2026-05-27
Scope: migrate `camp-platform` from Vite SPA toward a Next.js App Router structure optimized for search landing pages.

## Goal

Make `cheheommoa.com` indexable for high-intent Korean 체험단 searches while preserving the existing search, map, detail, login, favorite, and application workflows.

The SEO priority is not just site registration. The app needs crawlable, intent-specific HTML pages for queries such as `서울 맛집 체험단`, `블로그 체험단`, `오늘 마감 체험단`, and `디너의여왕 체험단`.

## Official Domain

The official SEO domain is:

```text
https://cheheommoa.com
```

Canonical URLs, sitemap entries, robots sitemap URL, Open Graph URLs, and production internal links should use this domain.

Redirect policy:

- `https://www.cheheommoa.com/*` redirects to `https://cheheommoa.com/*`.
- `https://camp-platform-liart.vercel.app/*` should not be treated as the canonical SEO host.
- Preview deployment URLs should remain usable for QA and should not be blindly redirected.

## Current State

The current app is a Vite React SPA:

- `index.html` has site-level title, description, keywords, canonical, and OG tags.
- `public/robots.txt` allows all crawlers and points to `https://camp-platform-liart.vercel.app/sitemap.xml`.
- `public/sitemap.xml` contains only the root URL.
- `src/app/App.jsx` updates title/description/canonical at runtime.
- Campaign data is loaded from `/campaigns.json` by default to reduce Supabase egress.

This is usable, but weak for SEO because the first HTML response does not contain intent-specific content or campaign summaries.

## Recommended Architecture

Use Next.js App Router with a hybrid model:

- SEO landing pages are Server Components / static generated pages.
- Existing app workflows are moved behind client components.
- Campaign data for SEO pages is read at build time from the public snapshot.
- Supabase remains optional for frontend campaign refresh and user features.

Initial route shape:

```text
app/
  layout.jsx
  page.jsx
  robots.js
  sitemap.js
  (seo)/
    [slug]/
      page.jsx
  app/
    page.jsx
src/
  app/ClientApp.jsx
  seo/
    landingPages.js
    seoCampaignData.js
    seoMetadata.js
```

`/app` can host the full interactive product shell if the root page becomes a stronger SEO homepage. Landing CTAs can link to `/app?tab=explore&...`.

## Landing Page Set

Start with a small, high-quality page set before scaling:

- `/체험단`
- `/블로그체험단`
- `/인스타체험단`
- `/맛집체험단`
- `/카페체험단`
- `/뷰티체험단`
- `/서울-맛집-체험단`
- `/부산-맛집-체험단`
- `/오늘마감-체험단`
- `/디너의여왕-체험단`

Each page should define:

- slug
- title
- description
- h1
- intro copy
- filter intent
- related internal links
- CTA query into the app

Do not generate thousands of thin pages at first. Expand only after Search Console and Naver Search Advisor show useful impressions or missing query opportunities.

## Page Content

Every landing page should render meaningful HTML without waiting for client JavaScript:

- one clear `h1`
- short explanatory copy matching the search intent
- latest matching campaign cards or compact list items
- platform, category, location, deadline, and reward text when available
- links to related landing pages
- CTA to open the interactive app
- source/freshness notice: campaign conditions must be checked on the original platform

The page must not claim guaranteed availability. Campaigns can close or change on source platforms.

## Metadata And Indexing

Use Next.js metadata APIs:

- root metadata uses `https://cheheommoa.com`
- each SEO page uses unique title and description
- each page sets canonical to its own URL
- `robots.js` points to `https://cheheommoa.com/sitemap.xml`
- `sitemap.js` includes root, `/app`, and all SEO landing pages
- sitemap `lastModified` should use latest snapshot update time when available

The Vercel app host should not appear in canonical or sitemap once the custom domain is live.

## Internal Links

Use a hub-and-spoke structure:

- `/체험단` links to channel/category/deadline pages.
- `/맛집체험단` links to regional 맛집 pages.
- `/서울-맛집-체험단` links to `/맛집체험단`, `/오늘마감-체험단`, and app filtered view.
- `/디너의여왕-체험단` links to general 체험단 and 맛집 pages.

This helps search engines understand topical hierarchy instead of seeing isolated pages.

## Data Freshness

SEO pages are static at build time. Freshness flow:

1. crawler updates `public/campaigns.json`
2. Dinnerqueen point backfill runs when needed
3. build reads the latest snapshot
4. deploy publishes updated static HTML and sitemap

If a crawl is `blocked` or quality gate cannot publish, do not deploy regenerated SEO pages from that data.

## Migration Strategy

Use a phased migration:

1. Add Next.js dependencies and App Router files.
2. Move the existing React app into a client component without changing product behavior.
3. Add static SEO landing pages using snapshot data.
4. Replace Vite build script with Next.js build only after the Next app builds locally.
5. Deploy preview first, then production after approval.

This avoids a full rewrite while moving the SEO-critical surface to server/static HTML.

## Verification

Minimum verification before production:

- `npm.cmd run build`
- landing page HTML contains expected `h1`, canonical, and campaign text
- `sitemap.xml` includes `https://cheheommoa.com/...` entries
- `robots.txt` points to `https://cheheommoa.com/sitemap.xml`
- existing app shell still loads campaigns from `/campaigns.json`
- Dinnerqueen landing page shows reward text from the snapshot
- production deploy only after explicit approval

Add a focused QA script if practical:

```text
npm.cmd run qa:seo:landing
```

The QA should verify generated metadata, landing slugs, sitemap URLs, and at least one matching campaign per intent where data exists.

## Non-Goals

- Do not automate backlinks or spam community posts.
- Do not generate one page per campaign in the first phase.
- Do not depend on Supabase for SEO landing page rendering while quota is restricted.
- Do not remove the current app workflows during the migration.

## Risks

- Korean slugs must be handled consistently in links, sitemap, and canonical URLs.
- Thin or duplicated landing copy can reduce SEO quality. Each page needs a distinct search intent.
- Redirecting all Vercel hosts can break preview QA, so redirects must target only known production aliases.
- Next.js migration can break existing client behavior if browser-only code is imported into Server Components. Keep the app shell behind explicit client boundaries.

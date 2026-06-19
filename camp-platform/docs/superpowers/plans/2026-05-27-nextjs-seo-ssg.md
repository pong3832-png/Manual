# Next.js SEO SSG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the SEO-critical surface of `camp-platform` to Next.js App Router SSG so `https://cheheommoa.com` can expose crawlable landing pages for Korean 체험단 searches while preserving the existing app workflows.

**Architecture:** Use Next.js App Router with static Server Component landing pages and a client-only wrapper for the existing React app. Public campaign data comes from `public/campaigns.json` at build time, and Supabase remains optional for user features and explicit DB refresh.

**Tech Stack:** Next.js App Router, React 19, Supabase JS, existing campaign snapshot JSON, Vercel.

---

## File Structure

- Create `app/layout.jsx`: root HTML shell, global CSS imports, base metadata for `https://cheheommoa.com`.
- Create `app/page.jsx`: SEO homepage for `/`.
- Create `app/app/page.jsx`: interactive app route that renders the existing React app as a client component.
- Create `app/(seo)/[slug]/page.jsx`: static search-intent landing pages.
- Create `app/robots.js`: robots policy and sitemap URL for `cheheommoa.com`.
- Create `app/sitemap.js`: root, `/app`, and all SEO landing pages.
- Create `src/app/ClientApp.jsx`: client boundary around existing `App`.
- Modify `src/app/App.jsx`: remove global CSS import so Next root layout owns global CSS.
- Create `src/shared/config/publicEnv.js`: Vite/Next public env compatibility layer.
- Modify env consumers: `src/shared/api/supabase.js`, `src/shared/config/site.js`, `src/features/campaigns/hooks/useCampaigns.js`, ad components, and Kakao map loader.
- Create `src/seo/siteConfig.js`: official SEO domain and shared constants.
- Create `src/seo/landingPages.js`: declarative SEO landing page definitions.
- Create `src/seo/seoCampaignData.js`: build-time campaign snapshot reader and landing filters.
- Create `scripts/qa/seo-landing-fixture.mjs`: focused SEO QA.
- Modify `package.json`: add Next scripts/dependency and `qa:seo:landing`.
- Modify `.env.example`: add `NEXT_PUBLIC_*` equivalents and set public site URL to `https://cheheommoa.com`.
- Modify `next.config.mjs`: public env mapping and `www` redirect.
- Modify `docs/work-log.md`: record implementation and verification.
- Modify `AGENTS.md` only if new operating rules appear during implementation.

Do not remove Vite files in the first pass. Keep `index.html`, `vite.config.js`, and `src/main.jsx` until the Next build is verified and the user approves cleanup.

## Task 1: Public Env Compatibility

**Files:**
- Create: `src/shared/config/publicEnv.js`
- Modify: `src/shared/api/supabase.js`
- Modify: `src/shared/config/site.js`
- Modify: `src/features/campaigns/hooks/useCampaigns.js`
- Modify: `src/features/ads/components/AdSenseLoader.jsx`
- Modify: `src/features/ads/components/AdSenseUnit.jsx`
- Modify: `src/features/ads/components/MonetizedAdSlot.jsx`
- Modify: `src/features/map/hooks/useKakaoMapLoader.js`
- Modify: `src/legacy/supabase.legacy.js`
- Test: `scripts/qa/public-env-fixture.mjs`
- Modify: `package.json`

- [ ] **Step 1: Write the failing public env fixture**

Create `scripts/qa/public-env-fixture.mjs`:

```js
import assert from "node:assert/strict";

process.env.NEXT_PUBLIC_SUPABASE_URL = "https://next-ref.supabase.co";
process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "next-anon";
process.env.NEXT_PUBLIC_CAMPAIGN_DB_REFRESH_ENABLED = "0";
process.env.NEXT_PUBLIC_PUBLIC_SITE_NAME = "CheheomMoa";
process.env.NEXT_PUBLIC_PUBLIC_SITE_URL = "https://cheheommoa.com";
process.env.NEXT_PUBLIC_KAKAO_MAP_APP_KEY = "next-kakao";
process.env.NEXT_PUBLIC_ADSENSE_CLIENT = "ca-pub-next";
process.env.NEXT_PUBLIC_ADSENSE_ENABLE_LOCAL = "1";
process.env.NEXT_PUBLIC_ADSENSE_HOME_TOP_SLOT = "home";
process.env.NEXT_PUBLIC_ADSENSE_EXPLORE_INLINE_SLOT = "explore";
process.env.NEXT_PUBLIC_ADSENSE_MAP_BOTTOM_SLOT = "map";

const { publicEnv } = await import("../../src/shared/config/publicEnv.js");

assert.equal(publicEnv.supabaseUrl, "https://next-ref.supabase.co");
assert.equal(publicEnv.supabaseAnonKey, "next-anon");
assert.equal(publicEnv.campaignDbRefreshEnabled, "0");
assert.equal(publicEnv.publicSiteUrl, "https://cheheommoa.com");
assert.equal(publicEnv.kakaoMapAppKey, "next-kakao");
assert.equal(publicEnv.adsenseClient, "ca-pub-next");
assert.equal(publicEnv.adsenseEnableLocal, "1");
assert.equal(publicEnv.adsenseSlots.home_top, "home");
assert.equal(publicEnv.raw.VITE_CAMPAIGN_DB_REFRESH_ENABLED, "0");

console.log(JSON.stringify({ ok: true }));
```

- [ ] **Step 2: Add the QA script to `package.json`**

Add this script entry:

```json
"qa:public-env": "node scripts/qa/public-env-fixture.mjs"
```

- [ ] **Step 3: Run the fixture and verify it fails**

Run:

```powershell
npm.cmd run qa:public-env
```

Expected: failure with `ERR_MODULE_NOT_FOUND` for `src/shared/config/publicEnv.js`.

- [ ] **Step 4: Create `src/shared/config/publicEnv.js`**

```js
const env = typeof process !== "undefined" && process.env ? process.env : {};

function firstValue(...values) {
  return values.map((value) => String(value || "").trim()).find(Boolean) || "";
}

const raw = {
  VITE_SUPABASE_URL: firstValue(env.NEXT_PUBLIC_SUPABASE_URL, env.VITE_SUPABASE_URL),
  VITE_SUPABASE_ANON_KEY: firstValue(env.NEXT_PUBLIC_SUPABASE_ANON_KEY, env.VITE_SUPABASE_ANON_KEY),
  VITE_CAMPAIGN_DB_REFRESH_ENABLED: firstValue(
    env.NEXT_PUBLIC_CAMPAIGN_DB_REFRESH_ENABLED,
    env.VITE_CAMPAIGN_DB_REFRESH_ENABLED,
  ),
  VITE_KAKAO_MAP_APP_KEY: firstValue(env.NEXT_PUBLIC_KAKAO_MAP_APP_KEY, env.VITE_KAKAO_MAP_APP_KEY),
  VITE_PUBLIC_SITE_NAME: firstValue(env.NEXT_PUBLIC_PUBLIC_SITE_NAME, env.VITE_PUBLIC_SITE_NAME),
  VITE_PUBLIC_SITE_URL: firstValue(env.NEXT_PUBLIC_PUBLIC_SITE_URL, env.VITE_PUBLIC_SITE_URL),
  VITE_PUBLIC_CONTACT_EMAIL: firstValue(env.NEXT_PUBLIC_PUBLIC_CONTACT_EMAIL, env.VITE_PUBLIC_CONTACT_EMAIL),
  VITE_PUBLIC_OPERATOR_NAME: firstValue(env.NEXT_PUBLIC_PUBLIC_OPERATOR_NAME, env.VITE_PUBLIC_OPERATOR_NAME),
  VITE_ADSENSE_CLIENT: firstValue(env.NEXT_PUBLIC_ADSENSE_CLIENT, env.VITE_ADSENSE_CLIENT),
  VITE_ADSENSE_ENABLE_LOCAL: firstValue(env.NEXT_PUBLIC_ADSENSE_ENABLE_LOCAL, env.VITE_ADSENSE_ENABLE_LOCAL),
  VITE_ADSENSE_HOME_TOP_SLOT: firstValue(env.NEXT_PUBLIC_ADSENSE_HOME_TOP_SLOT, env.VITE_ADSENSE_HOME_TOP_SLOT),
  VITE_ADSENSE_EXPLORE_INLINE_SLOT: firstValue(
    env.NEXT_PUBLIC_ADSENSE_EXPLORE_INLINE_SLOT,
    env.VITE_ADSENSE_EXPLORE_INLINE_SLOT,
  ),
  VITE_ADSENSE_MAP_BOTTOM_SLOT: firstValue(env.NEXT_PUBLIC_ADSENSE_MAP_BOTTOM_SLOT, env.VITE_ADSENSE_MAP_BOTTOM_SLOT),
  VITE_ADSENSE_HOME_TOP_CHANNEL: firstValue(
    env.NEXT_PUBLIC_ADSENSE_HOME_TOP_CHANNEL,
    env.VITE_ADSENSE_HOME_TOP_CHANNEL,
  ),
  VITE_ADSENSE_EXPLORE_INLINE_CHANNEL: firstValue(
    env.NEXT_PUBLIC_ADSENSE_EXPLORE_INLINE_CHANNEL,
    env.VITE_ADSENSE_EXPLORE_INLINE_CHANNEL,
  ),
  VITE_ADSENSE_MAP_BOTTOM_CHANNEL: firstValue(
    env.NEXT_PUBLIC_ADSENSE_MAP_BOTTOM_CHANNEL,
    env.VITE_ADSENSE_MAP_BOTTOM_CHANNEL,
  ),
};

export const publicEnv = {
  raw,
  supabaseUrl: raw.VITE_SUPABASE_URL,
  supabaseAnonKey: raw.VITE_SUPABASE_ANON_KEY,
  campaignDbRefreshEnabled: raw.VITE_CAMPAIGN_DB_REFRESH_ENABLED,
  kakaoMapAppKey: raw.VITE_KAKAO_MAP_APP_KEY,
  publicSiteName: raw.VITE_PUBLIC_SITE_NAME,
  publicSiteUrl: raw.VITE_PUBLIC_SITE_URL,
  publicContactEmail: raw.VITE_PUBLIC_CONTACT_EMAIL,
  publicOperatorName: raw.VITE_PUBLIC_OPERATOR_NAME,
  adsenseClient: raw.VITE_ADSENSE_CLIENT,
  adsenseEnableLocal: raw.VITE_ADSENSE_ENABLE_LOCAL,
  adsenseSlots: {
    home_top: raw.VITE_ADSENSE_HOME_TOP_SLOT,
    explore_inline: raw.VITE_ADSENSE_EXPLORE_INLINE_SLOT,
    map_bottom: raw.VITE_ADSENSE_MAP_BOTTOM_SLOT,
  },
  adsenseChannels: {
    home_top: raw.VITE_ADSENSE_HOME_TOP_CHANNEL,
    explore_inline: raw.VITE_ADSENSE_EXPLORE_INLINE_CHANNEL,
    map_bottom: raw.VITE_ADSENSE_MAP_BOTTOM_CHANNEL,
  },
};
```

- [ ] **Step 5: Replace `import.meta.env` consumers**

Use these exact replacement patterns.

`src/shared/api/supabase.js`:

```js
import { createClient } from "@supabase/supabase-js";
import { publicEnv } from "../config/publicEnv";

const supabaseUrl = publicEnv.supabaseUrl;
const supabaseKey = publicEnv.supabaseAnonKey;
```

`src/shared/config/site.js`:

```js
import { publicEnv } from "./publicEnv";

const fallbackOrigin = typeof window !== "undefined" ? window.location.origin : "";

export const SITE_NAME = publicEnv.publicSiteName || "CheheomMoa";
export const PUBLIC_SITE_URL = publicEnv.publicSiteUrl || fallbackOrigin;
export const PUBLIC_CONTACT_EMAIL = String(publicEnv.publicContactEmail || "").trim();
export const PUBLIC_OPERATOR_NAME = String(publicEnv.publicOperatorName || "").trim();
export const LEGAL_UPDATED_AT = "2026-05-13";
```

`src/features/campaigns/hooks/useCampaigns.js`:

```js
import { publicEnv } from "../../../shared/config/publicEnv";
```

and pass `env: publicEnv.raw` into `shouldUseSupabaseCampaignSource`.

`src/features/map/hooks/useKakaoMapLoader.js`:

```js
import { publicEnv } from "../../../shared/config/publicEnv";

const KAKAO_MAP_KEY = publicEnv.kakaoMapAppKey;
```

`src/features/ads/components/AdSenseLoader.jsx`, `src/features/ads/components/AdSenseUnit.jsx`, and `src/features/ads/components/MonetizedAdSlot.jsx` should import `publicEnv` and replace all `import.meta.env.VITE_ADSENSE_*` reads with `publicEnv.adsense*` fields.

`src/legacy/supabase.legacy.js` should either import `publicEnv` or be deleted only if `rg "supabase.legacy"` confirms no references. Prefer import replacement in this task.

- [ ] **Step 6: Verify the env fixture passes**

Run:

```powershell
npm.cmd run qa:public-env
```

Expected: `{ "ok": true }`.

- [ ] **Step 7: Search for remaining Vite env usage**

Run:

```powershell
rg -n "import\\.meta\\.env|import\\.meta" src
```

Expected: no matches in runtime code. If `src/main.jsx` still has `import.meta.env.PROD`, leave it only while Vite fallback remains and confirm it is not imported by Next.

## Task 2: Next.js Scaffold And Config

**Files:**
- Modify: `package.json`
- Modify: `package-lock.json`
- Create: `next.config.mjs`
- Modify: `.env.example`

- [ ] **Step 1: Install Next**

Run only after user approval for dependency install if required:

```powershell
npm.cmd install next@latest
```

Expected: `package.json` gains `next`, and `package-lock.json` updates.

- [ ] **Step 2: Update `package.json` scripts**

Keep Vite fallback scripts for one pass:

```json
"dev": "next dev",
"build": "next build",
"start": "next start",
"dev:vite": "vite",
"build:vite": "vite build",
"preview:vite": "vite preview"
```

Do not remove existing crawler, ops, ads, or QA scripts.

- [ ] **Step 3: Create `next.config.mjs`**

```js
const publicEnv = {
  NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.VITE_SUPABASE_URL || "",
  NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.VITE_SUPABASE_ANON_KEY || "",
  NEXT_PUBLIC_CAMPAIGN_DB_REFRESH_ENABLED:
    process.env.NEXT_PUBLIC_CAMPAIGN_DB_REFRESH_ENABLED || process.env.VITE_CAMPAIGN_DB_REFRESH_ENABLED || "0",
  NEXT_PUBLIC_KAKAO_MAP_APP_KEY: process.env.NEXT_PUBLIC_KAKAO_MAP_APP_KEY || process.env.VITE_KAKAO_MAP_APP_KEY || "",
  NEXT_PUBLIC_PUBLIC_SITE_NAME: process.env.NEXT_PUBLIC_PUBLIC_SITE_NAME || process.env.VITE_PUBLIC_SITE_NAME || "CheheomMoa",
  NEXT_PUBLIC_PUBLIC_SITE_URL:
    process.env.NEXT_PUBLIC_PUBLIC_SITE_URL || process.env.VITE_PUBLIC_SITE_URL || "https://cheheommoa.com",
  NEXT_PUBLIC_PUBLIC_CONTACT_EMAIL:
    process.env.NEXT_PUBLIC_PUBLIC_CONTACT_EMAIL || process.env.VITE_PUBLIC_CONTACT_EMAIL || "",
  NEXT_PUBLIC_PUBLIC_OPERATOR_NAME:
    process.env.NEXT_PUBLIC_PUBLIC_OPERATOR_NAME || process.env.VITE_PUBLIC_OPERATOR_NAME || "",
  NEXT_PUBLIC_ADSENSE_CLIENT: process.env.NEXT_PUBLIC_ADSENSE_CLIENT || process.env.VITE_ADSENSE_CLIENT || "",
  NEXT_PUBLIC_ADSENSE_ENABLE_LOCAL:
    process.env.NEXT_PUBLIC_ADSENSE_ENABLE_LOCAL || process.env.VITE_ADSENSE_ENABLE_LOCAL || "0",
  NEXT_PUBLIC_ADSENSE_HOME_TOP_SLOT:
    process.env.NEXT_PUBLIC_ADSENSE_HOME_TOP_SLOT || process.env.VITE_ADSENSE_HOME_TOP_SLOT || "",
  NEXT_PUBLIC_ADSENSE_EXPLORE_INLINE_SLOT:
    process.env.NEXT_PUBLIC_ADSENSE_EXPLORE_INLINE_SLOT || process.env.VITE_ADSENSE_EXPLORE_INLINE_SLOT || "",
  NEXT_PUBLIC_ADSENSE_MAP_BOTTOM_SLOT:
    process.env.NEXT_PUBLIC_ADSENSE_MAP_BOTTOM_SLOT || process.env.VITE_ADSENSE_MAP_BOTTOM_SLOT || "",
  NEXT_PUBLIC_ADSENSE_HOME_TOP_CHANNEL:
    process.env.NEXT_PUBLIC_ADSENSE_HOME_TOP_CHANNEL || process.env.VITE_ADSENSE_HOME_TOP_CHANNEL || "",
  NEXT_PUBLIC_ADSENSE_EXPLORE_INLINE_CHANNEL:
    process.env.NEXT_PUBLIC_ADSENSE_EXPLORE_INLINE_CHANNEL || process.env.VITE_ADSENSE_EXPLORE_INLINE_CHANNEL || "",
  NEXT_PUBLIC_ADSENSE_MAP_BOTTOM_CHANNEL:
    process.env.NEXT_PUBLIC_ADSENSE_MAP_BOTTOM_CHANNEL || process.env.VITE_ADSENSE_MAP_BOTTOM_CHANNEL || "",
};

const nextConfig = {
  env: publicEnv,
  async redirects() {
    return [
      {
        source: "/:path*",
        has: [{ type: "host", value: "www.cheheommoa.com" }],
        destination: "https://cheheommoa.com/:path*",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
```

- [ ] **Step 4: Update `.env.example`**

Add `NEXT_PUBLIC_*` examples above the existing `VITE_*` block and set the public site URL to the official domain:

```dotenv
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
NEXT_PUBLIC_CAMPAIGN_DB_REFRESH_ENABLED=0
NEXT_PUBLIC_KAKAO_MAP_APP_KEY=your-kakao-map-javascript-key
NEXT_PUBLIC_PUBLIC_SITE_NAME=CheheomMoa
NEXT_PUBLIC_PUBLIC_SITE_URL=https://cheheommoa.com
NEXT_PUBLIC_PUBLIC_CONTACT_EMAIL=contact@example.com
NEXT_PUBLIC_PUBLIC_OPERATOR_NAME=CheheomMoa
```

Keep the existing `VITE_*` variables during migration.

## Task 3: Client App Boundary

**Files:**
- Create: `src/app/ClientApp.jsx`
- Modify: `src/app/App.jsx`
- Create: `app/layout.jsx`
- Create: `app/app/page.jsx`

- [ ] **Step 1: Create `src/app/ClientApp.jsx`**

```jsx
"use client";

import { useEffect } from "react";
import App from "./App";

function registerServiceWorker() {
  if (typeof window === "undefined") return;
  if (!("serviceWorker" in navigator)) return;
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => null);
  });
}

export default function ClientApp() {
  useEffect(() => {
    if (process.env.NODE_ENV === "production") registerServiceWorker();
  }, []);

  return <App />;
}
```

- [ ] **Step 2: Remove the global CSS import from `src/app/App.jsx`**

Delete only this line:

```js
import "./App.css";
```

Do not change App behavior in this task.

- [ ] **Step 3: Create `app/layout.jsx`**

```jsx
import "../src/index.css";
import "../src/app/compact-ui.css";
import "../src/app/App.css";
import { SEO_SITE_URL, SITE_NAME } from "../src/seo/siteConfig";

export const metadata = {
  metadataBase: new URL(SEO_SITE_URL),
  applicationName: SITE_NAME,
  title: {
    default: `${SITE_NAME} | 전국 체험단 캠페인 모음`,
    template: `%s | ${SITE_NAME}`,
  },
  description: "맛집, 카페, 뷰티, 숙박, 생활용품 체험단 캠페인을 한 곳에서 찾고 비교해보세요.",
  alternates: {
    canonical: "/",
  },
  openGraph: {
    type: "website",
    locale: "ko_KR",
    siteName: SITE_NAME,
    url: SEO_SITE_URL,
    title: `${SITE_NAME} | 전국 체험단 캠페인 모음`,
    description: "맛집, 카페, 뷰티, 숙박, 생활용품 체험단 캠페인을 한 곳에서 찾고 비교해보세요.",
  },
  twitter: {
    card: "summary",
    title: `${SITE_NAME} | 전국 체험단 캠페인 모음`,
    description: "맛집, 카페, 뷰티, 숙박, 생활용품 체험단 캠페인을 한 곳에서 찾고 비교해보세요.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#C1440E",
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 4: Create `app/app/page.jsx`**

```jsx
import ClientApp from "../../src/app/ClientApp";

export const metadata = {
  title: "캠페인 검색 앱",
  description: "체험단 캠페인을 검색하고 지도, 즐겨찾기, 신청 현황을 관리합니다.",
  alternates: {
    canonical: "/app",
  },
};

export default function AppPage() {
  return <ClientApp />;
}
```

- [ ] **Step 5: Run build and capture expected first failure**

Run:

```powershell
npm.cmd run build
```

Expected at this point: failure because SEO modules/routes are not all created yet, or because remaining global CSS/import-meta usage needs cleanup. Do not proceed by guessing; fix the exact reported file.

## Task 4: SEO Data Modules

**Files:**
- Create: `src/seo/siteConfig.js`
- Create: `src/seo/landingPages.js`
- Create: `src/seo/seoCampaignData.js`

- [ ] **Step 1: Create `src/seo/siteConfig.js`**

```js
export const SEO_SITE_URL = "https://cheheommoa.com";
export const SITE_NAME = "CheheomMoa";
export const DEFAULT_SEO_DESCRIPTION =
  "맛집, 카페, 뷰티, 숙박, 생활용품 체험단 캠페인을 한 곳에서 찾고 비교해보세요.";

export function absoluteUrl(path = "/") {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${SEO_SITE_URL}${normalizedPath}`;
}
```

- [ ] **Step 2: Create `src/seo/landingPages.js`**

```js
export const SEO_LANDING_PAGES = [
  {
    slug: "체험단",
    title: "체험단 캠페인 모아보기",
    description: "전국 체험단 캠페인을 지역, 카테고리, 마감일, 제공내역 기준으로 비교해보세요.",
    h1: "전국 체험단 캠페인 모아보기",
    intro: "여러 체험단 플랫폼의 공개 모집글을 한 곳에서 확인하고, 조건에 맞는 캠페인을 빠르게 찾을 수 있습니다.",
    filters: {},
    appQuery: "?tab=explore",
    relatedSlugs: ["맛집체험단", "블로그체험단", "오늘마감-체험단"],
  },
  {
    slug: "블로그체험단",
    title: "블로그 체험단 모집 모아보기",
    description: "블로그 리뷰어를 모집하는 체험단 캠페인을 지역과 마감일 기준으로 찾아보세요.",
    h1: "블로그 체험단 모집 모아보기",
    intro: "블로그 리뷰 작성이 필요한 캠페인을 중심으로 최신 모집글을 정리합니다.",
    filters: { channelKeywords: ["블로그"] },
    appQuery: "?tab=explore&preset=blog",
    relatedSlugs: ["체험단", "맛집체험단", "서울-맛집-체험단"],
  },
  {
    slug: "인스타체험단",
    title: "인스타 체험단 모집 모아보기",
    description: "인스타그램, 릴스, SNS 리뷰어를 모집하는 체험단 캠페인을 확인해보세요.",
    h1: "인스타 체험단 모집 모아보기",
    intro: "인스타그램 콘텐츠 제작이나 릴스 업로드가 필요한 캠페인을 빠르게 찾을 수 있습니다.",
    filters: { channelKeywords: ["인스타", "릴스"] },
    appQuery: "?tab=explore&preset=instagram",
    relatedSlugs: ["체험단", "뷰티체험단", "카페체험단"],
  },
  {
    slug: "맛집체험단",
    title: "맛집 체험단 모집 모아보기",
    description: "전국 맛집 체험단 캠페인을 지역, 마감일, 제공내역 기준으로 비교해보세요.",
    h1: "맛집 체험단 모집 모아보기",
    intro: "식사권, 메뉴 제공, 방문 리뷰 등 맛집 중심 캠페인을 한 번에 비교합니다.",
    filters: { categoryKeywords: ["맛집", "식품"] },
    appQuery: "?tab=explore&category=맛집",
    relatedSlugs: ["서울-맛집-체험단", "부산-맛집-체험단", "오늘마감-체험단"],
  },
  {
    slug: "카페체험단",
    title: "카페 체험단 모집 모아보기",
    description: "카페, 디저트, 음료 체험단 캠페인을 한 곳에서 찾아보세요.",
    h1: "카페 체험단 모집 모아보기",
    intro: "카페 방문, 디저트, 음료 제공 캠페인을 중심으로 최신 모집글을 정리합니다.",
    filters: { categoryKeywords: ["카페", "디저트"] },
    appQuery: "?tab=explore&category=카페",
    relatedSlugs: ["맛집체험단", "서울-맛집-체험단", "인스타체험단"],
  },
  {
    slug: "뷰티체험단",
    title: "뷰티 체험단 모집 모아보기",
    description: "뷰티, 피부관리, 헤어, 네일 관련 체험단 캠페인을 찾아보세요.",
    h1: "뷰티 체험단 모집 모아보기",
    intro: "뷰티 서비스와 제품 체험 캠페인을 지역과 마감일 기준으로 비교합니다.",
    filters: { categoryKeywords: ["뷰티", "미용", "헤어", "네일"] },
    appQuery: "?tab=explore&category=뷰티",
    relatedSlugs: ["체험단", "인스타체험단", "오늘마감-체험단"],
  },
  {
    slug: "서울-맛집-체험단",
    title: "서울 맛집 체험단 모집 모아보기",
    description: "서울 지역 맛집 체험단 캠페인을 마감일과 제공내역 기준으로 비교해보세요.",
    h1: "서울 맛집 체험단 모집 모아보기",
    intro: "서울에서 모집 중인 맛집 체험단을 중심으로 방문 위치, 마감일, 제공내역을 확인할 수 있습니다.",
    filters: { province: "서울", categoryKeywords: ["맛집", "식품"] },
    appQuery: "?tab=explore&province=서울&category=맛집",
    relatedSlugs: ["맛집체험단", "오늘마감-체험단", "블로그체험단"],
  },
  {
    slug: "부산-맛집-체험단",
    title: "부산 맛집 체험단 모집 모아보기",
    description: "부산 지역 맛집 체험단 캠페인을 마감일과 제공내역 기준으로 비교해보세요.",
    h1: "부산 맛집 체험단 모집 모아보기",
    intro: "부산에서 모집 중인 맛집 체험단을 중심으로 위치와 조건을 빠르게 살펴볼 수 있습니다.",
    filters: { province: "부산", categoryKeywords: ["맛집", "식품"] },
    appQuery: "?tab=explore&province=부산&category=맛집",
    relatedSlugs: ["맛집체험단", "서울-맛집-체험단", "오늘마감-체험단"],
  },
  {
    slug: "오늘마감-체험단",
    title: "오늘 마감 체험단 모집 모아보기",
    description: "오늘 또는 곧 마감되는 체험단 캠페인을 빠르게 확인해보세요.",
    h1: "오늘 마감 체험단 모집 모아보기",
    intro: "마감이 가까운 체험단 캠페인을 우선 확인하고 원문 신청 페이지로 이동할 수 있습니다.",
    filters: { maxDday: 1 },
    appQuery: "?tab=explore&preset=deadline",
    relatedSlugs: ["체험단", "맛집체험단", "서울-맛집-체험단"],
  },
  {
    slug: "디너의여왕-체험단",
    title: "디너의여왕 체험단 모집 모아보기",
    description: "디너의여왕 체험단 캠페인을 제공내역과 마감일 기준으로 확인해보세요.",
    h1: "디너의여왕 체험단 모집 모아보기",
    intro: "디너의여왕에 올라온 공개 캠페인을 제공내역과 함께 비교할 수 있습니다.",
    filters: { platformIds: ["dinner"] },
    appQuery: "?tab=explore&platform=dinner",
    relatedSlugs: ["체험단", "맛집체험단", "오늘마감-체험단"],
  },
];

export function getLandingPage(slug) {
  return SEO_LANDING_PAGES.find((page) => page.slug === decodeURIComponent(String(slug || ""))) || null;
}
```

- [ ] **Step 3: Create `src/seo/seoCampaignData.js`**

```js
import fs from "node:fs";
import path from "node:path";

const PROJECT_ROOT = process.cwd();
const SNAPSHOT_PATH = path.join(PROJECT_ROOT, "public", "campaigns.json");

function cleanText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function parseCampaignsSnapshot() {
  const raw = JSON.parse(fs.readFileSync(SNAPSHOT_PATH, "utf-8"));
  const campaigns = Array.isArray(raw) ? raw : raw.campaigns || [];
  return {
    updatedAt: cleanText(raw.updatedAt || raw.generatedAt || raw.completedAt),
    campaigns: campaigns.filter((campaign) => cleanText(campaign.id) && cleanText(campaign.title)),
  };
}

export function getSnapshotUpdatedAt() {
  return parseCampaignsSnapshot().updatedAt || new Date().toISOString();
}

function campaignSearchText(campaign) {
  return [
    campaign.title,
    campaign.category,
    campaign.platform,
    campaign.platformId,
    campaign.province,
    campaign.city,
    campaign.address,
    campaign.point,
    campaign.rewardText,
    campaign.reward_text,
    campaign.channel,
    campaign.media,
  ].map(cleanText).join(" ");
}

function hasKeyword(campaign, keywords = []) {
  if (!keywords.length) return true;
  const text = campaignSearchText(campaign);
  return keywords.some((keyword) => text.includes(keyword));
}

function isOpenCampaign(campaign) {
  if (cleanText(campaign.status) && cleanText(campaign.status) !== "open") return false;
  const dDay = Number(campaign.dDay);
  return !Number.isFinite(dDay) || dDay >= 0;
}

function matchesLanding(campaign, filters = {}) {
  if (!isOpenCampaign(campaign)) return false;
  if (filters.platformIds?.length && !filters.platformIds.includes(cleanText(campaign.platformId))) return false;
  if (filters.province && cleanText(campaign.province) !== filters.province) return false;
  if (Number.isFinite(filters.maxDday)) {
    const dDay = Number(campaign.dDay);
    if (!Number.isFinite(dDay) || dDay > filters.maxDday || dDay < 0) return false;
  }
  if (!hasKeyword(campaign, filters.categoryKeywords || [])) return false;
  if (!hasKeyword(campaign, filters.channelKeywords || [])) return false;
  return true;
}

function compareCampaigns(left, right) {
  const leftDday = Number.isFinite(Number(left.dDay)) ? Number(left.dDay) : 999;
  const rightDday = Number.isFinite(Number(right.dDay)) ? Number(right.dDay) : 999;
  if (leftDday !== rightDday) return leftDday - rightDday;
  return cleanText(left.title).localeCompare(cleanText(right.title), "ko");
}

export function getCampaignsForLanding(page, limit = 12) {
  const { campaigns } = parseCampaignsSnapshot();
  return campaigns
    .filter((campaign) => matchesLanding(campaign, page.filters || {}))
    .sort(compareCampaigns)
    .slice(0, limit)
    .map((campaign) => ({
      id: cleanText(campaign.id),
      title: cleanText(campaign.title),
      platform: cleanText(campaign.platform || campaign.platformId),
      category: cleanText(campaign.category),
      province: cleanText(campaign.province),
      city: cleanText(campaign.city),
      dDay: Number.isFinite(Number(campaign.dDay)) ? Number(campaign.dDay) : null,
      reward: cleanText(campaign.point || campaign.rewardText || campaign.reward_text),
      url: cleanText(campaign.url),
    }));
}
```

## Task 5: SEO Routes, Sitemap, Robots

**Files:**
- Create: `app/page.jsx`
- Create: `app/(seo)/[slug]/page.jsx`
- Create: `app/robots.js`
- Create: `app/sitemap.js`

- [ ] **Step 1: Create `app/page.jsx`**

```jsx
import Link from "next/link";
import { SEO_LANDING_PAGES } from "../src/seo/landingPages";
import { getCampaignsForLanding, getSnapshotUpdatedAt } from "../src/seo/seoCampaignData";
import { absoluteUrl, DEFAULT_SEO_DESCRIPTION, SITE_NAME } from "../src/seo/siteConfig";

export const metadata = {
  title: "전국 체험단 캠페인 모음",
  description: DEFAULT_SEO_DESCRIPTION,
  alternates: {
    canonical: absoluteUrl("/"),
  },
};

export default function HomeSeoPage() {
  const representativePage = SEO_LANDING_PAGES.find((page) => page.slug === "체험단") || SEO_LANDING_PAGES[0];
  const campaigns = getCampaignsForLanding(representativePage, 8);
  const updatedAt = getSnapshotUpdatedAt();

  return (
    <main className="seo-page">
      <section className="seo-hero">
        <p className="seo-eyebrow">{SITE_NAME}</p>
        <h1>전국 체험단 캠페인을 한 곳에서 비교하세요</h1>
        <p>
          맛집, 카페, 뷰티, 숙박, 생활 체험단을 지역, 카테고리, 마감일, 제공내역 기준으로 빠르게 찾아볼 수 있습니다.
        </p>
        <Link className="primary-action" href="/app?tab=explore">
          캠페인 검색하기
        </Link>
      </section>
      <section className="seo-section" aria-labelledby="seo-links-title">
        <h2 id="seo-links-title">체험단 검색 주제</h2>
        <div className="seo-link-grid">
          {SEO_LANDING_PAGES.map((page) => (
            <Link key={page.slug} href={`/${page.slug}`}>
              {page.h1}
            </Link>
          ))}
        </div>
      </section>
      <section className="seo-section" aria-labelledby="seo-campaigns-title">
        <h2 id="seo-campaigns-title">최신 체험단 캠페인</h2>
        <p className="seo-muted">최근 업데이트: {updatedAt}</p>
        <ul className="seo-campaign-list">
          {campaigns.map((campaign) => (
            <li key={campaign.id}>
              <strong>{campaign.title}</strong>
              <span>{[campaign.platform, campaign.province, campaign.city].filter(Boolean).join(" · ")}</span>
              {campaign.reward ? <small>{campaign.reward}</small> : null}
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
```

- [ ] **Step 2: Create `app/(seo)/[slug]/page.jsx`**

```jsx
import Link from "next/link";
import { notFound } from "next/navigation";
import { SEO_LANDING_PAGES, getLandingPage } from "../../../src/seo/landingPages";
import { getCampaignsForLanding, getSnapshotUpdatedAt } from "../../../src/seo/seoCampaignData";
import { absoluteUrl } from "../../../src/seo/siteConfig";

export function generateStaticParams() {
  return SEO_LANDING_PAGES.map((page) => ({ slug: page.slug }));
}

export async function generateMetadata({ params }) {
  const { slug } = await params;
  const page = getLandingPage(slug);
  if (!page) return {};
  return {
    title: page.title,
    description: page.description,
    alternates: {
      canonical: absoluteUrl(`/${page.slug}`),
    },
    openGraph: {
      title: page.title,
      description: page.description,
      url: absoluteUrl(`/${page.slug}`),
    },
  };
}

export default async function SeoLandingPage({ params }) {
  const { slug } = await params;
  const page = getLandingPage(slug);
  if (!page) notFound();

  const campaigns = getCampaignsForLanding(page, 12);
  const updatedAt = getSnapshotUpdatedAt();
  const relatedPages = page.relatedSlugs
    .map((relatedSlug) => getLandingPage(relatedSlug))
    .filter(Boolean);

  return (
    <main className="seo-page">
      <nav className="seo-breadcrumb" aria-label="breadcrumb">
        <Link href="/">체험모아</Link>
        <span>{page.h1}</span>
      </nav>
      <section className="seo-hero">
        <h1>{page.h1}</h1>
        <p>{page.intro}</p>
        <Link className="primary-action" href={`/app${page.appQuery}`}>
          사이트에서 조건별로 보기
        </Link>
      </section>
      <section className="seo-section" aria-labelledby="campaign-list-title">
        <h2 id="campaign-list-title">관련 캠페인</h2>
        <p className="seo-muted">최근 업데이트: {updatedAt}. 모집 조건은 원문 신청 페이지에서 최종 확인하세요.</p>
        <ul className="seo-campaign-list">
          {campaigns.map((campaign) => (
            <li key={campaign.id}>
              <strong>{campaign.title}</strong>
              <span>{[campaign.platform, campaign.category, campaign.province, campaign.city].filter(Boolean).join(" · ")}</span>
              {campaign.reward ? <small>{campaign.reward}</small> : null}
              {campaign.dDay !== null ? <small>D-{campaign.dDay}</small> : null}
            </li>
          ))}
        </ul>
        {!campaigns.length ? (
          <p className="seo-muted">현재 이 조건에 맞는 공개 캠페인이 적습니다. 전체 탐색에서 조건을 넓혀 확인하세요.</p>
        ) : null}
      </section>
      <section className="seo-section" aria-labelledby="related-title">
        <h2 id="related-title">같이 보면 좋은 체험단 검색</h2>
        <div className="seo-link-grid">
          {relatedPages.map((related) => (
            <Link key={related.slug} href={`/${related.slug}`}>
              {related.h1}
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
```

- [ ] **Step 3: Create `app/robots.js`**

```js
import { SEO_SITE_URL } from "../src/seo/siteConfig";

export default function robots() {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
    },
    sitemap: `${SEO_SITE_URL}/sitemap.xml`,
  };
}
```

- [ ] **Step 4: Create `app/sitemap.js`**

```js
import { SEO_LANDING_PAGES } from "../src/seo/landingPages";
import { getSnapshotUpdatedAt } from "../src/seo/seoCampaignData";
import { absoluteUrl } from "../src/seo/siteConfig";

export default function sitemap() {
  const lastModified = new Date(getSnapshotUpdatedAt());
  const routes = [
    { url: absoluteUrl("/"), priority: 1 },
    { url: absoluteUrl("/app"), priority: 0.8 },
    ...SEO_LANDING_PAGES.map((page) => ({
      url: absoluteUrl(`/${page.slug}`),
      priority: page.slug === "체험단" ? 0.9 : 0.75,
    })),
  ];

  return routes.map((route) => ({
    url: route.url,
    lastModified,
    changeFrequency: "daily",
    priority: route.priority,
  }));
}
```

## Task 6: SEO Styling

**Files:**
- Modify: `src/index.css` or create `src/app/seo.css` and import it from `app/layout.jsx`

- [ ] **Step 1: Add constrained SEO page styles**

If creating `src/app/seo.css`, import it in `app/layout.jsx` after existing CSS:

```js
import "../src/app/seo.css";
```

Create `src/app/seo.css`:

```css
.seo-page {
  color: #1f2933;
  background: #fffaf7;
  min-height: 100vh;
}

.seo-hero,
.seo-section,
.seo-breadcrumb {
  width: min(1080px, calc(100% - 32px));
  margin: 0 auto;
}

.seo-hero {
  padding: 56px 0 28px;
}

.seo-eyebrow,
.seo-muted {
  color: #68737d;
  font-size: 0.95rem;
}

.seo-hero h1 {
  margin: 0 0 16px;
  font-size: clamp(2rem, 4vw, 3.5rem);
  line-height: 1.08;
  letter-spacing: 0;
}

.seo-hero p {
  max-width: 720px;
  margin: 0 0 22px;
  font-size: 1.08rem;
  line-height: 1.7;
}

.seo-section {
  padding: 28px 0;
}

.seo-section h2 {
  margin: 0 0 14px;
  font-size: 1.45rem;
}

.primary-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 0 18px;
  border-radius: 8px;
  background: #c1440e;
  color: #fff;
  font-weight: 800;
  text-decoration: none;
}

.seo-link-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}

.seo-link-grid a,
.seo-campaign-list li {
  border: 1px solid #eadfd8;
  border-radius: 8px;
  background: #fff;
}

.seo-link-grid a {
  padding: 14px;
  color: #24313d;
  font-weight: 800;
  text-decoration: none;
}

.seo-campaign-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
  margin: 14px 0 0;
  padding: 0;
  list-style: none;
}

.seo-campaign-list li {
  display: grid;
  gap: 8px;
  padding: 14px;
}

.seo-campaign-list strong {
  font-size: 1rem;
  line-height: 1.45;
}

.seo-campaign-list span,
.seo-campaign-list small {
  color: #68737d;
  line-height: 1.45;
}

.seo-breadcrumb {
  display: flex;
  gap: 8px;
  padding-top: 22px;
  color: #68737d;
  font-size: 0.92rem;
}

.seo-breadcrumb a {
  color: #8d3b15;
  text-decoration: none;
}
```

- [ ] **Step 2: Verify no text overlap at mobile widths**

Run local dev or preview after build and inspect:

```powershell
npm.cmd run build
npm.cmd run start
```

Open `/체험단`, `/서울-맛집-체험단`, `/디너의여왕-체험단` at desktop and mobile widths. No text should overflow buttons/cards.

## Task 7: SEO QA

**Files:**
- Create: `scripts/qa/seo-landing-fixture.mjs`
- Modify: `package.json`

- [ ] **Step 1: Write `scripts/qa/seo-landing-fixture.mjs`**

```js
import assert from "node:assert/strict";
import { SEO_LANDING_PAGES, getLandingPage } from "../../src/seo/landingPages.js";
import { getCampaignsForLanding, getSnapshotUpdatedAt } from "../../src/seo/seoCampaignData.js";
import { SEO_SITE_URL, absoluteUrl } from "../../src/seo/siteConfig.js";

const requiredSlugs = [
  "체험단",
  "블로그체험단",
  "인스타체험단",
  "맛집체험단",
  "서울-맛집-체험단",
  "오늘마감-체험단",
  "디너의여왕-체험단",
];

assert.equal(SEO_SITE_URL, "https://cheheommoa.com");
assert.equal(absoluteUrl("/체험단"), "https://cheheommoa.com/체험단");

for (const slug of requiredSlugs) {
  const page = getLandingPage(slug);
  assert.ok(page, `missing landing page: ${slug}`);
  assert.ok(page.title.includes("체험단"), `title should include 체험단: ${slug}`);
  assert.ok(page.description.length >= 20, `description too short: ${slug}`);
  assert.ok(page.h1.length >= 6, `h1 too short: ${slug}`);
}

const duplicateSlugs = SEO_LANDING_PAGES
  .map((page) => page.slug)
  .filter((slug, index, slugs) => slugs.indexOf(slug) !== index);
assert.deepEqual(duplicateSlugs, []);

const dinnerqueenPage = getLandingPage("디너의여왕-체험단");
const dinnerqueenCampaigns = getCampaignsForLanding(dinnerqueenPage, 5);
assert.ok(dinnerqueenCampaigns.length > 0, "Dinnerqueen landing should have campaigns");
assert.ok(
  dinnerqueenCampaigns.some((campaign) => campaign.reward),
  "Dinnerqueen landing should include at least one reward text",
);

const updatedAt = getSnapshotUpdatedAt();
assert.ok(Date.parse(updatedAt) || updatedAt.length > 0, "snapshot updatedAt should be present");

console.log(JSON.stringify({
  ok: true,
  landingPages: SEO_LANDING_PAGES.length,
  dinnerqueenCampaigns: dinnerqueenCampaigns.length,
  updatedAt,
}));
```

- [ ] **Step 2: Add script to `package.json`**

```json
"qa:seo:landing": "node scripts/qa/seo-landing-fixture.mjs"
```

- [ ] **Step 3: Run QA**

Run:

```powershell
npm.cmd run qa:seo:landing
```

Expected: `{ "ok": true, ... }`.

## Task 8: Build Verification And Static Output Checks

**Files:**
- No new files unless failures require fixes.

- [ ] **Step 1: Run focused QA**

Run:

```powershell
npm.cmd run qa:public-env
npm.cmd run qa:campaigns:source-policy
npm.cmd run qa:campaigns:point-merge
npm.cmd run qa:seo:landing
```

Expected: all pass.

- [ ] **Step 2: Run Next build**

Run:

```powershell
npm.cmd run build
```

Expected: Next build completes. If it fails due browser-only code in a Server Component, move that import behind `src/app/ClientApp.jsx` and rerun.

- [ ] **Step 3: Check generated routes via dev/start**

Run:

```powershell
npm.cmd run start
```

Visit:

```text
http://localhost:3000/
http://localhost:3000/app
http://localhost:3000/체험단
http://localhost:3000/서울-맛집-체험단
http://localhost:3000/디너의여왕-체험단
http://localhost:3000/sitemap.xml
http://localhost:3000/robots.txt
```

Expected:

- landing pages render without blank screens
- `/app` loads the interactive app
- `/sitemap.xml` uses `https://cheheommoa.com`
- `/robots.txt` points to `https://cheheommoa.com/sitemap.xml`

Stop the server after manual check.

## Task 9: Documentation And Handoff

**Files:**
- Modify: `docs/work-log.md`
- Modify: `AGENTS.md` if new rules appear
- Modify: `marketing/README.md` if messaging changes

- [ ] **Step 1: Update `docs/work-log.md`**

Add concise bullets under `2026-05-27`:

```markdown
- Next.js App Router 기반 SEO SSG 전환을 구현했다. 공식 canonical/sitemap/robots 도메인은 `https://cheheommoa.com`이다.
- `/`, `/app`, `/체험단`, `/서울-맛집-체험단`, `/디너의여왕-체험단` 등 검색 의도별 정적 랜딩 페이지와 sitemap/robots를 추가했다.

검증:
- `npm.cmd run qa:public-env`, `npm.cmd run qa:seo:landing`, `npm.cmd run build` 통과.
```

- [ ] **Step 2: Update `AGENTS.md` only if implementation creates new operational rules**

If no new operational rule appears, do not edit `AGENTS.md`.

- [ ] **Step 3: Check git status for relevant files**

Run:

```powershell
git status --short -- AGENTS.md docs/work-log.md docs/superpowers package.json package-lock.json next.config.mjs app src scripts/qa .env.example
```

Expected: only relevant implementation files are listed. Do not stage `AI identity prompt.md`, `.env`, `.cache`, `logs`, `dist`, `.next`, or unrelated runtime files.

## Task 10: Preview Deploy Gate

**Files:**
- No source files unless preview reveals a bug.

- [ ] **Step 1: Ask before any deployment**

Production deploy requires explicit approval. Preview deploy also uses external network and should be announced.

Recommended first deploy command after local build passes:

```powershell
vercel.cmd --yes
```

Do not run `vercel.cmd --prod --yes` until the user explicitly approves production.

- [ ] **Step 2: Verify preview routes manually**

After preview deploy, check:

```text
/
/app
/체험단
/서울-맛집-체험단
/디너의여왕-체험단
/sitemap.xml
/robots.txt
```

Expected: preview works. Canonical and sitemap still point to `https://cheheommoa.com`, not preview host.

## Commit Guidance

Git commit requires explicit user approval in this repository. When approval is given, stage only related files:

```powershell
git add package.json package-lock.json next.config.mjs .env.example app src scripts/qa docs/work-log.md docs/superpowers/specs/2026-05-27-nextjs-seo-ssg-design.md docs/superpowers/plans/2026-05-27-nextjs-seo-ssg.md
git commit -m "Migrate SEO landing pages to Next.js SSG"
```

Do not stage:

```text
AI identity prompt.md
.env
.cache/
logs/
dist/
.next/
node_modules/
unrelated public runtime artifacts
```

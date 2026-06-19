# SEO Landing Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add seven crawlable SEO landing pages for high-supply campaign search terms while avoiding empty pages.

**Architecture:** Keep the existing static landing model. Extend the campaign filter helper with grouped text keyword matching, add seven `SEO_LANDING_PAGES` entries, expose a small set of new links from the home page, and verify that every new page has campaign data.

**Tech Stack:** Next.js App Router, React, Node.js fixture scripts, static `public/campaigns.json` snapshot.

---

## Files

- Modify: `src/seo/seoCampaignData.js`
  - Add `textKeywords` matching support.
- Modify: `src/seo/landingPages.js`
  - Add seven landing page definitions.
  - Keep `/리뷰노트-체험단` excluded.
- Modify: `src/app/page.jsx`
  - Add representative new SEO entry links.
- Modify: `scripts/qa/seo-landing-fixture.mjs`
  - Assert new slugs exist and have data.
  - Assert `/리뷰노트-체험단` is absent.
  - Assert home links include representative new pages.
- Modify: `docs/work-log.md`
  - Record implementation and verification results.

---

### Task 1: Expand SEO Fixture First

**Files:**
- Modify: `scripts/qa/seo-landing-fixture.mjs`

- [ ] **Step 1: Add failing assertions for the new landing pages**

Add a `newLandingSlugs` list:

```js
const newLandingSlugs = [
  "레뷰-체험단",
  "미블-체험단",
  "강남-맛집-체험단",
  "서울-블로그-체험단",
  "부산-카페-체험단",
  "뷰티-체험단-모집",
  "오늘마감-블로그-체험단",
];
```

For each slug:

```js
for (const slug of newLandingSlugs) {
  const page = getLandingPage(slug);
  assert.ok(page, `missing new landing page: ${slug}`);
  const campaigns = getCampaignsForLanding(page, 5);
  assert.ok(campaigns.length > 0, `new landing should have campaigns: ${slug}`);
}
```

Add the explicit exclusion:

```js
assert.equal(getLandingPage("리뷰노트-체험단"), null);
```

Add home link expectations:

```js
for (const expectedFragment of [
  "/레뷰-체험단",
  "/미블-체험단",
  "/강남-맛집-체험단",
  "/부산-카페-체험단",
]) {
  assert.ok(
    homePageSource.includes(expectedFragment),
    `home page should include ${expectedFragment}`,
  );
}
```

- [ ] **Step 2: Run fixture and confirm it fails**

Run:

```powershell
npm.cmd run qa:seo:landing
```

Expected: fails because the new landing pages and home links are not implemented yet.

---

### Task 2: Add Grouped Text Keyword Filtering

**Files:**
- Modify: `src/seo/seoCampaignData.js`

- [ ] **Step 1: Add helper functions**

Add below `hasKeyword()`:

```js
function keywordGroupMatches(text, group) {
  if (Array.isArray(group)) {
    return group.some((keyword) => text.includes(keyword));
  }
  return text.includes(group);
}

function hasTextKeywordGroups(campaign, groups = []) {
  if (!groups.length) return true;
  const text = campaignSearchText(campaign);
  return groups.every((group) => keywordGroupMatches(text, group));
}
```

- [ ] **Step 2: Use the new filter in `matchesLanding()`**

Add before `return true;`:

```js
if (!hasTextKeywordGroups(campaign, filters.textKeywords || [])) return false;
```

- [ ] **Step 3: Run fixture**

Run:

```powershell
npm.cmd run qa:seo:landing
```

Expected: still fails because landing definitions and home links are not added yet.

---

### Task 3: Add Seven Landing Definitions

**Files:**
- Modify: `src/seo/landingPages.js`

- [ ] **Step 1: Add platform landing pages**

Add entries for:

```js
{
  slug: "레뷰-체험단",
  title: "레뷰 체험단 모집 모아보기",
  description: "레뷰에 올라온 맛집, 뷰티, 생활 체험단 모집 정보를 한 곳에서 비교해보세요.",
  h1: "레뷰 체험단 캠페인 모아보기",
  intro: "레뷰 공개 모집 캠페인을 마감일과 제공내역 중심으로 정리해 빠르게 비교할 수 있습니다.",
  filters: { platformIds: ["revu"] },
  appQuery: "?tab=explore&platform=revu",
  relatedSlugs: ["체험단", "오늘마감-체험단", "맛집체험단"],
}
```

```js
{
  slug: "미블-체험단",
  title: "미블 체험단 모집 모아보기",
  description: "미블 체험단 캠페인을 맛집, 카페, 뷰티 등 관심 조건별로 확인해보세요.",
  h1: "미블 체험단 캠페인 모아보기",
  intro: "미블에 올라온 공개 모집 캠페인을 제공내역, 지역, 마감일 기준으로 비교합니다.",
  filters: { platformIds: ["mrblog"] },
  appQuery: "?tab=explore&platform=mrblog",
  relatedSlugs: ["체험단", "맛집체험단", "카페체험단"],
}
```

- [ ] **Step 2: Add region/category landing pages**

Add entries for:

```js
{
  slug: "강남-맛집-체험단",
  title: "강남 맛집 체험단 모집 모아보기",
  description: "강남 지역 맛집 체험단 모집 정보를 마감일과 제공내역 기준으로 비교해보세요.",
  h1: "강남 맛집 체험단 캠페인 모아보기",
  intro: "강남 키워드가 포함된 맛집 체험단 캠페인을 모아 방문 조건과 신청 흐름을 빠르게 확인합니다.",
  filters: { textKeywords: ["강남", ["맛집", "음식", "식품"]] },
  appQuery: "?tab=explore&query=강남%20맛집",
  relatedSlugs: ["맛집체험단", "서울-맛집-체험단", "오늘마감-체험단"],
}
```

```js
{
  slug: "서울-블로그-체험단",
  title: "서울 블로그 체험단 모집 모아보기",
  description: "서울 지역 블로그 리뷰 체험단 캠페인을 한 곳에서 찾아보세요.",
  h1: "서울 블로그 체험단 캠페인 모아보기",
  intro: "서울 키워드와 블로그 리뷰 조건이 있는 체험단 캠페인을 중심으로 정리합니다.",
  filters: { textKeywords: ["서울", "블로그"] },
  appQuery: "?tab=explore&query=서울%20블로그",
  relatedSlugs: ["블로그체험단", "서울-맛집-체험단", "체험단"],
}
```

```js
{
  slug: "부산-카페-체험단",
  title: "부산 카페 체험단 모집 모아보기",
  description: "부산 카페와 디저트 체험단 모집 정보를 조건별로 비교해보세요.",
  h1: "부산 카페 체험단 캠페인 모아보기",
  intro: "부산 지역 카페, 디저트 관련 체험단 캠페인을 마감일과 제공내역 기준으로 모았습니다.",
  filters: { textKeywords: ["부산", ["카페", "디저트"]] },
  appQuery: "?tab=explore&query=부산%20카페",
  relatedSlugs: ["카페체험단", "맛집체험단", "체험단"],
}
```

- [ ] **Step 3: Add beauty and deadline blog landing pages**

Add entries for:

```js
{
  slug: "뷰티-체험단-모집",
  title: "뷰티 체험단 모집 모아보기",
  description: "미용, 헤어, 네일 등 뷰티 체험단 모집 정보를 한 곳에서 비교해보세요.",
  h1: "뷰티 체험단 모집 캠페인 모아보기",
  intro: "뷰티 서비스와 제품 체험단 캠페인을 제공내역, 지역, 마감일 기준으로 확인합니다.",
  filters: { textKeywords: [["뷰티", "미용", "헤어", "네일"]] },
  appQuery: "?tab=explore&category=뷰티",
  relatedSlugs: ["체험단", "인스타체험단", "오늘마감-체험단"],
}
```

```js
{
  slug: "오늘마감-블로그-체험단",
  title: "오늘 마감 블로그 체험단 모집 모아보기",
  description: "오늘 또는 곧 마감되는 블로그 체험단 캠페인을 빠르게 확인해보세요.",
  h1: "오늘 마감 블로그 체험단 캠페인 모아보기",
  intro: "마감이 가까운 블로그 리뷰 체험단 캠페인을 우선 정리해 신청 기회를 놓치지 않도록 돕습니다.",
  filters: { maxDday: 1, textKeywords: ["블로그"] },
  appQuery: "?tab=explore&preset=deadline&query=블로그",
  relatedSlugs: ["오늘마감-체험단", "블로그체험단", "체험단"],
}
```

- [ ] **Step 4: Run fixture**

Run:

```powershell
npm.cmd run qa:seo:landing
```

Expected: still fails only on missing home links if the landing filters are correct.

---

### Task 4: Add Representative Home Links

**Files:**
- Modify: `src/app/page.jsx`

- [ ] **Step 1: Add four home search entry links**

Add to `SEARCH_ENTRY_LINKS`:

```js
{ label: "레뷰 체험단", href: "/레뷰-체험단" },
{ label: "미블 체험단", href: "/미블-체험단" },
{ label: "강남 맛집 체험단", href: "/강남-맛집-체험단" },
{ label: "부산 카페 체험단", href: "/부산-카페-체험단" },
```

- [ ] **Step 2: Run fixture**

Run:

```powershell
npm.cmd run qa:seo:landing
```

Expected: passes.

---

### Task 5: Final Verification And Docs

**Files:**
- Modify: `docs/work-log.md`

- [ ] **Step 1: Run full verification**

Run:

```powershell
npm.cmd run qa:seo:landing
npm.cmd run qa:public-env
npm.cmd run build
git diff --check -- src/seo/landingPages.js src/seo/seoCampaignData.js src/app/page.jsx scripts/qa/seo-landing-fixture.mjs docs/work-log.md
```

Expected:

- Both QA fixtures pass.
- Next build succeeds.
- `git diff --check` has no errors.

- [ ] **Step 2: Update work log**

Record:

- Seven landing pages added.
- `/리뷰노트-체험단` intentionally excluded because current snapshot has 0 matching campaigns.
- Verification commands and results.

- [ ] **Step 3: Stage only related files**

Run:

```powershell
git add -- `
  docs/superpowers/specs/2026-05-28-seo-landing-expansion-design.md `
  docs/superpowers/plans/2026-05-28-seo-landing-expansion.md `
  docs/work-log.md `
  src/seo/landingPages.js `
  src/seo/seoCampaignData.js `
  src/app/page.jsx `
  scripts/qa/seo-landing-fixture.mjs
git diff --cached --check
git diff --cached --name-status
```

Expected: only the related files are staged.

- [ ] **Step 4: Commit after user approval**

Use:

```powershell
git commit -m "Expand SEO landing pages for campaign searches"
```

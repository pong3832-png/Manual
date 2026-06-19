# Work Log

## 2026-06-05

### UI/UX planning document application
- Read `docs/CAMP_UIUX_기획서_v1.2_최종_실무착수본.docx` via extracted DOCX text and reviewed it in five passes: product principles, conversion/KPI, data trust, mobile/component spec, and immediate low-risk application.
- Applied the strongest low-risk fit: clarified external-apply copy so cards say `원본 신청`, the detail CTA says `원본 플랫폼에서 신청하기`, and the detail hint states that real application happens on the source platform.
- Added `apply_click` analytics metadata for external apply context: `externalApply`, source `applyDomain`, and `deadlineDays`, without renaming the existing event type.
- Verification passed: targeted ESLint for `src/app/App.jsx`, `CampaignCard.jsx`, `DetailModal.jsx`; `npm.cmd run build`.
- Deferred larger doc items for separate scoped work: GA4/BigQuery migration, crawler status/allowlist contract, duplicate-group DB changes, onboarding-based recommendation, Saved sync, and admin/review flows.

### Delivery display trust polish
- Checked local production build for `/`, `/app?tab=explore`, and `/app?tab=explore&type=delivery` on desktop and mobile with `agent-browser` screenshots/DOM checks. No framework overlay or page errors were found.
- Fixed delivery card fulfillment display so benefit text such as `포장불가` no longer turns a delivery campaign into `포장형`; explicit packaging/pickup cases still show `포장형`.
- Verification passed: `node .\scripts\qa\campaign-display-fixture.mjs`; targeted ESLint for the touched display/QA files; `node .\scripts\qa\seo-landing-fixture.mjs`; `npm.cmd run build`.
- Next: commit only `src/features/campaigns/lib/campaigns.js`, `scripts/qa/campaign-display-fixture.mjs`, and this work log entry. Deploy only after explicit user approval, then continue Search Console/Naver checks.

## 2026-06-02

### UI trust polish after visual check
- Checked local `/`, `/app?tab=explore`, and `/app?tab=explore&type=delivery` on desktop and mobile with `agent-browser`; no page errors were found.
- Changed home hero headline wrapping/copy, Explore quick-scope text, delivery card fulfillment display (`포장형` for pickup/packaging cases), and display-only benefit cleanup for URLs/guideline notes.
- Verification passed: `node .\scripts\qa\campaign-display-fixture.mjs`; targeted ESLint for touched JS/JSX/QA files; `node .\scripts\qa\seo-landing-fixture.mjs`; `npm.cmd run build`.
- Next: commit only the related UI/QA/work-log files, then deploy only after explicit user approval and continue Search Console/Naver checks after deploy.

### Search Console handoff
- Deployed SEO landing and sitemap fixes: `c3efe63` delivery/product landings, `8be22ba` encoded dynamic sitemap URLs, `5f20731` alternate `sitemap-pages.xml`, and `588bad5` dynamic robots exposing both sitemap URLs.
- Public checks passed after deploy: `/sitemap.xml` and `/sitemap-pages.xml` return `200 OK` with `Content-Type: application/xml`; `/robots.txt` lists both sitemap URLs; sitemap URLs are percent-encoded.
- Search Console property is `https://camp-platform-liart.vercel.app/`, but both `/sitemap.xml` and `sitemap-pages.xml` still showed `가져올 수 없음` in the UI after retry.
- Next session: click the `sitemap-pages.xml` row and capture the detailed error text. If no detail is available, add a plain text `sitemap.txt` fallback and submit that. Avoid repeated same-day resubmits without a new error detail.

### Delivery/product SEO landing growth
- Added SEO landing pages for `배송형-체험단` and `제품-체험단`, with home entry links and static sitemap coverage.
- Extended SEO campaign filtering to support delivery/product campaign-type matching while preserving the existing landing page filtering behavior.
- Verification passed: `node .\scripts\qa\seo-landing-fixture.mjs`; `node .\scripts\qa\campaign-display-fixture.mjs`; targeted ESLint for touched SEO/home/QA files; `npm.cmd run build`.
- Deployed in commit `c3efe63`; continue with Search Console/Naver status checks only.

### Search Console sitemap fetch fix
- Search Console still reported `/sitemap.xml` as `가져올 수 없음` even though the public endpoint returned `200 OK`.
- Found the served Next dynamic sitemap emitted Korean slug URLs unescaped, while the static `public/sitemap.xml` used percent-encoded URLs. Updated the dynamic sitemap route to emit encoded URLs and added QA coverage for encoded dynamic sitemap entries.
- Verification passed: `node .\scripts\qa\seo-landing-fixture.mjs`; targeted ESLint for `src/app/sitemap.js` and `scripts/qa/seo-landing-fixture.mjs`; `npm.cmd run build`.
- Deployed in commit `8be22ba`; `/sitemap.xml` still stayed stuck in Search Console, so use the alternate sitemap fallback path below.

### Alternate sitemap fallback
- Search Console still reported `/sitemap.xml` as `가져올 수 없음` after the encoded dynamic sitemap deploy. Added `public/sitemap-pages.xml` as a static mirror and declared it in `robots.txt` so Search Console can retry with a fresh sitemap URL.
- Follow-up: the served robots file is generated by `src/app/robots.js`, so the dynamic robots route now returns both sitemap URLs as well.
- Verification passed: `node .\scripts\qa\seo-landing-fixture.mjs`; targeted ESLint for `src/app/robots.js` and `scripts/qa/seo-landing-fixture.mjs`; `npm.cmd run build`.
- Deployed in commits `5f20731` and `588bad5`; submit/check `sitemap-pages.xml`, then capture the row detail if it still fails.

### Delivery card display trust check
- Checked local `/`, `/app?tab=explore`, and `/app?tab=explore&type=delivery` on desktop and mobile. No console/page errors and no `COPYRIGHT`, `D-99`, or raw `미정` exposure were found.
- Changed delivery display formatting so delivery campaigns show `배송형` instead of visit-style addresses or bracket tokens such as `[클립]` in card/detail location areas. Visit campaign location display is unchanged.
- Verification passed: `node .\scripts\qa\campaign-display-fixture.mjs`; targeted ESLint for `src/features/campaigns/lib/campaigns.js` and `scripts/qa/campaign-display-fixture.mjs`; `node .\scripts\qa\seo-landing-fixture.mjs`; `npm.cmd run build`; Playwright desktop/mobile screenshots for delivery cards and modal.
- Next: commit only the UI/QA/work-log files after final status review, then deploy only after explicit user approval. Runtime `public/*.json`, root screenshots, `.cache` screenshots, and dev-server logs remain local artifacts unless explicitly requested.

### Public delivery snapshot redeploy
- User approved committing the current public snapshot after production Git deploy showed `/app?tab=explore&type=delivery` empty because the previous committed snapshot had no delivery campaigns.
- Snapshot to publish: `public/campaigns.json` total `18,681`, including `delivery 1,680`; related public status/check/quality JSON files are included with the snapshot.
- Keep excluding unrelated local files: `public/HTML편집.txt`, `ui-app.png`, `ui-home.png`, `.cache` screenshots.

## 2026-06-01

### Public UI trust pass
- Changed: cleaned `/` home copy, removed internal validation wording, changed home counts to uncapped landing counts, formatted snapshot time as readable KST, and hid empty featured sections.
- Changed: added campaign display formatting so cards/details strip `COPYRIGHT`, hide raw `미정`, show `D-99`/missing deadlines as `마감일 확인`, and use `배송형` as the fallback label for delivery campaigns without a location.
- Added QA: `scripts/qa/campaign-display-fixture.mjs`; extended `scripts/qa/seo-landing-fixture.mjs` for home copy/count/date guards.
- Verification passed: `node .\scripts\qa\campaign-display-fixture.mjs`; `node .\scripts\qa\seo-landing-fixture.mjs`; targeted ESLint for touched UI/SEO/QA files; `npm.cmd run build`; local `http://127.0.0.1:3002/` returned 200; agent-browser checked `/` and `/app?tab=explore` with no overlay and no `D-99`/`COPYRIGHT`/raw `미정` exposure.
- Current dirty files to avoid staging unless explicitly intended: runtime `public/*.json`, `public/HTML편집.txt`, old root screenshots `ui-home.png`, `ui-app.png`; new `.cache/ui-*-check.png` screenshots are local verification artifacts only.
- Next session: 1) inspect current `git status`; 2) if port `3002` is occupied, check whether the previous local Next dev server is still running; 3) visually review `/` and `/app?tab=explore&type=delivery` on desktop/mobile; 4) commit only the UI/SEO/QA/work-log files if approved; 5) deploy only after user approval; 6) after deploy, verify public `/`, `/app?tab=explore`, `/robots.txt`, `/sitemap.xml`; 7) retry Google Search Console sitemap/URL inspection after quota reset and check Naver collection status.

### End-of-session search handoff
- Changed today: switched the active SEO canonical target to the free Vercel alias `https://camp-platform-liart.vercel.app`, pushed `2b181bc`, and confirmed Vercel Production deployment `dpl_GKiZ5FZcVm3SUPAj4v9r2wa4M9Q5` is `READY`.
- User completed Google Search Console and Naver Search Advisor setup/submission for `https://camp-platform-liart.vercel.app` and sitemap `https://camp-platform-liart.vercel.app/sitemap.xml`.
- Verification: `node .\scripts\qa\seo-landing-fixture.mjs` passed; public `/robots.txt` and `/sitemap.xml` both return `200`; sitemap serves `Content-Type: application/xml` and lists the SEO landing URLs. Search Console currently shows sitemap as “couldn't fetch”, but local/public fetch is normal and the user saw indexing status present.
- Google URL inspection quota is exhausted today. Do not keep retrying today; retry after quota resets.
- Next session: recheck Google sitemap status and URL inspection for `/`, `/체험단`, `/맛집체험단`, `/오늘마감-체험단`; check Naver collection status; only if sitemap still cannot be fetched after waiting, investigate sitemap encoding/route output. Then decide whether to add `배송형 체험단`/`제품 체험단` landing pages.

### Free Vercel SEO canonical decision
- Decided not to pay for custom-domain DNS right now. The operational SEO canonical target is the free Vercel domain `https://camp-platform-liart.vercel.app`.
- Updated default SEO config, Vite fallback HTML canonical/OG URL, static `robots.txt`, static `sitemap.xml`, and `seo-landing-fixture` expectations to use the free Vercel domain.
- Verification passed: `node .\scripts\qa\seo-landing-fixture.mjs`.
- Next: submit `https://camp-platform-liart.vercel.app/sitemap.xml` to Google Search Console and Naver Search Advisor. If a custom domain is connected later, switch canonical/sitemap back after DNS resolves.

### Live SEO domain audit
- Checked public SEO endpoints after the sitemap baseline work. `https://camp-platform-liart.vercel.app/robots.txt`, `/sitemap.xml`, and `/체험단` return `200`; sitemap includes the SEO landing pages.
- Google-style `site:` checks did not show indexed results yet for either `camp-platform-liart.vercel.app` or `cheheommoa.com`.
- `cheheommoa.com` currently fails DNS resolution (`NXDOMAIN`). Vercel has the domain attached to `camp-platform`, but DNS is not configured.
- Vercel recommended DNS records from `vercel domains inspect`: `A cheheommoa.com 76.76.21.21` and `A www.cheheommoa.com 76.76.21.21`, or switch nameservers to `ns1.vercel-dns.com` / `ns2.vercel-dns.com`.
- Until DNS is configured and propagates, submit/check `https://camp-platform-liart.vercel.app/sitemap.xml`; after DNS works, submit `https://cheheommoa.com/sitemap.xml`.

### SEO canonical sitemap baseline
- Normalized static SEO entrypoints to the canonical domain `https://cheheommoa.com`: `index.html` canonical/OG URL, `public/robots.txt`, and `public/sitemap.xml`.
- Expanded static `sitemap.xml` beyond the home page to include `/app` and all 17 SEO landing pages, using percent-encoded Korean slugs.
- Improved SEO landing campaign ordering so campaigns with reward/provision text are preferred within the same D-day group. This keeps landing snippets more useful when the latest public snapshot has mixed enrichment depth.
- Extended `scripts/qa/seo-landing-fixture.mjs` to guard robots/sitemap canonical URLs and landing-page sitemap coverage. Verification passed: `node .\scripts\qa\seo-landing-fixture.mjs`.

### Full crawl completion and Ringble seed fix
- User-run full crawl finished as `completed_with_errors`: started `2026-06-01 11:07:51 KST`, completed `2026-06-01 13:26:44 KST`, active platforms `13`, failed platforms `0`, candidate campaigns `18,681`.
- Quality gate was `passed_with_warnings` with `canPublish=true`; coordinate completeness was `55.8%`, address completeness `79.4%`.
- Latest delivery counts from `*-last-crawl.json`: Mrblog `154/2,581`, Reviewplace `428/887`, Comeplay `35/451`, Popomon `164/3,366`, Pavlo `14/60`, Revu `597/2,818`, Gangnam `231/5,689`, Tble `110/476`, Tqueens `70/70`, Dinnerqueen `107/8,657`, Chvu `375/6,600`, Seouloba `291/686`, Ringble `0/275`.
- Supabase sync failed with FK error: `campaigns_platform_id_fkey`. Root cause was `ringble` campaigns in crawler output while `PLATFORM_SEEDS` had no `ringble` row.
- Added `ringble` to `PLATFORM_SEEDS` and added `scripts/qa/platform-seeds-fixture.cjs` to guard that crawler platform IDs have Supabase seeds. No live crawl or Supabase sync rerun was performed after the fix.

### Delivery crawler handoff check
- Checked the current crawl state before any limited crawl. Local time was `2026-06-01 10:25 KST`; no `crawl.cjs`/`npm run crawl` node process was running. The latest 17:00 full-crawl evidence is `2026-05-29 17:00 KST`, completed around `19:20 KST`.
- Latest `*-last-crawl.json` artifacts are from `2026-05-29`: Mrblog 2,717 total / 158 delivery, Reviewplace 1,039 / 441, Comeplay 439 / 41, Popomon 3,385 / 168, Pavlo 60 / 14, Revu 3,268 / 637, Gangnam 5,715 / 243, Tble 517 / 119, Tqueens 64 / 64, Dinnerqueen 7,916 / 95, Chvu 6,600 / 376.
- `quality-gate.json` is `passed_with_warnings`, `canPublish=true`, `blockingFailures=[]`; no `quarantine` marker was found in latest crawl artifacts. Supabase sync remains blocked by `exceed_egress_quota`.
- Revu product-tab behavior was rechecked in code: `REVU_LIST_SCOPE=delivery` resolves to the product category only, and product-category rows map to `type=delivery`. Added fixture coverage for the scoped category selection.
- Verification passed: `node --check .\scripts\crawler\crawl.cjs`, `node .\scripts\qa\delivery-category-fixture.mjs`, `mrblog/reviewplace/comeplay/popomon/pavlo` delivery fixtures, and `node .\scripts\qa\revu-product-fixture.cjs`.
- No live `CRAWL_ONLY=... npm run crawl` was run in this session. Run limited live crawls only after explicit user approval, and do not start them while a full crawl is running.

## 2026-05-29

### 배송형 소스 추가 인수인계
- 오늘 변경: Tble, Tqueens, Mrblog, Reviewplace, Comeplay, Popomon, Pavlo 배송형 제한 수집 경로와 fixture를 추가/보강했다. Revu/Gangnam 제한 크롤은 type summary와 `*-last-crawl.json` artifact를 남기게 했다.
- 검증: `node --check scripts/crawler/crawl.cjs`; Tble, Tqueens, Mrblog, Reviewplace, Comeplay, Popomon, Pavlo 배송형 fixture 통과. 방문형/배송형 상위 필터 fixture도 통과 상태.
- 사용자 실행 live 결과: Revu `627` total(`611` delivery + 16 non-delivery media rows), Gangnam `91` delivery, Tble `116` delivery, Tqueens `63` delivery. Supabase sync는 `exceed_egress_quota`로 계속 실패.
- 최신 코드 기준 live 미확인: Mrblog, Reviewplace, Comeplay, Popomon, Pavlo. 사용자의 전체 크롤이 실행 중이면 이 제한 크롤들을 겹쳐 실행하지 않는다.
- 다음 세션: 전체 크롤 종료 확인 후 Mrblog/Reviewplace/Comeplay/Popomon/Pavlo 제한 크롤, 개수/quarantine 기록, Revu 제품 카테고리 행을 전부 `delivery`로 강제할지 결정, 이후 Reviewnote 배송형 추가.

### End-of-session handoff
- Changed today: fixed Dinnerqueen delivery paging (`41` live delivery campaigns), reran Ringble after point/coordinate fixes, added Revu product delivery, added Gangnam `ca=30` delivery parsing, split frontend filters into top-level `방문형/배송형` type and second-level detail categories, fixed `/app?tab=...` routing, and deployed commit `fbc6cbf`.
- Verified: Dinnerqueen delivery QA/crawl, Ringble QA/crawl, Revu/Gangnam fixtures, delivery category/type fixture, app routing fixture, targeted ESLint, `npm.cmd run build`, `agent-browser` check for `/app?tab=explore&type=delivery`, and Vercel production deployment `dpl_DzJ4wJ9hMribbY5Vvd899R62CTDr`.
- Deployment: `https://camp-platform-liart.vercel.app/app?tab=explore&type=delivery` now opens Explore with `유형 > 배송형`; deployment was made from a clean `HEAD` worktree so dirty `public/*.json` and unrelated local changes were not included.
- Next session: wait for new source details from the user, add each source with a small parser + fixture first, then user-run limited crawl before any full crawl/snapshot publish. SEO technical setup is done; remaining SEO work is Search Console/Naver indexing/status checks and later performance review.
- Still blocked/deferred: Supabase `exceed_egress_quota` blocks Dinnerqueen `reward_text` DB sync; Google URL inspection quota should be retried later; do not commit/deploy current dirty `public/*.json` unless the user explicitly chooses that snapshot.

### Dinnerqueen delivery pagination check
- Inspected the live browser network for `https://dinnerqueen.net/taste?ct=배송` with `agent-browser`. Infinite scroll calls only `/taste/taste_list`; no separate delivery API was observed.
- Actual scroll request params were `ct=배송`, `area1=전국`, `area2=전체`, `page`, `ctype=`, and `query=`. `lpage`, `deal`, `cate`, and `order` were used in the browser history/Referer URL, not the XHR API URL. Default delivery view had no active `sns[]` filter.
- Current live API sample returned page 1 with 30 links and `has_next=true`, page 2 with 11 links and `has_next=false`, and page 3 as an empty `[]` response. Main carousel links are separate page links and are not part of the list API grid.
- Updated `crawlDinnerqueen()` to parse `has_next`, stop on `has_next=false`, and continue past duplicate-only pages only when the response explicitly says another page exists. Added QA coverage for delivery request params, response parsing, terminal pages, and duplicate-only continuation rules.
- Verification passed: `node --check scripts/crawler/crawl.cjs` and `npm.cmd run qa:dinnerqueen:delivery`.
- Ran the approved limited crawl with `CRAWL_ONLY=dinner` and `DINNERQUEEN_LIST_SCOPE=delivery`. The crawler collected 41 Dinnerqueen delivery campaigns, matching the live API sample above. Detail enrich filled provision text for 39/41 campaigns; two detail requests timed out.
- User rechecked the expected count and confirmed 41 is the correct current Dinnerqueen delivery count, so no extra hidden delivery API/filter source is being pursued.
- The run was intentionally blocked by quality gate because a delivery-only Dinnerqueen run is much smaller than the previous full Dinnerqueen baseline (`visible count 2` below the full-source threshold from previous 3,284). `public/campaigns.json` was kept unchanged and Supabase sync was skipped.
- Next: keep delivery snapshot publish/deploy blocked unless the quality gate/test-only behavior is adjusted deliberately; then rerun only if we need a published delivery-only artifact.

### Ringble limited crawl rerun
- Ran the approved limited crawl with `CRAWL_ONLY=ringble`. The crawler collected 223 Ringble campaigns, enriched 223/223 detail pages, and ran Kakao geocoding for 223/223.
- The previous `point` pollution check passed after the filter fix: `public/campaigns.json` contains 223 Ringble rows and 0 rows matching `모집 기간` or `리뷰어 신청하기` in the snapshot.
- Quality gate passed with warnings and updated `public/campaigns.json` to 17,078 published campaigns. Warning: 80/223 Ringble campaigns shared the same Kakao address coordinate cluster (`37.574703,127.002749`) and were invalidated.
- Investigated the Ringble coordinate cluster: affected rows had no extracted visit address and only a Naver map URL plus title region hint. Updated Ringble geocoding so it no longer geocodes `[지역/시군구] 상호명` title hints; Ringble still geocodes when an actual `addressRaw` visit address is extracted. Added QA coverage for both cases.
- Re-ran `CRAWL_ONLY=ringble` after also rejecting the known Kakao fallback coordinate (`37.574703,127.002749`) at geocode result/cache time. The cluster warning disappeared; `public/campaigns.json` now has 213 Ringble rows, 0 rows at the bad coordinate, 0 coordinate invalidations, and 0 `point` pollution rows.
- Supabase sync still failed because the project remains restricted by `exceed_egress_quota`; local/public snapshot was updated, but DB sync is still blocked until quota/spend-cap is resolved.
- Follow-up safe verification passed: `node --check scripts/crawler/crawl.cjs`, `npm.cmd run qa:dinnerqueen:delivery`, `npm.cmd run qa:ringble`, and `npm.cmd run qa:crawler:active-selection`.

### Revu product delivery intake
- Added Revu product category support by including `cat=제품` alongside `cat=지역` in the Revu API crawl. Product-category Revu campaigns now map to `type=delivery` even when the media channel is blog or Instagram.
- Extracted Revu API item normalization into a testable helper and added QA coverage using the provided product campaign examples (`1345843`, `1345875`) for reward, applicant count, thumbnail, and type mapping.
- Verification passed: `node --check scripts/crawler/crawl.cjs` and `node scripts/qa/revu-product-fixture.cjs`.

### Gangnam product delivery intake
- Added a testable Gangnam list parser for `ca=30` product/delivery rows. It now reads `dd.sub_tit` rewards, thumbnail URLs, applicant/recruit counts, and maps category `30` rows to `type=delivery`.
- Refactored `crawlGangnam()` to use the shared parser for all Gangnam list categories while preserving duplicate-page stopping behavior.
- Added a detail enrichment guard so Gangnam delivery campaigns do not pick up address/coordinate values from product detail pages.
- Verification passed: `node --check scripts/crawler/crawl.cjs`, `node --check scripts/qa/gangnam-provision-fixture.cjs`, `node scripts/qa/gangnam-provision-fixture.cjs`, and `npm.cmd run qa:crawler:active-selection`.

### Delivery category exposure
- Superseded in the next section: `배송형` must not stay as a detailed campaign category.
- Added `배송형` to the shared campaign category list, slug mapping, color map, and emoji map so it appears as a first-class Explore/Home/Map category filter.
- Updated frontend campaign category normalization so `type=delivery` campaigns from Dinnerqueen, Gangnam, Chvu, and other platforms are grouped under `배송형` even when the original source category is `맛집` or `생활용품`.
- Added `scripts/qa/delivery-category-fixture.mjs` to lock the new category, slug, and delivery-type grouping behavior.
- Verification passed: `node scripts/qa/delivery-category-fixture.mjs`.

### Campaign type and category split
- Corrected the delivery UX model: `방문형` and `배송형` are now top-level campaign type filters, while `맛집`, `뷰티`, `생활용품`, and other labels remain second-level campaign categories.
- Updated frontend normalization so delivery campaigns keep `campaignType=delivery` / `campaignMode=배송형` without overwriting their detailed `category`.
- Updated Explore and Map filters to show a separate `유형` row before the detailed category row.
- Verification passed: `node scripts/qa/delivery-category-fixture.mjs` and targeted ESLint for the touched frontend/filter files.

### App tab URL routing
- Fixed `/app?tab=explore&type=delivery` so shared Explore/Map links open the requested app tab instead of always starting on Home.
- Added `src/app/appRouting.js` and `scripts/qa/app-routing-fixture.mjs` to lock allowed tab parsing, including hidden `ops` behavior.
- Browser check confirmed the delivery Explore URL now renders the `유형` row with `전체`, `방문형`, `배송형`, followed by detailed category filters and delivery campaign cards.

## 2026-05-28

### Vercel custom domain and SEO verification
- Added Vercel aliases for `cheheommoa.com` and `www.cheheommoa.com` to the latest production deployment `dpl_CvRNXFTgc2t1k6K7CAG9Hx85qQHu` (`camp-platform-clmlsxg5j-pong3832-pngs-projects.vercel.app`).
- Vercel domain inspection still reports DNS not configured. Required DNS is `A cheheommoa.com 76.76.21.21` and `A www.cheheommoa.com 76.76.21.21`, or delegation to `ns1.vercel-dns.com` / `ns2.vercel-dns.com`.
- `Resolve-DnsName cheheommoa.com` and `Resolve-DnsName www.cheheommoa.com` still return NXDOMAIN, so production URL, Google Search Console, and Naver Search Advisor submission remain blocked until DNS propagates.
- Vercel domain availability check says `cheheommoa.com` is still available for purchase (`$11.25 USD` for 1 year), so the likely blocker is that the domain has not been registered yet.
- Confirmed Vercel deployment protection is `all_except_custom_domains`; `*.vercel.app` stays protected, but custom domains should be public after DNS is fixed.
- Supabase check and Dinnerqueen Supabase sync remain blocked by `exceed_egress_quota`. Dry-run target is 2,962 existing Dinnerqueen public `point` values for DB `reward_text` sync.
- Updated `eslint.config.js` for the Next/Vite mixed app: ignore `.next`, allow Node globals, and disable Vite fast-refresh export checks for Next App Router/API files.
- Verification passed: `npm.cmd run qa:public-env`, `npm.cmd run qa:seo:landing`, `npm.cmd run lint`, `npm.cmd run build`.
- Rebuilt `/` from a thin SEO shell into a structured service home with primary CTA, campaign status metrics, search-intent entry links, featured sections for deadline/Seoul food/Dinnerqueen campaigns, and a clear flow into the existing `/app` search experience.
- Added QA coverage so the home page keeps links to `/app?tab=explore`, `/오늘마감-체험단`, `/서울-맛집-체험단`, `/디너의여왕-체험단`, `home-deadline`, and `home-platforms`.
- Deployed the structured home update to Vercel Production: `dpl_2hmeqEpkpzL5wBGHAyKTPKSQHNt5`, URL `https://camp-platform-l08m3lnzu-pong3832-pngs-projects.vercel.app`. Vercel aliases now point `camp-platform-liart.vercel.app`, `camp-platform-pong3832-pngs-projects.vercel.app`, `cheheommoa.com`, and `www.cheheommoa.com` to this deployment; `cheheommoa.com` DNS/domain ownership is still the external blocker.
- Verified the public Vercel alias `https://camp-platform-liart.vercel.app`: `/`, `/app`, `/체험단`, `/서울-맛집-체험단`, `/디너의여왕-체험단`, `/sitemap.xml`, and `/robots.txt` all returned HTTP 200; browser check showed no Next/Vite error overlay and rendered the new home sections.
- After pushing `47519c9`, the GitHub-triggered Vercel deployment `camp-platform-lvys41ypz-pong3832-pngs-projects.vercel.app` failed because `src/screens/OpsPage.jsx` imported analytics market-report exports that were present locally but missing from the committed `src/features/analytics/lib/analytics.js`. The currently serving manual production deployment remains `READY`.
- Fixed the missing analytics exports and pushed `fe11392`. The GitHub-triggered production deployment `dpl_7dE6Ysub21a9M2eqnEi9X4B8HqjH` is `READY`, and `camp-platform-liart.vercel.app`, `cheheommoa.com`, and `www.cheheommoa.com` aliases now point to `camp-platform-6mwjsgx7v-pong3832-pngs-projects.vercel.app`.
- Rechecked the public Vercel alias after the GitHub deployment: `/`, `/app`, `/체험단`, `/서울-맛집-체험단`, `/디너의여왕-체험단`, `/sitemap.xml`, and `/robots.txt` returned HTTP 200. Browser check returned no Next/Vite overlay and confirmed the new structured home content. Sitemap canonical URLs still use `https://cheheommoa.com`, so Search Console/Naver remain blocked until domain ownership/DNS is resolved.
- Rechecked blockers: `cheheommoa.com` and `www.cheheommoa.com` still return NXDOMAIN, and `node .\scripts\ops\check-supabase.cjs` still fails before DB sync. Updated `src/seo/siteConfig.js` so `NEXT_PUBLIC_PUBLIC_SITE_URL` or `VITE_PUBLIC_SITE_URL` can override the SEO canonical/sitemap origin while keeping `https://cheheommoa.com` as the default.
- For the temporary SEO path, pushed `0d25178`, added Vercel Production env `NEXT_PUBLIC_PUBLIC_SITE_URL=https://camp-platform-liart.vercel.app`, and redeployed `dpl_C3rw51ibuivQbFBgz1jkUgYaa1BR` (`camp-platform-ev2ivzdxt-pong3832-pngs-projects.vercel.app`, `READY`). `camp-platform-liart.vercel.app` now serves sitemap, robots, canonical, and `og:url` tags with the Vercel alias origin.
- Search submission prep: `https://camp-platform-liart.vercel.app/sitemap.xml`, `/robots.txt`, `/오늘마감-체험단`, `/서울-맛집-체험단`, and `/디너의여왕-체험단` returned HTTP 200. Google Search Console and Naver Search Advisor both opened to login screens in `agent-browser`, so sitemap submission/index requests require an authenticated browser session before continuing.
- Added Google Search Console HTML verification file candidate `public/googlee0f5f1649e1592a4.html`; it must stay deployed so ownership verification remains valid.
- Pushed Google verification file in `6791ac3`; Vercel production deployment `dpl_7g5HGfZKy9k5aw7ZePmVxuyPyWpf` is `READY`, and `https://camp-platform-liart.vercel.app/googlee0f5f1649e1592a4.html` returns HTTP 200 with the expected `google-site-verification` content.
- User confirmed Google Search Console ownership verification succeeded for `https://camp-platform-liart.vercel.app/`. Rechecked `sitemap.xml`, `/`, `/체험단`, and `/오늘마감-체험단`; all returned HTTP 200 before sitemap/index submission.
- Google Search Console URL inspection quota was reached before requesting indexing for `/체험단`, `/서울-맛집-체험단`, `/오늘마감-체험단`, and `/디너의여왕-체험단`. Remind the user to retry these tomorrow, starting with `/체험단` and `/오늘마감-체험단`.
- Naver Search Advisor showed an access failure when the user tried to add `https://camp-platform-liart.vercel.app/`. Local checks returned HTTP 200 for `/` and `/robots.txt`, including with a Naver Yeti-style user-agent, so the next retry should use the site root without a trailing slash: `https://camp-platform-liart.vercel.app`.
- Added Naver Search Advisor HTML verification file candidate `public/naver1f22d1c4fe7f26bc2b5b94fbf0ee2629.html`; it must stay deployed so ownership verification remains valid.
- Pushed Naver verification file in `7200c0f`; Vercel production deployment `dpl_Ftt5HXkNSAd8d7sxVBSPQdVs2j8e` is `READY`, and `https://camp-platform-liart.vercel.app/naver1f22d1c4fe7f26bc2b5b94fbf0ee2629.html` returns HTTP 200 with the expected `naver-site-verification` content.
- Naver Search Advisor robots.txt was collected successfully at `2026-05-28 15:22:42 KST`. User requested page collection for `/`, `/체험단`, `/오늘마감-체험단`, `/서울-맛집-체험단`, and `/디너의여왕-체험단` between `15:25:28` and `15:26:03 KST`.
- Naver Search Advisor sitemap submission is present as `sitemap.xml`, submitted at `2026-05-28 15:21:56 KST`.
- Drafted SEO landing expansion design in `docs/superpowers/specs/2026-05-28-seo-landing-expansion-design.md`. Current data supports adding `/레뷰-체험단`, `/미블-체험단`, `/강남-맛집-체험단`, `/서울-블로그-체험단`, `/부산-카페-체험단`, `/뷰티-체험단-모집`, and `/오늘마감-블로그-체험단`; `/리뷰노트-체험단` remains excluded until matching campaigns exist.
- Implemented the SEO landing expansion plan in `docs/superpowers/plans/2026-05-28-seo-landing-expansion.md`: added `textKeywords` grouped filtering, seven new landing definitions, representative home links, and QA coverage that keeps `/리뷰노트-체험단` excluded until data exists.
- Verification passed: `npm.cmd run qa:seo:landing` (`landingPages=17`), `npm.cmd run qa:public-env`, `npm.cmd run build` (23 static pages), and `git diff --check` for the related files.
- Pushed SEO landing expansion in `95d2e7d`; Vercel production deployment `dpl_7bXx6HDMFZaEGw8PCNP6TggJV5Bz` is `READY`. Verified all seven new landing URLs return HTTP 200 and `sitemap.xml` includes `/레뷰-체험단`, `/미블-체험단`, `/강남-맛집-체험단`, `/서울-블로그-체험단`, `/부산-카페-체험단`, `/뷰티-체험단-모집`, and `/오늘마감-블로그-체험단`.
- User completed Naver Search Advisor page collection requests for the seven new SEO landing URLs: `/레뷰-체험단`, `/미블-체험단`, `/강남-맛집-체험단`, `/서울-블로그-체험단`, `/부산-카페-체험단`, `/뷰티-체험단-모집`, and `/오늘마감-블로그-체험단`.
- Added `docs/crawler/new-source-intake.md` so the user can collect the minimum URLs, screenshots, login notes, and field examples needed before adding new crawler sources, delivery campaigns, or reporter campaigns.
- Received Ringble (`링블`) as a candidate visit campaign source and documented its listing URL, sample detail URLs, and pagination notes in `docs/crawler/ringble-intake.md`; it was initially listed as a candidate before implementation.
- Added Ringble follow-up intake: confirmed 2/3 page URLs, captured one detail field sample (`274969`), noted Ringble date/people/provision parsing hints, and left closed-campaign URL plus login/detail visibility as remaining checks.
- Implemented first Ringble (`ringble`) visit crawler: parses `category=832` list pages, `start=N` pagination, detail dates/counts/provision/location URL, and title region hints for geocoding. Updated crawler inventory and AGENTS active crawler count to 13.
- Added `qa:ringble` fixture for list parsing, `오늘 마감` D-day handling, short Korean date ranges, provision text, people counts, and Naver location URL extraction.
- Verification passed: `node --check scripts/crawler/crawl.cjs`, `node --check scripts/qa/ringble-fixture.cjs`, `npm.cmd run qa:ringble`, `npm.cmd run qa:crawler:active-selection`, and targeted `git diff --check`.
- Next crawler step: user should run limited crawl separately with `$env:CRAWL_ONLY="ringble"; npm.cmd run crawl` when ready, then inspect `public/campaigns.json` Ringble count/fields before any full crawl or deployment.
- Added Dinnerqueen delivery list support: `crawlDinnerqueen()` now also requests `ct=배송`, preserves `delivery` campaign type in crawler artifacts/DB mapping, parses delivery card title/image/D-day/apply/selected counts, and keeps duplicate IDs from double-counting when all and delivery lists overlap.
- Added `qa:dinnerqueen:delivery` fixture using the provided delivery card HTML. Verification passed: `node --check scripts/crawler/crawl.cjs`, `node --check scripts/qa/dinnerqueen-delivery-fixture.cjs`, `npm.cmd run qa:dinnerqueen:delivery`, `npm.cmd run qa:dinnerqueen:detail-targets`, `npm.cmd run qa:dinnerqueen:provision`, `npm.cmd run qa:ringble`, and `npm.cmd run qa:crawler:active-selection`.
- Next Dinnerqueen check: after the current Ringble crawl finishes, run a limited Dinnerqueen crawl separately with `$env:CRAWL_ONLY="dinner"; npm.cmd run crawl`, then inspect `public/campaigns.json` for `platformId="dinner"` and `type="delivery"` rows before any full crawl/deploy.
- Ringble limited crawl completed with 237 fresh campaigns and quality gate `passed_with_warnings`; Supabase sync failed only because the project is still restricted by `exceed_egress_quota`. Found 33 Ringble `point` rows polluted by full detail text (`모집 기간`, `리뷰어 신청하기`) and tightened the provision filter. Re-run `CRAWL_ONLY=ringble` before committing/publishing the snapshot.
- Added `DINNERQUEEN_LIST_SCOPE=delivery` so Dinnerqueen can be tested with shipping-only pages while the default operational Dinnerqueen crawl remains all+delivery. Use it with `CRAWL_ONLY=dinner` for the next limited delivery verification.
- Dinnerqueen delivery crawl follow-up: user confirmed the real delivery campaign count is much higher than 47. Current check only collected 30 initial `ct=배송` cards plus 17 `page=2` cards. Next session must inspect the live browser/network pagination and filters (`page` vs `lpage`, `sns[]`, `order`, `ctype`, `area1/area2`, possible hidden/closed/open states) before treating `DINNERQUEEN_LIST_SCOPE=delivery` as valid.

### End-of-day handoff
- Changed today: added `docs/crawler/new-source-intake.md`, implemented first Ringble crawler/QA, documented Ringble intake, added Dinnerqueen delivery list parsing/scope QA, and tightened Ringble provision filtering after polluted `point` rows were found.
- Verified: `node --check scripts/crawler/crawl.cjs`, `node --check scripts/qa/ringble-fixture.cjs`, `node --check scripts/qa/dinnerqueen-delivery-fixture.cjs`, `npm.cmd run qa:ringble`, `npm.cmd run qa:dinnerqueen:delivery`, `npm.cmd run qa:dinnerqueen:detail-targets`, `npm.cmd run qa:dinnerqueen:provision`, `npm.cmd run qa:crawler:active-selection`, and targeted `git diff --check`. User-run Ringble crawl returned 237 campaigns but needs rerun after the `point` filter fix; Supabase sync remains blocked by `exceed_egress_quota`.
- Next session: first fix Dinnerqueen delivery count mismatch (`47` is known undercount), then rerun limited Ringble crawl, inspect artifacts, and only then select files for commit. Google quota-blocked URL indexing and Supabase Dinnerqueen `reward_text` sync remain follow-up tasks.

### Next
- After DNS setup, recheck `/`, `/app`, `/체험단`, `/서울-맛집-체험단`, `/디너의여왕-체험단`, `/sitemap.xml`, `/robots.txt`, and `www` redirect.
- Register or otherwise acquire `cheheommoa.com` before DNS setup; Vercel currently reports it as available.
- Retry Google Search Console URL inspection/indexing requests tomorrow for `/체험단`, `/서울-맛집-체험단`, `/오늘마감-체험단`, and `/디너의여왕-체험단`; if quota remains, request indexing for the seven new SEO landing URLs too.
- After Google/Naver have crawled the submitted URLs, review actual search queries and impressions before adding more landing pages.
- After Supabase quota is cleared, rerun `DINNERQUEEN_PROVISION_BACKFILL_LIMIT=0 npm.cmd run crawl:dinnerqueen:provision-backfill -- --sync-existing-public --sync-supabase`.
- Fix Dinnerqueen delivery count mismatch before any delivery snapshot publish: reproduce the site's actual scrolling/network requests, update the crawler pagination/filter params, then rerun only `CRAWL_ONLY=dinner` + `DINNERQUEEN_LIST_SCOPE=delivery` and compare the count with the site.

## 2026-05-27

### Next SEO SSG 전환
- Next.js App Router 기반 SSG SEO 전환을 로컬 구현했다. `/`, `/app`, `/robots.txt`, `/sitemap.xml`, `/[slug]` 10개 랜딩 페이지가 정적 생성된다.
- 공식 canonical 도메인은 `https://cheheommoa.com`이다. sitemap에는 `/체험단`, `/블로그체험단`, `/인스타체험단`, `/맛집체험단`, `/카페체험단`, `/뷰티체험단`, `/서울-맛집-체험단`, `/부산-맛집-체험단`, `/오늘마감-체험단`, `/디너의여왕-체험단`이 포함된다.
- 기존 SPA 앱은 `/app` 아래 client-only route로 유지하고, 기존 `src/pages/*.jsx` 화면 파일은 Next Pages Router 충돌을 피하려고 `src/screens/*.jsx`로 이동했다.
- `.next`는 Next 빌드 산출물이므로 `.gitignore`에 추가했다.
- 검증: `npm.cmd run qa:public-env`, `npm.cmd run qa:seo:landing`, `npm.cmd run build`, `git diff --check` 통과. sitemap/robots 산출물에서 `cheheommoa.com` URL 확인.
- production deploy 완료: `dpl_CvRNXFTgc2t1k6K7CAG9Hx85qQHu`, production alias `https://camp-platform-liart.vercel.app`.
- 첫 배포 시 Vercel 프로젝트 Output Directory가 Vite 시절 `dist`로 남아 실패했다. `vercel.json`에 `framework: "nextjs"`와 `outputDirectory: null`을 명시해 Next.js auto output으로 재배포 성공했다.
- 아직 commit은 하지 않았다. 커밋 전 `AI identity prompt.md`, 런타임/크롤 산출물, 무관 dirty 파일은 제외하고 관련 파일만 선별한다.

### 다음 CLI 우선순위
- Vercel Dashboard에서 `cheheommoa.com`과 `www.cheheommoa.com`이 최신 production 배포 `dpl_CvRNXFTgc2t1k6K7CAG9Hx85qQHu`를 보고 있는지 확인한다.
- 운영 URL `/`, `/app`, `/체험단`, `/서울-맛집-체험단`, `/디너의여왕-체험단`, `/sitemap.xml`, `/robots.txt`를 확인하고 Google Search Console/Naver Search Advisor에 sitemap과 주요 URL을 제출한다.
- Supabase quota 리셋 또는 Pro 전환 후 `DINNERQUEEN_PROVISION_BACKFILL_LIMIT=0 npm.cmd run crawl:dinnerqueen:provision-backfill -- --sync-existing-public --sync-supabase`를 재실행해 DB `campaigns.reward_text`를 맞춘다.
- DB 동기화 후 운영 사이트에서 Dinnerqueen 카드/상세의 제공내역 노출을 다시 확인한다.
- 커밋 전 `AI identity prompt.md`, 런타임/크롤 산출물, 무관 dirty 파일을 제외하고 Next SEO 전환 관련 파일만 선별한다.

### 변경사항

- 출시 준비 점검: `npm audit fix`로 `@supabase/realtime-js` 경유 `ws` moderate 취약점을 lockfile에서 해소했다.
- Supabase egress 절감을 위해 프론트 캠페인 목록은 기본적으로 `/campaigns.json` 정적 snapshot을 사용하게 하고, `VITE_CAMPAIGN_DB_REFRESH_ENABLED=1`일 때만 Supabase 캠페인 전체 조회/주기 refresh를 켜도록 했다.
- 최신 순차 크롤 결과를 반영했다. `public/campaigns.json` 기준 전체 16,775건, Dinnerqueen 3,418건이다.
- 크롤 직후 Dinnerqueen `point`가 2,163/3,418건만 채워져 있어, 사용자 승인 후 `DINNERQUEEN_PROVISION_BACKFILL_LIMIT=0 npm.cmd run crawl:dinnerqueen:provision-backfill -- --write-public`로 나머지 1,255건을 public snapshot에 반영했다.
- Vercel production 배포 완료: `dpl_2URUuaHbZJsq8SWVAGZgc32xyCtG`, alias `https://camp-platform-liart.vercel.app`.
- Supabase egress 절감 변경 반영을 위해 Vercel production 추가 배포 완료: `dpl_5zpWoRaTz4BYSMjtGW3TdJMf4irg`, alias `https://camp-platform-liart.vercel.app`.
- 향후 마케팅 작업을 분리 관리하기 위해 `marketing/README.md`를 추가하고, 출시 포지셔닝/리스크/홍보 채널 초안을 정리했다.
- 공식 SEO 도메인을 `https://cheheommoa.com`으로 정하고, Next.js App Router + SSG 기반 SEO 랜딩 전환 설계를 `docs/superpowers/specs/2026-05-27-nextjs-seo-ssg-design.md`에 정리했다.
- Next.js SEO SSG 전환 구현 계획을 `docs/superpowers/plans/2026-05-27-nextjs-seo-ssg.md`에 작성했다.
- 루트 정리: 참조되지 않는 일회성 `CLI_NEXT_SESSION_PROMPT.md`, 오래된 단독 `supabase_ads_schema.sql`, 루트 dev/test `*.log` 산출물을 삭제했다.
- `supabase_ads_schema.sql`은 `database/supabase/migrations/20260512_ad_events*.sql`로 대체된 오래된 DDL이라 커밋 후보에서 제외했다.
- `CLI_NEXT_SESSION_PROMPT.md`는 work-log/AGENTS 인수인계와 중복되는 임시 파일이라 삭제하고 `.gitignore`에 추가했다.

### 검증

- `npm.cmd audit --audit-level=moderate` 결과 `found 0 vulnerabilities`.
- `npm.cmd run qa:campaigns:source-policy`, `npm.cmd run qa:campaigns:point-merge` 통과.
- Supabase egress 절감 배포 전 `npm.cmd run build` 통과, Vercel build도 `found 0 vulnerabilities` 및 `readyState=READY`로 완료.
- Next.js SEO SSG 계획 문서의 placeholder/TODO scan과 `git diff --check`를 통과했다.
- `robots.txt`, `sitemap.xml` 로컬/운영 URL 확인. 둘 다 `https://camp-platform-liart.vercel.app` 기준 정상 응답.
- `npm.cmd run build` 통과.
- `npm.cmd run crawl:check` 결과는 `WARN`, critical 없음. 경고는 좌표 완성도와 hidden duplicate 관련이며 publish gate는 `passed_with_warnings`다.
- 운영 alias `/campaigns.json` 확인: `updatedAt=2026-05-27T03:39:15.089Z`, 전체 16,775건, Dinnerqueen `point` 3,418/3,418건.
- Supabase sync는 무료 quota 제한으로 `exceed_egress_quota` 실패가 유지되어 DB `reward_text` 동기화는 보류했다.
- 정리 전 `rg`로 `CLI_NEXT_SESSION_PROMPT.md`, `supabase_ads_schema.sql`, 루트 dev/test 로그 참조 여부를 확인했고 코드 참조는 없었다.
- `supabase_ads_schema.sql`은 기존 Supabase migration과 비교해 오래된 중복 DDL임을 확인했다.

### 다음 세션에서 이어갈 작업

1. Supabase quota 리셋 또는 Pro 전환 후 `DINNERQUEEN_PROVISION_BACKFILL_LIMIT=0 npm.cmd run crawl:dinnerqueen:provision-backfill -- --sync-existing-public --sync-supabase`를 재실행해 DB `campaigns.reward_text`를 맞춘다.
2. DB 동기화 후 운영 사이트에서 Dinnerqueen 카드/상세의 제공내역 노출을 다시 확인한다.
3. 커밋 전 `AI identity prompt.md`와 무관한 dirty/runtime 산출물을 제외하고 관련 파일만 선별한다.
4. Next.js SEO SSG 전환은 `docs/superpowers/plans/2026-05-27-nextjs-seo-ssg.md`를 기준으로 구현한다.
5. 마케팅 작업은 `marketing/`에서 이어가고, 초기 베타 홍보 문구/채널별 실험 기록부터 정리한다.

## 2026-05-26

### 변경사항

- `reviewnote`는 기본 전체 크롤 대상에서 제외하고, 명시적 `CRAWL_ONLY=reviewnote`일 때만 선택되게 했다.
- 품질 게이트와 `crawl:check`를 보강해 실패 플랫폼의 이전 데이터가 0건인데 publish 가능한 상태로 남는 문제를 막았다.
- 분석 이벤트 redaction, opt-out, 이벤트 카탈로그, dashboard, 시장 리포트/감사 metadata QA를 추가했다.
- 디너의여왕 상세 보강 대상 정렬을 수정해 `point`가 비어 있는 공개 가능 캠페인을 마감 캠페인보다 먼저 처리하게 했다.
- 디너의여왕 backfill을 보강하고 승인된 배치로 `public/campaigns.json`의 Dinnerqueen `point` 3,616/3,616건을 채웠다.
- 자동 크롤이 다시 돌아도 새 Dinnerqueen 결과의 `point`가 비어 있으면 이전 public snapshot의 값을 이어받게 했다.
- Supabase quota 제한으로 DB upsert가 실패해, 운영 화면에서 DB 결과의 빈 Dinnerqueen `point`를 배포된 `/campaigns.json` 값으로 병합하는 fallback을 추가했다.
- Vercel production 배포 완료: `dpl_8D1F1L9WhvTyVFbrkP583sQPh3Rc`, alias `https://camp-platform-liart.vercel.app`.

### 검증

- 통과: `qa:quality-gate`, `qa:crawl-check:quality-gate`, `qa:crawler:active-selection`.
- 통과: `qa:analytics:privacy`, `qa:analytics:market-report`, `qa:analytics:market-audit`, `qa:analytics:events`, `qa:analytics:dashboard`.
- 통과: `qa:dinnerqueen:backfill-plan`, `qa:dinnerqueen:provision`, `qa:dinnerqueen:detail-targets`, `qa:dinnerqueen:point-preserve`, `qa:campaigns:point-merge`.
- 통과: 관련 `node --check`, 관련 `eslint`, `npm.cmd run build`, `vercel.cmd --prod --yes`, `git diff --check`.
- 확인: `crawl:dinnerqueen:provision-backfill -- --plan-only` 기준 Dinnerqueen `pointFilled=3616`, `pointEmpty=0`.
- 실패/보류: `--sync-existing-public --sync-supabase`는 Supabase `exceed_egress_quota` 제한으로 실패. DB `reward_text`는 quota 해소 후 재시도 필요.
- 참고: `npm.cmd run crawl:check`는 기존 dirty 산출물 기준 `reviewnote` 403 관련 FAIL이 남아 있다.

### 다음 세션에서 이어갈 작업

1. Supabase Dashboard에서 `exceed_egress_quota`/project restricted 상태를 해소한다.
2. 제한 해소 후 `DINNERQUEEN_PROVISION_BACKFILL_LIMIT=0 npm.cmd run crawl:dinnerqueen:provision-backfill -- --sync-existing-public --sync-supabase`를 재실행해 DB `campaigns.reward_text`를 맞춘다.
3. DB 동기화 후 운영 사이트에서 Dinnerqueen 카드/상세의 제공내역 노출을 확인한다.
4. 필요 시 `npm.cmd run crawl:check`를 최신 산출물 기준으로 다시 실행해 `reviewnote` 403 잔여 상태를 분리 확인한다.
5. 커밋 전 `AI identity prompt.md` 등 관련 없는 dirty 파일과 runtime JSON 변경 범위를 선별한다.
## 2026-05-15

### 변경사항

- 유튜브 채널 연동 v1 설계 문서와 단계별 실행 계획을 `docs/superpowers/` 아래에 추가했다.
- 유튜브 채널 URL/@핸들 파서, 공개 지표 병합 유틸, mock 기반 `qa:youtube:social` fixture를 추가했다.
- 유튜브 서버 helper와 `/api/social/youtube-sync` 엔드포인트를 추가했다. 로그인 access token을 Supabase service role로 검증하고, YouTube Data API 결과를 `social_connections`/`social_metrics`와 `profiles.youtube_*` 백업 필드에 반영하는 구조다.
- 운영 DB 적용용 `20260515_social_connections.sql` migration과 schema 기준을 추가했고, Supabase `camp-platform` 운영 DB에 `social_connections` migration으로 적용했다. 메타데이터 검증에서 `social_connections` 13컬럼/RLS on, `social_metrics` 9컬럼/RLS on, 각 테이블 constraint 7개와 정책 5개를 확인했다.
- 마이페이지 유튜브 영역에 연동 확인/다시 동기화 버튼, 연동 상태, API/수동 출처 지표 표시를 추가했다. 네이버/인스타그램 자동 연동은 아직 구현하지 않았다.
- Vercel Production env에 `SUPABASE_SERVICE_ROLE_KEY`와 `YOUTUBE_API_KEY`를 등록했다. 루트의 `AI identity prompt.md`는 배포 소스에서 제외하도록 `.vercelignore`에 추가했다.
- Vercel Production 배포를 진행했다. 배포 ID는 `dpl_B8qb1MBUpx7So5SVCYhf4HziqpPA`이고, alias는 `https://camp-platform-liart.vercel.app`로 반영됐다.
- `qa:auth`를 최신 마이페이지 UI와 카드 UX에 맞춰 보강했다. 블로그 주소/네이버 지표/인스타그램/유튜브 수동 백업/신청 멘트 저장을 채우고, `QA_YOUTUBE_SYNC_URL`이 있을 때만 유튜브 API 동기화 버튼까지 확인한다.
- 운영 `/api/social/youtube-sync`는 비로그인 POST 요청에서 `401 Login is required`를 반환해 인증 없이 YouTube API나 DB 쓰기로 넘어가지 않는 것을 확인했다. 실제 로그인 QA는 `QA_EMAIL`/`QA_PASSWORD` env가 없어 아직 실행하지 않았다.
- `qa:auth` 신청 확인을 최신 운영 UI에 맞춰 다시 보강했다. 지원 버튼 토스트 한 문구에 의존하지 않고 상세 모달 닫힘과 현황 탭의 실제 신청 상태를 확인하며, 실패 진단에는 QA 계정 이메일을 마스킹한다.
- 인계된 데이터 수익화 보강 순서 중 `campaign_impression` 노출 이벤트를 추가했다.
- 캠페인 카드는 IntersectionObserver로 실제 화면 진입 시 1회만 노출을 보고하고, `App`에서 `page/section/campaign_id` 기준 세션 중복 제한과 최대 160건 제한을 둔다.
- 홈 섹션과 탐색 결과 목록에서 노출 컨텍스트(`page`, `section`, `position`, `resultCount`, `sortBy`, `preset`)를 전달한다.
- `analytics_events` allowlist를 프론트, schema, 기존 migration에 반영하고, 운영 DB 적용용 `20260515_analytics_campaign_impression.sql` migration을 추가했다.
- 사용자가 운영 DB에 `20260515_analytics_campaign_impression.sql` 적용을 완료했고, Supabase 단일 확인 요청으로 `campaign_impression` 검증 이벤트 1건 insert와 24시간 count 1건을 확인했다.
- `application_status_update`, `application_memo_update`, `application_review_url_update` 이벤트를 추가했다. 메모 원문과 리뷰 URL 원문은 저장하지 않고 길이/존재 여부와 상태 변경값만 metadata에 남긴다.
- 운영 DB 적용용 `20260515_analytics_application_activity.sql` migration을 추가했다.
- 사용자가 Supabase 플러그인 사용을 승인했고, `analytics_application_activity` migration을 운영 DB에 적용했다. 세 application 이벤트 타입은 rollback 트랜잭션 insert 검증을 통과해 검증 데이터가 남지 않았다.
- `map_filter`, `map_pin_open`, `map_cluster_interaction` 이벤트를 추가했다. 지도 필터 변경, 클러스터 확대, 지도 핀/사이드 목록 선택을 집계하되 좌표나 원문은 metadata에 저장하지 않는다.
- 운영 DB 적용용 `20260515_analytics_map_activity.sql` migration을 추가했다.
- 사용자가 지도 이벤트 migration 적용을 승인했고, `analytics_map_activity` migration을 운영 DB에 적용했다. 세 지도 이벤트 타입은 rollback 트랜잭션 insert 검증을 통과해 검증 데이터가 남지 않았다.
- `traffic_source` 이벤트를 추가했다. 첫 세션 진입 1회만 UTM 계열 파라미터와 외부 referrer host를 저장하고, 검색어 원문/referrer 전체 URL은 저장하지 않는다.
- 운영 DB 적용용 `20260515_analytics_traffic_source.sql` migration을 추가했다.
- 사용자가 UTM/referrer migration 적용을 승인했고, `analytics_traffic_source` migration을 운영 DB에 적용했다. `traffic_source`는 rollback 트랜잭션 insert 검증을 통과해 검증 데이터가 남지 않았다.
- `market_report_create`, `market_report_download` 감사 이벤트를 추가했다. 리포트 생성/CSV 다운로드 시 report id, 상태, 항목 수, 표본 기준 같은 운영 감사 수치만 metadata에 남긴다.
- 운영 DB 적용용 `20260515_analytics_market_report_audit.sql` migration을 추가하고, 사용자 승인 후 운영 DB에 적용했다. 두 감사 이벤트 타입은 rollback 트랜잭션 insert 검증을 통과했다.
- Vercel Production 배포를 진행했다. 배포 ID는 `dpl_frLzGbiH8P1kXDiodQrem19hxLWc`이고, alias는 `https://camp-platform-liart.vercel.app`로 반영됐다.
- 운영 URL에서 agent-browser로 익명 분석 이벤트 적재를 확인했다. QA 익명 ID 기준 `traffic_source` 1건, `campaign_impression` 2건, `map_filter` 2건, `map_cluster_interaction` 3건, `tab_view` 2건이 Supabase에 적재됐다.
- 지도 SDK는 운영 URL에서 정상 로드됐고, 확대 전에는 `확대 필요`로 핀을 숨기며 확대 후 클러스터 클릭 이벤트가 적재됐다.
- 추가 익명 QA에서 `패션 > 서울 > 성북` 조합으로 정확 위치 핀 2개를 표시한 뒤 사이드 목록 항목을 선택했고, QA 익명 ID 기준 `map_pin_open` 1건이 Supabase에 적재됐다. 확인 후 agent-browser 세션은 닫았다.
- 로그인 QA 세션에서 현황 상태/메모/리뷰 URL 수정과 시장 리포트 생성 이벤트의 실제 UI 적재를 확인했다. QA 익명 ID 기준 `application_status_update`, `application_memo_update`, `application_review_url_update`, `market_report_create`가 각각 1건씩 Supabase에 적재됐다.
- 별도 로그인 QA 세션에서 운영 탭 `CSV 다운로드` 버튼 클릭을 확인했고, QA 익명 ID 기준 `market_report_download` 1건이 Supabase에 적재됐다. 확인 후 agent-browser 세션은 닫았다.
- 분석 이벤트/시장 리포트 변경을 `cd3d232 Add analytics event tracking and market reports` 커밋으로 저장했다.
- 이후 사용자가 최신 크롤 완료를 확인했다. 로컬 산출물 기준 크롤은 `completed_with_errors`, quality gate는 `passed_with_warnings`, `canPublish=true`이며, 12개 플랫폼 중 11개가 성공했다.
- `reviewnote`는 쿠키 갱신 문제가 아니라 IP 차단으로 접근이 막힌 상태라고 사용자 확인을 받았다. 최신 산출물에서도 `Request failed with status code 403`으로 실패했고, 이전 캠페인 2,893건 보존 경로가 동작했다.
- 사용자가 현재부터 7일 동안 reviewnote 크롤을 돌리지 말고 2026-05-22 이후 다시 확인하기로 결정했다. `.cache/reviewnote-forbidden-cooldown.json`을 2026-05-22T02:42:10.473Z까지 연장해 전체 크롤 중에도 reviewnote 네트워크 요청을 skip하게 했다.
- 출시 전 남은 dirty 변경을 광고/수익화, PWA/오프라인, 로그인 QA, 프로필/법적 문구, reviewnote cooldown, 문서로 분류했다. `AI identity prompt.md`는 런타임과 무관한 별도 작업물이라 출시 후보에서 제외한다.
- production DB에서 `ad_events`, `profiles.blog_url`, `applications.campaign_url`, `applications.review_url`, `get_ad_event_summary` 존재를 읽기 전용 쿼리로 확인했다.
- 출시 후보 변경을 `07c5135 Prepare release QA ads PWA and profile polish` 커밋으로 저장하고, 사용자 승인 후 Vercel Production 배포를 진행했다. 배포 ID는 `dpl_3Gs9FGnrxVAKRXcj4kCv7XDdDa9T`이고 alias는 `https://camp-platform-liart.vercel.app`로 반영됐다.
- 미블(`mrblog`) 상세 HTML에서 혜택 카드가 비는 문제를 확인했다. 미블은 `체험 상품` 라벨을 쓰므로 상세 보강 단계에서 해당 `info_row`/`dt`/`dd .c_blue` 구조를 읽어 `campaign.point`에 저장하게 했다.
- 크롤러 헬퍼를 실제 크롤 없이 검증할 수 있도록 `CRAWLER_TEST_EXPORTS=1` export guard와 `qa:mrblog:provision` fixture QA를 추가했다.
- 디너의여왕(`dinner`) 상세 HTML에서 혜택 카드가 비는 문제를 보강했다. 디너의여왕은 `제공 내역` 라벨 주변과 `p.qz-body-kr... strong.w-600` 구조를 읽어 `campaign.point`에 저장하게 했다.
- `qa:dinnerqueen:provision` fixture QA를 추가해 사용자가 준 디너의여왕 HTML 2개에서 제공 내역 텍스트가 추출되는지 검증했다.
- 디너의여왕 실제 상세 구조인 `.qz-collapse` 블록 안의 `제공 내역` 라벨과 `.qz-collapse__content` 첫 제공 문단을 우선 읽도록 보강했다. 다른 `strong.w-600` 안내 문구가 먼저 있어도 제공 내역을 선택하게 fixture를 추가했다.
- 디너의여왕 최신 public snapshot은 `point`가 0/3,148건인 것을 확인했다. 실제 상세 1건과 새 dry-run에서는 제공내역이 추출되므로, 전체 크롤 재시도 대신 빈 `point`만 보강하는 `crawl:dinnerqueen:provision-backfill` 스크립트를 추가했다.
- 리뷰플레이스(`reviewplace`) 상세 HTML에서 혜택 카드가 비는 문제를 보강했다. 리뷰플레이스는 `제공내역` 라벨 주변과 `dd.bstyle` 제공내역 후보를 읽어 `campaign.point`에 저장하게 했다.
- `qa:reviewplace:provision` fixture QA를 추가해 사용자가 준 리뷰플레이스 HTML 2개에서 제공내역 텍스트가 추출되는지 검증했다.
- 강남맛집(`gangnam`) 상세 HTML에서 혜택 카드가 비는 문제를 보강했다. 강남맛집은 별도 라벨 대신 `p.sub_tit`의 업체 홈페이지 링크 텍스트에 체험권/이용권/상당 같은 제공내역 후보가 있으면 `campaign.point`에 저장하게 했다.
- `qa:gangnam:provision` fixture QA를 추가해 사용자가 준 강남맛집 HTML 2개에서 체험권 텍스트가 추출되는지 검증했다.
- 탐색 탭 무한 스크롤에서 일정 위치로 되돌아가는 현상을 보강했다. sentinel이 계속 intersecting 상태일 때 연속 로드가 반복되지 않도록 재진입 가드를 추가하고, sentinel을 scroll anchoring 기준점에서 제외했다.
- 캠페인 카드의 `자세히` 버튼을 제거하고 카드 액션 영역을 `저장`/`신청` 2버튼 구조로 정리했다. 카드 본문 클릭으로 상세 모달을 여는 기존 동작은 유지했다.
- 마이페이지에 채널 연동과 신청 멘트 관리를 추가했다. `profiles.blog_url`은 네이버 블로그 주소로 유지하고, 인스타그램/유튜브 URL, 네이버 이웃수/하루 방문자/총 방문자, 인스타 팔로워, 유튜브 구독자, 신청 멘트 템플릿을 저장하는 구조다.
- 지원 버튼 클릭 시 저장된 신청 멘트가 있으면 클립보드에 자동 복사한 뒤 원문 지원 페이지로 이동하도록 했다. 외부 플랫폼 API/OAuth 연동이나 자동 지표 수집은 추가하지 않았다.
- 운영 DB 적용용 `20260515_profiles_social_channels.sql` migration을 추가했고, Supabase `camp-platform` 운영 DB에 `profiles_social_channels` migration으로 적용했다.

### 검증

- `.\node_modules\.bin\eslint.cmd .\src\app\App.jsx .\src\pages\HomePage.jsx .\src\pages\ExplorePage.jsx .\src\features\campaigns\components\CampaignCard.jsx .\src\features\analytics\lib\analytics.js` 통과.
- `git diff --check` 관련 파일 기준 통과. Windows CRLF 변환 warning만 출력됐다.
- `.\node_modules\.bin\eslint.cmd .\src\pages\StatusPage.jsx .\src\features\analytics\lib\analytics.js` 통과.
- `npm.cmd run build` 통과.
- `.\node_modules\.bin\eslint.cmd .\src\pages\MapPage.jsx .\src\app\App.jsx .\src\features\analytics\lib\analytics.js` 통과.
- 지도 이벤트 추가 후 `npm.cmd run build` 통과.
- `.\node_modules\.bin\eslint.cmd .\src\app\App.jsx .\src\features\analytics\lib\analytics.js` 통과.
- UTM/referrer 이벤트 추가 후 `npm.cmd run build` 통과.
- `.\node_modules\.bin\eslint.cmd .\src\pages\OpsPage.jsx .\src\features\analytics\lib\analytics.js` 통과.
- market report audit 이벤트 추가 후 `npm.cmd run build` 통과.
- 배포 전 최종 `npm.cmd run lint`, `npm.cmd run build` 통과.
- `vercel.cmd --prod --yes` 통과. Vercel 빌드 로그에서 `found 0 vulnerabilities`, `vite v8.0.12` 빌드 완료, alias 반영을 확인했다.
- 운영 DB에는 `campaign_impression`, application activity, map activity, traffic source, market report audit migration을 적용했다. 크롤은 실행하지 않았다.
- `agent-browser` QA 세션은 `camp-platform-analytics-qa`로 사용했고 확인 후 닫았다.
- 로그인 QA 세션에서 `application_status_update`, `application_memo_update`, `application_review_url_update`, `market_report_create`, `market_report_download`의 실제 UI 이벤트 적재를 Supabase count로 확인했고, 확인 후 브라우저 세션을 닫았다.
- 추가 익명 QA 세션에서 `map_pin_open`의 실제 UI 이벤트 적재를 Supabase count로 확인했고, 확인 후 브라우저 세션을 닫았다.
- 최신 크롤 산출물 확인: `public/crawl-status.json`, `public/data-quality.json`에서 candidate 19,753건, fresh 22,991건, successful platform 11/12, failed platform `reviewnote` 1건을 확인했다. 추가 크롤이나 외부 호출은 실행하지 않았다.
- 출시 후보 전체 기준 `node --check scripts/crawler/crawl.cjs`, `node --check scripts/ads/sync-coupang-ads.cjs`, `node --check scripts/qa/smoke-ui.cjs`, `node --check scripts/qa/auth-flow.cjs` 통과.
- `public/ads.json`, `public/site.webmanifest` JSON parse 통과. 광고 후보는 65개이고 fallback 광고는 실제 제목/링크/이미지를 갖고 있다.
- 출시 후보 전체 기준 `npm.cmd run lint`, `npm.cmd run build`, `npm.cmd run qa:smoke` 통과. `qa:auth`는 실제 Supabase Auth 쓰기 흐름이라 테스트 계정 env 없이 실행하지 않았다.
- `vercel.cmd --prod --yes` 통과. Vercel 빌드 로그에서 `npm install`, `found 0 vulnerabilities`, `vite v8.0.12` 빌드 완료와 production alias 반영을 확인했다.
- 미블 혜택 추출 fixture 기준 `npm.cmd run qa:mrblog:provision`, `node --check scripts\crawler\crawl.cjs`, `node --check scripts\qa\mrblog-provision-fixture.cjs`, `npm.cmd run lint` 통과. 크롤은 실행하지 않았다.
- 디너의여왕 혜택 추출 fixture 기준 `npm.cmd run qa:dinnerqueen:provision`, `npm.cmd run qa:mrblog:provision`, `node --check scripts\crawler\crawl.cjs`, `node --check scripts\qa\dinnerqueen-provision-fixture.cjs`, `npm.cmd run lint`, `git diff --check` 통과. 크롤은 실행하지 않았다.
- 디너의여왕 `.qz-collapse` 제공 내역 우선 추출 보강 후 `npm.cmd run qa:dinnerqueen:provision`, `node --check scripts\crawler\crawl.cjs`, `npm.cmd run qa:mrblog:provision`, `npm.cmd run qa:reviewplace:provision`, `npm.cmd run qa:gangnam:provision`, `npm.cmd run lint`, `git diff --check` 통과. 크롤은 실행하지 않았다.
- 리뷰플레이스 혜택 추출 fixture 기준 `npm.cmd run qa:reviewplace:provision`, `npm.cmd run qa:dinnerqueen:provision`, `npm.cmd run qa:mrblog:provision`, `node --check scripts\crawler\crawl.cjs`, `npm.cmd run lint`, `git diff --check` 통과. 크롤은 실행하지 않았다.
- 강남맛집 혜택 추출 fixture 기준 `npm.cmd run qa:gangnam:provision`, `npm.cmd run qa:reviewplace:provision`, `npm.cmd run qa:dinnerqueen:provision`, `npm.cmd run qa:mrblog:provision`, `node --check scripts\crawler\crawl.cjs`, `npm.cmd run lint`, `git diff --check` 통과. 크롤은 실행하지 않았다.
- 탐색 무한 스크롤 보강 후 `.\node_modules\.bin\eslint.cmd .\src\pages\ExplorePage.jsx`, `npm.cmd run build`, `git diff --check -- src/pages/ExplorePage.jsx src/app/App.css` 통과.
- 카드 `자세히` 버튼 제거 후 `CampaignCard detail button removed` 검사, `.\node_modules\.bin\eslint.cmd .\src\features\campaigns\components\CampaignCard.jsx`, `npm.cmd run build`, `git diff --check -- src/features/campaigns/components/CampaignCard.jsx src/app/compact-ui.css` 통과.
- 마이페이지 채널/신청 멘트 추가 후 `npm.cmd run qa:profile`, `node --check scripts\qa\profile-fixture.cjs`, `git diff --check` 관련 파일 기준, `npm.cmd run lint`, `npm.cmd run build` 통과.
- `profiles_social_channels` 적용 후 운영 DB에서 새 `profiles` 컬럼 8개와 nonnegative 제약 5개를 확인했다.
- 운영 DB rollback 트랜잭션으로 채널 URL, 공개 지표, 신청 멘트 필드 update 검증이 `profile_social_fields_update_ok`로 통과했다.
- 이번 세션에서 `npm.cmd run qa:profile`, `npm.cmd run build` 통과. `qa:auth`는 `QA_EMAIL`/`QA_PASSWORD` env가 없어 실제 로그인 마이페이지 저장 QA를 실행하지 못했다.
- 유튜브 연동 배포 후 `node --check .\scripts\qa\auth-flow.cjs`, 운영 endpoint 비로그인 401 확인, `git diff --check -- .\scripts\qa\auth-flow.cjs` 통과.
- 실제 운영 URL 기준 `npm.cmd run qa:auth` 통과. 확인 범위는 로그인, 마이페이지 채널/지표/신청 멘트 저장, 유튜브 연동, 신청 기록, 현황 상태 변경, 메모/리뷰 URL 저장, 마이페이지 최근 활동 반영이다.
- QA 중 1회 Supabase `campaigns` 조회 500이 콘솔에 잡혔으나 동일 쿼리 직접 확인은 200이었고, 같은 QA 재실행은 통과했다. 크롤/배포/스케줄러는 추가 실행하지 않았다.
- 디너의여왕 backfill 추가 후 `node --check .\scripts\crawler\backfill-dinnerqueen-provisions.cjs`, `git diff --check -- .\scripts\crawler\backfill-dinnerqueen-provisions.cjs .\package.json` 통과. `DINNERQUEEN_PROVISION_BACKFILL_LIMIT=1` dry-run에서 1/1건 추출 성공했고 파일/DB 쓰기는 하지 않았다.

### 다음 세션에서 이어갈 작업

- 분석 이벤트 보강 작업은 배포/운영 DB 적용/실제 UI 적재 확인/커밋까지 완료됐다.
- 마이페이지 채널/신청 멘트 기능은 운영 DB migration 적용, 비영구 DB 저장 검증, 실제 로그인 QA까지 완료됐다.
- 이후 로그인 QA를 다시 돌릴 때는 `.env` 또는 현재 PowerShell 세션의 `QA_EMAIL`, `QA_PASSWORD`, `QA_BASE_URL`, `QA_YOUTUBE_SYNC_URL`을 사용한다. 값은 문서나 커밋에 남기지 않는다.
- `reviewnote`는 2026-05-22 11:42 KST 전까지 반복 제한 크롤 대상에서 제외한다. 일반 브라우저에서도 접근이 풀렸는지 확인되기 전에는 쿠키 교체만으로 해결된다고 가정하지 않는다.
- 다음 우선순위는 사용자가 별도 터미널에서 디너의여왕 혜택 backfill을 300건 단위로 실행하는 것이다. 기본은 dry-run이며 실제 반영은 `DINNERQUEEN_PROVISION_BACKFILL_WRITE_PUBLIC=1`, Supabase 반영은 `DINNERQUEEN_PROVISION_BACKFILL_SYNC_SUPABASE=1`을 명시한다.
- backfill 후 `public/campaigns.json`의 dinner `point` 채움률, `public/crawl-status.json`의 blocked 여부, Supabase `reward_text` 반영 여부를 확인한다. 현재 dirty `public/*.json`은 마지막 dinner 제한 크롤이 timeout/blocked였으므로 검증 전 커밋/배포하지 않는다.

## 2026-05-13

### 변경사항

- 컴퓨터가 오전 9시 전에 꺼져 있어 누락된 정기 크롤을 `npm run ops:crawl`로 수동 실행했다.
- 크롤 결과 `public/campaigns.json`, `public/crawl-status.json`, `public/data-quality.json`과 런타임 로그/캐시 산출물이 갱신됐다.
- 12개 플랫폼 중 11개가 성공했고 `reviewnote`는 좌표 급락으로 격리되어 이전 데이터 보존 경로가 동작했다.

### 검증

- 크롤 최종 상태는 `completed_with_errors`, quality gate는 `passed_with_warnings`, `canPublish=true`, Supabase sync는 `completed`다.
- 발행 후보/공개 캠페인 수는 20,711건이고, Supabase upsert는 30,606건 완료됐다.
- 실패 항목은 `reviewnote`: `quarantined: coordinates 6 is below minimum 30 from previous 154`.
- 이후 `CRAWL_ONLY=reviewnote` 제한 크롤을 실행했지만 첫 요청에서 `Request failed with status code 403`으로 즉시 실패했다. `public/campaigns.json`은 유지됐고 이전 리뷰노트 데이터 보존 경로가 동작했다.
- 리뷰노트 403이 반복 요청으로 이어지지 않도록 12시간 cooldown 상태 파일(`.cache/reviewnote-forbidden-cooldown.json`)을 추가하고, cooldown 중에는 네트워크 요청 없이 리뷰노트를 실패/보존 처리하도록 크롤러를 보강했다. `REVIEWNOTE_FORBIDDEN_COOLDOWN_HOURS`, `REVIEWNOTE_IGNORE_COOLDOWN` 예시 env와 `AGENTS.md` 운영 규칙도 추가했다.
- 배포 전 `npm.cmd run lint`, `npm.cmd run build`를 통과한 뒤 Vercel Production 배포를 진행했다. 새 배포는 `dpl_D5rHhXtfRWDDErzdrPgYRTa99Sbw`이고 alias는 `https://camp-platform-liart.vercel.app`로 반영됐다.
- 홈 카테고리 위 광고가 AdSense no-fill/차단 때 빈칸으로 보이는 문제를 수정했다. AdSense가 3.5초 안에 채워지지 않으면 기존 쿠팡/직접 광고 슬롯으로 fallback되게 했고, Production 재배포(`dpl_G5Lo7pcasGqJaUbzSDNnhHEFPNqo`)로 alias에 반영했다.
- fallback 쿠팡 광고가 같은 제품만 반복되지 않도록 광고 후보 풀을 65개로 확장했다. `home_top`, `explore_top`, `explore_inline`, `map_bottom` 슬롯별 16개 안팎의 후보와 `맛집/카페/뷰티/숙박/생활/서비스` 카테고리 후보를 생성했다.
- 광고 선택은 사용자 최근 카테고리/지역 신호를 브라우저 localStorage에만 저장해 다음 광고 선택에 반영하도록 바꿨다. 광고는 페이지 로드/컨텍스트 변경 시 선택되고, 화면을 보고 있는 중에는 자동 교체하지 않는다.
- Vercel Production 재배포(`dpl_AR9yyg7YvikgEVg7G6w9zLERx9vm`)로 확장된 `public/ads.json`과 맞춤 광고 선택 로직을 alias에 반영했다.
- 사용자 행동 분석 v1을 추가했다. `analytics_events` migration과 schema 기준을 만들고, 탭 보기, 홈 탐색 클릭, 탐색 필터, 캠페인 상세 열기, 즐겨찾기, 신청 버튼, legal 열기, 분석 수집 동의/거부 이벤트만 허용했다.
- 분석 이벤트는 검색어 원문을 저장하지 않고 사용 여부/길이만 저장한다. `page_path`의 `q` 값과 인증 hash 토큰도 마스킹하도록 했다.
- 홈/탐색 카드의 바로 신청 버튼도 `handleApply` 경로를 타게 연결해 신청 클릭 분석과 로그인 사용자 지원 현황 기록이 같은 흐름으로 처리되게 했다.
- 개인정보 처리방침에 행태정보 분석 항목과 분석 수집 켜기/끄기 토글을 추가하고, 법적 문서 갱신일을 `2026-05-13`으로 올렸다.
- 분석 집계 RPC는 일반 anon/auth 사용자에게 열지 않고 service role에서만 실행하도록 migration과 schema를 맞췄다. 운영 DB 적용은 아직 하지 않았다.
- 분석 이벤트 v1 프론트 변경을 Vercel Production에 배포했다. 새 배포는 `dpl_HSkApuNwGqWPQVqCA5PmChgDppRf`이고 alias는 `https://camp-platform-liart.vercel.app`로 반영됐다.
- 운영 탭에 사용자 행동 분석 요약판을 추가했다. 전체 이벤트, 고유 브라우저, 로그인 사용자, 상세 열기, 신청 버튼, 검색/필터 합계를 보고 행동 유형, 탭 사용, 인기 카테고리, 인기 지역, 로그인/비로그인, 신청 클릭 캠페인을 집계 테이블로 확인한다.
- 원본 이벤트를 브라우저에서 직접 읽지 않고 `get_analytics_dashboard_summary` aggregate-only RPC만 호출하도록 했다. 이 RPC는 authenticated 사용자에게만 grant하는 새 migration `20260513_analytics_dashboard_summary.sql`로 분리했다.
- 운영 탭 분석 요약판을 Vercel Production에 배포했다. 새 배포는 `dpl_3fCWpGQqTWqkZqRZxEMXopm5567L`이고 alias는 `https://camp-platform-liart.vercel.app`로 반영됐다.
- 향후 정보 판매/제공은 개인별 행동 원본이 아니라 카테고리/지역/플랫폼/기간 단위 집계 리포트로만 다루기로 했다. `user_id`, `anonymous_id`, `session_id`, 원본 경로, 개별 사용자 여정은 외부 제공 대상에서 제외한다.
- 판매/제공용 첫 시장 리포트 RPC `get_analytics_market_report` migration을 추가했다. 기본값은 최근 30일, 최소 이벤트 20건, 최소 고유 브라우저 5개이고 SQL 내부에서 최소 이벤트 10건/고유 브라우저 5개 미만 segment는 억제한다.
- `docs/product/analytics-market-report.md`를 추가해 허용 리포트 단위, 금지 데이터, 최소 표본 기준, 상품화 운영 규칙을 문서화했다.
- 운영 탭에 판매용 리포트 준비 상태 패널을 추가했다. 현재 이벤트/고유 브라우저 수, 부족 표본, 생성 가능 집계 항목, 기준을 넘은 후보 항목을 `get_analytics_dashboard_summary` 집계값으로만 표시한다.
- 준비 상태 패널은 운영자가 보는 표본 충족 안내용이며, 실제 외부 제공/판매용 추출 기준은 service role 전용 `get_analytics_market_report` RPC와 `docs/product/analytics-market-report.md`를 따른다.
- 판매용 리포트 준비 상태 패널을 Vercel Production에 배포했다. 새 배포는 `dpl_5ehBmWmCyojBype5vaWADX6fZezY`이고 alias는 `https://camp-platform-liart.vercel.app`로 반영됐다.
- 저장형 시장 리포트 archive migration을 추가했다. `analytics_report_admins` allowlist, `analytics_market_reports`, `analytics_market_report_items`, 생성/목록/항목 조회 RPC를 만들고 원본 이벤트 row나 사용자/세션 식별자는 저장하지 않는다.
- 운영 탭에 저장된 시장 리포트 목록, 집계 항목 미리보기, CSV 다운로드, 새 리포트 생성 버튼을 추가했다. 생성/조회는 `analytics_report_admins`에 등록된 로그인 사용자만 성공한다.
- 저장형 시장 리포트 UI를 Vercel Production에 배포했다. 새 배포는 `dpl_CoPwhCACmR9m58B7jdxkRdCpgLtX`이고 alias는 `https://camp-platform-liart.vercel.app`로 반영됐다.
- 저장형 시장 리포트가 `표본 부족` 상태라 저장 항목이 0개여도 선택된 리포트의 메타데이터/헤더 CSV를 다운로드할 수 있게 했다.
- 사용자 확인: Supabase `analytics_report_admins`에 오너 Auth user ID를 등록했고, 운영 홈페이지에서 관리자 리포트 화면 접근을 확인했다.
- 코드 변경 없이 데이터 수익화 관점 분석을 진행했다. 현재 수집 축은 `analytics_events`, `ad_events`, `profiles/favorites/applications`이고, 다음 보강 우선순위는 캠페인 노출, 지원 상태 변경, 지도 행동, 유입 source, 리포트 감사 로그다.

### 다음 세션에서 이어갈 작업

- `reviewnote`는 새 브라우저 세션 쿠키를 `.env`의 `REVIEWNOTE_COOKIE`에 갱신한 뒤 제한 크롤을 다시 실행한다. 현재 실패는 동시성보다 쿠키/세션 403 문제로 본다.
- 리뷰노트 사이트가 일반 브라우저에서도 403이면 cooldown이 끝날 때까지 재시도하지 않는다. 수동 재확인이 필요하면 `REVIEWNOTE_IGNORE_COOLDOWN=1`을 임시로 사용한다.
- 배포 전에는 `npm.cmd run lint`, `npm.cmd run build`, 필요 시 QA 명령을 다시 확인한다.
- 운영 탭 리포트 준비 상태 패널 추가 후 `.\node_modules\.bin\eslint.cmd .\src\pages\OpsPage.jsx`, `git diff --check`, `npm.cmd run lint`, `npm.cmd run build`를 통과했다.
- 배포 후 `curl.exe -I -L https://camp-platform-liart.vercel.app/?ops=1`와 새 `OpsPage-D9iAGmPE.js` asset 응답이 모두 `200 OK`인 것을 확인했다.
- 저장형 시장 리포트 UI 추가 후 `.\node_modules\.bin\eslint.cmd .\src\features\analytics\lib\analytics.js .\src\pages\OpsPage.jsx`, `git diff --check`, `npm.cmd run lint`, `npm.cmd run build`를 통과했다.
- 배포 후 `curl.exe -I -L https://camp-platform-liart.vercel.app/?ops=1`와 새 `OpsPage-0CeY2oSc.js` asset 응답이 모두 `200 OK`인 것을 확인했다.
- 표본 부족 CSV 다운로드 조건 수정 후 `.\node_modules\.bin\eslint.cmd .\src\pages\OpsPage.jsx` 통과.
- 데이터 수익화 분석은 `src/features/analytics/lib/analytics.js`, `src/app/App.jsx`, `src/pages/ExplorePage.jsx`, `src/pages/MapPage.jsx`, `src/pages/StatusPage.jsx`, `src/pages/ProfilePage.jsx`, `database/supabase/migrations/20260513_analytics_*.sql`, `docs/product/analytics-market-report.md`를 확인했다. 코드 수정은 하지 않았다.
- 운영 탭 분석 요약판을 실제로 보려면 Supabase SQL Editor에서 `database/supabase/migrations/20260513_analytics_dashboard_summary.sql`을 적용하고, 로그인 상태로 `?ops=1` 운영 탭을 확인한다.
- 판매/제공용 데이터 리포트가 필요하면 원본 `analytics_events`가 아니라 표본 수 기준을 둔 별도 집계 export 또는 리포트 테이블을 만든다.
- 시장 리포트 RPC를 실제 운영 DB에 추가하려면 Supabase SQL Editor에서 `database/supabase/migrations/20260513_analytics_market_report.sql`을 적용한다. 현재 이벤트 수가 적으면 기본 threshold 때문에 결과가 비어 있는 것이 정상이다.
- 저장형 리포트 UI를 실제로 쓰려면 Supabase SQL Editor에서 `database/supabase/migrations/20260513_analytics_market_report_archive.sql`을 적용하고, 본인 Auth user ID를 `analytics_report_admins`에 추가한다.
- 다음 작업은 먼저 운영 DB에서 `analytics_events` 실제 적재를 확인한다. 그 다음 `campaign_impression` 노출 이벤트, `application_status_update`/메모/리뷰 URL 이벤트, 지도 필터/핀/클러스터 이벤트, UTM/referrer 유입 추적, 운영 리포트 RPC 관리자 제한, 리포트 생성/다운로드 감사 로그 순서로 진행한다.
- `표본 부족` CSV 다운로드 로컬 수정분은 운영 배포 전 `npm.cmd run lint`, `npm.cmd run build` 확인 후 사용자 승인으로 배포한다.

## 2026-05-12

### 변경사항

- 지도 첫 진입/넓은 배율에서는 캠페인 핀과 클러스터를 숨기고, 동네 단위로 확대됐을 때만 표시하도록 조정했다.
- Kakao 지도 축소 한계를 `level 11`로 제한하고, 넓은 배율에서는 확대 안내 오버레이를 표시했다.
- 홈 히어로에서 사용자에게 불필요한 `최근 확인 기준` 시간 지표를 제거했다.
- 탐색 카테고리를 상위 필터로 두고, 카테고리 선택 시 지역 후보/숫자가 현재 카테고리 기준으로 다시 계산되게 했다.
- 탐색 상태 요약에서도 사용자에게 불필요한 `최근 확인` 시간 지표를 제거했다.
- 지도 상단 상태 영역에서도 사용자에게 불필요한 `최근 확인 기준` 시간 지표를 제거했다.
- 광고 선택 로직에 슬롯/카테고리/지역/최근 노출 이력 기반 회전을 추가하고, 다음 Coupang 광고 동기화부터 슬롯당 후보가 여러 개 생성되도록 기본값을 조정했다.
- `VITE_ADSENSE_CLIENT` 기반 AdSense 자동 광고 스크립트 로더를 추가했다. 로컬 개발 환경에서는 기본 비활성화하고 배포 환경에서만 로드한다.
- 홈/탐색/지도 광고 위치에 수동 AdSense 광고 단위 컴포넌트를 연결했다. slot ID가 없거나 로컬 환경이면 기존 쿠팡/직접 광고로 fallback된다.
- AdSense 슬롯은 클릭 추적 없이 노출 이벤트만 기록하고, 운영 탭에서 브라우저 로컬 광고 이벤트 기준 슬롯별 노출/클릭/CTR을 볼 수 있게 했다.
- Supabase 장기 누적용 `ad_events` 테이블 migration을 추가했고, 사용자가 Supabase SQL Editor에서 적용 성공을 확인했다.
- 쿠팡 광고 동기화 스크립트에 카테고리별 키워드 매핑을 추가했다. 기본값은 탐색 중간 슬롯에서 `맛집/카페/뷰티/숙박/생활/서비스`별 후보를 생성한다.
- 운영 탭 광고 성과 영역을 Supabase 30일 집계 RPC 우선, 브라우저 로컬 이벤트 fallback 방식으로 확장했다. RPC migration은 파일만 추가했고 실제 DB 적용은 아직 필요하다.
- Vercel Production에 AdSense 환경변수 4개가 등록된 것을 확인했다. 사용자가 Supabase SQL Editor에서 `get_ad_event_summary` RPC를 적용했고, 호출 결과 `rpc_ok=true`, 현재 집계 row 0건을 확인했다.
- Production 배포를 진행했고 `https://camp-platform-liart.vercel.app` alias로 반영됐다. 이후 PWA 기본 보강으로 service worker, offline page, manifest 아이콘 항목을 추가해 재배포했다.
- 배포된 `/`, `/site.webmanifest`, `/sw.js`, `/offline.html`이 200으로 응답했고, manifest는 `display=standalone`, icon 2개, service worker는 offline fallback을 포함하는 것을 확인했다.
- 브랜드 표시명을 `CheheomMoa`로 정리하고, npm package slug를 `cheheommoa`, 출시 체크리스트의 Android 패키지명을 `com.cheheommoa.app`, 목표 커스텀 도메인을 `https://cheheommoa.com`으로 맞췄다.
- SEO/PWA 메타, sitemap/robots, 내부 광고 fallback 문구, Auth 문구, Coupang Sub ID 기본값을 새 브랜드 slug 기준으로 갱신했다. 기존 `cheommoa_*` localStorage 광고 이벤트는 새 key로 읽을 때 이전되게 했다.
- 사용자가 도메인 구매를 보류하기로 해서 공식 배포 URL은 현재 Vercel alias `https://camp-platform-liart.vercel.app`로 유지했다. canonical, og:url, sitemap, robots, env example, release checklist의 현재 운영 URL을 Vercel alias 기준으로 되돌렸다.
- Vercel Production env에 `VITE_PUBLIC_SITE_NAME=CheheomMoa`, `VITE_PUBLIC_OPERATOR_NAME=CheheomMoa`, `VITE_PUBLIC_SITE_URL=https://camp-platform-liart.vercel.app`를 맞추고 Production 배포를 진행했다. Alias는 `https://camp-platform-liart.vercel.app`로 반영됐다.
- `npm audit fix`로 보안 경고를 해소했다. lockfile 기준 `axios 1.16.0`, `vite 8.0.12`, `postcss 8.5.14`, `follow-redirects 1.16.0`, `brace-expansion 1.1.14`가 반영됐고 `npm audit` 결과 0 vulnerabilities를 확인했다.
- 보안 패치 lockfile로 Production 재배포를 진행했다. Vercel 빌드 로그에서 `found 0 vulnerabilities`와 `vite v8.0.12` 빌드를 확인했고, alias는 `https://camp-platform-liart.vercel.app`로 반영됐다.
- `agent-browser`는 도입하더라도 우리 배포/로컬 URL의 출시 QA 보조 도구로만 사용하기로 했다. 앱 기능, 크롤러 대체, 외부 사이트 자동 조작, 로그인 세션 수집, 대량 요청에는 쓰지 않는 조건을 `AGENTS.md` Safety Rules에 기록했다.
- `agent-browser 0.27.0`을 전역 QA 도구로 설치했고, 사용자 Chrome과 분리하기 위해 Chrome for Testing `148.0.7778.97`을 설치했다. 프로젝트 `package.json`에는 의존성을 추가하지 않았다.
- `agent-browser`를 `https://camp-platform-liart.vercel.app`에만 사용해 모바일 홈/지도 smoke QA를 수행했다. 허용 도메인을 Vercel alias, Supabase, Kakao/Daum 지도, 광고/Google asset 도메인으로 제한했고 console/errors는 비어 있음을 확인했다.
- 모바일 지도 QA에서 전국/서울 배율은 `확대 필요` 상태로 핀을 숨기고, 서울 강남 필터 후 확대하면 지도 핀/클러스터가 표시되는 것을 확인했다. 스크린샷은 `.cache/qa/agent-browser/` 아래에 저장했다.
- 같은 `agent-browser` 세션에 병렬 명령을 보내면 CDP channel이 닫힐 수 있어, 이후 운영은 실제 사용자 환경에서 순차 실행 기준으로 진행한다.
- 로그인 후 `현황` 탭을 1차 개선했다. 신청 클릭을 실제 지원완료로 단정하지 않고 `지원 페이지 열림`으로 기록하며, 현황에서 `지원완료/선정/리뷰 작성중/완료/미선정` 상태, 메모, 리뷰 URL을 관리할 수 있게 했다.
- `현황`에 오늘 볼 것, 다음 액션, 단계 진행 표시, 상태별 요약, 찜 목록 정리를 추가했다. `마이` 탭은 아직 건드리지 않았고 다음 우선순위로 남긴다.
- 로그인 후 `마이` 탭을 1차 개선했다. 계정 정보 저장, 프로필 완성도, 진행/선정/선정률 요약, 다음 할 일, 최근 활동, 서비스 범위 요약을 추가하고 현황/탐색/지도 바로가기를 연결했다.
- 출시 QA와 폴더 정리 기준을 `docs/release-qa-cleanup.md`에 정리했다. 실제 삭제/이동 없이 보존, 커밋 후보, 정리 후보, 주의 후보를 분류했다.
- 로그인 전 smoke QA 스크립트 `scripts/qa/smoke-ui.cjs`와 `npm run qa:smoke` 명령을 추가했다. 홈 렌더링, 현황/마이 로그인 보호, 개인정보/문의 라우트를 확인한다.
- 로그인 후 쓰기 QA용 `scripts/qa/auth-flow.cjs`와 `npm run qa:auth` 명령을 추가했다. 테스트 계정 env가 있을 때만 로그인, 프로필 저장, 지원 기록 생성, 현황 상태/메모 저장, 마이 최근 활동 반영을 확인한다.
- `qa:auth` 실패 원인을 쉽게 볼 수 있도록 현재 단계, URL, 화면 텍스트 일부, 로그인 실패 메시지 진단 출력을 보강했다.
- `qa:auth`가 프로필 저장 단계에서 멈출 때 원인을 좁힐 수 있도록 저장 버튼 상태, 입력값, Supabase 요청/응답 진단 출력을 추가했다.
- 프로필 저장 400 대응으로 `profiles` 저장 경로를 `upsert`에서 `update 후 없으면 insert` 방식으로 바꿨다. 회원가입 프로필 동기화도 같은 방식으로 맞췄고, 운영 DB 컬럼 누락 가능성에 대비해 `20260512_profiles_account_fields.sql` migration 파일을 추가했다. 실제 DB 적용은 아직 하지 않았다.
- 로그인 QA 결과 운영 Supabase `profiles` 저장은 `record "new" has no field "updated_at"`로 실패하는 것을 확인했다. `20260512_profiles_account_fields.sql`에 schema reload를 추가했고, `ad_events.id` 누락 방지를 위해 프론트 insert에 `id`를 포함하고 `20260512_ad_events_id_default.sql` migration 파일을 추가했다. 실제 DB 적용은 아직 하지 않았다.
- 로그인 QA에서 프로필 저장은 통과했고, 지원 기록 생성은 운영 Supabase `applications.d_day` 컬럼 누락으로 실패하는 것을 확인했다. `applications` 활동 필드 보강용 `20260512_applications_activity_fields.sql` migration 파일을 추가했다. 실제 DB 적용은 아직 하지 않았다.
- 사용자가 Supabase SQL Editor에서 `20260512_profiles_account_fields.sql`, `20260512_ad_events_id_default.sql`, 수정된 `20260512_applications_activity_fields.sql`을 적용했고, `qa:auth`가 로그인, 프로필 저장, 지원 기록 생성, 상태 변경, 메모/리뷰 URL 저장, 마이 최근 활동 반영까지 통과했다.

### 검증

- `npm.cmd run lint` 통과.
- `.\node_modules\.bin\eslint.cmd .\src\pages\HomePage.jsx` 통과.
- `.\node_modules\.bin\eslint.cmd .\src\app\App.jsx .\src\pages\ExplorePage.jsx` 통과.
- `.\node_modules\.bin\eslint.cmd .\src\pages\ExplorePage.jsx` 통과.
- `.\node_modules\.bin\eslint.cmd .\src\pages\MapPage.jsx` 통과.
- `.\node_modules\.bin\eslint.cmd .\src\features\ads\lib\ads.js .\src\features\ads\hooks\useAds.js .\src\features\ads\components\AdBanner.jsx` 통과.
- `node --check .\scripts\ads\sync-coupang-ads.cjs` 통과.
- `.\node_modules\.bin\eslint.cmd .\src\app\App.jsx .\src\features\ads\components\AdSenseLoader.jsx` 통과.
- `npm.cmd run build` 통과.
- `.\node_modules\.bin\eslint.cmd .\src\features\ads\components\AdSenseUnit.jsx .\src\features\ads\components\MonetizedAdSlot.jsx .\src\pages\HomePage.jsx .\src\pages\ExplorePage.jsx .\src\pages\MapPage.jsx` 통과.
- `.\node_modules\.bin\eslint.cmd .\src\features\ads\lib\ads.js .\src\features\ads\components\AdSenseUnit.jsx .\src\features\ads\components\MonetizedAdSlot.jsx .\src\pages\OpsPage.jsx` 통과.
- `node --check .\scripts\ads\sync-coupang-ads.cjs` 통과.
- `.\node_modules\.bin\eslint.cmd .\src\features\ads\lib\ads.js .\src\pages\OpsPage.jsx` 통과.
- `node --check .\public\sw.js`, `.\node_modules\.bin\eslint.cmd .\src\main.jsx`, `npm.cmd run build` 통과.
- `.\node_modules\.bin\eslint.cmd .\src\app\App.jsx .\src\features\auth\components\AuthModal.jsx .\src\features\ads\components\AdBanner.jsx .\src\features\ads\lib\ads.js` 통과.
- `node --check .\scripts\ads\sync-coupang-ads.cjs` 통과.
- `npm.cmd run build` 통과.
- 배포 후 `https://camp-platform-liart.vercel.app/`, `/site.webmanifest`, `/robots.txt`, `/sw.js` 확인. HTML title/canonical/og/url, manifest name, sitemap URL이 `CheheomMoa`와 현재 Vercel alias 기준으로 반영된 것을 확인했다.
- `npm.cmd audit` 결과 0 vulnerabilities.
- `npm.cmd run lint` 통과.
- `npm.cmd run build` 통과. 로컬 Node가 프로젝트 기준 20.x가 아닌 24.14.1이라 `npm audit fix` 중 engine warning이 있었지만 build는 정상 완료됐다.
- 보안 패치 재배포 후 `https://camp-platform-liart.vercel.app/` 200 응답 및 HTML의 `CheheomMoa` title/canonical/og URL을 확인했다.
- 문서 변경 검증: `rg -n "agent-browser|브라우저 자동 QA|출시 QA" AGENTS.md docs/work-log.md`로 사용 제한 기록을 확인했다.
- `agent-browser doctor --offline --quick --json` 통과. 기존 Chrome 감지는 됐지만 sandbox 실행에서 CDP channel 이슈가 있어 Chrome for Testing 설치 후 실제 사용자 환경에서 QA를 진행했다.
- `agent-browser` console/errors 확인 결과 홈/지도 모두 빈 배열. `home-mobile.png`, `map-mobile-scrolled.png`, `map-mobile-seoul-zoom.png`, `map-mobile-gangnam-zoom.png` 생성 확인.
- `.\node_modules\.bin\eslint.cmd .\src\pages\StatusPage.jsx .\src\app\App.jsx` 통과.
- `npm.cmd run build` 통과.
- `.\node_modules\.bin\eslint.cmd .\src\pages\ProfilePage.jsx .\src\app\App.jsx .\src\features\user\hooks\useUserActivity.js` 통과.
- `npm.cmd run build` 통과.
- `node --check .\scripts\qa\smoke-ui.cjs` 통과.
- `npm.cmd run qa:smoke` 통과. 로컬 샌드박스에서는 외부 Supabase/Kakao/광고 요청이 차단되므로 `QA_ALLOW_NETWORK_DENIED=1`로 해당 네트워크 차단 오류만 허용했다.
- `node --check .\scripts\qa\auth-flow.cjs` 통과.
- `npm.cmd run qa:auth`는 `QA_EMAIL`, `QA_PASSWORD`가 없어 안전하게 중단되는 것을 확인했다. 실제 로그인 후 쓰기 QA는 테스트 계정 값 설정 후 진행한다.
- `qa:auth` 진단 출력 보강 후 `node --check .\scripts\qa\auth-flow.cjs`, `npm.cmd run lint` 통과.
- 프로필 저장 단계 진단 출력 추가 후 `node --check .\scripts\qa\auth-flow.cjs`, `npm.cmd run lint` 통과.
- 프로필 저장 로직 변경 후 `.\node_modules\.bin\eslint.cmd .\src\pages\ProfilePage.jsx .\src\features\auth\components\AuthModal.jsx`, `node --check .\scripts\qa\auth-flow.cjs`, `npm.cmd run build` 통과.
- `ad_events.id` 저장 보강 후 `.\node_modules\.bin\eslint.cmd .\src\features\ads\lib\ads.js .\src\pages\ProfilePage.jsx .\src\features\auth\components\AuthModal.jsx`, `node --check .\scripts\qa\auth-flow.cjs`, `npm.cmd run build` 통과.
- `git diff --check -- .\database\supabase\migrations\20260512_applications_activity_fields.sql .\docs\work-log.md` 통과.
- `npm.cmd run qa:auth` 통과. 출력 결과 `ok=true`, checks는 `login`, `profile save`, `application record`, `status update`, `memo and review URL save`, `profile activity reflection`.
- `npm.cmd run lint` 통과.
- `npm.cmd run build` 통과.
- `vercel.cmd --prod --yes` 통과. Vercel 빌드 로그에서 `found 0 vulnerabilities`, `vite v8.0.12`, alias `https://camp-platform-liart.vercel.app` 반영을 확인했다.
- `.\node_modules\.bin\eslint.cmd .\src\features\ads\components\AdSenseUnit.jsx .\src\features\ads\components\MonetizedAdSlot.jsx` 통과.
- 광고 fallback 수정 후 `npm.cmd run build` 통과.
- `vercel.cmd --prod --yes` 재실행 통과. Vercel 빌드 로그에서 `found 0 vulnerabilities`, alias `https://camp-platform-liart.vercel.app` 반영을 확인했다.
- `node --check scripts/ads/sync-coupang-ads.cjs` 통과.
- `.\node_modules\.bin\eslint.cmd .\src\features\ads\lib\ads.js .\src\features\ads\hooks\useAds.js` 통과.
- `npm.cmd run ads:sync:coupang` 통과. `public/ads.json`은 총 65개 광고, `home_top/explore_top/explore_inline` 각 16개, `map_bottom` 17개로 갱신됐다.
- 광고 맞춤/회전 수정 후 `npm.cmd run lint`, `npm.cmd run build` 통과.
- `vercel.cmd --prod --yes` 재실행 통과. Vercel 빌드 로그에서 `found 0 vulnerabilities`, alias `https://camp-platform-liart.vercel.app` 반영을 확인했다.
- 분석 이벤트 v1 수정 후 `.\node_modules\.bin\eslint.cmd .\src\app\App.jsx .\src\pages\HomePage.jsx .\src\pages\ExplorePage.jsx .\src\features\campaigns\components\CampaignCard.jsx .\src\features\analytics\lib\analytics.js .\src\shared\components\LegalModal.jsx` 통과.
- `git diff --check`는 관련 파일 기준 통과했다. Windows CRLF 변환 warning만 출력됐다.
- `npm.cmd run build` 통과.
- 배포 전 `npm.cmd run lint`, `npm.cmd run build`를 다시 통과했다.
- `vercel.cmd --prod --yes` 통과. Vercel 빌드 로그에서 `found 0 vulnerabilities`, alias `https://camp-platform-liart.vercel.app` 반영을 확인했다.
- `curl.exe -I -L https://camp-platform-liart.vercel.app/`와 새 메인 JS asset 응답은 모두 `200 OK`였다.
- 운영 탭 분석 요약판 추가 후 `.\node_modules\.bin\eslint.cmd .\src\pages\OpsPage.jsx .\src\features\analytics\lib\analytics.js`, `git diff --check`, `npm.cmd run lint`, `npm.cmd run build`를 통과했다.
- 운영 탭 분석 요약판 배포 후 `curl.exe -I -L https://camp-platform-liart.vercel.app/?ops=1`와 새 `OpsPage-DNFe1C4V.js` asset 응답은 모두 `200 OK`였다.
- 시장 리포트 RPC/문서 추가 후 SQL/문서 기준 `git diff --check`를 통과했다.

### 다음 세션에서 이어갈 작업

- 먼저 노출된 테스트 계정 비밀번호를 변경하고 PowerShell `QA_EMAIL`, `QA_PASSWORD`, `QA_ALLOW_NETWORK_DENIED` env 정리를 확인한다.
- 배포 전 `npm.cmd run lint`, `npm.cmd run build`, 필요 시 `QA_ALLOW_NETWORK_DENIED=1` 기준 `npm.cmd run qa:smoke`와 테스트 계정 `npm.cmd run qa:auth`를 다시 확인한다.
- 사용자 승인 후 Production 배포를 진행하고, 배포 URL에서 로그인/마이/현황/광고/지도 smoke QA를 확인한다.
- 배포 후 Supabase `profiles`, `applications`, `ad_events` 관련 400 오류가 없는지 브라우저 콘솔과 운영 탭 광고 이벤트를 본다.
- 폴더 정리는 `docs/release-qa-cleanup.md` 기준으로 사용자 승인 후 처리한다.

## 2026-05-11

### 변경사항

- 서비스 방향을 좌표 완성도보다 카테고리별 통합 탐색과 플랫폼 분산 노출 중심으로 조정했다. 탐색 기본 정렬은 `사이트 골고루`, 홈 추천도 플랫폼 분산으로 노출한다.
- 탐색/카드/상세/현황 UI를 출시 전 QA 기준으로 다듬었다. 모바일 탐색 첫 카드 시작 위치를 앞당기고, 카드/모달 CTA 터치 높이와 바텀시트 전환을 보강했다.
- 새 카테고리 `서비스`를 추가하고 프론트/크롤러 카테고리 정규화를 맞췄다.
- 놀러와체험단 `comeplay` 혜택 파싱을 상세 `.etc_list2`의 `제공내역`/`혜택` 값 우선으로 수정했다. 기존 public 데이터는 수동 덮어쓰지 않았다.
- Vercel에 `VITE_PUBLIC_OPERATOR_NAME=체험단 플랫폼 운영팀`을 Production 및 기존 Preview 브랜치에 등록했고, Production에 있던 `VITE_KAKAO_MAP_APP_KEY`를 기존 Preview 브랜치에도 추가했다.
- 지도는 `kakao_address` 좌표도 표시 후보에 포함하고, 전국 첫 화면은 우선순위 160개, 지역/도시 선택 후는 최대 300개로 제한했다. 지도 로드/초기화 에러와 `지도 데이터 계산 중` 상태도 화면에 표시한다.

### 검증

- `node --check scripts/crawler/crawl.cjs` 통과.
- `npm.cmd run lint`, `npm.cmd run build` 통과.
- 데스크톱 1366x900, 모바일 390x844에서 홈, 탐색, 상세 모달, 지도, 현황, 로그인, 개인정보/약관, 문의 모달을 QA했다.
- Playwright 확인: 모바일 탐색 첫 카드 top `611px`, 카드 버튼 `44px`, 상세 모달 신청 버튼 `52px`, 닫기 버튼 `40px`.
- 최신 공개 데이터 확인: 20,638건, 12/12 플랫폼 성공, 필수 필드 누락 0건, 좌표 완성도 50.2%는 지도 보조 지표로만 봄.
- Kakao mock 지도 검증: 표시 후보 4,686개, 지역 기준 15,815개, 전국 첫 화면 클러스터 27개/핀 43개/총 overlay 70개/사이드 표시 160개.
- 로컬 샌드박스에서는 외부 Kakao/Supabase 요청이 `ERR_NETWORK_ACCESS_DENIED`로 차단된다. 실 SDK 핀 표시는 Kakao 도메인이 허용된 로컬/배포 URL에서 재확인 필요.
- 실제 `vercel --prod`, 크롤러 실행, 스케줄러 등록은 하지 않았다.

### 다음 세션에서 이어갈 작업

- 로컬은 5173 기준으로 사용한다. Kakao Developers Web 플랫폼 도메인에 `http://localhost:5173`, `http://127.0.0.1:5173`, 배포 도메인이 등록됐는지 확인한다.
- 배포 전 마지막으로 5173 또는 preview에서 모바일/PC 지도 핀, 법적 문의 문구, 탐색 첫 화면, 신청 이동을 재확인한다.
- 사용자가 명시 승인하면 `vercel --prod` 배포 후 배포 URL에서 모바일/PC 최종 QA를 진행한다.
- `comeplay` 혜택 수정은 크롤 결과물에 아직 반영되지 않았다. 사용자 승인 후 comeplay 제한 크롤 또는 전체 크롤로 갱신한다.
- 출시 직후 스케줄러는 바로 등록하지 말고 수동 크롤과 Supabase/crawl-status/data-quality를 며칠 확인한 뒤 결정한다.

## 2026-05-08

### 변경사항

- 출시 전 UX/SEO/PWA/운영 문서, 홈/탐색/지도/카드 성능 보강을 진행했다.
- 자동 크롤 등록 스크립트는 기본 오전 08:00, `-MorningTime`/`-AfternoonTime` 지정 가능 상태다. 실제 스케줄러 재등록은 아직 하지 않았다.
- 리뷰노트 잘못된 부산 주소/좌표를 public/Supabase/cache/artifact에서 제거했고, 해당 좌표를 known-bad로 등록했다.
- 리뷰노트는 공개 HTML 주소 추출을 중단하고 `REVIEWNOTE_COOKIE`가 있을 때 `/api/campaign?id=...` 상세 API의 주소/좌표만 쓰게 했다. 제목 기반 지오코딩도 막았다.
- 리뷰노트 상세 API 403 circuit breaker, 플랫폼별 주소/좌표 급락 격리, 같은 캠페인 ID 기존 정상 주소/좌표 carry-forward를 추가했다.
- 크롤 병목 완화를 위해 기본 상세 보강 제한을 `dinner=1200`, `popomon=720`, `seouloba=120`으로 조정했다.
- 크롤 시작 직후 `public/crawl-status.json`이 `running`으로 기록되게 했다.

### 검증

- 09:00 KST 전체 순차 크롤은 12/12 성공, 실패 0, `passed_with_warnings`, Supabase sync 완료, published 19,478건이었다. 전체 소요는 약 216분, 주요 병목은 `dinner`, `popomon`, `gangnam`, `reviewnote`, `seouloba`였다.
- 리뷰노트 제한 크롤은 쿠키 없을 때 주소/좌표 0건, 쿠키 입력 후 일부 회복(address 152, coords 157)했으나 상세 API가 중간부터 403으로 막혔다.
- 이후 403/품질 급락 방어를 넣은 최신 리뷰노트 제한 크롤은 quality gate가 발행을 막아 기존 public/Supabase 데이터를 덮어쓰지 않았다.
- `node --check scripts/crawler/crawl.cjs`, `npm run lint`, `npm run build`, `git diff --check -- scripts/crawler/crawl.cjs` 통과. `git diff --check`는 CRLF warning만 있었다.
- 빌드 preview QA에서 홈, 탐색, 지도, 현황, 마이, legal/contact/ops route가 desktop/mobile에서 렌더링됐고 가로 overflow/pageerror는 없었다.
- 이 정리 작업에서는 크롤, 배포, 스케줄러 재등록, Supabase 직접 수정은 실행하지 않았다.

### 다음 세션에서 이어갈 작업

- 먼저 브라우저에서 새 `REVIEWNOTE_COOKIE`를 `.env`에 갱신하고, 사용자 승인 후 `CRAWL_ONLY=reviewnote` 제한 크롤로 상세 API 주소/좌표 회복률을 확인한다.
- 리뷰노트가 다시 403이면 `REVIEWNOTE_DETAIL_ENRICH_CONCURRENCY=1`, `REVIEWNOTE_DETAIL_BATCH_DELAY_MS=3000~5000`으로 낮춰 재검증한다.
- 제한 크롤 후 `public/crawl-status.json`, `public/data-quality.json`, `.cache/crawl-artifacts/quality-gate.json`에서 reviewnote address/coords, gate, Supabase sync를 확인한다.
- 리뷰노트가 안정되면 사용자 승인 후 전체 순차 크롤을 돌려 병목 제한값과 품질 경고를 다시 본다.
- 출시 전 최종으로 `npm run build`와 preview QA를 확인하고, 사용자 승인 후 Vercel 배포 및 Windows 스케줄러 재등록을 진행한다.

## 2026-05-07

### 변경사항

- 병렬 크롤 운영 구조를 제거하고 순차 크롤 기준으로 `package.json`, crawler, 운영/출시 문서를 정리했다.
- 프론트 대량 데이터 렌더링을 보강했다. 홈 랭킹, 탐색/지도 facet count, 검색 `searchText`, 카드 memo 처리로 체감 성능을 개선했다.
- 지도는 정확 좌표 핀과 지역 기준/추정 캠페인을 분리했다. 지도 핀은 `html`, `naver`, `naver_marker`, `kakao_tile`, `*_api` 계열 중심으로 제한한다.
- 디너의여왕/체험뷰의 `[지역] 업체명` 제목 패턴을 `locationRaw`/`placeName` 지오코딩 힌트로 보존하게 했다.
- 마감일 정규화를 보강했다. 포포몬은 `C_regi_end_date_count` 우선, 체험뷰는 `/v2/campaigns` API의 `closeAt`/`status` 우선, 강남맛집은 신청/모집/접수 기간 우선, 놀러와체험단은 `comeplay_minus_one` 보정 제거와 `리뷰어 신청`/`체험단 신청` 기간 우선으로 수정했다.
- ISO timestamp는 날짜 부분만 잘라 KST 0시로 재해석하지 않고 `Date.parse`로 먼저 처리하게 했다.
- 운영 방향을 정리했다. 현재는 하루 1회 전체 12개 순차 크롤, 수정 검증은 `CRAWL_ONLY` 제한 크롤, 증분 크롤은 출시 후 운영 최적화로 별도 설계한다.

### 검증

- `AGENTS.md`, `docs/work-log.md`, `git status --short`, `package.json`을 확인했다.
- 사용자 순차 크롤 결과 12개 플랫폼 성공, quality gate `passed_with_warnings`, `public/campaigns.json` 발행, Supabase upsert 완료를 확인했다.
- 체험뷰 제한 크롤 결과 `chvu_175035` 제거, D-99 open 0건, 체험뷰 public 좌표 82.9%, 주소 96.1%, Supabase upsert 6,597건 완료를 확인했다.
- 샘플 검증: `gn_2160017`은 D-3, `pm_246612`은 D-1, `chvu_181093`은 D-1, `cply_1777863953`은 D-1로 계산되는 것을 확인했다.
- `node --check scripts\crawler\crawl.cjs`, `npm run lint`, `npm run build`, `git diff --check` 통과. `git diff --check`는 CRLF 변환 warning만 출력했다.

### 다음 세션에서 이어갈 작업

- 병렬 수집/merge 명령은 제거됐으므로 사용하지 않는다.
- 사용자가 제한 크롤을 실행하면 `popomon`, `chvu`, `comeplay`, `dinner`, 필요 시 `gangnam` 결과를 먼저 확인한다.
- 최신 크롤 후 `public/crawl-status.json`, `public/data-quality.json`, `.cache/crawl-artifacts/quality-gate.json`에서 quality gate, Supabase sync, D-day 샘플, 좌표 warning을 확인한다.
- 전체 12개 순차 크롤이 통과하면 홈/탐색/지도/상세 모달 모바일 QA와 legal/contact/ops route 확인을 진행한다.
- 출시 후 개선안으로 증분 크롤을 설계한다. 단, 일일 전체 크롤을 대체하지 말고 D-0~D-3, 신규, 좌표 누락, 최근 실패/수정 플랫폼 보강 용도로 둔다.

## 2026-05-06

### 변경사항

- 출시 MVP 기준을 방문형 중심으로 정리했다. 프론트/크롤러 모두 `campaign_type`을 `visit`으로 정규화하고, 배송형/기자단은 안정화 후 별도 타입으로 복원한다.
- `기타` 카테고리를 줄이기 위해 제목/혜택/장소명 기반 카테고리 재추론을 보강했고, `dinner`, `gangnam` 미분류 기본값은 `맛집`으로 둔다.
- 수동 병렬 수집 흐름을 실험으로 추가했었다. 2026-05-07에 운영 구조에서 제거했다.
- 병렬 스크립트의 한글/공백 경로 인용 문제와 종료된 worker를 `Wait-Process`로 다시 기다리다 실패하는 문제를 보완했다.
- 홈/탐색/지도/캠페인 카드 UX를 출시용으로 보강했다. 전체 캠페인 CTA, 지도 CTA, 카테고리/지역 탐색, 데이터 신뢰 지표, 카드 핵심 지표를 추가했다.
- 출시 문서를 정리했다. `docs/launch-priorities.md`, `docs/release-checklist.md`, SEO/PWA 메타, `sitemap.xml`을 추가/보강했다.
- 포포몬 D-day는 publish/merge 정규화 단계에서 1일 앞당기고, 강남맛집/리뷰플레이스의 과도한 상세 마감 판정을 완화했다. 포포몬 1일 앞당김은 2026-05-07 실제 사이트 기준과 맞지 않아 제거했다.
- 품질 게이트를 조정했다. 성공 플랫폼 70%는 hard gate, 좌표 70%는 지도 품질 warning, 플랫폼 open 수 80% 이상 급락은 격리 후 이전 공개 데이터 보존이다.

### 검증

- `node --check scripts\crawler\crawl.cjs` 통과.
- `npm.cmd run lint` 통과.
- `npm.cmd run build` 통과.
- 병렬 PowerShell 스크립트 parser check 통과.
- `git diff --check` 관련 변경 파일 통과.
- 병렬 수집 run `20260506-153328`은 worker 4개 결과 생성 완료. 최신 게이트 보완 전 merge는 `gangnam`, `reviewplace` 급락과 좌표 기준으로 blocked 됐다.

### 다음 세션에서 이어갈 작업

- 2026-05-07 결정으로 병렬 merge 검증은 폐기한다. 기존 순차 크롤링 운영 기준을 우선한다.
- 순차 크롤 후 `public/crawl-status.json`, `public/data-quality.json`에서 `gangnam`, `reviewplace`, 포포몬 D-day, 좌표 warning을 확인한다.
- 발행 통과 후 홈/탐색/지도에서 카테고리 `기타`, 전체보기 CTA, 지도 커버리지, 모바일 카드 가독성을 QA한다.
- 병렬 수집 run `20260506-153328`은 과거 품질 비교 자료로만 본다.

## 2026-05-05

### 변경사항

- 루트 `AGENTS.md`를 실제 코드/설정/스크립트 기준으로 재작성했다.
- `.gitignore`에서 `AGENTS.md` ignore 규칙을 제거해 다음 세션/커밋에서 문서가 보이게 했다.
- `docs/work-log.md`를 새로 만들었다.

### 검증

- `rg --files`, `git status --short`, `package.json`, `.env.example`, 주요 `src/`, `scripts/`, `database/`, `public/`, `.cache`, `logs` 구조를 확인했다.
- `node --check scripts\crawler\crawl.cjs` 통과.
- 일부 `node --check`는 sandbox의 `C:\Users\pong3` 접근 제한으로 실패했지만, `new Function(fs.readFileSync(...))` 방식의 syntax parse는 통과했다.
- 문서 작업이므로 `npm run lint`, `npm run build`, `npm run crawl`은 실행하지 않았다.

### 다음 세션에서 이어갈 작업

- Popomon/comeplay/chvu 마감일 정규화가 최신 public snapshot/Supabase에 반영됐는지 사용자 승인 후 재크롤 확인.
- 작업 시작 시 `AGENTS.md`, 이 파일, `git status --short`, `public/crawl-status.json`, `public/data-quality.json`를 먼저 확인.
- 프론트 수정 시 `npm run lint`, `npm run build`로 검증.
- 크롤러/광고/Supabase/스케줄러 실행은 사용자 승인 후 진행.

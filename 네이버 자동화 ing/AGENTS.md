# AGENTS.md

## Scope

- Work only on the Naver automation project in this repository.
- Do not inspect or modify other automation folders unless the user explicitly asks.
- Other automation folders may be read only when the user asks to identify an external popup/process source.
- Treat user files and existing working-tree changes as user-owned.

## Before Work

- If `docs/work-log.md` exists, read it first.
- Do not re-analyze the whole folder by default.
- Before reading or editing files, briefly state which files will be checked and why.
- Use only the files needed for the current goal.

## Change Rules

- Modify only what the user explicitly asked to change.
- Keep edits minimal and localized.
- Do not perform unrelated refactors, formatting churn, or cleanup.
- Do not add new persistence, resume, retry, or workflow features unless the user explicitly asks for that implementation.
- Never revert user changes unless the user explicitly requests it.
- Do not publish posts, deploy, delete files, register schedulers, or make large external API calls without explicit approval.

## Naver Shopping Connect

- Keep `네이버 블로그 글쓰기/제미나이웹.py` as the Coupang posting file unless the user explicitly asks to convert it.
- Use `네이버 블로그 글쓰기/네이버커넥팅.py` for Naver Shopping Connect. Its intended live command is `python "네이버 자동화 ing\네이버 블로그 글쓰기\네이버커넥팅.py" --post-type 네이버`, but live posting still requires explicit approval.
- `skssj2629` is currently not used for scheduled posting. Do not run `네이버 블로그 글쓰기/skssj2629/skssj2629.py` or `skssj2629(스케줄러).py` unless the user explicitly reactivates that account.
- The current scheduled Naver automation targets are the parent `네이버 블로그 글쓰기/스케줄러.py` for `제미나이웹.py` and `네이버 블로그 글쓰기/skssj2628/skssj2628(스케줄러).py` for `skssj2628.py`.
- Historical `skssj2629` Shopping Connect files may remain in the folder, including `skssj2629_naver.csv`, but they are not active scheduler targets.
- Shopping Connect rows must preserve the user-provided `쇼핑커넥트링크` and `광고고지문`; do not replace `naver.me` affiliate links with generic product URLs.
- `평점` and `리뷰개수` are reference-only prompt inputs; never turn them into quality, satisfaction, medical, or performance guarantees.
- The `skssj2629` blog persona is a detail-sensitive Cheongdam mother. Keep ad/daily prompts natural, using technical terms only when explained plainly and mixing conversational endings like `~하더라고요`, `~거든요`, and `~잖아요`.
- `skssj2629` daily and ad body text should keep ordinary visible lines around 40 Korean characters instead of overly short chopped lines or long paragraphs; preserve URLs, hashtags, and Naver editor markers during any line-wrap post-processing, and do not alter product-name text.
- Do not run Coupang deeplink/API conversion for Shopping Connect data.
- Keep Shopping Connect state files separate from Coupang used-product history.

## Gemini Web Automation

- `네이버 블로그 글쓰기/제미나이웹.py` uses the Gemini Chrome profile at `C:\Users\itwill\ChromeGeminiBot`.
- `네이버 블로그 글쓰기/skssj2628/skssj2628.py` also uses Gemini Web. Save only its Gemini session with `--login`/`--gemini-login`; use `GEMINI_PROFILE_PATH` when separating the account profile, for example `C:\Users\itwill\ChromeGeminiBot_skssj2628`.
- To change the Gemini Google account, close any Chrome/ChromeDriver using that profile, back up or rename `ChromeGeminiBot`, then log in with a fresh profile. Do not delete old session folders unless the user explicitly approves.
- Close any manually opened Gemini Chrome window before running automation, because the same profile can be locked by an existing browser process.
- Gemini UI no longer exposes the old `사고 모델` option. `제미나이웹.py` should select `Gemini 3.1 Pro` by visible model text.
- `skssj2628.py` should not force the Gemini model selector during startup unless the user explicitly asks to restore it; keep the already-selected/default Gemini model and debug input readiness first.
- If Gemini model selection fails after a UI update, inspect `_select_thinking_model()` and the visible model menu first; do not guess new selectors.

## skssj2628 Account And Links

- `skssj2628/skssj2628.py` defaults to Naver ID `skssj2628`; do not let global `NAVER_ID` or `NAVER_PROFILE_PATH` silently point it at another account.
- Use `SKSSJ2628_NAVER_ID`, `SKSSJ2628_NAVER_PASSWORD`, and `SKSSJ2628_NAVER_PROFILE_PATH` for `skssj2628`-specific overrides.
- Use `skssj2628.py --naver-login` to save only the `skssj2628` Naver session before scheduled posting. This does not publish.
- The default `skssj2628` Naver profile is `네이버 블로그 글쓰기/skssj2628/ChromeNaverBot_skssj2628`; do not save its session into the home-level `C:\Users\itwill\ChromeNaverBot_skssj2628` profile unless `SKSSJ2628_NAVER_PROFILE_PATH` intentionally points there.
- The current `skssj2628` monetization direction is a 체험단 플랫폼 유입용 blog: daily/info posts should focus on 체험단 신청, 후기 작성, 블로그 운영, 네이버 플레이스/리뷰 마케팅, and 소상공인 캠페인 운영.
- Keep `skssj2628` Coupang as a supplemental track. The scheduler target mix is 체험단형 `일상` 7건 + `쿠팡` 3건 unless the user explicitly changes the strategy.
- `skssj2628` 체험단 platform name is `CheheomMoa`. Main URL is `https://camp-platform-liart.vercel.app/`; blogger campaign discovery URL is `https://camp-platform-liart.vercel.app/app?tab=explore`.
- `skssj2628` advertiser/campaign registration URL is not separately available yet. Prompts must not invent a 사장님 캠페인 등록 페이지; advertiser-facing posts can only point to the main URL as a general platform check while this URL is blank.
- `skssj2628` prompts must not invent links, domains, 가입 유도, 선정 보장, 매출 보장, or 검색 노출 보장.
- `skssj2628` prompts should optimize through search-intent consistency, useful checklists, retention, and trustworthy structure; do not expose terms like `상위노출`, `SEO`, `D.I.A.`, `C-Rank`, or `AI 브리핑` in generated post text.
- In `skssj2628.py`, Coupang deeplink conversion failures skip that CSV candidate and try the next candidate. Do not publish with the original non-deeplink URL after conversion failure.
- `skssj2628.py` currently has no similar-product API fallback after deeplink conversion failures; add one only after the user explicitly asks.

## Daily Content Quality

- `skssj2628/skssj2628.py` daily posts should use narrow search-intent topics, not diary-style broad topics.
- Preserve the topic fields that drive depth: `core_explanation`, `specific_terms`, `check_sequence`, `practical_points`, `mistakes_to_avoid`, `faq_questions`, and `fact_guardrails`.
- For policy, weather, electricity-rate, or other changeable factual topics, do not invent numbers or dates. Use the guardrails in the prompt and verify official sources before adding hard facts.

## Coupang Crawlers

- Running Coupang crawlers modifies CSV databases and calls an external site, so start crawls only after explicit user approval.
- If Coupang blocks normal automation, open debugger Chrome first and wait for the user to finish login/authentication before starting the crawler.
- Port `9333` with profile `C:\Users\itwill\ChromeCoupangDebugStable9333` is a working fallback when `9222` is blocked. Set `COUPANG_DEBUGGER_ADDRESS=127.0.0.1:9333` for that session.
- `skssj2627_crawler.py` and `skssj2628/skssj2628_crawler.py` must skip products that were already crawled or ever posted by normalized product name, canonical URL, product ID, item ID, and product+item identity keys.
- `skssj2627_db.csv` uses parent `네이버 블로그 글쓰기/자동발행상태기록파일/coupang_used_products.json`; `skssj2628_db.csv` uses `skssj2628/자동발행상태기록파일/coupang_used_products.json`.
- Do not clear used-history JSON files during CSV cleanup. If the user asks to remove used rows from a CSV, create a backup first.
- Current replenishment crawls should not click Coupang `판매량순`; crawl the current category screen before sort. A target count can require multiple pages because existing/used products are filtered out.
- Review sampled rows before large no-sort crawls because Coupang can return mixed product names even when the CSV category label is fixed.

## Scheduler Notes

- The actual posting schedule is Windows Task Scheduler, not necessarily any in-code `generate_daily_schedule()` helper.
- Querying schedules is read-only, but scheduler registration, deletion, or edits require explicit approval.
- When the user says "스케줄러 두 개", the active targets are only:
  - `네이버 블로그 글쓰기/스케줄러.py` for `제미나이웹.py`
  - `네이버 블로그 글쓰기/skssj2628/skssj2628(스케줄러).py` for `skssj2628.py`
- Parent `스케줄러.py` registers `NaverBlogAutoPost_*` tasks for `제미나이웹.py` with `일상 3건`, `쿠팡 0건`.
- `skssj2628` scheduler entry point is `네이버 블로그 글쓰기/skssj2628/skssj2628(스케줄러).py`.
- `skssj2628` scheduler tasks use `NaverBlogAutoPost_skssj2628_*`; the daily refresh task is `NaverBlogAutoPost_skssj2628_RefreshDaily` and defaults to `00:05`.
- `skssj2628(스케줄러).py` registers `skssj2628.py` with `일상 7건 + 쿠팡 3건`.
- `skssj2628` scheduled tasks must use `티스토리 자동화 ing/.venv/Scripts/python.exe` when available. Do not let them fall back to bare `Python311`; that environment lacked `pyperclip` and caused an import-time exit.
- After changing scheduler command construction, re-run `skssj2628(스케줄러).py --target-date auto` before judging live behavior; already-registered Windows tasks keep the old command until re-registered.
- When debugging `skssj2628` scheduler account issues, query a registered task with `schtasks /Query /TN "NaverBlogAutoPost_skssj2628_01" /V /FO LIST` and check that `Task To Run` includes `--naver-id "skssj2628"`.
- After any scheduler registration, verify:
  - `schtasks /Query /TN "NaverBlogAutoPost_01" /V /FO LIST`
  - `schtasks /Query /TN "NaverBlogAutoPost_RefreshDaily" /V /FO LIST`
  - `schtasks /Query /TN "NaverBlogAutoPost_skssj2628_01" /V /FO LIST`
  - `schtasks /Query /TN "NaverBlogAutoPost_skssj2628_RefreshDaily" /V /FO LIST`
  - no `NaverBlogAutoPost_2629` tasks remain unless the user explicitly reactivates `skssj2629`.
- Historical `skssj2629` scheduler tasks use `NaverBlogAutoPost_2629_*`. If they exist while `skssj2629` is inactive, delete them only after explicit user approval.

## AdPost Daily Prompt Notes

- `제미나이웹.py` daily posts are currently optimized for AdPost-centered 생활비 체크형 content: 월세, 이사, 통신, 공과금.
- User analysis showed revenue mainly from mobile body and PC bottom placements. Daily prompts should keep readers scrolling with practical mid/body checks and useful bottom sections, not direct ad or click wording.
- Keep the `제미나이웹.py` daily prompt rule that forbids outputting `광고`, `클릭`, `하단 광고`, `수익`, and `애드포스트` in generated body text.
- Preserve the added bottom structure for daily posts: `오늘 바로 확인할 순서` checklist and short FAQ near the end.

## Debugging

- For cause analysis, inspect recent logs first, then the smallest related code path.
- Separate confirmed facts from likely causes.
- If the user asks for analysis only, do not modify code.
- For browser automation issues, check session/profile paths, recent logs, and the exact failed Selenium step before proposing changes.
- If a scheduled run appears to open and close immediately, first check `schtasks /Query ... /V /FO LIST` for `Last Result` and `Task To Run`, then check whether a new log file was created. No new log usually means import/startup failure before scheduled logging.
- Recent `skssj2628` immediate-close root cause was wrong Python: `Python311` missing `pyperclip`. Confirm with `skssj2628.py --help` using the scheduled Python path before changing browser logic.
- For `skssj2628` Coupang logs, repeated deeplink conversion failures can be warnings if a later candidate succeeds. Judge by the final lines: `발행 성공` vs `콘텐츠 생성 실패` / `에러 1건`.

## Verification

- After a change, run the smallest practical verification command.
- Prefer syntax checks or focused dry checks before live automation.
- Do not run live posting unless the user explicitly asks.
- Final responses should include changed files and verification results.

## Communication

- Keep updates short and concrete.
- If a task is ambiguous, make the safest narrow assumption or ask one concise question.
- If a command may affect publishing, scheduling, deletion, or external systems, stop and ask first.

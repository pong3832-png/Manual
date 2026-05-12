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
- The active `skssj2629` Shopping Connect script is `네이버 블로그 글쓰기/skssj2629/skssj2629.py`; it can publish live posts and requires explicit approval for manual runs.
- The active `skssj2629` Shopping Connect CSV is `네이버 블로그 글쓰기/skssj2629/skssj2629_naver.csv`.
- The default Shopping Connect Naver blog ID is `skssj2629`; use `NAVER_CONNECT_PROFILE_PATH` for an explicit Naver profile override.
- Shopping Connect rows must preserve the user-provided `쇼핑커넥트링크` and `광고고지문`; do not replace `naver.me` affiliate links with generic product URLs.
- `평점` and `리뷰개수` are reference-only prompt inputs; never turn them into quality, satisfaction, medical, or performance guarantees.
- The `skssj2629` blog persona is a detail-sensitive Cheongdam mother. Keep ad/daily prompts natural, using technical terms only when explained plainly and mixing conversational endings like `~하더라고요`, `~거든요`, and `~잖아요`.
- `skssj2629` daily and ad body text should keep ordinary visible lines at about 25 Korean characters or less instead of long paragraphs; preserve URLs, hashtags, and Naver editor markers during any line-wrap post-processing, and do not alter product-name text.
- Do not run Coupang deeplink/API conversion for Shopping Connect data.
- Keep Shopping Connect state files separate from Coupang used-product history.

## Scheduler Notes

- The actual posting schedule is Windows Task Scheduler, not necessarily any in-code `generate_daily_schedule()` helper.
- Querying schedules is read-only, but scheduler registration, deletion, or edits require explicit approval.
- `skssj2629` scheduler entry point is `네이버 블로그 글쓰기/skssj2629/skssj2629(스케줄러).py`.
- `skssj2629` scheduler tasks use `NaverBlogAutoPost_2629_*`; the daily refresh task is `NaverBlogAutoPost_2629_RefreshDaily` and defaults to `00:05`.
- `skssj2629` scheduled runs use `네이버 블로그 글쓰기/skssj2629/자동발행실행보조파일/run_scheduled_post.ps1`; do not reuse parent `자동발행실행보조파일` because it targets the older parent scripts.

## Debugging

- For cause analysis, inspect recent logs first, then the smallest related code path.
- Separate confirmed facts from likely causes.
- If the user asks for analysis only, do not modify code.
- For browser automation issues, check session/profile paths, recent logs, and the exact failed Selenium step before proposing changes.

## Verification

- After a change, run the smallest practical verification command.
- Prefer syntax checks or focused dry checks before live automation.
- Do not run live posting unless the user explicitly asks.
- Final responses should include changed files and verification results.

## Communication

- Keep updates short and concrete.
- If a task is ambiguous, make the safest narrow assumption or ask one concise question.
- If a command may affect publishing, scheduling, deletion, or external systems, stop and ask first.

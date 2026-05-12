# Work Log

## 2026-05-12

### Changed

- Updated `네이버 블로그 글쓰기/네이버커넥팅.py` default Shopping Connect CSV from `skssj2627_naver.csv` to `skssj2629_naver.csv`.
- Updated the Shopping Connect blog label in `네이버커넥팅.py` prompts from `skssj2627` to `skssj2629`.
- Set `네이버커넥팅.py` default Naver blog ID to `skssj2629`, changed write URL to `https://blog.naver.com/skssj2629?Redirect=Write&`, and separated the Naver profile override to `NAVER_CONNECT_PROFILE_PATH`.
- Added `--naver-login` to save only the `skssj2629` Naver browser session without generating or publishing a post.
- Updated Shopping Connect success handling to mark the selected row in CSV with `used`, `used_at`, and `post_title` in addition to JSON state.
- Updated `skssj2629/skssj2629.py` quote handling so Shopping Connect links and hashtags are forced back into normal body text instead of staying inside a quote block.
- Added 24 user-provided Naver Shopping Connect products to `skssj2629/skssj2629_naver.csv`.
- Added `평점` and `리뷰개수` columns to `skssj2629/skssj2629_naver.csv` and passed those values into the Shopping Connect body prompt as reference-only data.
- Updated `skssj2629/skssj2629.py` daily prompt, daily title prompt, and image prompt to use the "청담 사는 자녀 둔 예민한 어머니" persona instead of generic home-management topics.
- Updated `skssj2629/skssj2629.py` Shopping Connect body prompt so ad posts reference provided rating/review counts naturally and evaluate products through ingredient, material, age, cleaning, storage, and child-route criteria.
- Added baby/child product group guides in `skssj2629/skssj2629.py` for formula/baby food, feeding goods, skincare/hygiene, baby clothing, toys/teaching aids, and baby food containers.
- Added Shopping Connect prompt rules in `skssj2629/skssj2629.py` to use 2-4 product-specific technical terms and immediately explain them in plain "청담 엄마" language without making medical or performance guarantees.
- Updated `skssj2629/skssj2629.py` daily and Shopping Connect body prompts to mix natural blog endings such as `~하더라고요`, `~거든요`, and `~잖아요` instead of repeating only formal `~합니다` / `~됩니다` endings.
- Updated `skssj2629/skssj2629.py` daily and Shopping Connect body prompts plus local post-processing so ordinary body lines are wrapped around 25 Korean characters while URLs, hashtags, and editor markers are preserved; product-name text is kept but may wrap across short lines.
- Updated `skssj2629/skssj2629(스케줄러).py` for the `skssj2629` folder: task prefix, peer schedule paths, post types, and target script now point to `skssj2629.py` / Naver Shopping Connect.
- Added `skssj2629/자동발행실행보조파일/run_scheduled_post.ps1` and `run_refresh_schedule.ps1` so scheduled runs execute the local `skssj2629.py` and `skssj2629(스케줄러).py` paths.
- Registered the `skssj2629` Windows scheduled tasks for `2026-05-12`: 5 daily posts and 5 Naver Shopping Connect posts, plus `NaverBlogAutoPost_2629_RefreshDaily`.
- Updated root and Naver `AGENTS.md` to document `skssj2629` CSV, scheduler, and prompt operating rules.

### Verified

- Confirmed `네이버 블로그 글쓰기/skssj2629/skssj2629_naver.csv` exists and the old parent-level `skssj2627_naver.csv` target is not used.
- AST syntax check passed for `네이버커넥팅.py`.
- `skssj2629/skssj2629_naver.csv` parsed with `rows=43`, no missing required fields, and no duplicate Shopping Connect links.
- Newly added 24 CSV rows all have `평점` and `리뷰개수` populated.
- AST syntax check passed for `skssj2629/skssj2629.py`.
- AST syntax check passed for `skssj2629/skssj2629(스케줄러).py`.
- PowerShell parser checks passed for `skssj2629` scheduled-run and refresh wrapper scripts.
- `schtasks /Query` confirmed `NaverBlogAutoPost_2629_01` and `NaverBlogAutoPost_2629_RefreshDaily` exist and are `Ready`.
- `skssj2629/skssj2629_naver.csv` still parses with `rows=43`, `평점=True`, `리뷰개수=True`, and 24 populated rating/review values.
- `py_compile` passed for `skssj2629/skssj2629.py` after short-line body formatting changes.
- `git diff --check` passed for `AGENTS.md`, `네이버 자동화 ing/AGENTS.md`, and `skssj2629/skssj2629.py`; only LF/CRLF warnings appeared.
- No live posting, deletion, or bulk external API calls were run.

### Next

- Check the next scheduled logs in `skssj2629/자동발행상태기록파일/logs/` for ChatGPT/Naver session health, link/hashtag placement outside quote blocks, CSV `used` marking, natural Cheongdam-mom tone, and short-line body flow.
- If the first Shopping Connect clicks or sales appear, add a lightweight performance CSV for product group, title pattern, rating/review count, and link-position results.

## 2026-05-11

### Changed

- Updated `네이버 블로그 글쓰기/제미나이웹.py` daily prompt: snippet-first opening, 2600~3200자 target, rotating neighbor CTA.
- Improved `제미나이웹.py` and `skssj2628/skssj2628.py` product prompts: problem-diagnosis flow, product-group density, position-independent CTA, quote/list marker guards, and "먼저 확인할 환경" wording.
- Cleaned `제미나이웹.py`: removed unreachable legacy daily block, unused Coupang API search helpers, and unused imports/variables.
- Added `네이버 블로그 글쓰기/skssj2627_naver.csv` with 19 Naver Shopping Connect products from user-provided links.
- Converted `네이버 블로그 글쓰기/네이버커넥팅.py` for Shopping Connect: default CSV `skssj2627_naver.csv`, `쇼핑커넥트링크`, separate state files, `--post-type 네이버`, Shopping Connect disclosure and prompts.

### Verified

- `py_compile` passed for `제미나이웹.py`, `skssj2628.py`, `네이버커넥팅.py`, and `gemini_web_runner.py`.
- `--help` passed for `제미나이웹.py`, `skssj2628.py`, `네이버커넥팅.py`, and `gemini_web_runner.py`.
- `git diff --check` passed for changed Python/CSV files; only LF/CRLF warnings appeared.
- `skssj2627_naver.csv` parsed with `rows=19` and no missing `상품명`, `키워드`, or `쇼핑커넥트링크`.
- Safe import-only selection test confirmed `네이버커넥팅.py` reads `skssj2627_naver.csv` and selects a `naver.me` link.
- Read-only scheduler check confirmed Windows Task Scheduler is the actual schedule source; no schedule changes were made.

### Next

- Keep `제미나이웹.py` as the Coupang posting file; use `네이버커넥팅.py` for Shopping Connect.
- Before live Shopping Connect posting, run only with explicit approval: `python "네이버 자동화 ing\네이버 블로그 글쓰기\네이버커넥팅.py" --post-type 네이버`.
- Review one generated Shopping Connect sample before scheduler registration.
- Do not commit/push until sensitive credentials and affiliate-link CSV exposure in the working tree are reviewed.

## 2026-05-08

### Changed

- Added root `AGENTS.md` with project operating rules for Naver automation work.
- Updated `네이버 블로그 글쓰기/skssj2628/skssj2628.py` so empty quote markers are skipped before creating Naver quote blocks.
- Updated `네이버 블로그 글쓰기/제미나이웹.py` with the same empty quote guard.

### Verified

- `skssj2628.py` syntax check: `syntax ok`.
- `제미나이웹.py` syntax check: `syntax ok`.
- CSV inventory check, read-only:
  - `skssj2627_db.csv`: 86 total, 10 used, 76 unused.
  - `skssj2628_db.csv`: 100 total, 48 used, 52 unused.
- `skssj2628` daily schedule for `2026-05-08` confirmed from `daily_schedule.json`.
- Naver session profile for `skssj2628` had cookie updates at `2026-05-08 10:41:46`.
- A brief PowerShell popup was identified as Tistory scheduled automation, not Naver automation.

### Next

- Continue only in `C:\Users\itwill\자동화 공부\네이버 자동화 ing`.
- Do not touch Tistory or other automation folders unless the user explicitly asks.
- If the Naver title-click failure repeats, analyze logs first; do not change click logic without approval.
- Do not add resume/pending/retry features unless explicitly requested.
- Live posting, scheduler registration, deletion, crawling, or external bulk API calls require explicit approval.

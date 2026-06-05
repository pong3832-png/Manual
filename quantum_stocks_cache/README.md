# Quantum Stocks Cache

Local-only Phase 2 quant trainer for Dynamic Trend Following.

## 쉬운 사용법

새 앱 화면은 FastAPI + React 버전입니다.

Windows에서 바로 열려면 이 파일을 더블클릭합니다.

```text
start_gui.cmd
```

이미 `127.0.0.1:8766` 서버가 떠 있으면 브라우저만 열고, 서버가 없으면 로컬 앱을 백그라운드로 띄운 뒤 브라우저를 엽니다.

```powershell
cd .\web
npm.cmd install
npm.cmd run build
cd ..
.\.venv\Scripts\python.exe .\scripts\run_web_app.py
```

브라우저에서 `http://127.0.0.1:8766`을 엽니다. 이 화면은 `/api/status`로 현재 후보, 가격 기준일, 비교군 상태, 성과 추적 상태를 읽고, 종목 입력창은 `/api/search`로 로컬 종목명 후보를 보여주며, `오늘 분석` 버튼은 `/api/analyze`를 호출합니다. 기본값은 외부 가격 갱신을 하지 않으며 주문도 실행하지 않습니다.

종목은 코드 없이 이름으로 검색할 수 있습니다. 예: `삼성전자`, `삼성바이오로직스`, `LG화학`, `한국전력`, `하이브`. 현재 검색은 로컬 universe와 별칭 테이블 기준입니다. 전체 KRX 종목명 DB를 자동 갱신하는 기능은 별도 외부 데이터 호출 승인이 필요합니다.

웹 화면으로 쓰려면 로컬 앱을 실행합니다.

```powershell
.\.venv\Scripts\python.exe .\scripts\app.py
```

기존 가벼운 HTML 화면은 `http://127.0.0.1:8765`에서 계속 쓸 수 있습니다. 브라우저에서 열고 아래 순서로 사용합니다.

1. `종목 입력`에 `삼성전자`, `현대차`, `005930`처럼 입력
2. `오늘 분석 실행` 클릭
3. `오늘 결론 보기`로 대시보드 확인

기본 실행은 캐시된 로컬 데이터만 사용합니다. `최신 가격 갱신`을 체크하면 외부 가격 데이터 호출 경로가 켜집니다. 주문은 실행하지 않습니다.

오늘 분석은 이 한 줄로 실행합니다.

```powershell
.\.venv\Scripts\python.exe .\scripts\today.py
```

특정 종목을 추가하면서 오늘 분석까지 실행하려면:

```powershell
.\.venv\Scripts\python.exe .\scripts\today.py 삼성전자
.\.venv\Scripts\python.exe .\scripts\today.py 005930
```

실행 전에 어떤 단계가 돌지 확인하려면:

```powershell
.\.venv\Scripts\python.exe .\scripts\today.py 삼성전자 --dry-run
```

최신 가격까지 갱신하려면 명시적으로 아래 옵션을 붙입니다. 이 옵션은 외부 가격 데이터를 호출합니다.

```powershell
.\.venv\Scripts\python.exe .\scripts\today.py 삼성전자 --refresh-market-data
```

주문은 실행하지 않습니다. 결과는 대시보드와 리포트에 검토용으로만 생성됩니다.

종목은 이름이나 6자리 코드로 넣을 수 있습니다.

```powershell
.\.venv\Scripts\python.exe .\scripts\add_stock.py 삼성전자
.\.venv\Scripts\python.exe .\scripts\add_stock.py 현대차
.\.venv\Scripts\python.exe .\scripts\add_stock.py 005930
```

오늘 분석 파이프라인에 바로 연결하려면:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py --add-stock 삼성전자
```

이 명령은 로컬 분석 대상에 종목을 추가하고 리포트/대시보드를 갱신합니다. `--refresh-market-data`를 붙이지 않으면 외부 가격 조회를 하지 않습니다. 주문은 실행하지 않으며 결과는 항상 검토용입니다.

## Market Data

Update real listed-stock data from Yahoo Finance via `yfinance`:

```powershell
.\.venv\Scripts\python.exe .\scripts\update_market_data.py --config .\configs\portfolio.yaml
```

This writes `data/prices.csv` for the symbols in `configs/portfolio.yaml`.

To update prices for a research universe instead of only the portfolio symbols:

```powershell
.\.venv\Scripts\python.exe .\scripts\update_market_data.py --config .\configs\portfolio.yaml --universe-csv .\configs\research_universe.actual.csv
```

This command calls Yahoo Finance through `yfinance`, so run it only when external data access is approved.

Manual CSV format:

```csv
date,000660.KS,005380.KS
2025-01-02,170000,220000
2025-01-03,172000,221500
```

Use adjusted close prices when possible.

## Backtest

```powershell
.\.venv\Scripts\python.exe .\scripts\run_backtest.py --config .\configs\portfolio.yaml
```

## Daily Trainer

```powershell
.\.venv\Scripts\python.exe .\scripts\run_daily_trainer.py --config .\configs\portfolio.yaml
```

## Current Weights Check

Before using a trade plan, compare the actual holdings CSV with `configs/portfolio.yaml`:

```powershell
.\.venv\Scripts\python.exe .\scripts\check_current_weights.py --config .\configs\portfolio.yaml --current-weights-csv .\configs\current_weights.example.csv
```

Input CSV format:

```csv
symbol,current_weight
000660.KS,0.60
005380.KS,0.40
```

Default mode is dry-run. It writes:

- `reports\portfolio_state\current_weights_check.csv`
- `reports\portfolio_state\current_weights_check.md`

Rows with `abs(config_weight - actual_weight) >= --threshold` are marked `WARN`.
Use `--write-config` only when you explicitly want to replace the YAML `current_weights` section.

## Investment Readiness Gate

Create one human-review report from current weights, pre-trade checks, and alpha timing:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_investment_readiness.py --config .\configs\portfolio.yaml --current-weights-csv .\configs\current_weights.example.csv
```

By default, this reads:

- latest `reports\runs\*\pretrade_checked_trade_plan.csv`
- `reports\alpha\buy_timing_report.csv`

It writes:

- `reports\investment_readiness\investment_readiness.csv`
- `reports\investment_readiness\investment_readiness.md`
- `reports\portfolio_state\current_weights_check.csv`
- `reports\portfolio_state\current_weights_check.md`

Status rules:

- `BLOCK`: current weights mismatch, risk block, or pre-trade block exists.
- `READY_FOR_HUMAN_REVIEW`: controls pass and the result is ready for manual investment review.

This command does not place orders, connect to a broker, or call external APIs.

## Institutional Control Plane

```powershell
.\.venv\Scripts\python.exe .\scripts\run_institutional_trainer.py --config .\configs\portfolio.yaml
```

Use cached prices without network:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_institutional_trainer.py --config .\configs\portfolio.yaml --skip-market-data-update
```

The institutional runner writes:

- `reports\runs\<run_id>\investment_committee_report.md`
- `reports\runs\<run_id>\trade_plan.csv`
- `reports\runs\<run_id>\pretrade_checked_trade_plan.csv`
- `models\registry\<run_id>.json`
- `ledger\research_ledger.csv`

## Alpha Forecast And Buy Timing

```powershell
.\.venv\Scripts\python.exe .\scripts\run_alpha_research.py --config .\configs\portfolio.yaml
```

The alpha runner writes:

- `reports\alpha\buy_timing_report.csv`
- `reports\alpha\buy_timing_report.md`

Fields:

- `expected_20d_return`
- `upside_probability`
- `buy_timing_score`
- `decision`
- `sample_count`
- `model_r2`

## Company Research Candidates

Build a normalized universe CSV from a seed file:

```powershell
.\.venv\Scripts\python.exe .\scripts\build_research_universe.py --source-csv .\configs\research_universe_seed.example.csv --output-csv .\configs\research_universe.actual.csv
```

Merge multiple seed files, keep first-seed priority for duplicates, and optionally cap the universe size:

```powershell
.\.venv\Scripts\python.exe .\scripts\build_research_universe.py --source-csv .\configs\research_universe_seed.example.csv --source-csv .\configs\research_universe_seed.core_korea.csv --output-csv .\configs\research_universe.actual.csv --limit 50
```

Add one company to the active local universe without rebuilding the whole file:

```powershell
.\.venv\Scripts\python.exe .\scripts\add_research_symbol.py --code 006800 --company-name "Mirae Asset Securities" --market KOSPI --sector Securities
```

Use `--replace` to update an existing row. This command only edits the local universe CSV; it does not fetch prices, call OpenDART, place orders, or write manual-review PASS values. For KOSDAQ companies, pass `--market KOSDAQ`.

Add one company and immediately create a no-order local analysis report from cached prices:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_symbol_analysis.py --code 006800 --company-name "Mirae Asset Securities" --market KOSPI --sector Securities
```

This writes `reports\symbol_analysis\symbol_analysis_<symbol>.csv|md`. If cached price history is missing, the report is marked `DATA_REQUIRED` and tells you to refresh market data only after explicit approval. It keeps `order_status=NO_ORDER` and `external_api_requested=NO`.

Add multiple companies from one CSV:

```powershell
.\.venv\Scripts\python.exe .\scripts\add_research_symbols.py --symbols-csv .\configs\research_universe_additions.csv
.\.venv\Scripts\python.exe .\scripts\run_symbol_batch_analysis.py --symbols-csv .\configs\research_universe_additions.csv
```

Batch CSV format:

```csv
code,company_name,market,sector
006800,Mirae Asset Securities,KOSPI,Securities
091990,Celltrion Healthcare,KOSDAQ,Biotech
```

The batch path is local-only. It updates the universe CSV and writes `reports\symbol_analysis\symbol_analysis_batch.csv|md`; it does not fetch prices, call OpenDART, apply manual PASS values, or place orders.

Check whether the active universe is broad enough and covered by cached prices:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_universe_coverage.py --universe-csv .\configs\research_universe.actual.csv --prices-csv .\data\prices.csv
```

It writes `reports\universe_coverage\universe_coverage.csv|md`. The default target is 20-50 companies, with core comparison names such as Samsung Electronics, Hyundai Motor, SK hynix, Samsung C&T, LG, and Hyundai Mobis required. Missing prices are reported as `PRICE_DATA_REQUIRED`; the command does not fetch prices or place orders.

Seed CSV format:

```csv
code,company_name,market,sector
005930,Samsung Electronics,KOSPI,Semiconductors
091990,Celltrion Healthcare,KOSDAQ,Biotech
```

The builder converts KOSPI codes to `.KS` and KOSDAQ codes to `.KQ`.
`configs/research_universe_seed.core_korea.csv` is a curated starter seed, not a full official KRX universe.

Validate and score optional fundamentals:

```powershell
.\.venv\Scripts\python.exe .\scripts\check_fundamentals.py --fundamentals-csv .\configs\fundamentals.example.csv
```

Fetch fundamentals from OpenDART after setting `OPENDART_API_KEY` in `.env`:

```powershell
.\.venv\Scripts\python.exe .\scripts\fetch_opendart_fundamentals.py --universe-csv .\configs\research_universe.actual.csv --output-csv .\configs\fundamentals.actual.csv --year 2025
```

Fetch common shares outstanding and apply market-cap based PER/PBR:

```powershell
.\.venv\Scripts\python.exe .\scripts\fetch_opendart_shares.py --universe-csv .\configs\research_universe.actual.csv --output-csv .\configs\shares_outstanding.actual.csv --year 2025
.\.venv\Scripts\python.exe .\scripts\apply_valuation_metrics.py --fundamentals-csv .\configs\fundamentals.actual.csv --prices-csv .\data\prices.csv --shares-csv .\configs\shares_outstanding.actual.csv --output-csv .\configs\fundamentals.actual.csv
```

The OpenDART fetcher reads the key from `.env` or the `OPENDART_API_KEY` environment variable. Never commit or print the key.

Fetch a single-stock OpenDART filing-review draft:

```powershell
.\.venv\Scripts\python.exe .\scripts\fetch_opendart_filing_review.py --symbol 028260.KS --begin-date 20260101 --end-date 20260527 --output-dir .\reports
```

This calls OpenDART `list.json` for one company and writes `reports\filing_review\opendart_filings_028260.csv`, `opendart_filing_review_028260.csv`, and `.md`. It only pre-fills filing existence checks and does not edit `configs\manual_review.actual.csv`.

Scan the downloaded filing list for risk-review text evidence:

```powershell
.\.venv\Scripts\python.exe .\scripts\fetch_opendart_text_risk_scan.py --symbol 028260.KS --disclosures-csv .\reports\filing_review\opendart_filings_028260.csv --max-documents 2 --output-dir .\reports
```

This downloads only the selected annual/quarterly/semiannual documents via OpenDART `document.xml` and writes `opendart_text_risk_scan_028260.csv`, `opendart_text_risk_summary_028260.csv`, and `.md`. Keyword hits are review candidates only; all recommended manual values remain `UNKNOWN` until human confirmation.

Fundamentals CSV format:

```csv
symbol,revenue_growth,operating_margin,roe,per,pbr,debt_ratio
005930.KS,0.12,0.18,0.15,18.5,1.4,0.65
```

Use ratios as decimals: `0.12` means 12%.

Rank companies from local cached price data and explain the data reasons:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_company_research.py --config .\configs\portfolio.yaml --universe-csv .\configs\research_universe.example.csv
```

To combine price/alpha data with fundamentals:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_company_research.py --config .\configs\portfolio.yaml --universe-csv .\configs\research_universe.actual.csv --fundamentals-csv .\configs\fundamentals.example.csv
```

Optional universe CSV:

```csv
symbol,company_name,sector
000660.KS,SK hynix,Semiconductors
005380.KS,Hyundai Motor,Autos
```

The report combines:

- alpha timing score and decision
- 20-day momentum
- SMA20 trend gap
- 20-day drawdown
- optional fundamental score and reasons
- latest cached price date
- human-readable thesis, risk points, and review questions for each candidate

It writes:

- `reports\company_research\company_research.csv`
- `reports\company_research\company_research.md`

Analyze every company from `company_research.csv` with the same local price, alpha, valuation, and risk rules:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_universe_stock_analysis.py --company-research-csv .\reports\company_research\company_research.csv --output-dir .\reports
```

It writes:

- `reports\universe_stock_analysis\universe_stock_analysis.csv`
- `reports\universe_stock_analysis\universe_stock_analysis.md`

Every row keeps `order_status=NO_ORDER`; `BUY_READY` is only a manual gate and sizing review candidate.

Track market/watchlist changes without deciding capital:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_market_watch.py --company-research-csv .\reports\company_research\company_research.csv --output-dir .\reports --top-n 15
```

It writes:

- `reports\market_watch\market_watch.csv`
- `reports\market_watch\market_watch.md`
- `reports\market_watch\market_watch_history.csv`

The watcher compares against the previous `reports\market_watch\market_watch.csv` when it exists and flags upgrades, downgrades, stable priority names, and today's focus list. It also appends each snapshot to `market_watch_history.csv`, so status changes remain auditable over time.

Persistence labels:

- `NEW_FOCUS`: first `TODAY_FOCUS` snapshot.
- `BUILDING_FOCUS`: second consecutive `TODAY_FOCUS` snapshot.
- `PERSISTENT_FOCUS`: third or later consecutive `TODAY_FOCUS` snapshot.
- `NOT_FOCUS`: not currently in `TODAY_FOCUS`.

It uses local reports only and does not call external APIs.

Create a conviction score report from persistent focus names:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_conviction_score.py --market-watch-csv .\reports\market_watch\market_watch.csv --company-research-csv .\reports\company_research\company_research.csv --output-dir .\reports
```

Before any name reaches `PERSISTENT_FOCUS`, you can preview developing names:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_conviction_score.py --market-watch-csv .\reports\market_watch\market_watch.csv --company-research-csv .\reports\company_research\company_research.csv --output-dir .\reports --include-building-focus
```

It writes:

- `reports\conviction\conviction_score.csv`
- `reports\conviction\conviction_score.md`

Conviction tiers are research attention levels only, not buy instructions.

Distill the conviction and checklist reports into a small profit-focused list:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_profit_focus.py --conviction-csv .\reports\conviction\conviction_score.csv --checklist-csv .\reports\investment_checklist\investment_checklist.csv --output-dir .\reports --max-core 3
```

It writes:

- `reports\profit_focus\profit_focus.csv`
- `reports\profit_focus\profit_focus.md`
- `reports\profit_focus\today_focus.md`

Profit focus statuses:

- `CORE_FOCUS`: strongest current research candidate, still manual-review only.
- `WAIT_RISK`: promising signal, but risk/valuation/checklist issue blocks action.
- `NEEDS_CHECKLIST`: candidate needs brief/checklist before it can be considered.
- `WATCH_ONLY`: keep monitoring.

This is the simplest operating view: what to focus on, why, what invalidates it, and what to do next. It still does not place orders or guarantee returns.
Use `today_focus.md` first when capital is undecided: it keeps one top candidate, wait/exclude reasons, and loss-defense rules on a single page.

Turn the top `CORE_FOCUS` name into a no-order thesis memo:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_investment_memo.py --profit-focus-csv .\reports\profit_focus\profit_focus.csv --output-dir .\reports --max-memos 1
```

It writes:

- `reports\investment_memo\investment_memo.csv`
- `reports\investment_memo\investment_memo.md`

Every memo row is `order_status=NO_ORDER`. Use it to review the thesis, evidence, manual checks, and loss-defense rules before any capital decision.

Create a rule-first capital plan review before entering any amount:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_capital_plan_review.py --investment-memo-csv .\reports\investment_memo\investment_memo.csv --investment-checklist-csv .\reports\investment_checklist\investment_checklist.csv --company-research-csv .\reports\company_research\company_research.csv --output-dir .\reports
```

When actual capital is known, pass it explicitly:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_capital_plan_review.py --investment-memo-csv .\reports\investment_memo\investment_memo.csv --investment-checklist-csv .\reports\investment_checklist\investment_checklist.csv --company-research-csv .\reports\company_research\company_research.csv --output-dir .\reports --total-capital-krw 3000000
```

Or keep the actual amount in a local-only file:

```csv
total_capital_krw,notes
3000000,actual review capital
```

Save that format as `configs\capital.actual.csv`. The integrated today pipeline reads it automatically when `--total-capital-krw` is omitted. The CLI value overrides the CSV. Use `configs\capital.example.csv` as the template; do not commit or invent the actual amount.

It writes:

- `reports\decision_gate\capital_plan_review.csv`
- `reports\decision_gate\capital_plan_review.md`
- per-symbol files such as `capital_plan_review_003550.csv`

The default rule set keeps `order_status=NO_ORDER`, caps one name at 15%, keeps a 25% cash buffer, uses 30% / 30% / 40% tranches, and marks `amount_status=CAPITAL_AMOUNT_REQUIRED` until total capital is explicitly provided. With `--total-capital-krw`, it marks `CAPITAL_PROVIDED` for review only; it still does not place orders.

Create a draft for the six manual decision-gate fields:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_manual_review_draft.py --investment-memo-csv .\reports\investment_memo\investment_memo.csv --investment-checklist-csv .\reports\investment_checklist\investment_checklist.csv --company-research-csv .\reports\company_research\company_research.csv --filing-risk-dir .\reports\filing_review --capital-plan-dir .\reports\decision_gate --output-dir .\reports
```

It writes:

- `reports\decision_gate\manual_review_draft.csv`
- `reports\decision_gate\manual_review_draft.md`
- per-symbol draft files such as `manual_review_draft_003550.csv`

Draft values are `PASS_CANDIDATE`, `FAIL_CANDIDATE`, or `UNKNOWN`. They are evidence support only; do not copy them into `configs\manual_review.actual.csv` as actual `PASS` without human confirmation. `capital_plan_review=PASS_CANDIDATE` means the rule set exists; it does not mean capital amount or order size has been approved.

Create a user-confirmation proposal from the draft:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_manual_review_proposal.py --manual-review-draft-csv .\reports\decision_gate\manual_review_draft.csv --output-dir .\reports
```

It writes:

- `reports\decision_gate\manual_review_proposal.csv`
- `reports\decision_gate\manual_review_proposal.md`
- per-symbol proposal files such as `manual_review_proposal_003550.csv`

The proposal converts draft candidates into reviewable `PASS`/`FAIL`/`UNKNOWN` values and marks `approval_required=YES`. It still does not write `configs\manual_review.actual.csv`; only a final human-confirmed step may do that.

Create an auditable apply plan before any actual manual config write:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_manual_review_apply_plan.py --manual-proposal-csv .\reports\decision_gate\manual_review_proposal.csv --actual-output-csv .\configs\manual_review.actual.csv --output-dir .\reports
```

It writes:

- `reports\decision_gate\manual_review_apply_plan.csv`
- `reports\decision_gate\manual_review_apply_plan.md`
- `reports\decision_gate\manual_review_actual_candidate.csv`

Default mode is `DRY_RUN`, with `actual_config_written=NO`. The script writes `configs\manual_review.actual.csv` only when `--confirm-final-review I_CONFIRM_MANUAL_REVIEW` is explicitly supplied. Do not use that confirmation token until the proposal has been reviewed and accepted.

Gate the memo with explicit manual evidence before any sizing review:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_decision_gate.py --investment-memo-csv .\reports\investment_memo\investment_memo.csv --output-dir .\reports
```

It writes:

- `reports\decision_gate\decision_gate.csv`
- `reports\decision_gate\decision_gate.md`
- `reports\decision_gate\manual_review_template.csv`

Optional manual review input:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_decision_gate.py --investment-memo-csv .\reports\investment_memo\investment_memo.csv --manual-review-csv .\configs\manual_review.example.csv --output-dir .\reports
```

Manual review fields use `PASS`, `FAIL`, or `UNKNOWN`:

- `filing_review`
- `earnings_review`
- `business_driver_review`
- `valuation_review`
- `loss_rule_review`
- `capital_plan_review`

All six fields must be `PASS` before the status becomes `READY_FOR_SIZING_REVIEW`. The order status remains `NO_ORDER`.

Build one local HTML page for the current operating view:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_dashboard.py --reports-dir .\reports
```

It writes:

- `reports\dashboard\index.html`

Open that file in a browser to see the top candidate, universe coverage gate, decision gate, manual review draft/proposal, thesis memo, loss-defense rules, wait/exclude list, single-symbol intake results from `reports\symbol_analysis\`, and links to the source reports. This dashboard is read-only output and still does not place orders.

Create the final "done or not done" operating status report:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_operating_status.py --reports-dir .\reports
```

It writes `reports\operating_status\operating_status.csv|md`. `completion_status=DONE` means the local review workflow is ready to use; it still keeps `order_status=NO_ORDER` and `broker_order_requested=NO`. `NOT_DONE` lists the remaining blockers such as manual review config, capital amount, universe coverage, or cached price coverage.

Run the full "today candidate refresh" pipeline as the dashboard refresh button equivalent:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py --dry-run
.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py
```

Add one company, include it in the same local refresh, and render its intake status before the dashboard:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py --add-code 006800 --add-company-name "Mirae Asset Securities" --add-market KOSPI --add-sector Securities
```

Batch-add companies before the same refresh:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py --add-symbols-csv .\configs\research_universe_additions.csv
```

The add-symbol path inserts a local universe update before any optional market refresh, then writes a `Symbol Analysis Intake` report before the dashboard. It keeps `order_status=NO_ORDER`; if cached prices are missing, the intake row remains `DATA_REQUIRED`. Add `--refresh-market-data` only when external price access has been explicitly approved.

When actual capital is known, pass it through the same refresh:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py --total-capital-krw 3000000
```

By default this reuses cached/local inputs, checks universe coverage, recalculates the candidate reports, refreshes the top candidate, creates the capital plan review, runs filing summaries before the manual draft, creates the user-confirmation manual review proposal, creates a dry-run manual review apply plan, runs the decision gate, creates a pre-buy decision with manual-proposal/capital blockers, creates no-capital order candidates, capital scenarios, creates the final operating status, and rebuilds `reports\dashboard\index.html`. If `configs\manual_review.actual.csv` exists, the decision gate uses it automatically. If `configs\capital.actual.csv` exists, capital plan review and order sizing receive that amount automatically; `--total-capital-krw` overrides it. To fetch latest prices first, add `--refresh-market-data`; that calls the external market data provider, reapplies PER/PBR valuation metrics when `fundamentals.actual.csv` and `shares_outstanding.actual.csv` exist, and requires explicit approval before running.

Build a local filing-review report for the remaining manual gate:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_filing_review.py --input-csv .\configs\filing_review.example.csv --output-dir .\reports
```

It writes `reports\filing_review\filing_review.csv` and `.md`. The output recommends only `PASS`, `FAIL`, or `UNKNOWN` for the `filing_review` field; it does not edit `configs\manual_review.actual.csv`.
You can also pass the OpenDART draft CSV, for example `--input-csv .\reports\filing_review\opendart_filing_review_028260.csv`.

Create a sharper human-review filter from the generated company research report:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_research_filter.py --company-research-csv .\reports\company_research\company_research.csv --output-dir .\reports --top-n 5
```

It writes:

- `reports\research_filter\research_filter.csv`
- `reports\research_filter\research_filter.md`

Filter statuses:

- `PRIORITY_RESEARCH`: data supports manual deep-dive first.
- `WATCH_FOR_CONFIRMATION`: timing may be strong, but fundamentals/view need confirmation.
- `EXCLUDE_UNTIL_RESET`: exclude until alpha/view conditions recover.

`--top-n` limits the ordinary watchlist rows, but it does not drop `PRIORITY_RESEARCH` rows that rank just outside the cutoff.

Create individual company briefs for the priority candidates:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_candidate_briefs.py --research-filter-csv .\reports\research_filter\research_filter.csv --output-dir .\reports --status PRIORITY_RESEARCH
```

It writes:

- `reports\candidate_briefs\candidate_briefs.csv`
- `reports\candidate_briefs\candidate_briefs.md`
- one Markdown file per selected company under `reports\candidate_briefs\`

These briefs are local research notes only. They do not place orders or connect to broker APIs.

Create a pre-investment checklist from the selected candidate briefs:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_investment_checklist.py --candidate-briefs-csv .\reports\candidate_briefs\candidate_briefs.csv --output-dir .\reports
```

It writes:

- `reports\investment_checklist\investment_checklist.csv`
- `reports\investment_checklist\investment_checklist.md`

Checklist statuses:

- `READY_FOR_MANUAL_REVIEW`: automatic gates have no blockers, but manual checks still remain.
- `NEEDS_MANUAL_REVIEW`: one or more automatic blockers or valuation/risk warnings remain.

Create manual-review order candidates without assuming capital:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_order_sizer.py --candidate-checklist-csv .\reports\investment_checklist\investment_checklist.csv --prices-csv .\data\prices.csv --output-dir .\reports
```

Without `--total-capital-krw`, rows are marked `BLOCKED_CAPITAL_REQUIRED` with zero shares and zero estimated order value.
After entering total capital explicitly:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_order_sizer.py --candidate-checklist-csv .\reports\investment_checklist\investment_checklist.csv --prices-csv .\data\prices.csv --output-dir .\reports --total-capital-krw 10000000
```

It writes:

- `reports\orders\order_candidates.csv`
- `reports\orders\order_candidates.md`

Default sizing rules:

- includes only `READY_FOR_MANUAL_REVIEW`
- keeps `--cash-buffer-weight 0.10`
- caps each candidate at `--max-position-weight 0.20`
- floors share quantity to whole shares
- marks sized rows `REVIEW_ONLY`

This creates order candidates only. It does not place orders, connect to broker APIs, or assume your capital unless `--total-capital-krw` is provided.

Create split-buy scenarios for possible future capital amounts:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_capital_scenarios.py --candidate-checklist-csv .\reports\investment_checklist\investment_checklist.csv --prices-csv .\data\prices.csv --capital-plan-dir .\reports\decision_gate --output-dir .\reports
```

It writes:

- `reports\orders\capital_scenarios.csv`
- `reports\orders\capital_scenarios.md`

Default scenarios are 1M, 3M, 5M, and 10M KRW. Rows stay `order_status=NO_ORDER` and `execution_mode=MANUAL_REVIEW_ONLY`; the report only shows target-position and first/second/final tranche shares under the capital-plan rules.

Track post-buy thesis and performance after a real manual order:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_investment_tracking.py --trade-journal-csv .\configs\trade_journal.actual.csv
```

Use `configs\trade_journal.example.csv` as the template. The tracker writes:

- `reports\performance_tracking\performance_tracking.csv`
- `reports\performance_tracking\performance_tracking.md`

It calculates invested value, current value, unrealized PnL, unrealized return, and 1-week/1-month/quarter review dates from cached prices. It does not connect to a broker or place orders. If `configs\trade_journal.actual.csv` does not exist, it writes a `NO_TRADE_JOURNAL` report so the dashboard clearly says tracking has not started.

Views:

- `RESEARCH_CANDIDATE`: data supports deeper manual research
- `WATCHLIST`: not enough edge yet
- `AVOID_FOR_NOW`: alpha/trend data is weak

This is not an instruction to trade and does not guarantee returns. It uses cached price data only unless you separately run market data update.

The daily trainer writes:

- `reports\daily\YYYY-MM-DD_trade_plan.csv`
- `reports\daily\YYYY-MM-DD_decision_report.md`
- `reports\daily\YYYY-MM-DD_sizing_diagnostics.csv`

## Reports

The runner writes:

- `reports/equity_curve.csv`
- `reports\position_matrix.csv`
- `reports\signal_matrix.csv`
- `reports\performance_summary.csv`

## Strategy Logic

```python
signal = close > SMA20
position = signal.shift(1)
dynamic_return = position * asset_return - transaction_cost
```

`shift(1)` is mandatory. It prevents using today's close to trade today's return.

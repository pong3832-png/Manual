# Work Log

## 2026-06-05 - Documentation Handoff Cleanup

- Cleaned the active handoff guidance used by future CLI sessions.
- Changed `AGENTS.md`:
  - Replaced stale May handoff values such as old sample tickers and a fixed historical run id with current start rules.
  - Marked old work-log/dashboard/ranking/candidate values as snapshots unless latest local evidence is re-opened.
  - Pointed the next development stream to `compliance_pretrade_gate` and `CLI_NEXT_SESSION_PROMPT.md`.
  - Clarified that the listed test table is representative and recent tests should be checked from `tests/test_*` as needed.
- Updated `CLI_NEXT_SESSION_PROMPT.md`:
  - Filled the `오늘 작업 목표` bracket with the next P0 build plan for `compliance_pretrade_gate`.
  - Included required local files, output reports, TDD cases, no-order safety flags, and blocked operations.
- Cleaned this work log:
  - Old "Next Session Start" / "Next Session Handoff" sections are preserved as archived historical snapshots, not current instructions.
- Verification:
  - `rg` confirmed `compliance_pretrade_gate`, `READY_FOR_HUMAN_REVIEW`, `NO_ORDER`, archived handoff labels, and current handoff guidance.
  - `git diff --check -- .\CLI_NEXT_SESSION_PROMPT.md .\AGENTS.md .\docs\work-log.md` passed, with only existing LF/CRLF warnings from Git.
- Next:
  - Start next session from `CLI_NEXT_SESSION_PROMPT.md`.
  - Implement `compliance_pretrade_gate` with TDD, local files only, and keep every output `external_api_requested=NO`, `order_status=NO_ORDER`, `broker_order_requested=NO`.
- Safety:
  - Documentation-only change.
  - No external API, OpenDART call, price refresh, broker/order action, scheduler change, deletion, deployment, git action, or `configs/manual_review.actual.csv` write.

## 2026-06-05 - Institutional Program Stack

- Added a local hedge-fund/quant-platform capability map:
  - `configs/institutional_program_stack.seed.csv`
  - `src/quantum_trainer/institutional_program_stack.py`
  - `scripts/run_institutional_program_stack.py`
  - `tests/test_institutional_program_stack.py`
- Public capability examples reviewed:
  - Bloomberg Terminal for data/research terminal workflow.
  - BlackRock Aladdin for portfolio/risk platform workflow.
  - MSCI Barra/RiskMetrics for factor risk and portfolio risk workflow.
  - QuantConnect LEAN and Microsoft Qlib for backtesting/AI quant research workflow.
  - MLflow Model Registry for model lineage/versioning workflow.
  - SS&C Eze, FlexTRADER, and Enfusion for OMS/EMS/portfolio workbench workflow.
- Behavior:
  - Maps public capability categories to local review-only implementation candidates.
  - Writes `reports/institutional_program_stack/institutional_program_stack.csv|md` and summary CSV.
  - Keeps `external_api_requested=NO`, `order_status=NO_ORDER`, and `broker_order_requested=NO`.
- First local run:
  - `row_count=13`
  - `p0_count=5`
  - `p1_count=6`
  - `p2_count=2`
  - P0 next modules: `compliance_pretrade_gate`, `factor_risk_exposure`, `model_registry_audit`, `tca_slippage_guard`, `institutional_control_tower`.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_institutional_program_stack.py -q` -> `4 passed`.
  - `.\.venv\Scripts\python.exe .\scripts\run_institutional_program_stack.py` -> generated reports, `external_api_requested=NO`, `order_status=NO_ORDER`.
- Safety:
  - Public products/frameworks are used only as capability references.
  - No proprietary system cloning, broker/order action, external API refresh, OpenDART call, dependency install, scheduler change, deletion, deployment, git action, or `configs/manual_review.actual.csv` write.

## 2026-06-05 - Panic Rebound Signal

- Added a local close-price panic/rebound watch program:
  - `src/quantum_trainer/panic_rebound_signal.py`
  - `scripts/run_panic_rebound_signal.py`
  - `tests/test_panic_rebound_signal.py`
- Behavior:
  - Reads cached `data/prices.csv` and local `reports/company_research/company_research.csv`.
  - Detects sharp drawdown, rebound from 20-day low, MA10/MA20 reclaim, reversal confirmation, and chase risk.
  - Writes `reports/panic_rebound_signal/panic_rebound_signal.csv|md`.
  - Labels rows as `READY_REBOUND_REVIEW`, `WAIT_CONFIRMATION`, `CHASE_RISK`, `LOW_PRIORITY`, or `INSUFFICIENT_DATA`.
  - Keeps `external_api_requested=NO`, `order_status=NO_ORDER`, and `broker_order_requested=NO`.
- First local run:
  - `row_count=2657`
  - `ready_rebound_review_count=35`
  - `wait_confirmation_count=2207`
  - `chase_risk_count=31`
  - `insufficient_count=101`
  - Top ready examples include `001510.KS` SK증권, `015260.KS` 에이엔피, `023530.KS` 롯데쇼핑, `031980.KQ` 피에스케이홀딩스, `084370.KQ` 유진테크.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_panic_rebound_signal.py -q` -> `2 passed`.
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\panic_rebound_signal.py .\scripts\run_panic_rebound_signal.py` -> passed.
  - `.\.venv\Scripts\python.exe .\scripts\run_panic_rebound_signal.py` -> generated reports, `external_api_requested=NO`, `order_status=NO_ORDER`.
- Safety:
  - `READY_REBOUND_REVIEW` is a watch label only, not a buy signal.
  - No broker/order action, external API refresh, OpenDART call, ML dependency install, scheduler change, deletion, deployment, git action, or `configs/manual_review.actual.csv` write.

## 2026-06-05 - Strategy Research Backlog

- Added a local public-research-to-feature backlog:
  - `configs/strategy_research_backlog.seed.csv`
  - `src/quantum_trainer/strategy_research_backlog.py`
  - `scripts/run_strategy_research_backlog.py`
  - `tests/test_strategy_research_backlog.py`
- Behavior:
  - Translates papers/books into feature candidates, required local inputs, blocked external inputs, validation gates, promotion rules, Korea-market notes, and next steps.
  - Ranks backlog rows by priority and implementation status.
  - Writes `reports/strategy_research_backlog/strategy_research_backlog.csv|md` and summary CSV.
  - Keeps `external_api_requested=NO`, `order_status=NO_ORDER`, and `broker_order_requested=NO`.
- First local run:
  - `row_count=15`
  - `p0_count=6`
  - `p1_count=5`
  - `p2_count=4`
  - Top P0 themes: Korea momentum/liquidity, Korea multi-factor, Korea pricing factors, Piotroski F-score, profitability quality, accrual quality.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_strategy_research_backlog.py -q` -> `4 passed`.
  - `.\.venv\Scripts\python.exe .\scripts\run_strategy_research_backlog.py` -> generated backlog reports, `external_api_requested=NO`, `order_status=NO_ORDER`.
- Safety:
  - No broker/order action, external API refresh, OpenDART call, ML dependency install, scheduler change, deletion, deployment, git action, or `configs/manual_review.actual.csv` write.

## 2026-06-05 - Public Quant Learning Feedback Loop

- Added a local learning-feedback layer for alpha predictions:
  - `src/quantum_trainer/learning_feedback.py`
  - `scripts/run_learning_feedback.py`
  - `tests/test_learning_feedback.py`
  - `docs/strategy-learning-system.md`
- Behavior:
  - Appends timestamped prediction snapshots from `reports/alpha/buy_timing_report.csv`.
  - Compares matured snapshots with cached `data/prices.csv` after the configured forward horizon.
  - Writes realized forecast error, MAE/RMSE/bias, directional accuracy, and model action guidance under `reports/learning_feedback/`.
  - Keeps `external_api_requested=NO`, `order_status=NO_ORDER`, and `broker_order_requested=NO`.
- Public research boundary:
  - Documented that only public papers, public filings, public statements, cached prices, and user-approved public data refreshes may be used.
  - Private hedge-fund models, leaked research, inside information, non-public order flow, credentials, and broker-confidential logic remain prohibited.
- First local run:
  - `as_of=2026-06-05`
  - `snapshot_count=2`
  - `realized_count=0`
  - `pending_count=2`
  - `learning_action=WAIT_FOR_MORE_REALIZED_SAMPLES`
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_learning_feedback.py .\tests\test_alpha_forecast.py -q` -> `11 passed`.
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\learning_feedback.py .\scripts\run_learning_feedback.py` -> passed.
- Safety:
  - No broker/order action, external API refresh, OpenDART call, scheduler change, deletion, deployment, git action, or `configs/manual_review.actual.csv` write.

## 2026-06-05 - Today Market Refresh And Candidate Start

- Ran the approved `.\.venv\Scripts\python.exe .\scripts\today.py` daily pipeline with latest price refresh.
- Result:
  - Price cache refreshed through `2026-06-05`.
  - Market regime remains `RISK_OFF / DEFENSIVE`.
  - Operating status remains `NOT_DONE`, `WAIT`, `NO_ORDER`.
  - Today's operating top candidate changed to `085910.KQ` 네오티스, not Komico.
  - Profit focus top 3: 네오티스, 코리아써키트, 오스템.
  - Main blockers: manual gate not ready and market regime defensive.
- Safety:
  - No broker/order action, scheduler change, deletion, deployment, or `configs/manual_review.actual.csv` write.
  - Generated order candidates remain review-only / no real order.

## 2026-06-05 - Stale Research Snapshot Rule

- Added an `AGENTS.md` operating rule for investment analysis:
  - Old thesis, dashboard, ranking, work-log, and candidate notes are snapshots, not current truth.
  - Each session must re-check latest local report dates, cached price date, ranking rows, gate rows, and filing/valuation evidence before carrying forward old conclusions.
  - If a touched report has stale price/rank/gate/filing/valuation data, update it to the latest local evidence or mark `UNKNOWN` / `DATA_REQUIRED`.
  - Do not keep analyzing a previous top candidate just because it was top in an older run.
- Safety:
  - No external API, OpenDART call, price refresh, dashboard/pre-buy regeneration, broker/order action, scheduler change, deletion, deployment, or `configs/manual_review.actual.csv` write.

## 2026-06-05 - Komico Thesis And Manual Gate Review

- Updated `reports/investment_thesis/investment_thesis_183300.md` from local-only evidence.
- Result:
  - Filing `HOLD_REVIEW` cause is treated as a keyword-gap hold: `Regulatory/accounting litigation overhang` has evidence 0, source reports 0, fatal risk 0.
  - Komico filing gate is a `PASS` candidate only; no actual manual config was written.
  - Valuation remains `UNKNOWN` because `configs/fundamentals.actual.csv` and `configs/shares_outstanding.actual.csv` have no Komico row.
  - Current conclusion stays `WAIT / NO_ORDER` due to valuation gap, premium fallback metrics, chase risk, and market/sector `RISK_OFF`.
  - Peer filing summaries for Neotis, Selemix, and Peptron were reviewed from existing local files only.
- Verification:
  - `rg "작성일: 2026-06-05|결론: WAIT / NO_ORDER|filing_review=PASS 후보|valuation_review=UNKNOWN|MARKET_WAIT|NO_ORDER" .\reports\investment_thesis\investment_thesis_183300.md` -> expected lines found.
  - `git diff --check -- "quantum_stocks_cache/reports/investment_thesis/investment_thesis_183300.md"` -> passed.
- Safety:
  - No external API, OpenDART call, price refresh, dashboard/pre-buy regeneration, broker/order action, scheduler change, deletion, deployment, or `configs/manual_review.actual.csv` write.

## 2026-06-04 - GUI Light Operator Theme

- Converted the React GUI from the dark terminal palette to a light operator-console palette after user preference feedback.
- Changed:
  - `web/src/styles.css`
  - `docs/work-log.md`
- Behavior:
  - Preserves the fixed top bar, left analysis panel, main canvas, fixed status footer, dense candidate/holding boards, and `NO_ORDER` safety visual.
  - Uses light neutral surfaces with cyan/green/yellow/red/purple/gold accents for status and decision signals.
- Verification:
  - `npm.cmd run build` in `web/` -> passed.
- Safety:
  - No broker/order action, external API refresh, OpenDART call, scheduler change, deletion, deployment, or manual actual config write.

## 2026-06-04 - Terminal UIUX Docx-Informed Redesign

- Applied the local `docs/QSP_Terminal_UIUX_기획서_v1.0.docx` direction to the FastAPI + React GUI without adding execution features.
- Changed:
  - `src/quantum_trainer/web_api.py`
  - `web/src/main.jsx`
  - `web/src/styles.css`
  - `tests/test_web_api.py`
- Behavior:
  - Background analyze jobs now expose `stage`, `stage_text`, `elapsed_seconds`, and top-level `external_api_requested` for terminal-style progress display.
  - React layout now uses a terminal-style fixed top bar, left analysis panel, main canvas, and fixed status footer.
  - CSS was rebuilt around dark terminal design tokens from the docx: deep background, surface panels, cyan/green/yellow/red/purple/gold status accents, and monospace numeric presentation.
  - Existing Control Tower, Decision Card, candidate board, and holding defense board remain review-only with `NO_ORDER`.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_web_api.py -q` -> `12 passed`.
  - `npm.cmd run build` in `web/` -> passed.
- Safety:
  - No broker/order action, external API refresh, OpenDART call, scheduler change, deletion, deployment, or manual actual config write.

## 2026-06-04 - GUI Control Tower And Decision Cards

- Added hedge-fund-style operator summaries to the local FastAPI + React GUI while keeping the app review-only.
- Changed:
  - `src/quantum_trainer/web_api.py`
  - `web/src/main.jsx`
  - `web/src/styles.css`
  - `tests/test_web_api.py`
- Behavior:
  - `/api/candidates` now includes a `control_tower` summary with market entry policy, cached data status, candidate counts, and `NO_ORDER` safety flags.
  - Candidate rows now include `decision_summary` with review label, watch price range, risk line, market gate, and chase-risk context.
  - `/api/holdings` now includes a portfolio defense `control_tower`; holding rows include review-only `decision_summary` fields.
  - React UI now shows an operator control tower, one-line decision card, progress elapsed time, and richer candidate/holding cards.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_web_api.py -q` -> `12 passed`.
  - `npm.cmd run build` in `web/` -> passed.
- Safety:
  - No broker/order action, external API refresh, OpenDART call, scheduler change, deletion, deployment, or manual actual config write.

## 2026-06-04 - GUI Quick Stock Analysis

- Tuned GUI background analysis so a user-entered stock no longer waits on the full 2,657-symbol daily pipeline.
- Changed:
  - `src/quantum_trainer/web_api.py`
  - `src/quantum_trainer/today_command.py`
  - `src/quantum_trainer/symbol_analysis.py`
  - `tests/test_web_api.py`
  - `tests/test_symbol_analysis.py`
  - `AGENTS.md`
- Behavior:
  - `/api/analyze/jobs` with `stock` now uses `analysis_mode=QUICK_STOCK`.
  - Quick stock jobs force `refresh_market_data=false`, use cached `data/prices.csv`, run local `symbol_analysis`, and refresh the dashboard.
  - `symbol_analysis` now runs company research against a one-symbol universe and writes its intermediate research output under `reports/symbol_analysis/`, avoiding full-universe recomputation.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_web_api.py .\tests\test_symbol_analysis.py .\tests\test_today_command.py -q` -> `16 passed`.
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\today_command.py .\src\quantum_trainer\web_api.py .\src\quantum_trainer\symbol_analysis.py` -> passed.
  - Restarted local GUI server at `http://127.0.0.1:8766`; dry-run `005930` job returned `DONE`, `analysis_mode=QUICK_STOCK`, `external_api_requested=NO`, `order_status=NO_ORDER`.
- Safety:
  - Stopped stale `update_market_data.py` processes left by the previous long GUI run after approval.
  - No broker/order action, OpenDART call, scheduler change, deletion, git action, or manual actual config write.

## 2026-06-02 - Live Refresh Default For Daily Analysis

- Updated user-facing daily analysis so each normal run starts with latest market data refresh by default after the user's 2026-06-02 approval.
- Changed:
  - `src/quantum_trainer/today_command.py`
  - `src/quantum_trainer/today_pipeline.py`
  - `src/quantum_trainer/web_api.py`
  - `src/quantum_trainer/local_app.py`
  - `scripts/today.py`
  - `scripts/run_today_pipeline.py`
  - `web/src/main.jsx`
- New opt-out path:
  - CLI: `--cached-market-data`
  - API: `cache_market_data=true`
  - local app: uncheck `최신 가격 갱신`
- Safety:
  - Still no broker/order execution; every analysis keeps `order_status=NO_ORDER`.
  - No actual market refresh was executed in this change; only dry-run/compile/test verification should be used unless the user asks to run the live refresh.

## 2026-06-02 - Tactical Watchlist

- Added a local tactical watchlist so the operator can see one "what to check first today" board instead of reading event ranking, entry triggers, and sector rotation separately.
- New files:
  - `src/quantum_trainer/tactical_watchlist.py`
  - `scripts/run_tactical_watchlist.py`
  - `tests/test_tactical_watchlist.py`
- Changed:
  - `today_pipeline.py` now runs `tactical_watchlist` after `sector_rotation_watch` and before order sizing.
  - `dashboard.py` now shows `오늘 전술 관찰 우선순위` and links to `../tactical_watchlist/tactical_watchlist.md`.
  - `AGENTS.md` documents that tactical statuses are review priorities only, not order permission.
- Local generation result:
  - `reports/tactical_watchlist/tactical_watchlist.csv|md`
  - `row_count=30`
  - `ready_manual_review_count=0`
  - `sector_recovery_watch_count=16`
  - `market_defensive_wait_count=14`
  - `overheated_wait_count=0`
  - `external_api_requested=NO`
  - `order_status=NO_ORDER`
- Current interpretation:
  - The program now separates "sector recovery watch" names from broad defensive waits, while keeping Komico and all other rows blocked from actual orders.
- Safety:
  - No external API, OpenDART, price refresh, broker/order action, scheduler, deletion, or `configs/manual_review.actual.csv` write.

## 2026-06-02 - Local GUI Candidate Board

- Added a local candidate board API:
  - `src/quantum_trainer/web_api.py`
  - Endpoint: `GET /api/candidates`
  - Inputs: `reports/tactical_watchlist/tactical_watchlist.csv`, `reports/pre_buy_decision/pre_buy_decision.csv`, `reports/market_regime/market_regime.csv`, `data/prices.csv`
  - Output includes market gate, latest price date, candidate watch status, entry range, blockers, and `NO_ORDER` safety flags.
- Expanded the React GUI:
  - `web/src/main.jsx`
  - `web/src/styles.css`
  - New `오늘 후보 보드` view shows current candidates, market posture, chase risk, entry range, and readiness blockers.
  - Candidate board refreshes after running analysis.
- Added API coverage:
  - `tests/test_web_api.py` now verifies `/api/candidates` combines tactical watchlist, pre-buy decision, and market regime while preserving `order_status=NO_ORDER`.
- Verification:
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\web_api.py` -> passed.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_web_api.py -q` -> `5 passed`.
  - `npm.cmd run build` in `web/` -> passed.
  - `curl.exe http://127.0.0.1:8766/api/candidates?limit=3` -> `as_of=2026-06-02`, market `RISK_OFF/DEFENSIVE`, `order_status=NO_ORDER`.
- Local GUI:
  - Running at `http://127.0.0.1:8766/` with PID `2396`.
- Safety:
  - Local report read only.
  - No external API, OpenDART, price refresh, broker/order action, scheduler, deletion, or `configs/manual_review.actual.csv` write.

## 2026-06-02 - Local GUI Holding Defense Board

- Added a user-provided holding watch input:
  - `configs/holding_watch.actual.csv`
  - Rows: GST `083450.KQ` at `48200`, 현대로템 `064350.KS` at `197000`, LS `006260.KS` at `423500`
  - Quantity is blank; use it for entry-price risk watch only, not full trade-journal PnL.
- Added a holding defense API:
  - `GET /api/holdings`
  - Reads `configs/holding_watch.actual.csv`, `reports/trend_forecast/trend_forecast.csv`, `reports/event_adjusted_ranking/event_adjusted_ranking.csv`, and `data/prices.csv`.
  - Returns latest price, unrealized return, 7% risk stop, 10% hard stop, trend labels, and review-only action status.
- Expanded the React GUI:
  - New `보유종목 방어 보드` above the candidate board.
  - Shows 매수가, 현재가, 손익률, stop levels, trend status, and `SELL_REVIEW`/`REDUCE_REVIEW`/`HOLD_*` labels.
- Verification:
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\web_api.py` -> passed.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_web_api.py -q` -> `6 passed`.
  - `npm.cmd run build` in `web/` -> passed.
  - `curl.exe http://127.0.0.1:8766/api/holdings` -> `as_of=2026-06-02`, GST `HOLD_DEFENSIVE`, 현대로템 `REDUCE_REVIEW`, LS `HOLD_DEFENSIVE`, `order_status=NO_ORDER`.
- Local GUI:
  - Running at `http://127.0.0.1:8766/` with PID `27936`.
- Safety:
  - No broker/order action. All holding actions are review labels only.
  - No external API, OpenDART, price refresh, scheduler, deletion, or `configs/manual_review.actual.csv` write.

## 2026-06-02 - Holding Portfolio Defense Summary

- Extended `/api/holdings` with a review-only portfolio summary:
  - `holding_count`
  - `quantity_known_count`
  - `quantity_missing_count`
  - `risk_review_count`
  - known-position cost basis, market value, unrealized PnL, and return
  - `highest_priority_action`
  - `next_operator_step`
- Quantity handling:
  - Blank or zero quantity stays `quantity_known=false`.
  - Total valuation/PnL only uses rows with positive quantity.
  - Current actual holding watch file still has blank quantities, so portfolio totals stay locked until the user provides share counts.
- GUI change:
  - `보유종목 방어 보드` now shows summary KPI rows above individual holdings.
  - Individual holding cards now show whether quantity is entered.
- Verification:
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\web_api.py` -> passed.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_web_api.py -q` -> `6 passed`.
  - `npm.cmd run build` in `web/` -> passed.
  - `curl.exe http://127.0.0.1:8766/api/holdings` -> `holding_count=3`, `quantity_known_count=0`, `quantity_missing_count=3`, `highest_priority_action=REDUCE_REVIEW`, `order_status=NO_ORDER`.
- Local GUI:
  - Running at `http://127.0.0.1:8766/` with PID `23420`.
- Safety:
  - No broker/order action. All holding actions are review labels only.
  - No external API, OpenDART, price refresh, scheduler, deletion, or `configs/manual_review.actual.csv` write.

## 2026-06-02 - GUI Holding Quantity Save

- Added local GUI/API support for user-entered holding quantities:
  - `POST /api/holdings`
  - Writes user-submitted `symbol`, `company_name`, `entry_price`, `quantity`, and `notes` to `configs/holding_watch.actual.csv`.
  - Returns refreshed `/api/holdings` payload with `order_status=NO_ORDER`.
- GUI change:
  - `보유종목 방어 보드` cards now include editable `매수가` and `수량` inputs.
  - Added `수량 저장` button.
  - Saving refreshes portfolio totals and keeps order flags disabled.
- Verification:
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\web_api.py` -> passed.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_web_api.py -q` -> `7 passed`.
  - `npm.cmd run build` in `web/` -> passed.
  - `curl.exe http://127.0.0.1:8766/api/holdings` -> existing actual input preserved, `quantity_known_count=0`, `quantity_missing_count=3`, `order_status=NO_ORDER`.
- Local GUI:
  - Running at `http://127.0.0.1:8766/` with PID `30456`.
- Safety:
  - No actual holding quantity was guessed or written during implementation.
  - No broker/order action, external API, OpenDART, price refresh, scheduler, deletion, or `configs/manual_review.actual.csv` write.

## 2026-06-02 - GUI Analyze Refresh Flag Fix

- Fixed a GUI/API mismatch that could leave the user seeing only `실행 중`:
  - Frontend sent `refresh_market_data=false` when the user unchecked `최신 가격 갱신`.
  - Backend previously ignored that flag unless `cache_market_data=true` was also present.
- Changed:
  - `src/quantum_trainer/web_api.py` now computes `refresh_market_data = request.refresh_market_data and not request.cache_market_data`.
  - `web/src/main.jsx` now sends both `refresh_market_data` and `cache_market_data=!refreshMarketData`.
  - `tests/test_web_api.py` covers `refresh_market_data=false`.
- Verification:
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\web_api.py` -> passed.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_web_api.py -q` -> `8 passed`.
  - `npm.cmd run build` in `web/` -> passed.
  - Local GUI restarted at `http://127.0.0.1:8766/` with PID `25232`.
  - `curl.exe http://127.0.0.1:8766/health` -> `{"status":"OK"}`.
- User operation note:
  - Refresh the browser.
  - For a quick local run, uncheck `최신 가격 갱신` before pressing `오늘 분석`.
  - If `최신 가격 갱신` is checked, full-universe price refresh can take several minutes.
- Safety:
  - No actual report regeneration, price refresh, broker/order action, external API, OpenDART, scheduler, deletion, or `configs/manual_review.actual.csv` write.

## 2026-06-02 - Sector Rotation Watch

- Added a local sector rotation watch report so the system can show which sectors are leading, recovering early, overextended, or still defensive before reviewing individual stocks.
- New files:
  - `src/quantum_trainer/sector_rotation_watch.py`
  - `scripts/run_sector_rotation_watch.py`
  - `tests/test_sector_rotation_watch.py`
- Changed:
  - `today_pipeline.py` now runs `sector_rotation_watch` after `market_recovery_watch` and before order sizing.
  - `dashboard.py` now shows `섹터 로테이션 감시` and links to `../sector_rotation_watch/sector_rotation_watch.md`.
  - `AGENTS.md` documents that sector rotation labels are watch states only, not order permission.
- Local generation result:
  - `reports/sector_rotation_watch/sector_rotation_watch.csv|md`
  - `row_count=161`
  - `leader_count=3`
  - `early_rotation_count=17`
  - `defensive_wait_count=121`
  - `external_api_requested=NO`
  - `order_status=NO_ORDER`
- Current interpretation:
  - The market is still broadly defensive, but the dashboard can now separate early/leading sectors from defensive sectors before individual candidate review.
- Safety:
  - No external API, OpenDART, price refresh, broker/order action, scheduler, deletion, or `configs/manual_review.actual.csv` write.

## 2026-06-02 - Market Recovery Watch

- Added a local market recovery watch report so market/sector blockers have explicit unlock conditions instead of a generic wait state.
- New files:
  - `src/quantum_trainer/market_recovery_watch.py`
  - `scripts/run_market_recovery_watch.py`
  - `tests/test_market_recovery_watch.py`
- Changed:
  - `today_pipeline.py` now runs `market_recovery_watch` after `entry_signal_watch` and before order sizing.
  - `dashboard.py` now shows `시장 회복 감시` and links to `../market_recovery_watch/market_recovery_watch.md`.
  - `AGENTS.md` documents that recovery labels are monitoring states only, not order permission.
- Local generation result:
  - `reports/market_recovery_watch/market_recovery_watch.csv|md`
  - `row_count=162`
  - `breadth_wait_count=122`
  - `overheat_wait_count=1`
  - `confirmed_count=3`
  - `external_api_requested=NO`
  - `order_status=NO_ORDER`
- Current interpretation:
  - The main blocker remains market breadth recovery. Top watch candidates should not be reviewed for entry until whole-market/sector breadth improves or specific sector conditions clear.
- Safety:
  - No external API, OpenDART, price refresh, broker/order action, scheduler, deletion, or `configs/manual_review.actual.csv` write.

## 2026-06-02 - Valuation Data Quality Report

- Added a local valuation data-quality report so blank `company_research.csv` PER/PBR fields are surfaced instead of silently treated as usable valuation data.
- New files:
  - `src/quantum_trainer/valuation_data_quality.py`
  - `scripts/run_valuation_data_quality.py`
  - `tests/test_valuation_data_quality.py`
- Changed:
  - `src/quantum_trainer/today_pipeline.py` now runs `valuation_data_quality` after `investment_memo` and before manual gate drafting.
  - `tests/test_today_pipeline.py` covers the new local-only pipeline step.
- Result:
  - Generated `reports/valuation_data_quality/valuation_data_quality.csv|md`.
  - Current report: `row_count=2657`, `fallback_count=1`, `missing_count=2625`, `external_api_requested=NO`, `order_status=NO_ORDER`.
  - Komico is `INVESTMENT_MEMO_FALLBACK`, `RESEARCH_VALUATION_BLANK`, PER 40.08, PBR 4.75, `PREMIUM_REVIEW_REQUIRED`, `valuation_review_candidate=UNKNOWN`.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_valuation_data_quality.py .\tests\test_today_pipeline.py .\tests\test_manual_review_draft.py .\tests\test_dashboard.py -q` -> `20 passed`.
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\valuation_data_quality.py .\scripts\run_valuation_data_quality.py .\src\quantum_trainer\today_pipeline.py` -> passed.

## 2026-06-02 - External Data Approval Signal

- Tightened the one-command today analysis safety output.
- Changed:
  - `src/quantum_trainer/today_command.py`
  - `tests/test_today_command.py`
- Result:
  - When `refresh_market_data=True`, output now includes `외부 데이터 승인 필요: YES`.
  - Default local analysis still keeps `external_api_requested=NO` and `주문 실행: 안함`.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_today_command.py .\tests\test_today_pipeline.py .\tests\test_web_api.py .\tests\test_dashboard.py -q` -> `18 passed`.
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\today_command.py .\src\quantum_trainer\today_pipeline.py .\src\quantum_trainer\web_api.py .\src\quantum_trainer\dashboard.py` -> passed.

## 2026-06-02 - Daily Operating Checklist

- Added `docs/daily-operating-checklist.md` as the one-page daily operating order: startup checks, safety rails, Komico state, manual gates, peer comparison, local report regeneration, verification, and stop conditions.
- No code, external API, market-data refresh, manual actual config write, order execution, git action, deletion, deployment, or scheduler change was performed.

## 2026-06-02 - Stale Evidence Regression Hardening

- Added regression coverage so resolved filing HOLD_REVIEW evidence is shown as non-fatal manual resolution instead of a stale blocker.
- Added premium valuation coverage so manual review draft/proposal preserves Komico memo PER/PBR fallback when `company_research.csv` has blank valuation fields.
- Changed:
  - `src/quantum_trainer/pre_buy_decision.py`
  - `src/quantum_trainer/manual_review_draft.py`
  - `tests/test_pre_buy_decision.py`
  - `tests/test_manual_review_draft.py`
- Regenerated local reports only: manual review draft/proposal, pre-buy decision, and dashboard.
- Result:
  - Komico manual proposal remains `INCOMPLETE_DRAFT`, `valuation_review=UNKNOWN`, `actual_config_written=NO`.
  - Komico pre-buy decision remains `WAIT / NO_ORDER`.
  - Dashboard remains `top_symbol=183300.KQ`, `order_status=NO_ORDER`.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_pre_buy_decision.py .\tests\test_manual_review_draft.py .\tests\test_dashboard.py -q` -> `13 passed`.
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\pre_buy_decision.py .\src\quantum_trainer\manual_review_draft.py` -> passed.

## 2026-06-02 - Unicorn-Grade Operating Checklist

- Added `docs/superpowers/plans/2026-06-02-unicorn-grade-operating-system.md` to pin the priority board, safety contract, Komico evidence closure, manual gates, peer comparison, dashboard/pre-buy regeneration, and daily operating cadence.
- No code, config, external API, market-data refresh, order execution, git action, or manual actual config write was performed.

## 2026-06-02 - Komico Filing, Valuation, Thesis Review

- Scope stayed inside `quantum_stocks_cache`; no external API, OpenDART fetch, market-data refresh, order execution, deployment, deletion, or scheduler change was run.
- Confirmed Komico `Regulatory/accounting litigation overhang` was a keyword-evidence gap, not an identified fatal regulatory/accounting/litigation issue. Filing proposal now remains `PASS` candidate with monitoring.
- Regenerated manual review proposal and pre-buy decision reports only; `actual_config_written=NO`, `configs/manual_review.actual.csv` was not edited, and every output keeps `order_status=NO_ORDER`.
- Updated `reports/investment_thesis/investment_thesis_183300.md` and added `reports/investment_thesis/top_candidate_filing_comparison_2026-06-02.md`.
- Current Komico view: 1순위 유지, PER 40.08 / PBR 4.75 / ROE 19.69% / total liabilities-equity about 214.5%, `valuation_review=UNKNOWN`, final decision `WAIT / NO_ORDER`.
- Peer filing view: 네오티스 PASS 후보, 셀레믹스/펩트론 HOLD_REVIEW 유지, all fatal risk counts 0.
- Verification:
  - `.\.venv\Scripts\python.exe .\scripts\run_manual_review_proposal.py` -> `actual_config_written=NO`.
  - `.\.venv\Scripts\python.exe .\scripts\run_pre_buy_decision.py` -> Komico `WAIT / NO_ORDER`.
  - `.\.venv\Scripts\python.exe .\scripts\run_dashboard.py --reports-dir .\reports` -> `top_symbol=183300.KQ`, `order_status=NO_ORDER`.

## 2026-06-01 - Event-Adjusted Final Watch Ranking

- Added a local final watch ranking that combines full-universe quant output with manually entered event catalysts and chase-risk flags.
- New files:
  - `src/quantum_trainer/event_adjusted_ranking.py`
  - `scripts/run_event_adjusted_ranking.py`
  - `tests/test_event_adjusted_ranking.py`
- Changed:
  - `src/quantum_trainer/today_pipeline.py` now runs `event_adjusted_ranking` immediately after `event_catalysts`.
  - `src/quantum_trainer/dashboard.py` now shows `이벤트 조정 최종 감시 랭킹`; dashboard display prioritizes event-tagged names while keeping all rows `NO_ORDER`.
  - `tests/test_today_pipeline.py` and `tests/test_dashboard.py` cover the new pipeline step and dashboard section.
  - `AGENTS.md` documents that event-adjusted rankings are local watchlist labels only and do not authorize orders or manual gate writes.
- Result:
  - `reports/event_adjusted_ranking/event_adjusted_ranking.csv|md` generated `row_count=2657`, `ready_count=12`, `pullback_count=18`, `external_api_requested=NO`.
  - Dashboard still reports top symbol `183300.KQ` 코미코, `decision_gate_status=WAITING_MANUAL_EVIDENCE`, `order_status=NO_ORDER`.
  - Dashboard event-adjusted section now surfaces LG, 코미코, LG씨엔에스, NAVER, 삼성전자, 현대차, SK하이닉스, LG전자 ahead of no-event quant names.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_event_catalysts.py .\tests\test_event_adjusted_ranking.py .\tests\test_today_pipeline.py .\tests\test_dashboard.py -q` -> `17 passed`.
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\event_catalysts.py .\scripts\run_event_catalysts.py .\src\quantum_trainer\event_adjusted_ranking.py .\scripts\run_event_adjusted_ranking.py .\src\quantum_trainer\dashboard.py .\src\quantum_trainer\today_pipeline.py` -> passed.
  - `.\.venv\Scripts\python.exe .\scripts\run_event_adjusted_ranking.py` -> generated reports with `external_api_requested=NO`.
  - `.\.venv\Scripts\python.exe .\scripts\run_dashboard.py --reports-dir .\reports` -> regenerated dashboard, `order_status=NO_ORDER`.
- Next:
  - Komico filing: open only `reports/filing_review/filing_risk_summary_183300.md` plus the minimum source scan/report files needed; decide whether `Regulatory/accounting litigation overhang` is real risk, keyword-only hold, or fatal issue.
  - Komico valuation: first use local `configs/fundamentals.actual.csv`, `configs/shares_outstanding.actual.csv`, `data/prices.csv`, and generated reports. If PER/PBR/ROE/debt ratio inputs are still missing, request approval before OpenDART/market-data refresh.
  - Komico thesis: draft `reports/investment_thesis/investment_thesis_183300.md` with BUY_READY / WAIT / REJECT conclusion; current expected conclusion remains `WAIT / NO_ORDER` until filing and valuation gates are resolved.
  - Peer filing checks: for 네오티스 `085910.KQ`, 셀레믹스 `331920.KQ`, 펩트론 `087010.KQ`, request approval before any OpenDART list/document calls; summarize 5 key risks each and compare against Komico.
  - Manual gates: prepare only proposal/report updates for the 6 review gates. Do not edit `configs/manual_review.actual.csv` without explicit user confirmation.
  - Dashboard/pre-buy: keep event/quant labels separated from actual buy permission; regenerate dashboard and pre-buy decision after evidence updates, still `NO_ORDER`.

## 2026-06-01 - Local Event Catalyst Layer

- Added a local-only news/event catalyst layer so event-driven names such as NAVER/LG are visible separately from pure quant ranking.
- New files:
  - `src/quantum_trainer/event_catalysts.py`
  - `scripts/run_event_catalysts.py`
  - `tests/test_event_catalysts.py`
  - `configs/event_catalysts.example.csv`
- Changed:
  - `src/quantum_trainer/today_pipeline.py` now runs `event_catalysts` after `universe_stock_analysis`.
  - `src/quantum_trainer/dashboard.py` now shows `뉴스/이벤트 촉매`, event counts, chase-risk labels, and keeps every row `NO_ORDER`.
  - `tests/test_today_pipeline.py` and `tests/test_dashboard.py` cover the new step and dashboard board.
  - `configs/event_catalysts.actual.csv` was created locally for the 2026-06-01 Jensen Huang Korea event watch; this file is local manual input and may be ignored by git.
- Result:
  - `reports/event_catalysts/event_catalysts.md` generated 8 local event rows.
  - Current event output: NAVER is `EVENT_FOCUS`; LG, Samsung Electronics, LG CNS, LG Electronics, SK hynix, and Hyundai Motor are `WAIT_PULLBACK_EVENT` due chase risk; Komico is `EVENT_WATCH`.
  - Dashboard regenerated with top symbol still `183300.KQ` 코미코, final status still `WAIT / NO_ORDER`.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_event_catalysts.py .\tests\test_today_pipeline.py .\tests\test_dashboard.py -q` -> `15 passed`.
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\event_catalysts.py .\scripts\run_event_catalysts.py .\src\quantum_trainer\dashboard.py .\src\quantum_trainer\today_pipeline.py` -> passed.
  - `.\.venv\Scripts\python.exe .\scripts\run_event_catalysts.py --as-of 2026-06-01` -> `event_count=8`, `external_api_requested=NO`.
  - `.\.venv\Scripts\python.exe .\scripts\run_dashboard.py --reports-dir .\reports` -> dashboard regenerated, `order_status=NO_ORDER`.
- Next:
  - Add an event-adjusted ranking report that combines quant score, catalyst score, chase risk, and entry-price rules into one final watchlist.
  - If using live news later, require explicit approval before any crawler/API path.

## 2026-05-29 - Full KOSPI/KOSDAQ Universe Activated

- Installed and pinned `pykrx`, but direct pykrx/KRX calls returned empty/JSON errors in this environment, so the active full universe was built from the KRX KIND listed-corporation download instead.
- Added:
  - `src/quantum_trainer/kind_universe.py`
  - `scripts/import_kind_corp_list.py`
  - `tests/test_kind_universe.py`
  - `src/quantum_trainer/krx_universe.py`
  - `scripts/fetch_pykrx_universe.py`
  - `tests/test_krx_universe.py`
- Changed:
  - `configs/research_universe.actual.csv` now contains 2,657 KOSPI/KOSDAQ listed companies: 838 KOSPI and 1,819 KOSDAQ.
  - `data/prices.csv` was refreshed for 2,656 symbols through the approved bulk yfinance path; `099520.KQ` was unavailable from the provider.
  - `update_market_data.py --allow-partial` isolates failed symbols instead of failing the whole full-universe refresh.
  - Full-universe coverage now treats tiny provider gaps as `PRICE_COVERAGE_PARTIAL` and usable for ranking.
  - Company research now loads sparse full-universe price history for research ranking while strict loading remains the default for other flows.
- Result:
  - Local today pipeline completed with `external_api_requested=NO` after the approved data refresh.
  - Full-universe top research scores: `003550.KS` LG 89.72, `028260.KS` Samsung C&T 88.38, `005930.KS` Samsung Electronics 87.55, `005380.KS` Hyundai Motor 82.68, `009150.KS` Samsung Electro-Mechanics 81.63.
  - Final operating status is still `NOT_DONE` because Samsung C&T pre-buy decision is `WAIT` until manual review evidence is confirmed. Broker/order state remains `NO_ORDER`.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_config_io.py .\tests\test_alpha_forecast.py .\tests\test_market_data.py .\tests\test_today_pipeline.py .\tests\test_universe_coverage.py -q` -> `30 passed`.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_kind_universe.py .\tests\test_krx_universe.py .\tests\test_universe_coverage.py .\tests\test_operating_status.py -q` -> `12 passed`.
  - `.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py` -> `executed_count=23`, `external_api_requested=NO`, dashboard regenerated, `order_status=NO_ORDER`.

## 2026-05-29 - Full Universe And Time-Series Gate Prep

- Added a local full-KRX universe import path.
- New/changed files:
  - `scripts/import_krx_universe.py`
  - `src/quantum_trainer/research_universe.py`
  - `src/quantum_trainer/market_data.py`
  - `scripts/update_market_data.py`
  - `src/quantum_trainer/features.py`
  - `src/quantum_trainer/alpha_forecast.py`
  - `tests/test_research_universe.py`
  - `tests/test_market_data.py`
  - `tests/test_alpha_forecast.py`
  - `AGENTS.md`
  - `docs/superpowers/plans/2026-05-29-full-krx-universe-timeseries.md`
- Result:
  - `normalize_full_krx_universe()` accepts KRX-style Korean/English columns and keeps all security types, including preferred shares, ETFs, and SPACs.
  - `scripts/import_krx_universe.py --source-csv <csv>` writes a normalized full universe locally and prints `external_api_requested=NO`.
  - `update_market_data.py` now supports `--batch-size` and uses batched fetches for large universes.
  - Time-series candidate features were added: market-relative 20D return, 60D trend quality, 20/60 volatility regime, and 120D breakout gap.
  - Enhanced time-series features remain evaluation-only unless walk-forward comparison marks them `IMPROVED_CANDIDATE`.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_research_universe.py .\tests\test_market_data.py .\tests\test_alpha_forecast.py -q` -> `20 passed`.

## 2026-05-29 - Approved Market Refresh

- Ran the user-approved `run_today_pipeline.py --refresh-market-data`.
- Result:
  - `data/prices.csv` latest date updated to `2026-05-29`.
  - `configs/fundamentals.actual.csv` valuation metrics refreshed with PER/PBR/market cap and existing ROE/fundamental inputs.
  - Current program top remains `003550.KS` LG Corp: `BUY_READY`, `CORE_FOCUS`, `order_status=NO_ORDER`.
  - `028260.KS` Samsung C&T is also `CORE_FOCUS` but pre-buy decision remains `WAIT` because the manual gate is not active for that symbol.
  - `000270.KS` Kia is `WAIT`, not the top quant candidate.
- Verification:
  - Pipeline completed 25 steps with `external_api_requested=YES`.
  - Operating status is `DONE`, broker order remains `NO_ORDER`.

## 2026-05-29 - Dashboard Filing Risk Board

- Added a top-candidate filing risk card to the dashboard so the first candidate shows its fatal-risk count and review opinion beside the main decision metrics.
- Added a candidate-level filing risk board that reads all local `reports/filing_review/filing_risk_summary_*.csv` files, so Samsung C&T `028260.KS` remains visible even when it is not the current top candidate.
- Changed files:
  - `src/quantum_trainer/dashboard.py`
  - `tests/test_dashboard.py`
  - `docs/work-log.md`
- Result:
  - The dashboard keeps `order_status=NO_ORDER` and does not fetch external data.
  - Current regenerated dashboard top candidate is `003550.KS`; the new board also shows `028260.KS` with 0 fatal filing risks and `PASS_CANDIDATE_WITH_MONITORING`.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_dashboard.py -q` -> `1 passed`.
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\dashboard.py` -> passed.
  - `.\.venv\Scripts\python.exe .\scripts\run_dashboard.py --reports-dir .\reports` -> regenerated `reports/dashboard/index.html`, `top_symbol=003550.KS`, `order_status=NO_ORDER`.
  - `rg "1순위 공시 리스크|후보별 공시 리스크 현황|028260.KS|삼성물산|치명 0개" .\reports\dashboard\index.html` -> matched.
  - `rg "order_status=|Broker order|manual gate|actual_config_written|conviction_score|upside_probability" .\reports\dashboard\index.html` -> no matches.

## 2026-05-28 - Company Name Search UI

- Added local company-name search so users do not need to know the 6-digit stock code for covered names.
- Changed:
  - `src/quantum_trainer/symbol_input.py` now exposes `search_stock_inputs()` and Korean aliases/display names for the current 35-company universe.
  - `src/quantum_trainer/web_api.py` now exposes local-only `/api/search`.
  - `web/src/main.jsx` now shows search suggestions in the stock input and sends the selected symbol to analysis.
  - `web/src/styles.css` styles the suggestion list.
  - `tests/test_symbol_input.py` and `tests/test_web_api.py` cover name-only search.
  - `README.md` and `AGENTS.md` document that search is local-only and no-order.
- Result:
  - Names such as `삼성바이오로직스`, `LG화학`, `한국전력`, and `하이브` can be searched without typing codes.
  - Search reads local universe/aliases only; no external KRX lookup, market data refresh, broker API, or order execution was added.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_symbol_input.py .\tests\test_web_api.py -q` -> `11 passed`.
  - `npm.cmd run build` under `web/` -> passed.
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\symbol_input.py .\src\quantum_trainer\web_api.py` -> passed.
  - Restarted FastAPI app at `http://127.0.0.1:8766`, PID `30516`.
  - `curl.exe http://127.0.0.1:8766/health` -> `{"status":"OK"}`.
  - `/api/search?q=삼성` returned Samsung candidates; `/api/search?q=LG화학` returned `051910.KS`.
  - `/api/status` stayed `completion_status=DONE`, `latest_price_date=2026-05-28`, `top_candidate=003550.KS`, `order_status=NO_ORDER`.
- Next:
  - Keep using `http://127.0.0.1:8766` as the main UI.
  - Next improvement is a broader local KRX company-name universe so unknown names do not require codes. Treat that as data import/update work; do not fetch external KRX/market data without approval.
  - Keep order execution out of scope; UI/API must stay `NO_ORDER`.

## 2026-05-28 - FastAPI React App

- Added a product-style FastAPI + React app as the preferred UI.
- New files:
  - `src/quantum_trainer/web_api.py`
  - `scripts/run_web_app.py`
  - `tests/test_web_api.py`
  - `web/package.json`
  - `web/package-lock.json`
  - `web/index.html`
  - `web/vite.config.js`
  - `web/src/main.jsx`
  - `web/src/styles.css`
- Changed:
  - `requirements.txt` now includes `fastapi`, `uvicorn`, and `httpx`.
  - `.gitignore` excludes `web/node_modules/` and `web/dist/`.
  - `README.md` and `AGENTS.md` document the new app flow.
- Result:
  - FastAPI app runs at `http://127.0.0.1:8766`.
  - `/api/status` returns top candidate, latest price date, universe coverage, performance tracking, and fixed `NO_ORDER` state.
  - `/api/analyze` defaults to cached/local analysis and does not request external price refresh unless `refresh_market_data=true`.
  - React app is built with Vite and served from FastAPI.
- Verification:
  - `.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt` -> installed FastAPI stack.
  - `npm.cmd install` under `web/` -> installed React/Vite stack.
  - `npm.cmd run build` under `web/` -> build passed.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_web_api.py .\tests\test_local_app.py -q` -> `5 passed`.
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\web_api.py .\scripts\run_web_app.py` -> passed.
  - `curl.exe http://127.0.0.1:8766/health` -> `{"status":"OK"}`.
  - `curl.exe http://127.0.0.1:8766/api/status` -> `completion_status=DONE`, `top_candidate=003550.KS`, `order_status=NO_ORDER`.

## 2026-05-28 - Approved Price Refresh And Investment Tracking

- Ran the approved latest-price refresh path through the today pipeline.
- Result:
  - `data/prices.csv` updated to latest date `2026-05-28`.
  - Price cache now has 583 rows and 35 symbols.
  - Universe coverage is `PASS_CANDIDATE`, count `35`, price coverage `PRICE_COVERAGE_READY`.
  - Current top focus remains `003550.KS` LG, `decision_status=BUY_READY`, `order_status=NO_ORDER`.
  - Samsung C&T remains a watch/risk candidate after refresh: `WAIT_RISK` because of drawdown risk.
  - Operating status is `DONE`; broker order remains manual outside this repo.
- Added post-buy tracking:
  - `src/quantum_trainer/investment_tracking.py`
  - `scripts/run_investment_tracking.py`
  - `tests/test_investment_tracking.py`
  - `configs/trade_journal.example.csv`
- Changed:
  - `src/quantum_trainer/today_pipeline.py` now runs `investment_tracking` before operating status.
  - `src/quantum_trainer/dashboard.py` now shows `투자 후 성과 추적`.
  - `README.md` and `AGENTS.md` document the manual trade journal flow.
- Verification:
  - `.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py --refresh-market-data` -> 24 steps, `external_api_requested=YES`, `order_status=NO_ORDER`.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_today_pipeline.py .\tests\test_dashboard.py .\tests\test_investment_tracking.py -q` -> `13 passed`.
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\investment_tracking.py .\src\quantum_trainer\today_pipeline.py .\src\quantum_trainer\dashboard.py .\scripts\run_investment_tracking.py` -> passed.
  - `.\.venv\Scripts\python.exe .\scripts\run_investment_tracking.py` -> `tracked_positions=0`, `order_status=NO_ORDER`.
  - Dashboard regenerated with the performance tracking section.

## 2026-05-28 - Dashboard Status Wording Cleanup

- Made dashboard status text more natural for ordinary Korean users.
- Changed files:
  - `src/quantum_trainer/dashboard.py`
  - `tests/test_dashboard.py`
  - `docs/work-log.md`
- Result:
  - Raw technical fragments such as `manual gate`, `actual_config_written`, `conviction_score`, `upside_probability`, `order_status=`, and `missing cached price history` are translated before rendering.
  - Common English company names in the dashboard are displayed as Korean names when known.
  - Existing local web app can show the refreshed `reports/dashboard/index.html`; no order path or external data call was added.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_dashboard.py -q` -> `1 passed`.
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\dashboard.py` -> passed.
  - `.\.venv\Scripts\python.exe .\scripts\run_dashboard.py --reports-dir .\reports` -> regenerated dashboard, `order_status=NO_ORDER`.
  - `rg "manual gate|actual_config_written|conviction_score|upside_probability|order_status=|fatal filing risk|thesis break|missing cached price history|BUY_READY candidate|SMA20 holds|no new filing" .\reports\dashboard\index.html` -> no matches.

## 2026-05-28 - Local Web App

- Added a simple Korean local web app for the user flow: stock input, today analysis, and dashboard view.
- New files:
  - `src/quantum_trainer/local_app.py`
  - `scripts/app.py`
  - `tests/test_local_app.py`
- Result:
  - `.\.venv\Scripts\python.exe .\scripts\app.py` starts the app at `http://127.0.0.1:8765`.
  - The first screen shows `종목 입력`, `오늘 분석 실행`, `오늘 결론 보기`, and `주문 실행 없음`.
  - Default analysis uses the local cached pipeline; `최신 가격 갱신` is an explicit external-data checkbox.
  - No broker/order execution was added.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_local_app.py .\tests\test_today_command.py -q` -> `5 passed`.
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\local_app.py .\scripts\app.py` -> passed.

## 2026-05-28 - One Command Today Analysis

- Added a user-facing one-command wrapper for the full local today analysis flow.
- New files:
  - `src/quantum_trainer/today_command.py`
  - `scripts/today.py`
  - `tests/test_today_command.py`
- Result:
  - `.\.venv\Scripts\python.exe .\scripts\today.py` runs the local today pipeline and prints a short Korean summary.
  - `.\.venv\Scripts\python.exe .\scripts\today.py 삼성전자` adds the easy stock input and runs the same local analysis flow.
  - `--dry-run` previews the steps without rewriting reports.
  - `--refresh-market-data` is still explicit and remains the external price refresh path.
  - Output always states `주문 실행: 안함`; no broker/order execution was added.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_today_command.py .\tests\test_today_pipeline.py -q` -> `12 passed`.

## 2026-05-28 - Easy Stock Input

- Added an easy local stock intake path for ordinary user input such as `삼성전자`, `현대차`, `005930`, and `005930.KS`.
- New files:
  - `src/quantum_trainer/symbol_input.py`
  - `scripts/add_stock.py`
  - `tests/test_symbol_input.py`
- Changed files:
  - `src/quantum_trainer/today_pipeline.py`
  - `scripts/run_today_pipeline.py`
  - `tests/test_today_pipeline.py`
  - `README.md`
  - `AGENTS.md`
- Result:
  - `run_today_pipeline.py --add-stock 삼성전자 --dry-run` resolves to `005930`, `삼성전자`, `KOSPI`, `반도체`.
  - Unknown names do not trigger external lookup; they ask for a 6-digit KRX code.
  - No broker order path was added and generated order fields remain review-only/`NO_ORDER`.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_symbol_input.py .\tests\test_today_pipeline.py -q` -> `16 passed`.
  - `.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py --add-stock 삼성전자 --dry-run` -> `external_api_requested=NO`, `symbol_intake_requested=YES`.
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\symbol_input.py .\src\quantum_trainer\today_pipeline.py .\scripts\add_stock.py .\scripts\run_today_pipeline.py`

## 2026-05-28

- Applied the user-confirmed 3,000,000 KRW review capital input.
- Changed files:
  - `configs/capital.actual.csv`
  - `docs/work-log.md`
- Result:
  - Today pipeline can now use the actual capital amount automatically for capital plan review and review-only order sizing.
  - This does not place orders and must keep `order_status=NO_ORDER`.
- Verification:
  - `.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py` -> 22 local steps, `external_api_requested=NO`.
  - Operating status is now `DONE`, top symbol `003550.KS`, `decision_status=BUY_READY`, `decision_gate_status=READY_FOR_SIZING_REVIEW`.
  - Order candidate remains `REVIEW_ONLY` / `MANUAL_REVIEW_ONLY`: 5 shares, estimated value 582,500 KRW, `order_status=NO_ORDER`.

- Added persistent local capital input support so the final capital blocker can be cleared without repeating the CLI amount.
- Changed files:
  - `src/quantum_trainer/capital_config.py`
  - `configs/capital.example.csv`
  - `src/quantum_trainer/today_pipeline.py`
  - `tests/test_capital_config.py`
  - `tests/test_today_pipeline.py`
  - `README.md`
  - `AGENTS.md`
- Result:
  - `run_today_pipeline.py` reads `configs/capital.actual.csv` automatically when it exists and passes `total_capital_krw` to capital plan review and review-only order sizing.
  - `--total-capital-krw` still overrides the CSV.
  - No actual capital file was created and no order path was added; order output remains review-only/`NO_ORDER`.

- Unblocked the manual review gate and added a safe capital input path for the final blocker.
- Changed files:
  - `src/quantum_trainer/capital_plan_review.py`
  - `scripts/run_capital_plan_review.py`
  - `src/quantum_trainer/manual_review_apply_plan.py`
  - `src/quantum_trainer/today_pipeline.py`
  - `scripts/run_today_pipeline.py`
  - `src/quantum_trainer/operating_status.py`
  - `tests/test_capital_plan_review.py`
  - `tests/test_manual_review_apply_plan.py`
  - `tests/test_today_pipeline.py`
  - `tests/test_operating_status.py`
  - `README.md`
  - `AGENTS.md`
- Result:
  - `configs/manual_review.actual.csv` was created from the confirmed proposal for `003550.KS`; decision gate is now `READY_FOR_SIZING_REVIEW`, still `NO_ORDER`.
  - `run_today_pipeline.py` now automatically uses existing `configs/manual_review.actual.csv`.
  - `--total-capital-krw` is now passed into capital plan review and order sizing so the remaining capital blocker can be cleared only when the user provides an actual amount.
  - Existing actual manual review config is recognized as `apply_mode=EXISTING_ACTUAL`.
- Current blocker:
  - Operating status is still `NOT_DONE` until actual total capital is provided; current remaining blocker is `capital amount required`.
- Verification:
  - RED confirmed missing total capital args, missing existing actual recognition, and manual approval note counted as blocker.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_manual_review_apply_plan.py .\tests\test_today_pipeline.py .\tests\test_capital_plan_review.py .\tests\test_operating_status.py -q` -> `16 passed`.
  - `.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py --dry-run --total-capital-krw 3000000` -> planned `--manual-review-csv configs\manual_review.actual.csv`, capital plan amount, and order sizing amount; `external_api_requested=NO`.

- Added the final operating status report so the system explicitly says `DONE` or `NOT_DONE` instead of leaving the next action implicit.
- Changed files:
  - `src/quantum_trainer/operating_status.py`
  - `scripts/run_operating_status.py`
  - `src/quantum_trainer/today_pipeline.py`
  - `src/quantum_trainer/dashboard.py`
  - `tests/test_operating_status.py`
  - `tests/test_today_pipeline.py`
  - `tests/test_dashboard.py`
  - `README.md`
  - `AGENTS.md`
- Result:
  - `run_operating_status.py` writes `reports/operating_status/operating_status.csv|md`.
  - Today pipeline now runs `operating_status` after capital scenarios and before dashboard.
  - Dashboard shows `Operating Status` with `DONE`/`NOT_DONE`, blockers, next step, and `NO_ORDER`.
- Verification:
  - RED confirmed: missing `quantum_trainer.operating_status`.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_operating_status.py .\tests\test_today_pipeline.py .\tests\test_dashboard.py -q` -> `9 passed`.

- Added a local universe coverage gate so Samsung C&T or any user-added company is compared inside a broad enough universe before ranking.
- Changed files:
  - `src/quantum_trainer/universe_coverage.py`
  - `scripts/run_universe_coverage.py`
  - `src/quantum_trainer/today_pipeline.py`
  - `src/quantum_trainer/dashboard.py`
  - `tests/test_universe_coverage.py`
  - `tests/test_today_pipeline.py`
  - `tests/test_dashboard.py`
  - `README.md`
  - `AGENTS.md`
- Result:
  - `run_universe_coverage.py` writes `reports/universe_coverage/universe_coverage.csv|md`.
  - Today pipeline runs `universe_coverage` before company research.
  - Dashboard shows `Universe Coverage` with count, missing required symbols, cached price blockers, and `NO_ORDER`.
- Verification:
  - RED confirmed: missing `quantum_trainer.universe_coverage`, missing pipeline step, and missing dashboard summary/section.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_universe_coverage.py .\tests\test_today_pipeline.py .\tests\test_dashboard.py -q` -> `9 passed`.

- Added batch company intake so a CSV of companies can be added and checked in one local workflow.
- Changed files:
  - `src/quantum_trainer/research_universe.py`
  - `src/quantum_trainer/symbol_analysis.py`
  - `scripts/add_research_symbols.py`
  - `scripts/run_symbol_batch_analysis.py`
  - `src/quantum_trainer/today_pipeline.py`
  - `scripts/run_today_pipeline.py`
  - `tests/test_research_universe.py`
  - `tests/test_symbol_analysis.py`
  - `tests/test_today_pipeline.py`
  - `README.md`
  - `AGENTS.md`
- Result:
  - Batch CSV additions preserve existing universe order, append new symbols, and optionally update existing rows with `--replace`.
  - Batch intake writes `reports/symbol_analysis/symbol_analysis_batch.csv|md` with `ANALYSIS_READY` or `DATA_REQUIRED` per symbol.
  - Today pipeline supports `--add-symbols-csv` before optional market refresh and creates `symbol_batch_analysis_intake` before dashboard.
- Verification:
  - RED confirmed: missing `add_research_symbols_from_csv`, missing `run_symbol_batch_analysis`, and missing `add_symbols_csv` pipeline argument.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_research_universe.py .\tests\test_symbol_analysis.py .\tests\test_today_pipeline.py -q` -> `16 passed`.

- Added optional single-company intake to the today pipeline.
- Changed files:
  - `src/quantum_trainer/today_pipeline.py`
  - `scripts/run_today_pipeline.py`
  - `tests/test_today_pipeline.py`
  - `README.md`
  - `AGENTS.md`
- Result:
  - `run_today_pipeline.py --add-code ...` first runs a local universe add step.
  - If `--refresh-market-data` is approved, the newly added company is already in the universe before the external price refresh step.
  - The pipeline creates `symbol_analysis_intake` before dashboard and keeps `order_status=NO_ORDER`.
- Verification:
  - RED confirmed: `run_today_pipeline()` rejected `add_code`.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_today_pipeline.py -q` -> `5 passed`.

- Added Symbol Analysis Intake to the dashboard so user-added companies are visible beside the normal universe workflow.
- Changed files:
  - `src/quantum_trainer/dashboard.py`
  - `tests/test_dashboard.py`
  - `README.md`
  - `AGENTS.md`
- Result:
  - Dashboard reads `reports/symbol_analysis/*.csv` when present.
  - It shows `ANALYSIS_READY` and `DATA_REQUIRED` rows, cached price status, blockers, and `NO_ORDER`.
  - No pipeline step fetches missing prices automatically; missing data remains an approval-gated refresh decision.
- Verification:
  - RED confirmed: dashboard summary lacked `symbol_analysis_count`.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_dashboard.py -q` -> `1 passed`.

- Added a single-symbol analysis intake so any KRX company can be added and checked against local cached price data before the full ranking workflow.
- Changed files:
  - `src/quantum_trainer/symbol_analysis.py`
  - `scripts/run_symbol_analysis.py`
  - `tests/test_symbol_analysis.py`
  - `README.md`
  - `AGENTS.md`
- Result:
  - Cached-price symbols produce `ANALYSIS_READY` and link to generated company research.
  - Missing-price symbols produce `DATA_REQUIRED` with `order_status=NO_ORDER` and `external_api_requested=NO`.
  - The command can update `configs/research_universe.actual.csv`, but it does not call price/OpenDART APIs or apply manual-review PASS values.
- Verification:
  - RED confirmed: missing `quantum_trainer.symbol_analysis` import failed before implementation.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_symbol_analysis.py -q` -> `2 passed`.

- Added a one-company research-universe input path so any KRX company can be added before the same local ranking pipeline is rerun.
- Changed files:
  - `src/quantum_trainer/research_universe.py`
  - `scripts/add_research_symbol.py`
  - `tests/test_research_universe.py`
  - `README.md`
  - `AGENTS.md`
- Result:
  - `add_research_symbol()` appends a normalized `006800.KS`-style row without reordering existing universe rows.
  - `--replace` updates an existing row without duplication.
  - The command prints `external_api_requested=NO`; price/OpenDART refresh and manual-review PASS application remain separate approval-gated steps.
- Verification:
  - RED confirmed: missing `add_research_symbol` import failed before implementation.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_research_universe.py -q` -> `5 passed`.

- Added capital scenario planning so irregular future capital can be reviewed without placing orders.
- 추가 파일:
  - `src/quantum_trainer/capital_scenario.py`
  - `scripts/run_capital_scenarios.py`
  - `tests/test_capital_scenario.py`
- 변경:
  - `src/quantum_trainer/today_pipeline.py`가 no-capital `order_sizer` 다음 `capital_scenarios`를 실행한다.
  - `src/quantum_trainer/dashboard.py`에 `Capital Scenarios` 섹션과 `capital_scenarios.md` 링크를 추가했다.
  - `README.md`, `AGENTS.md`에 capital scenarios는 가정 자본금별 계획표이며 `order_status=NO_ORDER`를 유지한다고 명시했다.
- 결과:
  - 최신 local pipeline은 20 steps, external_api_requested=`NO`.
  - LG 시나리오: 100만원은 첫 tranche 0주라 `INSUFFICIENT_FOR_FIRST_TRANCHE`; 300만원은 첫 tranche 1주/목표 3주, 500만원은 1주/6주, 1000만원은 3주/12주로 `SCENARIO_REVIEW_ONLY`.
  - 실제 주문/브로커 API 호출과 `configs/manual_review.actual.csv` 수정은 실행하지 않았다.
- 검증:
  - RED 확인: capital scenario module 없음, pipeline 단계 없음, dashboard 섹션 없음 실패 확인.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_capital_scenario.py .\tests\test_today_pipeline.py .\tests\test_dashboard.py -q` -> `6 passed`.
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\capital_scenario.py .\src\quantum_trainer\today_pipeline.py .\src\quantum_trainer\dashboard.py .\scripts\run_capital_scenarios.py` -> 통과.
  - `.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py` -> 20 local steps 완료.

- Added a guarded manual-review apply plan so the final PASS handoff is auditable before actual config is written.
- 추가 파일:
  - `src/quantum_trainer/manual_review_apply_plan.py`
  - `scripts/run_manual_review_apply_plan.py`
  - `tests/test_manual_review_apply_plan.py`
- 변경:
  - `src/quantum_trainer/today_pipeline.py`가 `manual_review_proposal` 직후 `manual_review_apply_plan` dry-run 단계를 실행한다.
  - `src/quantum_trainer/dashboard.py`에 `Manual Review Apply Plan` 섹션과 `manual_review_apply_plan.md` 링크를 추가했다.
  - `README.md`, `AGENTS.md`에 기본은 `actual_config_written=NO`이며 confirmed token 없이는 `configs/manual_review.actual.csv`를 쓰지 않는다고 명시했다.
- 결과:
  - 최신 local pipeline은 19 steps, external_api_requested=`NO`.
  - LG apply plan은 `apply_mode=DRY_RUN`, `ready_to_apply=YES`, `actual_config_written=NO`, blocker=`waiting for explicit user confirmation`.
  - `reports/decision_gate/manual_review_actual_candidate.csv`는 생성됐지만, `configs/manual_review.actual.csv`는 생성/수정하지 않았다.
- 검증:
  - RED 확인: apply plan module 없음, pipeline 단계 없음, dashboard 섹션 없음 실패 확인.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_manual_review_apply_plan.py .\tests\test_today_pipeline.py .\tests\test_dashboard.py -q` -> `7 passed`.
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\manual_review_apply_plan.py .\src\quantum_trainer\today_pipeline.py .\src\quantum_trainer\dashboard.py .\scripts\run_manual_review_apply_plan.py` -> 통과.
  - `.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py` -> 19 local steps 완료.

- Strengthened the pre-buy report so it explains the last blockers before any order.
- 변경:
  - `src/quantum_trainer/pre_buy_decision.py`가 manual proposal과 capital plan을 읽어 `final_action`, `manual_proposal_status`, `capital_status`, `readiness_blockers`를 출력한다.
  - `scripts/run_pre_buy_decision.py`에 `--manual-proposal-csv`, `--capital-plan-dir` 옵션을 추가했다.
  - `src/quantum_trainer/today_pipeline.py`가 pre-buy 단계에 proposal/capital plan 경로를 넘긴다.
  - `src/quantum_trainer/dashboard.py`가 pre-buy 섹션에서 최종 action, proposal, capital blocker를 표시한다.
- 결과:
  - 최신 LG pre-buy row는 `decision_status=WAIT`, `final_action=NO_ORDER`, `manual_proposal_status=READY_FOR_USER_CONFIRMATION`, `capital_status=CAPITAL_AMOUNT_REQUIRED`.
  - `readiness_blockers=actual manual review config not applied; capital amount required`.
  - 실제 주문/브로커 API 호출과 `configs/manual_review.actual.csv` 수정은 실행하지 않았다.
- 검증:
  - RED 확인: pre-buy proposal/capital 인자 없음, pipeline 인자 없음, dashboard blocker 표시 없음 실패 확인.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_pre_buy_decision.py .\tests\test_today_pipeline.py .\tests\test_dashboard.py -q` -> `7 passed`.
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\pre_buy_decision.py .\src\quantum_trainer\today_pipeline.py .\src\quantum_trainer\dashboard.py .\scripts\run_pre_buy_decision.py` -> 통과.
  - `.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py` -> 18 local steps 완료, external_api_requested=`NO`.

- Added a manual-review proposal stage between draft evidence and the actual decision gate.
- 추가 파일:
  - `src/quantum_trainer/manual_review_proposal.py`
  - `scripts/run_manual_review_proposal.py`
  - `tests/test_manual_review_proposal.py`
- 변경:
  - `src/quantum_trainer/today_pipeline.py`가 `manual_review_draft` 직후 `manual_review_proposal`을 실행한다.
  - `src/quantum_trainer/dashboard.py`에 `Manual Review Proposal` 섹션과 `manual_review_proposal.md` 링크를 추가했다.
  - `README.md`, `AGENTS.md`에 proposal은 actual config가 아니며 사용자 확인 전 `configs/manual_review.actual.csv`에 반영하지 않는다고 명시했다.
- 결과:
  - 최신 local pipeline은 18 steps, external_api_requested=`NO`.
  - LG proposal은 6개 항목 `PASS`, `proposal_status=READY_FOR_USER_CONFIRMATION`, `approval_required=YES`.
  - `configs/manual_review.actual.csv`는 생성/수정하지 않았고, decision gate는 `WAITING_MANUAL_EVIDENCE`, order는 `NO_ORDER` 유지.
- 검증:
  - RED 확인: pipeline proposal 단계 없음, dashboard proposal 섹션 없음 실패 확인.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_manual_review_proposal.py .\tests\test_today_pipeline.py .\tests\test_dashboard.py -q` -> `7 passed`.
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\manual_review_proposal.py .\src\quantum_trainer\today_pipeline.py .\src\quantum_trainer\dashboard.py .\scripts\run_manual_review_proposal.py` -> 통과.
  - `.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py` -> 18 local steps 완료.

- Added generic capital-plan review so the last manual draft field no longer stays hard-coded `UNKNOWN`.
- 추가 파일:
  - `src/quantum_trainer/capital_plan_review.py`
  - `scripts/run_capital_plan_review.py`
  - `tests/test_capital_plan_review.py`
- 변경:
  - `src/quantum_trainer/manual_review_draft.py`가 `capital_plan_review_<code>.csv`를 읽어 `capital_plan_review=PASS_CANDIDATE`를 evidence candidate로 반영한다.
  - `src/quantum_trainer/today_pipeline.py`가 `investment_memo` 다음 `capital_plan_review`, 그 다음 최신 `filing_risk_summary_*`, 그 다음 `manual_review_draft` 순서로 실행된다.
  - `src/quantum_trainer/dashboard.py`에 `Capital Plan Review` 섹션과 `capital_plan_review.md` 링크를 추가했다.
  - `README.md`, `AGENTS.md`에 새 자금 계획 리포트와 수동 draft 의미를 반영했다.
- 결과:
  - 최신 local pipeline은 17 steps, external_api_requested=`NO`.
  - LG `capital_plan_review=PASS_CANDIDATE`, `amount_status=CAPITAL_AMOUNT_REQUIRED`, `order_status=NO_ORDER`.
  - LG manual review draft 6개 항목은 모두 `PASS_CANDIDATE` 후보가 됐지만, 실제 `configs/manual_review.actual.csv`는 수정하지 않았다.
  - 실제 주문/브로커 API 호출은 실행하지 않았다.
- 검증:
  - RED 확인 후 구현: capital plan module 없음, manual draft capital-plan 인자 없음, dashboard capital plan 섹션 없음, filing summary 순서가 manual draft보다 늦는 실패 확인.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_capital_plan_review.py .\tests\test_manual_review_draft.py .\tests\test_dashboard.py .\tests\test_today_pipeline.py -q` -> `8 passed`.
  - `.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py` -> 17 local steps 완료.

- Extended the generic quant trainer path beyond Samsung C&T and executed the approved LG filing calls/order-candidate step.
- 실행:
  - `fetch_opendart_filing_review.py --symbol 003550.KS --begin-date 20260101 --end-date 20260528` -> LG 공시 45건, filing-review draft 생성.
  - `fetch_opendart_text_risk_scan.py --symbol 003550.KS --max-documents 2` -> 원문 2건, evidence 32건 생성.
  - `run_today_pipeline.py` -> local 15 steps 완료, top symbol `003550.KS`, decision gate `WAITING_MANUAL_EVIDENCE`, `NO_ORDER`.
  - `run_order_sizer.py` without total capital -> `reports/orders/order_candidates.csv|md`, LG row `BLOCKED_CAPITAL_REQUIRED`, shares 0.
  - 최종 `run_today_pipeline.py` -> local 16 steps 완료, `order_sizer` 포함, external_api_requested=`NO`.
- 변경:
  - `src/quantum_trainer/filing_risk_summary.py`가 `028260.KS` 외 종목에는 삼성바이오/건설 전용 risk title/id를 쓰지 않고 generic regulatory/project risk로 요약하도록 수정했다.
  - `src/quantum_trainer/order_sizer.py`와 `scripts/run_order_sizer.py`가 총투자금 생략 시 자본금 필요 상태의 zero-share 후보표를 생성하도록 수정했다.
  - `src/quantum_trainer/dashboard.py`에 `Order Candidates` 섹션과 `order_candidates.md` 링크를 추가했다.
  - `src/quantum_trainer/today_pipeline.py`가 `pre_buy_decision` 다음, `dashboard` 전에 no-capital `order_sizer` 단계를 실행하도록 연결했다.
  - `README.md`, `AGENTS.md`에 no-capital order candidate 동작을 반영했다.
- 결과:
  - LG manual review draft: `filing_review=PASS_CANDIDATE`, `earnings_review=PASS_CANDIDATE`, `business_driver_review=PASS_CANDIDATE`, `valuation_review=PASS_CANDIDATE`, `loss_rule_review=PASS_CANDIDATE`, `capital_plan_review=UNKNOWN`.
  - `configs/manual_review.actual.csv`는 수정하지 않았다.
  - 실제 증권사 주문/브로커 API 호출은 실행하지 않았다.
- 검증:
  - RED 확인 후 구현: non-Samsung filing summary에서 삼성물산 전용 title/id가 남는 실패, no-capital order sizing 실패, dashboard order candidate 섹션 없음 실패.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_filing_risk_summary.py .\tests\test_order_sizer.py .\tests\test_dashboard.py .\tests\test_today_pipeline.py -q` -> `9 passed`.
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\filing_risk_summary.py .\src\quantum_trainer\order_sizer.py .\src\quantum_trainer\dashboard.py .\scripts\run_order_sizer.py` -> 통과.

- Added generic manual-review draft generation for whichever company becomes the current core candidate.
- 추가 파일:
  - `src/quantum_trainer/manual_review_draft.py`
  - `scripts/run_manual_review_draft.py`
  - `tests/test_manual_review_draft.py`
  - `reports/decision_gate/manual_review_draft.csv`
  - `reports/decision_gate/manual_review_draft.md`
  - `reports/decision_gate/manual_review_draft_003550.csv`
  - `reports/decision_gate/manual_review_draft_003550.md`
- 변경 파일:
  - `src/quantum_trainer/today_pipeline.py`
  - `src/quantum_trainer/dashboard.py`
  - `tests/test_today_pipeline.py`
  - `tests/test_dashboard.py`
  - `reports/dashboard/index.html`
  - `README.md`
  - `AGENTS.md`
- 결과:
  - `run_today_pipeline.py`에 `manual_review_draft` 로컬 단계가 `investment_memo` 다음, `decision_gate` 전에 포함됐다.
  - 현재 `003550.KS` LG Corp draft: `filing_review=UNKNOWN`, `earnings_review=PASS_CANDIDATE`, `business_driver_review=PASS_CANDIDATE`, `valuation_review=PASS_CANDIDATE`, `loss_rule_review=PASS_CANDIDATE`, `capital_plan_review=UNKNOWN`.
  - dashboard에 `Manual Review Draft` 섹션을 추가했다.
  - draft 값은 실제 `PASS`가 아니며 `configs/manual_review.actual.csv`는 수정하지 않았다.
- 검증:
  - RED: manual review draft 모듈 없음, dashboard 섹션 없음, pipeline 단계 없음 실패 확인 후 구현.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_manual_review_draft.py .\tests\test_dashboard.py .\tests\test_today_pipeline.py -q` -> `6 passed`.
  - `.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py` -> 14 local steps 완료, external_api_requested=`NO`.

- Removed a downstream candidate bottleneck in the research filter.
- 문제:
  - `research_filter --top-n 5`가 점수 상위 5개를 먼저 자른 뒤 status를 계산해, 6위 이하의 `PRIORITY_RESEARCH` 후보가 브리프/checklist로 내려가지 못할 수 있었다.
- 변경:
  - `src/quantum_trainer/research_filter.py`가 전체 universe에 먼저 `filter_status`를 계산한 뒤, 상위 `top_n` row와 모든 `PRIORITY_RESEARCH` row를 함께 보존하도록 수정했다.
  - `tests/test_research_filter.py`에 6위 priority 후보 보존 회귀 테스트를 추가했다.
  - `README.md`, `AGENTS.md`에 `--top-n`은 watchlist cap이며 priority 후보 hard cap이 아니라고 명시했다.
- 결과:
  - 최신 캐시 기준 local pipeline 재실행 완료.
  - `003550.KS` LG Corp가 `PRIORITY_RESEARCH`로 candidate brief/checklist까지 내려갔다.
  - 현재 `profit_focus`: `003550.KS` CORE_FOCUS, `028260.KS` WAIT_RISK, `005930.KS` WAIT_RISK.
  - 현재 dashboard top symbol: `003550.KS`, decision gate `WAITING_MANUAL_EVIDENCE`, order status `NO_ORDER`.
- 검증:
  - RED: `003550.KS`가 `top_n=5` 밖 priority 후보일 때 누락되는 실패 확인.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_research_filter.py .\tests\test_candidate_brief.py .\tests\test_today_pipeline.py -q` -> `7 passed`.
  - `.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py` -> 13 local steps 완료, external_api_requested=`NO`.

- Approved market refresh was executed for the full research universe.
- 실행:
  - `.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py --refresh-market-data`
  - Yahoo 가격 캐시 갱신 완료: 35 symbols, 583 rows, last date `2026-05-28`.
  - valuation metrics 재계산 후 company research/universe analysis 등 로컬 단계가 재생성됐다.
- 중간 이슈와 수정:
  - 최신 데이터 기준 `CORE_FOCUS`가 0개가 되면서 `investment_memo.csv`가 헤더 없는 빈 파일로 생성되고 `decision_gate`가 `EmptyDataError`로 중단됐다.
  - `src/quantum_trainer/investment_memo.py`가 후보 0개일 때도 표준 컬럼 헤더를 가진 빈 CSV를 쓰도록 수정했다.
  - `tests/test_investment_memo.py`에 no-core 후보 회귀 테스트를 추가했다.
- 최종 결과:
  - 외부 호출 없이 `.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py`를 재실행해 13개 로컬 단계 완료.
  - 현재 `profit_focus`: `028260.KS` WAIT_RISK, `005930.KS` WAIT_RISK, `003550.KS` NEEDS_CHECKLIST.
  - 현재 `investment_memo`: memo_count 0, `decision_gate`: row_count 0, `pre_buy_decision`: 3개 모두 `WAIT / NO_ORDER`.
  - 현재 `universe_stock_analysis`: 35개 종목, `BUY_READY` 1개, `WAIT` 4개, `REJECT` 30개.
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_investment_memo.py .\tests\test_decision_gate.py -q` -> `4 passed`.

- Added universe-wide stock analysis so the trainer no longer depends on Samsung C&T as the only visible decision target.
- 추가 파일:
  - `src/quantum_trainer/universe_stock_analysis.py`
  - `scripts/run_universe_stock_analysis.py`
  - `tests/test_universe_stock_analysis.py`
  - `reports/universe_stock_analysis/universe_stock_analysis.csv`
  - `reports/universe_stock_analysis/universe_stock_analysis.md`
- 변경 파일:
  - `src/quantum_trainer/dashboard.py`
  - `src/quantum_trainer/today_pipeline.py`
  - `tests/test_dashboard.py`
  - `tests/test_today_pipeline.py`
  - `reports/dashboard/index.html`
  - `README.md`
  - `AGENTS.md`
- 결과:
  - `company_research.csv`의 모든 종목을 같은 price trend, alpha, valuation, risk 규칙으로 `BUY_READY / WAIT / REJECT`로 재분석한다.
  - 모든 행은 `order_status=NO_ORDER`를 유지한다.
  - 현재 로컬 리포트 기준 35개 종목 분석: `BUY_READY` 2개, `WAIT` 6개, `REJECT` 27개.
  - dashboard에 `Universe Stock Analysis`와 `전체 분석 종목 35개` 섹션을 추가했다.
  - `run_today_pipeline.py --dry-run`에 `universe_stock_analysis` 로컬 단계가 `company_research` 직후 포함된다.
- 검증:
  - RED: 신규 모듈 없음, dashboard 섹션 없음, pipeline 단계 없음 실패 확인 후 구현.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_universe_stock_analysis.py .\tests\test_dashboard.py .\tests\test_today_pipeline.py -q` -> `6 passed`.
  - `.\.venv\Scripts\python.exe .\scripts\run_universe_stock_analysis.py ...` -> 35 rows 생성.
  - `.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py --dry-run` -> external_api_requested=`NO`, `universe_stock_analysis` 단계 확인.

- Added pre-buy decision report workflow after the filing risk/dashboard work.
- 추가 파일:
  - `src/quantum_trainer/pre_buy_decision.py`
  - `scripts/run_pre_buy_decision.py`
  - `tests/test_pre_buy_decision.py`
  - `reports/pre_buy_decision/pre_buy_decision.csv`
  - `reports/pre_buy_decision/pre_buy_decision.md`
- 변경 파일:
  - `src/quantum_trainer/dashboard.py`
  - `src/quantum_trainer/today_pipeline.py`
  - `tests/test_dashboard.py`
  - `tests/test_today_pipeline.py`
  - `reports/dashboard/index.html`
  - `AGENTS.md`
- 결과:
  - `run_pre_buy_decision.py`는 기존 local reports만 읽고 `BUY_READY / WAIT / REJECT` 판단과 `NO_ORDER` 주문 상태를 생성한다.
  - 현재 3개 후보 모두 `WAIT / NO_ORDER`: 삼성물산은 manual gate 미완료와 20D 상승 과열, LG는 checklist 없음, 삼성전자는 manual gate 미완료와 valuation 부담.
  - 삼성물산 진입 밴드는 386,000-410,500원, first tranche 30%, -7% 축소/-10% 제외 검토 규칙으로 표시된다.
  - `run_today_pipeline.py --dry-run`에 `pre_buy_decision` 로컬 단계가 dashboard 직전에 포함된다.
  - dashboard에 `Pre-Buy Decision` 섹션과 `pre_buy_decision.md` 링크를 추가했다.
- 검증:
  - RED: `pre_buy_decision` 모듈 없음, dashboard 섹션 없음, pipeline 단계 없음 실패 확인 후 구현.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_pre_buy_decision.py .\tests\test_dashboard.py .\tests\test_today_pipeline.py -q` -> `7 passed`.
  - `.\.venv\Scripts\python.exe .\scripts\run_pre_buy_decision.py ...` -> 보고서 생성, `WAIT / NO_ORDER` 확인.
  - `.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py --dry-run` -> external_api_requested=`NO`, `pre_buy_decision` 단계 확인.

- OpenDART 공시 리스크 32개 evidence를 5개 핵심 리스크로 압축하는 로컬 요약 workflow를 추가했다.
- 추가 파일:
  - `src/quantum_trainer/filing_risk_summary.py`
  - `scripts/run_filing_risk_summary.py`
  - `tests/test_filing_risk_summary.py`
  - `reports/filing_review/filing_risk_summary_028260.csv`
  - `reports/filing_review/filing_risk_summary_028260.md`
  - `reports/investment_memo/investment_thesis_028260.md`
  - `reports/decision_gate/capital_plan_review_028260.md`
- 변경 파일:
  - `src/quantum_trainer/dashboard.py`
  - `src/quantum_trainer/today_pipeline.py`
  - `tests/test_dashboard.py`
  - `tests/test_today_pipeline.py`
  - `reports/dashboard/index.html`
  - `reports/decision_gate/manual_review_draft_028260.csv`
  - `reports/decision_gate/manual_review_draft_028260.md`
- 결과:
  - `filing_risk_summary_028260` 전체 의견은 `PASS_CANDIDATE_WITH_MONITORING`, fatal risk count는 0.
  - 핵심 리스크 5개: 법적 소송 노출, 삼성바이오로직스 회계처리 소송 overhang, 파생/원자재 hedge 약정, 복잡한 계열/특수관계 구조, 건설 수주/프로젝트 수익성.
  - dashboard에 `Filing Risk Summary` 섹션과 1순위 후보 옆 `공시 리스크: PASS_CANDIDATE_WITH_MONITORING` 표시를 추가했다.
  - `run_today_pipeline.py --dry-run`에서 기존 scan CSV가 있으면 `filing_risk_summary_028260` 로컬 단계가 dashboard 전 단계에 포함된다.
  - `investment_thesis_028260.md`는 현재 결론을 `WAIT / NO_ORDER`로 유지하고, 수동 6개 gate가 승인될 때만 sizing review 후보로 넘기도록 정리했다.
  - `capital_plan_review_028260.md`에 한 종목 최대 15%, 첫 매수 목표 포지션 30%, 현금 버퍼 25%, -7% 축소/-10% 제외 검토 규칙을 확정했다.
- 검증:
  - RED 확인 후 구현: `test_filing_risk_summary.py`, `test_dashboard.py`, `test_today_pipeline.py`에서 신규 기대 동작 실패 확인.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_filing_risk_summary.py .\tests\test_dashboard.py .\tests\test_today_pipeline.py -q` -> `6 passed`.
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\filing_risk_summary.py .\src\quantum_trainer\dashboard.py .\src\quantum_trainer\today_pipeline.py .\scripts\run_filing_risk_summary.py` -> 통과.
  - `rg -n "Filing Risk Summary|공시 리스크: PASS_CANDIDATE_WITH_MONITORING" .\reports\dashboard\index.html` -> 두 문구 확인.
- 주의:
  - `configs/manual_review.actual.csv`는 만들거나 수정하지 않았다.
  - 실제 주문/브로커 API/시장데이터 refresh/OpenDART 추가 호출은 실행하지 않았다.
  - 현재 active `decision_gate.csv`는 사용자 최종 승인 전까지 `WAITING_MANUAL_EVIDENCE`, `NO_ORDER`가 맞다.

## 2026-05-27

- Session closeout:
  - 오늘 핵심 변경: OpenDART `list.json` 기반 filing-review 초안과 `document.xml` 기반 원문 리스크 키워드 스캔 workflow를 추가했다.
  - 주요 산출물: `reports/filing_review/opendart_filing_review_028260.csv`, `opendart_text_risk_scan_028260.csv`, `opendart_text_risk_summary_028260.csv`, `opendart_text_risk_scan_028260.md`.
  - 현재 상태: `028260.KS`는 annual/quarterly filing existence는 `PASS`, 4개 risk check는 모두 `TEXT_HIT_REVIEW_REQUIRED`이며 manual value는 `UNKNOWN`.
  - 검증: `.\.venv\Scripts\python.exe -m pytest .\tests\test_opendart_client.py .\tests\test_filing_review.py .\tests\test_opendart_filing_review.py .\tests\test_filing_text_scan.py -v` -> `19 passed`; 관련 `compileall` 통과.
  - 다음 세션: `opendart_text_risk_scan_028260.csv`의 32개 evidence를 핵심 리스크 5개로 압축하는 로컬 요약 리포트를 만든다. 이 단계는 추가 OpenDART 호출 없이 기존 CSV/MD만 사용한다.
  - 주의: evidence hit는 법률/회계 판단이 아니며 `configs/manual_review.actual.csv`를 자동으로 `PASS/FAIL`로 바꾸지 않는다.

- OpenDART 원문 기반 filing text risk scan workflow를 추가했다.
- 추가 파일:
  - `src/quantum_trainer/filing_text_scan.py`
  - `scripts/fetch_opendart_text_risk_scan.py`
  - `tests/test_filing_text_scan.py`
- 변경 파일:
  - `src/quantum_trainer/opendart_client.py`
  - `tests/test_opendart_client.py`
  - `README.md`
  - `AGENTS.md`
- 동작:
  - OpenDART `document.xml`로 선택된 사업보고서/분기보고서/반기보고서 원문 ZIP을 내려받고 XML 텍스트를 추출한다.
  - `litigation_review`, `contingent_liability_review`, `related_party_review`, `project_risk_review`별 키워드 스니펫을 생성한다.
  - 카테고리별 evidence는 기본 8개로 제한한다.
  - `PF`처럼 짧은 영문 키워드는 `PFS` 같은 긴 영문 토큰 내부에서는 매칭하지 않는다.
  - 키워드 hit는 검토 후보일 뿐이며 manual review 추천값은 항상 `UNKNOWN`으로 둔다.
- 실제 실행:
  - `.\.venv\Scripts\python.exe .\scripts\fetch_opendart_text_risk_scan.py --symbol 028260.KS --disclosures-csv .\reports\filing_review\opendart_filings_028260.csv --max-documents 2 --output-dir .\reports`
  - 다운로드 문서 2건, evidence 32건 생성.
  - 출력: `reports/filing_review/opendart_text_risk_scan_028260.csv`, `opendart_text_risk_summary_028260.csv`, `opendart_text_risk_scan_028260.md`
  - 4개 하위 check 모두 `TEXT_HIT_REVIEW_REQUIRED`, recommended value는 `UNKNOWN`.
- 검증:
  - RED: `document.xml` 함수 import 실패, cap 테스트 실패, `PF` false-positive 테스트 실패를 각각 확인한 뒤 구현.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_filing_text_scan.py -v` -> `4 passed`

- OpenDART filing-review draft workflow를 추가했다.
- 추가 파일:
  - `src/quantum_trainer/opendart_filing_review.py`
  - `scripts/fetch_opendart_filing_review.py`
  - `tests/test_opendart_filing_review.py`
- 변경 파일:
  - `src/quantum_trainer/opendart_client.py`
  - `src/quantum_trainer/filing_review.py`
  - `tests/test_opendart_client.py`
  - `tests/test_filing_review.py`
  - `README.md`
  - `AGENTS.md`
- 동작:
  - OpenDART `corpCode.xml`로 단일 종목 `corp_code`를 찾고 `list.json`으로 공시 목록만 조회한다.
  - 공시 목록에서 `사업보고서`와 `분기보고서`/`반기보고서` 존재 여부만 `PASS`로 prefill한다.
  - 소송, 우발채무, 특수관계자, 프로젝트 리스크는 본문 확인 전까지 `UNKNOWN`으로 남긴다.
  - `configs/manual_review.actual.csv`는 자동 수정하지 않는다.
- 실제 실행:
  - `.\.venv\Scripts\python.exe .\scripts\fetch_opendart_filing_review.py --symbol 028260.KS --begin-date 20260101 --end-date 20260527 --output-dir .\reports`
  - `028260.KS` 공시 57건을 조회했고 `reports/filing_review/opendart_filings_028260.csv`, `opendart_filing_review_028260.csv`, `opendart_filing_review_028260.md`를 생성했다.
  - `.\.venv\Scripts\python.exe .\scripts\run_filing_review.py --input-csv .\reports\filing_review\opendart_filing_review_028260.csv --output-dir .\reports`
  - 결과는 `FILING_REVIEW_UNKNOWN`; blocking checks는 `litigation_review`, `contingent_liability_review`, `related_party_review`, `project_risk_review`.
- 검증:
  - RED: `test_opendart_filing_review.py` import 실패 확인 후 구현.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_opendart_client.py .\tests\test_filing_review.py .\tests\test_opendart_filing_review.py -v` -> `13 passed`
  - `.\.venv\Scripts\python.exe -m compileall .\src\quantum_trainer\opendart_client.py .\src\quantum_trainer\filing_review.py .\src\quantum_trainer\opendart_filing_review.py .\scripts\fetch_opendart_filing_review.py .\scripts\run_filing_review.py` -> 통과

- `filing_review` workflow를 추가했다.
- 추가 파일:
  - `src/quantum_trainer/filing_review.py`
  - `scripts/run_filing_review.py`
  - `tests/test_filing_review.py`
  - `configs/filing_review.example.csv`
- 동작:
  - `annual_report_review`, `quarterly_report_review`, `litigation_review`, `contingent_liability_review`, `related_party_review`, `project_risk_review`를 `PASS/FAIL/UNKNOWN`으로 입력받는다.
  - 전부 `PASS`면 `recommended_manual_review_value=PASS`, 하나라도 `FAIL`이면 `FAIL`, 남은 `UNKNOWN`이 있으면 `UNKNOWN`으로 막는다.
  - `configs/manual_review.actual.csv`는 자동 수정하지 않는다.
- 실행:
  - `.\.venv\Scripts\python.exe .\scripts\run_filing_review.py --input-csv .\configs\filing_review.example.csv --output-dir .\reports`
  - 현재 예시 기준 `028260.KS`는 모든 하위 항목이 `UNKNOWN`이라 `FILING_REVIEW_UNKNOWN`.
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_filing_review.py -v` -> `3 passed`

- `today_pipeline` workflow를 추가했다.
- 추가 파일:
  - `src/quantum_trainer/today_pipeline.py`
  - `scripts/run_today_pipeline.py`
  - `tests/test_today_pipeline.py`
- 변경 파일:
  - `README.md`
  - `AGENTS.md`
  - `docs/work-log.md`
- 동작:
  - `run_today_pipeline.py`가 오늘 후보 갱신 버튼 역할을 한다.
  - 기본 실행은 기존 캐시/CSV를 사용해 company research, filter, candidate briefs, checklist, market watch, conviction, profit focus, investment memo, decision gate, dashboard를 순서대로 재생성한다.
  - `--dry-run`은 실행 없이 계획만 출력한다.
  - `--refresh-market-data`를 붙이면 첫 단계에 최신 가격 갱신을 추가한다. 이 옵션은 외부 market data provider 호출이므로 사용자 명시 승인 후에만 실행한다.
  - 실제 주문, 증권사 API, 자동 매수/매도는 없다.
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_today_pipeline.py -v` -> `2 passed`
  - `.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py --dry-run` -> 10개 local step 출력, `executed_count=0`, `external_api_requested=NO`
- 승인 후 실제 최신 시세 반영 실행:
  - `.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py --refresh-market-data`
  - `data/prices.csv` 갱신: 35 symbols, last date `2026-05-27`
  - 실행 단계: 11개, `external_api_requested=YES`
  - 대시보드 재생성: `reports/dashboard/index.html`
  - 현재 1순위: `028260.KS` Samsung C&T
  - decision gate: `WAITING_MANUAL_EVIDENCE`, `order_status=NO_ORDER`
- 수동 근거 초안 작업 중 valuation 재계산 누락을 발견해 수정했다.
  - 문제: 최신 가격 갱신 후 `configs/fundamentals.actual.csv`의 valuation용 `latest_price`, `PER`, `PBR`이 자동 재계산되지 않을 수 있었다.
  - 수정:
    - `src/quantum_trainer/today_pipeline.py`에 `valuation_metrics_refresh` 단계를 추가했다. `--refresh-market-data` 실행 시 `fundamentals.actual.csv`와 `shares_outstanding.actual.csv`가 있으면 `apply_valuation_metrics.py`를 company research 전에 실행한다.
    - `src/quantum_trainer/fundamentals.py`의 `apply_valuation_metrics()`가 이미 valuation 컬럼이 있는 CSV에도 반복 적용되도록 수정했다.
    - `scripts/run_today_pipeline.py`에 `--shares-csv` 옵션을 추가했다.
  - 검증:
    - `.\.venv\Scripts\python.exe -m pytest .\tests\test_fundamentals.py .\tests\test_today_pipeline.py -v` -> `7 passed`
    - `.\.venv\Scripts\python.exe .\scripts\apply_valuation_metrics.py --fundamentals-csv .\configs\fundamentals.actual.csv --prices-csv .\data\prices.csv --shares-csv .\configs\shares_outstanding.actual.csv --output-csv .\configs\fundamentals.actual.csv` -> 성공
    - `.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py` -> 로컬 10단계 성공, `external_api_requested=NO`
  - 재계산 후 `028260.KS`: latest price `410500`, PER `17.86`, PBR `1.21`
- `028260.KS` Samsung C&T 수동 검토 초안을 생성했다.
  - 출력:
    - `reports/decision_gate/manual_review_draft_028260.csv`
    - `reports/decision_gate/manual_review_draft_028260.md`
  - 초안 판단:
    - `earnings_review`, `business_driver_review`, `valuation_review`, `loss_rule_review`는 `PASS_CANDIDATE`.
    - `filing_review`, `capital_plan_review`는 아직 `UNKNOWN` 유지 권장.
  - `configs/manual_review.actual.csv`는 자동으로 PASS 처리하지 않았다.

- `dashboard` workflow를 추가했다.
- 추가 파일:
  - `src/quantum_trainer/dashboard.py`
  - `scripts/run_dashboard.py`
  - `tests/test_dashboard.py`
- 변경 파일:
  - `README.md`
  - `AGENTS.md`
- 동작:
  - `reports/profit_focus/profit_focus.csv`, `reports/investment_memo/investment_memo.csv`, `reports/decision_gate/decision_gate.csv`를 읽는다.
  - `reports/dashboard/index.html`에 오늘 1순위, decision gate, 투자 메모, 손실 방어, 후보 전체 표, 원본 리포트 링크를 한 화면으로 만든다.
  - 읽기 전용 산출물이며 실제 주문/증권사 API/외부 API 호출은 없다.
- 실제 실행:
  - `run_dashboard.py --reports-dir .\reports`
  - 대시보드: `reports/dashboard/index.html`
  - 현재 표시 상태: `028260.KS`, `WAITING_MANUAL_EVIDENCE`, `NO_ORDER`
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_dashboard.py -v` -> `1 passed`

- `decision_gate` workflow를 추가했다.
- 추가 파일:
  - `src/quantum_trainer/decision_gate.py`
  - `scripts/run_decision_gate.py`
  - `tests/test_decision_gate.py`
  - `configs/manual_review.example.csv`
- 변경 파일:
  - `README.md`
  - `AGENTS.md`
- 동작:
  - `reports/investment_memo/investment_memo.csv`를 읽고 수동 검토 입력 CSV와 결합한다.
  - 수동 입력이 없으면 `reports/decision_gate/manual_review_template.csv`를 만들고 `WAITING_MANUAL_EVIDENCE`로 막는다.
  - `filing_review`, `earnings_review`, `business_driver_review`, `valuation_review`, `loss_rule_review`, `capital_plan_review` 6개가 모두 `PASS`일 때만 `READY_FOR_SIZING_REVIEW`가 된다.
  - 모든 결과는 `order_status=NO_ORDER`이며 실제 주문/증권사 API/외부 API 호출은 없다.
- 실제 실행:
  - `run_decision_gate.py --investment-memo-csv .\reports\investment_memo\investment_memo.csv --output-dir .\reports`
  - 현재 `028260.KS` Samsung C&T는 6개 수동 근거가 `UNKNOWN`이라 `WAITING_MANUAL_EVIDENCE`.
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_decision_gate.py -v` -> `2 passed`

- `investment_memo` workflow를 추가했다.
- 추가 파일:
  - `src/quantum_trainer/investment_memo.py`
  - `scripts/run_investment_memo.py`
  - `tests/test_investment_memo.py`
- 변경 파일:
  - `README.md`
  - `AGENTS.md`
- 동작:
  - `reports/profit_focus/profit_focus.csv`에서 `CORE_FOCUS`만 읽어 투자 논리 검토 메모를 만든다.
  - 산출물은 `reports/investment_memo/investment_memo.csv`, `reports/investment_memo/investment_memo.md`다.
  - 모든 메모는 `order_status=NO_ORDER`이며 실제 주문/증권사 API/외부 API 호출은 없다.
- 실제 실행:
  - `run_investment_memo.py --profit-focus-csv .\reports\profit_focus\profit_focus.csv --output-dir .\reports --max-memos 1`
  - 생성 메모: `028260.KS` Samsung C&T, `THESIS_REVIEW`, `NO_ORDER`
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_investment_memo.py -v` -> `1 passed`

- `profit_focus`에 `today_focus.md` 운영 보드를 추가했다.
- 변경 파일:
  - `src/quantum_trainer/profit_focus.py`
  - `scripts/run_profit_focus.py`
  - `tests/test_profit_focus.py`
  - `README.md`
  - `AGENTS.md`
- 동작:
  - 기존 `profit_focus.csv/md` 외에 `reports/profit_focus/today_focus.md`를 생성한다.
  - 오늘 1순위 후보 1개, 왜 후보인지, 아직 막는 조건, 손실 방어 조건, 대기/제외 후보를 한 페이지로 압축한다.
  - 실제 주문, 증권사 API, 외부 API 호출은 없다.
- 실제 실행:
  - `run_profit_focus.py --conviction-csv .\reports\conviction\conviction_score.csv --checklist-csv .\reports\investment_checklist\investment_checklist.csv --output-dir .\reports --max-core 3`
  - 오늘 1순위: `028260.KS` Samsung C&T
  - 대기/제외: `005930.KS` Samsung Electronics, `003550.KS` LG Corp
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_profit_focus.py -v` -> `2 passed`

- `profit_focus` workflow를 추가했다.
- 추가 파일:
  - `src/quantum_trainer/profit_focus.py`
  - `scripts/run_profit_focus.py`
  - `tests/test_profit_focus.py`
- 동작:
  - `reports/conviction/conviction_score.csv`와 `reports/investment_checklist/investment_checklist.csv`를 결합한다.
  - `CORE_FOCUS`, `WAIT_RISK`, `NEEDS_CHECKLIST`, `WATCH_ONLY`로 단순화한다.
  - 수익 후보를 과도하게 넓히지 않고, 체크리스트 자동 차단/밸류에이션 부담/낮은 conviction은 보류한다.
  - 산출물은 `reports/profit_focus/profit_focus.csv`, `reports/profit_focus/profit_focus.md`다.
  - 실제 주문, 증권사 API, 외부 API 호출은 없다.
- 실제 실행:
  - `run_profit_focus.py --conviction-csv .\reports\conviction\conviction_score.csv --checklist-csv .\reports\investment_checklist\investment_checklist.csv --output-dir .\reports --max-core 3`
  - `CORE_FOCUS`: `028260.KS` Samsung C&T
  - `WAIT_RISK`: `005930.KS` Samsung Electronics, 사유 `밸류에이션 부담`, `not persistent yet`, `conviction_score 65 미만`
  - `NEEDS_CHECKLIST`: `003550.KS` LG Corp
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_profit_focus.py .\tests\test_conviction_score.py .\tests\test_market_watch.py -v` -> `5 passed`
  - `.\.venv\Scripts\python.exe -m compileall .\src\quantum_trainer\profit_focus.py .\scripts\run_profit_focus.py` -> 통과

- `conviction_score` workflow를 추가했다.
- 추가 파일:
  - `src/quantum_trainer/conviction_score.py`
  - `scripts/run_conviction_score.py`
  - `tests/test_conviction_score.py`
- 동작:
  - `reports/market_watch/market_watch.csv`와 `reports/company_research/company_research.csv`를 결합한다.
  - persistence, research score, 상승확률, 기대수익률, 추세, 재무 점수에서 conviction score를 만든다.
  - PER/PBR 과열, 재무 약세, 부채, drawdown은 penalty로 반영한다.
  - 기본값은 `PERSISTENT_FOCUS`만 포함하고, `--include-building-focus`를 쓰면 `BUILDING_FOCUS`도 미리 점검한다.
  - 산출물은 `reports/conviction/conviction_score.csv`, `reports/conviction/conviction_score.md`다.
  - 실제 주문, 증권사 API, 외부 API 호출은 없다.
- 실제 실행:
  - `run_conviction_score.py --market-watch-csv .\reports\market_watch\market_watch.csv --company-research-csv .\reports\company_research\company_research.csv --output-dir .\reports --include-building-focus`
  - 현재 후보 3개는 모두 `DEVELOPING_CONVICTION`: `028260.KS`, `005930.KS`, `003550.KS`
  - `005930.KS`는 밸류에이션 부담 penalty가 붙었다.
  - 아직 `PERSISTENT_FOCUS`가 없으므로 `HIGH_CONVICTION_RESEARCH`는 없다.
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_conviction_score.py .\tests\test_market_watch.py .\tests\test_company_research.py -v` -> `7 passed`
  - `.\.venv\Scripts\python.exe -m compileall .\src\quantum_trainer\conviction_score.py .\scripts\run_conviction_score.py` -> 통과

- `market_watch`에 persistence score를 추가했다.
- 변경 파일:
  - `src/quantum_trainer/market_watch.py`
  - `scripts/run_market_watch.py`
  - `tests/test_market_watch.py`
  - `README.md`
  - `AGENTS.md`
- 동작:
  - `market_watch_history.csv`를 읽어 현재 `TODAY_FOCUS`가 몇 snapshot 연속 유지됐는지 계산한다.
  - `NEW_FOCUS`, `BUILDING_FOCUS`, `PERSISTENT_FOCUS`, `NOT_FOCUS` 라벨을 만든다.
  - `PERSISTENT_FOCUS`는 3회 이상 연속 `TODAY_FOCUS`일 때만 부여한다.
  - schema가 달라진 기존 history가 있어도 기존 행을 보존하고 새 컬럼을 맞춰 저장한다.
- 실제 실행:
  - `run_market_watch.py --company-research-csv .\reports\company_research\company_research.csv --output-dir .\reports --top-n 15 --as-of 2026-05-27`
  - 현재 `TODAY_FOCUS` 3개는 모두 `BUILDING_FOCUS (2)`다.
  - 현재 `PERSISTENT_FOCUS`는 0개다.
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_market_watch.py .\tests\test_company_research.py .\tests\test_research_filter.py -v` -> `7 passed`
  - `.\.venv\Scripts\python.exe -m compileall .\src\quantum_trainer\market_watch.py .\scripts\run_market_watch.py` -> 통과

- `market_watch` workflow를 추가했다.
- 추가 파일:
  - `src/quantum_trainer/market_watch.py`
  - `scripts/run_market_watch.py`
  - `tests/test_market_watch.py`
- 동작:
  - `reports/company_research/company_research.csv`를 읽어 투자금 없이 동향을 감시한다.
  - 기존 `reports/market_watch/market_watch.csv`가 있으면 이전 상태와 비교한다.
  - 각 실행 snapshot을 `reports/market_watch/market_watch_history.csv`에 append한다.
  - `UPGRADED_TO_RESEARCH_CANDIDATE`, `DOWNGRADED_TO_AVOID`, `STABLE_PRIORITY`, `NEW_RESEARCH_CANDIDATE` 같은 이벤트를 만든다.
  - 출력 파일은 `reports/market_watch/market_watch.csv`, `reports/market_watch/market_watch.md`, `reports/market_watch/market_watch_history.csv`다.
  - 외부 API 호출, 실제 주문, 증권사 API 연동은 없다.
- 실제 실행:
  - `run_market_watch.py --company-research-csv .\reports\company_research\company_research.csv --output-dir .\reports --top-n 15 --as-of 2026-05-27`
  - 직전 market watch와 비교되어 핵심 후보는 `STABLE_PRIORITY`로 표시됐다.
  - `TODAY_FOCUS`: `028260.KS` Samsung C&T, `005930.KS` Samsung Electronics, `003550.KS` LG Corp
  - 출력: `reports/market_watch/market_watch.csv`, `reports/market_watch/market_watch.md`, `reports/market_watch/market_watch_history.csv`
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_market_watch.py .\tests\test_company_research.py .\tests\test_research_filter.py -v` -> `6 passed`
  - `.\.venv\Scripts\python.exe -m compileall .\src\quantum_trainer\market_watch.py .\scripts\run_market_watch.py` -> 통과

- `order_sizer` workflow를 추가했다.
- 추가 파일:
  - `src/quantum_trainer/order_sizer.py`
  - `scripts/run_order_sizer.py`
  - `tests/test_order_sizer.py`
- 동작:
  - `reports/investment_checklist/investment_checklist.csv`와 `data/prices.csv`의 최신 가격을 읽는다.
  - 기본적으로 `READY_FOR_MANUAL_REVIEW` 후보만 주문 후보표에 포함한다.
  - `--total-capital-krw`를 반드시 받아 투자금 규모를 임의 가정하지 않는다.
  - 기본 현금 버퍼는 10%, 종목당 최대 목표 비중은 20%다.
  - 산출물은 `reports/orders/order_candidates.csv`, `reports/orders/order_candidates.md`다.
  - 모든 행은 `REVIEW_ONLY`이며 실제 주문, 증권사 API, 외부 API 호출은 없다.
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_order_sizer.py .\tests\test_investment_checklist.py .\tests\test_candidate_brief.py -v` -> `3 passed`
  - `.\.venv\Scripts\python.exe -m compileall .\src\quantum_trainer\order_sizer.py .\scripts\run_order_sizer.py` -> 통과
- 다음 실행:
  - 실제 후보표 생성은 사용자가 `--total-capital-krw` 값을 정한 뒤 실행한다.

- 투자 전 체크리스트 workflow를 추가했다.
- 추가 파일:
  - `src/quantum_trainer/investment_checklist.py`
  - `scripts/run_investment_checklist.py`
  - `tests/test_investment_checklist.py`
- 동작:
  - `reports/candidate_briefs/candidate_briefs.csv`를 읽어 자동 체크, 자동 차단/주의, 수동 체크리스트를 만든다.
  - 출력 파일은 `reports/investment_checklist/investment_checklist.csv`, `reports/investment_checklist/investment_checklist.md`다.
  - `READY_FOR_MANUAL_REVIEW`는 주문 가능 신호가 아니라 수동 검토 대상으로 올려도 된다는 뜻이다.
  - 실제 주문, 증권사 API, 외부 API 호출은 없다.
- 실제 실행:
  - `run_investment_checklist.py --candidate-briefs-csv .\reports\candidate_briefs\candidate_briefs.csv --output-dir .\reports`
  - `028260.KS` Samsung C&T: `READY_FOR_MANUAL_REVIEW`, 자동 차단 없음
  - `005930.KS` Samsung Electronics: `NEEDS_MANUAL_REVIEW`, 자동 차단/주의 `밸류에이션 부담`
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_investment_checklist.py .\tests\test_candidate_brief.py .\tests\test_research_filter.py -v` -> `3 passed`
  - `.\.venv\Scripts\python.exe -m compileall .\src\quantum_trainer\investment_checklist.py .\scripts\run_investment_checklist.py` -> 통과

- `PRIORITY_RESEARCH` 개별 기업 브리프 workflow를 추가했다.
- 추가 파일:
  - `src/quantum_trainer/candidate_brief.py`
  - `scripts/run_candidate_briefs.py`
  - `tests/test_candidate_brief.py`
- 동작:
  - `reports/research_filter/research_filter.csv`에서 지정한 `filter_status` 후보를 고른다.
  - 후보별 Markdown 브리프와 인덱스/CSV를 `reports/candidate_briefs/`에 만든다.
  - 브리프에는 `핵심 데이터`, `투자 논리`, `리스크`, `매수 보류 조건`, `추가 확인 질문`을 넣는다.
  - 외부 API 호출, 실제 주문, 증권사 API 연동은 없다.
- 실제 실행:
  - `run_candidate_briefs.py --research-filter-csv .\reports\research_filter\research_filter.csv --output-dir .\reports --status PRIORITY_RESEARCH`
  - 생성 브리프: `028260.KS` Samsung C&T, `005930.KS` Samsung Electronics
  - 출력: `reports/candidate_briefs/candidate_briefs.csv`, `reports/candidate_briefs/candidate_briefs.md`, 후보별 Markdown 2개
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_candidate_brief.py .\tests\test_research_filter.py -v` -> `2 passed`
  - `.\.venv\Scripts\python.exe -m compileall .\src\quantum_trainer\candidate_brief.py .\scripts\run_candidate_briefs.py` -> 통과

- 상위 후보 리서치 필터 workflow를 추가했다.
- 추가 파일:
  - `src/quantum_trainer/research_filter.py`
  - `scripts/run_research_filter.py`
  - `tests/test_research_filter.py`
- 동작:
  - `reports/company_research/company_research.csv`를 읽어 상위 후보를 `PRIORITY_RESEARCH`, `WATCH_FOR_CONFIRMATION`, `EXCLUDE_UNTIL_RESET`로 분류한다.
  - 각 후보별 `투자 논리`, `대기 사유`, `제외 조건`, `다음 확인`을 CSV/Markdown으로 만든다.
  - 출력 파일은 `reports/research_filter/research_filter.csv`, `reports/research_filter/research_filter.md`다.
  - 실제 주문, 증권사 API, 외부 API 호출은 없다.
- 실제 실행:
  - `run_research_filter.py --company-research-csv .\reports\company_research\company_research.csv --output-dir .\reports --top-n 5`
  - `PRIORITY_RESEARCH`: `028260.KS` Samsung C&T, `005930.KS` Samsung Electronics
  - `WATCH_FOR_CONFIRMATION`: `012330.KS` Hyundai Mobis, `009150.KS` Samsung Electro-Mechanics, `005380.KS` Hyundai Motor
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_research_filter.py .\tests\test_company_research.py -v` -> `4 passed`
  - `.\.venv\Scripts\python.exe -m compileall .\src\quantum_trainer\research_filter.py .\scripts\run_research_filter.py` -> 통과

- Universe 확장 workflow를 보강했다.
- 변경 파일:
  - `src/quantum_trainer/research_universe.py`
  - `scripts/build_research_universe.py`
  - `tests/test_research_universe.py`
  - `configs/research_universe_seed.core_korea.csv`
  - `README.md`
  - `AGENTS.md`
- 동작:
  - `build_research_universe.py`가 여러 `--source-csv`를 받아 병합한다.
  - 중복 symbol은 앞 seed의 값을 우선한다.
  - `--limit`으로 병합 후 최대 종목 수를 제한할 수 있다.
  - core Korea seed는 대형/유동성 후보를 빠르게 넓히는 starter seed이며, 공식 KRX 전체 universe가 아니다.
- 주의:
  - universe 병합은 로컬 CSV 생성만 수행한다.
  - 확장된 universe로 가격/yfinance 또는 OpenDART 수집을 실행하려면 외부 호출 승인이 필요하다.
- 실제 실행:
  - `build_research_universe.py --source-csv .\configs\research_universe_seed.example.csv --source-csv .\configs\research_universe_seed.core_korea.csv --output-csv .\configs\research_universe.actual.csv --limit 50` -> 35 rows
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_research_universe.py -v` -> `3 passed`
  - `.\.venv\Scripts\python.exe -m compileall .\src\quantum_trainer\research_universe.py .\scripts\build_research_universe.py` -> 통과
- 승인 후 확장 universe 기준 외부 데이터 갱신을 실행했다.
- 실행:
  - `update_market_data.py --config .\configs\portfolio.yaml --universe-csv .\configs\research_universe.actual.csv` -> 35 symbols, last date `2026-05-27`
  - `fetch_opendart_fundamentals.py --universe-csv .\configs\research_universe.actual.csv --output-csv .\configs\fundamentals.actual.csv --year 2025` -> 35 rows
  - `fetch_opendart_shares.py --universe-csv .\configs\research_universe.actual.csv --output-csv .\configs\shares_outstanding.actual.csv --year 2025` -> 35 rows
  - `apply_valuation_metrics.py --fundamentals-csv .\configs\fundamentals.actual.csv --prices-csv .\data\prices.csv --shares-csv .\configs\shares_outstanding.actual.csv --output-csv .\configs\fundamentals.actual.csv`
  - `check_fundamentals.py --fundamentals-csv .\configs\fundamentals.actual.csv --output-csv .\reports\fundamentals\fundamentals_actual_scored.csv`
  - `run_company_research.py --config .\configs\portfolio.yaml --universe-csv .\configs\research_universe.actual.csv --fundamentals-csv .\configs\fundamentals.actual.csv`
- 실행 결과:
  - 최종 리포트: `reports/company_research/company_research.csv`, `reports/company_research/company_research.md`
  - 상위 `RESEARCH_CANDIDATE`: `028260.KS` Samsung C&T, `005930.KS` Samsung Electronics, `003550.KS` LG Corp
  - `012330.KS`, `009150.KS`, `005380.KS`는 `BUY_READY`지만 재무 점수가 약해 `WATCHLIST`로 남았다.
  - `BUY_READY`/`RESEARCH_CANDIDATE`는 리서치 후보 상태이며 실제 매수 지시가 아니다.
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_research_universe.py .\tests\test_fundamentals.py .\tests\test_company_research.py -v` -> `9 passed`

- Company research Markdown 리포트 가독성을 개선했다.
- 변경 파일:
  - `src/quantum_trainer/company_research.py`
  - `tests/test_company_research.py`
  - `README.md`
- 동작:
  - 기존 ranking table 뒤에 종목별 상세 섹션을 추가했다.
  - 각 종목에 `투자 논리`, `주요 리스크`, `확인 질문`을 생성한다.
  - 기대수익률/상승확률은 모델 출력이며 확정 수익률이 아니라는 고지를 유지한다.
  - 리포트는 매수 지시가 아니라 사람이 확인해야 할 리서치 메모 성격이다.
- 실제 실행:
  - `run_company_research.py --config .\configs\portfolio.yaml --universe-csv .\configs\research_universe.actual.csv --fundamentals-csv .\configs\fundamentals.actual.csv`
  - `reports/company_research/company_research.md`에 종목별 상세 섹션 생성 확인.
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_company_research.py .\tests\test_fundamentals.py .\tests\test_opendart_client.py -v` -> `11 passed`
  - `.\.venv\Scripts\python.exe -m compileall .\src\quantum_trainer\company_research.py .\src\quantum_trainer\fundamentals.py .\src\quantum_trainer\opendart_client.py .\scripts\run_company_research.py` -> 통과

- PER/PBR 보강 workflow를 추가했다.
- 추가/변경 파일:
  - `src/quantum_trainer/opendart_client.py`
  - `src/quantum_trainer/fundamentals.py`
  - `src/quantum_trainer/company_research.py`
  - `scripts/fetch_opendart_shares.py`
  - `scripts/apply_valuation_metrics.py`
  - `tests/test_opendart_client.py`
  - `tests/test_fundamentals.py`
  - `tests/test_company_research.py`
- 동작:
  - OpenDART `stockTotqySttus.json`에서 보통주 발행주식수를 수집해 `configs/shares_outstanding.actual.csv`를 만든다.
  - 최신 가격 캐시와 `net_income`, `equity`, `shares_outstanding`으로 `market_cap`, `per`, `pbr`를 계산한다.
  - company research 리포트에서 valuation 보강 후에도 `latest_price` 중복 컬럼이 생기지 않게 수정했다.
- 실제 실행:
  - `fetch_opendart_shares.py --universe-csv .\configs\research_universe.actual.csv --output-csv .\configs\shares_outstanding.actual.csv --year 2025` -> 6 rows
  - `apply_valuation_metrics.py --fundamentals-csv .\configs\fundamentals.actual.csv --prices-csv .\data\prices.csv --shares-csv .\configs\shares_outstanding.actual.csv --output-csv .\configs\fundamentals.actual.csv`
  - `run_company_research.py --config .\configs\portfolio.yaml --universe-csv .\configs\research_universe.actual.csv --fundamentals-csv .\configs\fundamentals.actual.csv`
  - 최종 상위 후보: `005930.KS` Samsung Electronics `RESEARCH_CANDIDATE`, `005380.KS` Hyundai Motor `WATCHLIST`
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_opendart_client.py .\tests\test_fundamentals.py .\tests\test_company_research.py -v` -> `11 passed`
  - `.\.venv\Scripts\python.exe -m compileall .\src\quantum_trainer\opendart_client.py .\src\quantum_trainer\fundamentals.py .\src\quantum_trainer\company_research.py .\scripts\fetch_opendart_shares.py .\scripts\apply_valuation_metrics.py .\scripts\fetch_opendart_fundamentals.py .\scripts\run_company_research.py` -> 통과

- OpenDART API key 입력 후 자동 재무지표 수집기를 추가했다.
- 추가 파일:
  - `src/quantum_trainer/opendart_client.py`
  - `scripts/fetch_opendart_fundamentals.py`
  - `tests/test_opendart_client.py`
- 동작:
  - `.env` 또는 OS 환경변수에서 `OPENDART_API_KEY`를 읽는다.
  - 키 값은 출력/로그/문서에 남기지 않는다.
  - OpenDART `corpCode.xml`로 stock code -> corp_code 매핑을 만든다.
  - `fnlttSinglAcntAll.json` 연간 연결재무제표에서 매출액, 영업이익, 당기순이익, 부채총계, 자본총계를 읽어 `fundamentals.actual.csv` 형태로 저장한다.
  - PER/PBR은 OpenDART 재무제표만으로 계산하지 않고 현재 0.0으로 둔다. 시가총액/주가 기반 보강은 다음 단계다.
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_opendart_client.py .\tests\test_fundamentals.py -v` -> `5 passed`
  - `.\.venv\Scripts\python.exe -m compileall .\src\quantum_trainer\opendart_client.py .\scripts\fetch_opendart_fundamentals.py` -> 통과
- 후속 수정:
  - OpenDART 전체 재무제표에 같은 계정명이 여러 번 들어와 `부채총계`/`자본총계`가 잘못 덮어써지는 문제를 발견했다.
  - `account_id`(`ifrs-full_Liabilities`, `ifrs-full_Equity`, `ifrs-full_Revenue`, `ifrs-full_ProfitLoss`, `ifrs-full_OperatingIncomeLoss`)를 우선 사용하도록 파서를 수정했다.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_opendart_client.py -v` -> `4 passed`
- 실제 실행:
  - `fetch_opendart_fundamentals.py --universe-csv .\configs\research_universe.actual.csv --output-csv .\configs\fundamentals.actual.csv --year 2025` -> 6 rows
  - `check_fundamentals.py --fundamentals-csv .\configs\fundamentals.actual.csv --output-csv .\reports\fundamentals\fundamentals_actual_scored.csv`
  - `run_company_research.py --config .\configs\portfolio.yaml --universe-csv .\configs\research_universe.actual.csv --fundamentals-csv .\configs\fundamentals.actual.csv`
  - 실제 재무 결합 후 상위 후보: `005930.KS` Samsung Electronics는 `RESEARCH_CANDIDATE`, `005380.KS` Hyundai Motor는 `WATCHLIST`

- OpenDART API key 입력 준비:
  - `.gitignore`를 추가해 `.env`, `.env.*`, 런타임 리포트/캐시 산출물을 Git 제외 대상으로 지정했다.
  - `.env`와 `.env.example`을 추가했다.
  - `.env`에는 실제 키 없이 `OPENDART_API_KEY=` 항목만 만들었다.
  - 실제 OpenDART key는 사용자가 로컬 `.env`에 직접 입력하고, 답변/로그/문서에는 노출하지 않는다.

- 3순위인 재무지표 입력/검증/점수화 workflow를 추가했다.
- 추가/변경 파일:
  - `src/quantum_trainer/fundamentals.py`
  - `scripts/check_fundamentals.py`
  - `configs/fundamentals.example.csv`
  - `tests/test_fundamentals.py`
  - `src/quantum_trainer/company_research.py`
  - `scripts/run_company_research.py`
  - `tests/test_company_research.py`
- 동작:
  - `symbol,revenue_growth,operating_margin,roe,per,pbr,debt_ratio` CSV를 검증한다.
  - 성장성, 수익성, 밸류에이션, 부채 리스크를 0~100점으로 변환한다.
  - `FUNDAMENTAL_STRONG`, `FUNDAMENTAL_NEUTRAL`, `FUNDAMENTAL_WEAK`를 생성한다.
  - `run_company_research.py --fundamentals-csv`로 가격/알파 리서치에 재무 점수를 결합한다.
  - OpenDART API 호출은 아직 구현하지 않았고, 외부 호출 없이 CSV 입력 workflow로 제한했다.
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_fundamentals.py -v` -> `2 passed`
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_company_research.py -v` -> `3 passed`
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_fundamentals.py .\tests\test_company_research.py .\tests\test_research_universe.py .\tests\test_market_data.py -v` -> `12 passed`
  - `.\.venv\Scripts\python.exe -m compileall .\src\quantum_trainer\fundamentals.py .\src\quantum_trainer\company_research.py .\scripts\check_fundamentals.py .\scripts\run_company_research.py` -> 통과
- 다음 작업:
  - `configs/fundamentals.actual.csv`를 실제 지표로 만들거나 OpenDART API key 기반 자동 수집기를 추가한다.
  - 최신 가격 캐시와 실제 fundamentals를 결합해 company research를 재생성한다.
- 샘플 실행:
  - `check_fundamentals.py --fundamentals-csv .\configs\fundamentals.example.csv` -> `reports/fundamentals/fundamentals_scored.csv` 생성
  - `run_company_research.py --config .\configs\portfolio.yaml --universe-csv .\configs\research_universe.actual.csv --fundamentals-csv .\configs\fundamentals.example.csv` -> 가격+샘플 재무 통합 리포트 생성
  - 샘플 재무지표 기준 상위 후보: `005930.KS` Samsung Electronics, `005380.KS` Hyundai Motor
  - `fundamentals.example.csv`는 실제 공시 데이터가 아니므로 투자 판단에는 `fundamentals.actual.csv` 또는 OpenDART 기반 실데이터가 필요하다.

- 승인 후 우선순위대로 실제 운영 실행을 진행했다.
- 실행:
  - `build_research_universe.py --source-csv .\configs\research_universe_seed.example.csv --output-csv .\configs\research_universe.actual.csv` -> 6개 종목 생성
  - `update_market_data.py --config .\configs\portfolio.yaml --universe-csv .\configs\research_universe.actual.csv` -> `data/prices.csv` 업데이트
  - `run_company_research.py --config .\configs\portfolio.yaml --universe-csv .\configs\research_universe.actual.csv` -> company research 리포트 생성
- 실행 결과:
  - 가격 캐시: 582 rows, 6 symbols, last date `2026-05-27`
  - 리포트: `reports/company_research/company_research.csv`, `reports/company_research/company_research.md`
  - 상위 `RESEARCH_CANDIDATE`: `005380.KS` Hyundai Motor, `005930.KS` Samsung Electronics
  - `000660.KS`는 가격 모멘텀은 강하지만 alpha upside probability가 낮아 `AVOID_FOR_NOW`
- 주의:
  - 위 결과는 데이터 기반 리서치 후보이며 매수 지시나 수익 보장이 아니다.
  - 다음 단계는 재무지표 수집/입력 workflow를 붙여 가격+재무 통합 리서치로 확장하는 것이다.

- 2순위인 가격 캐시 최신화 workflow를 universe 기반으로 확장했다.
- 변경 파일:
  - `src/quantum_trainer/market_data.py`
  - `scripts/update_market_data.py`
  - `tests/test_market_data.py`
- 동작:
  - `update_market_data.py --universe-csv configs/research_universe.actual.csv`를 지원한다.
  - universe CSV의 `symbol` 컬럼을 가격 업데이트 대상 티커로 사용한다.
  - `--universe-csv`가 없으면 기존처럼 `configs/portfolio.yaml`의 `portfolio` symbols를 사용한다.
  - 실제 실행은 `yfinance` 외부 호출과 `data/prices.csv` 덮어쓰기가 있으므로 사용자 승인 후에만 한다.
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_market_data.py -v` -> `5 passed`
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_market_data.py .\tests\test_research_universe.py .\tests\test_company_research.py -v` -> `9 passed`
  - `.\.venv\Scripts\python.exe -m compileall .\src\quantum_trainer\market_data.py .\src\quantum_trainer\research_universe.py .\src\quantum_trainer\company_research.py .\scripts\update_market_data.py .\scripts\build_research_universe.py .\scripts\run_company_research.py` -> 통과
- 다음 작업:
  - 사용자 승인 후 `update_market_data.py --universe-csv`를 실제 실행해 `data/prices.csv`를 최신화한다.
  - 이후 `run_company_research.py`로 최신 가격 기반 후보 리포트를 생성한다.

- 우선순위를 다음 순서로 고정했다:
  1. Universe 표준화/생성
  2. 가격 캐시 최신화
  3. 재무지표 수집
  4. 가격+재무 통합 리서치
- 1순위인 universe builder를 추가했다.
- 추가 파일:
  - `src/quantum_trainer/research_universe.py`
  - `scripts/build_research_universe.py`
  - `tests/test_research_universe.py`
  - `configs/research_universe_seed.example.csv`
- 동작:
  - `code,company_name,market,sector` seed CSV를 `symbol,company_name,sector,market,code`로 표준화한다.
  - KOSPI는 Yahoo 티커 `.KS`, KOSDAQ은 `.KQ`로 변환한다.
  - 외부 API 호출은 하지 않는다.
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_research_universe.py -v` -> `2 passed`
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_research_universe.py .\tests\test_company_research.py -v` -> `4 passed`
  - `.\.venv\Scripts\python.exe -m compileall .\src\quantum_trainer\research_universe.py .\src\quantum_trainer\company_research.py .\scripts\build_research_universe.py .\scripts\run_company_research.py` -> 통과
- 다음 작업:
  - 사용자 승인 후 가격 캐시 업데이트 워크플로를 실행하거나, 외부 호출 없이 기존 캐시로 company research를 실행한다.
  - OpenDART API key가 준비되면 재무지표 수집기를 추가한다.

- 사용자 방향을 “현재 포트폴리오 리밸런싱”에서 “어떤 기업을 왜 검토할지에 대한 데이터 분석”으로 수정했다.
- 로컬 가격 캐시 기반 기업 리서치 후보 랭킹 CLI를 추가했다.
- 추가 파일:
  - `src/quantum_trainer/company_research.py`
  - `scripts/run_company_research.py`
  - `tests/test_company_research.py`
  - `configs/research_universe.example.csv`
- 동작:
  - `data/prices.csv` 같은 로컬 가격 캐시를 읽고 alpha timing, 20일 모멘텀, SMA20 gap, 20일 drawdown을 결합한다.
  - `RESEARCH_CANDIDATE`, `WATCHLIST`, `AVOID_FOR_NOW`로 수동 리서치 상태를 표시한다.
  - `why_summary`에 `POSITIVE_EXPECTED_RETURN`, `POSITIVE_20D_MOMENTUM`, `ABOVE_SMA20` 같은 데이터 근거를 남긴다.
  - 출력 파일은 `reports/company_research/company_research.csv`와 `reports/company_research/company_research.md`다.
  - 외부 API 호출, 주문 실행, 수익 보장 표현은 없다.
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_company_research.py -v` -> `2 passed`
  - `.\.venv\Scripts\python.exe -m compileall .\src\quantum_trainer\company_research.py .\scripts\run_company_research.py` -> 통과
- 다음 작업:
  - 분석할 후보 종목 universe를 `configs/research_universe.actual.csv`로 늘린다.
  - 외부 데이터 호출 승인이 있으면 가격 캐시 업데이트 후 리서치 리포트를 재생성한다.
  - 재무/밸류에이션/사업 품질까지 보려면 별도 fundamentals CSV 입력 workflow를 추가한다.

- 우선순위를 “대기업식 투자 운영 게이트”로 재정렬했다.
- 오늘 바로 쓸 수 있는 투자 준비 리포트 CLI를 추가했다.
- 추가 파일:
  - `src/quantum_trainer/investment_readiness.py`
  - `scripts/run_investment_readiness.py`
  - `tests/test_investment_readiness.py`
- 동작:
  - 실제 보유 비중 CSV, `pretrade_checked_trade_plan.csv`, `buy_timing_report.csv`를 결합한다.
  - `current_weights` 불일치, `Risk: BLOCK`, `Pre-Trade: BLOCK`이 있으면 전체 상태를 `BLOCK`으로 표시한다.
  - 통제 조건이 통과하면 `READY_FOR_HUMAN_REVIEW`로 표시한다.
  - 주문 실행, 브로커 연동, 외부 API 호출은 하지 않는다.
  - 출력 파일은 `reports/investment_readiness/investment_readiness.csv`와 `reports/investment_readiness/investment_readiness.md`다.
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_investment_readiness.py -v` -> `2 passed`
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_investment_readiness.py .\tests\test_portfolio_state.py -v` -> `5 passed`
  - `.\.venv\Scripts\python.exe -m compileall .\src\quantum_trainer\investment_readiness.py .\src\quantum_trainer\portfolio_state.py .\scripts\run_investment_readiness.py .\scripts\check_current_weights.py` -> 통과
- 다음 작업:
  - 실제 보유 비중 CSV를 준비한 뒤 `run_investment_readiness.py`를 dry-run 성격으로 실행해 `BLOCK` 원인을 확인한다.
  - 필요하면 Alpha forecast 결과를 institutional IC report에도 통합한다.

- `current_weights` 입력/검증 workflow를 추가했다.
- 추가 파일:
  - `src/quantum_trainer/portfolio_state.py`
  - `scripts/check_current_weights.py`
  - `tests/test_portfolio_state.py`
  - `configs/current_weights.example.csv`
- 동작:
  - `symbol,current_weight` CSV를 읽고 `configs/portfolio.yaml`의 `current_weights`와 비교한다.
  - `abs(config_weight - actual_weight) >= threshold`이면 `WARN`으로 표시한다.
  - 기본값은 dry-run이며 config를 덮어쓰지 않는다.
  - 명시적으로 `--write-config`를 쓸 때만 YAML `current_weights` 섹션을 갱신한다.
  - 출력 파일은 `reports/portfolio_state/current_weights_check.csv`와 `reports/portfolio_state/current_weights_check.md`다.
- 검증:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_portfolio_state.py -v` -> `3 passed`
  - `.\.venv\Scripts\python.exe -m compileall .\src\quantum_trainer\portfolio_state.py .\scripts\check_current_weights.py` -> 통과
- 다음 작업:
  - 필요하면 전체 테스트와 전체 `compileall`로 회귀 확인.
  - 실제 보유 비중 CSV를 사용해 dry-run 리포트를 만들려면 사용자 승인 후 운영 입력 파일 경로를 지정한다.

## 2026-05-26

- `quantum_stocks_cache`를 실제 상장 종목 기반 퀀트 트레이너로 구축했다.
- 추가 구현:
  - Dynamic Trend Following backtest: `src/quantum_trainer/trend.py`
  - Daily Trainer/Risk/Sizing/Trade Plan: `trainer.py`, `risk.py`, `sizing.py`, `trade_plan.py`
  - 실제 가격 업데이트: `market_data.py`, `scripts/update_market_data.py`
  - Institutional Control Plane: `data_quality.py`, `pretrade.py`, `model_registry.py`, `research_ledger.py`, `investment_committee.py`, `institutional_trainer.py`
  - Alpha Forecast / Buy Timing: `features.py`, `alpha_forecast.py`, `buy_timing.py`, `scripts_api.py`, `scripts/run_alpha_research.py`
- 당시 실제 데이터 스냅샷:
  - `data/prices.csv` 생성
  - 대상 종목: `000660.KS`, `005380.KS`
  - 마지막 확인일: `2026-05-26`
- 생성 산출물:
  - `reports/daily/2026-05-26_*`
  - `reports/runs/2026-05-26-174953/`
  - `reports/alpha/buy_timing_report.csv`
  - `models/registry/2026-05-26-174953.json`
  - `ledger/research_ledger.csv`
- 검증 결과:
  - `.\.venv\Scripts\python.exe -m pytest .\tests -v` -> `31 passed`
  - `.\.venv\Scripts\python.exe -m compileall .\src .\scripts` -> 통과
  - `run_institutional_trainer.py --skip-market-data-update` -> 실행 성공
  - `run_alpha_research.py` -> 실행 성공
- 운영 주의:
  - 현재 시스템은 주문 실행 시스템이 아니며, trade plan/report 생성까지만 한다.
  - `current_weights`가 실제 보유 비중과 다르면 trade plan이 왜곡된다.
  - `run_institutional_trainer.py`를 `--skip-market-data-update` 없이 실행하면 `yfinance` 외부 호출이 발생한다.
  - `Pre-Trade: BLOCK`이면 해당 plan 그대로 주문하면 안 된다.
  - Alpha forecast의 `expected_20d_return`은 확정 수익률이 아니라 모델 예측값이다.
- 다음 작업:
  - `configs/portfolio.yaml`의 `current_weights`를 실제 계좌 비중과 맞추는 입력/검증 workflow 추가.
  - Alpha forecast 결과를 institutional IC report에 통합.
  - `order_sizer.py`를 추가해 target weight를 실제 주문 수량 후보로 변환하되, broker execution은 별도 승인 전까지 금지.
  - KOSPI benchmark(`^KS11`)와 OHLCV/volume feature 확장 검토.

### Archived Next Session Start

- This 2026-05 handoff is superseded by the current `AGENTS.md` Handoff Notes and `CLI_NEXT_SESSION_PROMPT.md`.
- Historical candidate modules and run commands in this block are preserved only as context, not as current priorities.
- Current sessions must re-check latest local evidence and should not carry forward old run ids, candidate rankings, or test counts from this archived note.
## 2026-05-28 - Dashboard Korean Quant Trainer UI

- Reworked `src/quantum_trainer/dashboard.py` from a developer-style English dashboard into a Korean first-screen quant trainer view.
- First screen now shows `오늘 결론`, `지금 할 일`, `1순위 후보`, review quantity, and the fixed safety notice that orders are not auto-executed.
- Moved technical source reports into lower sections: filing risk, six manual review gates, capital plan, universe comparison, user-added symbol analysis, and detail links.
- Added/updated `tests/test_dashboard.py` to require the easier Korean UI and to reject the old English `Quantum Stocks Dashboard`/`Decision Gate` headings.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_dashboard.py -q`
  - `.\.venv\Scripts\python.exe .\scripts\run_dashboard.py --reports-dir .\reports`
  - `rg "퀀트 트레이너|오늘 결론|주문은 자동 실행되지 않습니다|다른 후보와 비교|내가 넣은 종목 분석 상태" .\reports\dashboard\index.html`

## 2026-05-29 - Full Universe And Buy-Blocker Tightening

- Expanded `configs/research_universe.actual.csv` to the active KRX KOSPI/KOSDAQ universe from KIND-listed corporation data.
  - Current universe: 2,657 rows (`KOSPI 838`, `KOSDAQ 1,819`).
  - Price cache refreshed for 2,656 symbols through `2026-05-29`; only `099520.KQ` is missing, so `PRICE_COVERAGE_PARTIAL` is accepted for review use.
- Added KIND/pykrx universe import modules and tests:
  - `src/quantum_trainer/kind_universe.py`
  - `src/quantum_trainer/krx_universe.py`
  - `scripts/import_kind_corp_list.py`
  - `scripts/fetch_pykrx_universe.py`
  - `tests/test_kind_universe.py`
  - `tests/test_krx_universe.py`
- Added full-universe sparse price support:
  - `load_price_csv(..., drop_incomplete=False)` keeps columns with isolated missing history.
  - `company_research` and alpha forecast handle partial symbol coverage without crashing.
  - `universe_coverage` and `operating_status` distinguish `PRICE_COVERAGE_PARTIAL` from a hard blocker.
- Added overextension/chase-buy control in `company_research`:
  - `extension_risk=OVEREXTENDED_WAIT` or `EXTREME_EXTENSION` lowers score and changes the research view to `WAIT_PULLBACK`.
  - This prevents already-stretched names from being treated as clean first-entry candidates.
- Tightened pre-buy and dashboard blockers:
  - Missing `filing_risk_summary_<code>.csv` now keeps the candidate at `WAIT / NO_ORDER`.
  - Dashboard shows `1순위 공시 리스크 = 공시요약 없음 / 검토 필요`.
  - Dashboard Korean text now translates the filing-summary blocker and uses a natural topic particle such as `코미코는`.
- Current local pipeline result:
  - Top quantitative candidate: `183300.KQ` 코미코.
  - Final pre-buy status: `WAIT`.
  - Final order status: `NO_ORDER`.
  - Main blockers: manual gate not ready, filing risk summary not available.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_pre_buy_decision.py .\tests\test_dashboard.py -q` -> `5 passed`
  - `.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py` -> success, `executed_count=23`, `external_api_requested=NO`
  - `.\.venv\Scripts\python.exe .\scripts\run_dashboard.py --reports-dir .\reports` -> success
  - `rg "코미코는|공시요약 없음|공시 리스크 요약이 없습니다" .\reports\dashboard\index.html` -> expected lines found
- Next:
  - To make a new full-universe top candidate actionable, generate OpenDART filing text scans and `filing_risk_summary_<code>.csv` for that specific symbol after explicit external API approval.
  - Do not write `PASS` into `configs/manual_review.actual.csv` automatically; keep using manual proposal/apply-plan files until final user confirmation.

## 2026-05-29 - Komico OpenDART Filing Gate

- Ran user-approved single-symbol OpenDART review for current top candidate `183300.KQ` 코미코.
  - Disclosure list: `reports/filing_review/opendart_filings_183300.csv`
  - Filing review draft: `reports/filing_review/opendart_filing_review_183300.csv|md`
  - Text risk scan: `reports/filing_review/opendart_text_risk_scan_183300.csv|md`
  - Compressed risk summary: `reports/filing_review/filing_risk_summary_183300.csv|md`
- OpenDART scan scope:
  - `disclosure_count=34`
  - `document_count=2`
  - `evidence_count=31`
  - External API was used only for the approved single-symbol OpenDART fetch/scan steps.
- Filing risk result for 코미코:
  - Core risks: 5
  - Fatal risk count: 0
  - Overall opinion: `HOLD_REVIEW`
  - Dashboard now shows `1순위 공시 리스크 = 치명 0개 / 보류 검토`.
- Fixed filing gate behavior:
  - Generic filing summaries no longer reuse Samsung C&T-specific related-party evidence such as "130개 종속기업/52개 관계기업".
  - If any filing risk row is `gate_opinion=HOLD_REVIEW`, `manual_review_draft` keeps `filing_review=UNKNOWN`.
  - If any filing risk row is `HOLD_REVIEW`, `pre_buy_decision` stays `WAIT / NO_ORDER` and surfaces `filing risk hold review`.
  - Dashboard translates that blocker to `공시 리스크 보류 검토`.
- Current final state:
  - Top candidate: `183300.KQ` 코미코
  - Pre-buy status: `WAIT`
  - Order status: `NO_ORDER`
  - Manual filing review: `UNKNOWN`
  - Main blockers: manual gate not ready, filing risk hold review.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_filing_risk_summary.py -q` -> `2 passed`
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_manual_review_draft.py .\tests\test_pre_buy_decision.py -q` -> `7 passed`
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_dashboard.py -q` -> `2 passed`
  - `.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py` -> success, `executed_count=24`, `external_api_requested=NO`
  - `.\.venv\Scripts\python.exe .\scripts\run_dashboard.py --reports-dir .\reports` -> success
  - `rg "코미코|보류 검토|공시 리스크 보류 검토" .\reports\dashboard\index.html` -> expected lines found
- Next:
  - Human review should decide whether the `HOLD_REVIEW` row is a true issue or a conservative keyword gap.
  - Do not apply `configs/manual_review.actual.csv` PASS values until the user explicitly confirms final manual review.

## 2026-05-29 - Archived Handoff Snapshot

- Archived 2026-05 snapshot. It is no longer the active next-session instruction.
- At that time, `183300.KQ` 코미코 was the top candidate and remained `WAIT / NO_ORDER` due to filing, valuation, and manual-review blockers.
- Later sessions added stale-snapshot rules, refreshed the market through 2026-06-05, and moved the next development stream toward institutional safety tooling.
- Current sessions must not assume 코미코 is still the top candidate without re-checking the latest local reports and cached price date.
- The safety constraints remain valid: do not write `configs/manual_review.actual.csv`, do not treat any watch label as buy permission, and do not run bulk price/OpenDART/API refresh without explicit approval.

## 2026-06-02 - Local Trend Forecast Engine

- Added local-only trend forecast report to move beyond single-stock review:
  - Module: `src/quantum_trainer/trend_forecast.py`
  - CLI: `scripts/run_trend_forecast.py`
  - Report: `reports/trend_forecast/trend_forecast.csv|md`
- The report reads cached `data/prices.csv` only and classifies every company research symbol by:
  - 5D/20D/60D returns
  - MA20/MA60 alignment
  - 20D volatility
  - 60D max drawdown
  - `trend_regime`, `forecast_bias`, `chase_risk`, `trend_score`
- Integrated `trend_forecast` into `today_pipeline.py` after `universe_stock_analysis` and before event catalyst ranking.
- Dashboard now shows a `가격 흐름 예측` board and links to `../trend_forecast/trend_forecast.md`.
- Local generation result:
  - `row_count=2657`
  - `bullish_count=76`
  - `watch_pullback_count=98`
  - `bearish_count=1675`
  - `insufficient_count=101`
  - `external_api_requested=NO`
  - `order_status=NO_ORDER`
- Safety:
  - No OpenDART call.
  - No price refresh.
  - No order placement.
  - No `configs/manual_review.actual.csv` write.

## 2026-06-02 - Trend Gate Applied To Buy Decisions

- Applied `reports/trend_forecast/trend_forecast.csv` to downstream decisions:
  - `pre_buy_decision` now keeps a candidate at `WAIT` when trend forecast says `WATCH_PULLBACK` or `chase_risk=HIGH`.
  - `event_adjusted_ranking` now treats `WATCH_PULLBACK` or `chase_risk=HIGH` as chase risk, changing `READY_REVIEW` to `WAIT_PULLBACK`.
  - `today_pipeline.py` passes `--trend-forecast-csv` to both downstream scripts.
- Regenerated local reports:
  - `reports/event_adjusted_ranking/event_adjusted_ranking.csv|md`
  - `reports/pre_buy_decision/pre_buy_decision.csv|md`
  - `reports/dashboard/index.html`
- Current 코미코 downstream state:
  - Trend forecast: `UPTREND / WATCH_PULLBACK / HIGH`
  - Event-adjusted ranking: `WAIT_PULLBACK / NO_ORDER`
  - Pre-buy decision: `WAIT / NO_ORDER`
  - Blocker added: `trend forecast wait pullback`
- Safety:
  - No OpenDART call.
  - No price refresh.
  - No order placement.
  - No `configs/manual_review.actual.csv` write.

## 2026-06-02 - Market Regime And Sector Breadth

- Added local market/sector breadth report:
  - Module: `src/quantum_trainer/market_regime.py`
  - CLI: `scripts/run_market_regime.py`
  - Report: `reports/market_regime/market_regime.csv|md`
- The report aggregates `trend_forecast.csv` into:
  - whole-market row: `scope=MARKET`, `sector=ALL`
  - sector rows: `scope=SECTOR`
  - counts/ratios for `BULLISH`, `WATCH_PULLBACK`, `WATCH_REBOUND`, `BEARISH`, and high chase risk
  - `regime_status` and `risk_posture`
- Integrated into `today_pipeline.py` after `trend_forecast` and before event catalyst/ranking.
- Dashboard now shows `시장/섹터 흐름` and links to `../market_regime/market_regime.md`.
- Local generation result:
  - `row_count=162`
  - `risk_on_count=3`
  - `extended_uptrend_count=1`
  - `risk_off_count=122`
  - `external_api_requested=NO`
  - `order_status=NO_ORDER`
- Safety:
  - No OpenDART call.
  - No price refresh.
  - No order placement.
  - No `configs/manual_review.actual.csv` write.

## 2026-06-02 - Market Regime Gate Applied

- Applied `reports/market_regime/market_regime.csv` to downstream entry decisions.
- Changed:
  - `src/quantum_trainer/pre_buy_decision.py` now keeps candidates at `WAIT` when the whole market or candidate sector is `RISK_OFF`, `EXTENDED_UPTREND`, `RECOVERY_WATCH`, or data-required.
  - `src/quantum_trainer/event_adjusted_ranking.py` now downgrades `BUY_READY` rows to `MARKET_WAIT` when market/sector posture blocks new entries.
  - `scripts/run_pre_buy_decision.py`, `scripts/run_event_adjusted_ranking.py`, and `today_pipeline.py` pass `--market-regime-csv`.
  - `dashboard.py` renders `MARKET_WAIT` as `시장/섹터 대기`.
- Local regeneration result:
  - Event-adjusted ranking: `ready_count=0`, `pullback_count=0`, `market_wait_count=30`, `external_api_requested=NO`.
  - Pre-buy decision: 코미코 remains `WAIT / NO_ORDER` with blockers `manual gate not ready; trend forecast wait pullback; market regime defensive`.
  - Dashboard regenerated with top symbol `183300.KQ`, `order_status=NO_ORDER`.
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_pre_buy_decision.py .\tests\test_event_adjusted_ranking.py .\tests\test_today_pipeline.py .\tests\test_dashboard.py -q` -> `24 passed`.
- Safety:
  - No external API, OpenDART, price refresh, broker/order action, scheduler, deletion, or `configs/manual_review.actual.csv` write.

## 2026-06-02 - Entry Signal Watch Triggers

- Added a local wait-trigger report so the system explains what must change before a blocked candidate should be reviewed again.
- New files:
  - `src/quantum_trainer/entry_signal_watch.py`
  - `scripts/run_entry_signal_watch.py`
  - `tests/test_entry_signal_watch.py`
- Changed:
  - `today_pipeline.py` now runs `entry_signal_watch` after `pre_buy_decision` and before order sizing/scenarios.
  - `dashboard.py` now shows `진입 트리거 감시` and links to `../entry_signal_watch/entry_signal_watch.md`.
  - `AGENTS.md` documents that trigger labels are monitoring states only and not order permission.
- Local generation result:
  - `reports/entry_signal_watch/entry_signal_watch.csv|md`
  - `row_count=30`
  - `market_wait_count=30`
  - `pullback_wait_count=0`
  - `event_only_count=0`
  - `external_api_requested=NO`
  - `order_status=NO_ORDER`
- Verification:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_entry_signal_watch.py .\tests\test_today_pipeline.py .\tests\test_dashboard.py -q` -> `14 passed`.
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\entry_signal_watch.py .\scripts\run_entry_signal_watch.py .\src\quantum_trainer\today_pipeline.py .\src\quantum_trainer\dashboard.py` -> passed.
- Safety:
  - No external API, OpenDART, price refresh, broker/order action, scheduler, deletion, or `configs/manual_review.actual.csv` write.

## 2026-06-02 - GUI Background Analyze Jobs

- Changed:
  - `src/quantum_trainer/web_api.py` exposes `POST /api/analyze/jobs` and `GET /api/analyze/jobs/{job_id}` for background analysis.
  - `web/src/main.jsx` creates an analyze job, polls `QUEUED/RUNNING/DONE/ERROR`, and refreshes status/candidates/holdings after completion.
  - `web/src/styles.css` adds progress notice styling.
  - `AGENTS.md` documents that job responses must stay `order_status=NO_ORDER`, `broker_order_requested=NO`, and cached jobs must avoid external price refresh.
- Verification:
  - `.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\web_api.py` -> passed.
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_web_api.py -q` -> `9 passed`.
  - `npm.cmd run build` from `web/` -> passed.
  - Local GUI restarted at `http://127.0.0.1:8766` with PID `9600`; `/health` returned `OK`, `/api/status` returned `NO_ORDER`.
- Next:
  - Re-test the GUI analysis button in the browser and confirm the progress notice advances instead of staying on `RUNNING`.
  - If still stuck, inspect `/api/analyze/jobs/{job_id}` response and server process/logs before changing pipeline logic.
  - Continue GUI productization: clearer live progress, job history/log preview, and daily analysis usability.
- Safety:
  - No external API/OpenDART call, price refresh, broker/order action, scheduler registration, deletion, or `configs/manual_review.actual.csv` write.

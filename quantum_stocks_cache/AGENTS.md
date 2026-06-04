# AGENTS.md

## Local Addendum - Research Universe Merge

- `scripts/import_krx_universe.py` imports a user-provided full KRX-style CSV locally and writes `configs/research_universe.full.csv` by default.
- `scripts/import_kind_corp_list.py` imports a downloaded KRX KIND listed-corporation HTML/XLS file locally and can write `configs/research_universe.actual.csv` for the active KOSPI/KOSDAQ company universe.
- `scripts/fetch_pykrx_universe.py` calls pykrx/KRX and is an external data operation. It must keep `order_status=NO_ORDER` and requires explicit user approval before execution.
- Full KRX import keeps KOSPI/KOSDAQ common stocks, preferred shares, ETFs, SPACs, and other security types unless the user explicitly asks for a filtered active universe.
- Importing an already downloaded local CSV is safe/local-only and must print `external_api_requested=NO`.
- Downloading the full KRX source file from an external site and refreshing prices for the full KOSPI/KOSDAQ universe are bulk external data operations and require explicit user approval in the same turn.
- `update_market_data.py --batch-size <n> --allow-partial` exists for large universes so thousands of tickers are not sent in one request and isolated provider-missing symbols do not block the whole cache refresh.
- Full-universe coverage may report `PRICE_COVERAGE_PARTIAL` when only a tiny fraction of symbols is unavailable from the provider. Treat it as usable for ranking, not as order permission.
- `load_price_csv(..., drop_incomplete=False)` is for sparse full-universe research data. Keep default strict loading for backtest/trading-style flows unless a research workflow explicitly needs sparse histories.
- Enhanced time-series features such as market-relative strength, trend quality, volatility regime, and breakout gap are evaluation-only until walk-forward comparison shows improvement.
- `company_research` may mark a strong but recently stretched candidate as `WAIT_PULLBACK`. Treat it as a chase-buy warning, not as a clean first-entry signal.
- `scripts/build_research_universe.py` accepts repeated `--source-csv` arguments and optional `--limit`.
- `scripts/add_research_symbol.py` adds or updates one company in `configs/research_universe.actual.csv` without rebuilding the whole universe.
- `scripts/add_research_symbols.py` adds or updates multiple companies from a CSV and is local-only.
- Adding a research symbol is local-only. It does not fetch prices, call OpenDART, write manual review PASS values, or create order instructions.
- `scripts/run_symbol_analysis.py` adds or updates one company, checks cached price coverage, and writes `reports/symbol_analysis/` for that symbol.
- `scripts/run_symbol_batch_analysis.py` adds or updates multiple companies, checks cached price coverage, and writes `reports/symbol_analysis/symbol_analysis_batch.csv|md`.
- Symbol analysis must keep `order_status=NO_ORDER` and `external_api_requested=NO`. If prices are missing, mark `DATA_REQUIRED` instead of fetching data automatically.
- `configs/research_universe_seed.core_korea.csv` is a curated starter seed, not an official full KRX universe.
- Building or merging universe CSVs is local-only. Running price/OpenDART fetchers still requires explicit user approval because they call external APIs.
- `scripts/run_research_filter.py` is local-only. It reads `reports/company_research/company_research.csv` and writes `reports/research_filter/` with human-review priority, wait, and exclusion conditions.
- `PRIORITY_RESEARCH` is not a buy instruction. It means the company should be manually reviewed before any investment decision.
- `run_research_filter.py --top-n` is a watchlist cap, not a hard cap on priority candidates. Keep all `PRIORITY_RESEARCH` rows even when they rank outside `top-n`.
- `scripts/run_candidate_briefs.py` is local-only. It reads `reports/research_filter/research_filter.csv` and writes individual Markdown briefs under `reports/candidate_briefs/`.
- Candidate briefs are research notes, not order tickets. Broker API or order execution remains prohibited without explicit approval.
- `scripts/run_investment_checklist.py` is local-only. It turns candidate briefs into automatic/manual pre-investment checklist reports under `reports/investment_checklist/`.
- `READY_FOR_MANUAL_REVIEW` still means manual review remains. It is not permission to place an order.
- `scripts/run_capital_plan_review.py` is local-only. It writes rule-first capital plan evidence under `reports/decision_gate/` without assuming capital or placing orders.
- `capital_plan_review=PASS_CANDIDATE` means the rule set exists, not that actual capital amount or order size is approved.
- `run_capital_plan_review.py --total-capital-krw <amount>` may mark `amount_status=CAPITAL_PROVIDED` for review only. It still must keep `order_status=NO_ORDER`.
- `scripts/run_order_sizer.py` is local-only and writes manual-review order candidates under `reports/orders/`.
- If `--total-capital-krw` is omitted, rows must be `BLOCKED_CAPITAL_REQUIRED` with zero shares. If capital is provided, sized rows must stay `REVIEW_ONLY`.
- `scripts/run_capital_scenarios.py` is local-only. It writes split-buy scenario rows under `reports/orders/` for hypothetical capital amounts and must keep `order_status=NO_ORDER`.
- Capital scenarios are planning math only. Do not treat `SCENARIO_REVIEW_ONLY` or nonzero share counts as permission to place orders.
- `scripts/run_investment_tracking.py` is local-only. It reads a manual `configs/trade_journal.actual.csv` when present, compares it with cached prices, and writes `reports/performance_tracking/`.
- Investment tracking is for post-buy review only: buy thesis, unrealized PnL, 1-week/1-month/quarter checks, and thesis-broken status. It must keep `order_status=NO_ORDER` and `broker_order_requested=NO`.
- Do not create or edit `configs/trade_journal.actual.csv` unless the user supplies actual executed trade details. Use `configs/trade_journal.example.csv` only as a template.
- Do not add broker API calls, auto-clicking, or order execution without explicit approval.
- `scripts/run_market_watch.py` is local-only. It reads `reports/company_research/company_research.csv`, optionally compares with previous `reports/market_watch/market_watch.csv`, and writes market/watchlist change reports.
- `reports/market_watch/market_watch_history.csv` is append-only monitoring history. Do not delete or truncate it without explicit approval.
- Market watch persistence labels are `NEW_FOCUS`, `BUILDING_FOCUS`, `PERSISTENT_FOCUS`, and `NOT_FOCUS`. Treat `PERSISTENT_FOCUS` as stronger research attention, not as a buy instruction.
- Market watch is the default path when capital is undecided. It tracks candidate changes; it is not a buy or order-sizing instruction.
- `scripts/run_conviction_score.py` is local-only. It reads market watch and company research reports and writes `reports/conviction/`.
- Conviction tiers are research attention levels only. Do not treat `HIGH_CONVICTION_RESEARCH` or `DEVELOPING_CONVICTION` as permission to buy.
- `scripts/run_profit_focus.py` is local-only. It reads conviction and investment checklist reports and writes `reports/profit_focus/`.
- `reports/profit_focus/today_focus.md` is the first operator view when capital is undecided. It must stay a concise one-page focus board: one top candidate, wait/exclude reasons, and loss-defense rules.
- `CORE_FOCUS` is the simplest current research focus, not a buy instruction. Keep invalidation rules and manual review before any capital decision.
- `scripts/run_investment_memo.py` is local-only. It reads `reports/profit_focus/profit_focus.csv` and writes `reports/investment_memo/`.
- Investment memo rows must stay `order_status=NO_ORDER`; they are thesis-review documents, not order tickets.
- `scripts/run_manual_review_draft.py` is local-only. It reads memo/checklist/company research/filing-risk summaries/capital-plan review and writes manual-review draft support under `reports/decision_gate/`.
- Manual review draft values such as `PASS_CANDIDATE` are not actual `PASS`; do not copy them into `configs/manual_review.actual.csv` without human confirmation.
- `scripts/run_manual_review_proposal.py` is local-only. It converts draft candidates into user-confirmation proposal files under `reports/decision_gate/` and must print/write `actual_config_written=NO`.
- Manual review proposal files are not actual manual review config. Do not copy proposal `PASS` values into `configs/manual_review.actual.csv` unless the user explicitly confirms that final write.
- `scripts/run_manual_review_apply_plan.py` is local-only in default mode. It writes `reports/decision_gate/manual_review_apply_plan.csv|md` and `manual_review_actual_candidate.csv` with `actual_config_written=NO`.
- `run_manual_review_apply_plan.py --confirm-final-review I_CONFIRM_MANUAL_REVIEW` can write `configs/manual_review.actual.csv`; do not run that confirmed write unless the user explicitly approves final manual config application in the same turn.
- If `configs/manual_review.actual.csv` already exists and matches the proposal statuses, `run_manual_review_apply_plan.py` should report `apply_mode=EXISTING_ACTUAL` and `actual_config_written=YES` without rewriting the config.
- `scripts/run_universe_stock_analysis.py` is local-only. It reads `reports/company_research/company_research.csv` and writes `reports/universe_stock_analysis/` for every company in the research universe.
- Universe stock analysis rows must stay `order_status=NO_ORDER`; `BUY_READY` means manual gate and sizing review candidate only, not an order instruction.
- `scripts/run_universe_coverage.py` is local-only. It reads the active research universe and cached prices, then writes `reports/universe_coverage/`.
- Universe coverage checks the 20-50 company target, required core comparison symbols, and cached price coverage. Missing price data must be reported as `PRICE_DATA_REQUIRED`; do not fetch prices automatically.
- `scripts/run_pre_buy_decision.py` is local-only. It reads existing local reports and writes `reports/pre_buy_decision/`; all rows must keep `order_status=NO_ORDER`.
- Pre-buy decision should surface manual-proposal and capital blockers such as `actual manual review config not applied` and `capital amount required`; these are stop signs before any real order.
- If the top candidate has no `reports/filing_review/filing_risk_summary_<code>.csv`, pre-buy decision must stay `WAIT / NO_ORDER` and surface `filing risk summary not available` until a user-approved OpenDART review creates evidence.
- If a filing risk summary contains any `gate_opinion=HOLD_REVIEW`, manual review draft must keep `filing_review=UNKNOWN` and pre-buy decision must stay `WAIT / NO_ORDER`; do not treat "no fatal risk" as enough for filing PASS.
- `scripts/run_market_regime.py` is local-only. It reads `reports/trend_forecast/trend_forecast.csv` and writes `reports/market_regime/`; market/sector `RISK_OFF`, `EXTENDED_UPTREND`, `RECOVERY_WATCH`, or `NO_DATA` must be treated as entry blockers, not buy permission.
- `scripts/run_event_catalysts.py` is local-only. It reads manual `configs/event_catalysts.actual.csv` input plus local company research, then writes `reports/event_catalysts/` with `external_api_requested=NO` and `order_status=NO_ORDER`.
- `configs/event_catalysts.actual.csv` is an operator-maintained event watch input, not a news crawler or verified official source. Do not auto-fetch news, scrape portals, or bulk-call external APIs to populate it without explicit approval.
- Event catalyst labels such as `EVENT_FOCUS` and `WAIT_PULLBACK_EVENT` are research attention labels only. They do not override quant gates, manual review gates, price-entry rules, or `NO_ORDER`.
- `scripts/run_event_adjusted_ranking.py` is local-only. It combines `reports/universe_stock_analysis/` with `reports/event_catalysts/` into `reports/event_adjusted_ranking/` and must keep `external_api_requested=NO` and `order_status=NO_ORDER`.
- Event-adjusted statuses such as `READY_REVIEW`, `WAIT_PULLBACK`, and `EVENT_ONLY` are final watchlist labels only. They do not authorize buying, do not write `configs/manual_review.actual.csv`, and do not override manual gates or price-entry rules.
- `MARKET_WAIT` means the candidate was strong enough for watch review but broad market/sector posture blocks entry. It is a wait label only and must remain `NO_ORDER`.
- `scripts/run_entry_signal_watch.py` is local-only. It converts wait reasons into re-check triggers under `reports/entry_signal_watch/`; trigger labels such as `WAIT_MARKET_REGIME`, `WAIT_PRICE_PULLBACK`, and `WATCH_EVENT_ONLY` are monitoring states only and must remain `NO_ORDER`.
- `scripts/run_market_recovery_watch.py` is local-only. It converts market/sector regime blockers into recovery unlock conditions under `reports/market_recovery_watch/`; recovery labels such as `WAIT_BREADTH_RECOVERY`, `WAIT_OVERHEAT_COOLING`, and `RECOVERY_CONFIRMED` are monitoring states only and must remain `NO_ORDER`.
- `scripts/run_sector_rotation_watch.py` is local-only. It ranks sector recovery/rotation states under `reports/sector_rotation_watch/`; labels such as `RECOVERY_LEADER`, `EARLY_ROTATION`, `SELECTIVE_ROTATION`, `OVERHEATED_WAIT`, and `DEFENSIVE_WAIT` are sector watch states only and must remain `NO_ORDER`.
- `scripts/run_tactical_watchlist.py` is local-only. It combines final ranking, entry triggers, and sector rotation into `reports/tactical_watchlist/`; tactical labels such as `READY_MANUAL_REVIEW`, `SECTOR_RECOVERY_WATCH`, `PULLBACK_WATCH`, `MARKET_DEFENSIVE_WAIT`, and `OVERHEATED_WAIT` are today's review priorities only and must remain `NO_ORDER`.
- Dashboard event-adjusted display may prioritize event-tagged rows ahead of no-event quant names. For raw ranking, check `reports/event_adjusted_ranking/event_adjusted_ranking.csv` fields `rank_bucket` and `final_rank_score`; still treat every row as `NO_ORDER`.
- `scripts/run_operating_status.py` is local-only. It reads the final local reports and writes `reports/operating_status/operating_status.csv|md` with `completion_status=DONE` or `NOT_DONE`.
- Operating status is the explicit "끝/아직 끝 아님" report. Even when it says `DONE`, it must keep `order_status=NO_ORDER` and `broker_order_requested=NO`; broker orders remain manual and outside this repo.
- `scripts/run_decision_gate.py` is local-only. It reads `reports/investment_memo/investment_memo.csv` plus an optional manual review CSV and writes `reports/decision_gate/`.
- `READY_FOR_SIZING_REVIEW` only means every manual evidence field is `PASS`; it is still not buy permission and must keep `order_status=NO_ORDER`.
- `scripts/run_dashboard.py` is local-only. It reads existing reports and writes `reports/dashboard/index.html`.
- The dashboard should surface `reports/symbol_analysis/*.csv` as Symbol Analysis Intake when present, including `DATA_REQUIRED` blockers for user-added companies.
- The dashboard should surface `reports/operating_status/operating_status.csv` as the first completion gate when present.
- The dashboard is a read-only operating view. Do not add order execution, broker API calls, or automatic external data refresh to it without explicit approval.
- `scripts/run_today_pipeline.py` is the integrated "today candidate refresh" entrypoint. It can rebuild company research, filters, briefs, checklist, market watch, conviction, profit focus, memo, capital plan review, filing summaries, manual draft, manual proposal, dry-run manual apply plan, decision gate, pre-buy decision with blockers, no-capital order candidates, capital scenarios, operating status, and dashboard in order.
- `scripts/app.py` starts the local web app at `http://127.0.0.1:8765` by default. It is the simple user flow for stock input, today analysis, and dashboard viewing.
- As of 2026-06-02, the user approved latest-price refresh as the default for user-facing daily analysis. The local web app must keep `주문 실행: 안함`; full/no-stock daily analysis requests latest market data by default, and unchecking `최신 가격 갱신` uses cached `data/prices.csv`.
- As of 2026-06-04, GUI background analysis with a stock input uses the quick local symbol-analysis path by default. It uses cached `data/prices.csv`, skips bulk `update_market_data.py`, skips full-universe pipeline regeneration, writes `reports/symbol_analysis/`, refreshes the dashboard, and keeps `order_status=NO_ORDER`.
- The local web app should not auto-open a browser, place orders, connect to broker APIs, or edit manual review actual config.
- `scripts/run_web_app.py` starts the FastAPI + React app at `http://127.0.0.1:8766` by default. It serves `web/dist` and exposes local APIs such as `/api/status` and `/api/analyze`.
- The FastAPI + React app is the preferred product-style UI. It must keep `order_status=NO_ORDER` and `broker_order_requested=NO`; do not add broker execution, auto-clicking, or order buttons.
- `/api/search` is local-only stock name search. It may read `configs/research_universe.actual.csv` and built-in Korean aliases, but must not call external APIs, fetch KRX data, or place orders.
- Name search should let ordinary users type company names such as `삼성전자`, `삼성바이오로직스`, `LG화학`, or `한국전력` without knowing the 6-digit stock code.
- If `/api/search` cannot find a company name locally, do not guess the code. Ask for a 6-digit KRX code or add a broader local KRX universe only after approved data import/update work.
- React source lives under `web/`. `web/node_modules/` and `web/dist/` are generated and must not be committed. Rebuild with `npm.cmd run build` after frontend edits.
- `/api/analyze` defaults to latest-price refresh for the user-facing app after the 2026-06-02 approval. To force cached analysis, requests must set `cache_market_data=true`.
- `scripts/today.py [stock]` is the user-facing one-command wrapper for the today pipeline. It may accept easy stock input such as `삼성전자` or `005930`, then rebuild the local review reports and dashboard. It must keep `주문 실행: 안함` and must not add broker/order execution.
- `scripts/today.py --dry-run` is safe inspection and does not rewrite reports or call external APIs.
- `scripts/today.py [stock]` now requests latest market data by default after the 2026-06-02 approval. Use `--cached-market-data` to force existing cached prices.
- `scripts/run_today_pipeline.py --dry-run` is safe inspection: it prints the planned steps and does not rewrite reports or call external APIs.
- `scripts/run_today_pipeline.py` now requests latest market data by default when run from the CLI after the 2026-06-02 approval. Use `--cached-market-data` to force local/report generation only.
- `scripts/run_today_pipeline.py --add-code/--add-symbol/--add-symbols-csv` may add companies to the universe before the local refresh and create Symbol Analysis Intake before dashboard. It must keep all generated order fields `NO_ORDER`.
- `scripts/add_stock.py <stock>` is the easy local intake command for user-facing stock input such as `삼성전자`, `현대차`, `005930`, or `005930.KS`. It resolves local aliases/existing universe rows only, does not call external APIs, and must keep order execution out of scope.
- `scripts/run_today_pipeline.py --add-stock <stock>` uses the same easy local resolver before the local refresh. Unknown company names must ask for a 6-digit KRX code instead of performing automatic external lookup.
- `scripts/run_today_pipeline.py --total-capital-krw <amount>` may pass capital through capital plan review and order sizing. This is still review-only and must not place orders.
- If `configs/capital.actual.csv` exists, `scripts/run_today_pipeline.py` should use its `total_capital_krw` by default for capital review and review-only sizing.
- `configs/capital.actual.csv` is a local actual capital input. Do not create or edit its amount unless the user supplies the actual amount; use `configs/capital.example.csv` as the template.
- If `configs/manual_review.actual.csv` exists, `scripts/run_today_pipeline.py` should pass it to `decision_gate` by default.
- `scripts/run_today_pipeline.py --refresh-market-data` starts with `update_market_data.py`, calls the external market data provider, then reapplies valuation metrics when fundamentals and shares CSVs exist. The user's 2026-06-02 request is standing approval for normal user-facing daily refresh; bulk/non-daily refresh work still requires explicit approval in the current turn.
- Manual review draft files under `reports/decision_gate/manual_review_draft_*.csv|md` are decision support only. Do not convert draft statuses into `configs/manual_review.actual.csv` `PASS` values without user confirmation.
- Manual review proposal files under `reports/decision_gate/manual_review_proposal*.csv|md` are final-confirmation support only. They do not unblock `decision_gate` unless a confirmed manual review CSV is supplied.
- Manual review apply-plan candidate files under `reports/decision_gate/manual_review_actual_candidate.csv` are still reports, not active config.
- `scripts/run_filing_review.py` is local-only. It reads a human-filled filing review CSV and writes `reports/filing_review/`; it does not fetch DART filings or edit manual review config.
- `reports/filing_review/filing_review.csv` may recommend `filing_review=PASS`, but that recommendation still requires user confirmation before copying into `configs/manual_review.actual.csv`.
- `scripts/fetch_opendart_filing_review.py` calls OpenDART `list.json` for a single symbol and writes filing-review draft files under `reports/filing_review/`. It requires explicit user approval before execution and does not update manual review config.
- `scripts/fetch_opendart_text_risk_scan.py` calls OpenDART `document.xml` for selected annual/quarterly/semiannual filings and writes keyword evidence reports. It requires explicit user approval, is not a legal opinion, and must keep recommended manual values as `UNKNOWN`.
- Downstream summaries from `opendart_text_risk_scan_*.csv` must preserve source report/date/receipt evidence and remain review support only; do not convert keyword hits into `PASS` or `FAIL` without human confirmation.

## Project Overview

이 저장소는 `C:\Users\itwill\자동화 공부\quantum_stocks_cache`에 있는 개인용 퀀트 트레이닝/리서치 시스템이다.

목적은 실제 상장 종목 가격 데이터를 로컬에 캐시하고, pandas/numpy 기반으로 다음 판단을 재현 가능하게 산출하는 것이다.

- Dynamic Trend Following: `SMA20` 기준 진입/현금화
- Volatility Targeting: 변동성 기준 목표 비중 축소
- Risk Gate: MDD, turnover, cash exposure 확인
- Pre-Trade Gate: 주문 전 gross exposure/order delta 제한
- Institutional Control Plane: data quality, registry, ledger, investment committee report
- Alpha Forecast / Buy Timing: 20거래일 기대수익률, 상승 확률, 매수 타이밍 점수

현재 시스템은 주문 실행 시스템이 아니다. 증권사 API 주문, 실시간 체결, 자동 매수/매도는 구현되어 있지 않다. 산출물은 투자 판단 보조용 trade plan/report다.

작업 범위는 이 폴더 내부로 제한한다. 사용자가 별도로 요청하지 않으면 `C:\Users\itwill\자동화 공부`의 다른 프로젝트, 루트 Git 메타데이터, 다른 자동화 폴더를 수정하지 않는다.

## Repository Map

중요 경로:

| 경로 | 역할 | 주의 |
|---|---|---|
| `README.md` | 현재 실행법과 산출물 요약 | 변경 시 실제 명령과 맞춰 갱신 |
| `requirements.txt` | Python 의존성 | 설치는 네트워크 작업 |
| `.env` | 로컬 비밀값 | 실제 키/토큰 입력 가능. 절대 출력/커밋 금지 |
| `.env.example` | 환경변수 예시 | 실제 값 금지 |
| `docs/work-log.md` | 변경사항/검증/다음 작업 기록 | 의미 있는 변경 후 짧게 갱신 |
| `configs/portfolio.yaml` | 실제 운영 config | `current_weights`는 실제 보유 비중과 맞춰야 함 |
| `configs/sample_portfolio.yaml` | 샘플 실행 config | 실제 투자 판단 근거로 쓰지 말 것 |
| `data/prices.csv` | 실제 상장 종목 가격 캐시 | `update_market_data.py`가 덮어씀 |
| `data/sample_prices.csv` | 샘플 가격 데이터 | 테스트/스모크용 |
| `src/quantum_trainer/` | 핵심 패키지 코드 | 모듈별 책임 유지 |
| `scripts/` | CLI 진입점 | 일부 명령은 외부 API 호출/파일 생성 |
| `tests/` | pytest 테스트 | 기능 변경 전후 반드시 실행 |
| `reports/` | 백테스트/트레이너/알파 산출물 | 생성물. 필요 없이 수동 편집하지 말 것 |
| `reports/runs/<run_id>/` | 기관식 실행별 산출물 | audit trail 성격 |
| `reports/daily/` | daily trainer 산출물 | trade plan/decision report/sizing diagnostics |
| `reports/alpha/` | alpha forecast/buy timing 산출물 | 예측 리포트 |
| `models/registry/` | run registry JSON | 실행 추적용 |
| `ledger/research_ledger.csv` | research ledger | append-only 성격 |
| `docs/superpowers/specs/` | 설계 문서 | 구현 의도 파악용 |
| `docs/superpowers/plans/` | 구현 계획 문서 | 다음 작업 이어갈 때 참고 |
| `.venv/` | 로컬 Python 가상환경 | 생성물. 소스처럼 편집하지 말 것 |
| `.pytest_cache/` | pytest 캐시 | 생성물 |

핵심 소스 파일:

| 파일 | 역할 |
|---|---|
| `src/quantum_trainer/config.py` | YAML config 로딩과 경로 해석 |
| `src/quantum_trainer/market_data.py` | `yfinance` 가격 다운로드와 CSV 캐시 저장 |
| `src/quantum_trainer/io.py` | 가격 CSV 로딩, 리포트 저장 |
| `src/quantum_trainer/trend.py` | SMA 기반 dynamic trend backtest |
| `src/quantum_trainer/sizing.py` | volatility targeting 목표 비중 계산 |
| `src/quantum_trainer/risk.py` | portfolio risk gate |
| `src/quantum_trainer/trade_plan.py` | target/current weight 기반 action 생성 |
| `src/quantum_trainer/trainer.py` | daily trainer orchestration |
| `src/quantum_trainer/data_quality.py` | 가격 데이터 품질 검사 |
| `src/quantum_trainer/pretrade.py` | 주문 전 risk check |
| `src/quantum_trainer/model_registry.py` | config hash/run artifact registry |
| `src/quantum_trainer/research_ledger.py` | ledger CSV append |
| `src/quantum_trainer/investment_committee.py` | IC report Markdown 생성 |
| `src/quantum_trainer/institutional_trainer.py` | institutional control plane orchestration |
| `src/quantum_trainer/features.py` | alpha feature 생성 |
| `src/quantum_trainer/alpha_forecast.py` | numpy 기반 Ridge-style alpha forecast |
| `src/quantum_trainer/buy_timing.py` | buy timing score/decision |
| `src/quantum_trainer/scripts_api.py` | alpha research script API |

CLI 진입점:

| 파일 | 역할 |
|---|---|
| `scripts/update_market_data.py` | `yfinance`로 실제 상장 종목 가격 업데이트 |
| `scripts/run_backtest.py` | 백테스트 리포트 생성 |
| `scripts/run_daily_trainer.py` | daily trade plan/report 생성 |
| `scripts/check_current_weights.py` | 실제 보유 비중 CSV와 config `current_weights` 비교 리포트 생성 |
| `scripts/run_investment_readiness.py` | current weights, pre-trade, alpha 결과를 한 장의 투자 준비 리포트로 결합 |
| `scripts/run_institutional_trainer.py` | 기관식 control plane 실행 |
| `scripts/run_alpha_research.py` | alpha forecast/buy timing report 생성 |
| `scripts/build_research_universe.py` | seed CSV를 표준 research universe CSV로 정리 |
| `scripts/check_fundamentals.py` | 재무지표 CSV 검증과 점수화 |
| `scripts/fetch_opendart_fundamentals.py` | OpenDART API로 universe 재무지표 CSV 생성 |
| `scripts/fetch_opendart_shares.py` | OpenDART API로 보통주 발행주식수 CSV 생성 |
| `scripts/fetch_opendart_filing_review.py` | OpenDART API로 단일 종목 공시 목록과 filing-review 초안 생성 |
| `scripts/fetch_opendart_text_risk_scan.py` | OpenDART API로 선택 공시 원문을 받아 filing-risk 키워드 후보 생성 |
| `scripts/apply_valuation_metrics.py` | 최신 가격과 발행주식수로 PER/PBR 보강 |
| `scripts/run_company_research.py` | 로컬 가격 캐시 기반 기업 리서치 후보 랭킹과 근거 리포트 생성 |
| `scripts/run_universe_stock_analysis.py` | `company_research.csv`의 모든 종목을 같은 가격/알파/밸류에이션/리스크 기준으로 재분석 |
| `scripts/run_event_catalysts.py` | 수동 이벤트 입력과 로컬 리서치 결과를 결합해 이벤트 촉매 리포트 생성. 외부 API 없음 |
| `scripts/run_event_adjusted_ranking.py` | 정량 후보, 이벤트 촉매, 추격위험을 합친 최종 감시 랭킹 생성. 주문 실행 없음 |
| `scripts/run_capital_plan_review.py` | 투자금 입력 전 한 종목 최대 비중, 분할 매수, 손절/중단 규칙을 자금 계획 초안으로 생성. 주문 실행 없음 |
| `scripts/run_manual_review_draft.py` | memo/checklist/research evidence로 수동 6개 gate 초안을 생성. 실제 manual config는 수정하지 않음 |

## Common Commands

작업 디렉터리:

```powershell
cd "C:\Users\itwill\자동화 공부\quantum_stocks_cache"
```

의존성 설치:

```powershell
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -r .\requirements.txt
```

실제 가격 데이터 업데이트. 외부 API 호출이므로 위험 작업:

```powershell
.\.venv\Scripts\python.exe .\scripts\update_market_data.py --config .\configs\portfolio.yaml
.\.venv\Scripts\python.exe .\scripts\update_market_data.py --config .\configs\portfolio.yaml --universe-csv .\configs\research_universe.actual.csv
```

백테스트:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_backtest.py --config .\configs\portfolio.yaml
```

Daily Trainer:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_daily_trainer.py --config .\configs\portfolio.yaml
```

Institutional Control Plane. 기본 실행은 market data update를 포함하므로 외부 API 호출:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_institutional_trainer.py --config .\configs\portfolio.yaml
```

캐시된 `data/prices.csv`만 쓰는 institutional 실행:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_institutional_trainer.py --config .\configs\portfolio.yaml --skip-market-data-update
```

Alpha Forecast / Buy Timing:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_alpha_research.py --config .\configs\portfolio.yaml
```

Company Research Candidates. 로컬 캐시 가격 데이터로 후보 기업 순위와 데이터 근거를 만든다. 투자 지시/수익 보장이 아니며 외부 API 호출 없음:

```powershell
.\.venv\Scripts\python.exe .\scripts\build_research_universe.py --source-csv .\configs\research_universe_seed.example.csv --output-csv .\configs\research_universe.actual.csv
.\.venv\Scripts\python.exe .\scripts\fetch_opendart_fundamentals.py --universe-csv .\configs\research_universe.actual.csv --output-csv .\configs\fundamentals.actual.csv --year 2025
.\.venv\Scripts\python.exe .\scripts\fetch_opendart_shares.py --universe-csv .\configs\research_universe.actual.csv --output-csv .\configs\shares_outstanding.actual.csv --year 2025
.\.venv\Scripts\python.exe .\scripts\apply_valuation_metrics.py --fundamentals-csv .\configs\fundamentals.actual.csv --prices-csv .\data\prices.csv --shares-csv .\configs\shares_outstanding.actual.csv --output-csv .\configs\fundamentals.actual.csv
.\.venv\Scripts\python.exe .\scripts\check_fundamentals.py --fundamentals-csv .\configs\fundamentals.example.csv
.\.venv\Scripts\python.exe .\scripts\run_company_research.py --config .\configs\portfolio.yaml --universe-csv .\configs\research_universe.example.csv
.\.venv\Scripts\python.exe .\scripts\run_company_research.py --config .\configs\portfolio.yaml --universe-csv .\configs\research_universe.actual.csv --fundamentals-csv .\configs\fundamentals.example.csv
```

Current Weights Check. 기본값은 dry-run이며 config를 덮어쓰지 않는다:

```powershell
.\.venv\Scripts\python.exe .\scripts\check_current_weights.py --config .\configs\portfolio.yaml --current-weights-csv .\configs\current_weights.example.csv
```

Investment Readiness Gate. 기존 리포트와 실제 보유 비중 CSV를 읽어 수동 검토용 리포트만 생성한다. 주문/브로커/API 호출 없음:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_investment_readiness.py --config .\configs\portfolio.yaml --current-weights-csv .\configs\current_weights.example.csv
```

## Verification Commands

전체 테스트:

```powershell
.\.venv\Scripts\python.exe -m pytest .\tests -v
```

문법/컴파일 확인:

```powershell
.\.venv\Scripts\python.exe -m compileall .\src .\scripts
```

개별 테스트 예시:

```powershell
.\.venv\Scripts\python.exe -m pytest .\tests\test_trend_engine.py -v
.\.venv\Scripts\python.exe -m pytest .\tests\test_institutional_control_plane.py -v
.\.venv\Scripts\python.exe -m pytest .\tests\test_alpha_forecast.py -v
```

실제 캐시 데이터 기반 스모크:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_institutional_trainer.py --config .\configs\portfolio.yaml --skip-market-data-update
.\.venv\Scripts\python.exe .\scripts\run_alpha_research.py --config .\configs\portfolio.yaml
```

코드 수정 후 최소 검증:

```powershell
.\.venv\Scripts\python.exe -m pytest .\tests -v
.\.venv\Scripts\python.exe -m compileall .\src .\scripts
```

## Configuration

주 config는 `configs/portfolio.yaml`이다.

현재 확인된 주요 섹션:

| 섹션 | 용도 |
|---|---|
| `data.prices_csv` | 가격 CSV 경로. 현재 `../data/prices.csv` |
| `reports.output_dir` | 리포트 출력 경로. 현재 `../reports` |
| `market_data.provider` | 데이터 공급자. 현재 `yfinance` |
| `market_data.start` | 다운로드 시작일 |
| `market_data.end` | 다운로드 종료일. 비어 있으면 최신 |
| `market_data.auto_adjust` | yfinance 조정가격 사용 여부 |
| `market_data.progress` | yfinance 진행 표시 여부 |
| `strategy.trend_window` | SMA trend window |
| `strategy.cost_bps` | 거래비용 bps |
| `strategy.periods_per_year` | 연환산 거래일 수 |
| `risk.max_portfolio_mdd` | portfolio MDD gate |
| `risk.max_daily_turnover` | turnover review gate |
| `risk.max_cash_exposure` | cash exposure review gate |
| `sizing.target_volatility` | target volatility |
| `sizing.realized_vol_window` | realized volatility 계산 window |
| `sizing.volatility_floor` | volatility denominator floor |
| `sizing.max_position_weight` | 단일 목표 비중 상한 |
| `sizing.max_leverage` | volatility scalar 상한 |
| `data_quality.max_stale_days` | stale data 허용 일수 |
| `data_quality.max_abs_daily_return` | 비정상 일수익률 jump 기준 |
| `pretrade.max_order_delta` | 단일 주문 delta 상한 |
| `pretrade.max_gross_exposure` | 총 target exposure 상한 |
| `portfolio` | 전략 기준 목표 비중 |
| `current_weights` | 실제 현재 보유 비중 |

`current_weights`는 실제 보유 상태와 다르면 trade plan이 잘못 나온다. 투자 판단 전 반드시 확인한다.

## Environment Variables

현재 확인된 코드에서는 환경변수를 읽지 않는다.

검색 기준:

- `os.environ`
- `getenv`
- `.env`
- `API_KEY`
- `TOKEN`
- `PASSWORD`
- `SECRET`

현재는 API key, broker credential, token이 필요 없는 구조다. `yfinance`는 별도 API key 없이 호출된다.

향후 증권사 API, OpenAI API, 텔레그램 알림 등을 추가할 경우 실제 값은 절대 문서에 쓰지 말고 변수명만 기록한다.

OpenDART 재무지표 자동 수집을 추가할 때는 `.env` 또는 OS 환경변수의 `OPENDART_API_KEY`만 읽는다. 실제 키 값은 답변, 로그, 문서, 코드에 쓰지 않는다.

예상 변수명 예시. 현재 미사용:

| 변수명 | 용도 |
|---|---|
| `OPENDART_API_KEY` | OpenDART 재무/공시 API 인증키 |
| `BROKER_API_KEY` | 증권사 API key |
| `BROKER_API_SECRET` | 증권사 API secret |
| `BROKER_ACCOUNT_ID` | 계좌 식별자 |
| `OPENAI_API_KEY` | LLM/AI 기능 추가 시 |

## Data, Logs, And Runtime Files

데이터:

| 경로 | 설명 |
|---|---|
| `data/prices.csv` | 실제 종목 가격 캐시. `update_market_data.py`가 생성/덮어씀 |
| `data/sample_prices.csv` | 샘플 데이터 |

리포트:

| 경로 | 설명 |
|---|---|
| `reports/equity_curve.csv` | 백테스트 equity curve |
| `reports/performance_summary.csv` | 백테스트 성과 요약 |
| `reports/position_matrix.csv` | position matrix |
| `reports/signal_matrix.csv` | signal matrix |
| `reports/daily/YYYY-MM-DD_trade_plan.csv` | daily trainer trade plan |
| `reports/daily/YYYY-MM-DD_decision_report.md` | daily trainer decision report |
| `reports/daily/YYYY-MM-DD_sizing_diagnostics.csv` | sizing 진단 |
| `reports/runs/<run_id>/investment_committee_report.md` | institutional IC report |
| `reports/runs/<run_id>/trade_plan.csv` | institutional run trade plan copy |
| `reports/runs/<run_id>/pretrade_checked_trade_plan.csv` | pre-trade check 반영 plan |
| `reports/alpha/buy_timing_report.csv` | alpha forecast/buy timing 결과 |
| `reports/alpha/buy_timing_report.md` | alpha forecast Markdown |
| `reports/sample/` | 샘플 실행 결과 |

Audit/registry:

| 경로 | 설명 |
|---|---|
| `ledger/research_ledger.csv` | institutional run ledger. append-only로 취급 |
| `models/registry/<run_id>.json` | run별 config hash, artifact path, status 기록 |

세션/캐시:

| 경로 | 설명 |
|---|---|
| `.venv/` | 로컬 가상환경 |
| `.pytest_cache/` | pytest 캐시 |
| `src/quantum_trainer/__pycache__/` | Python 캐시. 생성될 수 있음 |

현재 별도 로그인 세션, 쿠키, 브라우저 프로필, 비밀 파일은 확인되지 않았다.

## Operational Rules

투자 판단 순서:

1. `build_research_universe.py`로 분석 후보 universe CSV를 표준화
2. 필요 시 실제 가격 업데이트
3. 재무지표 CSV가 있으면 `check_fundamentals.py`로 검증/점수화
4. `run_company_research.py`로 기업 후보 순위와 데이터 근거 확인
5. `configs/portfolio.yaml`의 `portfolio`와 `current_weights` 확인
6. 실제 보유 비중 CSV가 있으면 `check_current_weights.py`로 `current_weights` 불일치 여부 확인
7. Institutional Control Plane 실행
8. `Data Quality`, `Risk Gate`, `Pre-Trade` 상태 확인
9. Alpha Forecast / Buy Timing 실행
10. `run_investment_readiness.py`로 current weights/pre-trade/alpha를 한 장으로 결합
11. `BUY_READY`, `WAIT`, `AVOID` 해석
12. 실제 주문은 사람이 별도로 판단. 이 저장소는 주문 실행 안 함

상태 해석:

| 상태 | 의미 |
|---|---|
| `Data Quality: FAIL` | 데이터 신뢰 불가. 투자 판단 금지 |
| `Risk Gate: BLOCK` | 신규 매수 금지 |
| `Pre-Trade: BLOCK` | 해당 trade plan 그대로 주문 금지 |
| `MAX_ORDER_DELTA` | 하루 주문 변화 폭이 너무 큼. 분할 실행 검토 |
| `BUY_READY` | alpha timing상 매수 후보 |
| `WAIT` | edge 부족. 관망 |
| `AVOID` | alpha timing상 제외 |
| `RESEARCH_CANDIDATE` | 데이터상 추가 분석 후보. 매수 지시가 아님 |
| `READY_FOR_HUMAN_REVIEW` | 자동 주문 가능이 아니라 사람이 최종 검토할 수 있는 상태 |

`expected_20d_return`과 `upside_probability`는 예측값이다. 확정 수익률이 아니다. 투자 판단에는 반드시 `Data Quality`, `Risk Gate`, `Pre-Trade`, `buy_timing_score`, `decision`, 실제 보유 비중을 함께 본다.

문서 운영:

- 의미 있는 코드/운영 변경 후 `docs/work-log.md`에 변경사항, 검증 결과, 다음 작업을 짧게 남긴다.
- 새 운영 규칙, 위험 명령, 민감 파일 위치가 생기면 `AGENTS.md`도 함께 갱신한다.
- work log는 장문 회고가 아니라 다음 CLI 세션이 바로 이어갈 수 있는 핵심만 기록한다.

## Dangerous Operations

외부 API 호출:

- `scripts/update_market_data.py`
- `scripts/run_institutional_trainer.py` without `--skip-market-data-update`

파일/상태 변경:

- `data/prices.csv` 덮어쓰기
- `reports/` 새 리포트 생성/덮어쓰기
- `ledger/research_ledger.csv` append
- `models/registry/` JSON 생성
- `.venv` 의존성 설치/변경

투자 관련 위험:

- 산출된 trade plan을 실제 주문으로 해석/집행
- `pretrade.max_order_delta`를 키워 대규모 주문 차단을 우회
- `current_weights`가 실제 보유 비중과 다른 상태에서 trade plan 사용

## Never Do

- 이 폴더 밖의 프로젝트를 수정하지 않는다.
- 사용자 승인 없이 `C:\Users\itwill\자동화 공부` 루트 또는 다른 자동화 폴더를 수정하지 않는다.
- 사용자 승인 없이 `.git`, commit, push, reset, clean, stash 작업을 하지 않는다. `.git`은 이 폴더 밖 루트에 있을 수 있다.
- 사용자 승인 없이 `data/prices.csv`, `reports/`, `ledger/`, `models/registry/`를 삭제하지 않는다.
- 사용자 승인 없이 `.venv/`를 삭제하거나 재생성하지 않는다.
- `git reset --hard`, `git clean`, 대량 삭제 명령을 실행하지 않는다.
- 비밀키, 계정, 토큰을 코드/문서/config에 쓰지 않는다.
- `position = signal.shift(1)` 원칙을 제거하지 않는다. Look-ahead bias 방지 핵심이다.
- Alpha forecast를 확정 수익률처럼 표시하지 않는다.
- `Pre-Trade: BLOCK` 상태를 무시하고 “주문 가능”이라고 말하지 않는다.
- 증권사 API 자동 주문 기능을 사용자 승인 없이 추가하지 않는다.

## Commands Requiring User Approval

외부 API/네트워크:

일반 사용자-facing daily analysis는 2026-06-02 요청으로 최신 가격 갱신 기본 실행이 승인되었다. 아래 명령은 별도 bulk/non-daily refresh 또는 수동 실행 맥락에서는 여전히 승인 필요 작업이다.

```powershell
.\.venv\Scripts\python.exe .\scripts\update_market_data.py --config .\configs\portfolio.yaml
.\.venv\Scripts\python.exe .\scripts\update_market_data.py --config .\configs\portfolio.yaml --universe-csv .\configs\research_universe.actual.csv
.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py --refresh-market-data
.\.venv\Scripts\python.exe .\scripts\fetch_opendart_fundamentals.py --universe-csv .\configs\research_universe.actual.csv --output-csv .\configs\fundamentals.actual.csv --year 2025
.\.venv\Scripts\python.exe .\scripts\fetch_opendart_shares.py --universe-csv .\configs\research_universe.actual.csv --output-csv .\configs\shares_outstanding.actual.csv --year 2025
.\.venv\Scripts\python.exe .\scripts\fetch_opendart_filing_review.py --symbol 028260.KS --begin-date 20260101 --end-date 20260527 --output-dir .\reports
.\.venv\Scripts\python.exe .\scripts\fetch_opendart_text_risk_scan.py --symbol 028260.KS --disclosures-csv .\reports\filing_review\opendart_filings_028260.csv --max-documents 2 --output-dir .\reports
.\.venv\Scripts\python.exe .\scripts\run_institutional_trainer.py --config .\configs\portfolio.yaml
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -r .\requirements.txt
```

상태 생성/append가 있는 운영 실행:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_daily_trainer.py --config .\configs\portfolio.yaml
.\.venv\Scripts\python.exe .\scripts\run_institutional_trainer.py --config .\configs\portfolio.yaml --skip-market-data-update
.\.venv\Scripts\python.exe .\scripts\run_alpha_research.py --config .\configs\portfolio.yaml
```

config 덮어쓰기:

```powershell
.\.venv\Scripts\python.exe .\scripts\check_current_weights.py --config .\configs\portfolio.yaml --current-weights-csv <actual.csv> --write-config
```

삭제/정리:

```powershell
Remove-Item .\reports -Recurse
Remove-Item .\ledger -Recurse
Remove-Item .\models -Recurse
Remove-Item .\data\prices.csv
Remove-Item .\.venv -Recurse
```

Git:

```powershell
git add
git commit
git push
git reset
git clean
git stash
```

## Safe Inspection Commands

읽기/검증 위주의 안전 명령:

```powershell
Get-Content -LiteralPath .\README.md
Get-Content -LiteralPath .\configs\portfolio.yaml
Get-Content -LiteralPath .\requirements.txt
Get-ChildItem -Recurse -File -Name -Exclude *.pyc
.\.venv\Scripts\python.exe -m pytest .\tests -v
.\.venv\Scripts\python.exe -m compileall .\src .\scripts
```

`reports/`, `ledger/`, `models/registry/`의 내용 확인은 가능하지만 투자 판단/개인 기록 성격이 있으므로 답변에 과도하게 원문 전체를 붙이지 않는다.

## Local GUI Notes

- `scripts/run_web_app.py`는 FastAPI + React 로컬 GUI를 `127.0.0.1:8766`에서 제공한다.
- GUI의 `/api/status`, `/api/search`, `/api/candidates`는 로컬 파일을 읽어 요약한다.
- `/api/candidates`는 `reports/tactical_watchlist/tactical_watchlist.csv`, `reports/pre_buy_decision/pre_buy_decision.csv`, `reports/market_regime/market_regime.csv`, `data/prices.csv`를 조합해 후보 보드를 만든다.
- GUI의 `/api/holdings`는 `configs/holding_watch.actual.csv`와 로컬 추세/랭킹/가격 파일을 조합해 보유종목 방어 보드를 만든다.
- `POST /api/holdings`는 사용자가 GUI에서 입력한 `entry_price`와 `quantity`를 `configs/holding_watch.actual.csv`에 저장하는 로컬 입력 저장 기능이다. 이 API는 broker/order API가 아니며 항상 `order_status=NO_ORDER`를 반환해야 한다.
- `configs/holding_watch.actual.csv`는 사용자가 제공한 보유종목 매수가 감시 입력이다. 수량이 없으면 종목별 손익률만 계산하고, `/api/holdings.summary`는 수량 누락을 표시하며 총 평가액/총 손익 계산에서 제외한다.
- Holding defense summary fields such as `highest_priority_action`, `risk_review_count`, and `next_operator_step` are review labels only, not sell/order instructions.
- GUI 분석 실행은 기본적으로 최신 가격 갱신을 요청하도록 되어 있다. 외부 가격 갱신이 부담되면 화면의 `최신 가격 갱신`을 끄거나 API에서 `cache_market_data=true`를 사용한다.
- `/api/analyze` must honor `refresh_market_data=false` as cached/local analysis. `cache_market_data=true` remains an explicit override that also disables refresh.
- `/api/analyze/jobs` runs analysis in a background job and `/api/analyze/jobs/{job_id}` polls progress so the GUI does not look stuck on long runs. Job responses must keep `order_status=NO_ORDER` and `broker_order_requested=NO`; cached requests must continue to avoid external price refresh. If `stock` is provided, the job must use `analysis_mode=QUICK_STOCK` and must not start bulk latest-price refresh.
- GUI와 API는 항상 `order_status=NO_ORDER`, `broker_order_requested=NO`를 유지해야 한다. 후보 보드, 진입 범위, 손절 규칙 표시는 주문 허가가 아니다.

## Common Failure Points

- `current_weights`가 실제 보유 비중과 다르면 action이 왜곡된다.
- `run_institutional_trainer.py`를 `--skip-market-data-update` 없이 실행하면 `yfinance` 네트워크 호출이 발생한다.
- `data/prices.csv`가 오래되면 `Data Quality: FAIL` 또는 stale 관련 판단이 나온다.
- `pretrade.max_order_delta` 기본값 `0.25` 때문에 큰 리밸런싱은 `Pre-Trade: BLOCK`이 될 수 있다.
- `yfinance` 데이터는 외부 공급자 상태, 티커, 휴장일, 지연/누락에 영향을 받는다.
- `market_data.auto_adjust: true`라서 가격 해석은 조정가격 기준이다.
- `AlphaForecastConfig`는 현재 코드에서 기본값으로 실행되며 외부 ML 라이브러리를 쓰지 않는다.
- `ma60` feature와 forward horizon 때문에 alpha 학습 샘플은 앞/뒤 구간이 잘린다.
- `expected_20d_return`은 model output이다. 반드시 `sample_count`, `model_r2`, `upside_probability`와 같이 해석한다.
- `reports/runs/<run_id>`는 실행 시각을 포함하므로 매 실행마다 새 폴더가 생긴다.
- `ledger/research_ledger.csv`는 append 방식이라 반복 실행하면 행이 늘어난다.
- `rg --files`가 이 폴더에서 빈 결과/exit 1을 낼 수 있었다. 그 경우 PowerShell `Get-ChildItem`로 보완한다.

## Testing Notes

현재 테스트 파일:

| 파일 | 커버 범위 |
|---|---|
| `tests/test_trend_engine.py` | shift(1), cash switch, MDD 개선 |
| `tests/test_sizing.py` | volatility adjusted weights |
| `tests/test_risk_and_trade_plan.py` | risk gate, trade action |
| `tests/test_trainer.py` | daily trainer report 생성 |
| `tests/test_market_data.py` | market data normalize/cache/config |
| `tests/test_institutional_control_plane.py` | data quality, pretrade, registry, ledger, IC report, institutional run |
| `tests/test_alpha_forecast.py` | feature, label, alpha forecast, buy timing, alpha report |
| `tests/test_config_io.py` | config/path/CSV/report IO |
| `tests/test_operating_status.py` | final DONE/NOT_DONE local operating status |

기능 변경 시 TDD 순서:

1. 실패하는 테스트 추가
2. 테스트 실패 확인
3. 최소 구현
4. 전체 테스트 실행
5. `compileall` 실행

## Handoff Notes

다음 CLI 세션에서 먼저 확인할 파일:

1. `AGENTS.md`
2. `docs/work-log.md`
3. `README.md`
4. `configs/portfolio.yaml`
5. `src/quantum_trainer/config.py`
6. `src/quantum_trainer/institutional_trainer.py`
7. `src/quantum_trainer/alpha_forecast.py`
8. `src/quantum_trainer/buy_timing.py`
9. `reports/runs/`의 최신 run 폴더
10. `reports/alpha/buy_timing_report.csv`
11. `ledger/research_ledger.csv`
12. `docs/superpowers/specs/`
13. `docs/superpowers/plans/`

최근 확인된 실제 실행 상태:

- 실제 가격 캐시: `data/prices.csv`
- 대상 종목: `000660.KS`, `005380.KS`
- Institutional run 예시: `reports/runs/2026-05-26-174953/`
- Alpha report: `reports/alpha/buy_timing_report.csv`
- 마지막 전체 검증 시점에는 `pytest` 31개가 통과했고 `compileall`도 통과했다. 다음 세션에서는 현재 상태를 다시 실행해 확인한다.

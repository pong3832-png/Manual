# Full KRX Universe And Time-Series Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the program accept the full KOSPI/KOSDAQ universe while adding only validated time-series improvements to ranking.

**Architecture:** Keep full KRX import local and explicit: import a user-provided KRX-style CSV, preserve all listed instruments, and write a normalized universe plus an import summary. Handle large price refreshes in batches. Add time-series candidate features and an evaluation report before using them in live ranking.

**Tech Stack:** Python, pandas, yfinance, pytest.

---

### Task 1: Full KRX Universe Import

**Files:**
- Modify: `src/quantum_trainer/research_universe.py`
- Create: `scripts/import_krx_universe.py`
- Test: `tests/test_research_universe.py`

- [ ] Write a failing test that feeds Korean/English KRX-like columns and expects all KOSPI/KOSDAQ rows, including ETF/SPAC/preferred rows, to remain present.
- [ ] Implement a local-only normalizer that maps code/name/market/sector/security type/status variants into a standard CSV.
- [ ] Add a script that writes `configs/research_universe.full.csv` by default and prints `external_api_requested=NO`.

### Task 2: Batched Market Data Refresh

**Files:**
- Modify: `src/quantum_trainer/market_data.py`
- Modify: `scripts/update_market_data.py`
- Test: `tests/test_market_data.py`

- [ ] Write a failing test that proves symbols are downloaded in batches and merged into one price frame.
- [ ] Add a batch fetch helper that preserves symbol order and raises if duplicate columns appear.
- [ ] Add `--batch-size` to `update_market_data.py` so full-universe refreshes do not send thousands of tickers in one request.

### Task 3: Time-Series Candidate Feature Gate

**Files:**
- Modify: `src/quantum_trainer/features.py`
- Modify: `src/quantum_trainer/alpha_forecast.py`
- Test: `tests/test_alpha_forecast.py`

- [ ] Add candidate features for market-relative 20-day strength, 60-day trend quality, 20/60 volatility regime, and 120-day breakout gap.
- [ ] Keep the live alpha model on the existing base feature set by default.
- [ ] Add a comparison function that reports base versus enhanced feature-set directional accuracy and average forward return.
- [ ] Only expose enhanced features as `EVALUATION_ONLY` until the comparison shows improvement.

### Task 4: Documentation And Safety

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/work-log.md`

- [ ] Document that full-universe import is local-only when using a supplied CSV.
- [ ] Document that KRX/downloaded universe acquisition and full-market price refresh are external/bulk operations requiring explicit approval.
- [ ] Record test results and changed files.

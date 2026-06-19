# Alpha Forecast And Buy Timing V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local alpha forecast layer that produces expected 20-day return, upside probability, and buy timing decision reports.

**Architecture:** Feature generation, model fitting, buy timing scoring, and CLI report writing are separate modules. Existing risk and institutional control-plane modules are not modified in this first V1 integration.

**Tech Stack:** Python 3.10+, pandas, numpy, pytest, pathlib, logging, dataclasses.

---

### Task 1: Feature Engine

**Files:**
- Create: `tests/test_alpha_forecast.py`
- Create: `src/quantum_trainer/features.py`

- [ ] **Step 1: Write failing tests**

Tests verify feature columns and forward labels exist for deterministic prices.

- [ ] **Step 2: Implement feature and label functions**

Implement `build_feature_frame()` and `build_forward_labels()`.

### Task 2: Alpha Forecast Model

**Files:**
- Modify: `tests/test_alpha_forecast.py`
- Create: `src/quantum_trainer/alpha_forecast.py`

- [ ] **Step 1: Write failing tests**

Tests verify forecasts include `expected_20d_return`, `upside_probability`, `sample_count`, and `model_r2`.

- [ ] **Step 2: Implement Ridge-style local model**

Use `numpy.linalg.solve`; clip forecast and probability.

### Task 3: Buy Timing

**Files:**
- Modify: `tests/test_alpha_forecast.py`
- Create: `src/quantum_trainer/buy_timing.py`

- [ ] **Step 1: Write failing tests**

Tests verify strong positive forecast returns `BUY_READY`, weak forecast returns `WAIT`, and negative forecast returns `AVOID`.

- [ ] **Step 2: Implement scoring and decision logic**

Return a report DataFrame with `buy_timing_score` and `decision`.

### Task 4: Alpha Research CLI

**Files:**
- Modify: `tests/test_alpha_forecast.py`
- Create: `scripts/run_alpha_research.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing integration test**

Test verifies report CSV and Markdown are written.

- [ ] **Step 2: Implement CLI**

Run with `--config configs/portfolio.yaml` and write `reports/alpha/buy_timing_report.csv`.

### Task 5: Verification

- [ ] **Step 1: Run tests**

Run: `.\.venv\Scripts\python.exe -m pytest .\tests -v`

Expected: all pass.

- [ ] **Step 2: Compile**

Run: `.\.venv\Scripts\python.exe -m compileall .\src .\scripts`

Expected: pass.

- [ ] **Step 3: Run real alpha research**

Run: `.\.venv\Scripts\python.exe .\scripts\run_alpha_research.py --config .\configs\portfolio.yaml`

Expected: report written under `reports/alpha`.

No git commands are allowed because `.git` is outside `quantum_stocks_cache`.

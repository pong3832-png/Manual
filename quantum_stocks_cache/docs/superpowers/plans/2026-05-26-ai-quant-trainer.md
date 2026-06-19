# AI Quant Trainer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local-only AI Quant Trainer layer that converts dynamic trend backtest output into risk-gated daily trade plans and Markdown audit reports.

**Architecture:** The existing vectorized `trend.py` remains the source of truth for signals and returns. New modules `risk.py`, `trade_plan.py`, and `trainer.py` add deterministic operating decisions without broker execution.

**Tech Stack:** Python 3.10+, pandas, PyYAML, pytest, pathlib, logging, dataclasses, type hints.

---

### Task 1: Risk Gate Tests

**Files:**
- Create: `tests/test_risk_and_trade_plan.py`

- [ ] **Step 1: Write failing tests**

Tests must verify:

- MDD breach returns `BLOCK`.
- High cash exposure returns `REVIEW`.
- Downside SMA break generates `SELL_TO_CASH`.
- Upside re-entry generates `BUY_TO_TARGET`.
- MDD block converts buy action to `HOLD_BLOCKED`.

- [ ] **Step 2: Run tests**

Run: `.\.venv\Scripts\python.exe -m pytest .\tests -v`

Expected: FAIL because `risk.py` and `trade_plan.py` do not exist.

### Task 2: Implement Risk And Trade Plan

**Files:**
- Create: `src/quantum_trainer/risk.py`
- Create: `src/quantum_trainer/trade_plan.py`
- Modify: `src/quantum_trainer/__init__.py`

- [ ] **Step 1: Implement dataclasses and deterministic logic**

Risk gate must not mutate signals. Trade plan must use the latest backtest position and current weights.

- [ ] **Step 2: Run tests**

Run: `.\.venv\Scripts\python.exe -m pytest .\tests -v`

Expected: PASS.

### Task 3: Trainer Report Tests

**Files:**
- Create: `tests/test_trainer.py`

- [ ] **Step 1: Write failing test**

The test must verify `run_daily_trainer()` writes a dated trade plan CSV and decision report Markdown.

- [ ] **Step 2: Run tests**

Expected: FAIL because `trainer.py` does not exist.

### Task 4: Implement Trainer And CLI

**Files:**
- Create: `src/quantum_trainer/trainer.py`
- Create: `scripts/run_daily_trainer.py`
- Modify: `src/quantum_trainer/config.py`
- Modify: `configs/portfolio.yaml`
- Modify: `configs/sample_portfolio.yaml`
- Modify: `README.md`

- [ ] **Step 1: Add `RiskConfig` to runtime config**

YAML section name: `risk`.

- [ ] **Step 2: Implement daily trainer**

Load prices, run backtest, evaluate risk, generate trade plan, write daily reports.

- [ ] **Step 3: Add CLI runner**

Run: `.\.venv\Scripts\python.exe .\scripts\run_daily_trainer.py --config .\configs\sample_portfolio.yaml`

Expected: daily report files under `reports/sample/daily`.

### Task 5: Verification

- [ ] **Step 1: Run all tests**

Run: `.\.venv\Scripts\python.exe -m pytest .\tests -v`

Expected: PASS.

- [ ] **Step 2: Compile Python files**

Run: `.\.venv\Scripts\python.exe -m compileall .\src .\scripts`

Expected: PASS.

No git commands are allowed for this plan because the user restricted work to `quantum_stocks_cache`, while `.git` is outside that folder.

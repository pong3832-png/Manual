# Dynamic Trend Trainer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-only pandas vectorized Dynamic Trend Following trainer that can backtest cached KOSPI price CSV files and emit operating reports.

**Architecture:** The core engine computes SMA signals, delayed positions, transaction-cost-adjusted returns, equity curves, and performance metrics. Config and IO are isolated from the vectorized backtest core so the strategy can be tested without filesystem dependencies.

**Tech Stack:** Python 3.10+, pandas, numpy, PyYAML, pytest, pathlib, logging, type hints.

---

### Task 1: Test First

**Files:**
- Create: `tests/test_trend_engine.py`

- [ ] **Step 1: Write failing tests**

Tests must import `quantum_trainer.trend`, verify `shift(1)` behavior, verify cash exposure after a downside break, and verify MDD improvement.

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest tests -v`

Expected: FAIL because `quantum_trainer` does not exist.

### Task 2: Core Trend Engine

**Files:**
- Create: `src/quantum_trainer/__init__.py`
- Create: `src/quantum_trainer/trend.py`

- [ ] **Step 1: Implement `BacktestConfig`, `BacktestResult`, `run_dynamic_trend_backtest`, and `summarize_performance`**

Use vectorized pandas operations only. No row loop.

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests -v`

Expected: PASS.

### Task 3: Config, IO, CLI

**Files:**
- Create: `src/quantum_trainer/config.py`
- Create: `src/quantum_trainer/io.py`
- Create: `scripts/run_backtest.py`
- Create: `configs/portfolio.yaml`
- Create: `README.md`

- [ ] **Step 1: Add YAML config loader**

Load symbols, weights, price CSV path, report directory, trend window, cost basis points, and annualization periods.

- [ ] **Step 2: Add CSV loader and report writer**

Write equity curve, positions, and performance summary.

- [ ] **Step 3: Add CLI runner**

Run: `python scripts/run_backtest.py --config configs/portfolio.yaml`

Expected: Clear error if `data/prices.csv` is missing; report files if present.

### Task 4: Local Environment

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: Create `.venv` inside `quantum_stocks_cache` only**

Run: `python -m venv .venv`

- [ ] **Step 2: Install dependencies into local venv only**

Run: `.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements.txt`

- [ ] **Step 3: Run verification**

Run: `.venv\Scripts\python.exe -m pytest tests -v`

Expected: PASS.

Git commits are intentionally omitted because the user explicitly restricted work to `quantum_stocks_cache` only; committing would modify `.git` outside that folder.

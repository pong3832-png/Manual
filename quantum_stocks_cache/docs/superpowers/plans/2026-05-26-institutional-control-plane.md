# Institutional Control Plane V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local institutional control plane that validates data, risk-checks trade plans, and writes registry, ledger, and investment committee artifacts.

**Architecture:** Existing market data, trend, sizing, risk, and daily trainer modules stay intact. New governance modules wrap them, with deterministic outputs and tests at each boundary.

**Tech Stack:** Python 3.10+, pandas, PyYAML, pytest, pathlib, dataclasses, hashlib, json, logging.

---

### Task 1: Data Quality Gate

**Files:**
- Create: `tests/test_institutional_control_plane.py`
- Create: `src/quantum_trainer/data_quality.py`

- [ ] **Step 1: Write failing tests**

Tests verify missing symbol failure, stale data failure, and pass result for clean data.

- [ ] **Step 2: Implement `DataQualityConfig`, `DataQualityResult`, and `validate_price_data`**

The implementation returns status, reason codes, and metrics without mutating prices.

### Task 2: Pre-Trade Gate

**Files:**
- Modify: `tests/test_institutional_control_plane.py`
- Create: `src/quantum_trainer/pretrade.py`

- [ ] **Step 1: Write failing tests**

Tests verify excessive order delta is blocked and clean trade plan passes.

- [ ] **Step 2: Implement `PreTradeConfig`, `PreTradeResult`, and `apply_pretrade_checks`**

The implementation appends `pretrade_status` and `pretrade_reason_codes` columns.

### Task 3: Registry And Ledger

**Files:**
- Modify: `tests/test_institutional_control_plane.py`
- Create: `src/quantum_trainer/model_registry.py`
- Create: `src/quantum_trainer/research_ledger.py`

- [ ] **Step 1: Write failing tests**

Tests verify registry JSON and ledger CSV are written with run id, config hash, symbols, and statuses.

- [ ] **Step 2: Implement registry and ledger writers**

Writers create parent directories and return output paths.

### Task 4: Investment Committee Report

**Files:**
- Modify: `tests/test_institutional_control_plane.py`
- Create: `src/quantum_trainer/investment_committee.py`

- [ ] **Step 1: Write failing test**

Test verifies Markdown report contains run id, data quality status, risk status, and pre-trade status.

- [ ] **Step 2: Implement report renderer**

Use internal Markdown table rendering; do not add optional dependencies.

### Task 5: Institutional Orchestrator

**Files:**
- Modify: `tests/test_institutional_control_plane.py`
- Create: `src/quantum_trainer/institutional_trainer.py`
- Create: `scripts/run_institutional_trainer.py`
- Modify: `src/quantum_trainer/config.py`
- Modify: `configs/portfolio.yaml`
- Modify: `README.md`

- [ ] **Step 1: Write failing integration test**

Test verifies one run writes run directory, IC report, registry JSON, ledger CSV, and checked trade plan.

- [ ] **Step 2: Implement orchestrator and CLI**

The CLI runs with `--config` and optional `--skip-market-data-update`.

### Task 6: Verification

- [ ] **Step 1: Run tests**

Run: `.\.venv\Scripts\python.exe -m pytest .\tests -v`

Expected: all pass.

- [ ] **Step 2: Compile**

Run: `.\.venv\Scripts\python.exe -m compileall .\src .\scripts`

Expected: pass.

- [ ] **Step 3: Run real institutional trainer**

Run: `.\.venv\Scripts\python.exe .\scripts\run_institutional_trainer.py --config .\configs\portfolio.yaml --skip-market-data-update`

Expected: run artifacts are written under `reports/runs`.

No git commands are allowed because `.git` is outside `quantum_stocks_cache`.

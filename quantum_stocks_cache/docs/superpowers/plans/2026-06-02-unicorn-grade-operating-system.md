# Unicorn-Grade Operating System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the stock research cache into a disciplined, repeatable, no-order investment research operating system.

**Architecture:** Keep all decisions evidence-first and local-report-first. Separate data ingestion, evidence review, ranking, manual gates, dashboard display, and final no-order decision so no single signal can accidentally become a buy instruction.

**Tech Stack:** Python CLI scripts, CSV/Markdown reports, local cached prices, OpenDART only with explicit approval, pytest/py_compile verification.

---

## Operating Principles

- Every generated decision must keep `order_status=NO_ORDER`.
- `BUY_READY`, `READY_REVIEW`, `CORE_FOCUS`, and nonzero sizing are research labels only.
- No external API, OpenDART fetch, market-data refresh, broker action, scheduler change, delete, commit, or push without explicit approval.
- `configs/manual_review.actual.csv` is human-confirmed only. Proposal files are not active config.
- The dashboard can prioritize event names visually, but raw ranking must remain traceable through `reports/event_adjusted_ranking/event_adjusted_ranking.csv`.

## Priority Board

| Priority | Workstream | Outcome | Owner Mode |
|---:|---|---|---|
| P0 | Safety rails | No accidental order, config write, or external refresh | Mandatory |
| P1 | Komico evidence closure | Filing PASS candidate, valuation UNKNOWN, final WAIT | Current focus |
| P1 | Manual gate workflow | Six gate proposal is clear and not auto-applied | Current focus |
| P1 | Dashboard/pre-buy truth | UI and pre-buy decision say WAIT / NO_ORDER | Current focus |
| P2 | Peer comparison | Komico vs Neotis/Selemix/PeptRon risk ranking | Current focus |
| P2 | Valuation data quality | Missing fundamentals are surfaced, not guessed | Next |
| P3 | Automation hardening | Tests prevent stale HOLD_REVIEW/PER=0 regressions | Next |
| P3 | Operator UX | One-page daily board shows what to do next | Next |

## Task 1: Freeze The Safety Contract

**Files:**
- Inspect: `AGENTS.md`
- Inspect: `src/quantum_trainer/today_pipeline.py`
- Inspect: `src/quantum_trainer/pre_buy_decision.py` if present
- Inspect: `src/quantum_trainer/dashboard.py`
- Test: `tests/test_today_pipeline.py`
- Test: `tests/test_dashboard.py`

- [ ] **Step 1: Verify no-order invariants**

Run:

```powershell
rg "NO_ORDER|broker_order_requested|actual_config_written|refresh_market_data" .\src .\scripts .\tests
```

Expected: all order-related paths are explicit report fields or blockers. No broker execution path exists.

- [ ] **Step 2: Add or tighten tests if a gap is found**

Required assertions:

```python
assert "NO_ORDER" in output_text
assert "actual_config_written=NO" in cli_output
assert "broker_order_requested=NO" in output_text or "broker" not in output_text.lower()
```

- [ ] **Step 3: Run focused verification**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest .\tests\test_today_pipeline.py .\tests\test_dashboard.py -q
```

Expected: tests pass. If they fail, fix safety regressions before doing any ranking work.

## Task 2: Close Komico Filing Review

**Files:**
- Inspect: `reports/filing_review/filing_risk_summary_183300.md`
- Inspect: `reports/filing_review/filing_risk_summary_183300.csv`
- Modify only if needed: `reports/decision_gate/manual_review_proposal.csv`
- Modify only via script: `reports/decision_gate/manual_review_proposal.md`

- [ ] **Step 1: Confirm HOLD_REVIEW root cause**

Check these exact items:

```text
fatal_risk = NO
Regulatory/accounting litigation overhang evidence_count = 0
gate_opinion = PASS_CANDIDATE_WITH_MONITORING after manual resolution
```

- [ ] **Step 2: Keep the conclusion conservative**

Required conclusion:

```text
filing_review = PASS candidate
monitoring = required
manual_review.actual.csv = unchanged
order_status = NO_ORDER
```

- [ ] **Step 3: Regenerate proposal only**

Run:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_manual_review_proposal.py
```

Expected:

```text
actual_config_written=NO
183300.KQ INCOMPLETE_DRAFT
filing_review PASS
valuation_review UNKNOWN
```

## Task 3: Make Komico Valuation Decision Explicit

**Files:**
- Inspect: `configs/fundamentals.actual.csv`
- Inspect: `configs/shares_outstanding.actual.csv`
- Inspect: `data/prices.csv`
- Inspect: `reports/pre_buy_decision/pre_buy_decision.csv`
- Modify: `reports/investment_thesis/investment_thesis_183300.md`

- [ ] **Step 1: Extract confirmed local valuation facts**

Required fields:

```text
latest_price = 90,000
PER = 40.08
PBR = 4.75
ROE = 19.69%
total liabilities/equity = about 214.5%
market cap = about 1.81 trillion KRW
```

- [ ] **Step 2: Decide the valuation gate**

Required output:

```text
valuation_review = UNKNOWN
reason = premium PER/PBR; not obviously cheap
decision = WAIT / NO_ORDER
```

- [ ] **Step 3: If inputs are missing, do not guess**

If local CSVs do not contain the values, stop and ask for approval before running:

```powershell
.\.venv\Scripts\python.exe .\scripts\fetch_opendart_fundamentals.py ...
.\.venv\Scripts\python.exe .\scripts\fetch_opendart_shares.py ...
.\.venv\Scripts\python.exe .\scripts\run_today_pipeline.py --refresh-market-data
```

## Task 4: Compare The Real Alternatives

**Files:**
- Inspect: `reports/filing_review/filing_risk_summary_085910.md`
- Inspect: `reports/filing_review/filing_risk_summary_331920.md`
- Inspect: `reports/filing_review/filing_risk_summary_087010.md`
- Inspect: `reports/event_adjusted_ranking/event_adjusted_ranking.csv`
- Modify: `reports/investment_thesis/top_candidate_filing_comparison_YYYY-MM-DD.md`

- [ ] **Step 1: Score each alternative**

Use this comparison table:

```text
Komico: filing PASS candidate, valuation UNKNOWN, event WAIT_PULLBACK, 1st priority
Neotis: filing PASS candidate, valuation UNKNOWN, lower thesis strength, not 1st
Selemix: filing HOLD_REVIEW, valuation UNKNOWN, not 1st
PeptRon: filing HOLD_REVIEW, valuation UNKNOWN, not 1st
GST/LS/LG CNS: reference only unless their local reports improve
```

- [ ] **Step 2: Write five risks per candidate**

Each candidate must include:

```text
legal/litigation
regulatory/accounting
derivative/commitments
affiliate/related-party
project/operating execution
```

- [ ] **Step 3: Preserve the final ranking**

Required conclusion:

```text
Komico remains 1st research candidate.
No candidate is approved for buying.
Final action remains WAIT / NO_ORDER.
```

## Task 5: Make The Six Manual Gates Operator-Ready

**Files:**
- Inspect: `reports/decision_gate/manual_review_draft.csv`
- Inspect: `reports/decision_gate/manual_review_proposal.csv`
- Do not modify: `configs/manual_review.actual.csv`

- [ ] **Step 1: Confirm six gate candidates**

Required Komico candidate state:

```text
filing_review = PASS candidate
earnings_review = PASS candidate
business_driver_review = PASS candidate
valuation_review = UNKNOWN
loss_rule_review = PASS candidate
capital_plan_review = PASS candidate
```

- [ ] **Step 2: Confirm why overall status is still incomplete**

Required blocker:

```text
manual_proposal_status = INCOMPLETE_DRAFT
reason = valuation_review UNKNOWN
```

- [ ] **Step 3: Do not apply actual config**

Forbidden without explicit user confirmation:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_manual_review_apply_plan.py --confirm-final-review I_CONFIRM_MANUAL_REVIEW
```

## Task 6: Regenerate Only The Necessary User-Facing Outputs

**Files:**
- Modify via script: `reports/pre_buy_decision/pre_buy_decision.csv`
- Modify via script: `reports/pre_buy_decision/pre_buy_decision.md`
- Modify via script: `reports/dashboard/index.html`

- [ ] **Step 1: Regenerate pre-buy decision**

Run:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_pre_buy_decision.py
```

Expected:

```text
183300.KQ WAIT NO_ORDER
readiness_blockers includes manual gate not ready
```

- [ ] **Step 2: Regenerate dashboard**

Run:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_dashboard.py --reports-dir .\reports
```

Expected:

```text
top_symbol=183300.KQ
decision_gate_status=WAITING_MANUAL_EVIDENCE
order_status=NO_ORDER
```

- [ ] **Step 3: Verify rendered evidence**

Run:

```powershell
rg "코미코|183300\.KQ|NO_ORDER|눌림 대기" .\reports\dashboard\index.html
```

Expected: Komico appears as top candidate, but the action remains wait/no-order.

## Task 7: Build Regression Tests For Stale Evidence

**Files:**
- Test: `tests/test_manual_review_proposal.py` if present, otherwise create it
- Test: `tests/test_pre_buy_decision.py`
- Test: `tests/test_dashboard.py`

- [ ] **Step 1: Add a test for resolved filing HOLD_REVIEW**

Test intent:

```python
def test_resolved_filing_hold_review_does_not_block_as_fatal():
    row = build_pre_buy_decision_row(
        filing_opinion="PASS_CANDIDATE_WITH_MONITORING",
        fatal_risk_count=0,
        valuation_review="UNKNOWN",
    )
    assert row.decision_status == "WAIT"
    assert row.order_status == "NO_ORDER"
    assert "fatal" not in row.readiness_blockers.lower()
```

- [ ] **Step 2: Add a test for premium valuation**

Test intent:

```python
def test_premium_per_pbr_keeps_valuation_unknown():
    result = classify_valuation(per=40.08, pbr=4.75, roe=0.1969)
    assert result.review == "UNKNOWN"
    assert "premium" in result.reason.lower()
```

- [ ] **Step 3: Run focused tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest .\tests\test_pre_buy_decision.py .\tests\test_dashboard.py -q
```

Expected: tests pass with no dashboard/order regression.

## Task 8: Define The Daily Operating Cadence

**Files:**
- Modify: `docs/work-log.md`
- Optional new doc: `docs/daily-operating-checklist.md`

- [ ] **Step 1: Start each session with a tiny status check**

Run:

```powershell
git status --short -- .
Get-Content -Encoding UTF8 -LiteralPath .\docs\work-log.md -TotalCount 60
```

Expected: know what changed and what the last decision was without full repo reanalysis.

- [ ] **Step 2: Use this daily order**

Daily sequence:

```text
1. Safety state: NO_ORDER, no external refresh
2. Top candidate: pre_buy_decision and dashboard
3. Evidence blockers: filing, valuation, manual gates
4. Peer alternative: only compare real contenders
5. Output refresh: pre-buy and dashboard only
6. Work log: short handoff
```

- [ ] **Step 3: Escalate only when local evidence is insufficient**

Ask for approval before:

```text
OpenDART fetch
market data refresh
manual actual config write
trade journal actual edits
order sizing with real capital
git commit/push
```

## Definition Of Done

- Komico has a one-page thesis with `WAIT / NO_ORDER`.
- Filing review is no longer blocked by a keyword-only HOLD_REVIEW.
- Valuation remains explicitly `UNKNOWN` because the stock is not clearly cheap.
- Peer comparison explains why Komico remains 1st, and why every peer is still no-order.
- Manual review proposal is regenerated with `actual_config_written=NO`.
- Dashboard and pre-buy decision are regenerated and both show `NO_ORDER`.
- Work log records what changed and what remains blocked.

## Execution Choice

Plan complete and saved to `docs/superpowers/plans/2026-06-02-unicorn-grade-operating-system.md`.

Execution options:

1. Subagent-Driven: split independent tasks into focused implementation/review passes.
2. Inline Execution: execute the checklist in this session with checkpoints.

Recommended next step: Inline Execution for Tasks 1-6, then decide whether Task 7 tests are worth adding now.

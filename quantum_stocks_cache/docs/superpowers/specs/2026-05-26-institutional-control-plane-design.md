# Institutional Control Plane V1 Design

## Scope

Build an institutional-style control plane on top of the existing quant trainer.

The system must remain local-only inside `quantum_stocks_cache`. It does not place broker orders. It produces validated, risk-gated, auditable trade plans from real market data.

## Architecture

The control plane adds governance layers around the existing engine:

- `data_quality.py`: validate cached market data before any signal or trade plan is trusted.
- `model_registry.py`: record strategy version, config hash, symbol universe, and generated artifacts.
- `research_ledger.py`: append immutable run summaries to local CSV ledger.
- `pretrade.py`: enforce trade-level risk limits after target weights are generated.
- `investment_committee.py`: render a concise institutional decision memo.
- `institutional_trainer.py`: orchestrate market data update, validation, daily trainer, pre-trade checks, registry, ledger, and report creation.

## Institutional Run Flow

1. Load `configs/portfolio.yaml`.
2. Optionally update real market data.
3. Validate `data/prices.csv`.
4. Run the existing daily trainer.
5. Apply pre-trade risk checks to the trade plan.
6. Generate an investment committee report.
7. Save a model registry record.
8. Append a research ledger row.

## Data Quality Gate

Rules:

- all configured symbols must exist
- no missing values after cleaning
- latest date must not be older than configured stale-day threshold
- absolute daily return must not exceed configured jump threshold

If the data quality gate fails, no trade plan should be trusted.

## Pre-Trade Gate

Rules:

- target gross exposure must not exceed configured maximum
- single order delta must not exceed configured maximum
- blocked risk state must prevent new buy exposure

Pre-trade output is appended to the final trade plan as `pretrade_status` and `pretrade_reason_codes`.

## Audit Artifacts

Every institutional run writes:

- `reports/runs/<run_id>/investment_committee_report.md`
- `reports/runs/<run_id>/trade_plan.csv`
- `reports/runs/<run_id>/pretrade_checked_trade_plan.csv`
- `models/registry/<run_id>.json`
- `ledger/research_ledger.csv`

## Risk Position

The system is a decision-support and trade-plan generator. It does not execute orders. This keeps the current phase below broker execution risk while adding institutional controls.

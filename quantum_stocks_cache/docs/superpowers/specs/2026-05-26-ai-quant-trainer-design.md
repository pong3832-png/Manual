# AI Quant Trainer Design

## Scope

Extend `quantum_stocks_cache` from a backtest engine into a local-only operating trainer.

The trainer consumes cached prices, runs the Dynamic Trend Following engine, evaluates risk gates, produces target weights, and writes a daily trade plan plus Markdown decision report.

No broker order is executed in this phase.

## Operating Model

The trainer acts as:

- `Quant Engine`: computes signals, delayed positions, returns, CAGR, MDD, turnover, and cash exposure.
- `Risk Officer`: blocks new exposure when portfolio risk exceeds limits.
- `Trade Planner`: converts target weights into actions.
- `Audit Logger`: writes reproducible CSV and Markdown reports.

AI narrative is constrained to explaining already-computed numbers. It does not overwrite signals.

## Risk Gate

Risk configuration:

- `max_portfolio_mdd`: block new entries when current dynamic-trend drawdown is below this threshold.
- `max_daily_turnover`: require manual review when latest turnover exceeds this threshold.
- `max_cash_exposure`: require manual review when cash exposure exceeds this threshold.

Risk states:

- `PASS`: plan can be followed.
- `REVIEW`: plan is generated but requires manual review.
- `BLOCK`: new buys are blocked; exits to cash remain allowed.

## Trade Plan

Per symbol:

- Latest target weight = `strategic_weight * latest_position`.
- If latest position is 0 and current weight is positive: `SELL_TO_CASH`.
- If latest position is 1 and current weight is below target: `BUY_TO_TARGET`.
- If current and target are effectively equal: `HOLD`.
- If risk state is `BLOCK`, new `BUY_TO_TARGET` actions become `HOLD_BLOCKED`.

## Reports

Daily trainer output:

- `daily/YYYY-MM-DD_trade_plan.csv`
- `daily/YYYY-MM-DD_decision_report.md`

The report includes:

- portfolio regime
- risk gate status
- latest CAGR/MDD summary
- per-symbol action table
- cash exposure
- warning codes

## Constraints

All implementation, tests, generated reports, and local environment files stay under `quantum_stocks_cache`.

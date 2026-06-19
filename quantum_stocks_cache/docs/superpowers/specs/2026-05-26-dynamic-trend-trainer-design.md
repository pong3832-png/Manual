# Dynamic Trend Trainer Design

## Scope

Build a local-only Phase 2 quant trainer inside `quantum_stocks_cache`.

The system must backtest a weighted KOSPI large-cap portfolio using a 20-day moving-average cash switch:

- Hold an asset when `Close > SMA20`.
- Move that asset allocation to cash when `Close <= SMA20`.
- Re-enter after the next confirmed upside signal.
- Apply positions with `shift(1)` to remove look-ahead bias.

## Architecture

The package is split into focused modules:

- `quantum_trainer.trend`: vectorized pandas backtest and performance metrics.
- `quantum_trainer.config`: YAML config loading.
- `quantum_trainer.io`: price CSV loading and report writing.
- `scripts/run_backtest.py`: command-line runner.

No network call is part of this phase. The runner consumes cached local CSV data only.

## Data Contract

Input price CSV format:

```csv
date,000660.KS,005380.KS
2025-01-02,170000,220000
```

Rules:

- `date` is parsed as index.
- All non-date columns are treated as adjusted close price series.
- Missing values are forward-filled, then rows with remaining missing values are dropped.

## Backtest Contract

For each asset:

```python
sma = prices.rolling(window=trend_window, min_periods=trend_window).mean()
signal = (prices > sma).astype(float).where(sma.notna(), 0.0)
position = signal.shift(1).fillna(0.0)
strategy_return = (position * asset_return * weight).sum(axis=1) - trading_cost
```

Portfolio-level reports:

- `equity_curve.csv`
- `position_matrix.csv`
- `performance_summary.csv`

## Risk Controls

- `shift(1)` is mandatory.
- Warm-up period exposure is zero.
- Transaction costs are included via `cost_bps`.
- Cash exposure is measured as `1 - weighted_position`.
- MDD improvement is reported in percentage points.

## Testing

Tests cover:

- Look-ahead prevention.
- Cash switch after downside SMA break.
- MDD improvement versus buy-and-hold in a deterministic crash path.
- Report schema stability.

## Constraints

All files, generated reports, virtual environment, and cache artifacts stay inside `quantum_stocks_cache`.

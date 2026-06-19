# Alpha Forecast And Buy Timing V1 Design

## Scope

Add an alpha forecast layer that estimates next-20-trading-day return, upside probability, and buy timing decision for configured listed stocks.

The layer is decision-support only. It does not execute orders and does not override the institutional risk gates.

## Architecture

- `features.py`: create per-symbol technical/statistical features from cached close prices.
- `alpha_forecast.py`: train a local linear alpha model per symbol using historical features and forward returns.
- `buy_timing.py`: convert forecast outputs into score and decision labels.
- `scripts/run_alpha_research.py`: run the layer and write reports under `reports/alpha`.

No external ML library is required in V1. The model uses a small Ridge-style linear regression implemented with `numpy.linalg.solve`.

## Features

Per symbol:

- `return_5d`
- `return_20d`
- `ma20_gap`
- `ma60_gap`
- `realized_vol_20d`
- `drawdown_20d`

Forward labels:

- `forward_20d_return`
- `forward_20d_upside`

## Forecast Output

Per symbol:

- `expected_20d_return`
- `upside_probability`
- `buy_timing_score`
- `decision`
- `sample_count`
- `model_r2`

Decision labels:

- `BUY_READY`: strong positive forecast and probability
- `WAIT`: positive but not enough edge
- `REDUCE`: trend/risk context says exposure should be cut
- `AVOID`: negative forecast or weak upside probability

## Guardrails

- Minimum historical sample count required before a forecast is trusted.
- Predictions are clipped to configurable return bounds.
- Probability is clipped to `[0.01, 0.99]`.
- Output is written as a research report, not an execution instruction.

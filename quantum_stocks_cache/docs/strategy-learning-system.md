# Strategy Learning System

Date: 2026-06-05

## Boundary

This project can learn from public market data, public filings, public financial statements, public academic research, and locally generated prediction outcomes.

It must not use private hedge-fund models, broker-confidential routing logic, corporate inside information, leaked research, non-public order flow, credentials, or any source that would create legal or operational risk.

All generated signals remain review-only. Every learning report must keep:

```text
external_api_requested=NO
order_status=NO_ORDER
broker_order_requested=NO
```

## Learning Loop

The practical learning loop is:

1. Generate a forecast from local evidence.
2. Save the forecast as a timestamped prediction snapshot.
3. Wait until the forecast horizon is observable in `data/prices.csv`.
4. Compare predicted return/direction with realized return/direction.
5. Measure error, bias, directional accuracy, and BUY_READY hit rate.
6. Promote a feature or threshold only after walk-forward evidence improves.

Current implementation:

```text
scripts/run_learning_feedback.py
src/quantum_trainer/learning_feedback.py
reports/learning_feedback/alpha_prediction_snapshots.csv
reports/learning_feedback/alpha_prediction_outcomes.csv
reports/learning_feedback/learning_feedback_summary.csv
reports/learning_feedback/learning_feedback.md
```

## Public Research Seed Library

These are starting points for translating public research into testable local signals. A paper is not a buy rule. Each item must be converted into local features, backtested, and reviewed for Korea-market fit.

| Theme | Public source | Local feature direction | Gate before use |
|---|---|---|---|
| Cross-sectional momentum | Jegadeesh and Titman, 1993, Journal of Finance, "Returns to Buying Winners and Selling Losers" | 3-12 month relative strength, trend persistence, pullback control | Must avoid chase risk and sector overextension |
| Value / profitability / investment | Fama and French, 2015, Journal of Financial Economics, "A Five-Factor Asset Pricing Model" | PER/PBR, profitability, asset growth, investment intensity | Needs complete OpenDART fundamentals |
| Value plus momentum across assets | Asness, Moskowitz, and Pedersen, 2013, Journal of Finance, "Value and Momentum Everywhere" | Combine cheapness with relative strength; avoid one-factor concentration | Must compare combined score vs standalone factors |
| Machine-learning asset pricing | Gu, Kelly, and Xiu, 2020, Review of Financial Studies, "Empirical Asset Pricing via Machine Learning" | Nonlinear interactions among momentum, liquidity, volatility, valuation | Must use walk-forward validation and out-of-sample metrics |
| Earnings quality / accruals | Sloan, 1996, The Accounting Review, "Do Stock Prices Fully Reflect Information in Accruals and Cash Flows About Future Earnings?" | Accrual quality, cash-flow backed earnings, receivables/inventory risk | Needs normalized financial statement fields |
| Distress risk | Campbell, Hilscher, and Szilagyi, 2008, Journal of Finance, "In Search of Distress Risk" | Leverage, volatility, drawdown, profitability weakness, failure-risk proxy | Must act as reject/risk gate, not high-return lottery signal |
| Low-beta / low-volatility | Frazzini and Pedersen, 2014, Journal of Financial Economics, "Betting Against Beta" | Volatility/beta penalty, quality defensive preference | Must not blindly prefer illiquid low-vol stocks |
| Post-earnings drift | Bernard and Thomas, 1989, Journal of Accounting Research, "Post-Earnings-Announcement Drift" | Earnings surprise persistence and revision drift | Needs earnings announcement calendar and surprise proxy |

Source links:

- https://academic.oup.com/rfs/article/33/5/2223/5758276
- https://doi.org/10.1016/j.jfineco.2014.10.010
- https://doi.org/10.1111/jofi.12021
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2598
- https://dash.harvard.edu/handle/1/3199070
- https://research.cbs.dk/en/publications/betting-against-beta/
- https://cir.nii.ac.jp/crid/1360576121027825152

## Model Policy

Start simple and measurable:

```text
baseline: existing ridge alpha forecast
candidate: enhanced factor set or ML model
promotion rule: candidate improves walk-forward directional accuracy and does not worsen MAE materially
deployment: report-only first, no automatic order execution
```

Acceptable model classes:

- Ridge/linear models for baseline transparency.
- Tree or ensemble models only after a no-new-dependency implementation path or an approved dependency install.
- Feature interaction scores when they can be explained and tested.

Blocked model behavior:

- No look-ahead labels.
- No training on future data.
- No automatic config overwrite from one good run.
- No hidden broker/order API.
- No model promotion without a written report and test evidence.

## Next Features To Convert

1. Add prediction snapshots to the normal daily pipeline after `run_alpha_research`.
2. Add a `panic_rebound_signal` module:
   - sharp drawdown
   - volume expansion
   - lower-tail reversal
   - MA/VWAP reclaim when available
   - foreign/institutional flow when locally available
   - filing/earnings risk blockers
3. Add a fundamentals quality feature set:
   - ROE
   - debt ratio
   - sales/profit growth
   - cash-flow backed earnings
   - valuation percentile by sector
4. Add model comparison:
   - baseline ridge
   - enhanced ridge
   - future approved ML model
   - walk-forward report by market regime

## Interpretation

The system should learn by accumulating forecast errors, not by forcing BUY_READY. If the market is defensive or manual gates are unknown, the final decision stays `WAIT / NO_ORDER` even when a learning model improves.

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.trend import BacktestConfig, run_dynamic_trend_backtest


def test_positions_are_shifted_to_prevent_lookahead_bias() -> None:
    dates = pd.date_range("2026-01-01", periods=8, freq="B")
    prices = pd.DataFrame({"000660.KS": [10, 11, 12, 13, 14, 13, 12, 11]}, index=dates)
    config = BacktestConfig(weights={"000660.KS": 1.0}, trend_window=3, cost_bps=0.0)

    result = run_dynamic_trend_backtest(prices, config)

    position = result.positions["000660.KS"]
    assert position.iloc[2] == 0.0
    assert position.iloc[3] == 1.0


def test_strategy_moves_to_cash_after_downside_sma_break() -> None:
    dates = pd.date_range("2026-01-01", periods=8, freq="B")
    prices = pd.DataFrame({"000660.KS": [10, 11, 12, 13, 14, 13, 12, 11]}, index=dates)
    config = BacktestConfig(weights={"000660.KS": 1.0}, trend_window=3, cost_bps=0.0)

    result = run_dynamic_trend_backtest(prices, config)

    assert result.positions["000660.KS"].iloc[6] == 0.0
    assert result.equity_curve["dynamic_ret"].iloc[6] == 0.0
    assert result.equity_curve["cash_exposure"].iloc[6] == 1.0


def test_dynamic_trend_reduces_mdd_during_persistent_crash() -> None:
    dates = pd.date_range("2026-01-01", periods=13, freq="B")
    prices = pd.DataFrame(
        {"000660.KS": [100, 101, 102, 103, 104, 90, 80, 70, 60, 50, 55, 60, 65]},
        index=dates,
    )
    config = BacktestConfig(weights={"000660.KS": 1.0}, trend_window=3, cost_bps=0.0)

    result = run_dynamic_trend_backtest(prices, config)
    summary = result.performance_summary

    buy_hold_mdd = float(summary.loc["buy_hold", "MDD"])
    dynamic_mdd = float(summary.loc["dynamic_trend", "MDD"])
    assert dynamic_mdd > buy_hold_mdd
    assert float(summary.loc["dynamic_trend", "MDD_Improvement_ppt"]) > 0.0

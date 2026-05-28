from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.risk import RiskConfig, evaluate_risk
from quantum_trainer.trade_plan import generate_trade_plan
from quantum_trainer.trend import BacktestConfig, run_dynamic_trend_backtest


def _single_asset_result(prices: list[float]) -> object:
    dates = pd.date_range("2026-01-01", periods=len(prices), freq="B")
    price_df = pd.DataFrame({"000660.KS": prices}, index=dates)
    return run_dynamic_trend_backtest(
        price_df,
        BacktestConfig(weights={"000660.KS": 1.0}, trend_window=3, cost_bps=0.0),
    )


def test_risk_gate_blocks_new_entries_when_mdd_limit_is_breached() -> None:
    result = _single_asset_result([100, 101, 102, 103, 104, 90, 80, 70, 60, 50])

    risk = evaluate_risk(result, RiskConfig(max_portfolio_mdd=-0.02))

    assert risk.status == "BLOCK"
    assert risk.allow_new_entries is False
    assert "MDD_LIMIT_BREACH" in risk.reason_codes


def test_risk_gate_requires_review_when_cash_exposure_is_high() -> None:
    result = _single_asset_result([10, 11, 12, 13, 14, 13, 12, 11])

    risk = evaluate_risk(result, RiskConfig(max_cash_exposure=0.50))

    assert risk.status == "REVIEW"
    assert risk.allow_new_entries is True
    assert "HIGH_CASH_EXPOSURE" in risk.reason_codes


def test_downside_sma_break_generates_sell_to_cash() -> None:
    result = _single_asset_result([10, 11, 12, 13, 14, 13, 12, 11])
    risk = evaluate_risk(result, RiskConfig(max_cash_exposure=1.0))

    trade_plan = generate_trade_plan(
        result=result,
        risk=risk,
        strategic_weights={"000660.KS": 1.0},
        current_weights={"000660.KS": 1.0},
    )

    row = trade_plan.loc["000660.KS"]
    assert row["action"] == "SELL_TO_CASH"
    assert row["target_weight"] == 0.0


def test_upside_reentry_generates_buy_to_target() -> None:
    result = _single_asset_result([10, 9, 8, 7, 8, 9, 10])
    risk = evaluate_risk(result, RiskConfig())

    trade_plan = generate_trade_plan(
        result=result,
        risk=risk,
        strategic_weights={"000660.KS": 1.0},
        current_weights={"000660.KS": 0.0},
    )

    row = trade_plan.loc["000660.KS"]
    assert row["action"] == "BUY_TO_TARGET"
    assert row["target_weight"] == 1.0


def test_mdd_block_converts_new_buy_to_hold_blocked() -> None:
    reentry_result = _single_asset_result([10, 9, 8, 7, 8, 9, 10])
    crash_result = _single_asset_result([100, 101, 102, 103, 104, 90, 80, 70, 60, 50])
    blocked_risk = evaluate_risk(crash_result, RiskConfig(max_portfolio_mdd=-0.02))

    trade_plan = generate_trade_plan(
        result=reentry_result,
        risk=blocked_risk,
        strategic_weights={"000660.KS": 1.0},
        current_weights={"000660.KS": 0.0},
    )

    row = trade_plan.loc["000660.KS"]
    assert row["action"] == "HOLD_BLOCKED"
    assert row["target_weight"] == 0.0


def test_trade_plan_uses_volatility_sized_target_weights() -> None:
    result = _single_asset_result([10, 9, 8, 7, 8, 9, 10])
    risk = evaluate_risk(result, RiskConfig())

    trade_plan = generate_trade_plan(
        result=result,
        risk=risk,
        strategic_weights={"000660.KS": 1.0},
        current_weights={"000660.KS": 0.60},
        target_weights={"000660.KS": 0.30},
    )

    row = trade_plan.loc["000660.KS"]
    assert row["action"] == "REDUCE_TO_TARGET"
    assert row["target_weight"] == 0.30
    assert row["delta_weight"] == -0.30

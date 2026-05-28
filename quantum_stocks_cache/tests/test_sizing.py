from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.sizing import SizingConfig, calculate_volatility_adjusted_weights


def test_high_volatility_asset_is_scaled_below_strategic_weight() -> None:
    dates = pd.date_range("2026-01-01", periods=8, freq="B")
    prices = pd.DataFrame(
        {"000660.KS": [100, 120, 90, 125, 80, 130, 75, 135]},
        index=dates,
    )

    result = calculate_volatility_adjusted_weights(
        prices=prices,
        strategic_weights={"000660.KS": 0.60},
        latest_positions={"000660.KS": 1.0},
        config=SizingConfig(
            target_volatility=0.10,
            realized_vol_window=5,
            volatility_floor=0.01,
            max_position_weight=0.60,
        ),
        periods_per_year=252,
    )

    assert result.target_weights["000660.KS"] < 0.60
    assert result.realized_volatility["000660.KS"] > 0.10


def test_low_volatility_asset_is_capped_at_max_position_weight() -> None:
    dates = pd.date_range("2026-01-01", periods=8, freq="B")
    prices = pd.DataFrame(
        {"005380.KS": [100, 100.1, 100.2, 100.3, 100.4, 100.5, 100.6, 100.7]},
        index=dates,
    )

    result = calculate_volatility_adjusted_weights(
        prices=prices,
        strategic_weights={"005380.KS": 0.40},
        latest_positions={"005380.KS": 1.0},
        config=SizingConfig(
            target_volatility=0.20,
            realized_vol_window=5,
            volatility_floor=0.01,
            max_position_weight=0.40,
        ),
        periods_per_year=252,
    )

    assert result.target_weights["005380.KS"] == 0.40
    assert result.volatility_scalars["005380.KS"] >= 1.0


def test_asset_out_of_trend_gets_zero_target_weight() -> None:
    dates = pd.date_range("2026-01-01", periods=8, freq="B")
    prices = pd.DataFrame({"000660.KS": [100, 101, 102, 103, 104, 105, 106, 107]}, index=dates)

    result = calculate_volatility_adjusted_weights(
        prices=prices,
        strategic_weights={"000660.KS": 0.60},
        latest_positions={"000660.KS": 0.0},
        config=SizingConfig(),
        periods_per_year=252,
    )

    assert result.target_weights["000660.KS"] == 0.0

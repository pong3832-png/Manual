from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SizingConfig:
    enabled: bool = True
    target_volatility: float = 0.15
    realized_vol_window: int = 20
    volatility_floor: float = 0.05
    max_position_weight: float = 1.0
    max_leverage: float = 1.0


@dataclass(frozen=True)
class SizingResult:
    target_weights: Dict[str, float]
    realized_volatility: Dict[str, float]
    volatility_scalars: Dict[str, float]


def calculate_volatility_adjusted_weights(
    prices: pd.DataFrame,
    strategic_weights: Dict[str, float],
    latest_positions: Dict[str, float],
    config: SizingConfig,
    periods_per_year: int = 252,
) -> SizingResult:
    try:
        if prices.empty:
            raise ValueError("prices must not be empty.")
        if config.realized_vol_window < 2:
            raise ValueError("realized_vol_window must be >= 2.")
        if config.target_volatility <= 0:
            raise ValueError("target_volatility must be > 0.")
        if config.volatility_floor <= 0:
            raise ValueError("volatility_floor must be > 0.")

        returns = prices.sort_index().pct_change(fill_method=None).tail(config.realized_vol_window)
        realized_vol = returns.std(ddof=0) * np.sqrt(periods_per_year)

        target_weights: dict[str, float] = {}
        realized_map: dict[str, float] = {}
        scalar_map: dict[str, float] = {}

        for symbol, strategic_weight in strategic_weights.items():
            position = float(latest_positions.get(symbol, 0.0))
            base_target = float(strategic_weight) * position

            if not config.enabled or base_target <= 0.0:
                target_weights[symbol] = max(0.0, base_target)
                realized_map[symbol] = float(realized_vol.get(symbol, np.nan))
                scalar_map[symbol] = 1.0 if base_target > 0.0 else 0.0
                continue

            asset_vol = float(realized_vol.get(symbol, np.nan))
            if not np.isfinite(asset_vol):
                asset_vol = config.volatility_floor

            denominator = max(asset_vol, config.volatility_floor)
            scalar = min(config.max_leverage, config.target_volatility / denominator)
            sized_target = min(base_target * scalar, config.max_position_weight)

            target_weights[symbol] = max(0.0, float(sized_target))
            realized_map[symbol] = asset_vol
            scalar_map[symbol] = float(scalar)

        return SizingResult(
            target_weights=target_weights,
            realized_volatility=realized_map,
            volatility_scalars=scalar_map,
        )
    except Exception as exc:
        logger.exception("Volatility adjusted sizing failed: %s", exc)
        raise

from __future__ import annotations

import logging
from typing import Dict

import pandas as pd

from quantum_trainer.risk import RiskGateResult
from quantum_trainer.trend import BacktestResult

logger = logging.getLogger(__name__)


def _action(current_weight: float, target_weight: float, tolerance: float = 1e-6) -> str:
    if abs(current_weight - target_weight) <= tolerance:
        return "HOLD"
    if target_weight == 0.0 and current_weight > target_weight:
        return "SELL_TO_CASH"
    if target_weight > current_weight:
        return "BUY_TO_TARGET"
    return "REDUCE_TO_TARGET"


def generate_trade_plan(
    result: BacktestResult,
    risk: RiskGateResult,
    strategic_weights: Dict[str, float],
    current_weights: Dict[str, float] | None = None,
    target_weights: Dict[str, float] | None = None,
) -> pd.DataFrame:
    try:
        if result.positions.empty:
            raise ValueError("positions must not be empty.")

        current_weights = current_weights or {}
        latest_positions = result.positions.iloc[-1]
        rows: list[dict[str, float | str]] = []

        for symbol, strategic_weight in strategic_weights.items():
            position = float(latest_positions.get(symbol, 0.0))
            current_weight = float(current_weights.get(symbol, 0.0))
            target_weight = (
                float(target_weights.get(symbol, 0.0))
                if target_weights is not None
                else float(strategic_weight) * position
            )
            action = _action(current_weight, target_weight)

            if action == "BUY_TO_TARGET" and not risk.allow_new_entries:
                action = "HOLD_BLOCKED"
                target_weight = current_weight

            rows.append(
                {
                    "symbol": symbol,
                    "position": position,
                    "current_weight": current_weight,
                    "target_weight": target_weight,
                    "delta_weight": target_weight - current_weight,
                    "action": action,
                    "risk_status": risk.status,
                }
            )

        return pd.DataFrame(rows).set_index("symbol")
    except Exception as exc:
        logger.exception("Trade plan generation failed: %s", exc)
        raise

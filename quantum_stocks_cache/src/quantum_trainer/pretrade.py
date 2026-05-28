from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreTradeConfig:
    max_order_delta: float = 0.25
    max_gross_exposure: float = 1.0


@dataclass(frozen=True)
class PreTradeResult:
    status: str
    reason_codes: Tuple[str, ...]
    metrics: Dict[str, float]
    checked_trade_plan: pd.DataFrame


def apply_pretrade_checks(
    trade_plan: pd.DataFrame,
    config: PreTradeConfig,
) -> PreTradeResult:
    try:
        required = {"target_weight", "delta_weight", "action", "risk_status"}
        missing = required.difference(trade_plan.columns)
        if missing:
            raise ValueError(f"trade_plan missing required columns: {sorted(missing)}")

        checked = trade_plan.copy()
        gross_exposure = float(checked["target_weight"].abs().sum())
        max_order_delta = float(checked["delta_weight"].abs().max()) if not checked.empty else 0.0

        reason_codes: list[str] = []
        if gross_exposure > config.max_gross_exposure:
            reason_codes.append("MAX_GROSS_EXPOSURE")
        if max_order_delta > config.max_order_delta:
            reason_codes.append("MAX_ORDER_DELTA")
        if ((checked["risk_status"] == "BLOCK") & (checked["action"] == "BUY_TO_TARGET")).any():
            reason_codes.append("BLOCKED_RISK_BUY")

        status = "BLOCK" if reason_codes else "PASS"
        reason_text = ",".join(reason_codes)
        checked["pretrade_status"] = status
        checked["pretrade_reason_codes"] = reason_text if reason_text else "NONE"

        return PreTradeResult(
            status=status,
            reason_codes=tuple(reason_codes),
            metrics={
                "gross_exposure": gross_exposure,
                "max_order_delta": max_order_delta,
            },
            checked_trade_plan=checked,
        )
    except Exception as exc:
        logger.exception("Pre-trade checks failed: %s", exc)
        raise

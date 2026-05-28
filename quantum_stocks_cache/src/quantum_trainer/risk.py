from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Tuple

from quantum_trainer.trend import BacktestResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RiskConfig:
    max_portfolio_mdd: float = -0.12
    max_daily_turnover: float = 0.50
    max_cash_exposure: float = 0.80


@dataclass(frozen=True)
class RiskGateResult:
    status: str
    allow_new_entries: bool
    require_manual_review: bool
    reason_codes: Tuple[str, ...]
    metrics: Dict[str, float]


def evaluate_risk(result: BacktestResult, config: RiskConfig) -> RiskGateResult:
    try:
        equity = result.equity_curve["dynamic_equity"].dropna()
        if equity.empty:
            raise ValueError("dynamic_equity is empty.")

        current_drawdown = float(equity.iloc[-1] / equity.cummax().iloc[-1] - 1.0)
        latest_turnover = float(result.equity_curve["turnover"].iloc[-1])
        latest_cash_exposure = float(result.equity_curve["cash_exposure"].iloc[-1])

        reason_codes: list[str] = []
        status = "PASS"
        allow_new_entries = True
        require_manual_review = False

        if current_drawdown <= config.max_portfolio_mdd:
            status = "BLOCK"
            allow_new_entries = False
            require_manual_review = True
            reason_codes.append("MDD_LIMIT_BREACH")

        if latest_turnover > config.max_daily_turnover:
            if status != "BLOCK":
                status = "REVIEW"
            require_manual_review = True
            reason_codes.append("TURNOVER_LIMIT_BREACH")

        if latest_cash_exposure > config.max_cash_exposure:
            if status != "BLOCK":
                status = "REVIEW"
            require_manual_review = True
            reason_codes.append("HIGH_CASH_EXPOSURE")

        return RiskGateResult(
            status=status,
            allow_new_entries=allow_new_entries,
            require_manual_review=require_manual_review,
            reason_codes=tuple(reason_codes),
            metrics={
                "current_drawdown": current_drawdown,
                "latest_turnover": latest_turnover,
                "latest_cash_exposure": latest_cash_exposure,
            },
        )
    except Exception as exc:
        logger.exception("Risk evaluation failed: %s", exc)
        raise

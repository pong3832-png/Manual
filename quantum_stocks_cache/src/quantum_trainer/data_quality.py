from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Dict, Sequence, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DataQualityConfig:
    max_stale_days: int = 5
    max_abs_daily_return: float = 0.35


@dataclass(frozen=True)
class DataQualityResult:
    status: str
    reason_codes: Tuple[str, ...]
    metrics: Dict[str, float | str]


def validate_price_data(
    prices: pd.DataFrame,
    required_symbols: Sequence[str],
    config: DataQualityConfig,
    as_of: date | None = None,
) -> DataQualityResult:
    try:
        reason_codes: list[str] = []
        metrics: dict[str, float | str] = {}

        if prices.empty:
            return DataQualityResult("FAIL", ("EMPTY_PRICE_DATA",), {"row_count": 0.0})

        required = [str(symbol) for symbol in required_symbols]
        missing_symbols = sorted(set(required).difference(prices.columns))
        if missing_symbols:
            reason_codes.append("MISSING_SYMBOLS")
            metrics["missing_symbols"] = ",".join(missing_symbols)

        if prices.isna().any().any():
            reason_codes.append("MISSING_VALUES")
            metrics["missing_value_count"] = float(prices.isna().sum().sum())

        last_date = pd.Timestamp(prices.index.max()).date()
        anchor_date = as_of or date.today()
        stale_days = (anchor_date - last_date).days
        metrics["last_date"] = last_date.isoformat()
        metrics["stale_days"] = float(stale_days)
        if stale_days > config.max_stale_days:
            reason_codes.append("STALE_DATA")

        returns = prices[list(set(required).intersection(prices.columns))].pct_change(fill_method=None)
        max_abs_return = float(returns.abs().max().max()) if not returns.empty else 0.0
        metrics["max_abs_daily_return"] = max_abs_return
        if max_abs_return > config.max_abs_daily_return:
            reason_codes.append("PRICE_JUMP")

        status = "FAIL" if reason_codes else "PASS"
        return DataQualityResult(status=status, reason_codes=tuple(reason_codes), metrics=metrics)
    except Exception as exc:
        logger.exception("Data quality validation failed: %s", exc)
        raise

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BacktestConfig:
    weights: Dict[str, float]
    trend_window: int = 20
    cost_bps: float = 5.0
    periods_per_year: int = 252


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: pd.DataFrame
    positions: pd.DataFrame
    signals: pd.DataFrame
    performance_summary: pd.DataFrame


def _normalized_weights(columns: pd.Index, weights: Dict[str, float]) -> pd.Series:
    try:
        weights_s = pd.Series(weights, dtype="float64").reindex(columns).fillna(0.0)
        if weights_s.sum() <= 0:
            raise ValueError("Portfolio weights must contain at least one positive asset weight.")
        return weights_s / weights_s.sum()
    except Exception as exc:
        logger.exception("Failed to normalize portfolio weights: %s", exc)
        raise


def _clean_prices(prices: pd.DataFrame) -> pd.DataFrame:
    try:
        if prices.empty:
            raise ValueError("prices must not be empty.")
        cleaned = prices.sort_index().astype("float64").ffill().dropna(how="any")
        if cleaned.empty:
            raise ValueError("prices became empty after cleaning missing values.")
        return cleaned
    except Exception as exc:
        logger.exception("Failed to clean price data: %s", exc)
        raise


def summarize_performance(
    equity_curve: pd.DataFrame,
    periods_per_year: int = 252,
) -> pd.DataFrame:
    try:
        required = {"buy_hold_ret", "dynamic_ret", "buy_hold_equity", "dynamic_equity"}
        missing = required.difference(equity_curve.columns)
        if missing:
            raise ValueError(f"equity_curve missing required columns: {sorted(missing)}")

        def _row(label: str, ret_col: str, equity_col: str) -> Dict[str, float | str]:
            returns = equity_curve[ret_col].dropna()
            equity = equity_curve[equity_col].dropna()
            years = max(len(equity) / periods_per_year, 1 / periods_per_year)
            total_return = equity.iloc[-1] / equity.iloc[0] - 1.0
            cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1.0 / years) - 1.0
            drawdown = equity / equity.cummax() - 1.0
            volatility = returns.std(ddof=0) * np.sqrt(periods_per_year)
            sharpe = cagr / volatility if volatility > 0 else np.nan
            return {
                "strategy": label,
                "Total_Return": total_return,
                "CAGR": cagr,
                "MDD": drawdown.min(),
                "Volatility": volatility,
                "Sharpe": sharpe,
            }

        rows = [
            _row("buy_hold", "buy_hold_ret", "buy_hold_equity"),
            _row("dynamic_trend", "dynamic_ret", "dynamic_equity"),
        ]
        summary = pd.DataFrame(rows).set_index("strategy")
        buy_hold_mdd = float(summary.loc["buy_hold", "MDD"])
        dynamic_mdd = float(summary.loc["dynamic_trend", "MDD"])
        summary["MDD_Improvement_ppt"] = 0.0
        summary.loc["dynamic_trend", "MDD_Improvement_ppt"] = (dynamic_mdd - buy_hold_mdd) * 100.0
        return summary
    except Exception as exc:
        logger.exception("Failed to summarize performance: %s", exc)
        raise


def run_dynamic_trend_backtest(
    prices: pd.DataFrame,
    config: BacktestConfig,
) -> BacktestResult:
    try:
        if config.trend_window < 2:
            raise ValueError("trend_window must be >= 2.")
        if config.cost_bps < 0:
            raise ValueError("cost_bps must be >= 0.")

        clean_prices = _clean_prices(prices)
        weights = _normalized_weights(clean_prices.columns, config.weights)

        asset_ret = clean_prices.pct_change(fill_method=None).fillna(0.0)
        sma = clean_prices.rolling(
            window=config.trend_window,
            min_periods=config.trend_window,
        ).mean()

        signals = (clean_prices > sma).astype("float64").where(sma.notna(), 0.0)
        positions = signals.shift(1).fillna(0.0)

        weighted_position = positions.mul(weights, axis=1).sum(axis=1)
        turnover = positions.diff().abs().fillna(positions.abs()).mul(weights, axis=1).sum(axis=1)
        trading_cost = turnover * (config.cost_bps / 10_000.0)

        buy_hold_ret = asset_ret.mul(weights, axis=1).sum(axis=1)
        dynamic_ret = positions.mul(asset_ret).mul(weights, axis=1).sum(axis=1) - trading_cost

        equity_curve = pd.DataFrame(
            {
                "buy_hold_ret": buy_hold_ret,
                "dynamic_ret": dynamic_ret,
                "buy_hold_equity": (1.0 + buy_hold_ret).cumprod(),
                "dynamic_equity": (1.0 + dynamic_ret).cumprod(),
                "weighted_position": weighted_position,
                "cash_exposure": (1.0 - weighted_position).clip(lower=0.0, upper=1.0),
                "turnover": turnover,
                "trading_cost": trading_cost,
            },
            index=clean_prices.index,
        )

        summary = summarize_performance(equity_curve, config.periods_per_year)
        return BacktestResult(
            equity_curve=equity_curve,
            positions=positions,
            signals=signals,
            performance_summary=summary,
        )
    except Exception as exc:
        logger.exception("Dynamic trend backtest failed: %s", exc)
        raise

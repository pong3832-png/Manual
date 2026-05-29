from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _drawdown(series: pd.Series, window: int) -> pd.Series:
    rolling_max = series.rolling(window=window, min_periods=window).max()
    return series / rolling_max - 1.0


def build_feature_frame(prices: pd.DataFrame) -> pd.DataFrame:
    try:
        if prices.empty:
            raise ValueError("prices must not be empty.")

        frames: list[pd.DataFrame] = []
        for symbol in prices.columns:
            close = prices[symbol].astype("float64")
            returns = close.pct_change(fill_method=None)
            ma20 = close.rolling(window=20, min_periods=20).mean()
            ma60 = close.rolling(window=60, min_periods=60).mean()
            vol20 = returns.rolling(window=20, min_periods=20).std(ddof=0) * np.sqrt(252)
            vol60 = returns.rolling(window=60, min_periods=60).std(ddof=0) * np.sqrt(252)
            above_ma20 = (close > ma20).astype("float64")
            frame = pd.DataFrame(
                {
                    "date": close.index,
                    "symbol": str(symbol),
                    "return_5d": close.pct_change(periods=5, fill_method=None),
                    "return_20d": close.pct_change(periods=20, fill_method=None),
                    "ma20_gap": close / ma20 - 1.0,
                    "ma60_gap": close / ma60 - 1.0,
                    "realized_vol_20d": vol20,
                    "drawdown_20d": _drawdown(close, 20),
                    "trend_quality_60d": above_ma20.rolling(window=60, min_periods=60).mean(),
                    "volatility_regime_20_60": vol20 / vol60 - 1.0,
                    "breakout_120d_gap": close / close.rolling(window=120, min_periods=120).max() - 1.0,
                }
            )
            frames.append(frame)

        output = pd.concat(frames, ignore_index=True)
        market_return = output.groupby("date")["return_20d"].transform("median")
        output["market_relative_return_20d"] = output["return_20d"] - market_return
        base_columns = [
            "return_5d",
            "return_20d",
            "ma20_gap",
            "ma60_gap",
            "realized_vol_20d",
            "drawdown_20d",
        ]
        return output.dropna(subset=base_columns).reset_index(drop=True)
    except Exception as exc:
        logger.exception("Feature frame build failed: %s", exc)
        raise


def build_forward_labels(prices: pd.DataFrame, horizon: int = 20) -> pd.DataFrame:
    try:
        if prices.empty:
            raise ValueError("prices must not be empty.")
        if horizon < 1:
            raise ValueError("horizon must be >= 1.")

        frames: list[pd.DataFrame] = []
        return_col = f"forward_{horizon}d_return"
        upside_col = f"forward_{horizon}d_upside"

        for symbol in prices.columns:
            close = prices[symbol].astype("float64")
            forward_return = close.shift(-horizon) / close - 1.0
            frame = pd.DataFrame(
                {
                    "date": close.index,
                    "symbol": str(symbol),
                    return_col: forward_return,
                    upside_col: (forward_return > 0.0).astype("int64"),
                }
            )
            frames.append(frame)

        return pd.concat(frames, ignore_index=True).dropna().reset_index(drop=True)
    except Exception as exc:
        logger.exception("Forward label build failed: %s", exc)
        raise

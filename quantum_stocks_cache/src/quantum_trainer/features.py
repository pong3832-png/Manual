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
            frame = pd.DataFrame(
                {
                    "date": close.index,
                    "symbol": str(symbol),
                    "return_5d": close.pct_change(periods=5, fill_method=None),
                    "return_20d": close.pct_change(periods=20, fill_method=None),
                    "ma20_gap": close / ma20 - 1.0,
                    "ma60_gap": close / ma60 - 1.0,
                    "realized_vol_20d": returns.rolling(window=20, min_periods=20).std(ddof=0)
                    * np.sqrt(252),
                    "drawdown_20d": _drawdown(close, 20),
                }
            )
            frames.append(frame)

        return pd.concat(frames, ignore_index=True).dropna().reset_index(drop=True)
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

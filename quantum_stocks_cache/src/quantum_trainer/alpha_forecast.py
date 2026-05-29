from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd

from quantum_trainer.features import build_feature_frame, build_forward_labels

logger = logging.getLogger(__name__)


FEATURE_COLUMNS = [
    "return_5d",
    "return_20d",
    "ma20_gap",
    "ma60_gap",
    "realized_vol_20d",
    "drawdown_20d",
]

ENHANCED_FEATURE_COLUMNS = FEATURE_COLUMNS + [
    "market_relative_return_20d",
    "trend_quality_60d",
    "volatility_regime_20_60",
    "breakout_120d_gap",
]


@dataclass(frozen=True)
class AlphaForecastConfig:
    horizon: int = 20
    min_samples: int = 80
    ridge_lambda: float = 1.0
    min_expected_return: float = -0.20
    max_expected_return: float = 0.20
    evaluate_enhanced_features: bool = False


def _fit_ridge_predict(
    train: pd.DataFrame,
    latest: pd.Series,
    target_col: str,
    features: Sequence[str],
    ridge_lambda: float,
) -> tuple[float, float]:
    x = train[list(features)].to_numpy(dtype="float64")
    y = train[target_col].to_numpy(dtype="float64")
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    std[std == 0.0] = 1.0
    x_scaled = (x - mean) / std
    x_design = np.column_stack([np.ones(len(x_scaled)), x_scaled])

    penalty = np.eye(x_design.shape[1]) * ridge_lambda
    penalty[0, 0] = 0.0
    beta = np.linalg.solve(x_design.T @ x_design + penalty, x_design.T @ y)

    latest_x = latest[list(features)].to_numpy(dtype="float64")
    latest_scaled = (latest_x - mean) / std
    latest_design = np.concatenate([[1.0], latest_scaled])
    prediction = float(latest_design @ beta)

    fitted = x_design @ beta
    ss_res = float(((y - fitted) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 0.0 if ss_tot == 0.0 else 1.0 - ss_res / ss_tot
    return prediction, r2


def run_alpha_forecast(
    prices: pd.DataFrame,
    config: AlphaForecastConfig | None = None,
) -> pd.DataFrame:
    try:
        config = config or AlphaForecastConfig()
        features = build_feature_frame(prices)
        labels = build_forward_labels(prices, horizon=config.horizon)
        return_col = f"forward_{config.horizon}d_return"
        upside_col = f"forward_{config.horizon}d_upside"
        dataset = features.merge(labels, on=["date", "symbol"], how="inner")
        dataset = dataset.dropna(subset=FEATURE_COLUMNS + [return_col, upside_col])

        rows: list[dict[str, float | str | int]] = []
        latest_features = features.sort_values("date").groupby("symbol").tail(1)

        for _, latest in latest_features.iterrows():
            symbol = str(latest["symbol"])
            train = dataset[dataset["symbol"] == symbol].copy()
            sample_count = int(len(train))
            if sample_count < config.min_samples:
                expected = 0.0
                probability = 0.50
                r2 = 0.0
            else:
                expected, r2 = _fit_ridge_predict(
                    train=train,
                    latest=latest,
                    target_col=return_col,
                    features=FEATURE_COLUMNS,
                    ridge_lambda=config.ridge_lambda,
                )
                prob_linear, _ = _fit_ridge_predict(
                    train=train,
                    latest=latest,
                    target_col=upside_col,
                    features=FEATURE_COLUMNS,
                    ridge_lambda=config.ridge_lambda,
                )
                probability = float(np.clip(prob_linear, 0.01, 0.99))

            expected = float(np.clip(expected, config.min_expected_return, config.max_expected_return))
            row = {
                "symbol": symbol,
                "expected_20d_return": expected,
                "upside_probability": probability,
                "sample_count": sample_count,
                "model_r2": float(r2),
            }
            if config.evaluate_enhanced_features:
                row.update(_feature_set_evaluation(train, return_col, upside_col, config.ridge_lambda))
            rows.append(row)

        if not rows:
            columns = ["expected_20d_return", "upside_probability", "sample_count", "model_r2"]
            if config.evaluate_enhanced_features:
                columns.extend(
                    [
                        "base_directional_accuracy",
                        "enhanced_directional_accuracy",
                        "enhanced_feature_policy",
                    ]
                )
            empty = pd.DataFrame(columns=columns)
            empty.index = pd.Index([], name="symbol")
            return empty
        return pd.DataFrame(rows).set_index("symbol")
    except Exception as exc:
        logger.exception("Alpha forecast failed: %s", exc)
        raise


def _feature_set_evaluation(
    train: pd.DataFrame,
    return_col: str,
    upside_col: str,
    ridge_lambda: float,
) -> dict[str, float | str]:
    base = train.dropna(subset=FEATURE_COLUMNS + [return_col, upside_col]).copy()
    enhanced = train.dropna(subset=ENHANCED_FEATURE_COLUMNS + [return_col, upside_col]).copy()
    base_accuracy = _walk_forward_directional_accuracy(base, return_col, upside_col, FEATURE_COLUMNS, ridge_lambda)
    enhanced_accuracy = _walk_forward_directional_accuracy(
        enhanced,
        return_col,
        upside_col,
        ENHANCED_FEATURE_COLUMNS,
        ridge_lambda,
    )
    policy = (
        "IMPROVED_CANDIDATE"
        if enhanced_accuracy > base_accuracy and len(enhanced) >= 30
        else "EVALUATION_ONLY"
    )
    return {
        "base_directional_accuracy": base_accuracy,
        "enhanced_directional_accuracy": enhanced_accuracy,
        "enhanced_feature_policy": policy,
    }


def _walk_forward_directional_accuracy(
    train: pd.DataFrame,
    return_col: str,
    upside_col: str,
    features: Sequence[str],
    ridge_lambda: float,
) -> float:
    if len(train) < 30:
        return 0.0
    ordered = train.sort_values("date").reset_index(drop=True)
    split = max(20, int(len(ordered) * 0.70))
    if split >= len(ordered):
        return 0.0
    train_part = ordered.iloc[:split].copy()
    test_part = ordered.iloc[split:].copy()
    predictions: list[int] = []
    actuals: list[int] = []
    for _, latest in test_part.iterrows():
        prediction, _ = _fit_ridge_predict(
            train=train_part,
            latest=latest,
            target_col=return_col,
            features=features,
            ridge_lambda=ridge_lambda,
        )
        predictions.append(1 if prediction > 0.0 else 0)
        actuals.append(int(latest[upside_col]))
    if not actuals:
        return 0.0
    return float(np.mean(np.array(predictions) == np.array(actuals)))

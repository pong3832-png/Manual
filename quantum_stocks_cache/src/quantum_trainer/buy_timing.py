from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _score_row(expected_return: float, probability: float) -> float:
    return_score = np.clip((expected_return + 0.05) / 0.15, 0.0, 1.0) * 50.0
    prob_score = np.clip((probability - 0.40) / 0.30, 0.0, 1.0) * 50.0
    return float(np.clip(return_score + prob_score, 0.0, 100.0))


def _decision(expected_return: float, probability: float, score: float) -> str:
    if expected_return < 0.0 or probability < 0.45:
        return "AVOID"
    if score >= 70.0 and expected_return >= 0.03 and probability >= 0.55:
        return "BUY_READY"
    return "WAIT"


def score_buy_timing(forecast: pd.DataFrame) -> pd.DataFrame:
    try:
        required = {"expected_20d_return", "upside_probability"}
        missing = required.difference(forecast.columns)
        if missing:
            raise ValueError(f"forecast missing required columns: {sorted(missing)}")

        output = forecast.copy()
        scores = []
        decisions = []
        for _, row in output.iterrows():
            expected = float(row["expected_20d_return"])
            probability = float(row["upside_probability"])
            score = _score_row(expected, probability)
            scores.append(score)
            decisions.append(_decision(expected, probability, score))

        output["buy_timing_score"] = scores
        output["decision"] = decisions
        return output
    except Exception as exc:
        logger.exception("Buy timing scoring failed: %s", exc)
        raise

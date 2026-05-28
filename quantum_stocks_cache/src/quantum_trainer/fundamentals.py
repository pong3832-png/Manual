from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


REQUIRED_FUNDAMENTAL_COLUMNS = {
    "symbol",
    "revenue_growth",
    "operating_margin",
    "roe",
    "per",
    "pbr",
    "debt_ratio",
}


def load_fundamentals_csv(path: Path | str) -> pd.DataFrame:
    csv_path = Path(path).resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"Fundamentals CSV not found: {csv_path}")

    raw = pd.read_csv(csv_path)
    missing = REQUIRED_FUNDAMENTAL_COLUMNS.difference(raw.columns)
    if missing:
        raise ValueError(f"Fundamentals CSV missing required columns: {sorted(missing)}")
    return score_fundamentals(raw)


def score_fundamentals(raw: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_FUNDAMENTAL_COLUMNS.difference(raw.columns)
    if missing:
        raise ValueError(f"Fundamentals data missing required columns: {sorted(missing)}")

    scored = raw.copy()
    scored["symbol"] = scored["symbol"].astype(str).str.strip()
    if (scored["symbol"] == "").any():
        raise ValueError("Fundamentals data contains empty symbols.")
    if scored["symbol"].duplicated().any():
        duplicates = scored.loc[scored["symbol"].duplicated(), "symbol"].tolist()
        raise ValueError(f"Fundamentals data contains duplicate symbols: {duplicates}")

    for column in REQUIRED_FUNDAMENTAL_COLUMNS - {"symbol"}:
        scored[column] = pd.to_numeric(scored[column], errors="coerce")
    if scored[list(REQUIRED_FUNDAMENTAL_COLUMNS - {"symbol"})].isna().any().any():
        raise ValueError("Fundamentals data contains non-numeric values.")

    scored["growth_score"] = scored["revenue_growth"].map(_growth_score)
    scored["profitability_score"] = (
        scored["operating_margin"].map(_operating_margin_score) * 0.45
        + scored["roe"].map(_roe_score) * 0.55
    )
    scored["valuation_score"] = (
        scored["per"].map(_per_score) * 0.55
        + scored["pbr"].map(_pbr_score) * 0.45
    )
    scored["balance_sheet_score"] = scored["debt_ratio"].map(_debt_score)
    scored["fundamental_score"] = (
        scored["growth_score"] * 0.25
        + scored["profitability_score"] * 0.35
        + scored["valuation_score"] * 0.20
        + scored["balance_sheet_score"] * 0.20
    ).clip(0.0, 100.0)
    scored["fundamental_view"] = scored["fundamental_score"].map(_fundamental_view)
    scored["fundamental_reasons"] = scored.apply(_fundamental_reasons, axis=1)
    return scored


def apply_valuation_metrics(
    fundamentals: pd.DataFrame,
    prices: pd.DataFrame,
    shares_outstanding: pd.DataFrame,
) -> pd.DataFrame:
    required_fundamentals = {"symbol", "net_income", "equity"}
    missing_fundamentals = required_fundamentals.difference(fundamentals.columns)
    if missing_fundamentals:
        raise ValueError(
            f"Fundamentals data missing valuation columns: {sorted(missing_fundamentals)}"
        )
    if "symbol" not in shares_outstanding.columns or "shares_outstanding" not in shares_outstanding.columns:
        raise ValueError("Shares CSV must include symbol and shares_outstanding columns.")
    if prices.empty:
        raise ValueError("Price data must not be empty.")

    latest_prices = prices.tail(1).T.reset_index()
    latest_prices.columns = ["symbol", "latest_price"]
    enriched = fundamentals.drop(
        columns=[column for column in ["shares_outstanding", "latest_price"] if column in fundamentals.columns]
    ).copy()
    enriched = enriched.merge(
        shares_outstanding.loc[:, ["symbol", "shares_outstanding"]],
        on="symbol",
        how="left",
    ).merge(latest_prices, on="symbol", how="left")

    for column in ["net_income", "equity", "shares_outstanding", "latest_price"]:
        enriched[column] = pd.to_numeric(enriched[column], errors="coerce")
    if enriched[["shares_outstanding", "latest_price"]].isna().any().any():
        raise ValueError("Missing latest price or shares_outstanding for valuation.")

    enriched["market_cap"] = enriched["latest_price"] * enriched["shares_outstanding"]
    enriched["per"] = [
        _safe_ratio(market_cap, net_income)
        for market_cap, net_income in zip(enriched["market_cap"], enriched["net_income"])
    ]
    enriched["pbr"] = [
        _safe_ratio(market_cap, equity)
        for market_cap, equity in zip(enriched["market_cap"], enriched["equity"])
    ]
    return enriched


def _growth_score(value: float) -> float:
    return float(np.clip((value + 0.05) / 0.25, 0.0, 1.0) * 100.0)


def _operating_margin_score(value: float) -> float:
    return float(np.clip(value / 0.20, 0.0, 1.0) * 100.0)


def _roe_score(value: float) -> float:
    return float(np.clip(value / 0.18, 0.0, 1.0) * 100.0)


def _per_score(value: float) -> float:
    if value <= 0:
        return 0.0
    return float(np.clip((35.0 - value) / 25.0, 0.0, 1.0) * 100.0)


def _pbr_score(value: float) -> float:
    if value <= 0:
        return 0.0
    return float(np.clip((3.0 - value) / 2.5, 0.0, 1.0) * 100.0)


def _debt_score(value: float) -> float:
    return float(np.clip((1.5 - value) / 1.2, 0.0, 1.0) * 100.0)


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator / denominator)


def _fundamental_view(score: float) -> str:
    if score >= 70.0:
        return "FUNDAMENTAL_STRONG"
    if score >= 45.0:
        return "FUNDAMENTAL_NEUTRAL"
    return "FUNDAMENTAL_WEAK"


def _fundamental_reasons(row: pd.Series) -> str:
    reasons: list[str] = []
    reasons.append("GROWTH_OK" if row["revenue_growth"] >= 0.05 else "GROWTH_WEAK")
    reasons.append(
        "PROFITABILITY_OK"
        if row["operating_margin"] >= 0.08 and row["roe"] >= 0.08
        else "PROFITABILITY_WEAK"
    )
    reasons.append(
        "VALUATION_REASONABLE" if row["per"] <= 25.0 and row["pbr"] <= 2.0 else "VALUATION_EXPENSIVE"
    )
    reasons.append("DEBT_CONTROLLED" if row["debt_ratio"] <= 1.0 else "DEBT_RISK_HIGH")
    return ",".join(reasons)

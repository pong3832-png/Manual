from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.fundamentals import (
    apply_valuation_metrics,
    load_fundamentals_csv,
    score_fundamentals,
)


def test_score_fundamentals_outputs_quality_value_and_risk_reasons() -> None:
    raw = pd.DataFrame(
        {
            "symbol": ["005930.KS", "051910.KS"],
            "revenue_growth": [0.12, -0.04],
            "operating_margin": [0.18, 0.03],
            "roe": [0.16, 0.02],
            "per": [14.0, 55.0],
            "pbr": [1.2, 3.5],
            "debt_ratio": [0.45, 1.80],
        }
    )

    scored = score_fundamentals(raw)

    assert {
        "symbol",
        "fundamental_score",
        "fundamental_view",
        "fundamental_reasons",
    }.issubset(scored.columns)
    assert scored.loc[0, "fundamental_view"] == "FUNDAMENTAL_STRONG"
    assert "PROFITABILITY_OK" in scored.loc[0, "fundamental_reasons"]
    assert scored.loc[1, "fundamental_view"] == "FUNDAMENTAL_WEAK"
    assert "DEBT_RISK_HIGH" in scored.loc[1, "fundamental_reasons"]


def test_load_fundamentals_csv_validates_required_columns() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        path = Path(tmp_dir) / "fundamentals.csv"
        path.write_text(
            "\n".join(
                [
                    "symbol,revenue_growth,operating_margin,roe,per,pbr,debt_ratio",
                    "005930.KS,0.12,0.18,0.16,14.0,1.2,0.45",
                ]
            ),
            encoding="utf-8",
        )

        scored = load_fundamentals_csv(path)

        assert scored.loc[0, "symbol"] == "005930.KS"
        assert scored.loc[0, "fundamental_score"] > 0.0


def test_apply_valuation_metrics_calculates_per_and_pbr_from_price_shares_income_equity() -> None:
    fundamentals = pd.DataFrame(
        {
            "symbol": ["005930.KS"],
            "revenue_growth": [0.0],
            "operating_margin": [0.10],
            "roe": [0.12],
            "per": [0.0],
            "pbr": [0.0],
            "debt_ratio": [0.50],
            "net_income": [1000.0],
            "equity": [5000.0],
        }
    )
    prices = pd.DataFrame(
        {"005930.KS": [50.0]},
        index=pd.date_range("2026-05-27", periods=1, name="date"),
    )
    shares = pd.DataFrame({"symbol": ["005930.KS"], "shares_outstanding": [100.0]})

    enriched = apply_valuation_metrics(fundamentals, prices, shares)

    assert enriched.loc[0, "market_cap"] == 5000.0
    assert enriched.loc[0, "per"] == 5.0
    assert enriched.loc[0, "pbr"] == 1.0


def test_apply_valuation_metrics_refreshes_existing_valuation_columns() -> None:
    fundamentals = pd.DataFrame(
        {
            "symbol": ["005930.KS"],
            "net_income": [10.0],
            "equity": [50.0],
            "shares_outstanding": [1.0],
            "latest_price": [1.0],
            "market_cap": [1.0],
            "per": [1.0],
            "pbr": [1.0],
        }
    )
    prices = pd.DataFrame({"005930.KS": [20.0]})
    shares = pd.DataFrame({"symbol": ["005930.KS"], "shares_outstanding": [100.0]})

    enriched = apply_valuation_metrics(fundamentals, prices, shares)

    assert "shares_outstanding_x" not in enriched.columns
    assert "shares_outstanding_y" not in enriched.columns
    assert enriched.loc[0, "shares_outstanding"] == 100.0
    assert enriched.loc[0, "latest_price"] == 20.0
    assert enriched.loc[0, "market_cap"] == 2000.0
    assert enriched.loc[0, "per"] == 200.0
    assert enriched.loc[0, "pbr"] == 40.0

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def test_trend_forecast_classifies_market_flow_and_chase_risk_without_orders() -> None:
    module = importlib.import_module("quantum_trainer.trend_forecast")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        prices_csv = root / "prices.csv"
        company_research_csv = root / "company_research.csv"

        dates = pd.date_range("2026-01-01", periods=80, freq="D")
        pd.DataFrame(
            {
                "date": dates,
                "STEADY.KQ": [100 + i * 0.5 for i in range(80)],
                "SURGE.KQ": [100] * 55 + [104 + i * 4 for i in range(25)],
                "FALL.KQ": [140 - i * 0.7 for i in range(80)],
            }
        ).to_csv(prices_csv, index=False)
        pd.DataFrame(
            [
                {"symbol": "STEADY.KQ", "company_name": "Steady Up", "sector": "Semiconductors", "research_score": 72},
                {"symbol": "SURGE.KQ", "company_name": "Surge Co", "sector": "Materials", "research_score": 80},
                {"symbol": "FALL.KQ", "company_name": "Falling Co", "sector": "Biotech", "research_score": 45},
            ]
        ).to_csv(company_research_csv, index=False)

        output = module.run_trend_forecast(
            prices_csv=prices_csv,
            company_research_csv=company_research_csv,
            output_dir=root / "reports",
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.summary["row_count"] == 3
        assert output.summary["external_api_requested"] == "NO"
        assert output.summary["order_status"] == "NO_ORDER"
        assert set(output.report["order_status"]) == {"NO_ORDER"}

        by_symbol = output.report.set_index("symbol")
        assert by_symbol.loc["STEADY.KQ", "trend_regime"] == "UPTREND"
        assert by_symbol.loc["STEADY.KQ", "forecast_bias"] == "BULLISH"
        assert by_symbol.loc["STEADY.KQ", "chase_risk"] != "HIGH"

        assert by_symbol.loc["SURGE.KQ", "trend_regime"] == "UPTREND"
        assert by_symbol.loc["SURGE.KQ", "forecast_bias"] == "WATCH_PULLBACK"
        assert by_symbol.loc["SURGE.KQ", "chase_risk"] == "HIGH"

        assert by_symbol.loc["FALL.KQ", "trend_regime"] == "DOWNTREND"
        assert by_symbol.loc["FALL.KQ", "forecast_bias"] == "BEARISH"

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "Trend Forecast" in markdown
        assert "WATCH_PULLBACK" in markdown
        assert "NO_ORDER" in markdown


def test_trend_forecast_marks_insufficient_price_history_without_guessing() -> None:
    module = importlib.import_module("quantum_trainer.trend_forecast")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        prices_csv = root / "prices.csv"
        company_research_csv = root / "company_research.csv"

        pd.DataFrame(
            {
                "date": pd.date_range("2026-01-01", periods=20, freq="D"),
                "SHORT.KQ": [100 + i for i in range(20)],
            }
        ).to_csv(prices_csv, index=False)
        pd.DataFrame(
            [{"symbol": "SHORT.KQ", "company_name": "Short History", "sector": "New Listing", "research_score": 65}]
        ).to_csv(company_research_csv, index=False)

        output = module.run_trend_forecast(
            prices_csv=prices_csv,
            company_research_csv=company_research_csv,
            output_dir=root / "reports",
        )

        row = output.report.iloc[0]
        assert row["sample_count"] == 20
        assert row["trend_regime"] == "INSUFFICIENT_DATA"
        assert row["forecast_bias"] == "UNKNOWN"
        assert row["chase_risk"] == "UNKNOWN"
        assert row["order_status"] == "NO_ORDER"
        assert row["external_api_requested"] == "NO"

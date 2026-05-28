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


def test_universe_stock_analysis_keeps_every_company_from_research_report() -> None:
    module = importlib.import_module("quantum_trainer.universe_stock_analysis")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        company_research = root / "company_research.csv"
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "Samsung C&T",
                    "sector": "Holding",
                    "latest_price": 410500,
                    "latest_price_date": "2026-05-27",
                    "research_score": 77.0,
                    "research_view": "RESEARCH_CANDIDATE",
                    "decision": "BUY_READY",
                    "expected_20d_return": 0.14,
                    "upside_probability": 0.74,
                    "return_20d": 0.12,
                    "ma20_gap": 0.05,
                    "drawdown_20d": -0.03,
                    "per": 17.8,
                    "pbr": 1.2,
                    "fundamental_view": "FUNDAMENTAL_NEUTRAL",
                    "why_summary": "ALPHA_BUY_READY,POSITIVE_20D_MOMENTUM,ABOVE_SMA20",
                },
                {
                    "symbol": "005930.KS",
                    "company_name": "Samsung Electronics",
                    "sector": "Semiconductors",
                    "latest_price": 91000,
                    "latest_price_date": "2026-05-27",
                    "research_score": 62.0,
                    "research_view": "WATCHLIST",
                    "decision": "WAIT",
                    "expected_20d_return": 0.08,
                    "upside_probability": 0.58,
                    "return_20d": -0.02,
                    "ma20_gap": -0.01,
                    "drawdown_20d": -0.06,
                    "per": 26.0,
                    "pbr": 2.3,
                    "fundamental_view": "FUNDAMENTAL_NEUTRAL",
                    "why_summary": "ALPHA_WAIT,NEGATIVE_20D_MOMENTUM,BELOW_SMA20",
                },
                {
                    "symbol": "999999.KS",
                    "company_name": "User Added Co",
                    "sector": "User Universe",
                    "latest_price": 12345,
                    "latest_price_date": "2026-05-27",
                    "research_score": 19.0,
                    "research_view": "AVOID_FOR_NOW",
                    "decision": "AVOID",
                    "expected_20d_return": -0.04,
                    "upside_probability": 0.41,
                    "return_20d": -0.18,
                    "ma20_gap": -0.12,
                    "drawdown_20d": -0.16,
                    "per": 0.0,
                    "pbr": 0.0,
                    "fundamental_view": "FUNDAMENTAL_WEAK",
                    "why_summary": "ALPHA_AVOID,NEGATIVE_20D_MOMENTUM,BELOW_SMA20",
                },
            ]
        ).to_csv(company_research, index=False)

        output = module.run_universe_stock_analysis(
            company_research_csv=company_research,
            output_dir=root / "reports",
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert list(output.report["symbol"]) == ["028260.KS", "005930.KS", "999999.KS"]
        assert set(output.report["order_status"]) == {"NO_ORDER"}
        assert output.summary == {
            "row_count": 3,
            "buy_ready_count": 1,
            "wait_count": 1,
            "reject_count": 1,
        }

        by_symbol = output.report.set_index("symbol")
        assert by_symbol.loc["028260.KS", "price_trend_status"] == "TREND_OK"
        assert by_symbol.loc["028260.KS", "decision_status"] == "BUY_READY"
        assert by_symbol.loc["005930.KS", "price_trend_status"] == "TREND_WEAK"
        assert by_symbol.loc["005930.KS", "decision_status"] == "WAIT"
        assert by_symbol.loc["999999.KS", "risk_status"] == "RISK_REVIEW"
        assert by_symbol.loc["999999.KS", "decision_status"] == "REJECT"

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "# Universe Stock Analysis" in markdown
        assert "every company in `company_research.csv`" in markdown
        assert "User Added Co" in markdown
        assert "NO_ORDER" in markdown

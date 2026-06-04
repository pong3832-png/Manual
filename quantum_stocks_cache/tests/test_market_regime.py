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


def test_market_regime_summarizes_market_and_sector_trend_without_orders() -> None:
    module = importlib.import_module("quantum_trainer.market_regime")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        trend_csv = root / "trend_forecast.csv"
        pd.DataFrame(
            [
                {
                    "symbol": "A.KQ",
                    "company_name": "A",
                    "sector": "Semiconductors",
                    "forecast_bias": "BULLISH",
                    "chase_risk": "LOW",
                    "trend_score": 80,
                },
                {
                    "symbol": "B.KQ",
                    "company_name": "B",
                    "sector": "Semiconductors",
                    "forecast_bias": "BULLISH",
                    "chase_risk": "MEDIUM",
                    "trend_score": 75,
                },
                {
                    "symbol": "C.KQ",
                    "company_name": "C",
                    "sector": "Semiconductors",
                    "forecast_bias": "WATCH_PULLBACK",
                    "chase_risk": "HIGH",
                    "trend_score": 90,
                },
                {
                    "symbol": "D.KQ",
                    "company_name": "D",
                    "sector": "Semiconductors",
                    "forecast_bias": "BEARISH",
                    "chase_risk": "LOW",
                    "trend_score": 20,
                },
                {
                    "symbol": "E.KQ",
                    "company_name": "E",
                    "sector": "Biotech",
                    "forecast_bias": "BEARISH",
                    "chase_risk": "LOW",
                    "trend_score": 15,
                },
                {
                    "symbol": "F.KQ",
                    "company_name": "F",
                    "sector": "Biotech",
                    "forecast_bias": "BEARISH",
                    "chase_risk": "MEDIUM",
                    "trend_score": 25,
                },
                {
                    "symbol": "G.KQ",
                    "company_name": "G",
                    "sector": "Biotech",
                    "forecast_bias": "UNKNOWN",
                    "chase_risk": "UNKNOWN",
                    "trend_score": 0,
                },
            ]
        ).to_csv(trend_csv, index=False)

        output = module.run_market_regime(
            trend_forecast_csv=trend_csv,
            output_dir=root / "reports",
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.summary["external_api_requested"] == "NO"
        assert output.summary["order_status"] == "NO_ORDER"
        assert output.summary["row_count"] == 3
        assert set(output.report["order_status"]) == {"NO_ORDER"}

        by_scope = output.report.set_index(["scope", "sector"])
        market = by_scope.loc[("MARKET", "ALL")]
        assert market["symbol_count"] == 7
        assert market["high_chase_count"] == 1
        assert market["regime_status"] == "MIXED"

        semi = by_scope.loc[("SECTOR", "Semiconductors")]
        assert semi["symbol_count"] == 4
        assert semi["bullish_count"] == 2
        assert semi["watch_pullback_count"] == 1
        assert semi["high_chase_count"] == 1
        assert semi["regime_status"] == "EXTENDED_UPTREND"
        assert semi["risk_posture"] == "WAIT_PULLBACK"

        biotech = by_scope.loc[("SECTOR", "Biotech")]
        assert biotech["bearish_count"] == 2
        assert biotech["regime_status"] == "RISK_OFF"
        assert biotech["risk_posture"] == "DEFENSIVE"

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "Market Regime" in markdown
        assert "Semiconductors" in markdown
        assert "EXTENDED_UPTREND" in markdown
        assert "NO_ORDER" in markdown

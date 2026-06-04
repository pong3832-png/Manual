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


def test_sector_rotation_watch_ranks_recovering_sectors_and_candidates_without_orders() -> None:
    module = importlib.import_module("quantum_trainer.sector_rotation_watch")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        recovery_csv = root / "market_recovery_watch.csv"
        trend_csv = root / "trend_forecast.csv"
        output_dir = root / "reports"

        pd.DataFrame(
            [
                {
                    "scope": "MARKET",
                    "sector": "ALL",
                    "recovery_status": "WAIT_BREADTH_RECOVERY",
                    "review_priority": 1,
                    "regime_status": "RISK_OFF",
                    "risk_posture": "DEFENSIVE",
                    "symbol_count": 10,
                    "bullish_ratio": 0.20,
                    "bearish_ratio": 0.60,
                    "high_chase_ratio": 0.05,
                    "blocked_watch_count": 4,
                    "unlock_condition": "market breadth required",
                    "required_evidence": "local reports",
                    "review_cadence": "daily",
                    "action_summary": "wait",
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                    "broker_order_requested": "NO",
                },
                {
                    "scope": "SECTOR",
                    "sector": "Semiconductors",
                    "recovery_status": "WATCH_CONFIRMATION",
                    "review_priority": 3,
                    "regime_status": "RECOVERY_WATCH",
                    "risk_posture": "WAIT_CONFIRMATION",
                    "symbol_count": 5,
                    "bullish_ratio": 0.35,
                    "bearish_ratio": 0.25,
                    "high_chase_ratio": 0.10,
                    "blocked_watch_count": 2,
                    "unlock_condition": "confirmation",
                    "required_evidence": "local reports",
                    "review_cadence": "daily",
                    "action_summary": "watch",
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                    "broker_order_requested": "NO",
                },
                {
                    "scope": "SECTOR",
                    "sector": "Biotech",
                    "recovery_status": "RECOVERY_CONFIRMED",
                    "review_priority": 5,
                    "regime_status": "RISK_ON",
                    "risk_posture": "SELECTIVE_BUY_REVIEW",
                    "symbol_count": 4,
                    "bullish_ratio": 0.60,
                    "bearish_ratio": 0.10,
                    "high_chase_ratio": 0.10,
                    "blocked_watch_count": 1,
                    "unlock_condition": "confirmed",
                    "required_evidence": "local reports",
                    "review_cadence": "manual review",
                    "action_summary": "review",
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                    "broker_order_requested": "NO",
                },
                {
                    "scope": "SECTOR",
                    "sector": "Overheated",
                    "recovery_status": "WAIT_OVERHEAT_COOLING",
                    "review_priority": 2,
                    "regime_status": "EXTENDED_UPTREND",
                    "risk_posture": "WAIT_PULLBACK",
                    "symbol_count": 3,
                    "bullish_ratio": 0.80,
                    "bearish_ratio": 0.00,
                    "high_chase_ratio": 0.50,
                    "blocked_watch_count": 0,
                    "unlock_condition": "cooling",
                    "required_evidence": "local reports",
                    "review_cadence": "daily",
                    "action_summary": "do not chase",
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                    "broker_order_requested": "NO",
                },
                {
                    "scope": "SECTOR",
                    "sector": "Defensive",
                    "recovery_status": "WAIT_BREADTH_RECOVERY",
                    "review_priority": 1,
                    "regime_status": "RISK_OFF",
                    "risk_posture": "DEFENSIVE",
                    "symbol_count": 6,
                    "bullish_ratio": 0.10,
                    "bearish_ratio": 0.70,
                    "high_chase_ratio": 0.00,
                    "blocked_watch_count": 1,
                    "unlock_condition": "breadth",
                    "required_evidence": "local reports",
                    "review_cadence": "daily",
                    "action_summary": "wait",
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                    "broker_order_requested": "NO",
                },
            ]
        ).to_csv(recovery_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "A.KQ",
                    "company_name": "A Corp",
                    "sector": "Semiconductors",
                    "latest_price": 1000,
                    "forecast_bias": "BULLISH",
                    "chase_risk": "LOW",
                    "trend_score": 82,
                    "research_score": 70,
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                },
                {
                    "symbol": "B.KQ",
                    "company_name": "B Corp",
                    "sector": "Semiconductors",
                    "latest_price": 2000,
                    "forecast_bias": "WATCH_REBOUND",
                    "chase_risk": "LOW",
                    "trend_score": 74,
                    "research_score": 66,
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                },
                {
                    "symbol": "C.KQ",
                    "company_name": "C Corp",
                    "sector": "Semiconductors",
                    "latest_price": 3000,
                    "forecast_bias": "WATCH_PULLBACK",
                    "chase_risk": "HIGH",
                    "trend_score": 95,
                    "research_score": 80,
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                },
                {
                    "symbol": "D.KQ",
                    "company_name": "D Bio",
                    "sector": "Biotech",
                    "latest_price": 4000,
                    "forecast_bias": "BULLISH",
                    "chase_risk": "LOW",
                    "trend_score": 88,
                    "research_score": 77,
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                },
            ]
        ).to_csv(trend_csv, index=False)

        output = module.run_sector_rotation_watch(
            market_recovery_watch_csv=recovery_csv,
            trend_forecast_csv=trend_csv,
            output_dir=output_dir,
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.summary["row_count"] == 4
        assert output.summary["leader_count"] == 1
        assert output.summary["early_rotation_count"] == 1
        assert output.summary["defensive_wait_count"] == 1
        assert output.summary["external_api_requested"] == "NO"
        assert output.summary["order_status"] == "NO_ORDER"

        report = output.report.set_index("sector")
        assert report.loc["Biotech", "rotation_status"] == "RECOVERY_LEADER"
        assert report.loc["Semiconductors", "rotation_status"] == "EARLY_ROTATION"
        assert report.loc["Overheated", "rotation_status"] == "OVERHEATED_WAIT"
        assert report.loc["Defensive", "rotation_status"] == "DEFENSIVE_WAIT"
        assert report.loc["Semiconductors", "top_candidates"] == "A Corp(A.KQ); B Corp(B.KQ)"
        assert "C Corp" not in report.loc["Semiconductors", "top_candidates"]
        assert report.loc["Biotech", "opportunity_score"] > report.loc["Defensive", "opportunity_score"]
        assert set(output.report["order_status"]) == {"NO_ORDER"}
        assert set(output.report["broker_order_requested"]) == {"NO"}

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "Sector Rotation Watch" in markdown
        assert "EARLY_ROTATION" in markdown
        assert "NO_ORDER" in markdown

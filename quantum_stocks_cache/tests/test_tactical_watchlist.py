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


def test_tactical_watchlist_combines_rank_trigger_and_sector_without_orders() -> None:
    module = importlib.import_module("quantum_trainer.tactical_watchlist")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        event_csv = root / "event_adjusted_ranking.csv"
        entry_csv = root / "entry_signal_watch.csv"
        sector_csv = root / "sector_rotation_watch.csv"
        output_dir = root / "reports"

        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "company_name": "Komico",
                    "sector": "Semiconductors",
                    "final_watch_status": "MARKET_WAIT",
                    "rank_bucket": 2,
                    "final_rank_score": 67.6,
                    "quant_decision": "BUY_READY",
                    "event_decision": "EVENT_WATCH",
                    "chase_risk": "YES",
                    "entry_status": "MARKET_WAIT",
                    "market_regime_status": "RISK_OFF",
                    "sector_regime_status": "RECOVERY_WATCH",
                    "latest_price": 90000,
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                },
                {
                    "symbol": "BAT.KQ",
                    "company_name": "Battery Leader",
                    "sector": "Battery",
                    "final_watch_status": "MARKET_WAIT",
                    "rank_bucket": 2,
                    "final_rank_score": 65.0,
                    "quant_decision": "BUY_READY",
                    "event_decision": "NO_EVENT",
                    "chase_risk": "NO",
                    "entry_status": "MARKET_WAIT",
                    "market_regime_status": "RISK_OFF",
                    "sector_regime_status": "RECOVERY_WATCH",
                    "latest_price": 12000,
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                },
                {
                    "symbol": "TOB.KS",
                    "company_name": "Tobacco Ready",
                    "sector": "Tobacco",
                    "final_watch_status": "READY_REVIEW",
                    "rank_bucket": 1,
                    "final_rank_score": 50.0,
                    "quant_decision": "BUY_READY",
                    "event_decision": "NO_EVENT",
                    "chase_risk": "NO",
                    "entry_status": "READY_MANUAL_REVIEW",
                    "market_regime_status": "RISK_ON",
                    "sector_regime_status": "RISK_ON",
                    "latest_price": 100000,
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                },
                {
                    "symbol": "HOT.KQ",
                    "company_name": "Hot Stock",
                    "sector": "Overheated",
                    "final_watch_status": "WAIT_PULLBACK",
                    "rank_bucket": 3,
                    "final_rank_score": 90.0,
                    "quant_decision": "BUY_READY",
                    "event_decision": "NO_EVENT",
                    "chase_risk": "YES",
                    "entry_status": "WAIT_PULLBACK",
                    "market_regime_status": "RISK_OFF",
                    "sector_regime_status": "EXTENDED_UPTREND",
                    "latest_price": 5000,
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                },
            ]
        ).to_csv(event_csv, index=False)
        pd.DataFrame(
            [
                {"symbol": "183300.KQ", "watch_status": "WAIT_MARKET_REGIME", "trigger_priority": 1, "primary_blocker": "MARKET_REGIME", "trigger_condition": "breadth", "action_summary": "wait market", "order_status": "NO_ORDER", "external_api_requested": "NO", "broker_order_requested": "NO"},
                {"symbol": "BAT.KQ", "watch_status": "WAIT_MARKET_REGIME", "trigger_priority": 1, "primary_blocker": "MARKET_REGIME", "trigger_condition": "breadth", "action_summary": "wait market", "order_status": "NO_ORDER", "external_api_requested": "NO", "broker_order_requested": "NO"},
                {"symbol": "TOB.KS", "watch_status": "READY_MANUAL_REVIEW", "trigger_priority": 0, "primary_blocker": "USER_CONFIRMATION", "trigger_condition": "manual review", "action_summary": "manual review only", "order_status": "NO_ORDER", "external_api_requested": "NO", "broker_order_requested": "NO"},
                {"symbol": "HOT.KQ", "watch_status": "WAIT_PRICE_PULLBACK", "trigger_priority": 2, "primary_blocker": "PRICE_PULLBACK", "trigger_condition": "pullback", "action_summary": "wait pullback", "order_status": "NO_ORDER", "external_api_requested": "NO", "broker_order_requested": "NO"},
            ]
        ).to_csv(entry_csv, index=False)
        pd.DataFrame(
            [
                {"sector": "Semiconductors", "rotation_status": "EARLY_ROTATION", "rotation_priority": 2, "recovery_status": "WATCH_CONFIRMATION", "regime_status": "RECOVERY_WATCH", "opportunity_score": 74.0, "top_candidates": "Komico(183300.KQ)", "operator_action": "watch", "order_status": "NO_ORDER", "external_api_requested": "NO", "broker_order_requested": "NO"},
                {"sector": "Battery", "rotation_status": "RECOVERY_LEADER", "rotation_priority": 1, "recovery_status": "RECOVERY_CONFIRMED", "regime_status": "RISK_ON", "opportunity_score": 105.0, "top_candidates": "Battery Leader(BAT.KQ)", "operator_action": "leader watch", "order_status": "NO_ORDER", "external_api_requested": "NO", "broker_order_requested": "NO"},
                {"sector": "Tobacco", "rotation_status": "RECOVERY_LEADER", "rotation_priority": 1, "recovery_status": "RECOVERY_CONFIRMED", "regime_status": "RISK_ON", "opportunity_score": 95.0, "top_candidates": "Tobacco Ready(TOB.KS)", "operator_action": "leader watch", "order_status": "NO_ORDER", "external_api_requested": "NO", "broker_order_requested": "NO"},
                {"sector": "Overheated", "rotation_status": "OVERHEATED_WAIT", "rotation_priority": 4, "recovery_status": "WAIT_OVERHEAT_COOLING", "regime_status": "EXTENDED_UPTREND", "opportunity_score": 30.0, "top_candidates": "", "operator_action": "do not chase", "order_status": "NO_ORDER", "external_api_requested": "NO", "broker_order_requested": "NO"},
            ]
        ).to_csv(sector_csv, index=False)

        output = module.run_tactical_watchlist(
            event_adjusted_ranking_csv=event_csv,
            entry_signal_watch_csv=entry_csv,
            sector_rotation_watch_csv=sector_csv,
            output_dir=output_dir,
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.summary["row_count"] == 4
        assert output.summary["ready_manual_review_count"] == 1
        assert output.summary["sector_recovery_watch_count"] == 2
        assert output.summary["overheated_wait_count"] == 1
        assert output.summary["external_api_requested"] == "NO"
        assert output.summary["order_status"] == "NO_ORDER"

        report = output.report.set_index("symbol")
        assert report.loc["TOB.KS", "tactical_status"] == "READY_MANUAL_REVIEW"
        assert report.loc["BAT.KQ", "tactical_status"] == "SECTOR_RECOVERY_WATCH"
        assert report.loc["183300.KQ", "tactical_status"] == "SECTOR_RECOVERY_WATCH"
        assert report.loc["HOT.KQ", "tactical_status"] == "OVERHEATED_WAIT"
        assert report.loc["BAT.KQ", "priority_score"] > report.loc["183300.KQ", "priority_score"]
        assert output.report.iloc[0]["symbol"] == "TOB.KS"
        assert set(output.report["order_status"]) == {"NO_ORDER"}
        assert set(output.report["broker_order_requested"]) == {"NO"}

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "Tactical Watchlist" in markdown
        assert "SECTOR_RECOVERY_WATCH" in markdown
        assert "NO_ORDER" in markdown

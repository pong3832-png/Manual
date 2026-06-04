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


def test_market_recovery_watch_turns_regime_blockers_into_unlock_conditions() -> None:
    module = importlib.import_module("quantum_trainer.market_recovery_watch")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        market_regime_csv = root / "market_regime.csv"
        entry_signal_csv = root / "entry_signal_watch.csv"
        output_dir = root / "reports"

        pd.DataFrame(
            [
                {
                    "scope": "MARKET",
                    "sector": "ALL",
                    "symbol_count": 10,
                    "bullish_count": 1,
                    "watch_pullback_count": 1,
                    "watch_rebound_count": 1,
                    "bearish_count": 6,
                    "neutral_count": 1,
                    "unknown_count": 0,
                    "high_chase_count": 0,
                    "bullish_ratio": 0.2,
                    "bearish_ratio": 0.6,
                    "high_chase_ratio": 0.0,
                    "average_trend_score": 21.0,
                    "regime_status": "RISK_OFF",
                    "risk_posture": "DEFENSIVE",
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                    "action_summary": "downtrend breadth dominates",
                },
                {
                    "scope": "SECTOR",
                    "sector": "Semiconductors",
                    "symbol_count": 5,
                    "bullish_count": 1,
                    "watch_pullback_count": 0,
                    "watch_rebound_count": 1,
                    "bearish_count": 3,
                    "neutral_count": 0,
                    "unknown_count": 0,
                    "high_chase_count": 0,
                    "bullish_ratio": 0.2,
                    "bearish_ratio": 0.6,
                    "high_chase_ratio": 0.0,
                    "average_trend_score": 25.0,
                    "regime_status": "RISK_OFF",
                    "risk_posture": "DEFENSIVE",
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                    "action_summary": "downtrend breadth dominates",
                },
                {
                    "scope": "SECTOR",
                    "sector": "Biotech",
                    "symbol_count": 4,
                    "bullish_count": 2,
                    "watch_pullback_count": 1,
                    "watch_rebound_count": 0,
                    "bearish_count": 0,
                    "neutral_count": 1,
                    "unknown_count": 0,
                    "high_chase_count": 2,
                    "bullish_ratio": 0.75,
                    "bearish_ratio": 0.0,
                    "high_chase_ratio": 0.5,
                    "average_trend_score": 88.0,
                    "regime_status": "EXTENDED_UPTREND",
                    "risk_posture": "WAIT_PULLBACK",
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                    "action_summary": "trend is strong but crowded",
                },
                {
                    "scope": "SECTOR",
                    "sector": "Utilities",
                    "symbol_count": 3,
                    "bullish_count": 2,
                    "watch_pullback_count": 0,
                    "watch_rebound_count": 0,
                    "bearish_count": 0,
                    "neutral_count": 1,
                    "unknown_count": 0,
                    "high_chase_count": 0,
                    "bullish_ratio": 0.667,
                    "bearish_ratio": 0.0,
                    "high_chase_ratio": 0.0,
                    "average_trend_score": 72.0,
                    "regime_status": "RISK_ON",
                    "risk_posture": "SELECTIVE_BUY_REVIEW",
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                    "action_summary": "selective review",
                },
            ]
        ).to_csv(market_regime_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "company_name": "코미코",
                    "sector": "Semiconductors",
                    "watch_status": "WAIT_MARKET_REGIME",
                    "trigger_priority": 1,
                    "order_status": "NO_ORDER",
                },
                {
                    "symbol": "000660.KS",
                    "company_name": "SK하이닉스",
                    "sector": "Semiconductors",
                    "watch_status": "WAIT_MARKET_REGIME",
                    "trigger_priority": 1,
                    "order_status": "NO_ORDER",
                },
                {
                    "symbol": "087010.KQ",
                    "company_name": "펩트론",
                    "sector": "Biotech",
                    "watch_status": "WAIT_MARKET_REGIME",
                    "trigger_priority": 1,
                    "order_status": "NO_ORDER",
                },
            ]
        ).to_csv(entry_signal_csv, index=False)

        output = module.run_market_recovery_watch(
            market_regime_csv=market_regime_csv,
            entry_signal_watch_csv=entry_signal_csv,
            output_dir=output_dir,
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.summary["row_count"] == 4
        assert output.summary["breadth_wait_count"] == 2
        assert output.summary["overheat_wait_count"] == 1
        assert output.summary["confirmed_count"] == 1
        assert output.summary["external_api_requested"] == "NO"
        assert output.summary["order_status"] == "NO_ORDER"

        report = output.report.set_index(["scope", "sector"])
        market = report.loc[("MARKET", "ALL")]
        assert market["recovery_status"] == "WAIT_BREADTH_RECOVERY"
        assert market["blocked_watch_count"] == 3
        assert "30%" in market["unlock_condition"]
        assert market["broker_order_requested"] == "NO"

        semi = report.loc[("SECTOR", "Semiconductors")]
        assert semi["recovery_status"] == "WAIT_BREADTH_RECOVERY"
        assert semi["blocked_watch_count"] == 2

        biotech = report.loc[("SECTOR", "Biotech")]
        assert biotech["recovery_status"] == "WAIT_OVERHEAT_COOLING"
        assert "추격위험" in biotech["action_summary"]

        utilities = report.loc[("SECTOR", "Utilities")]
        assert utilities["recovery_status"] == "RECOVERY_CONFIRMED"
        assert utilities["order_status"] == "NO_ORDER"

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "Market Recovery Watch" in markdown
        assert "WAIT_BREADTH_RECOVERY" in markdown
        assert "NO_ORDER" in markdown

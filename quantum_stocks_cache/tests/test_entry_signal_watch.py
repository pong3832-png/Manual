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


def test_entry_signal_watch_turns_wait_reasons_into_recheck_triggers() -> None:
    module = importlib.import_module("quantum_trainer.entry_signal_watch")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        event_rank_csv = root / "event_adjusted_ranking.csv"
        pre_buy_csv = root / "pre_buy_decision.csv"
        trend_csv = root / "trend_forecast.csv"
        output_dir = root / "reports"

        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "company_name": "코미코",
                    "sector": "특수 목적용 기계 제조업",
                    "final_watch_status": "MARKET_WAIT",
                    "rank_bucket": 2,
                    "final_rank_score": 67.6,
                    "quant_decision": "BUY_READY",
                    "research_score": 69.0,
                    "event_decision": "EVENT_WATCH",
                    "event_score": 65.0,
                    "chase_risk": "YES",
                    "entry_status": "MARKET_WAIT",
                    "market_regime_status": "RISK_OFF",
                    "market_risk_posture": "DEFENSIVE",
                    "sector_regime_status": "MIXED",
                    "sector_risk_posture": "SELECTIVE_WATCH",
                    "latest_price": 90000,
                    "expected_20d_return": 0.20,
                    "upside_probability": 0.99,
                    "return_20d": 0.214,
                    "ma20_gap": 0.117,
                    "valuation_status": "VALUATION_UNKNOWN",
                    "risk_status": "RISK_OK",
                    "catalyst_title": "AI 반도체 생산 증가의 후방 수혜",
                    "action_summary": "개별 후보가 좋아도 시장/섹터 흐름이 불리합니다.",
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                },
                {
                    "symbol": "035420.KS",
                    "company_name": "NAVER",
                    "sector": "AI 플랫폼",
                    "final_watch_status": "EVENT_ONLY",
                    "rank_bucket": 3,
                    "final_rank_score": 50.4,
                    "quant_decision": "REJECT",
                    "research_score": 31.8,
                    "event_decision": "EVENT_FOCUS",
                    "event_score": 85.0,
                    "chase_risk": "NO",
                    "entry_status": "ENTRY_REVIEW",
                    "market_regime_status": "RISK_OFF",
                    "market_risk_posture": "DEFENSIVE",
                    "sector_regime_status": "RISK_OFF",
                    "sector_risk_posture": "DEFENSIVE",
                    "latest_price": 234000,
                    "expected_20d_return": -0.09,
                    "upside_probability": 0.11,
                    "return_20d": 0.066,
                    "ma20_gap": 0.132,
                    "valuation_status": "VALUATION_NEUTRAL",
                    "risk_status": "RISK_OK",
                    "catalyst_title": "젠슨 황 네이버 1784 방문 가능성",
                    "action_summary": "이벤트 직접성은 높지만 정량 게이트가 부족합니다.",
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                },
            ]
        ).to_csv(event_rank_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "company_name": "코미코",
                    "decision_status": "WAIT",
                    "order_status": "NO_ORDER",
                    "final_action": "NO_ORDER",
                    "manual_proposal_status": "INCOMPLETE_DRAFT",
                    "capital_status": "CAPITAL_PROVIDED",
                    "readiness_blockers": "manual gate not ready; trend forecast wait pullback; market regime defensive",
                    "buy_reasons": "conviction_score=74.83",
                    "buy_ban_reasons": "manual gate not ready; trend chase risk high; market regime defensive",
                    "entry_price_low": 81000,
                    "entry_price_high": 90000,
                    "staged_buy_plan": "first tranche 30%",
                    "stop_loss_rule": "SMA20 break",
                    "next_review_date": "2026-06-03",
                }
            ]
        ).to_csv(pre_buy_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "trend_regime": "UPTREND",
                    "forecast_bias": "WATCH_PULLBACK",
                    "chase_risk": "HIGH",
                    "trend_score": 100.0,
                }
            ]
        ).to_csv(trend_csv, index=False)

        output = module.run_entry_signal_watch(
            event_adjusted_ranking_csv=event_rank_csv,
            pre_buy_decision_csv=pre_buy_csv,
            trend_forecast_csv=trend_csv,
            output_dir=output_dir,
            top_n=10,
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.summary["row_count"] == 2
        assert output.summary["market_wait_count"] == 1
        assert output.summary["event_only_count"] == 1
        assert output.summary["external_api_requested"] == "NO"
        assert output.summary["order_status"] == "NO_ORDER"

        report = output.report.set_index("symbol")
        assert report.loc["183300.KQ", "watch_status"] == "WAIT_MARKET_REGIME"
        assert report.loc["183300.KQ", "primary_blocker"] == "MARKET_REGIME"
        assert "RISK_OFF" in report.loc["183300.KQ", "trigger_condition"]
        assert "NO_ORDER" == report.loc["183300.KQ", "order_status"]
        assert report.loc["035420.KS", "watch_status"] == "WATCH_EVENT_ONLY"
        assert report.loc["035420.KS", "broker_order_requested"] == "NO"

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "Entry Signal Watch" in markdown
        assert "WAIT_MARKET_REGIME" in markdown
        assert "WATCH_EVENT_ONLY" in markdown
        assert "NO_ORDER" in markdown

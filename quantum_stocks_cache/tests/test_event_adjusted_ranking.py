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


def test_event_adjusted_ranking_separates_quant_event_and_chase_risk() -> None:
    module = importlib.import_module("quantum_trainer.event_adjusted_ranking")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        universe_csv = root / "universe_stock_analysis.csv"
        event_csv = root / "event_catalysts.csv"
        output_dir = root / "reports"

        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "company_name": "코미코",
                    "sector": "반도체 장비",
                    "analysis_status": "ANALYZED",
                    "decision_status": "BUY_READY",
                    "order_status": "NO_ORDER",
                    "price_trend_status": "TREND_OK",
                    "alpha_status": "ALPHA_BUY_READY",
                    "valuation_status": "VALUATION_UNKNOWN",
                    "risk_status": "RISK_OK",
                    "latest_price": 90000,
                    "latest_price_date": "2026-05-29",
                    "research_score": 69.0,
                    "expected_20d_return": 0.20,
                    "upside_probability": 0.99,
                    "return_20d": 0.214,
                    "ma20_gap": 0.117,
                    "drawdown_20d": -0.098,
                    "per": 0,
                    "pbr": 0,
                    "reason_summary": "ALPHA_BUY_READY",
                    "action_summary": "manual gate required",
                },
                {
                    "symbol": "003550.KS",
                    "company_name": "LG",
                    "sector": "지주",
                    "analysis_status": "ANALYZED",
                    "decision_status": "BUY_READY",
                    "order_status": "NO_ORDER",
                    "price_trend_status": "TREND_OK",
                    "alpha_status": "ALPHA_BUY_READY",
                    "valuation_status": "VALUATION_NEUTRAL",
                    "risk_status": "RISK_OK",
                    "latest_price": 146600,
                    "latest_price_date": "2026-05-29",
                    "research_score": 70.5,
                    "expected_20d_return": 0.137,
                    "upside_probability": 0.825,
                    "return_20d": 0.493,
                    "ma20_gap": 0.302,
                    "drawdown_20d": 0.0,
                    "per": 22.9,
                    "pbr": 0.76,
                    "reason_summary": "EXTREME_PRICE_EXTENSION",
                    "action_summary": "manual gate required",
                },
                {
                    "symbol": "035420.KS",
                    "company_name": "NAVER",
                    "sector": "AI 플랫폼",
                    "analysis_status": "ANALYZED",
                    "decision_status": "REJECT",
                    "order_status": "NO_ORDER",
                    "price_trend_status": "TREND_OK",
                    "alpha_status": "ALPHA_AVOID",
                    "valuation_status": "VALUATION_NEUTRAL",
                    "risk_status": "RISK_OK",
                    "latest_price": 234000,
                    "latest_price_date": "2026-05-29",
                    "research_score": 31.8,
                    "expected_20d_return": -0.091,
                    "upside_probability": 0.116,
                    "return_20d": 0.066,
                    "ma20_gap": 0.132,
                    "drawdown_20d": 0.0,
                    "per": 20.1,
                    "pbr": 1.26,
                    "reason_summary": "ALPHA_AVOID",
                    "action_summary": "exclude",
                },
            ]
        ).to_csv(universe_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "company_name": "코미코",
                    "catalyst_title": "AI 반도체 생산 증가의 후방 수혜",
                    "catalyst_type": "THEME_SPILLOVER",
                    "impact_level": "MEDIUM",
                    "event_status": "REPORTED",
                    "source": "manual",
                    "summary": "세정·코팅 수요",
                    "event_score": 65.0,
                    "event_decision": "EVENT_WATCH",
                    "chase_risk": "NO",
                    "research_score": 69.0,
                    "research_view": "RESEARCH_CANDIDATE",
                    "quant_decision": "BUY_READY",
                    "return_20d": 0.214,
                    "ma20_gap": 0.117,
                    "extension_risk": "ENTRY_RANGE_OK",
                    "action_summary": "이벤트 후보로 관찰",
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                },
                {
                    "symbol": "003550.KS",
                    "company_name": "LG",
                    "catalyst_title": "LG 피지컬 AI 협력 기대",
                    "catalyst_type": "AI_PARTNERSHIP",
                    "impact_level": "HIGH",
                    "event_status": "REPORTED",
                    "source": "manual",
                    "summary": "그룹 이벤트",
                    "event_score": 90.0,
                    "event_decision": "WAIT_PULLBACK_EVENT",
                    "chase_risk": "YES",
                    "research_score": 70.5,
                    "research_view": "WAIT_PULLBACK",
                    "quant_decision": "BUY_READY",
                    "return_20d": 0.493,
                    "ma20_gap": 0.302,
                    "extension_risk": "EXTREME_EXTENSION",
                    "action_summary": "추격 금지",
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                },
                {
                    "symbol": "035420.KS",
                    "company_name": "NAVER",
                    "catalyst_title": "젠슨 황 네이버 1784 방문 가능성",
                    "catalyst_type": "DIRECT_MEETING",
                    "impact_level": "HIGH",
                    "event_status": "REPORTED",
                    "source": "manual",
                    "summary": "직접 이벤트",
                    "event_score": 85.0,
                    "event_decision": "EVENT_FOCUS",
                    "chase_risk": "NO",
                    "research_score": 31.8,
                    "research_view": "AVOID_FOR_NOW",
                    "quant_decision": "AVOID",
                    "return_20d": 0.066,
                    "ma20_gap": 0.132,
                    "extension_risk": "ENTRY_RANGE_OK",
                    "action_summary": "이벤트 직접성 높음",
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                },
            ]
        ).to_csv(event_csv, index=False)

        output = module.run_event_adjusted_ranking(
            universe_csv=universe_csv,
            event_csv=event_csv,
            output_dir=output_dir,
        )

        assert output.summary["external_api_requested"] == "NO"
        assert output.summary["row_count"] == 3
        assert output.summary["ready_count"] == 1
        assert output.summary["pullback_count"] == 1
        assert output.csv_path.exists()
        assert output.markdown_path.exists()

        report = output.report.set_index("symbol")
        assert report.loc["183300.KQ", "final_watch_status"] == "READY_REVIEW"
        assert report.loc["003550.KS", "final_watch_status"] == "WAIT_PULLBACK"
        assert report.loc["035420.KS", "final_watch_status"] == "EVENT_ONLY"
        assert report.loc["183300.KQ", "rank_bucket"] == 1
        assert report.loc["003550.KS", "rank_bucket"] == 2
        assert report.loc["035420.KS", "rank_bucket"] == 3
        assert report.loc["183300.KQ", "order_status"] == "NO_ORDER"

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "이벤트 조정 최종 감시 랭킹" in markdown
        assert "READY_REVIEW" in markdown
        assert "WAIT_PULLBACK" in markdown
        assert "EVENT_ONLY" in markdown


def test_event_adjusted_ranking_works_without_event_report() -> None:
    module = importlib.import_module("quantum_trainer.event_adjusted_ranking")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        universe_csv = root / "universe_stock_analysis.csv"
        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "company_name": "코미코",
                    "sector": "반도체 장비",
                    "analysis_status": "ANALYZED",
                    "decision_status": "BUY_READY",
                    "order_status": "NO_ORDER",
                    "price_trend_status": "TREND_OK",
                    "alpha_status": "ALPHA_BUY_READY",
                    "valuation_status": "VALUATION_UNKNOWN",
                    "risk_status": "RISK_OK",
                    "latest_price": 90000,
                    "latest_price_date": "2026-05-29",
                    "research_score": 69.0,
                    "expected_20d_return": 0.20,
                    "upside_probability": 0.99,
                    "return_20d": 0.214,
                    "ma20_gap": 0.117,
                    "drawdown_20d": -0.098,
                    "per": 0,
                    "pbr": 0,
                    "reason_summary": "ALPHA_BUY_READY",
                    "action_summary": "manual gate required",
                }
            ]
        ).to_csv(universe_csv, index=False)

        output = module.run_event_adjusted_ranking(
            universe_csv=universe_csv,
            event_csv=root / "missing_event_catalysts.csv",
            output_dir=root / "reports",
        )

        assert output.summary["event_input_status"] == "NO_EVENT_REPORT"
        assert output.summary["row_count"] == 1
        assert output.report.iloc[0]["final_watch_status"] == "READY_REVIEW"


def test_event_adjusted_ranking_uses_trend_forecast_to_block_chasing() -> None:
    module = importlib.import_module("quantum_trainer.event_adjusted_ranking")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        universe_csv = root / "universe_stock_analysis.csv"
        event_csv = root / "event_catalysts.csv"
        trend_csv = root / "trend_forecast.csv"
        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "company_name": "코미코",
                    "sector": "반도체 장비",
                    "analysis_status": "ANALYZED",
                    "decision_status": "BUY_READY",
                    "order_status": "NO_ORDER",
                    "price_trend_status": "TREND_OK",
                    "alpha_status": "ALPHA_BUY_READY",
                    "valuation_status": "VALUATION_UNKNOWN",
                    "risk_status": "RISK_OK",
                    "latest_price": 90000,
                    "latest_price_date": "2026-05-29",
                    "research_score": 69.0,
                    "expected_20d_return": 0.20,
                    "upside_probability": 0.99,
                    "return_20d": 0.214,
                    "ma20_gap": 0.117,
                    "drawdown_20d": -0.098,
                    "per": 0,
                    "pbr": 0,
                    "reason_summary": "ALPHA_BUY_READY",
                    "action_summary": "manual gate required",
                }
            ]
        ).to_csv(universe_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "company_name": "코미코",
                    "catalyst_title": "AI 반도체 생산 증가의 후방 수혜",
                    "catalyst_type": "THEME_SPILLOVER",
                    "impact_level": "MEDIUM",
                    "event_status": "REPORTED",
                    "source": "manual",
                    "summary": "세정·코팅 수요",
                    "event_score": 65.0,
                    "event_decision": "EVENT_WATCH",
                    "chase_risk": "NO",
                    "research_score": 69.0,
                    "research_view": "RESEARCH_CANDIDATE",
                    "quant_decision": "BUY_READY",
                    "return_20d": 0.214,
                    "ma20_gap": 0.117,
                    "extension_risk": "ENTRY_RANGE_OK",
                    "action_summary": "이벤트 후보로 관찰",
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                }
            ]
        ).to_csv(event_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "trend_regime": "UPTREND",
                    "forecast_bias": "WATCH_PULLBACK",
                    "chase_risk": "HIGH",
                    "trend_score": 100.0,
                    "action_summary": "trend strong but extended",
                }
            ]
        ).to_csv(trend_csv, index=False)

        output = module.run_event_adjusted_ranking(
            universe_csv=universe_csv,
            event_csv=event_csv,
            trend_forecast_csv=trend_csv,
            output_dir=root / "reports",
        )

        row = output.report.iloc[0]
        assert row["symbol"] == "183300.KQ"
        assert row["final_watch_status"] == "WAIT_PULLBACK"
        assert row["rank_bucket"] == 2
        assert row["chase_risk"] == "YES"
        assert row["entry_status"] == "WAIT_PULLBACK"
        assert row["order_status"] == "NO_ORDER"


def test_event_adjusted_ranking_uses_market_regime_to_wait_even_when_quant_is_ready() -> None:
    module = importlib.import_module("quantum_trainer.event_adjusted_ranking")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        universe_csv = root / "universe_stock_analysis.csv"
        event_csv = root / "event_catalysts.csv"
        market_regime_csv = root / "market_regime.csv"
        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "company_name": "코미코",
                    "sector": "반도체 장비",
                    "analysis_status": "ANALYZED",
                    "decision_status": "BUY_READY",
                    "order_status": "NO_ORDER",
                    "price_trend_status": "TREND_OK",
                    "alpha_status": "ALPHA_BUY_READY",
                    "valuation_status": "VALUATION_UNKNOWN",
                    "risk_status": "RISK_OK",
                    "latest_price": 90000,
                    "latest_price_date": "2026-05-29",
                    "research_score": 69.0,
                    "expected_20d_return": 0.20,
                    "upside_probability": 0.99,
                    "return_20d": 0.05,
                    "ma20_gap": 0.02,
                    "drawdown_20d": -0.03,
                    "per": 40.08,
                    "pbr": 4.75,
                    "reason_summary": "ALPHA_BUY_READY",
                    "action_summary": "manual gate required",
                }
            ]
        ).to_csv(universe_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "company_name": "코미코",
                    "catalyst_title": "AI 반도체 생산 증가의 후방 수혜",
                    "catalyst_type": "THEME_SPILLOVER",
                    "impact_level": "MEDIUM",
                    "event_status": "REPORTED",
                    "source": "manual",
                    "summary": "세정·코팅 수요",
                    "event_score": 65.0,
                    "event_decision": "EVENT_WATCH",
                    "chase_risk": "NO",
                    "research_score": 69.0,
                    "research_view": "RESEARCH_CANDIDATE",
                    "quant_decision": "BUY_READY",
                    "return_20d": 0.05,
                    "ma20_gap": 0.02,
                    "extension_risk": "ENTRY_RANGE_OK",
                    "action_summary": "이벤트 후보로 관찰",
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                }
            ]
        ).to_csv(event_csv, index=False)
        pd.DataFrame(
            [
                {
                    "scope": "MARKET",
                    "sector": "ALL",
                    "symbol_count": 100,
                    "regime_status": "RISK_OFF",
                    "risk_posture": "DEFENSIVE",
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                },
                {
                    "scope": "SECTOR",
                    "sector": "반도체 장비",
                    "symbol_count": 10,
                    "regime_status": "RISK_ON",
                    "risk_posture": "SELECTIVE_BUY_REVIEW",
                    "order_status": "NO_ORDER",
                    "external_api_requested": "NO",
                },
            ]
        ).to_csv(market_regime_csv, index=False)

        output = module.run_event_adjusted_ranking(
            universe_csv=universe_csv,
            event_csv=event_csv,
            market_regime_csv=market_regime_csv,
            output_dir=root / "reports",
        )

        row = output.report.iloc[0]
        assert row["symbol"] == "183300.KQ"
        assert row["final_watch_status"] == "MARKET_WAIT"
        assert row["rank_bucket"] == 2
        assert row["entry_status"] == "MARKET_WAIT"
        assert row["market_regime_status"] == "RISK_OFF"
        assert row["sector_regime_status"] == "RISK_ON"
        assert row["order_status"] == "NO_ORDER"
        assert output.summary["market_wait_count"] == 1

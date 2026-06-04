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


def test_event_catalysts_rank_direct_news_and_block_chase_buys() -> None:
    module = importlib.import_module("quantum_trainer.event_catalysts")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        research_csv = root / "company_research.csv"
        event_csv = root / "event_catalysts.actual.csv"
        output_dir = root / "reports"

        pd.DataFrame(
            [
                {
                    "symbol": "035420.KS",
                    "company_name": "NAVER",
                    "sector": "AI 플랫폼",
                    "research_score": 31.8,
                    "research_view": "AVOID_FOR_NOW",
                    "decision": "AVOID",
                    "return_20d": 0.066,
                    "ma20_gap": 0.132,
                    "drawdown_20d": 0.0,
                    "extension_risk": "ENTRY_RANGE_OK",
                },
                {
                    "symbol": "003550.KS",
                    "company_name": "LG",
                    "sector": "지주",
                    "research_score": 70.5,
                    "research_view": "WAIT_PULLBACK",
                    "decision": "BUY_READY",
                    "return_20d": 0.493,
                    "ma20_gap": 0.302,
                    "drawdown_20d": 0.0,
                    "extension_risk": "EXTREME_EXTENSION",
                },
            ]
        ).to_csv(research_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "035420.KS",
                    "company_name": "NAVER",
                    "catalyst_title": "젠슨 황 네이버 1784 방문 가능성",
                    "catalyst_type": "DIRECT_MEETING",
                    "impact_level": "HIGH",
                    "event_status": "REPORTED",
                    "source": "연합뉴스",
                    "summary": "네이버클라우드, 소버린 AI, GPU 협력 기대",
                },
                {
                    "symbol": "003550.KS",
                    "company_name": "LG",
                    "catalyst_title": "LG 피지컬 AI 협력 기대",
                    "catalyst_type": "AI_PARTNERSHIP",
                    "impact_level": "HIGH",
                    "event_status": "REPORTED",
                    "source": "국내 언론",
                    "summary": "LG전자, LG CNS, LG이노텍 동반 수혜 기대",
                },
            ]
        ).to_csv(event_csv, index=False)

        output = module.run_event_catalysts(
            event_csv=event_csv,
            company_research_csv=research_csv,
            output_dir=output_dir,
            as_of="2026-06-01",
        )

        assert output.summary["external_api_requested"] == "NO"
        assert output.summary["event_count"] == 2
        assert output.csv_path.exists()
        assert output.markdown_path.exists()

        report = output.report.set_index("symbol")
        assert report.loc["035420.KS", "event_decision"] == "EVENT_FOCUS"
        assert report.loc["035420.KS", "chase_risk"] == "NO"
        assert report.loc["035420.KS", "order_status"] == "NO_ORDER"

        assert report.loc["003550.KS", "event_decision"] == "WAIT_PULLBACK_EVENT"
        assert report.loc["003550.KS", "chase_risk"] == "YES"
        assert "추격 금지" in report.loc["003550.KS", "action_summary"]

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "뉴스/이벤트 촉매" in markdown
        assert "주문 실행 없음" in markdown


def test_event_catalysts_noops_when_local_event_input_is_missing() -> None:
    module = importlib.import_module("quantum_trainer.event_catalysts")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        research_csv = root / "company_research.csv"
        pd.DataFrame(
            [
                {
                    "symbol": "183300.KQ",
                    "company_name": "코미코",
                    "sector": "반도체 장비",
                    "research_score": 69.0,
                    "research_view": "RESEARCH_CANDIDATE",
                    "decision": "BUY_READY",
                    "return_20d": 0.215,
                    "ma20_gap": 0.117,
                    "drawdown_20d": -0.098,
                    "extension_risk": "ENTRY_RANGE_OK",
                }
            ]
        ).to_csv(research_csv, index=False)

        output = module.run_event_catalysts(
            event_csv=root / "missing_event_catalysts.actual.csv",
            company_research_csv=research_csv,
            output_dir=root / "reports",
        )

        assert output.summary["input_status"] == "NO_EVENT_INPUT"
        assert output.summary["event_count"] == 0
        assert output.report.empty
        assert output.csv_path.exists()
        assert output.markdown_path.exists()

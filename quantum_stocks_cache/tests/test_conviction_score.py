from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.conviction_score import run_conviction_score


def test_conviction_score_ranks_persistent_focus_with_valuation_penalties() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        market_watch_csv = root / "market_watch.csv"
        company_research_csv = root / "company_research.csv"
        output_dir = root / "reports"

        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "Samsung C&T",
                    "sector": "Holding",
                    "research_score": 88.5,
                    "watch_status": "TODAY_FOCUS",
                    "watch_event": "STABLE_PRIORITY",
                    "focus_reason": "STABLE_PRIORITY; BUY_READY",
                    "expected_20d_return": 0.15,
                    "upside_probability": 0.78,
                    "return_20d": 0.32,
                    "ma20_gap": 0.08,
                    "drawdown_20d": -0.04,
                    "focus_persistence_count": 3,
                    "persistence_label": "PERSISTENT_FOCUS",
                    "persistence_score": 86.0,
                    "fundamental_view": "FUNDAMENTAL_NEUTRAL",
                },
                {
                    "symbol": "005930.KS",
                    "company_name": "Samsung Electronics",
                    "sector": "Semiconductors",
                    "research_score": 87.5,
                    "watch_status": "TODAY_FOCUS",
                    "watch_event": "STABLE_PRIORITY",
                    "focus_reason": "STABLE_PRIORITY; BUY_READY",
                    "expected_20d_return": 0.19,
                    "upside_probability": 0.86,
                    "return_20d": 0.45,
                    "ma20_gap": 0.18,
                    "drawdown_20d": 0.0,
                    "focus_persistence_count": 2,
                    "persistence_label": "BUILDING_FOCUS",
                    "persistence_score": 78.0,
                    "fundamental_view": "FUNDAMENTAL_NEUTRAL",
                },
                {
                    "symbol": "012330.KS",
                    "company_name": "Hyundai Mobis",
                    "sector": "Autos",
                    "research_score": 86.9,
                    "watch_status": "WATCH_FOR_CONFIRMATION",
                    "watch_event": "UNCHANGED",
                    "focus_reason": "fundamental confirmation needed",
                    "expected_20d_return": 0.14,
                    "upside_probability": 0.73,
                    "return_20d": 0.63,
                    "ma20_gap": 0.27,
                    "drawdown_20d": 0.0,
                    "focus_persistence_count": 0,
                    "persistence_label": "NOT_FOCUS",
                    "persistence_score": 0.0,
                    "fundamental_view": "FUNDAMENTAL_WEAK",
                },
            ]
        ).to_csv(market_watch_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "per": 18.4,
                    "pbr": 1.25,
                    "debt_ratio": 0.50,
                    "fundamental_score": 48.7,
                    "fundamental_view": "FUNDAMENTAL_NEUTRAL",
                    "why_summary": "FUNDAMENTAL_NEUTRAL",
                },
                {
                    "symbol": "005930.KS",
                    "per": 41.9,
                    "pbr": 4.34,
                    "debt_ratio": 0.30,
                    "fundamental_score": 46.3,
                    "fundamental_view": "FUNDAMENTAL_NEUTRAL",
                    "why_summary": "VALUATION_EXPENSIVE",
                },
                {
                    "symbol": "012330.KS",
                    "per": 17.1,
                    "pbr": 1.27,
                    "debt_ratio": 0.43,
                    "fundamental_score": 44.8,
                    "fundamental_view": "FUNDAMENTAL_WEAK",
                    "why_summary": "FUNDAMENTAL_WEAK",
                },
            ]
        ).to_csv(company_research_csv, index=False)

        output = run_conviction_score(
            market_watch_csv=market_watch_csv,
            company_research_csv=company_research_csv,
            output_dir=output_dir,
            include_labels=("PERSISTENT_FOCUS", "BUILDING_FOCUS"),
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.summary["candidate_count"] == 2
        assert output.report["symbol"].tolist() == ["028260.KS", "005930.KS"]
        assert output.report.loc[0, "conviction_tier"] == "HIGH_CONVICTION_RESEARCH"
        assert output.report.loc[1, "conviction_tier"] == "DEVELOPING_CONVICTION"
        assert output.report.loc[1, "valuation_penalty"] > 0
        assert "밸류에이션 부담" in output.report.loc[1, "conviction_risks"]

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "# Conviction Score" in markdown
        assert "실제 주문 실행 문서가 아닙니다" in markdown
        assert "028260.KS Samsung C&T" in markdown
        assert "012330.KS" not in markdown

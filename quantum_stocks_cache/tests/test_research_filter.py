from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.research_filter import run_research_filter


def test_research_filter_classifies_candidates_and_writes_decision_report() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        company_research_csv = root / "company_research.csv"
        output_dir = root / "reports"
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "Samsung C&T",
                    "research_score": 88.5,
                    "research_view": "RESEARCH_CANDIDATE",
                    "decision": "BUY_READY",
                    "fundamental_view": "FUNDAMENTAL_NEUTRAL",
                    "why_summary": "ALPHA_BUY_READY,POSITIVE_EXPECTED_RETURN,ABOVE_SMA20",
                    "expected_20d_return": 0.15,
                    "upside_probability": 0.78,
                    "return_20d": 0.32,
                    "ma20_gap": 0.08,
                    "drawdown_20d": -0.04,
                    "per": 18.4,
                    "pbr": 1.25,
                    "debt_ratio": 0.50,
                    "fundamental_score": 48.7,
                },
                {
                    "symbol": "012330.KS",
                    "company_name": "Hyundai Mobis",
                    "research_score": 86.9,
                    "research_view": "WATCHLIST",
                    "decision": "BUY_READY",
                    "fundamental_view": "FUNDAMENTAL_WEAK",
                    "why_summary": "ALPHA_BUY_READY,POSITIVE_20D_MOMENTUM,FUNDAMENTAL_WEAK",
                    "expected_20d_return": 0.14,
                    "upside_probability": 0.73,
                    "return_20d": 0.63,
                    "ma20_gap": 0.27,
                    "drawdown_20d": 0.0,
                    "per": 17.1,
                    "pbr": 1.27,
                    "debt_ratio": 0.43,
                    "fundamental_score": 44.8,
                },
                {
                    "symbol": "000660.KS",
                    "company_name": "SK hynix",
                    "research_score": 56.5,
                    "research_view": "AVOID_FOR_NOW",
                    "decision": "AVOID",
                    "fundamental_view": "FUNDAMENTAL_WEAK",
                    "why_summary": "ALPHA_AVOID,FUNDAMENTAL_WEAK",
                    "expected_20d_return": -0.03,
                    "upside_probability": 0.38,
                    "return_20d": 0.12,
                    "ma20_gap": 0.04,
                    "drawdown_20d": -0.10,
                    "per": 39.6,
                    "pbr": 14.1,
                    "debt_ratio": 0.8,
                    "fundamental_score": 41.5,
                },
            ]
        ).to_csv(company_research_csv, index=False)

        output = run_research_filter(
            company_research_csv=company_research_csv,
            output_dir=output_dir,
            top_n=3,
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.report["filter_status"].tolist() == [
            "PRIORITY_RESEARCH",
            "WATCH_FOR_CONFIRMATION",
            "EXCLUDE_UNTIL_RESET",
        ]
        assert "재무 점수 보강 확인" in output.report.loc[1, "wait_reason"]
        assert "AVOID" in output.report.loc[2, "exclusion_condition"]

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "# Candidate Research Filter" in markdown
        assert "## 1. 028260.KS Samsung C&T" in markdown
        assert "### 투자 논리" in markdown
        assert "### 대기 사유" in markdown
        assert "### 제외 조건" in markdown
        assert "실제 주문 실행 리포트가 아닙니다" in markdown


def test_research_filter_keeps_priority_candidates_even_outside_top_n() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        company_research_csv = root / "company_research.csv"
        output_dir = root / "reports"
        rows = []
        for index in range(5):
            rows.append(
                {
                    "symbol": f"00000{index}.KS",
                    "company_name": f"High Score Watch {index}",
                    "research_score": 90.0 - index,
                    "research_view": "WATCHLIST",
                    "decision": "BUY_READY",
                    "fundamental_view": "FUNDAMENTAL_WEAK",
                    "why_summary": "ALPHA_BUY_READY,FUNDAMENTAL_WEAK",
                    "expected_20d_return": 0.12,
                    "upside_probability": 0.72,
                    "return_20d": 0.10,
                    "ma20_gap": 0.05,
                    "drawdown_20d": -0.02,
                    "per": 12.0,
                    "pbr": 1.0,
                    "debt_ratio": 0.5,
                    "fundamental_score": 35.0,
                }
            )
        rows.append(
            {
                "symbol": "003550.KS",
                "company_name": "LG Corp",
                "research_score": 75.0,
                "research_view": "RESEARCH_CANDIDATE",
                "decision": "BUY_READY",
                "fundamental_view": "FUNDAMENTAL_NEUTRAL",
                "why_summary": "ALPHA_BUY_READY,POSITIVE_EXPECTED_RETURN,ABOVE_SMA20",
                "expected_20d_return": 0.09,
                "upside_probability": 0.65,
                "return_20d": 0.07,
                "ma20_gap": 0.03,
                "drawdown_20d": -0.02,
                "per": 18.0,
                "pbr": 0.8,
                "debt_ratio": 0.4,
                "fundamental_score": 52.0,
            }
        )
        pd.DataFrame(rows).to_csv(company_research_csv, index=False)

        output = run_research_filter(
            company_research_csv=company_research_csv,
            output_dir=output_dir,
            top_n=5,
        )

        assert "003550.KS" in output.report["symbol"].tolist()
        lg = output.report.loc[output.report["symbol"] == "003550.KS"].iloc[0]
        assert lg["filter_status"] == "PRIORITY_RESEARCH"
        assert len(output.report) == 6

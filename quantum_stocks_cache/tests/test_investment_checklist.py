from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.investment_checklist import run_investment_checklist


def test_investment_checklist_writes_automatic_and_manual_gates() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        candidate_briefs_csv = root / "candidate_briefs.csv"
        output_dir = root / "reports"
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "Samsung C&T",
                    "filter_status": "PRIORITY_RESEARCH",
                    "research_score": 88.5,
                    "decision": "BUY_READY",
                    "fundamental_view": "FUNDAMENTAL_NEUTRAL",
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
                    "symbol": "005930.KS",
                    "company_name": "Samsung Electronics",
                    "filter_status": "PRIORITY_RESEARCH",
                    "research_score": 87.5,
                    "decision": "BUY_READY",
                    "fundamental_view": "FUNDAMENTAL_NEUTRAL",
                    "expected_20d_return": 0.19,
                    "upside_probability": 0.86,
                    "return_20d": 0.45,
                    "ma20_gap": 0.18,
                    "drawdown_20d": 0.0,
                    "per": 41.9,
                    "pbr": 4.34,
                    "debt_ratio": 0.30,
                    "fundamental_score": 46.3,
                },
            ]
        ).to_csv(candidate_briefs_csv, index=False)

        output = run_investment_checklist(
            candidate_briefs_csv=candidate_briefs_csv,
            output_dir=output_dir,
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.report["checklist_status"].tolist() == [
            "READY_FOR_MANUAL_REVIEW",
            "NEEDS_MANUAL_REVIEW",
        ]
        assert output.report.loc[0, "automatic_pass_count"] >= 6
        assert "밸류에이션 부담" in output.report.loc[1, "automatic_blockers"]
        assert "최근 공시 확인" in output.report.loc[0, "manual_checklist"]
        assert "목표 비중은 별도 order sizing에서만 계산" in output.report.loc[0, "manual_checklist"]

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "# Investment Checklist" in markdown
        assert "실제 주문 실행 문서가 아닙니다" in markdown
        assert "## 1. 028260.KS Samsung C&T" in markdown
        assert "### 자동 체크" in markdown
        assert "### 수동 체크리스트" in markdown

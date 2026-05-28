from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.profit_focus import run_profit_focus


def test_profit_focus_distills_core_wait_and_missing_checklist_candidates() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        conviction_csv = root / "conviction_score.csv"
        checklist_csv = root / "investment_checklist.csv"
        output_dir = root / "reports"
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "Samsung C&T",
                    "sector": "Holding",
                    "conviction_score": 77.0,
                    "conviction_tier": "DEVELOPING_CONVICTION",
                    "persistence_label": "BUILDING_FOCUS",
                    "conviction_reasons": "BUILDING_FOCUS; upside probability ok",
                    "conviction_risks": "not persistent yet",
                    "expected_20d_return": 0.15,
                    "upside_probability": 0.78,
                    "ma20_gap": 0.08,
                    "drawdown_20d": -0.04,
                    "per": 18.4,
                    "pbr": 1.25,
                },
                {
                    "symbol": "005930.KS",
                    "company_name": "Samsung Electronics",
                    "sector": "Semiconductors",
                    "conviction_score": 62.1,
                    "conviction_tier": "DEVELOPING_CONVICTION",
                    "persistence_label": "BUILDING_FOCUS",
                    "conviction_reasons": "BUILDING_FOCUS; upside probability ok",
                    "conviction_risks": "밸류에이션 부담; not persistent yet",
                    "expected_20d_return": 0.19,
                    "upside_probability": 0.86,
                    "ma20_gap": 0.18,
                    "drawdown_20d": 0.0,
                    "per": 41.9,
                    "pbr": 4.34,
                },
                {
                    "symbol": "003550.KS",
                    "company_name": "LG Corp",
                    "sector": "Holding",
                    "conviction_score": 60.5,
                    "conviction_tier": "DEVELOPING_CONVICTION",
                    "persistence_label": "BUILDING_FOCUS",
                    "conviction_reasons": "BUILDING_FOCUS; above SMA20",
                    "conviction_risks": "not persistent yet",
                    "expected_20d_return": 0.05,
                    "upside_probability": 0.62,
                    "ma20_gap": 0.08,
                    "drawdown_20d": -0.05,
                    "per": 18.2,
                    "pbr": 0.60,
                },
            ]
        ).to_csv(conviction_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "checklist_status": "READY_FOR_MANUAL_REVIEW",
                    "automatic_blockers": "없음",
                    "manual_checklist": "최근 공시 확인; 손절 조건 문서화",
                },
                {
                    "symbol": "005930.KS",
                    "checklist_status": "NEEDS_MANUAL_REVIEW",
                    "automatic_blockers": "밸류에이션 부담",
                    "manual_checklist": "높은 PER/PBR 확인",
                },
            ]
        ).to_csv(checklist_csv, index=False)

        output = run_profit_focus(
            conviction_csv=conviction_csv,
            checklist_csv=checklist_csv,
            output_dir=output_dir,
            max_core=2,
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.summary["core_count"] == 1
        assert output.report["symbol"].tolist() == ["028260.KS", "005930.KS", "003550.KS"]
        assert output.report.loc[0, "profit_focus_status"] == "CORE_FOCUS"
        assert output.report.loc[1, "profit_focus_status"] == "WAIT_RISK"
        assert output.report.loc[2, "profit_focus_status"] == "NEEDS_CHECKLIST"
        assert "밸류에이션 부담" in output.report.loc[1, "why_not_now"]
        assert output.report.loc[1, "why_not_now"].count("밸류에이션 부담") == 1
        assert "체크리스트 없음" in output.report.loc[2, "why_not_now"]

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "# Profit Focus" in markdown
        assert "실제 주문 실행 문서가 아닙니다" in markdown
        assert "## Core Focus" in markdown
        assert "028260.KS Samsung C&T" in markdown
        assert "005930.KS Samsung Electronics" in markdown


def test_profit_focus_writes_today_focus_action_board() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        conviction_csv = root / "conviction_score.csv"
        checklist_csv = root / "investment_checklist.csv"
        output_dir = root / "reports"
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "Samsung C&T",
                    "sector": "Holding",
                    "conviction_score": 77.0,
                    "conviction_tier": "DEVELOPING_CONVICTION",
                    "persistence_label": "BUILDING_FOCUS",
                    "conviction_reasons": "BUILDING_FOCUS; upside probability ok",
                    "conviction_risks": "not persistent yet",
                    "expected_20d_return": 0.15,
                    "upside_probability": 0.78,
                    "ma20_gap": 0.08,
                    "drawdown_20d": -0.04,
                    "per": 18.4,
                    "pbr": 1.25,
                },
                {
                    "symbol": "005930.KS",
                    "company_name": "Samsung Electronics",
                    "sector": "Semiconductors",
                    "conviction_score": 62.1,
                    "conviction_tier": "DEVELOPING_CONVICTION",
                    "persistence_label": "BUILDING_FOCUS",
                    "conviction_reasons": "BUILDING_FOCUS; upside probability ok",
                    "conviction_risks": "밸류에이션 부담; not persistent yet",
                    "expected_20d_return": 0.19,
                    "upside_probability": 0.86,
                    "ma20_gap": 0.18,
                    "drawdown_20d": 0.0,
                    "per": 41.9,
                    "pbr": 4.34,
                },
            ]
        ).to_csv(conviction_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "checklist_status": "READY_FOR_MANUAL_REVIEW",
                    "automatic_blockers": "없음",
                    "manual_checklist": "최근 공시 확인; 손절 조건 문서화",
                },
                {
                    "symbol": "005930.KS",
                    "checklist_status": "NEEDS_MANUAL_REVIEW",
                    "automatic_blockers": "밸류에이션 부담",
                    "manual_checklist": "높은 PER/PBR 확인",
                },
            ]
        ).to_csv(checklist_csv, index=False)

        output = run_profit_focus(
            conviction_csv=conviction_csv,
            checklist_csv=checklist_csv,
            output_dir=output_dir,
            max_core=3,
        )

        assert output.today_focus_path.exists()
        today = output.today_focus_path.read_text(encoding="utf-8")
        assert "# Today Focus" in today
        assert "오늘 1순위" in today
        assert "028260.KS Samsung C&T" in today
        assert "왜 후보인가" in today
        assert "손실 방어" in today
        assert "아직 매수 버튼을 누르지 않는다" in today
        assert "대기/제외" in today
        assert "005930.KS Samsung Electronics" in today
        assert "밸류에이션 부담" in today

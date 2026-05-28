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


def test_investment_memo_turns_core_focus_into_no_order_thesis_review() -> None:
    module = importlib.import_module("quantum_trainer.investment_memo")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        profit_focus_csv = root / "profit_focus.csv"
        output_dir = root / "reports"
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "Samsung C&T",
                    "sector": "Holding",
                    "profit_focus_status": "CORE_FOCUS",
                    "conviction_score": 77.0,
                    "expected_20d_return": 0.158,
                    "upside_probability": 0.99,
                    "ma20_gap": 0.097,
                    "return_20d": 0.361,
                    "per": 18.4,
                    "pbr": 1.25,
                    "debt_ratio": 0.50,
                    "fundamental_view": "FUNDAMENTAL_NEUTRAL",
                    "why_profit_candidate": "conviction_score=77.00; upside_probability=99.0%",
                    "why_not_now": "핵심 후보지만 실제 주문 전 수동 확인 필요",
                    "invalidation_rule": "TODAY_FOCUS 이탈, SMA20 하회, conviction_score 60 미만",
                    "next_step": "사업/공시 수동 확인 후 투자금이 생길 때만 order_sizer 검토",
                    "checklist_status": "READY_FOR_MANUAL_REVIEW",
                    "automatic_blockers": "없음",
                    "manual_checklist": "최근 공시 확인; 손절 조건 문서화; 실제 주문 전 current_weights 확인",
                    "conviction_risks": "not persistent yet",
                },
                {
                    "symbol": "005930.KS",
                    "company_name": "Samsung Electronics",
                    "sector": "Semiconductors",
                    "profit_focus_status": "WAIT_RISK",
                    "conviction_score": 62.0,
                    "expected_20d_return": 0.198,
                    "upside_probability": 0.86,
                    "ma20_gap": 0.187,
                    "return_20d": 0.458,
                    "per": 41.9,
                    "pbr": 4.34,
                    "debt_ratio": 0.30,
                    "fundamental_view": "FUNDAMENTAL_NEUTRAL",
                    "why_profit_candidate": "conviction_score=62.00",
                    "why_not_now": "밸류에이션 부담; conviction_score 65 미만",
                    "invalidation_rule": "TODAY_FOCUS 이탈",
                    "next_step": "리스크가 해소될 때까지 관찰",
                    "checklist_status": "NEEDS_MANUAL_REVIEW",
                    "automatic_blockers": "밸류에이션 부담",
                    "manual_checklist": "높은 PER/PBR 확인",
                    "conviction_risks": "밸류에이션 부담",
                },
            ]
        ).to_csv(profit_focus_csv, index=False)

        output = module.run_investment_memo(
            profit_focus_csv=profit_focus_csv,
            output_dir=output_dir,
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.summary["memo_count"] == 1
        assert output.report["symbol"].tolist() == ["028260.KS"]
        assert output.report.loc[0, "memo_status"] == "THESIS_REVIEW"
        assert output.report.loc[0, "order_status"] == "NO_ORDER"
        assert "최근 공시 확인" in output.report.loc[0, "manual_checks"]
        assert "TODAY_FOCUS 이탈" in output.report.loc[0, "loss_defense"]

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "# Investment Memo" in markdown
        assert "028260.KS Samsung C&T" in markdown
        assert "핵심 판단" in markdown
        assert "손실 방어" in markdown
        assert "수동 확인" in markdown
        assert "실제 주문 문서가 아닙니다" in markdown
        assert "주문으로 해석하지 않는다" in markdown


def test_investment_memo_writes_readable_empty_report_when_no_core_focus_exists() -> None:
    module = importlib.import_module("quantum_trainer.investment_memo")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        profit_focus_csv = root / "profit_focus.csv"
        output_dir = root / "reports"
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "Samsung C&T",
                    "sector": "Holding",
                    "profit_focus_status": "WAIT_RISK",
                    "conviction_score": 74.0,
                    "expected_20d_return": 0.158,
                    "upside_probability": 0.99,
                    "ma20_gap": 0.097,
                    "return_20d": 0.361,
                    "per": 18.4,
                    "pbr": 1.25,
                    "debt_ratio": 0.50,
                    "fundamental_view": "FUNDAMENTAL_NEUTRAL",
                    "why_profit_candidate": "conviction_score=74.00",
                    "why_not_now": "20일 낙폭 10% 초과",
                    "invalidation_rule": "TODAY_FOCUS 이탈",
                    "next_step": "관찰",
                    "checklist_status": "NEEDS_MANUAL_REVIEW",
                    "automatic_blockers": "20일 낙폭 10% 초과",
                    "manual_checklist": "낙폭 원인 확인",
                    "conviction_risks": "drawdown deep",
                }
            ]
        ).to_csv(profit_focus_csv, index=False)

        output = module.run_investment_memo(
            profit_focus_csv=profit_focus_csv,
            output_dir=output_dir,
        )

        assert output.summary["memo_count"] == 0
        saved = pd.read_csv(output.csv_path)
        assert saved.empty
        assert {
            "symbol",
            "company_name",
            "sector",
            "memo_status",
            "order_status",
            "core_thesis",
            "evidence",
            "risks",
            "manual_checks",
            "loss_defense",
            "next_action",
        }.issubset(saved.columns)
        assert "No Core Candidate" in output.markdown_path.read_text(encoding="utf-8")

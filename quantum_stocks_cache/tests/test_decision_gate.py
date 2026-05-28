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


def _write_investment_memo(path: Path) -> None:
    pd.DataFrame(
        [
            {
                "symbol": "028260.KS",
                "company_name": "Samsung C&T",
                "sector": "Holding",
                "memo_status": "THESIS_REVIEW",
                "order_status": "NO_ORDER",
                "core_thesis": "Samsung C&T는 CORE_FOCUS입니다.",
                "evidence": "conviction_score=77.00; PER=18.40",
                "risks": "not persistent yet",
                "manual_checks": "최근 공시 확인; 손절 조건 문서화; 실제 주문 전 current_weights 확인",
                "loss_defense": "TODAY_FOCUS 이탈, SMA20 하회",
                "next_action": "수동 확인 후 투자금이 생길 때만 order_sizer 검토",
            }
        ]
    ).to_csv(path, index=False)


def test_decision_gate_creates_manual_review_template_and_waits_for_evidence() -> None:
    module = importlib.import_module("quantum_trainer.decision_gate")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        memo_csv = root / "investment_memo.csv"
        output_dir = root / "reports"
        _write_investment_memo(memo_csv)

        output = module.run_decision_gate(
            investment_memo_csv=memo_csv,
            output_dir=output_dir,
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.template_path.exists()
        assert output.report.loc[0, "decision_gate_status"] == "WAITING_MANUAL_EVIDENCE"
        assert output.report.loc[0, "order_status"] == "NO_ORDER"
        assert "filing_review" in output.template_path.read_text(encoding="utf-8")

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "# Decision Gate" in markdown
        assert "실제 주문 문서가 아닙니다" in markdown
        assert "수동 근거 대기" in markdown


def test_decision_gate_marks_all_passed_manual_review_ready_for_sizing_review() -> None:
    module = importlib.import_module("quantum_trainer.decision_gate")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        memo_csv = root / "investment_memo.csv"
        review_csv = root / "manual_review.csv"
        output_dir = root / "reports"
        _write_investment_memo(memo_csv)
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "filing_review": "PASS",
                    "earnings_review": "PASS",
                    "business_driver_review": "PASS",
                    "valuation_review": "PASS",
                    "loss_rule_review": "PASS",
                    "capital_plan_review": "PASS",
                    "review_notes": "공시와 손실 방어 조건 수동 확인 완료",
                }
            ]
        ).to_csv(review_csv, index=False)

        output = module.run_decision_gate(
            investment_memo_csv=memo_csv,
            output_dir=output_dir,
            manual_review_csv=review_csv,
        )

        assert output.summary["ready_count"] == 1
        assert output.report.loc[0, "decision_gate_status"] == "READY_FOR_SIZING_REVIEW"
        assert output.report.loc[0, "order_status"] == "NO_ORDER"
        assert "공시와 손실 방어 조건" in output.report.loc[0, "review_notes"]

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "READY_FOR_SIZING_REVIEW" in markdown
        assert "NO_ORDER" in markdown

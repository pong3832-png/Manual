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


def test_capital_plan_review_creates_rule_first_plan_without_assuming_capital() -> None:
    module = importlib.import_module("quantum_trainer.capital_plan_review")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        memo_csv = root / "investment_memo.csv"
        checklist_csv = root / "investment_checklist.csv"
        research_csv = root / "company_research.csv"
        output_dir = root / "reports"

        pd.DataFrame(
            [
                {
                    "symbol": "003550.KS",
                    "company_name": "LG Corp",
                    "sector": "Holding",
                    "memo_status": "THESIS_REVIEW",
                    "order_status": "NO_ORDER",
                    "core_thesis": "LG Corp is CORE_FOCUS.",
                    "evidence": "conviction_score=68.64",
                    "risks": "manual checks remain",
                    "manual_checks": "recent filing and capital plan",
                    "loss_defense": "TODAY_FOCUS 이탈, SMA20 하회, conviction_score 60 미만",
                    "next_action": "수동 확인 후 투자금이 생길 때만 order_sizer 검토",
                }
            ]
        ).to_csv(memo_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "003550.KS",
                    "company_name": "LG Corp",
                    "checklist_status": "READY_FOR_MANUAL_REVIEW",
                    "automatic_blockers": "없음",
                    "manual_checklist": "목표 비중은 별도 order sizing에서만 계산",
                }
            ]
        ).to_csv(checklist_csv, index=False)
        pd.DataFrame(
            [
                {
                    "symbol": "003550.KS",
                    "company_name": "LG Corp",
                    "research_score": 75.18,
                    "research_view": "RESEARCH_CANDIDATE",
                    "decision": "BUY_READY",
                    "expected_20d_return": 0.057,
                    "upside_probability": 0.629,
                    "ma20_gap": 0.057,
                    "return_20d": 0.15,
                    "drawdown_20d": -0.03,
                    "per": 17.96,
                    "pbr": 0.59,
                }
            ]
        ).to_csv(research_csv, index=False)

        output = module.run_capital_plan_review(
            investment_memo_csv=memo_csv,
            investment_checklist_csv=checklist_csv,
            company_research_csv=research_csv,
            output_dir=output_dir,
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert (output_dir / "decision_gate" / "capital_plan_review_003550.csv").exists()
        assert (output_dir / "decision_gate" / "capital_plan_review_003550.md").exists()

        row = output.report.iloc[0]
        assert row["symbol"] == "003550.KS"
        assert row["capital_plan_review"] == "PASS_CANDIDATE"
        assert row["amount_status"] == "CAPITAL_AMOUNT_REQUIRED"
        assert row["order_status"] == "NO_ORDER"
        assert row["max_position_weight"] == 0.15
        assert row["first_tranche_pct"] == 0.30
        assert row["second_tranche_pct"] == 0.30
        assert row["final_tranche_pct"] == 0.40
        assert "CORE_FOCUS" in row["add_condition"]
        assert "-7%" in row["reduce_condition"]
        assert "conviction_score 60" in row["stop_condition"]
        assert "실적 훼손" in row["immediate_halt_condition"]

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "# Capital Plan Review" in markdown
        assert "CAPITAL_AMOUNT_REQUIRED" in markdown
        assert "실제 주문 실행 문서가 아닙니다" in markdown


def test_capital_plan_review_marks_amount_provided_when_total_capital_is_given() -> None:
    module = importlib.import_module("quantum_trainer.capital_plan_review")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        memo_csv = root / "investment_memo.csv"
        checklist_csv = root / "investment_checklist.csv"
        research_csv = root / "company_research.csv"
        output_dir = root / "reports"
        _write_capital_plan_inputs(memo_csv, checklist_csv, research_csv)

        output = module.run_capital_plan_review(
            investment_memo_csv=memo_csv,
            investment_checklist_csv=checklist_csv,
            company_research_csv=research_csv,
            output_dir=output_dir,
            total_capital=3_000_000,
        )

        row = output.report.iloc[0]
        assert row["amount_status"] == "CAPITAL_PROVIDED"
        assert row["total_capital"] == 3_000_000
        assert "total_capital=3000000" in row["review_notes"]


def _write_capital_plan_inputs(memo_csv: Path, checklist_csv: Path, research_csv: Path) -> None:
    pd.DataFrame(
        [
            {
                "symbol": "003550.KS",
                "company_name": "LG Corp",
                "sector": "Holding",
                "memo_status": "THESIS_REVIEW",
                "order_status": "NO_ORDER",
                "core_thesis": "LG Corp is CORE_FOCUS.",
                "evidence": "conviction_score=68.64",
                "risks": "manual checks remain",
                "manual_checks": "recent filing and capital plan",
                "loss_defense": "TODAY_FOCUS 이탈, SMA20 하회, conviction_score 60 미만",
                "next_action": "수동 확인 후 투자금이 생길 때만 order_sizer 검토",
            }
        ]
    ).to_csv(memo_csv, index=False)
    pd.DataFrame(
        [
            {
                "symbol": "003550.KS",
                "company_name": "LG Corp",
                "checklist_status": "READY_FOR_MANUAL_REVIEW",
                "automatic_blockers": "없음",
                "manual_checklist": "목표 비중은 별도 order sizing에서만 계산",
            }
        ]
    ).to_csv(checklist_csv, index=False)
    pd.DataFrame(
        [
            {
                "symbol": "003550.KS",
                "company_name": "LG Corp",
                "research_score": 75.18,
                "research_view": "RESEARCH_CANDIDATE",
                "decision": "BUY_READY",
                "expected_20d_return": 0.057,
                "upside_probability": 0.629,
                "ma20_gap": 0.057,
                "return_20d": 0.15,
                "drawdown_20d": -0.03,
                "per": 17.96,
                "pbr": 0.59,
            }
        ]
    ).to_csv(research_csv, index=False)

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.order_sizer import run_order_sizer


def test_order_sizer_creates_review_only_buy_candidates_from_ready_checklist() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        checklist_csv = root / "investment_checklist.csv"
        prices_csv = root / "prices.csv"
        output_dir = root / "reports"

        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "Samsung C&T",
                    "checklist_status": "READY_FOR_MANUAL_REVIEW",
                    "automatic_blockers": "없음",
                    "research_score": 88.5,
                    "decision": "BUY_READY",
                },
                {
                    "symbol": "005930.KS",
                    "company_name": "Samsung Electronics",
                    "checklist_status": "NEEDS_MANUAL_REVIEW",
                    "automatic_blockers": "밸류에이션 부담",
                    "research_score": 87.5,
                    "decision": "BUY_READY",
                },
            ]
        ).to_csv(checklist_csv, index=False)
        pd.DataFrame(
            [
                {"date": "2026-05-26", "028260.KS": 400000, "005930.KS": 300000},
                {"date": "2026-05-27", "028260.KS": 424000, "005930.KS": 320000},
            ]
        ).to_csv(prices_csv, index=False)

        output = run_order_sizer(
            candidate_checklist_csv=checklist_csv,
            prices_csv=prices_csv,
            output_dir=output_dir,
            total_capital=10_000_000,
            max_position_weight=0.20,
            cash_buffer_weight=0.10,
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.summary["eligible_count"] == 1
        assert output.summary["estimated_cash_after_orders"] == 8_304_000
        row = output.report.iloc[0]
        assert row["symbol"] == "028260.KS"
        assert row["order_status"] == "REVIEW_ONLY"
        assert row["latest_price"] == 424_000
        assert row["target_weight"] == 0.20
        assert row["target_value"] == 2_000_000
        assert row["candidate_shares"] == 4
        assert row["estimated_order_value"] == 1_696_000
        assert row["uninvested_target_cash"] == 304_000

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "# Order Candidates" in markdown
        assert "실제 주문 실행 문서가 아닙니다" in markdown
        assert "028260.KS Samsung C&T" in markdown
        assert "005930.KS" not in markdown


def test_order_sizer_blocks_sizing_without_assuming_total_capital() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        checklist_csv = root / "investment_checklist.csv"
        prices_csv = root / "prices.csv"
        output_dir = root / "reports"

        pd.DataFrame(
            [
                {
                    "symbol": "003550.KS",
                    "company_name": "LG Corp",
                    "checklist_status": "READY_FOR_MANUAL_REVIEW",
                    "automatic_blockers": "없음",
                    "research_score": 75.2,
                    "decision": "BUY_READY",
                },
            ]
        ).to_csv(checklist_csv, index=False)
        pd.DataFrame(
            [
                {"date": "2026-05-28", "003550.KS": 116_500},
            ]
        ).to_csv(prices_csv, index=False)

        output = run_order_sizer(
            candidate_checklist_csv=checklist_csv,
            prices_csv=prices_csv,
            output_dir=output_dir,
            total_capital=None,
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.summary["capital_status"] == "CAPITAL_REQUIRED"
        row = output.report.iloc[0]
        assert row["symbol"] == "003550.KS"
        assert row["order_status"] == "BLOCKED_CAPITAL_REQUIRED"
        assert row["target_value"] == 0
        assert row["candidate_shares"] == 0
        assert row["estimated_order_value"] == 0

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "Capital status: CAPITAL_REQUIRED" in markdown
        assert "BLOCKED_CAPITAL_REQUIRED" in markdown

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


def test_manual_review_proposal_converts_pass_candidates_without_touching_actual_config() -> None:
    module = importlib.import_module("quantum_trainer.manual_review_proposal")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        draft_csv = root / "manual_review_draft.csv"
        output_dir = root / "reports"
        actual_config = root / "configs" / "manual_review.actual.csv"

        pd.DataFrame(
            [
                {
                    "symbol": "003550.KS",
                    "company_name": "LG Corp",
                    "filing_review": "PASS_CANDIDATE",
                    "earnings_review": "PASS_CANDIDATE",
                    "business_driver_review": "PASS_CANDIDATE",
                    "valuation_review": "PASS_CANDIDATE",
                    "loss_rule_review": "PASS_CANDIDATE",
                    "capital_plan_review": "PASS_CANDIDATE",
                    "recommended_actual_action": "DO_NOT_COPY_AUTOMATICALLY",
                    "review_notes": "all six draft fields have candidate evidence",
                }
            ]
        ).to_csv(draft_csv, index=False)

        output = module.run_manual_review_proposal(
            manual_review_draft_csv=draft_csv,
            output_dir=output_dir,
        )

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert (output_dir / "decision_gate" / "manual_review_proposal_003550.csv").exists()
        assert not actual_config.exists()

        row = output.report.iloc[0]
        assert row["proposal_status"] == "READY_FOR_USER_CONFIRMATION"
        assert row["approval_required"] == "YES"
        assert row["apply_target"] == "configs/manual_review.actual.csv"
        for column in module.REVIEW_STATUS_COLUMNS:
            assert row[column] == "PASS"
        assert "USER_CONFIRMATION_REQUIRED" in row["review_notes"]

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "# Manual Review Proposal" in markdown
        assert "Do not copy automatically" in markdown
        assert "READY_FOR_USER_CONFIRMATION" in markdown


def test_manual_review_proposal_keeps_unknown_when_draft_is_incomplete() -> None:
    module = importlib.import_module("quantum_trainer.manual_review_proposal")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        draft_csv = root / "manual_review_draft.csv"
        output_dir = root / "reports"

        pd.DataFrame(
            [
                {
                    "symbol": "005930.KS",
                    "company_name": "Samsung Electronics",
                    "filing_review": "UNKNOWN",
                    "earnings_review": "PASS_CANDIDATE",
                    "business_driver_review": "PASS_CANDIDATE",
                    "valuation_review": "UNKNOWN",
                    "loss_rule_review": "PASS_CANDIDATE",
                    "capital_plan_review": "PASS_CANDIDATE",
                    "recommended_actual_action": "DO_NOT_COPY_AUTOMATICALLY",
                    "review_notes": "filing and valuation still missing",
                }
            ]
        ).to_csv(draft_csv, index=False)

        output = module.run_manual_review_proposal(
            manual_review_draft_csv=draft_csv,
            output_dir=output_dir,
        )

        row = output.report.iloc[0]
        assert row["proposal_status"] == "INCOMPLETE_DRAFT"
        assert row["filing_review"] == "UNKNOWN"
        assert row["valuation_review"] == "UNKNOWN"
        assert row["earnings_review"] == "PASS"

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


def test_manual_review_apply_plan_dry_run_writes_candidate_but_not_actual_config() -> None:
    module = importlib.import_module("quantum_trainer.manual_review_apply_plan")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        proposal_csv = root / "manual_review_proposal.csv"
        output_dir = root / "reports"
        actual_config = root / "configs" / "manual_review.actual.csv"

        pd.DataFrame(
            [
                {
                    "symbol": "003550.KS",
                    "filing_review": "PASS",
                    "earnings_review": "PASS",
                    "business_driver_review": "PASS",
                    "valuation_review": "PASS",
                    "loss_rule_review": "PASS",
                    "capital_plan_review": "PASS",
                    "review_notes": "USER_CONFIRMATION_REQUIRED",
                    "proposal_status": "READY_FOR_USER_CONFIRMATION",
                    "approval_required": "YES",
                    "apply_target": "configs/manual_review.actual.csv",
                    "source_action": "DO_NOT_COPY_AUTOMATICALLY",
                }
            ]
        ).to_csv(proposal_csv, index=False)

        output = module.run_manual_review_apply_plan(
            manual_review_proposal_csv=proposal_csv,
            output_dir=output_dir,
            actual_output_csv=actual_config,
        )

        assert output.plan_csv_path.exists()
        assert output.candidate_csv_path.exists()
        assert output.markdown_path.exists()
        assert not actual_config.exists()

        plan_row = output.plan.iloc[0]
        assert plan_row["apply_mode"] == "DRY_RUN"
        assert plan_row["ready_to_apply"] == "YES"
        assert plan_row["confirm_required"] == "YES"
        assert plan_row["actual_config_written"] == "NO"
        assert plan_row["actual_output_csv"] == str(actual_config)

        candidate = pd.read_csv(output.candidate_csv_path).fillna("")
        assert list(candidate.columns) == module.ACTUAL_COLUMNS
        assert candidate.loc[0, "symbol"] == "003550.KS"
        assert candidate.loc[0, "filing_review"] == "PASS"
        assert "SOURCE=manual_review_proposal" in candidate.loc[0, "review_notes"]


def test_manual_review_apply_plan_requires_exact_confirmation_token_to_write_actual_config() -> None:
    module = importlib.import_module("quantum_trainer.manual_review_apply_plan")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        proposal_csv = root / "manual_review_proposal.csv"
        output_dir = root / "reports"
        actual_config = root / "configs" / "manual_review.actual.csv"

        pd.DataFrame(
            [
                {
                    "symbol": "003550.KS",
                    "filing_review": "PASS",
                    "earnings_review": "PASS",
                    "business_driver_review": "PASS",
                    "valuation_review": "PASS",
                    "loss_rule_review": "PASS",
                    "capital_plan_review": "PASS",
                    "review_notes": "USER_CONFIRMATION_REQUIRED",
                    "proposal_status": "READY_FOR_USER_CONFIRMATION",
                    "approval_required": "YES",
                    "apply_target": "configs/manual_review.actual.csv",
                    "source_action": "DO_NOT_COPY_AUTOMATICALLY",
                }
            ]
        ).to_csv(proposal_csv, index=False)

        wrong = module.run_manual_review_apply_plan(
            manual_review_proposal_csv=proposal_csv,
            output_dir=output_dir,
            actual_output_csv=actual_config,
            confirm_token="yes",
        )
        assert wrong.plan.iloc[0]["actual_config_written"] == "NO"
        assert not actual_config.exists()

        confirmed = module.run_manual_review_apply_plan(
            manual_review_proposal_csv=proposal_csv,
            output_dir=output_dir,
            actual_output_csv=actual_config,
            confirm_token=module.CONFIRM_TOKEN,
        )
        assert confirmed.plan.iloc[0]["apply_mode"] == "CONFIRMED_WRITE"
        assert confirmed.plan.iloc[0]["actual_config_written"] == "YES"
        assert actual_config.exists()
        actual = pd.read_csv(actual_config).fillna("")
        assert actual.loc[0, "capital_plan_review"] == "PASS"


def test_manual_review_apply_plan_recognizes_existing_matching_actual_config() -> None:
    module = importlib.import_module("quantum_trainer.manual_review_apply_plan")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        proposal_csv = root / "manual_review_proposal.csv"
        output_dir = root / "reports"
        actual_config = root / "configs" / "manual_review.actual.csv"

        pd.DataFrame(
            [
                {
                    "symbol": "003550.KS",
                    "filing_review": "PASS",
                    "earnings_review": "PASS",
                    "business_driver_review": "PASS",
                    "valuation_review": "PASS",
                    "loss_rule_review": "PASS",
                    "capital_plan_review": "PASS",
                    "review_notes": "USER_CONFIRMATION_REQUIRED",
                    "proposal_status": "READY_FOR_USER_CONFIRMATION",
                    "approval_required": "YES",
                    "apply_target": "configs/manual_review.actual.csv",
                    "source_action": "DO_NOT_COPY_AUTOMATICALLY",
                }
            ]
        ).to_csv(proposal_csv, index=False)
        actual_config.parent.mkdir(parents=True)
        pd.DataFrame(
            [
                {
                    "symbol": "003550.KS",
                    "filing_review": "PASS",
                    "earnings_review": "PASS",
                    "business_driver_review": "PASS",
                    "valuation_review": "PASS",
                    "loss_rule_review": "PASS",
                    "capital_plan_review": "PASS",
                    "review_notes": "previously confirmed",
                }
            ]
        ).to_csv(actual_config, index=False)

        output = module.run_manual_review_apply_plan(
            manual_review_proposal_csv=proposal_csv,
            output_dir=output_dir,
            actual_output_csv=actual_config,
        )

        plan_row = output.plan.iloc[0]
        assert plan_row["apply_mode"] == "EXISTING_ACTUAL"
        assert plan_row["actual_config_written"] == "YES"
        assert plan_row["blocker"] == ""

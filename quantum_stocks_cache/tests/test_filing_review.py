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


def test_filing_review_passes_only_when_all_required_checks_pass() -> None:
    module = importlib.import_module("quantum_trainer.filing_review")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        input_csv = root / "filing_review.csv"
        output_dir = root / "reports"
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "annual_report_review": "PASS",
                    "quarterly_report_review": "PASS",
                    "litigation_review": "PASS",
                    "contingent_liability_review": "PASS",
                    "related_party_review": "PASS",
                    "project_risk_review": "PASS",
                    "notes": "Latest annual and quarterly filings reviewed.",
                }
            ]
        ).to_csv(input_csv, index=False)

        output = module.run_filing_review(input_csv=input_csv, output_dir=output_dir)

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert output.report.loc[0, "filing_review_status"] == "FILING_REVIEW_PASS"
        assert output.report.loc[0, "recommended_manual_review_value"] == "PASS"
        assert output.report.loc[0, "blocking_checks"] == ""
        assert output.summary["pass_count"] == 1


def test_filing_review_blocks_fail_and_keeps_unknown_unready() -> None:
    module = importlib.import_module("quantum_trainer.filing_review")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        input_csv = root / "filing_review.csv"
        output_dir = root / "reports"
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "annual_report_review": "PASS",
                    "quarterly_report_review": "UNKNOWN",
                    "litigation_review": "PASS",
                    "contingent_liability_review": "PASS",
                    "related_party_review": "PASS",
                    "project_risk_review": "PASS",
                    "notes": "Quarterly filing not reviewed.",
                },
                {
                    "symbol": "005930.KS",
                    "annual_report_review": "PASS",
                    "quarterly_report_review": "PASS",
                    "litigation_review": "FAIL",
                    "contingent_liability_review": "PASS",
                    "related_party_review": "PASS",
                    "project_risk_review": "PASS",
                    "notes": "Material litigation risk not accepted.",
                },
            ]
        ).to_csv(input_csv, index=False)

        output = module.run_filing_review(input_csv=input_csv, output_dir=output_dir)

        unknown = output.report.loc[output.report["symbol"] == "028260.KS"].iloc[0]
        failed = output.report.loc[output.report["symbol"] == "005930.KS"].iloc[0]
        assert unknown["filing_review_status"] == "FILING_REVIEW_UNKNOWN"
        assert unknown["recommended_manual_review_value"] == "UNKNOWN"
        assert "quarterly_report_review" in unknown["blocking_checks"]
        assert failed["filing_review_status"] == "FILING_REVIEW_FAIL"
        assert failed["recommended_manual_review_value"] == "FAIL"
        assert "litigation_review" in failed["blocking_checks"]
        assert output.summary["unknown_count"] == 1
        assert output.summary["fail_count"] == 1


def test_filing_review_validates_required_columns() -> None:
    module = importlib.import_module("quantum_trainer.filing_review")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        input_csv = root / "filing_review.csv"
        pd.DataFrame([{"symbol": "028260.KS"}]).to_csv(input_csv, index=False)

        try:
            module.run_filing_review(input_csv=input_csv, output_dir=root / "reports")
        except ValueError as exc:
            assert "missing required columns" in str(exc)
        else:
            raise AssertionError("Expected required-column validation to fail.")


def test_build_filing_review_input_from_disclosures_prefills_report_existence_only() -> None:
    module = importlib.import_module("quantum_trainer.filing_review")
    disclosures = pd.DataFrame(
        [
            {
                "symbol": "028260.KS",
                "report_nm": "사업보고서 (2025.12)",
                "rcept_dt": "20260320",
                "rcept_no": "20260320000111",
            },
            {
                "symbol": "028260.KS",
                "report_nm": "분기보고서 (2026.03)",
                "rcept_dt": "20260515",
                "rcept_no": "20260515000222",
            },
        ]
    )

    review_input = module.build_filing_review_input_from_disclosures(
        symbol="028260.KS",
        disclosures=disclosures,
    )

    row = review_input.iloc[0]
    assert row["symbol"] == "028260.KS"
    assert row["annual_report_review"] == "PASS"
    assert row["quarterly_report_review"] == "PASS"
    assert row["litigation_review"] == "UNKNOWN"
    assert row["contingent_liability_review"] == "UNKNOWN"
    assert row["related_party_review"] == "UNKNOWN"
    assert row["project_risk_review"] == "UNKNOWN"
    assert "사업보고서" in row["notes"]
    assert "분기보고서" in row["notes"]

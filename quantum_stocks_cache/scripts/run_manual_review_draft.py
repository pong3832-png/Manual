from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.manual_review_draft import run_manual_review_draft

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create manual review draft evidence without editing manual_review.actual.csv."
    )
    parser.add_argument(
        "--investment-memo-csv",
        default=str(PROJECT_ROOT / "reports" / "investment_memo" / "investment_memo.csv"),
        help="Input investment memo CSV.",
    )
    parser.add_argument(
        "--investment-checklist-csv",
        default=str(PROJECT_ROOT / "reports" / "investment_checklist" / "investment_checklist.csv"),
        help="Input investment checklist CSV.",
    )
    parser.add_argument(
        "--company-research-csv",
        default=str(PROJECT_ROOT / "reports" / "company_research" / "company_research.csv"),
        help="Input company research CSV.",
    )
    parser.add_argument(
        "--filing-risk-dir",
        default=str(PROJECT_ROOT / "reports" / "filing_review"),
        help="Directory containing filing_risk_summary_<code>.csv files.",
    )
    parser.add_argument(
        "--capital-plan-dir",
        default=str(PROJECT_ROOT / "reports" / "decision_gate"),
        help="Directory containing capital_plan_review_<code>.csv files.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "reports"),
        help="Output reports root.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        output = run_manual_review_draft(
            investment_memo_csv=Path(args.investment_memo_csv),
            investment_checklist_csv=Path(args.investment_checklist_csv),
            company_research_csv=Path(args.company_research_csv),
            filing_risk_dir=Path(args.filing_risk_dir),
            output_dir=Path(args.output_dir),
            capital_plan_dir=Path(args.capital_plan_dir),
        )
        logger.info("Manual review draft complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        if output.report.empty:
            print("row_count=0")
        else:
            print(
                output.report.loc[
                    :,
                    [
                        "symbol",
                        "filing_review",
                        "earnings_review",
                        "business_driver_review",
                        "valuation_review",
                        "loss_rule_review",
                        "capital_plan_review",
                    ],
                ].to_string(index=False)
            )
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Manual review draft failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

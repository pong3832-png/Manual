from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.capital_plan_review import run_capital_plan_review

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a rule-first capital plan review without assuming capital or placing orders."
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
        "--output-dir",
        default=str(PROJECT_ROOT / "reports"),
        help="Output reports root.",
    )
    parser.add_argument(
        "--total-capital-krw",
        type=float,
        default=None,
        help="Optional total capital for review status. Does not place orders.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        output = run_capital_plan_review(
            investment_memo_csv=Path(args.investment_memo_csv),
            investment_checklist_csv=Path(args.investment_checklist_csv),
            company_research_csv=Path(args.company_research_csv),
            output_dir=Path(args.output_dir),
            total_capital=args.total_capital_krw,
        )
        logger.info("Capital plan review complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        if output.report.empty:
            print("row_count=0")
        else:
            print(
                output.report.loc[
                    :, ["symbol", "capital_plan_review", "amount_status", "order_status"]
                ].to_string(index=False)
            )
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Capital plan review failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

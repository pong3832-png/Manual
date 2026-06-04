from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.valuation_data_quality import run_valuation_data_quality

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit local valuation evidence without fetching external data."
    )
    parser.add_argument(
        "--company-research-csv",
        default=str(PROJECT_ROOT / "reports" / "company_research" / "company_research.csv"),
        help="Input company research CSV.",
    )
    parser.add_argument(
        "--investment-memo-csv",
        default=str(PROJECT_ROOT / "reports" / "investment_memo" / "investment_memo.csv"),
        help="Input investment memo CSV.",
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
        output = run_valuation_data_quality(
            company_research_csv=Path(args.company_research_csv),
            investment_memo_csv=Path(args.investment_memo_csv),
            output_dir=Path(args.output_dir),
        )
        logger.info("Valuation data quality complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(f"row_count={output.summary['row_count']}")
        print(f"fallback_count={output.summary['fallback_count']}")
        print(f"missing_count={output.summary['missing_count']}")
        print("external_api_requested=NO")
        print("order_status=NO_ORDER")
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Valuation data quality failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

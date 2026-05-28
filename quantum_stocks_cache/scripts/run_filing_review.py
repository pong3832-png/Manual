from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.filing_review import run_filing_review

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a local filing review report for the manual decision gate."
    )
    parser.add_argument(
        "--input-csv",
        default=str(PROJECT_ROOT / "configs" / "filing_review.example.csv"),
        help="Input filing review CSV with PASS/FAIL/UNKNOWN checks.",
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
        output = run_filing_review(input_csv=Path(args.input_csv), output_dir=Path(args.output_dir))
        logger.info("Filing review complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        if output.report.empty:
            print("row_count=0")
        else:
            print(
                output.report.loc[
                    :, ["symbol", "filing_review_status", "recommended_manual_review_value", "blocking_checks"]
                ].to_string(index=False)
            )
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Filing review failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

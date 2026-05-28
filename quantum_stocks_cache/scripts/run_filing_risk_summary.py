from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.filing_risk_summary import run_filing_risk_summary

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compress an existing OpenDART text risk scan into five core filing risks."
    )
    parser.add_argument(
        "--scan-csv",
        required=True,
        help="Existing reports/filing_review/opendart_text_risk_scan_<code>.csv file.",
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
        output = run_filing_risk_summary(scan_csv=Path(args.scan_csv), output_dir=Path(args.output_dir))
        logger.info("Filing risk summary complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(f"overall_opinion={output.summary['overall_opinion']}")
        print(f"fatal_risk_count={output.summary['fatal_risk_count']}")
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Filing risk summary failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

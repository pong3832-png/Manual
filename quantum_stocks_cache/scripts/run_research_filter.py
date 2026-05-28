from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.research_filter import run_research_filter

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a human review filter from the company research report."
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
        "--top-n",
        type=int,
        default=5,
        help="Number of top ranked companies to include.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        output = run_research_filter(
            company_research_csv=Path(args.company_research_csv),
            output_dir=Path(args.output_dir),
            top_n=args.top_n,
        )
        logger.info("Research filter complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(
            output.report.loc[
                :, ["symbol", "research_score", "filter_status", "decision", "fundamental_view"]
            ].to_string(index=False)
        )
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Research filter failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

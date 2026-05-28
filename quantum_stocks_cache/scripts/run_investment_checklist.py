from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.investment_checklist import run_investment_checklist

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a pre-investment manual checklist from candidate briefs."
    )
    parser.add_argument(
        "--candidate-briefs-csv",
        default=str(PROJECT_ROOT / "reports" / "candidate_briefs" / "candidate_briefs.csv"),
        help="Input candidate briefs CSV.",
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
        output = run_investment_checklist(
            candidate_briefs_csv=Path(args.candidate_briefs_csv),
            output_dir=Path(args.output_dir),
        )
        logger.info("Investment checklist complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(
            output.report.loc[
                :, ["symbol", "company_name", "checklist_status", "automatic_blockers"]
            ].to_string(index=False)
        )
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Investment checklist failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

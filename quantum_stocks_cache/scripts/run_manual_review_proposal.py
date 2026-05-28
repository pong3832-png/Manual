from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.manual_review_proposal import run_manual_review_proposal

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a user-confirmation manual review proposal without editing actual config."
    )
    parser.add_argument(
        "--manual-review-draft-csv",
        default=str(PROJECT_ROOT / "reports" / "decision_gate" / "manual_review_draft.csv"),
        help="Input manual review draft CSV.",
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
        output = run_manual_review_proposal(
            manual_review_draft_csv=Path(args.manual_review_draft_csv),
            output_dir=Path(args.output_dir),
        )
        logger.info("Manual review proposal complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print("actual_config_written=NO")
        if output.report.empty:
            print("row_count=0")
        else:
            print(
                output.report.loc[
                    :, ["symbol", "proposal_status", "approval_required", "apply_target"]
                ].to_string(index=False)
            )
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Manual review proposal failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

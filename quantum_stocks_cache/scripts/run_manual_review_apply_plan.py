from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.manual_review_apply_plan import CONFIRM_TOKEN, run_manual_review_apply_plan

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or explicitly confirm a manual-review actual config apply plan."
    )
    parser.add_argument(
        "--manual-proposal-csv",
        default=str(PROJECT_ROOT / "reports" / "decision_gate" / "manual_review_proposal.csv"),
        help="Input manual review proposal CSV.",
    )
    parser.add_argument(
        "--actual-output-csv",
        default=str(PROJECT_ROOT / "configs" / "manual_review.actual.csv"),
        help="Actual manual review CSV target. Written only with the exact confirmation token.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "reports"),
        help="Output reports root.",
    )
    parser.add_argument(
        "--confirm-final-review",
        default="",
        help=f"Write actual config only when this exactly equals {CONFIRM_TOKEN}.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        output = run_manual_review_apply_plan(
            manual_review_proposal_csv=Path(args.manual_proposal_csv),
            output_dir=Path(args.output_dir),
            actual_output_csv=Path(args.actual_output_csv),
            confirm_token=args.confirm_final_review or None,
        )
        logger.info("Manual review apply plan complete.")
        logger.info("Plan CSV: %s", output.plan_csv_path)
        logger.info("Candidate CSV: %s", output.candidate_csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"plan_csv={output.plan_csv_path}")
        print(f"candidate_csv={output.candidate_csv_path}")
        print(f"markdown_report={output.markdown_path}")
        if output.plan.empty:
            print("row_count=0")
        else:
            print(output.plan.to_string(index=False))
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Manual review apply plan failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

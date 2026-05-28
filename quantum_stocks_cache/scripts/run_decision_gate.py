from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.decision_gate import run_decision_gate

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gate investment memos with manual evidence before sizing review."
    )
    parser.add_argument(
        "--investment-memo-csv",
        default=str(PROJECT_ROOT / "reports" / "investment_memo" / "investment_memo.csv"),
        help="Input investment memo CSV.",
    )
    parser.add_argument(
        "--manual-review-csv",
        default=None,
        help="Optional manual review CSV with PASS/FAIL/UNKNOWN fields.",
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
        output = run_decision_gate(
            investment_memo_csv=Path(args.investment_memo_csv),
            output_dir=Path(args.output_dir),
            manual_review_csv=Path(args.manual_review_csv) if args.manual_review_csv else None,
        )
        logger.info("Decision gate complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        logger.info("Manual review template: %s", output.template_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(f"manual_review_template={output.template_path}")
        if output.report.empty:
            print("row_count=0")
        else:
            print(
                output.report.loc[
                    :, ["symbol", "decision_gate_status", "order_status", "gate_reason"]
                ].to_string(index=False)
            )
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Decision gate failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

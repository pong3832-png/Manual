from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.investment_tracking import run_investment_tracking

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Track post-buy thesis and performance without placing orders.")
    parser.add_argument(
        "--trade-journal-csv",
        default=str(PROJECT_ROOT / "configs" / "trade_journal.actual.csv"),
        help="Manual trade journal CSV. If missing, a not-started tracking report is written.",
    )
    parser.add_argument(
        "--prices-csv",
        default=str(PROJECT_ROOT / "data" / "prices.csv"),
        help="Input cached prices CSV.",
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
        output = run_investment_tracking(
            trade_journal_csv=Path(args.trade_journal_csv),
            prices_csv=Path(args.prices_csv),
            output_dir=Path(args.output_dir),
        )
        logger.info("Investment tracking complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(f"tracked_positions={output.summary['tracked_positions']}")
        print(f"review_due_count={output.summary['review_due_count']}")
        print(f"order_status={output.summary['order_status']}")
        return 0
    except Exception as exc:
        logger.exception("Investment tracking failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.order_sizer import run_order_sizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create manual-review order candidates from investment checklist and latest prices."
    )
    parser.add_argument(
        "--candidate-checklist-csv",
        default=str(PROJECT_ROOT / "reports" / "investment_checklist" / "investment_checklist.csv"),
        help="Input investment checklist CSV.",
    )
    parser.add_argument(
        "--prices-csv",
        default=str(PROJECT_ROOT / "data" / "prices.csv"),
        help="Input price CSV with date column and symbol columns.",
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
        help="Total capital to size candidates against. Omit to produce BLOCKED_CAPITAL_REQUIRED candidates.",
    )
    parser.add_argument(
        "--max-position-weight",
        type=float,
        default=0.20,
        help="Maximum target weight per candidate.",
    )
    parser.add_argument(
        "--cash-buffer-weight",
        type=float,
        default=0.10,
        help="Cash buffer weight to keep unallocated.",
    )
    parser.add_argument(
        "--include-status",
        action="append",
        default=None,
        help="Checklist status to include. Can be repeated. Defaults to READY_FOR_MANUAL_REVIEW.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        include_statuses = tuple(args.include_status) if args.include_status else ("READY_FOR_MANUAL_REVIEW",)
        output = run_order_sizer(
            candidate_checklist_csv=Path(args.candidate_checklist_csv),
            prices_csv=Path(args.prices_csv),
            output_dir=Path(args.output_dir),
            total_capital=args.total_capital_krw,
            max_position_weight=args.max_position_weight,
            cash_buffer_weight=args.cash_buffer_weight,
            include_statuses=include_statuses,
        )
        logger.info("Order sizing complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(
            output.report.loc[
                :, ["symbol", "company_name", "order_status", "candidate_shares", "estimated_order_value"]
            ].to_string(index=False)
        )
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Order sizing failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

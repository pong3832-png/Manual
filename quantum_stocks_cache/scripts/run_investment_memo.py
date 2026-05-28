from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.investment_memo import run_investment_memo

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Turn CORE_FOCUS names into no-order investment thesis memos."
    )
    parser.add_argument(
        "--profit-focus-csv",
        default=str(PROJECT_ROOT / "reports" / "profit_focus" / "profit_focus.csv"),
        help="Input profit focus CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "reports"),
        help="Output reports root.",
    )
    parser.add_argument(
        "--max-memos",
        type=int,
        default=1,
        help="Maximum number of CORE_FOCUS memos.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        output = run_investment_memo(
            profit_focus_csv=Path(args.profit_focus_csv),
            output_dir=Path(args.output_dir),
            max_memos=args.max_memos,
        )
        logger.info("Investment memo complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        if output.report.empty:
            print("memo_count=0")
        else:
            print(output.report.loc[:, ["symbol", "memo_status", "order_status"]].to_string(index=False))
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Investment memo failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.market_watch import run_market_watch

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a local market watch report from company research output."
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
        "--previous-watch-csv",
        default=None,
        help="Optional previous market watch CSV. Defaults to existing output file if present.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=15,
        help="Number of watch rows to include.",
    )
    parser.add_argument(
        "--as-of",
        default=None,
        help="Optional snapshot date label for market_watch_history.csv.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        output = run_market_watch(
            company_research_csv=Path(args.company_research_csv),
            output_dir=Path(args.output_dir),
            previous_watch_csv=Path(args.previous_watch_csv) if args.previous_watch_csv else None,
            top_n=args.top_n,
            as_of=args.as_of,
        )
        logger.info("Market watch complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        logger.info("History report: %s", output.history_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(f"history_report={output.history_path}")
        print(output.report.loc[:, ["symbol", "watch_status", "watch_event", "research_score"]].to_string(index=False))
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Market watch failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

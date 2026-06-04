from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.trend_forecast import run_trend_forecast

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a local-only trend forecast report from cached prices."
    )
    parser.add_argument(
        "--prices-csv",
        default=str(PROJECT_ROOT / "data" / "prices.csv"),
        help="Wide-format cached prices CSV.",
    )
    parser.add_argument(
        "--company-research-csv",
        default=str(PROJECT_ROOT / "reports" / "company_research" / "company_research.csv"),
        help="Company research CSV used for symbol names and research scores.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "reports"),
        help="Output reports root.",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=60,
        help="Minimum non-empty price samples required for trend classification.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        output = run_trend_forecast(
            prices_csv=Path(args.prices_csv),
            company_research_csv=Path(args.company_research_csv),
            output_dir=Path(args.output_dir),
            min_samples=args.min_samples,
        )
        logger.info("Trend forecast complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(f"row_count={output.summary['row_count']}")
        print(f"bullish_count={output.summary['bullish_count']}")
        print(f"watch_pullback_count={output.summary['watch_pullback_count']}")
        print(f"bearish_count={output.summary['bearish_count']}")
        print(f"insufficient_count={output.summary['insufficient_count']}")
        print("external_api_requested=NO")
        print("order_status=NO_ORDER")
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Trend forecast failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

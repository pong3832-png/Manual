from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.universe_coverage import run_universe_coverage

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check whether the local research universe is broad enough and price-covered."
    )
    parser.add_argument(
        "--universe-csv",
        default=str(PROJECT_ROOT / "configs" / "research_universe.actual.csv"),
        help="Active research universe CSV.",
    )
    parser.add_argument(
        "--prices-csv",
        default=str(PROJECT_ROOT / "data" / "prices.csv"),
        help="Cached prices CSV. Missing coverage is reported, not fetched.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "reports"),
        help="Output reports root.",
    )
    parser.add_argument("--min-count", type=int, default=20, help="Minimum target universe count.")
    parser.add_argument("--max-count", type=int, default=50, help="Maximum target universe count.")
    parser.add_argument(
        "--required-symbols",
        default=None,
        help="Optional comma/semicolon separated required symbols.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        required_symbols = _split_symbols(args.required_symbols) if args.required_symbols else None
        output = run_universe_coverage(
            universe_csv=Path(args.universe_csv),
            prices_csv=Path(args.prices_csv),
            output_dir=Path(args.output_dir),
            min_count=args.min_count,
            max_count=args.max_count,
            required_symbols=required_symbols,
        )
        logger.info("Universe coverage complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        row = output.report.iloc[0]
        print(f"universe_status={row['universe_status']}")
        print(f"universe_count={row['universe_count']}")
        print(f"price_coverage_status={row['price_coverage_status']}")
        print(f"required_missing_count={row['required_missing_count']}")
        print("external_api_requested=NO")
        print("order_status=NO_ORDER")
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Universe coverage failed: %s", exc)
        return 1


def _split_symbols(value: str) -> list[str]:
    return [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]


if __name__ == "__main__":
    raise SystemExit(main())

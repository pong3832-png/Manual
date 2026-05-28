from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.research_universe import add_research_symbol

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add or update one company in the local research universe CSV."
    )
    parser.add_argument(
        "--universe-csv",
        default=str(PROJECT_ROOT / "configs" / "research_universe.actual.csv"),
        help="Existing normalized research universe CSV.",
    )
    parser.add_argument(
        "--output-csv",
        default=None,
        help="Output CSV. Defaults to --universe-csv for in-place local update.",
    )
    parser.add_argument("--code", default=None, help="Six-digit KRX code, for example 006800.")
    parser.add_argument("--symbol", default=None, help="Full symbol, for example 006800.KS.")
    parser.add_argument("--company-name", required=True, help="Company name to store.")
    parser.add_argument("--market", default="KOSPI", help="KOSPI/KOSDAQ/KQ/KS. Defaults to KOSPI.")
    parser.add_argument("--sector", default="UNKNOWN", help="Sector label.")
    parser.add_argument("--replace", action="store_true", help="Update an existing symbol row instead of leaving it unchanged.")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        universe_csv = Path(args.universe_csv)
        output_csv = Path(args.output_csv) if args.output_csv else universe_csv
        result = add_research_symbol(
            universe_csv=universe_csv,
            output_csv=output_csv,
            code=args.code,
            symbol=args.symbol,
            company_name=args.company_name,
            market=args.market,
            sector=args.sector,
            replace=args.replace,
        )
        logger.info("Research symbol update complete.")
        logger.info("Output CSV: %s", result.output_csv)
        print(f"output_csv={result.output_csv}")
        print(f"symbol={result.symbol}")
        print(f"action={result.action}")
        print(f"row_count={result.row_count}")
        print("external_api_requested=NO")
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Research symbol update failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

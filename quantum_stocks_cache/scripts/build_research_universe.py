from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.research_universe import merge_research_universe

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize a research universe seed CSV for company research."
    )
    parser.add_argument(
        "--source-csv",
        action="append",
        required=True,
        help="CSV with symbol or code. Optional columns: company_name,market,sector.",
    )
    parser.add_argument(
        "--output-csv",
        default=str(PROJECT_ROOT / "configs" / "research_universe.actual.csv"),
        help="Output normalized research universe CSV.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of unique symbols to keep after merging.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        result = merge_research_universe(
            source_csvs=[Path(source_csv) for source_csv in args.source_csv],
            output_csv=Path(args.output_csv),
            limit=args.limit,
        )
        logger.info("Research universe created: %s", result.output_csv)
        logger.info("Rows: %s", result.row_count)
        print(f"output_csv={result.output_csv}")
        print(f"row_count={result.row_count}")
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Research universe build failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

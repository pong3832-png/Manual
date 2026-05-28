from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.opendart_client import (
    fetch_fundamentals_for_universe,
    load_opendart_api_key,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch OpenDART fundamentals for a research universe."
    )
    parser.add_argument(
        "--universe-csv",
        default=str(PROJECT_ROOT / "configs" / "research_universe.actual.csv"),
        help="Universe CSV with a symbol column.",
    )
    parser.add_argument(
        "--output-csv",
        default=str(PROJECT_ROOT / "configs" / "fundamentals.actual.csv"),
        help="Output fundamentals CSV.",
    )
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Business year, for example 2025.",
    )
    parser.add_argument(
        "--report-code",
        default="11011",
        help="OpenDART report code. 11011 is annual report.",
    )
    parser.add_argument(
        "--fs-div",
        default="CFS",
        choices=["CFS", "OFS"],
        help="Financial statement division: CFS consolidated, OFS separate.",
    )
    parser.add_argument(
        "--env",
        default=str(PROJECT_ROOT / ".env"),
        help="Path to local .env file containing OPENDART_API_KEY.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        api_key = load_opendart_api_key(args.env)
        fundamentals = fetch_fundamentals_for_universe(
            universe_csv=Path(args.universe_csv),
            api_key=api_key,
            business_year=args.year,
            report_code=args.report_code,
            fs_div=args.fs_div,
        )
        output_path = Path(args.output_csv).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fundamentals.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info("OpenDART fundamentals written: %s", output_path)
        logger.info("Rows: %s", len(fundamentals))
        print(f"output_csv={output_path}")
        print(f"row_count={len(fundamentals)}")
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("OpenDART fundamentals fetch failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

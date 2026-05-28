from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.opendart_client import load_opendart_api_key
from quantum_trainer.opendart_filing_review import fetch_opendart_filing_review

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    today = date.today()
    parser = argparse.ArgumentParser(
        description="Fetch OpenDART disclosure list metadata and create a filing review draft."
    )
    parser.add_argument(
        "--symbol",
        default="028260.KS",
        help="Ticker symbol to fetch, for example 028260.KS.",
    )
    parser.add_argument(
        "--begin-date",
        default=f"{today.year}0101",
        help="OpenDART start date in YYYYMMDD.",
    )
    parser.add_argument(
        "--end-date",
        default=today.strftime("%Y%m%d"),
        help="OpenDART end date in YYYYMMDD.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "reports"),
        help="Output reports root.",
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
        output = fetch_opendart_filing_review(
            symbol=args.symbol,
            api_key=api_key,
            begin_date=args.begin_date,
            end_date=args.end_date,
            output_dir=Path(args.output_dir),
        )
        logger.info("OpenDART filing review draft complete.")
        logger.info("Disclosures CSV: %s", output.disclosures_csv_path)
        logger.info("Review input CSV: %s", output.review_input_csv_path)
        logger.info("Markdown draft: %s", output.markdown_path)
        print(f"disclosures_csv={output.disclosures_csv_path}")
        print(f"review_input_csv={output.review_input_csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(f"disclosure_count={output.summary['disclosure_count']}")
        print(output.review_input.to_string(index=False))
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("OpenDART filing review fetch failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

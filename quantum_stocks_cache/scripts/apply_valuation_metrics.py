from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.fundamentals import apply_valuation_metrics
from quantum_trainer.io import load_price_csv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply market-cap based PER/PBR to fundamentals CSV."
    )
    parser.add_argument(
        "--fundamentals-csv",
        default=str(PROJECT_ROOT / "configs" / "fundamentals.actual.csv"),
        help="Input fundamentals CSV with net_income and equity.",
    )
    parser.add_argument(
        "--prices-csv",
        default=str(PROJECT_ROOT / "data" / "prices.csv"),
        help="Price cache CSV.",
    )
    parser.add_argument(
        "--shares-csv",
        default=str(PROJECT_ROOT / "configs" / "shares_outstanding.actual.csv"),
        help="CSV with symbol,shares_outstanding.",
    )
    parser.add_argument(
        "--output-csv",
        default=str(PROJECT_ROOT / "configs" / "fundamentals.actual.csv"),
        help="Output fundamentals CSV. Defaults to overwrite fundamentals.actual.csv.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        fundamentals = pd.read_csv(Path(args.fundamentals_csv))
        prices = load_price_csv(Path(args.prices_csv))
        shares = pd.read_csv(Path(args.shares_csv))
        enriched = apply_valuation_metrics(fundamentals, prices, shares)
        output_path = Path(args.output_csv).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        enriched.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info("Valuation metrics written: %s", output_path)
        print(f"output_csv={output_path}")
        print(enriched.loc[:, ["symbol", "market_cap", "per", "pbr"]].to_string(index=False))
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Valuation metric application failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

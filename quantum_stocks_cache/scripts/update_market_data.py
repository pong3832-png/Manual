from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.config import load_runtime_config
from quantum_trainer.market_data import (
    fetch_market_prices_batched_async,
    resolve_market_data_symbols,
    write_price_cache,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    try:
        parser = argparse.ArgumentParser(description="Update cached listed-stock market prices.")
        parser.add_argument(
            "--config",
            default=str(PROJECT_ROOT / "configs" / "portfolio.yaml"),
            help="Path to portfolio YAML config.",
        )
        parser.add_argument(
            "--universe-csv",
            help="Optional research universe CSV. When provided, update prices for its symbols.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=200,
            help="Number of symbols per market-data request. Use a smaller value for full KRX universes.",
        )
        parser.add_argument(
            "--allow-partial",
            action="store_true",
            help="For large universes, keep symbols with valid prices and skip symbols unavailable from provider.",
        )
        return parser.parse_args()
    except Exception as exc:
        logger.exception("Argument parsing failed: %s", exc)
        raise


async def main_async() -> int:
    try:
        args = parse_args()
        runtime_config = load_runtime_config(Path(args.config))
        symbols = resolve_market_data_symbols(
            portfolio_symbols=list(runtime_config.backtest.weights.keys()),
            universe_csv=Path(args.universe_csv) if args.universe_csv else None,
        )
        prices = await fetch_market_prices_batched_async(
            symbols=symbols,
            config=runtime_config.market_data,
            batch_size=args.batch_size,
            allow_partial=args.allow_partial,
        )
        missing_symbols = [symbol for symbol in symbols if symbol not in prices.columns]
        output_path = write_price_cache(prices, runtime_config.prices_csv)
        logger.info("Market data cache updated: %s", output_path)
        logger.info("Rows=%s Columns=%s LastDate=%s", len(prices), list(prices.columns), prices.index[-1].date())
        if missing_symbols:
            logger.warning("Missing symbols skipped=%s", len(missing_symbols))
        return 0
    except Exception as exc:
        logger.exception("Market data update failed: %s", exc)
        return 1


def main() -> int:
    try:
        return asyncio.run(main_async())
    except Exception as exc:
        logger.exception("Market data update failed before event loop completion: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

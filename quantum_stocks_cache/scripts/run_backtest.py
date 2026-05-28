from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.config import load_runtime_config
from quantum_trainer.io import load_price_csv, save_backtest_reports
from quantum_trainer.trend import run_dynamic_trend_backtest

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    try:
        parser = argparse.ArgumentParser(description="Run Dynamic Trend Following backtest.")
        parser.add_argument(
            "--config",
            default=str(PROJECT_ROOT / "configs" / "portfolio.yaml"),
            help="Path to portfolio YAML config.",
        )
        return parser.parse_args()
    except Exception as exc:
        logger.exception("Argument parsing failed: %s", exc)
        raise


def main() -> int:
    try:
        args = parse_args()
        runtime_config = load_runtime_config(Path(args.config))
        prices = load_price_csv(runtime_config.prices_csv)
        result = run_dynamic_trend_backtest(prices, runtime_config.backtest)
        report_paths = save_backtest_reports(result, runtime_config.reports_dir)

        logger.info("Backtest complete.")
        logger.info("Reports written:")
        for name, path in report_paths.items():
            logger.info("  %s=%s", name, path)

        print(result.performance_summary.to_string(float_format=lambda value: f"{value:.6f}"))
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Backtest failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

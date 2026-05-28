from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.institutional_trainer import run_institutional_trainer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    try:
        parser = argparse.ArgumentParser(description="Run institutional quant control plane.")
        parser.add_argument(
            "--config",
            default=str(PROJECT_ROOT / "configs" / "portfolio.yaml"),
            help="Path to portfolio YAML config.",
        )
        parser.add_argument(
            "--skip-market-data-update",
            action="store_true",
            help="Use existing data/prices.csv without calling the market data provider.",
        )
        return parser.parse_args()
    except Exception as exc:
        logger.exception("Argument parsing failed: %s", exc)
        raise


def main() -> int:
    try:
        args = parse_args()
        output = run_institutional_trainer(
            config_path=Path(args.config),
            update_market_data=not args.skip_market_data_update,
        )
        logger.info("Institutional trainer complete.")
        logger.info("Run ID: %s", output.run_id)
        logger.info("Run dir: %s", output.run_dir)
        logger.info("IC report: %s", output.ic_report_path)
        return 0
    except Exception as exc:
        logger.exception("Institutional trainer failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

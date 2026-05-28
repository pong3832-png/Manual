from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.trainer import run_daily_trainer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    try:
        parser = argparse.ArgumentParser(description="Run daily AI Quant Trainer.")
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
        output = run_daily_trainer(config_path=Path(args.config))
        logger.info("Daily trainer complete.")
        logger.info("Trade plan: %s", output.trade_plan_path)
        logger.info("Decision report: %s", output.decision_report_path)
        print(output.trade_plan.to_string())
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Daily trainer failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

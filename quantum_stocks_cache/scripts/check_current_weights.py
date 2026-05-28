from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.portfolio_state import check_current_weights

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare actual current weights CSV with config current_weights."
    )
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "configs" / "portfolio.yaml"),
        help="Path to portfolio YAML config.",
    )
    parser.add_argument(
        "--current-weights-csv",
        required=True,
        help="CSV with columns: symbol,current_weight.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.01,
        help="Absolute difference threshold that marks a row as WARN.",
    )
    parser.add_argument(
        "--reports-dir",
        help="Optional reports directory override. Defaults to reports.output_dir from config.",
    )
    parser.add_argument(
        "--write-config",
        action="store_true",
        help="Overwrite only the current_weights section in the YAML config. Default is dry-run.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        result = check_current_weights(
            config_path=Path(args.config),
            current_weights_csv=Path(args.current_weights_csv),
            threshold=args.threshold,
            reports_dir=Path(args.reports_dir) if args.reports_dir else None,
            write_config=args.write_config,
        )
        logger.info("Current weights check status: %s", result.status)
        logger.info("CSV report: %s", result.csv_path)
        logger.info("Markdown report: %s", result.markdown_path)
        if result.config_updated:
            logger.warning("Config current_weights was updated by explicit --write-config.")
        elif result.status == "WARN":
            logger.warning("Config current_weights differs from CSV by threshold or more.")
        print(f"status={result.status}")
        print(f"csv_report={result.csv_path}")
        print(f"markdown_report={result.markdown_path}")
        print(f"config_updated={result.config_updated}")
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Current weights check failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

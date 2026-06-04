from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.market_regime import run_market_regime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a local market and sector regime report from trend_forecast.csv."
    )
    parser.add_argument(
        "--trend-forecast-csv",
        default=str(PROJECT_ROOT / "reports" / "trend_forecast" / "trend_forecast.csv"),
        help="Input trend forecast CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "reports"),
        help="Output reports root.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        output = run_market_regime(
            trend_forecast_csv=Path(args.trend_forecast_csv),
            output_dir=Path(args.output_dir),
        )
        logger.info("Market regime complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(f"row_count={output.summary['row_count']}")
        print(f"risk_on_count={output.summary['risk_on_count']}")
        print(f"extended_uptrend_count={output.summary['extended_uptrend_count']}")
        print(f"risk_off_count={output.summary['risk_off_count']}")
        print("external_api_requested=NO")
        print("order_status=NO_ORDER")
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Market regime failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

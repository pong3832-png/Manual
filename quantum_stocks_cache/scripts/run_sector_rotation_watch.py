from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.sector_rotation_watch import run_sector_rotation_watch

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a local sector rotation watch report without placing orders.")
    parser.add_argument(
        "--market-recovery-watch-csv",
        default=str(PROJECT_ROOT / "reports" / "market_recovery_watch" / "market_recovery_watch.csv"),
        help="Input market recovery watch CSV.",
    )
    parser.add_argument(
        "--trend-forecast-csv",
        default=str(PROJECT_ROOT / "reports" / "trend_forecast" / "trend_forecast.csv"),
        help="Input trend forecast CSV.",
    )
    parser.add_argument(
        "--top-candidates-per-sector",
        type=int,
        default=3,
        help="Maximum candidate labels to show for each sector.",
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
        output = run_sector_rotation_watch(
            market_recovery_watch_csv=Path(args.market_recovery_watch_csv),
            trend_forecast_csv=Path(args.trend_forecast_csv),
            output_dir=Path(args.output_dir),
            top_candidates_per_sector=args.top_candidates_per_sector,
        )
        logger.info("Sector rotation watch complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(f"row_count={output.summary['row_count']}")
        print(f"leader_count={output.summary['leader_count']}")
        print(f"early_rotation_count={output.summary['early_rotation_count']}")
        print(f"defensive_wait_count={output.summary['defensive_wait_count']}")
        print("external_api_requested=NO")
        print("order_status=NO_ORDER")
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Sector rotation watch failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

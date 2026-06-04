from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.event_adjusted_ranking import run_event_adjusted_ranking

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a local final watch ranking from quant scores and event catalysts."
    )
    parser.add_argument(
        "--universe-csv",
        default=str(PROJECT_ROOT / "reports" / "universe_stock_analysis" / "universe_stock_analysis.csv"),
        help="Universe stock analysis CSV.",
    )
    parser.add_argument(
        "--event-csv",
        default=str(PROJECT_ROOT / "reports" / "event_catalysts" / "event_catalysts.csv"),
        help="Event catalysts CSV.",
    )
    parser.add_argument(
        "--trend-forecast-csv",
        default=str(PROJECT_ROOT / "reports" / "trend_forecast" / "trend_forecast.csv"),
        help="Optional local trend forecast CSV used to block high chase-risk entries.",
    )
    parser.add_argument(
        "--market-regime-csv",
        default=str(PROJECT_ROOT / "reports" / "market_regime" / "market_regime.csv"),
        help="Optional local market/sector regime CSV used to block broad-risk entries.",
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
        output = run_event_adjusted_ranking(
            universe_csv=Path(args.universe_csv),
            event_csv=Path(args.event_csv),
            trend_forecast_csv=Path(args.trend_forecast_csv),
            market_regime_csv=Path(args.market_regime_csv),
            output_dir=Path(args.output_dir),
        )
        logger.info("Event adjusted ranking complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(f"row_count={output.summary['row_count']}")
        print(f"ready_count={output.summary['ready_count']}")
        print(f"pullback_count={output.summary['pullback_count']}")
        print(f"market_wait_count={output.summary['market_wait_count']}")
        print(f"external_api_requested={output.summary['external_api_requested']}")
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Event adjusted ranking failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

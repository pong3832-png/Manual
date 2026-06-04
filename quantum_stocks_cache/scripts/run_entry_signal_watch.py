from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.entry_signal_watch import run_entry_signal_watch

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a local entry trigger watch report without placing orders.")
    parser.add_argument(
        "--event-adjusted-ranking-csv",
        default=str(PROJECT_ROOT / "reports" / "event_adjusted_ranking" / "event_adjusted_ranking.csv"),
        help="Input event-adjusted ranking CSV.",
    )
    parser.add_argument(
        "--pre-buy-decision-csv",
        default=str(PROJECT_ROOT / "reports" / "pre_buy_decision" / "pre_buy_decision.csv"),
        help="Input pre-buy decision CSV.",
    )
    parser.add_argument(
        "--trend-forecast-csv",
        default=str(PROJECT_ROOT / "reports" / "trend_forecast" / "trend_forecast.csv"),
        help="Input trend forecast CSV.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=30,
        help="Maximum ranked candidates to include.",
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
        output = run_entry_signal_watch(
            event_adjusted_ranking_csv=Path(args.event_adjusted_ranking_csv),
            pre_buy_decision_csv=Path(args.pre_buy_decision_csv),
            trend_forecast_csv=Path(args.trend_forecast_csv),
            output_dir=Path(args.output_dir),
            top_n=args.top_n,
        )
        logger.info("Entry signal watch complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(f"row_count={output.summary['row_count']}")
        print(f"market_wait_count={output.summary['market_wait_count']}")
        print(f"pullback_wait_count={output.summary['pullback_wait_count']}")
        print(f"event_only_count={output.summary['event_only_count']}")
        print("external_api_requested=NO")
        print("order_status=NO_ORDER")
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Entry signal watch failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

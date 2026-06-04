from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.tactical_watchlist import run_tactical_watchlist

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a local tactical watchlist without placing orders.")
    parser.add_argument(
        "--event-adjusted-ranking-csv",
        default=str(PROJECT_ROOT / "reports" / "event_adjusted_ranking" / "event_adjusted_ranking.csv"),
        help="Input event-adjusted ranking CSV.",
    )
    parser.add_argument(
        "--entry-signal-watch-csv",
        default=str(PROJECT_ROOT / "reports" / "entry_signal_watch" / "entry_signal_watch.csv"),
        help="Input entry signal watch CSV.",
    )
    parser.add_argument(
        "--sector-rotation-watch-csv",
        default=str(PROJECT_ROOT / "reports" / "sector_rotation_watch" / "sector_rotation_watch.csv"),
        help="Input sector rotation watch CSV.",
    )
    parser.add_argument("--top-n", type=int, default=30, help="Maximum event-ranking rows to include.")
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "reports"),
        help="Output reports root.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        output = run_tactical_watchlist(
            event_adjusted_ranking_csv=Path(args.event_adjusted_ranking_csv),
            entry_signal_watch_csv=Path(args.entry_signal_watch_csv),
            sector_rotation_watch_csv=Path(args.sector_rotation_watch_csv),
            output_dir=Path(args.output_dir),
            top_n=args.top_n,
        )
        logger.info("Tactical watchlist complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(f"row_count={output.summary['row_count']}")
        print(f"ready_manual_review_count={output.summary['ready_manual_review_count']}")
        print(f"sector_recovery_watch_count={output.summary['sector_recovery_watch_count']}")
        print(f"pullback_watch_count={output.summary['pullback_watch_count']}")
        print(f"market_defensive_wait_count={output.summary['market_defensive_wait_count']}")
        print(f"overheated_wait_count={output.summary['overheated_wait_count']}")
        print("external_api_requested=NO")
        print("order_status=NO_ORDER")
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Tactical watchlist failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

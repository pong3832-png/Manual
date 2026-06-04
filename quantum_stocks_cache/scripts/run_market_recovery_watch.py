from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.market_recovery_watch import run_market_recovery_watch

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a local market recovery trigger report without placing orders.")
    parser.add_argument(
        "--market-regime-csv",
        default=str(PROJECT_ROOT / "reports" / "market_regime" / "market_regime.csv"),
        help="Input market regime CSV.",
    )
    parser.add_argument(
        "--entry-signal-watch-csv",
        default=str(PROJECT_ROOT / "reports" / "entry_signal_watch" / "entry_signal_watch.csv"),
        help="Input entry signal watch CSV.",
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
        output = run_market_recovery_watch(
            market_regime_csv=Path(args.market_regime_csv),
            entry_signal_watch_csv=Path(args.entry_signal_watch_csv),
            output_dir=Path(args.output_dir),
        )
        logger.info("Market recovery watch complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(f"row_count={output.summary['row_count']}")
        print(f"breadth_wait_count={output.summary['breadth_wait_count']}")
        print(f"overheat_wait_count={output.summary['overheat_wait_count']}")
        print(f"confirmed_count={output.summary['confirmed_count']}")
        print("external_api_requested=NO")
        print("order_status=NO_ORDER")
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Market recovery watch failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

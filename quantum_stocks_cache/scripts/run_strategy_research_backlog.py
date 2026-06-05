from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.strategy_research_backlog import run_strategy_research_backlog

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a local public-research-to-feature backlog report."
    )
    parser.add_argument(
        "--backlog-csv",
        default=str(PROJECT_ROOT / "configs" / "strategy_research_backlog.seed.csv"),
        help="Input strategy research backlog CSV.",
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
        output = run_strategy_research_backlog(
            backlog_csv=Path(args.backlog_csv),
            output_dir=Path(args.output_dir),
        )
        summary = output.summary.iloc[0].to_dict()
        logger.info("Strategy research backlog complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(f"summary_report={output.summary_path}")
        print(f"row_count={summary['row_count']}")
        print(f"p0_count={summary['p0_count']}")
        print(f"p1_count={summary['p1_count']}")
        print(f"p2_count={summary['p2_count']}")
        print("external_api_requested=NO")
        print("order_status=NO_ORDER")
        print("broker_order_requested=NO")
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Strategy research backlog failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

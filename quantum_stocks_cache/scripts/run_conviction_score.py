from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.conviction_score import run_conviction_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a local conviction score report from market watch and company research outputs."
    )
    parser.add_argument(
        "--market-watch-csv",
        default=str(PROJECT_ROOT / "reports" / "market_watch" / "market_watch.csv"),
        help="Input market watch CSV.",
    )
    parser.add_argument(
        "--company-research-csv",
        default=str(PROJECT_ROOT / "reports" / "company_research" / "company_research.csv"),
        help="Input company research CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "reports"),
        help="Output reports root.",
    )
    parser.add_argument(
        "--include-building-focus",
        action="store_true",
        help="Also include BUILDING_FOCUS names before they become PERSISTENT_FOCUS.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        include_labels = ("PERSISTENT_FOCUS", "BUILDING_FOCUS") if args.include_building_focus else ("PERSISTENT_FOCUS",)
        output = run_conviction_score(
            market_watch_csv=Path(args.market_watch_csv),
            company_research_csv=Path(args.company_research_csv),
            output_dir=Path(args.output_dir),
            include_labels=include_labels,
        )
        logger.info("Conviction score complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(output.report.loc[:, ["symbol", "conviction_score", "conviction_tier", "persistence_label"]].to_string(index=False))
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Conviction score failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

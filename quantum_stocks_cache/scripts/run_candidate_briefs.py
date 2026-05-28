from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.candidate_brief import run_candidate_briefs

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create individual company research briefs from the research filter report."
    )
    parser.add_argument(
        "--research-filter-csv",
        default=str(PROJECT_ROOT / "reports" / "research_filter" / "research_filter.csv"),
        help="Input research filter CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "reports"),
        help="Output reports root.",
    )
    parser.add_argument(
        "--status",
        action="append",
        default=None,
        help="Filter status to include. Can be repeated. Defaults to PRIORITY_RESEARCH.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="Optional maximum number of selected companies to write.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        statuses = tuple(args.status) if args.status else ("PRIORITY_RESEARCH",)
        output = run_candidate_briefs(
            research_filter_csv=Path(args.research_filter_csv),
            output_dir=Path(args.output_dir),
            statuses=statuses,
            top_n=args.top_n,
        )
        logger.info("Candidate briefs complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Index report: %s", output.index_path)
        print(f"csv_report={output.csv_path}")
        print(f"index_report={output.index_path}")
        for brief_path in output.brief_paths:
            print(f"brief={brief_path}")
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Candidate briefs failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.event_catalysts import run_event_catalysts

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score local manual news/event catalysts without external API calls."
    )
    parser.add_argument(
        "--event-csv",
        default=str(PROJECT_ROOT / "configs" / "event_catalysts.actual.csv"),
        help="Local manual event catalyst CSV.",
    )
    parser.add_argument(
        "--company-research-csv",
        default=str(PROJECT_ROOT / "reports" / "company_research" / "company_research.csv"),
        help="Company research CSV used for quant/chase-risk context.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "reports"),
        help="Output reports root.",
    )
    parser.add_argument(
        "--as-of",
        default=None,
        help="Optional report date label.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        output = run_event_catalysts(
            event_csv=Path(args.event_csv),
            company_research_csv=Path(args.company_research_csv),
            output_dir=Path(args.output_dir),
            as_of=args.as_of,
        )
        logger.info("Event catalyst report complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(f"input_status={output.summary['input_status']}")
        print(f"event_count={output.summary['event_count']}")
        print(f"external_api_requested={output.summary['external_api_requested']}")
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Event catalyst report failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

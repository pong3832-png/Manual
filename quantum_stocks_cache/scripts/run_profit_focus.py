from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.profit_focus import run_profit_focus

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Distill conviction and checklist reports into a small profit focus list."
    )
    parser.add_argument(
        "--conviction-csv",
        default=str(PROJECT_ROOT / "reports" / "conviction" / "conviction_score.csv"),
        help="Input conviction score CSV.",
    )
    parser.add_argument(
        "--checklist-csv",
        default=str(PROJECT_ROOT / "reports" / "investment_checklist" / "investment_checklist.csv"),
        help="Input investment checklist CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "reports"),
        help="Output reports root.",
    )
    parser.add_argument(
        "--max-core",
        type=int,
        default=3,
        help="Maximum number of CORE_FOCUS candidates.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        output = run_profit_focus(
            conviction_csv=Path(args.conviction_csv),
            checklist_csv=Path(args.checklist_csv),
            output_dir=Path(args.output_dir),
            max_core=args.max_core,
        )
        logger.info("Profit focus complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        logger.info("Today focus report: %s", output.today_focus_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(f"today_focus_report={output.today_focus_path}")
        print(output.report.loc[:, ["symbol", "profit_focus_status", "conviction_score", "why_not_now"]].to_string(index=False))
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Profit focus failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

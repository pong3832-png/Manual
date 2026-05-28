from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.operating_status import run_operating_status

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the final local operating status report without orders.")
    parser.add_argument(
        "--reports-dir",
        default=str(PROJECT_ROOT / "reports"),
        help="Reports root.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional output directory. Defaults to reports/operating_status.",
    )
    parser.add_argument(
        "--dashboard-path",
        default=None,
        help="Optional dashboard path to include in the status report.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        output = run_operating_status(
            reports_dir=Path(args.reports_dir),
            output_dir=Path(args.output_dir) if args.output_dir else None,
            dashboard_path=Path(args.dashboard_path) if args.dashboard_path else None,
        )
        logger.info("Operating status complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        if output.report.empty:
            print("row_count=0")
        else:
            print(
                output.report.loc[
                    :,
                    [
                        "completion_status",
                        "usage_status",
                        "top_symbol",
                        "order_status",
                        "broker_order_requested",
                        "blockers",
                        "next_step",
                    ],
                ].to_string(index=False)
            )
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Operating status failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

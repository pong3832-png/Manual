from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.compliance_pretrade_gate import run_compliance_pretrade_gate

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a local-only compliance pretrade gate report.")
    parser.add_argument(
        "--reports-dir",
        default=str(PROJECT_ROOT / "reports"),
        help="Input reports root.",
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
        output = run_compliance_pretrade_gate(
            reports_dir=Path(args.reports_dir),
            output_dir=Path(args.output_dir),
        )
        logger.info("Compliance pretrade gate complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        logger.info("Summary CSV: %s", output.summary_csv_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(f"summary_csv={output.summary_csv_path}")
        print(
            output.report.loc[
                :,
                [
                    "symbol",
                    "final_compliance_status",
                    "primary_blocker",
                    "blocker_count",
                    "order_status",
                    "broker_order_requested",
                ],
            ].to_string(index=False)
        )
        return 0
    except Exception as exc:
        logger.exception("Compliance pretrade gate failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

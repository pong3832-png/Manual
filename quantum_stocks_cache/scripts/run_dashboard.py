from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.dashboard import run_dashboard

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a one-page local HTML dashboard from current research reports."
    )
    parser.add_argument(
        "--reports-dir",
        default=str(PROJECT_ROOT / "reports"),
        help="Reports root containing profit_focus, investment_memo, and decision_gate outputs.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Dashboard output directory. Defaults to <reports-dir>/dashboard.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        output = run_dashboard(
            reports_dir=Path(args.reports_dir),
            output_dir=Path(args.output_dir) if args.output_dir else None,
        )
        logger.info("Dashboard complete.")
        logger.info("HTML dashboard: %s", output.html_path)
        print(f"dashboard={output.html_path}")
        print(f"top_symbol={output.summary['top_symbol']}")
        print(f"decision_gate_status={output.summary['decision_gate_status']}")
        print(f"order_status={output.summary['order_status']}")
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Dashboard failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

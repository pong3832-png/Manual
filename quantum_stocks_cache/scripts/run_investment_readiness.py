from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.investment_readiness import run_investment_readiness

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a human-review investment readiness report from existing controls."
    )
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "configs" / "portfolio.yaml"),
        help="Path to portfolio YAML config.",
    )
    parser.add_argument(
        "--current-weights-csv",
        required=True,
        help="Actual holdings CSV with columns: symbol,current_weight.",
    )
    parser.add_argument(
        "--trade-plan-csv",
        help="Pre-trade checked trade plan CSV. Defaults to latest reports/runs/* file.",
    )
    parser.add_argument(
        "--alpha-report-csv",
        help="Alpha buy timing report CSV. Defaults to reports/alpha/buy_timing_report.csv.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.01,
        help="Absolute current_weights difference threshold for WARN.",
    )
    parser.add_argument(
        "--reports-dir",
        help="Optional reports directory override. Defaults to reports.output_dir from config.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        result = run_investment_readiness(
            config_path=Path(args.config),
            current_weights_csv=Path(args.current_weights_csv),
            trade_plan_csv=Path(args.trade_plan_csv) if args.trade_plan_csv else None,
            alpha_report_csv=Path(args.alpha_report_csv) if args.alpha_report_csv else None,
            threshold=args.threshold,
            reports_dir=Path(args.reports_dir) if args.reports_dir else None,
        )
        logger.info("Investment readiness status: %s", result.overall_status)
        logger.info("Readiness CSV: %s", result.csv_path)
        logger.info("Readiness Markdown: %s", result.markdown_path)
        logger.info("Current weights check: %s", result.current_weights_check_path)
        print(f"overall_status={result.overall_status}")
        print(f"readiness_csv={result.csv_path}")
        print(f"readiness_markdown={result.markdown_path}")
        print(f"current_weights_check={result.current_weights_check_path}")
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Investment readiness failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

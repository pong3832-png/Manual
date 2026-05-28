from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.capital_scenario import run_capital_scenarios

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create split-buy capital scenarios without placing orders.")
    parser.add_argument(
        "--candidate-checklist-csv",
        default=str(PROJECT_ROOT / "reports" / "investment_checklist" / "investment_checklist.csv"),
        help="Input investment checklist CSV.",
    )
    parser.add_argument(
        "--prices-csv",
        default=str(PROJECT_ROOT / "data" / "prices.csv"),
        help="Input price CSV.",
    )
    parser.add_argument(
        "--capital-plan-dir",
        default=str(PROJECT_ROOT / "reports" / "decision_gate"),
        help="Directory containing capital_plan_review_<code>.csv files.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "reports"),
        help="Output reports root.",
    )
    parser.add_argument(
        "--scenario-capital-krw",
        type=float,
        action="append",
        default=None,
        help="Scenario capital amount. Can be repeated. Defaults to 1M/3M/5M/10M KRW.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        output = run_capital_scenarios(
            candidate_checklist_csv=Path(args.candidate_checklist_csv),
            prices_csv=Path(args.prices_csv),
            capital_plan_dir=Path(args.capital_plan_dir),
            output_dir=Path(args.output_dir),
            scenario_capitals=tuple(args.scenario_capital_krw) if args.scenario_capital_krw else (1_000_000, 3_000_000, 5_000_000, 10_000_000),
        )
        logger.info("Capital scenarios complete.")
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
                        "symbol",
                        "scenario_capital",
                        "scenario_status",
                        "order_status",
                        "first_tranche_shares",
                        "target_position_shares",
                    ],
                ].to_string(index=False)
            )
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Capital scenarios failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.pre_buy_decision import run_pre_buy_decision

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a pre-buy decision report without placing orders.")
    parser.add_argument(
        "--profit-focus-csv",
        default=str(PROJECT_ROOT / "reports" / "profit_focus" / "profit_focus.csv"),
        help="Input profit focus CSV.",
    )
    parser.add_argument(
        "--decision-gate-csv",
        default=str(PROJECT_ROOT / "reports" / "decision_gate" / "decision_gate.csv"),
        help="Input decision gate CSV.",
    )
    parser.add_argument(
        "--company-research-csv",
        default=str(PROJECT_ROOT / "reports" / "company_research" / "company_research.csv"),
        help="Input company research CSV with latest price.",
    )
    parser.add_argument(
        "--filing-risk-dir",
        default=str(PROJECT_ROOT / "reports" / "filing_review"),
        help="Directory containing filing_risk_summary_<code>.csv files.",
    )
    parser.add_argument(
        "--manual-proposal-csv",
        default=str(PROJECT_ROOT / "reports" / "decision_gate" / "manual_review_proposal.csv"),
        help="Optional manual review proposal CSV.",
    )
    parser.add_argument(
        "--capital-plan-dir",
        default=str(PROJECT_ROOT / "reports" / "decision_gate"),
        help="Directory containing capital_plan_review_<code>.csv files.",
    )
    parser.add_argument(
        "--trend-forecast-csv",
        default=str(PROJECT_ROOT / "reports" / "trend_forecast" / "trend_forecast.csv"),
        help="Optional local trend forecast CSV used to block high chase-risk entries.",
    )
    parser.add_argument(
        "--market-regime-csv",
        default=str(PROJECT_ROOT / "reports" / "market_regime" / "market_regime.csv"),
        help="Optional local market/sector regime CSV used to block broad-risk entries.",
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
        output = run_pre_buy_decision(
            profit_focus_csv=Path(args.profit_focus_csv),
            decision_gate_csv=Path(args.decision_gate_csv),
            company_research_csv=Path(args.company_research_csv),
            filing_risk_dir=Path(args.filing_risk_dir),
            output_dir=Path(args.output_dir),
            manual_proposal_csv=Path(args.manual_proposal_csv),
            capital_plan_dir=Path(args.capital_plan_dir),
            trend_forecast_csv=Path(args.trend_forecast_csv),
            market_regime_csv=Path(args.market_regime_csv),
        )
        logger.info("Pre-buy decision complete.")
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
                        "decision_status",
                        "order_status",
                        "final_action",
                        "manual_proposal_status",
                        "capital_status",
                        "readiness_blockers",
                    ],
                ].to_string(index=False)
            )
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Pre-buy decision failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

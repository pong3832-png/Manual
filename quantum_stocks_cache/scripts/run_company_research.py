from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.company_research import run_company_research

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rank company research candidates from local cached price data."
    )
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "configs" / "portfolio.yaml"),
        help="Path to portfolio YAML config.",
    )
    parser.add_argument(
        "--universe-csv",
        help="Optional CSV with columns: symbol,company_name,sector.",
    )
    parser.add_argument(
        "--fundamentals-csv",
        help="Optional CSV with symbol,revenue_growth,operating_margin,roe,per,pbr,debt_ratio.",
    )
    parser.add_argument(
        "--reports-dir",
        help="Optional reports directory override. Defaults to reports.output_dir from config.",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=80,
        help="Minimum samples required for alpha forecast training.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        output = run_company_research(
            config_path=Path(args.config),
            universe_csv=Path(args.universe_csv) if args.universe_csv else None,
            fundamentals_csv=Path(args.fundamentals_csv) if args.fundamentals_csv else None,
            reports_dir=Path(args.reports_dir) if args.reports_dir else None,
            min_samples=args.min_samples,
        )
        logger.info("Company research complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(output.report.loc[:, ["symbol", "research_score", "research_view", "decision"]].to_string(index=False))
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Company research failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.today_pipeline import run_today_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the daily candidate refresh pipeline and rebuild the dashboard."
    )
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "configs" / "portfolio.yaml"),
        help="Portfolio config path.",
    )
    parser.add_argument(
        "--universe-csv",
        default=str(PROJECT_ROOT / "configs" / "research_universe.actual.csv"),
        help="Research universe CSV.",
    )
    parser.add_argument(
        "--fundamentals-csv",
        default=None,
        help="Optional fundamentals CSV. Defaults to configs/fundamentals.actual.csv when it exists.",
    )
    parser.add_argument(
        "--shares-csv",
        default=None,
        help="Optional shares outstanding CSV. Defaults to configs/shares_outstanding.actual.csv when it exists.",
    )
    parser.add_argument(
        "--reports-dir",
        default=str(PROJECT_ROOT / "reports"),
        help="Reports output root.",
    )
    parser.add_argument(
        "--manual-review-csv",
        default=None,
        help="Optional manual review CSV for decision gate.",
    )
    parser.add_argument(
        "--refresh-market-data",
        action="store_true",
        help="Fetch latest prices first. This is now the default unless --cached-market-data is set.",
    )
    parser.add_argument(
        "--cached-market-data",
        action="store_true",
        help="Use existing data/prices.csv without calling the external market data provider.",
    )
    parser.add_argument(
        "--strict-persistence",
        action="store_true",
        help="Only include PERSISTENT_FOCUS names in conviction scoring.",
    )
    parser.add_argument(
        "--add-stock",
        default=None,
        help="Easy stock input to add before the pipeline runs, for example 삼성전자, 현대차, 005930.",
    )
    parser.add_argument(
        "--add-code",
        default=None,
        help="Optional six-digit KRX code to add to the universe before the pipeline runs.",
    )
    parser.add_argument(
        "--add-symbol",
        default=None,
        help="Optional full symbol to add to the universe before the pipeline runs, for example 006800.KS.",
    )
    parser.add_argument(
        "--add-symbols-csv",
        default=None,
        help="Optional CSV of companies to add to the universe before the pipeline runs.",
    )
    parser.add_argument(
        "--add-company-name",
        default="",
        help="Company name for --add-code/--add-symbol.",
    )
    parser.add_argument(
        "--add-market",
        default="KOSPI",
        help="Market for --add-code, such as KOSPI or KOSDAQ.",
    )
    parser.add_argument(
        "--add-sector",
        default="UNKNOWN",
        help="Sector label for --add-code/--add-symbol.",
    )
    parser.add_argument(
        "--replace-symbol",
        action="store_true",
        help="Update an existing universe row for --add-code/--add-symbol.",
    )
    parser.add_argument(
        "--symbol-min-samples",
        type=int,
        default=80,
        help="Minimum cached price rows required for the optional symbol intake report.",
    )
    parser.add_argument(
        "--total-capital-krw",
        type=float,
        default=None,
        help="Optional total capital for capital plan and review-only sizing. Does not place orders.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned steps without executing them.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        output = run_today_pipeline(
            project_root=PROJECT_ROOT,
            config_path=Path(args.config),
            universe_csv=Path(args.universe_csv),
            fundamentals_csv=Path(args.fundamentals_csv) if args.fundamentals_csv else None,
            shares_csv=Path(args.shares_csv) if args.shares_csv else None,
            reports_dir=Path(args.reports_dir),
            manual_review_csv=Path(args.manual_review_csv) if args.manual_review_csv else None,
            refresh_market_data=args.refresh_market_data or not args.cached_market_data,
            include_building_focus=not args.strict_persistence,
            add_stock=args.add_stock,
            add_code=args.add_code,
            add_symbol=args.add_symbol,
            add_symbols_csv=Path(args.add_symbols_csv) if args.add_symbols_csv else None,
            add_company_name=args.add_company_name,
            add_market=args.add_market,
            add_sector=args.add_sector,
            replace_symbol=args.replace_symbol,
            symbol_min_samples=args.symbol_min_samples,
            total_capital_krw=args.total_capital_krw,
            dry_run=args.dry_run,
        )
        for step in output.steps:
            marker = "EXTERNAL_API" if step.external_api else "LOCAL"
            print(f"[{marker}] {step.name}: {' '.join(step.command)}")
        print(f"executed_count={output.summary['executed_count']}")
        print(f"analysis_date={output.summary['analysis_date']}")
        print(f"market_data_refresh={output.summary['market_data_refresh']}")
        print(f"external_api_requested={output.summary['external_api_requested']}")
        print(f"symbol_intake_requested={output.summary['symbol_intake_requested']}")
        print(f"dashboard={output.summary['dashboard_path']}")
        logger.info("Today pipeline complete.")
        return 0
    except Exception as exc:
        logger.exception("Today pipeline failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

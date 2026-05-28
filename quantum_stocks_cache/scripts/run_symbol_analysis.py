from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.symbol_analysis import run_symbol_analysis

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add one company to the local universe and produce a no-order symbol analysis report."
    )
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "configs" / "portfolio.yaml"),
        help="Path to portfolio YAML config.",
    )
    parser.add_argument(
        "--universe-csv",
        default=str(PROJECT_ROOT / "configs" / "research_universe.actual.csv"),
        help="Active research universe CSV.",
    )
    parser.add_argument("--code", default=None, help="Six-digit KRX code, for example 006800.")
    parser.add_argument("--symbol", default=None, help="Full symbol, for example 006800.KS.")
    parser.add_argument("--company-name", default="", help="Company name to store.")
    parser.add_argument("--market", default="KOSPI", help="KOSPI/KOSDAQ/KQ/KS. Defaults to KOSPI.")
    parser.add_argument("--sector", default="UNKNOWN", help="Sector label.")
    parser.add_argument("--replace", action="store_true", help="Update an existing universe row.")
    parser.add_argument(
        "--fundamentals-csv",
        default=None,
        help="Optional fundamentals CSV for valuation/fundamental score blending.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "reports"),
        help="Output reports root.",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=80,
        help="Minimum cached price rows required for local analysis.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        output = run_symbol_analysis(
            config_path=Path(args.config),
            universe_csv=Path(args.universe_csv),
            output_dir=Path(args.output_dir),
            code=args.code,
            symbol=args.symbol,
            company_name=args.company_name,
            market=args.market,
            sector=args.sector,
            fundamentals_csv=Path(args.fundamentals_csv) if args.fundamentals_csv else None,
            replace=args.replace,
            min_samples=args.min_samples,
        )
        logger.info("Symbol analysis complete.")
        logger.info("CSV report: %s", output.csv_path)
        logger.info("Markdown report: %s", output.markdown_path)
        print(f"csv_report={output.csv_path}")
        print(f"markdown_report={output.markdown_path}")
        print(f"symbol={output.symbol}")
        print(f"analysis_status={output.status}")
        print(f"external_api_requested={output.summary['external_api_requested']}")
        print("order_status=NO_ORDER")
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Symbol analysis failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

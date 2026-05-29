from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.krx_universe import DEFAULT_EQUITY_MARKETS, fetch_pykrx_equity_universe

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch KOSPI/KOSDAQ equity universe through pykrx.")
    parser.add_argument(
        "--output-csv",
        default=str(PROJECT_ROOT / "configs" / "research_universe.full.csv"),
        help="Output normalized universe CSV.",
    )
    parser.add_argument(
        "--markets",
        nargs="+",
        default=list(DEFAULT_EQUITY_MARKETS),
        help="KRX markets to fetch, default: KOSPI KOSDAQ.",
    )
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y%m%d"),
        help="KRX listing date as YYYYMMDD. Defaults to today to avoid pykrx nearest-day lookup.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        output_csv = Path(args.output_csv).resolve()
        universe = fetch_pykrx_equity_universe(markets=args.markets, date=args.date)
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        universe.to_csv(output_csv, index=False, encoding="utf-8-sig")

        print(f"output_csv={output_csv}")
        print(f"row_count={len(universe)}")
        print(f"kospi_count={int((universe['market'] == 'KOSPI').sum())}")
        print(f"kosdaq_count={int((universe['market'] == 'KOSDAQ').sum())}")
        print(f"date={args.date}")
        print("external_api_requested=YES")
        print("order_status=NO_ORDER")
        return 0
    except Exception as exc:
        logger.exception("pykrx universe fetch failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

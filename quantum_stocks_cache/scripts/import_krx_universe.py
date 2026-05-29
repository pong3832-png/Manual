from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.research_universe import normalize_full_krx_universe

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import a user-provided full KRX universe CSV locally.")
    parser.add_argument("--source-csv", required=True, help="Downloaded KRX-style CSV.")
    parser.add_argument(
        "--output-csv",
        default=str(PROJECT_ROOT / "configs" / "research_universe.full.csv"),
        help="Output normalized full universe CSV.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        source_csv = Path(args.source_csv).resolve()
        output_csv = Path(args.output_csv).resolve()
        if not source_csv.exists():
            raise FileNotFoundError(f"KRX universe source CSV not found: {source_csv}")

        source = pd.read_csv(source_csv, dtype=str).fillna("")
        universe = normalize_full_krx_universe(source)
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        universe.to_csv(output_csv, index=False, encoding="utf-8-sig")

        print(f"output_csv={output_csv}")
        print(f"row_count={len(universe)}")
        print(f"kospi_count={int((universe['market'] == 'KOSPI').sum())}")
        print(f"kosdaq_count={int((universe['market'] == 'KOSDAQ').sum())}")
        print("external_api_requested=NO")
        print("order_status=NO_ORDER")
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("KRX universe import failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.kind_universe import read_kind_corp_list, normalize_kind_corp_list

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import a downloaded KRX KIND listed-corporation file locally.")
    parser.add_argument("--source-xls", required=True, help="Downloaded KIND corpList HTML/XLS file.")
    parser.add_argument(
        "--output-csv",
        default=str(PROJECT_ROOT / "configs" / "research_universe.full.csv"),
        help="Output normalized universe CSV.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        source_xls = Path(args.source_xls).resolve()
        output_csv = Path(args.output_csv).resolve()
        if not source_xls.exists():
            raise FileNotFoundError(f"KIND corp list source not found: {source_xls}")

        raw = read_kind_corp_list(source_xls)
        universe = normalize_kind_corp_list(raw)
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        universe.to_csv(output_csv, index=False, encoding="utf-8-sig")

        print(f"output_csv={output_csv}")
        print(f"row_count={len(universe)}")
        print(f"kospi_count={int((universe['market'] == 'KOSPI').sum())}")
        print(f"kosdaq_count={int((universe['market'] == 'KOSDAQ').sum())}")
        print("external_api_requested=NO")
        print("order_status=NO_ORDER")
        return 0
    except Exception as exc:
        logger.exception("KIND corp list import failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

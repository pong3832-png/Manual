from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.fundamentals import load_fundamentals_csv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and score fundamentals CSV.")
    parser.add_argument(
        "--fundamentals-csv",
        required=True,
        help="CSV with symbol,revenue_growth,operating_margin,roe,per,pbr,debt_ratio.",
    )
    parser.add_argument(
        "--output-csv",
        default=str(PROJECT_ROOT / "reports" / "fundamentals" / "fundamentals_scored.csv"),
        help="Output scored fundamentals CSV.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        scored = load_fundamentals_csv(Path(args.fundamentals_csv))
        output_path = Path(args.output_csv).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        scored.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info("Scored fundamentals written: %s", output_path)
        print(f"output_csv={output_path}")
        print(scored.loc[:, ["symbol", "fundamental_score", "fundamental_view"]].to_string(index=False))
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Fundamentals check failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
